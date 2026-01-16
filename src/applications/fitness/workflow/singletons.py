# -*- coding: utf-8 -*-
"""
单例管理模块

从 workflow_executor.py 提取的单例管理函数。
提供全局组件实例的获取和初始化。

版本: v1.0.0
日期: 2025-12-28

单例组件:
- UserProfileCache: 用户档案缓存
- MembershipCache: 会员权限缓存
- CacheManager: 通用/工作流缓存管理器（MCP模块）
- ConnectionPoolManager: 连接池管理器
- LLMFallbackManager: LLM降级管理器
- ConcurrencyLimiter: 并发限流器
- MetricsCollector: 指标收集器（兼容 get_performance_monitor）
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# ============ Feature Flag配置（保留兼容，旧缓存实现已移除） ============

def _use_new_cache() -> bool:
    """
    检查是否使用新缓存系统

    说明：历史上存在“旧 Intelligent*Cache / 新 UnifiedCache 系列”两套实现。
    当前代码库已移除旧实现，因此无论flag如何都使用新缓存体系。
    """
    return os.getenv("USE_NEW_CACHE", "true").lower() in ("true", "1", "yes")


# ============ 全局组件实例（单例模式） ============

_user_cache_instance = None
_membership_cache_instance = None
_workflow_monitor_instance = None

# 性能优化组件全局实例
_cache_manager_instance = None
_connection_pool_manager_instance = None
_llm_degradation_manager_instance = None
_concurrency_limiter_instance = None
_performance_monitor_instance = None

# MCP编排器全局实例
_mcp_orchestrator_instance = None


# ============ 用户缓存 ============

def get_user_cache(backend_client=None, redis_client=None):
    """
    获取用户缓存单例
    
    当前仅保留 UnifiedCache + UserProfileCache 实现（旧 IntelligentUserCache 已移除）。
    
    Args:
        backend_client: 后端客户端（首次调用时需要）
        redis_client: Redis客户端（可选）
        
    Returns:
        用户缓存实例（UserProfileCache）
    """
    global _user_cache_instance
    if _user_cache_instance is None:
        from ....framework.storage.user_profile_cache import UserProfileCache
        from ....framework.storage.unified_cache import UnifiedCache, CacheConfig

        if not _use_new_cache():
            logger.warning("USE_NEW_CACHE=false 但旧缓存实现已移除，将使用新缓存实现")

        cache_config = CacheConfig()
        unified_cache = UnifiedCache(redis_client=redis_client, config=cache_config)
        _user_cache_instance = UserProfileCache(
            unified_cache=unified_cache,
            db_client=backend_client,
        )
        logger.info("✅ UserProfileCache 初始化完成")

    # 允许后续注入backend_client（避免首次以None创建后无法回源）
    if backend_client is not None and hasattr(_user_cache_instance, "db_client"):
        if getattr(_user_cache_instance, "db_client") is None:
            _user_cache_instance.db_client = backend_client
    return _user_cache_instance


# ============ 会员缓存 ============

def get_membership_cache(backend_client=None, redis_client=None):
    """
    获取会员权限缓存单例
    
    当前仅保留 UnifiedCache + MembershipCache 实现（旧 IntelligentMembershipCache 已移除）。
    
    Args:
        backend_client: 后端客户端（首次调用时需要）
        redis_client: Redis客户端（可选）
        
    Returns:
        会员缓存实例（MembershipCache）
    """
    global _membership_cache_instance
    if _membership_cache_instance is None:
        from ....framework.storage.membership_cache import MembershipCache
        from ....framework.storage.unified_cache import UnifiedCache, CacheConfig

        if not _use_new_cache():
            logger.warning("USE_NEW_CACHE=false 但旧缓存实现已移除，将使用新缓存实现")

        cache_config = CacheConfig()
        unified_cache = UnifiedCache(redis_client=redis_client, config=cache_config)
        _membership_cache_instance = MembershipCache(
            unified_cache=unified_cache,
            backend_client=backend_client,
        )
        logger.info("✅ MembershipCache 初始化完成")

    # 允许后续注入backend_client（避免首次以None创建后无法回源）
    if backend_client is not None and hasattr(_membership_cache_instance, "backend_client"):
        if getattr(_membership_cache_instance, "backend_client") is None:
            _membership_cache_instance.backend_client = backend_client
    return _membership_cache_instance


# ============ 工作流监控器 ============
# daml_workflow_monitor.py已删除，未使用

# def get_workflow_monitor():
#     """获取工作流程监控器单例（已废弃）"""
#     pass


# ============ 性能优化组件初始化 ============

def initialize_performance_components():
    """
    初始化性能优化组件（单例模式）
    
    该函数初始化以下4个性能优化组件：
    1. CacheManager - 缓存管理器（基于 framework/mcp/cache_manager.py）
    2. ConnectionPoolManager - 连接池管理器
    3. LLMFallbackManager - LLM降级管理器
    4. ConcurrencyLimiter - 并发限流器
    
    所有组件使用单例模式，确保全局只有一个实例。
    """
    global _cache_manager_instance, _connection_pool_manager_instance
    global _llm_degradation_manager_instance, _concurrency_limiter_instance
    global _performance_monitor_instance
    
    # 1. 初始化缓存管理器（懒加载下游依赖，确保代码可运行）
    if _cache_manager_instance is None:
        _cache_manager_instance = get_cache_manager()
        logger.info("✅ CacheManager初始化完成")
    
    # 2. 初始化连接池管理器
    if _connection_pool_manager_instance is None:
        from ....framework.storage.connection_pool_manager import (
            ConnectionPoolManager,
            PoolConfig
        )
        
        # MySQL连接池配置
        mysql_config = PoolConfig(
            min_size=10,
            max_size=50,
            max_idle_time=60,
            max_lifetime=3600,
            acquire_timeout=2,
            health_check_interval=30
        )
        
        mysql_db_config = {
            'host': os.getenv('MYSQL_HOST', 'fitness_mysql'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'root_password_2025'),
            'database': os.getenv('MYSQL_DATABASE', 'fitness_app')
        }
        
        # Neo4j连接池配置
        neo4j_config = PoolConfig(
            min_size=5,
            max_size=20,
            max_idle_time=120,
            max_lifetime=3600,
            acquire_timeout=2,
            health_check_interval=30
        )
        
        neo4j_db_config = {
            'uri': os.getenv('NEO4J_URI', 'bolt://fitness_neo4j:7687'),
            'user': os.getenv('NEO4J_USER', 'neo4j'),
            'password': os.getenv('NEO4J_PASSWORD', '')
        }
        
        _connection_pool_manager_instance = ConnectionPoolManager(
            mysql_config=mysql_config,
            neo4j_config=neo4j_config,
            mysql_db_config=mysql_db_config,
            neo4j_db_config=neo4j_db_config
        )
        logger.info("✅ ConnectionPoolManager初始化完成（MySQL + Neo4j连接池）")
    
    # 3. 初始化LLM降级管理器
    if _llm_degradation_manager_instance is None:
        from ....framework.clients.llm_fallback_manager import LLMFallbackManager
        _llm_degradation_manager_instance = LLMFallbackManager(
            primary_backend="deepseek",
            fallback_backends=["ollama", "template"],
            max_retries=3,
            timeout=30,
            enable_health_check=True
        )
        logger.info("✅ LLMFallbackManager初始化完成")
    
    # 4. 初始化并发限流器
    if _concurrency_limiter_instance is None:
        from ....framework.monitoring.concurrency_limiter import ConcurrencyLimiter
        _concurrency_limiter_instance = ConcurrencyLimiter()
        logger.info("✅ ConcurrencyLimiter初始化完成")
    
    # 5. 兼容：performance_monitor 已删除，保留 get_performance_monitor() 作为 MetricsCollector 别名
    if _performance_monitor_instance is None:
        from ....framework.monitoring.metrics_collector import get_metrics_collector
        _performance_monitor_instance = get_metrics_collector()
        logger.info("✅ MetricsCollector初始化完成（兼容 get_performance_monitor）")
    
    logger.info("🎉 所有性能优化组件初始化完成")


# ============ 智能缓存管理器 ============

def get_cache_manager():
    """
    获取智能缓存管理器单例
    
    Returns:
        CacheManager 实例
    """
    global _cache_manager_instance
    if _cache_manager_instance is None:
        from ....framework.mcp.cache_manager import CacheManager

        try:
            from ..clients.backend_client import BackendClient
            backend_client = BackendClient()
        except Exception:
            backend_client = None

        user_cache = get_user_cache(backend_client=backend_client)
        membership_cache = get_membership_cache(backend_client=backend_client)

        _cache_manager_instance = CacheManager(
            user_cache=user_cache,
            membership_cache=membership_cache,
            user_profile_ttl=300,
            membership_ttl=600,
        )
    return _cache_manager_instance


# ============ 连接池管理器 ============

def get_connection_pool_manager():
    """
    获取连接池管理器单例
    
    Returns:
        ConnectionPoolManager 实例
    """
    global _connection_pool_manager_instance
    if _connection_pool_manager_instance is None:
        initialize_performance_components()
    return _connection_pool_manager_instance


# ============ LLM降级管理器 ============

def get_llm_degradation_manager():
    """
    获取LLM降级管理器单例
    
    Returns:
        LLMFallbackManager 实例
    """
    global _llm_degradation_manager_instance
    if _llm_degradation_manager_instance is None:
        initialize_performance_components()
    return _llm_degradation_manager_instance


# ============ 并发限流器 ============

def get_concurrency_limiter():
    """
    获取并发限流器单例
    
    Returns:
        ConcurrencyLimiter 实例
    """
    global _concurrency_limiter_instance
    if _concurrency_limiter_instance is None:
        initialize_performance_components()
    return _concurrency_limiter_instance


# ============ 性能监控器 ============

def get_performance_monitor():
    """
    获取性能监控器单例
    
    Returns:
        MetricsCollector 实例（兼容旧命名）
    """
    global _performance_monitor_instance
    if _performance_monitor_instance is None:
        initialize_performance_components()
    return _performance_monitor_instance


# ============ 重置函数（用于测试） ============

def reset_all_singletons():
    """
    重置所有单例实例（仅用于测试）
    """
    global _user_cache_instance, _membership_cache_instance
    global _workflow_monitor_instance
    global _cache_manager_instance, _connection_pool_manager_instance
    global _llm_degradation_manager_instance, _concurrency_limiter_instance
    global _performance_monitor_instance, _mcp_orchestrator_instance
    global _mcp_tool_registry_instance
    
    _user_cache_instance = None
    _membership_cache_instance = None
    _workflow_monitor_instance = None
    _cache_manager_instance = None
    _connection_pool_manager_instance = None
    _llm_degradation_manager_instance = None
    _concurrency_limiter_instance = None
    _performance_monitor_instance = None
    _mcp_orchestrator_instance = None
    _mcp_tool_registry_instance = None
    
    logger.info("🔄 所有单例实例已重置")


# ============ 获取工作流缓存实例（供预热系统使用） ============

def get_workflow_caches():
    """
    获取工作流缓存实例（供预热系统使用）
    
    Returns:
        Dict[str, Any]: 包含 user_cache 和 membership_cache 的字典
    """
    global _user_cache_instance, _membership_cache_instance
    
    return {
        "user_cache": _user_cache_instance,
        "membership_cache": _membership_cache_instance
    }


# ============ MCP工具注册表 ============

_mcp_tool_registry_instance = None


def get_mcp_tool_registry(neo4j_client=None, qdrant_client=None, three_layer_engine=None, backend_client=None):
    """
    获取MCP工具注册表单例
    
    注册17个Python内置MCP工具，供MCPOrchestrator调用。
    
    Args:
        neo4j_client: Neo4j客户端实例（可选，会自动创建）
        qdrant_client: Qdrant客户端实例（可选，会自动创建）
        three_layer_engine: 三层检索引擎实例（可选，会自动创建）
        backend_client: 后端客户端实例（可选）
        
    Returns:
        MCPToolRegistry 实例
    """
    global _mcp_tool_registry_instance
    if _mcp_tool_registry_instance is None:
        try:
            from ..mcp_tools import MCPToolRegistry, initialize_all_tools
            
            # 如果没有传入客户端，自动创建
            if neo4j_client is None:
                try:
                    from ....framework.clients.neo4j_client import Neo4jClient
                    import asyncio
                    neo4j_client = Neo4jClient()
                    # Neo4jClient需要调用connect()方法才能使用
                    # 使用asyncio.get_event_loop()来运行异步connect方法
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环已经在运行，创建一个任务
                        asyncio.create_task(neo4j_client.connect())
                        logger.info("✅ Neo4jClient自动创建成功（异步连接中）")
                    else:
                        # 如果事件循环未运行，同步执行
                        loop.run_until_complete(neo4j_client.connect())
                        logger.info("✅ Neo4jClient自动创建并连接成功")
                except Exception as e:
                    logger.warning(f"⚠️ Neo4jClient创建失败: {e}")
            
            if qdrant_client is None:
                try:
                    from src.framework.clients.qdrant_client import create_qdrant_client
                    import os
                    qdrant_host = os.getenv('QDRANT_HOST', 'fitness_qdrant')
                    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
                    # 使用优化的客户端，自动从环境变量读取 QDRANT_PREFER_GRPC
                    qdrant_client = create_qdrant_client(host=qdrant_host, port=qdrant_port)
                    logger.info(f"✅ QdrantClient自动创建成功 ({qdrant_host}:{qdrant_port})")
                except Exception as e:
                    logger.warning(f"⚠️ QdrantClient创建失败: {e}")
            
            # 如果没有传入三层检索引擎，自动创建
            if three_layer_engine is None:
                try:
                    from ....framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine
                    three_layer_engine = TrueThreeLayerEngine(
                        enable_neo4j_direct=True,
                        enable_parallel_execution=False
                    )
                    logger.info("✅ TrueThreeLayerEngine自动创建成功")
                except Exception as e:
                    logger.warning(f"⚠️ TrueThreeLayerEngine创建失败: {e}")
            
            # 创建工具注册表
            _mcp_tool_registry_instance = MCPToolRegistry()
            
            # 初始化并注册所有17个Python MCP工具
            initialize_all_tools(
                registry=_mcp_tool_registry_instance,
                neo4j_client=neo4j_client,
                qdrant_client=qdrant_client,
                three_layer_engine=three_layer_engine,
                backend_client=backend_client,
                vector_store=None
            )
            
            logger.info(f"✅ MCPToolRegistry初始化完成，已注册 {_mcp_tool_registry_instance.get_tool_count()} 个工具")
        except Exception as e:
            logger.error(f"❌ MCPToolRegistry初始化失败: {e}")
            import traceback
            traceback.print_exc()
            _mcp_tool_registry_instance = None
    return _mcp_tool_registry_instance


# ============ MCP编排器 ============

def get_mcp_orchestrator(neo4j_client=None, qdrant_client=None, three_layer_engine=None, backend_client=None):
    """
    获取MCP编排器单例
    
    MCP编排器负责调用15个Python内置MCP工具。
    
    Args:
        neo4j_client: Neo4j客户端实例（首次调用时需要）
        qdrant_client: Qdrant客户端实例（首次调用时需要）
        three_layer_engine: 三层检索引擎实例（首次调用时需要）
        backend_client: 后端客户端实例（首次调用时需要）
    
    Returns:
        MCPOrchestrator 实例
    """
    global _mcp_orchestrator_instance
    if _mcp_orchestrator_instance is None:
        try:
            from ....framework.orchestration.mcp_orchestrator import MCPOrchestrator
            from ....framework.storage.metadata_database import MetadataDB
            from ....framework.clients.mcp_client_v2 import ConfigurableMCPClient
            
            # 初始化MetadataDB（用于缓存）
            import os
            db_path = os.getenv('MCP_METADATA_DB_PATH', '/tmp/mcp_metadata.db')
            metadata_db = MetadataDB(db_path=db_path)
            
            # MCP客户端设置为None，直接使用本地工具注册表
            # 原因：17个Python内置工具都通过tool_registry本地调用，无需stdio MCP客户端
            # 这样可以避免"客户端未连接"的错误日志
            mcp_client = None
            logger.info("✅ 使用本地工具注册表模式（跳过stdio MCP客户端）")
            
            # 初始化MCP工具注册表（关键！）
            tool_registry = get_mcp_tool_registry(
                neo4j_client=neo4j_client,
                qdrant_client=qdrant_client,
                three_layer_engine=three_layer_engine,
                backend_client=backend_client
            )
            
            # 初始化MCP编排器（传递tool_registry）
            _mcp_orchestrator_instance = MCPOrchestrator(
                metadata_db=metadata_db,
                mcp_client_pool=mcp_client,
                cache_ttl=300,
                max_parallel=5,
                tool_registry=tool_registry  # 关键：传递工具注册表
            )
            logger.info("✅ MCPOrchestrator初始化完成（已注入tool_registry）")
        except Exception as e:
            logger.error(f"❌ MCPOrchestrator初始化失败: {e}")
            import traceback
            traceback.print_exc()
            _mcp_orchestrator_instance = None
    return _mcp_orchestrator_instance


# ============ 导出 ============

__all__ = [
    # 缓存相关
    "get_user_cache",
    "get_membership_cache",
    "get_cache_manager",
    "get_workflow_caches",
    # 监控相关
    "get_performance_monitor",
    # 连接池和降级
    "get_connection_pool_manager",
    "get_llm_degradation_manager",
    "get_concurrency_limiter",
    # MCP编排器和工具注册表
    "get_mcp_orchestrator",
    "get_mcp_tool_registry",
    # 初始化
    "initialize_performance_components",
    # 测试
    "reset_all_singletons",
]
