#!/usr/bin/env python3
"""
Intelligent Wikipedia Research Bot -- CLI entry point.

Usage examples:
    python main.py search "quantum computing"
    python main.py research "Alan Turing"
    python main.py research "Python (programming language)" --full-text
    python main.py find "machine learning"
    python main.py recent --limit 5
    python main.py stats
    python main.py interactive
"""

import argparse
import logging
import os
import sys

import config
from src.exceptions import WikiBotError
from src.research_bot import ResearchBot


def setup_logging() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )


def cmd_search(bot: ResearchBot, args) -> None:
    results = bot.search(args.query, limit=args.limit)
    if not results:
        print(f"No results found for '{args.query}'.")
        return
    print(f"\nFound {len(results)} result(s) for '{args.query}':\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.title}  (page_id={r.page_id})")
        if r.snippet:
            print(f"   {r.snippet}")


def cmd_research(bot: ResearchBot, args) -> None:
    article = bot.research_topic(args.title, fetch_full_text=args.full_text)
    print(f"\n{article.title}")
    print("=" * len(article.title))
    print(article.summary or "(no summary available)")
    print(f"\nWord count: {article.word_count}")
    if article.categories:
        print(f"Categories: {', '.join(article.categories[:8])}")
    print(f"URL: {article.url}")
    print("\nSaved to database.")


def cmd_find(bot: ResearchBot, args) -> None:
    results = bot.find_stored(args.keyword, limit=args.limit)
    if not results:
        print(f"Nothing stored matching '{args.keyword}'.")
        return
    print(f"\n{len(results)} stored article(s) matching '{args.keyword}':\n")
    for r in results:
        print(f"- {r.title} (fetched {r.fetched_at})")


def cmd_recent(bot: ResearchBot, args) -> None:
    results = bot.recent(limit=args.limit)
    if not results:
        print("No articles stored yet.")
        return
    print(f"\n{len(results)} most recently stored article(s):\n")
    for r in results:
        print(f"- {r.title} (fetched {r.fetched_at})")


def cmd_stats(bot: ResearchBot, args) -> None:
    stats = bot.stats()
    print(f"Stored articles: {stats['stored_articles']}")


def cmd_interactive(bot: ResearchBot, args) -> None:
    print("Intelligent Wikipedia Research Bot -- interactive mode")
    print("Commands: search <q> | research <title> | find <keyword> | recent | stats | quit\n")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not raw:
            continue
        if raw.lower() in ("quit", "exit"):
            print("Goodbye.")
            break

        parts = raw.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        try:
            if command == "search" and arg:
                for i, r in enumerate(bot.search(arg), 1):
                    print(f"{i}. {r.title}")
            elif command == "research" and arg:
                article = bot.research_topic(arg)
                print(f"\n{article.title}\n{article.summary}\n")
            elif command == "find" and arg:
                for r in bot.find_stored(arg):
                    print(f"- {r.title}")
            elif command == "recent":
                for r in bot.recent():
                    print(f"- {r.title}")
            elif command == "stats":
                print(bot.stats())
            else:
                print("Unrecognized command. Try: search <q> | research <title> | find <keyword> | recent | stats | quit")
        except WikiBotError as exc:
            print(f"Error: {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Intelligent Wikipedia Research Bot")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search Wikipedia for a topic")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=config.DEFAULT_SEARCH_LIMIT)
    p_search.set_defaults(func=cmd_search)

    p_research = sub.add_parser("research", help="Fetch, process, and store an article")
    p_research.add_argument("title")
    p_research.add_argument("--full-text", action="store_true", help="Also fetch full article text")
    p_research.set_defaults(func=cmd_research)

    p_find = sub.add_parser("find", help="Search previously stored articles")
    p_find.add_argument("keyword")
    p_find.add_argument("--limit", type=int, default=20)
    p_find.set_defaults(func=cmd_find)

    p_recent = sub.add_parser("recent", help="List recently stored articles")
    p_recent.add_argument("--limit", type=int, default=10)
    p_recent.set_defaults(func=cmd_recent)

    p_stats = sub.add_parser("stats", help="Show storage statistics")
    p_stats.set_defaults(func=cmd_stats)

    p_interactive = sub.add_parser("interactive", help="Start an interactive session")
    p_interactive.set_defaults(func=cmd_interactive)

    return parser


def main() -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    bot = ResearchBot()

    try:
        args.func(bot, args)
        return 0
    except WikiBotError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - top-level safety net for the CLI
        logging.getLogger(__name__).exception("Unexpected error")
        print(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
