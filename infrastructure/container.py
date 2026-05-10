from dependency_injector import containers, providers

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient

from adapters.outbound.cache.redis_adapter import RedisSessionAdapter
from adapters.outbound.llm.factory import llm_factory
from adapters.outbound.persistence.mongo_profile_store import MongoProfileAdapter
from adapters.outbound.persistence.mongo_session_store import MongoSessionAdapter

from application.services.prompt_builder import PromptBuilder
from application.services.session_manager import SessionManager
from application.services.profile_manager import ProfileManager
from application.services.chat_service import ChatService
from application.stateless_services.learning_service import LearningService

from application.use_cases.chatbot_usecase import ChatbotUseCase
from infrastructure.config import Settings

class Container(containers.DeclarativeContainer):
    """Dependency injection container for managing application components and their dependencies"""

    wiring_config = containers.WiringConfiguration(modules=["adapters.inbound.rest.chat_router"])

    config = providers.Singleton(Settings)

    # Adapters
    redis_client = providers.Singleton(
        aioredis.from_url,
        url=config.provided.LOCAL_REDIS_URL,
        password=config.provided.REDIS_PASSWORD,
        decode_responses=True,
    )

    mongo_client = providers.Singleton(
        AsyncIOMotorClient,
        config.provided.LOCAL_MONGO_URL,
        username=config.provided.MONGO_USER,
        password=config.provided.MONGO_PASSWORD,
        port=config.provided.MONGO_PORT,
    )

    mongo_database = providers.Singleton(
        lambda client, db_name: client[db_name],
        client=mongo_client,
        db_name=config.provided.MONGO_DB_NAME,
    )

    llm_adapter = providers.Singleton(
        llm_factory,
        provider="groq",
        model_name="llama-3.3-70b-versatile",
        api_key=config.provided.GROQ_API_KEY,
    )

    cache_adapter = providers.Singleton(
        RedisSessionAdapter,
        redis_client=redis_client,
    )

    profile_store = providers.Singleton(
        MongoProfileAdapter,
        db=mongo_database,
    )

    session_store = providers.Singleton(
        MongoSessionAdapter,
        db=mongo_database,
    )

    # Sevices
    prompt_builder = providers.Singleton(
        PromptBuilder,
        profile_store=profile_store,
    )

    session_manager = providers.Singleton(
        SessionManager,
        redis_session_store=cache_adapter,
        mongo_session_store=session_store,
    )

    profile_manager = providers.Singleton(
        ProfileManager,
        profile_store=profile_store,
    )

    chat_service = providers.Singleton(
        ChatService,
        llm_port=llm_adapter,
    )

    learning_service = providers.Singleton(
        LearningService,
        chat_service=chat_service,
        session_manager=session_manager,
        prompt_builder=prompt_builder,
        profile_manager=profile_manager,
    )


    # Use Cases
    chatbot_use_case = providers.Singleton(
        ChatbotUseCase,
        chat_service=chat_service,
        session_manager=session_manager,
        prompt_builder=prompt_builder,
        learning_service=learning_service,
    )

    chatbot_manager = chatbot_use_case
    