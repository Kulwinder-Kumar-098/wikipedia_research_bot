#!/usr/bin/env python3
"""
Example: using ResearchBot as a library inside another Python program.

Run from the project root:
    python examples/usage_example.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import DisambiguationError, WikiBotError
from src.research_bot import ResearchBot


def main():
    bot = ResearchBot()

    # 1. Search for a topic
    print("Searching for 'artificial intelligence'...")
    results = bot.search("artificial intelligence", limit=5)
    for r in results:
        print(f"  - {r.title}")

    # 2. Research and store a specific article
    print("\nFetching article: 'Artificial intelligence'...")
    try:
        article = bot.research_topic("Artificial intelligence")
        print(f"  Title: {article.title}")
        print(f"  Word count: {article.word_count}")
        print(f"  Summary: {article.summary[:200]}...")
    except DisambiguationError as exc:
        print(f"  Ambiguous title: {exc}")
    except WikiBotError as exc:
        print(f"  Could not fetch article: {exc}")

    # 3. Research several topics at once, skipping failures
    print("\nBatch researching multiple topics...")
    topics = ["Machine learning", "Neural network", "Nonexistent Topic Xyzabc123"]
    articles = bot.research_many(topics)
    print(f"  Successfully researched {len(articles)}/{len(topics)} topics.")

    # 4. Search what has been stored locally
    print("\nSearching local database for 'learning'...")
    stored = bot.find_stored("learning")
    for s in stored:
        print(f"  - {s.title} (stored {s.fetched_at})")

    # 5. Stats
    print(f"\nTotal articles stored: {bot.stats()['stored_articles']}")


if __name__ == "__main__":
    main()
