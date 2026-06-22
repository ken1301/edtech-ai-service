from typing import ClassVar, Literal, Optional

from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_SUPPORTED_MODELS: ClassVar[set[str]] = {"gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4", "gpt-5.5"}

    JWT_SECRET: str 
    AI_SERVICE_API_KEY: str 

    # LLM Providers
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    STRONG_LLM_PROVIDER: Literal["openai", "groq"] = "openai"
    MID_LLM_PROVIDER: Literal["openai", "groq"] = "openai"
    WEAK_LLM_PROVIDER: Literal["openai", "groq"] = "openai"
    STRONG_LLM_MODEL: str = "gpt-5.4"
    MID_LLM_MODEL: str = "gpt-5.4-mini"
    WEAK_LLM_MODEL: str = "gpt-5.4-nano"
    
    # Redis
    LOCAL_REDIS_URL: str
    REDIS_PASSWORD: str
    REDIS_PORT: int

    # MongoDB
    MONGO_DB_NAME: str
    LOCAL_MONGO_URL: str
    MONGO_USER: str
    MONGO_PASSWORD: str
    MONGO_PORT: int

    # Cloud Storage
    MINIO_API_PORT: int
    MINIO_CONSOLE_PORT: int
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_ENDPOINT_URL: str
    REGION_NAME: str

    # NestJS Backend
    NESTJS_BACKEND_URL: str = "http://localhost:3000"

    # Expiration sweep worker
    SESSION_EXPIRATION_SWEEP_SECONDS: int = 30

    # LLM resilience
    LLM_REQUEST_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 1
    LLM_RETRY_BACKOFF_SECONDS: float = 0.1

    @model_validator(mode="after")
    def validate_llm_settings(self) -> "Settings":
        provider_models = [
            (self.STRONG_LLM_PROVIDER, self.STRONG_LLM_MODEL, "STRONG_LLM_MODEL"),
            (self.MID_LLM_PROVIDER, self.MID_LLM_MODEL, "MID_LLM_MODEL"),
            (self.WEAK_LLM_PROVIDER, self.WEAK_LLM_MODEL, "WEAK_LLM_MODEL"),
        ]

        configured_providers = {provider for provider, _, _ in provider_models}
        if "openai" in configured_providers and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when any configured LLM provider uses OpenAI")
        if "groq" in configured_providers and not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required when any configured LLM provider uses Groq")

        for provider, model_name, field_name in provider_models:
            if not model_name or not model_name.strip():
                raise ValueError(f"{field_name} must be a non-empty model name")
            if provider == "openai" and model_name not in self.OPENAI_SUPPORTED_MODELS:
                raise ValueError(
                    f"{field_name} must be one of: {', '.join(sorted(self.OPENAI_SUPPORTED_MODELS))}"
                )

        if self.LLM_REQUEST_TIMEOUT_SECONDS <= 0:
            raise ValueError("LLM_REQUEST_TIMEOUT_SECONDS must be greater than 0")
        if self.LLM_MAX_RETRIES < 0:
            raise ValueError("LLM_MAX_RETRIES must be greater than or equal to 0")
        if self.LLM_RETRY_BACKOFF_SECONDS < 0:
            raise ValueError("LLM_RETRY_BACKOFF_SECONDS must be greater than or equal to 0")

        return self

    model_config = ConfigDict(extra='ignore')

