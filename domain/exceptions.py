# === LLM-related exceptions ===
class LLMAdapterError(Exception):
    """Raised when the LLM fails to generate a response."""
    pass

class LLMManagerError(Exception):
    """Raised when there is an error in the LLMManager."""
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

# === Exercise-related exceptions ===
class ExerciseStoreError(Exception):
    """Raised when there is an error interacting with the exercise store."""
    pass

class ExerciseManagerError(Exception):
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

class ExerciseExtractionUseCaseError(Exception):
    """Raised when there is an error in the exercise selection use case."""
    pass