"""
SQL storage layer (SQLite) for persisting and retrieving research data.

SQLite is used so the project runs anywhere with zero external database
setup, while still exercising real SQL (schema, indexes, parameterized
queries) as required. Swapping to Postgres/MySQL later only requires
changing the connection layer -- the SQL itself is portable.
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import List, Optional

import config
from src.exceptions import DatabaseError
from src.models import Article, StoredArticle

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id       INTEGER NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT,
    url           TEXT,
    categories    TEXT,          -- JSON-encoded list
    word_count    INTEGER DEFAULT 0,
    source        TEXT DEFAULT 'wikipedia',
    fetched_at    TEXT NOT NULL,
    UNIQUE(page_id, source)
);

CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title);
CREATE INDEX IF NOT EXISTS idx_articles_fetched_at ON articles(fetched_at);

CREATE TABLE IF NOT EXISTS search_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query       TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    searched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class ResearchDatabase:
    """Handles all persistence for retrieved Wikipedia articles."""

    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(f"Database operation failed: {exc}") from exc
        finally:
            conn.close()

    def _init_schema(self) -> None:
        try:
            with self._connect() as conn:
                conn.executescript(SCHEMA)
        except DatabaseError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to initialize schema: {exc}") from exc

    # -- writes ------------------------------------------------------------

    def save_article(self, article: Article) -> int:
        """Insert an article, or update it if the same page was already stored."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO articles
                    (page_id, title, summary, url, categories, word_count, source, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(page_id, source) DO UPDATE SET
                    title=excluded.title,
                    summary=excluded.summary,
                    url=excluded.url,
                    categories=excluded.categories,
                    word_count=excluded.word_count,
                    fetched_at=excluded.fetched_at
                """,
                (
                    article.page_id,
                    article.title,
                    article.summary,
                    article.url,
                    json.dumps(article.categories),
                    article.word_count,
                    article.source,
                    article.fetched_at,
                ),
            )
            if cursor.lastrowid:
                return cursor.lastrowid
            row = conn.execute(
                "SELECT id FROM articles WHERE page_id = ? AND source = ?",
                (article.page_id, article.source),
            ).fetchone()
            return row["id"] if row else -1

    def log_search(self, query: str, result_count: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO search_log (query, result_count) VALUES (?, ?)",
                (query, result_count),
            )

    # -- reads -------------------------------------------------------------

    def get_by_title(self, title: str) -> Optional[StoredArticle]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM articles WHERE title = ? COLLATE NOCASE",
                (title,),
            ).fetchone()
            return _row_to_article(row) if row else None

    def search_stored(self, keyword: str, limit: int = 20) -> List[StoredArticle]:
        """Full-text-ish search across stored titles and summaries using SQL LIKE."""
        pattern = f"%{keyword}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM articles
                WHERE title LIKE ? OR summary LIKE ?
                ORDER BY fetched_at DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            ).fetchall()
            return [_row_to_article(r) for r in rows]

    def list_recent(self, limit: int = 10) -> List[StoredArticle]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM articles ORDER BY fetched_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [_row_to_article(r) for r in rows]

    def delete_article(self, page_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM articles WHERE page_id = ?", (page_id,)
            )
            return cursor.rowcount > 0

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM articles").fetchone()
            return row["c"]


def _row_to_article(row: sqlite3.Row) -> StoredArticle:
    return StoredArticle(
        record_id=row["id"],
        page_id=row["page_id"],
        title=row["title"],
        summary=row["summary"] or "",
        url=row["url"] or "",
        categories=json.loads(row["categories"] or "[]"),
        word_count=row["word_count"] or 0,
        source=row["source"] or "wikipedia",
        fetched_at=row["fetched_at"],
    )
