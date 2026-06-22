# === LLM-related exceptions ===
class LLMAdapterError(Exception):
    """Raised when the LLM fails to generate a response."""
    pass

class LLMRateLimitError(LLMAdapterError):
    """Raised when the provider rate-limits the request."""
    pass

class LLMAuthenticationError(LLMAdapterError):
    """Raised when the provider credentials or auth configuration are invalid."""
    pass

class LLMConfigurationError(LLMAdapterError):
    """Raised when the configured provider/model/request shape is invalid."""
    pass

class LLMStructuredOutputError(LLMAdapterError):
    """Raised when structured-output generation or validation fails."""
    pass

class LLMProviderError(LLMAdapterError):
    """Raised when the upstream provider returns an operational failure."""
    pass

class LLMManagerError(Exception):
    """Raised when there is an error in the LLMManager."""
    pass

class LLMManagerTimeoutError(LLMManagerError):
    """Raised when all LLM attempts time out."""
    pass

class LLMManagerRateLimitError(LLMManagerError):
    """Raised when all LLM attempts are rate-limited."""
    pass

class LLMManagerAuthenticationError(LLMManagerError):
    """Raised when all LLM attempts fail authentication."""
    pass

class LLMManagerConfigurationError(LLMManagerError):
    """Raised when LLM configuration or request construction is invalid."""
    pass

class LLMManagerStructuredOutputError(LLMManagerError):
    """Raised when all LLM structured-output attempts fail."""
    pass

class LLMManagerProviderError(LLMManagerError):
    """Raised when all LLM attempts fail due to provider-side operational errors."""
    pass

# === Session-related exceptions ===
class SessionStoreError(Exception):
    """Raised when there is an error interacting with the session store."""
    pass

class SessionManagerError(Exception):
    """Raised when there is an error in session management."""
    pass

# === Profile-related exceptions ===
class ProfileStoreError(Exception):
    """Raised when there is an error interacting with the profile store."""
    pass

class ProfileManagerError(Exception):
    """Raised when there is an error in fetching student profile."""
    pass

# === Cloud-related exceptions ===
class CloudAdapterError(Exception):
    """Raised when there is an error processing documents with the cloud adapter."""
    pass

class CloudManagerError(Exception):
    """Raised when there is an error in cloud management operations."""
    pass

# === Lesson 2 specific exceptions ===
class Lesson2OrchestrationError(Exception):
    """Raised when there is an error in the orchestration of the lesson 2 service."""
    pass

class Lesson2PipelineError(Exception):
    """Raised when there is an error in the overall pipeline of the lesson 2 service."""
    pass

class Lesson2LayerError(Exception):
    """Raised when there is an error in one of the layers of the lesson 2 service."""
    pass


class Lesson2ValidationError(Exception):
    """Raised when a lesson 2 request is semantically invalid."""
    pass


class Lesson2SessionConflictError(Exception):
    """Raised when lesson 2 session state cannot accept the requested action."""
    pass


class SessionNotFoundError(Exception):
    """Raised when a requested lesson 2 session does not exist."""
    pass


class SessionClosedError(Exception):
    """Raised when a requested lesson 2 session is closed or expired."""
    pass


class SessionClosingError(Exception):
    """Raised when a requested lesson 2 session is already closing."""
    pass

# === Exercise-related exceptions ===
class LessonStoreError(Exception):
    """Raised when there is an error interacting with the exercise store."""
    pass

class LessonManagerError(Exception):
    """Raised when there is an error in exercise management operations."""
    pass    

# === Other activity-specific exceptions ===
class AuthorizationError(Exception):
    """Raised when user authorization fails."""
    pass

class ProblemSelectionAnalysisError(Exception):
    """Raised when there is an error analyzing the problem for exercise selection."""
    pass

class UpdateStudentProfileError(Exception):
    """Raised when there is an error updating the student profile."""
    pass

class CompressSessionHistoryError(Exception):
    """Raised when session history compression fails."""
    pass

class SyncAndCloseSessionError(Exception):
    """Raised when syncing and closing session fails."""
    pass

class PromptGenerationError(Exception):
    """Raised when prompt generation fails."""
    pass

class DocumentTransformationError(Exception):
    """Raised when transforming PDF to Markdown fails."""
    pass

# === Use case specific exceptions ===
class ChatBotUseCaseError(Exception):
    """Raised when there is an error in the chatbot use case."""
    pass

class CreateLessonUseCaseError(Exception):
    """Raised when there is an error in the exercise selection use case."""
    pass