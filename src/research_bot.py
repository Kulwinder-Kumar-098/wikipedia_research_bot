"""
ResearchBot: the reusable, high-level module that ties together the API
client, text processor, and database. This is the main object other code
(the CLI, tests, or another application) should import and use.
"""

import logging
from typing import List, Optional

import config
from src import text_processor
from src.api_client import WikipediaAPIClient
from src.database import ResearchDatabase
from src.exceptions import (
    DisambiguationError,
    InvalidInputError,
    PageNotFoundError,
    WikiBotError,
)
from src.models import Article, SearchResult, StoredArticle

logger = logging.getLogger(__name__)


class ResearchBot:
    """Coordinates search, retrieval, processing, and storage."""

    def __init__(
        self,
        api_client: Optional[WikipediaAPIClient] = None,
        database: Optional[ResearchDatabase] = None,
    ):
        self.api = api_client or WikipediaAPIClient()
        self.db = database or ResearchDatabase()

    def search(self, query: str, limit: int = config.DEFAULT_SEARCH_LIMIT) -> List[SearchResult]:
        """Validate a query, search Wikipedia, and log the search."""
        clean_query = text_processor.validate_query(query)
        results = self.api.search(clean_query, limit=limit)
        try:
            self.db.log_search(clean_query, len(results))
        except WikiBotError as exc:
            # Logging search history is best-effort; don't fail the search over it.
            logger.warning("Could not log search: %s", exc)
        return results

    def research_topic(self, title: str, fetch_full_text: bool = False, store: bool = True) -> Article:
        """Fetch, process, and (optionally) persist a single article by title."""
        clean_title = text_processor.validate_query(title, max_length=500)

        try:
            article = self.api.get_summary(clean_title)
        except DisambiguationError:
            raise
        except PageNotFoundError:
            raise

        try:
            article.categories = self.api.get_categories(article.title)
        except WikiBotError as exc:
            logger.warning("Could not fetch categories for '%s': %s", article.title, exc)
            article.categories = []

        full_text = None
        if fetch_full_text:
            try:
                full_text = self.api.get_full_extract(article.title)
            except WikiBotError as exc:
                logger.warning("Could not fetch full text for '%s': %s", article.title, exc)

        article = text_processor.process_article(article, full_text=full_text)

        if store:
            self.db.save_article(article)

        return article

    def research_many(self, titles: List[str], fetch_full_text: bool = False) -> List[Article]:
        """Research multiple topics, continuing past individual failures."""
        articles = []
        for title in titles:
            try:
                articles.append(self.research_topic(title, fetch_full_text=fetch_full_text))
            except WikiBotError as exc:
                logger.error("Skipping '%s': %s", title, exc)
        return articles

    def find_stored(self, keyword: str, limit: int = 20) -> List[StoredArticle]:
        clean_keyword = text_processor.validate_query(keyword)
        return self.db.search_stored(clean_keyword, limit=limit)

    def recent(self, limit: int = 10) -> List[StoredArticle]:
        return self.db.list_recent(limit=limit)

    def stats(self) -> dict:
        return {"stored_articles": self.db.count()}
