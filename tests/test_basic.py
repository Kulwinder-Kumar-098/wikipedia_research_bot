"""
Basic unit tests.

Run with:  python -m pytest tests/ -v
These tests avoid network calls -- they test validation, text processing,
and the database layer only, so they run fast and deterministically in CI.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import text_processor
from src.database import ResearchDatabase
from src.exceptions import DatabaseError, InvalidInputError
from src.llm_client import normalize_answer
from src.models import Article
from src.research_bot import ResearchBot


class TestTextProcessor(unittest.TestCase):
    def test_validate_query_strips_whitespace(self):
        self.assertEqual(text_processor.validate_query("  hello  "), "hello")

    def test_validate_query_rejects_empty(self):
        with self.assertRaises(InvalidInputError):
            text_processor.validate_query("   ")

    def test_validate_query_rejects_non_string(self):
        with self.assertRaises(InvalidInputError):
            text_processor.validate_query(12345)

    def test_validate_query_rejects_too_long(self):
        with self.assertRaises(InvalidInputError):
            text_processor.validate_query("a" * 400, max_length=300)

    def test_clean_text_collapses_whitespace(self):
        self.assertEqual(text_processor.clean_text("a   b\n\nc"), "a b c")

    def test_summarize_limits_sentences(self):
        text = "One. Two. Three. Four."
        summary = text_processor.summarize(text, max_sentences=2)
        self.assertEqual(summary, "One. Two.")

    def test_word_count(self):
        self.assertEqual(text_processor.word_count("the quick brown fox"), 4)

    def test_extract_keywords_filters_stopwords(self):
        keywords = text_processor.extract_keywords(
            "The quantum computer uses quantum bits for quantum computation"
        )
        self.assertIn("quantum", keywords)
        self.assertNotIn("the", keywords)
        self.assertNotIn("for", keywords)

    def test_normalize_llm_answer(self):
        answer = "Lana\u202fDel\u202fRey is a singer\u2011songwriter【Lana Del Ray (album)】."
        self.assertEqual(
            normalize_answer(answer),
            "Lana Del Rey is a singer-songwriter[Lana Del Ray (album)].",
        )


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test.db")
        self.db = ResearchDatabase(db_path=self.db_path)

    def _sample_article(self, page_id=1, title="Test Article", summary=None):
        return Article(
            title=title,
            page_id=page_id,
            summary=summary or f"This is a test summary about {title}.",
            url="https://en.wikipedia.org/wiki/Test_Article",
            categories=["Physics", "Computing"],
            word_count=8,
        )

    def test_save_and_get_by_title(self):
        self.db.save_article(self._sample_article())
        found = self.db.get_by_title("Test Article")
        self.assertIsNotNone(found)
        self.assertEqual(found.title, "Test Article")
        self.assertIn("Physics", found.categories)

    def test_upsert_on_duplicate_page_id(self):
        self.db.save_article(self._sample_article(page_id=42, title="Original Title"))
        self.db.save_article(self._sample_article(page_id=42, title="Updated Title"))
        self.assertEqual(self.db.count(), 1)
        found = self.db.get_by_title("Updated Title")
        self.assertIsNotNone(found)

    def test_search_stored_matches_keyword(self):
        self.db.save_article(self._sample_article(page_id=1, title="Quantum Computing"))
        self.db.save_article(self._sample_article(page_id=2, title="Classical Mechanics"))
        results = self.db.search_stored("quantum")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Quantum Computing")

    def test_list_recent_orders_by_fetched_at(self):
        self.db.save_article(self._sample_article(page_id=1, title="First"))
        self.db.save_article(self._sample_article(page_id=2, title="Second"))
        recent = self.db.list_recent(limit=2)
        self.assertEqual(len(recent), 2)

    def test_delete_article(self):
        self.db.save_article(self._sample_article(page_id=99, title="To Delete"))
        self.assertTrue(self.db.delete_article(99))
        self.assertIsNone(self.db.get_by_title("To Delete"))

    def test_retrieve_includes_article_content(self):
        article = self._sample_article(page_id=7, title="Quantum Computing")
        article.content = "Quantum computers use qubits to process information."
        self.db.save_article(article)
        results = self.db.retrieve("qubits")
        self.assertEqual([result.title for result in results], ["Quantum Computing"])


class FakeLLM:
    def __init__(self):
        self.context = ""

    def answer(self, question, context):
        self.context = context
        return "Quantum computers use qubits. [Quantum Computing]"


class FakeEmbedding:
    model = "test-embeddings"

    def embed(self, text):
        return [1.0, 0.0] if "quantum" in text.lower() or "qubits" in text.lower() else [0.0, 1.0]


class TestRAG(unittest.TestCase):
    def test_ask_retrieves_context_and_returns_sources(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            database = ResearchDatabase(db_path=os.path.join(tmp_dir, "rag.db"))
            article = Article(
                title="Quantum Computing",
                page_id=8,
                summary="Quantum computing uses qubits.",
                content="Quantum computers use qubits to process information.",
                url="https://example.test/quantum",
            )
            database.save_article(article)
            database.save_embedding(1, [1.0, 0.0], "test-embeddings")
            llm = FakeLLM()
            result = ResearchBot(
                database=database,
                llm_client=llm,
                embedding_client=FakeEmbedding(),
            ).ask("How do qubits process information?")
            self.assertIn("qubits", llm.context)
            self.assertIn("Quantum computers", result["answer"])
            self.assertEqual(result["sources"][0]["title"], "Quantum Computing")


if __name__ == "__main__":
    unittest.main()
