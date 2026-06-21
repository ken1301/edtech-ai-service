from dependency_injector import containers, providers

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
import boto3

from adapters.outbound.cache.redis_lesson_adapter import RedisLessonAdapter
from adapters.outbound.cache.redis_session_adapter import RedisSessionAdapter
from adapters.outbound.llm.factory import llm_factory
from adapters.outbound.persistence.mongo_profile_store import MongoProfileAdapter
from adapters.outbound.persistence.mongo_session_store import MongoSessionAdapter
from adapters.outbound.persistence.mongo_exercise_store import MongoExerciseAdapter
from adapters.outbound.docs_storage.s3_adapter import S3Adapter

from application.services.lesson_manager import LessonManager
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService
from application.stateless_services.docs_transform import PDFToMarkdownTransformer
from application.stateless_services.prompt_builder import PromptBuilder
from application.services.cloud_manager import CloudManager
from application.services.session_manager import SessionManager
from application.services.profile_manager import ProfileManager
from application.stateless_services.llm_manager import LLMManager
from application.stateless_services.learning_service import LearningService

from application.stateless_services.lesson2_service.layers.classify_layer import ClassifyLayer
from application.stateless_services.lesson2_service.layers.ground_layer import GroundLayer
from application.stateless_services.lesson2_service.layers.evaluate_layer import EvaluateLayer
from application.stateless_services.lesson2_service.layers.decide_layer import DecideLayer
from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer
from application.stateless_services.lesson2_service.fast_path_reply import FastPathReply
from application.stateless_services.lesson2_service.safety_divert import SafetyDivert
from application.stateless_services.lesson2_service.full_pipeline import FullPipeline
from application.stateless_services.lesson2_service.orchestration import Lesson2Orchestration

from application.use_cases.chatbot_usecase import ChatbotUseCase
from application.use_cases.create_lesson_usecase import CreateLessonUseCase
from infrastructure.config import Settings

class Container(containers.DeclarativeContainer):
    """Dependency injection container for managing application components and their dependencies"""

    wiring_config = containers.WiringConfiguration(modules=["adapters.inbound.rest.lesson2_router", "adapters.inbound.rest.create_lesson_router"])

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
        authSource="admin",
    )

    s3_client = providers.Singleton(
        boto3.client,
        "s3",
        endpoint_url=config.provided.MINIO_ENDPOINT_URL,
        aws_access_key_id=config.provided.MINIO_ROOT_USER,
        aws_secret_access_key=config.provided.MINIO_ROOT_PASSWORD,
        region_name=config.provided.REGION_NAME,
    )

    mongo_database = providers.Singleton(
        lambda client, db_name: client[db_name],
        client=mongo_client,
        db_name=config.provided.MONGO_DB_NAME,
    )

    strong_llm_adapter = providers.Singleton(
        llm_factory,
        provider="openai",
        model_name="gpt-5.4",
        api_key=config.provided.OPENAI_API_KEY,
    )

    mid_llm_adapter = providers.Singleton(
        llm_factory,
        provider="openai",
        model_name="gpt-5.4-mini",
        api_key=config.provided.OPENAI_API_KEY,
    )

    weak_llm_adapter = providers.Singleton(
        llm_factory,
        provider="openai",
        model_name="gpt-5.4-nano",
        api_key=config.provided.OPENAI_API_KEY,
    )
    
    cache_adapter = providers.Singleton(
        RedisSessionAdapter,
        redis_client=redis_client,
    )

    lesson_creation_metadata_store = providers.Singleton(
        RedisLessonAdapter,
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

    exercise_store = providers.Singleton(
        MongoExerciseAdapter,
        db=mongo_database,
    )

    s3_adapter = providers.Singleton(
        S3Adapter,
        s3_client=s3_client,
    )

    cloud_manager = providers.Singleton(
        CloudManager,
        cloud_port=s3_adapter,
    )

    # Services
    prompt_builder = providers.Singleton(
        PromptBuilder,
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

    lesson_manager = providers.Singleton(
        LessonManager,
        exercise_store_port=exercise_store,
        lesson_creation_store_port=lesson_creation_metadata_store,
    )

    strong_llm_manager = providers.Singleton(
        LLMManager,
        llm_port=strong_llm_adapter,
    )

    mid_llm_manager = providers.Singleton(
        LLMManager,
        llm_port=mid_llm_adapter,
    )

    weak_llm_manager = providers.Singleton(
        LLMManager,
        llm_port=weak_llm_adapter,
    )

    adaptive_learning_service = providers.Singleton(
        AdaptiveLearningService,
    )

    learning_service = providers.Singleton(
        LearningService,
        llm_manager=mid_llm_manager,
        session_manager=session_manager,
        prompt_builder=prompt_builder,
        profile_manager=profile_manager,
        adaptive_learning_service=adaptive_learning_service,
    )

    docs_transformer = providers.Singleton(
        PDFToMarkdownTransformer,
    )

    # Lesson 2 Specific Services
    classify_layer = providers.Singleton(
        ClassifyLayer,
        llm_manager=weak_llm_manager,
        prompt_builder=prompt_builder,
    )

    ground_layer = providers.Singleton(
        GroundLayer,
        llm_manager=mid_llm_manager,
        prompt_builder=prompt_builder,
    )

    evaluate_layer = providers.Singleton(
        EvaluateLayer,
        llm_manager=strong_llm_manager,
        prompt_builder=prompt_builder,
    )

    decide_layer = providers.Singleton(
        DecideLayer,
        llm_manager=mid_llm_manager,
        prompt_builder=prompt_builder,
    )

    response_layer = providers.Singleton(
        ResponseLayer,
        llm_manager=weak_llm_manager,
        prompt_builder=prompt_builder,
    )

    state_writer_layer = providers.Singleton(
        StateWriterLayer,
    )

    fast_path_reply = providers.Singleton(
        FastPathReply,
        response_layer=response_layer,
        state_writer_layer=state_writer_layer,
    )

    safety_divert = providers.Singleton(
        SafetyDivert,
        response_layer=response_layer,
        state_writer_layer=state_writer_layer,
    )

    full_pipeline = providers.Singleton(
        FullPipeline,
        evaluate_layer=evaluate_layer,
        decide_layer=decide_layer,
        response_layer=response_layer,
        state_writer_layer=state_writer_layer,
    )

    lesson2_orchestration = providers.Singleton(
        Lesson2Orchestration,
        classify_layer=classify_layer,
        ground_layer=ground_layer,
        full_pipeline=full_pipeline,
        fast_path_reply=fast_path_reply,
        safety_divert=safety_divert,
    )

    # Use Cases
    chatbot_manager = providers.Singleton(
        ChatbotUseCase,
        session_manager=session_manager,
        learning_service=learning_service,
        orchestration=lesson2_orchestration,
    )

    lesson_creation_manager = providers.Singleton(
        CreateLessonUseCase,
        llm_manager=strong_llm_manager,
        cloud_manager=cloud_manager,
        lesson_manager=lesson_manager,
        prompt_builder=prompt_builder,
        pdf_to_markdown_transformer=docs_transformer,
    )
