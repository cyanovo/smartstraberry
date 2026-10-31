import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from yuxi.services.task_service import tasker
from yuxi.agents.mcp.service import ensure_builtin_mcp_servers_in_db
from yuxi.models.providers.service import ensure_builtin_model_providers_in_db
from yuxi.services.run_queue_service import close_queue_clients, get_redis_client
from yuxi.storage.postgres.manager import pg_manager
from yuxi.knowledge import knowledge_base
from yuxi.utils import logger
from yuxi.agents.backends.sandbox import init_sandbox_provider, shutdown_sandbox_provider
from yuxi.iot.mqtt_client import mqtt_client
from yuxi.services.iot_service import iot_service
from yuxi.services.detect_service import detect_service
from yuxi.repositories.detect_repository import detect_repository
from yuxi.services.vlm_service import vlm_service
from yuxi import get_version


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan事件管理器"""
    schema_mode = os.getenv("DATABASE_SCHEMA_MODE", "migrate").strip().lower()
    # 初始化数据库连接
    try:
        pg_manager.initialize()
        if schema_mode == "migrate":
            await pg_manager.create_tables()
            await pg_manager.ensure_business_schema()
            await pg_manager.ensure_knowledge_schema()
        elif schema_mode == "validate":
            await pg_manager.validate_classroom_schema()
        else:
            raise ValueError(f"不支持的 DATABASE_SCHEMA_MODE: {schema_mode}")
    except Exception as e:
        logger.error(f"Failed to initialize database during startup: {e}")
        if schema_mode == "validate" or os.getenv("CLASSROOM_MODE") == "true" or os.getenv("LOCAL_WINDOWS_MODE") == "true":
            raise

    # 确保内置 MCP 服务器定义存在于数据库
    try:
        await ensure_builtin_mcp_servers_in_db()
    except Exception as e:
        logger.error(f"Failed to ensure builtin MCP servers during startup: {e}")

    try:
        from yuxi.agents.skills.service import init_builtin_skills

        async with pg_manager.get_async_session_context() as session:
            await init_builtin_skills(session)
    except Exception as e:
        logger.error(f"Failed to initialize builtin skills during startup: {e}")

    try:
        from yuxi.repositories.agent_repository import AgentRepository

        async with pg_manager.get_async_session_context() as session:
            repository = AgentRepository(session)
            await repository.ensure_default_agent()
            await repository.ensure_strawberry_agent()
            await repository.ensure_general_purpose_subagent()
            await repository.ensure_web_search_subagent()
            await repository.ensure_deep_research_agents()
    except Exception as e:
        logger.error(f"Failed to ensure default agent during startup: {e}")

    # 初始化内置模型供应商配置
    try:
        async with pg_manager.get_async_session_context() as session:
            await ensure_builtin_model_providers_in_db(session)
    except Exception as e:
        logger.error(f"Failed to ensure builtin model providers during startup: {e}")

    # 初始化模型缓存（v2 模型选择使用）
    try:
        from yuxi.models.providers.cache import model_cache
        from yuxi.models.providers.service import get_all_model_providers

        async with pg_manager.get_async_session_context() as session:
            providers = await get_all_model_providers(session)
            model_cache.rebuild(providers)
    except Exception as e:
        logger.error(f"Failed to initialize model cache during startup: {e}")

    # 初始化知识库管理器
    if os.environ.get("LITE_MODE", "").lower() in ("true", "1"):
        logger.info("LITE_MODE enabled, skipping knowledge base initialization")
    else:
        try:
            await knowledge_base.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base manager: {e}")

    # 预热 Redis（run 队列）
    try:
        redis = await get_redis_client()
        await redis.ping()
    except Exception as e:
        logger.warning(f"Run queue redis unavailable on startup: {e}")

    if os.getenv("LOCAL_WINDOWS_MODE") != "true":
        try:
            init_sandbox_provider()
        except Exception as e:
            logger.error(f"Failed to initialize sandbox provider during startup: {e}")

    # History must be ready before MQTT starts delivering samples.
    from yuxi.repositories.sensor_history_repository import sensor_history_repository
    from yuxi.repositories.album_repository import album_repository

    await album_repository.initialize(validate=schema_mode == "validate")
    from yuxi.repositories.field_work_repository import field_repository
    from yuxi.services.field_work_service import capture_service

    await field_repository.initialize(validate=schema_mode == "validate")
    await field_repository.recover()

    if schema_mode == "migrate":
        await sensor_history_repository.initialize()

    # 初始化 MQTT 客户端（智能温室物联网）
    if mqtt_client.enabled:
        try:
            mqtt_client.register_air_handler(iot_service.on_air_data)
            mqtt_client.register_soil_handler(iot_service.on_soil_data)
            mqtt_client.register_state_handler(iot_service.on_state_data)
            mqtt_client.connect()
            logger.info("MQTT IoT client started")
        except Exception as e:
            logger.error(f"Failed to start MQTT client: {e}")
    else:
        logger.info("MQTT IoT client is disabled (set MQTT_ENABLED=true to enable)")

    # 初始化番茄成熟度检测服务
    try:
        await detect_repository.init_table()
        await detect_service.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize detect service: {e}")

    # 初始化大模型视觉识别服务
    try:
        vlm_service.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize VLM service: {e}")

    # =========================================================
    # 2. 核心修复：在这里执行一次 setup()，建完表就拉倒
    # =========================================================
    checkpointer = AsyncPostgresSaver(pg_manager.langgraph_pool)
    await checkpointer.setup()
    print("LangGraph Checkpoint tables verified/created!")

    await tasker.start()
    logger.info(f"""

░██     ░██                       ░██
 ░██   ░██
  ░██ ░██   ░██    ░██ ░██    ░██ ░██
   ░████    ░██    ░██  ░██  ░██  ░██
    ░██     ░██    ░██   ░█████   ░██
    ░██     ░██   ░███  ░██  ░██  ░██
    ░██      ░█████░██ ░██    ░██ ░██  v{get_version()}

    """)
    logger.info("Yuxi backend startup complete")
    yield

    # 关闭 MQTT 客户端
    await capture_service.shutdown()
    try:
        mqtt_client.disconnect()
    except Exception as e:
        logger.warning(f"Error during MQTT disconnect: {e}")

    await tasker.shutdown()
    shutdown_sandbox_provider()
    await close_queue_clients()
    await pg_manager.close()
