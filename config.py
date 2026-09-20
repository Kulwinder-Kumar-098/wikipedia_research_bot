"""
Central configuration for the Wikipedia Research Bot.

All tunables live here so behaviour can be changed without touching
application logic. Values can be overridden with environment variables,
which keeps the project friendly to Docker / CI deployment.
"""

import os

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

# --- Logging -----------------------------------------------------------
LOG_LEVEL = os.getenv("WIKIBOT_LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("WIKIBOT_LOG_FILE", os.path.join(DATA_DIR, "wikibot.log"))
