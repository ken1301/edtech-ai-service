class LLMError(Exception):
    """Raised when the LLM fails to generate a response."""
    pass

class AuthorizationError(Exception):
    """Raised when user authorization fails."""
    pass

class CompressSessionHistoryError(Exception):
    """Raised when session history compression fails."""
    pass

class SyncAndCloseSessionError(Exception):
    """Raised when syncing and closing session fails."""
    pass

class SessionExpiredError(Exception):
    """Raised when a session has expired and can no longer be used."""
    pass

class PromptGenerationError(Exception):
    """Raised when prompt generation fails."""
    pass

class SessionManagerError(Exception):
    """Raised when there is an error in session management."""
    pass

class ProfileManagerError(Exception):
    """Raised when there is an error in fetching student profile."""
    pass




