# Intelligent Wikipedia Research Bot

A Python application for retrieving, processing, and organizing information
from Wikipedia. It searches Wikipedia, pulls structured article data via
Wikipedia's public APIs, cleans and summarizes the text, and stores
everything in a local SQL database for fast future search and retrieval.

**Stack:** Python · REST APIs (`requests`) · SQL (SQLite) · Automation (CLI)

---

## Features

- **Search** Wikipedia by keyword and get ranked results with snippets
- **Retrieve** structured article data (summary, categories, URL, word count)
  via Wikipedia's REST and Action APIs
- **Process** raw text: whitespace cleanup, extractive summarization,
  lightweight keyword extraction
- **Validate** all input (empty queries, oversized queries, non-string input)
  before it ever reaches the network layer
- **Handle errors gracefully**: missing pages, disambiguation pages, rate
  limiting, network timeouts, and database failures all raise specific,
  catchable exceptions instead of crashing the app
- **Store** results in SQLite with indexed columns and upsert-on-duplicate
  logic, plus a search log for query history
- **Search & retrieve stored data** with real SQL (`LIKE`-based full text
  search across titles/summaries, "recent articles" queries, etc.)
- **Two ways to use it**: a full CLI (`main.py`) and a plain importable
  Python module (`ResearchBot`) for use inside other programs

---

## Project structure

```
wikipedia_research_bot/
├── main.py                  # CLI entry point
├── config.py                 # Central configuration (env-var driven)
├── requirements.txt
├── .env.example               # Copy to .env to override defaults
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── api_client.py         # All HTTP calls to Wikipedia's APIs
│   ├── text_processor.py     # Validation, cleaning, summarization
│   ├── database.py           # SQLite schema, storage, SQL search
│   ├── models.py             # Shared dataclasses (Article, SearchResult, ...)
│   ├── research_bot.py       # High-level orchestrator (the main API)
│   └── exceptions.py         # Custom exception hierarchy
├── tests/
│   └── test_basic.py         # Unit tests (no network required)
├── examples/
│   └── usage_example.py      # Example of using ResearchBot as a library
└── data/                      # SQLite DB + logs live here (gitignored)
```

### Architecture

```
                 ┌───────────────┐
                 │     main.py    │   (CLI)
                 └───────┬───────┘
                         │
                 ┌───────▼────────┐
                 │  ResearchBot    │   orchestrates the whole pipeline
                 └───┬────────┬────┘
                     │        │
        ┌────────────▼──┐  ┌──▼─────────────┐
        │ WikipediaAPI   │  │ text_processor  │
        │ Client (HTTP)  │  │ (clean/summarize│
        └────────────────┘  │  /validate)     │
                             └────────┬────────┘
                                      │
                             ┌────────▼────────┐
                             │ ResearchDatabase │  (SQLite)
                             └─────────────────┘
```

Each layer only knows about the layer below it through plain Python
objects (`Article`, `SearchResult`) defined in `models.py` — the API client
never touches SQL, and the database never makes HTTP calls. This makes each
piece independently testable and easy to swap out (e.g. replacing SQLite
with Postgres only requires changes inside `database.py`).

---

## Setup

### 1. Requirements
- Python 3.9+

### 2. Install

```bash
git clone <your-repo-url>
cd wikipedia_research_bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. (Optional) configure
```bash
cp .env.example .env
# edit .env if you want to change defaults (language, timeouts, DB path...)
```
The app runs out of the box with sensible defaults even without a `.env`
file — see `config.py`.

---

## Usage

### CLI

```bash
# Search Wikipedia
python main.py search "quantum computing"

# Fetch, process, and store an article
python main.py research "Alan Turing"

# Fetch with the full article text (not just the lead summary)
python main.py research "Python (programming language)" --full-text

# Search articles you've already stored locally
python main.py find "machine learning"

# List recently stored articles
python main.py recent --limit 5

# Show storage stats
python main.py stats

# Interactive REPL mode
python main.py interactive
```

### As a library

```python
from src.research_bot import ResearchBot

bot = ResearchBot()

# Search
results = bot.search("neural networks", limit=5)

# Research + store a topic
article = bot.research_topic("Neural network")
print(article.summary)

# Research many topics, skipping any that fail
articles = bot.research_many(["Turing machine", "Alan Turing"])

# Query what's already stored
stored = bot.find_stored("turing")
recent = bot.recent(limit=10)
```

See `examples/usage_example.py` for a complete runnable example.

### Deploy as a web API on Render

This project includes a Flask API and a `render.yaml` blueprint. In Render,
create a new Blueprint from this repository. Render will install the
dependencies and start the service with Gunicorn.

Available endpoints:

```text
GET  /health
GET  /search?q=quantum%20computing&limit=5
POST /research   JSON: {"title": "Alan Turing", "full_text": false}
GET  /articles/recent?limit=10
```

The default SQLite database is stored on the service filesystem. Attach a
Render persistent disk and set `WIKIBOT_DATA_DIR=/var/data` for data that must
survive redeploys, or replace the SQLite layer with a hosted database.

---

## Error handling

All failure modes raise a specific subclass of `WikiBotError`
(`src/exceptions.py`), so calling code can handle them precisely:

| Exception               | Raised when                                          |
|--------------------------|-------------------------------------------------------|
| `InvalidInputError`      | Empty / non-string / oversized query                  |
| `PageNotFoundError`      | No Wikipedia article matches the title                |
| `DisambiguationError`    | Title matches a disambiguation page (lists options)   |
| `APIRequestError`        | Network failure or unexpected HTTP error               |
| `RateLimitError`         | Wikipedia responded with HTTP 429                       |
| `DatabaseError`          | A SQL operation failed                                  |

```python
from src.exceptions import DisambiguationError, PageNotFoundError, WikiBotError

try:
    article = bot.research_topic("Mercury")
except DisambiguationError as exc:
    print(f"Please pick one: {exc.options}")
except PageNotFoundError:
    print("No such article.")
except WikiBotError as exc:
    print(f"Something went wrong: {exc}")
```

---

## Testing

```bash
python -m pytest tests/ -v
```

Tests cover input validation, text processing, and the SQL storage layer.
They run entirely offline (no live Wikipedia calls), using a temporary
SQLite database per test.

---

## Data storage

Data is stored in a local SQLite database at `data/research.db` (path
configurable via `WIKIBOT_DB_PATH`). Schema:

- **`articles`** — `page_id`, `title`, `summary`, `url`, `categories`
  (JSON), `word_count`, `source`, `fetched_at`, unique per `(page_id, source)`
  with indexes on `title` and `fetched_at`
- **`search_log`** — records every search query and result count, for
  usage history/analytics

---

## Extending the project

- **Swap the database**: replace `src/database.py`'s connection logic to
  point at Postgres/MySQL — the SQL statements are portable.
- **Add sources beyond Wikipedia**: implement a new client with the same
  `search()` / `get_summary()` interface as `WikipediaAPIClient` and pass
  it into `ResearchBot(api_client=...)`.
- **Smarter summarization**: swap the extractive `summarize()` in
  `text_processor.py` for an LLM-based or NLP-library-based summarizer.
- **Schedule automated runs**: wrap `bot.research_many([...])` in a cron
  job or scheduler to keep a research database continuously updated.

---

## License

MIT — use freely, modify, and build on top of it.
