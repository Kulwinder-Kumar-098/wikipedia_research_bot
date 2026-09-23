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
from src.embedding_client import EmbeddingClient
from src.llm_client import LLMClient
from src.exceptions import (
    DisambiguationError,
    EmbeddingError,
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
        llm_client: Optional[LLMClient] = None,
        embedding_client: Optional[EmbeddingClient] = None,
    ):
        self.api = api_client or WikipediaAPIClient()
        self.db = database or ResearchDatabase()
        self.llm = llm_client or LLMClient()
        self.embedder = embedding_client or EmbeddingClient()

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
            article_id = self.db.save_article(article)
            try:
                embedding = self.embedder.embed(article.content or article.summary)
                self.db.save_embedding(article_id, embedding, self.embedder.model)
            except EmbeddingError as exc:
                logger.warning("Could not create vector embedding for '%s': %s", article.title, exc)

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

    def ask(self, question: str, limit: int = config.RAG_MAX_SOURCES) -> dict:
        """Retrieve nearest vector matches and answer strictly from them."""
        clean_question = text_processor.validate_query(question)
        query_embedding = self.embedder.embed(clean_question)
        sources = self.db.vector_search(query_embedding, limit=limit)
        if not sources:
            return {"answer": "I could not find relevant information in the knowledge base.", "sources": []}
        context_parts = []
        used_chars = 0
        for source in sources:
            excerpt = (source.content or source.summary).strip()
            remaining = config.RAG_MAX_CONTEXT_CHARS - used_chars
            if remaining <= 0:
                break
            excerpt = excerpt[:remaining]
            context_parts.append(f"[{source.title}]\n{excerpt}\nURL: {source.url}")
            used_chars += len(excerpt)
        answer = self.llm.answer(clean_question, "\n\n".join(context_parts))
        return {
            "answer": answer,
            "sources": [{"title": source.title, "url": source.url} for source in sources],
        }

    def recent(self, limit: int = 10) -> List[StoredArticle]:
        return self.db.list_recent(limit=limit)

    def reindex_vectors(self) -> int:
        """Create or refresh vectors for every article already in the database."""
        indexed = 0
        for article in self.db.list_recent(limit=1_000_000):
            embedding = self.embedder.embed(article.content or article.summary)
            if article.record_id is not None:
                self.db.save_embedding(article.record_id, embedding, self.embedder.model)
                indexed += 1
        return indexed

    def stats(self) -> dict:
        return {"stored_articles": self.db.count()}
