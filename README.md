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
- **Retrieval-augmented answers**: ask questions against stored research;
  relevant SQL records are retrieved and passed to an OpenAI-compatible LLM
  with source citations and an instruction to avoid unsupported claims
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
│   ├── database.py           # SQLite / pgvector storage and retrieval
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

# Answer from stored research (requires LLM configuration)
python main.py ask "How does quantum computing use qubits?"

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

This project includes a Flask dashboard, Flask API, Neon PostgreSQL support,
and a `render.yaml` blueprint. In Render, create a new Blueprint from this
repository. Render will install the dependencies and start the service with
Gunicorn.

Open the service URL to use the dashboard. It lets you search Wikipedia,
research and save an article, and browse recently saved articles.

Available endpoints:

```text
GET  /health
GET  /search?q=quantum%20computing&limit=5
POST /research   JSON: {"title": "Alan Turing", "full_text": false}
GET  /articles/recent?limit=10
POST /ask   JSON: {"question": "How does quantum computing use qubits?"}
```

Set `DATABASE_URL` in Render to the Neon PostgreSQL connection string. When
that variable is present, saved articles, vectors, and search logs are stored in Neon.
Without it, local development falls back to SQLite at `data/research.db`.

### RAG and LLM configuration

The `/ask` endpoint embeds the question, retrieves nearest articles using
PostgreSQL `pgvector` cosine similarity, builds a bounded context, and sends it
to an OpenAI-compatible chat completions endpoint. Set:

```bash
LLM_API_KEY=your-key
LLM_BASE_URL=https://your-provider.example/v1
LLM_MODEL=gpt-5-mini

# Free local embeddings. The model downloads once and runs locally.
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
```

Groq is used for answer generation in `LLM_*`. The default embeddings model is
free and local, so no embedding API key is required. It downloads once on the
first research or reindex operation. Neon PostgreSQL automatically enables
`pgvector` and creates the vector index during startup. After upgrading an
existing database, run:

```bash
python main.py reindex-vectors
```

### Redeploy on Render

Commit and push the updated project to the GitHub repository connected to
Render. Render will install `sentence-transformers` during the build and
restart the web service automatically. Set these Render environment variables:

```text
DATABASE_URL       Neon PostgreSQL connection string
LLM_API_KEY        Groq API key
LLM_BASE_URL       https://api.groq.com/openai/v1
LLM_MODEL          openai/gpt-oss-120b
EMBEDDING_PROVIDER local
EMBEDDING_MODEL    sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS 384
```

After deployment, call `/health`, then run `python main.py reindex-vectors`
against the deployed database from a local environment with the same
`DATABASE_URL` and embedding settings. New articles are embedded automatically.

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
- **`article_embeddings`** — stores article vectors; Neon PostgreSQL uses
  `pgvector` and cosine nearest-neighbor search, while SQLite stores vectors
  for offline tests

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
