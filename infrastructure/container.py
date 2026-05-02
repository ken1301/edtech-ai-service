from dependency_injector import containers, providers

from infrastructure.config import Settings

from adapters.outbound.llm.factory import llm_factory
from adapters.outbound.cache.redis_adapter import RedisAdapter
from adapters.outbound.persistence.mongo_profile_store import MongoProfileStore
from adapters.outbound.persistence.mongo_session_store import MongoSessionStore

from application.services.chat_manager import SocraticChat
from application.services.learning_manager import LearningUseCase
from application.services.session_manager import SessionManager
from application.services.prompt_manager import PromptManager

from application.use_cases.chatbot_usecase import ChatbotManager


class Container(containers.DeclarativeContainer):
    config = providers.Singleton(Settings)

    # ------------------------------------------------------------------
    # LLM adapters
    # ------------------------------------------------------------------

    # Primary model — high quality (Llama 70B / GPT-4o-mini)
    llm_adapter = providers.Singleton(
        llm_factory,
        provider="groq",
        api_key=config.provided.GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
    )

    # Compression / summarisation model — cheap & fast (Llama 8B)
    compression_llm_adapter = providers.Singleton(
        llm_factory,
        provider="groq",
        api_key=config.provided.GROQ_API_KEY,
        model_name="llama-3.1-8b-instant",
    )

    # ------------------------------------------------------------------
    # Storage adapters
    # ------------------------------------------------------------------

    # Redis — hot session store (SessionStorePort + CachePort)
    cache_adapter = providers.Singleton(
        RedisAdapter,
        url=config.provided.LOCAL_REDIS_URL,
    )

    # MongoDB — student profile store
    profile_store = providers.Singleton(
        MongoProfileStore,
        url=config.provided.LOCAL_MONGO_URL,
        db_name=config.provided.MONGO_DB_NAME,
    )

    # MongoDB — durable session store (optional; used by LearningUseCase)
    session_store = providers.Singleton(
        MongoSessionStore,
        url=config.provided.LOCAL_MONGO_URL,
        db_name=config.provided.MONGO_DB_NAME,
    )

    # ------------------------------------------------------------------
    # Application services
    # ------------------------------------------------------------------

    session_manager = providers.Singleton(
        SessionManager,
        session_store=cache_adapter,  # Redis is the hot store
    )

    prompt_manager = providers.Singleton(
        PromptManager,
        profile_store=profile_store,
        session_store=cache_adapter,
    )

    # ------------------------------------------------------------------
    # Use cases
    # ------------------------------------------------------------------

    chat_use_case = providers.Singleton(
        SocraticChat,
        llm=llm_adapter,
        session_store=cache_adapter,
        session_manager=session_manager,
        compression_llm=compression_llm_adapter,
    )

    learning_use_case = providers.Singleton(
        LearningUseCase,
        llm=llm_adapter,
        profile_store=profile_store,
        session_store=cache_adapter,
        prompt_manager=prompt_manager,
    )

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    chatbot_manager = providers.Singleton(
        ChatbotManager,
        chat_use_case=chat_use_case,
        session_manager=session_manager,
        learning_use_case=learning_use_case,
        prompt_manager=prompt_manager,
    )
