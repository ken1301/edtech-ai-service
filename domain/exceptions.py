class SessionExpiredError(Exception):
    """Raised when a session has expired."""
    pass


class LLMError(Exception):
    """Raised when the LLM fails to generate a response."""
    pass


class ProfileNotFoundError(Exception):
    """Raised when a student profile is not found."""
    pass
