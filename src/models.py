"""
Plain data structures shared across the application.

Using dataclasses keeps the API client, text processor, and database layer
decoupled -- each only needs to know about this shape, not about each other.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class SearchResult:
    """A single hit returned by the Wikipedia search endpoint."""

    title: str
    page_id: int
    snippet: str = ""


@dataclass
class Article:
    """A processed Wikipedia article ready for storage or display."""

    title: str
    page_id: int
    summary: str
    url: str
    categories: List[str] = field(default_factory=list)
    word_count: int = 0
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = "wikipedia"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "page_id": self.page_id,
            "summary": self.summary,
            "url": self.url,
            "categories": self.categories,
            "word_count": self.word_count,
            "fetched_at": self.fetched_at,
            "source": self.source,
        }


@dataclass
class StoredArticle(Article):
    """An Article that has been persisted, with its database row id attached."""

    record_id: Optional[int] = None
