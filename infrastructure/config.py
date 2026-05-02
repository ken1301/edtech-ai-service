from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # LLM Providers
    GROQ_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None
    
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
    
    # NestJS Backend
    NESTJS_BACKEND_URL: str = "http://localhost:3000"

    model_config = ConfigDict(extra='ignore')

