"""
Central configuration for the Wikipedia Research Bot.

All tunables live here so behaviour can be changed without touching
application logic. Values can be overridden with environment variables,
which keeps the project friendly to Docker / CI deployment.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Wikipedia API -----------------------------------------------------
WIKI_LANGUAGE = os.getenv("WIKI_LANGUAGE", "en")
WIKI_API_BASE = f"https://{WIKI_LANGUAGE}.wikipedia.org/w/api.php"
WIKI_REST_BASE = f"https://{WIKI_LANGUAGE}.wikipedia.org/api/rest_v1"

# A descriptive User-Agent is required by Wikimedia's API etiquette policy.
USER_AGENT = os.getenv(
    "WIKIBOT_USER_AGENT",
    "IntelligentWikipediaResearchBot/1.0 (https://example.com; contact@example.com)",
)

REQUEST_TIMEOUT = float(os.getenv("WIKIBOT_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("WIKIBOT_MAX_RETRIES", "3"))
RETRY_BACKOFF_SECONDS = float(os.getenv("WIKIBOT_RETRY_BACKOFF", "1.5"))

# --- Search / validation -------------------------------------------------
MAX_QUERY_LENGTH = int(os.getenv("WIKIBOT_MAX_QUERY_LENGTH", "300"))
DEFAULT_SEARCH_LIMIT = int(os.getenv("WIKIBOT_SEARCH_LIMIT", "10"))

# --- Storage ---------------------------------------------------------
DATA_DIR = os.getenv(
    "WIKIBOT_DATA_DIR", os.path.join(os.path.dirname(__file__), "data")
)
DATABASE_PATH = os.getenv(
    "WIKIBOT_DB_PATH", os.path.join(DATA_DIR, "research.db")
)
DATABASE_URL = os.getenv("DATABASE_URL")

# --- RAG / LLM --------------------------------------------------------
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("NEON_AI_GATEWAY_TOKEN")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("NEON_AI_GATEWAY_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5-mini")
RAG_MAX_SOURCES = int(os.getenv("RAG_MAX_SOURCES", "5"))
RAG_MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "12000"))
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))

# --- Logging -----------------------------------------------------------
LOG_LEVEL = os.getenv("WIKIBOT_LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("WIKIBOT_LOG_FILE", os.path.join(DATA_DIR, "wikibot.log"))
