"""
Text processing and input validation utilities.

Separated from the API client so the cleaning/summarization rules can be
unit-tested without any network access.
"""

import re
from typing import List

from src.exceptions import InvalidInputError
from src.models import Article

_WHITESPACE_RE = re.compile(r"\s+")
_MAX_QUERY_LENGTH = 300


def validate_query(query: str, max_length: int = _MAX_QUERY_LENGTH) -> str:
    """Validate and normalize a raw search query string.

    Raises InvalidInputError for empty, non-string, or overlong input.
    """
    if not isinstance(query, str):
        raise InvalidInputError("Query must be a string.")

    cleaned = query.strip()
    if not cleaned:
        raise InvalidInputError("Query cannot be empty.")
    if len(cleaned) > max_length:
        raise InvalidInputError(
            f"Query is too long ({len(cleaned)} chars); max is {max_length}."
        )
    return cleaned


def clean_text(text: str) -> str:
    """Collapse whitespace and strip stray control characters from raw text."""
    if not text:
        return ""
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def summarize(text: str, max_sentences: int = 3) -> str:
    """Produce a short extractive summary: the first N sentences of `text`.

    This is intentionally simple and dependency-free (no NLP libraries
    required), which keeps the project easy to deploy anywhere.
    """
    text = clean_text(text)
    if not text:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:max_sentences])
    return summary


def word_count(text: str) -> int:
    return len(clean_text(text).split())


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Very lightweight keyword extraction based on word frequency.

    Filters out common English stopwords and short tokens. Good enough for
    tagging/search-hinting without pulling in a heavy NLP dependency.
    """
    stopwords = {
        "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
        "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
        "it", "its", "this", "that", "these", "those", "be", "been",
        "has", "have", "had", "not", "which", "who", "whom", "also",
    }
    words = re.findall(r"[A-Za-z]{3,}", text.lower())
    freq = {}
    for w in words:
        if w in stopwords:
            continue
        freq[w] = freq.get(w, 0) + 1

    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    return [word for word, _ in ranked[:top_n]]


def process_article(article: Article, full_text: str = None) -> Article:
    """Apply cleaning/summarization to a raw Article before storage."""
    article.summary = clean_text(article.summary)
    if full_text:
        article.content = clean_text(full_text)
        article.word_count = word_count(full_text)
    else:
        article.content = article.summary
        article.word_count = word_count(article.summary)
    return article
