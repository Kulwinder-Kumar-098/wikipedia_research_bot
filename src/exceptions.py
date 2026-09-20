"""
Custom exception hierarchy for the Wikipedia Research Bot.

Keeping exceptions specific (rather than raising generic Exception / ValueError
everywhere) makes it possible for calling code -- and the CLI -- to catch and
respond to exactly the failure mode that occurred.
"""


class WikiBotError(Exception):
    """Base class for all errors raised by this application."""


class InvalidInputError(WikiBotError):
    """Raised when user-supplied input fails validation (empty, too long, etc.)."""


class PageNotFoundError(WikiBotError):
    """Raised when Wikipedia has no article matching the requested title."""


class DisambiguationError(WikiBotError):
    """Raised when a title matches a disambiguation page instead of an article."""

    def __init__(self, title: str, options: list):
        self.title = title
        self.options = options
        super().__init__(
            f"'{title}' is ambiguous. Did you mean one of: {', '.join(options[:5])}"
        )


class APIRequestError(WikiBotError):
    """Raised when a request to the Wikipedia API fails (network, timeout, HTTP status)."""


class RateLimitError(APIRequestError):
    """Raised when Wikipedia responds with a rate-limiting / throttling status."""


class DatabaseError(WikiBotError):
    """Raised when a SQL storage or retrieval operation fails."""
