"""
API client responsible for all communication with Wikipedia's REST and
Action APIs. This is the only module that knows about HTTP -- everything
downstream works with plain Python objects (see models.py).
"""

import logging
import time
from typing import List
from urllib.parse import quote

import requests

import config
from src.exceptions import (
    APIRequestError,
    DisambiguationError,
    PageNotFoundError,
    RateLimitError,
)
from src.models import Article, SearchResult

logger = logging.getLogger(__name__)


class WikipediaAPIClient:
    """Thin, resilient wrapper around Wikipedia's public APIs."""

    def __init__(
        self,
        language: str = config.WIKI_LANGUAGE,
        timeout: float = config.REQUEST_TIMEOUT,
        max_retries: int = config.MAX_RETRIES,
    ):
        self.language = language
        self.action_base = f"https://{language}.wikipedia.org/w/api.php"
        self.rest_base = f"https://{language}.wikipedia.org/api/rest_v1"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})

    # -- low level -------------------------------------------------------

    def _get(self, url: str, params: dict = None) -> dict:
        """Perform a GET request with retry/backoff and normalized errors."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url, params=params, timeout=self.timeout
                )
                if response.status_code == 429:
                    raise RateLimitError(
                        "Wikipedia API rate limit hit (HTTP 429)."
                    )
                if response.status_code == 404:
                    raise PageNotFoundError("Requested resource was not found.")
                response.raise_for_status()
                return response.json()
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                logger.warning(
                    "Network error on attempt %d/%d: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                time.sleep(config.RETRY_BACKOFF_SECONDS * attempt)
            except requests.HTTPError as exc:
                raise APIRequestError(f"Wikipedia API returned an error: {exc}") from exc

        raise APIRequestError(
            f"Failed to reach Wikipedia API after {self.max_retries} attempts: {last_error}"
        )

    # -- public methods ---------------------------------------------------

    def search(
        self, query: str, limit: int = config.DEFAULT_SEARCH_LIMIT
    ) -> List[SearchResult]:
        """Search Wikipedia for articles matching `query`."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        data = self._get(self.action_base, params)
        hits = data.get("query", {}).get("search", [])

        results = []
        for hit in hits:
            snippet = _strip_html(hit.get("snippet", ""))
            results.append(
                SearchResult(
                    title=hit["title"], page_id=hit["pageid"], snippet=snippet
                )
            )
        return results

    def get_summary(self, title: str) -> Article:
        """Fetch a structured summary for an exact article title."""
        encoded_title = quote(title.replace(" ", "_"))
        url = f"{self.rest_base}/page/summary/{encoded_title}"

        try:
            data = self._get(url)
        except PageNotFoundError:
            raise PageNotFoundError(f"No Wikipedia article found for '{title}'.")

        if data.get("type") == "disambiguation":
            options = self._get_disambiguation_options(title)
            raise DisambiguationError(title, options)

        return Article(
            title=data.get("title", title),
            page_id=data.get("pageid", 0),
            summary=data.get("extract", ""),
            url=data.get("content_urls", {})
            .get("desktop", {})
            .get("page", f"https://{self.language}.wikipedia.org/wiki/{encoded_title}"),
            categories=[],
            word_count=len(data.get("extract", "").split()),
        )

    def get_categories(self, title: str) -> List[str]:
        """Fetch the categories an article belongs to."""
        params = {
            "action": "query",
            "prop": "categories",
            "titles": title,
            "cllimit": "max",
            "format": "json",
        }
        data = self._get(self.action_base, params)
        pages = data.get("query", {}).get("pages", {})
        categories = []
        for page in pages.values():
            for cat in page.get("categories", []):
                name = cat.get("title", "").replace("Category:", "")
                categories.append(name)
        return categories

    def get_full_extract(self, title: str) -> str:
        """Fetch the full plain-text extract of an article (not just the lead)."""
        params = {
            "action": "query",
            "prop": "extracts",
            "explaintext": True,
            "titles": title,
            "format": "json",
        }
        data = self._get(self.action_base, params)
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "missing" in page:
                raise PageNotFoundError(f"No Wikipedia article found for '{title}'.")
            return page.get("extract", "")
        return ""

    def _get_disambiguation_options(self, title: str) -> List[str]:
        params = {
            "action": "query",
            "prop": "links",
            "titles": title,
            "pllimit": "20",
            "format": "json",
        }
        try:
            data = self._get(self.action_base, params)
        except WikiBotErrorTypes:
            return []
        pages = data.get("query", {}).get("pages", {})
        options = []
        for page in pages.values():
            for link in page.get("links", []):
                options.append(link.get("title", ""))
        return [o for o in options if o]


# Tuple of exception types that should be swallowed when fetching optional
# disambiguation metadata (best-effort only, must not raise itself).
WikiBotErrorTypes = (APIRequestError, RateLimitError, PageNotFoundError)


def _strip_html(text: str) -> str:
    """Remove simple HTML tags (e.g. <span class="searchmatch">) from snippets."""
    import re

    return re.sub(r"<[^>]+>", "", text)
