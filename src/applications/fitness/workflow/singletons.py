# -*- coding: utf-8 -*-
"""
单例管理模块（薄代理层）

所有组件实例由 framework.container.AppContainer 统一管理。
本模块保留原有 get_xxx() API，委托到 DI 容器，确保向后兼容。

版本: v2.0.0 — DI 容器重构
日期: 2026-02-23
"""

import logging

from src.framework.container import get_container, reset_container

logger = logging.getLogger(__name__)


# ============ Feature Flag（保留兼容，永远返回 True） ============

def _use_new_cache() -> bool:
    """历史遗留，旧缓存已移除，永远返回 True"""
    return True


# ============ 用户缓存 ============

def get_user_cache(backend_client=None, redis_client=None):
    """获取用户缓存单例（UserProfileCache）"""
    return get_container().get("user_cache", backend_client=backend_client, redis_client=redis_client)


# ============ 会员缓存 ============

def get_membership_cache(backend_client=None, redis_client=None):
    """获取会员权限缓存单例（MembershipCache）"""
    return get_container().get("membership_cache", backend_client=backend_client, redis_client=redis_client)


# ============ 性能优化组件初始化 ============

def initialize_performance_components():
    """
    初始化性能优化组件（CacheManager/ConnectionPool/LLM/Concurrency/Prometheus）

    通过 DI 容器懒加载，逐个触发初始化。
    """
    container = get_container()
    container.get("cache_manager")
    container.get("connection_pool_manager")
    container.get("llm_fallback_manager")
    container.get("concurrency_limiter")
    container.get("performance_monitor")
    logger.info("🎉 所有性能优化组件初始化完成 (via Container)")


# ============ 智能缓存管理器 ============

def get_cache_manager():
    """获取智能缓存管理器单例（CacheManager）"""
    return get_container().get("cache_manager")


# ============ 连接池管理器 ============

def get_connection_pool_manager():
    """获取连接池管理器单例（ConnectionPoolManager）"""
    return get_container().get("connection_pool_manager")


# ============ LLM降级管理器 ============

def get_llm_degradation_manager():
    """获取LLM降级管理器单例（LLMFallbackManager）"""
    return get_container().get("llm_fallback_manager")


# ============ 并发限流器 ============

def get_concurrency_limiter():
    """获取并发限流器单例（ConcurrencyLimiter）"""
    return get_container().get("concurrency_limiter")


# ============ 性能监控器 ============

def get_performance_monitor():
    """获取性能监控器单例（Prometheus 兼容）"""
    return get_container().get("performance_monitor")


# ============ Neo4j Cypher 直查执行器 ============

def get_cypher_executor():
    """获取 CypherQueryExecutor 单例"""
    return get_container().get("cypher_executor")


# ============ 混合检索引擎 ============

def get_hybrid_search_engine():
    """获取混合检索引擎单例（BM25 + 向量 + RRF）"""
    return get_container().get("hybrid_search_engine")


# ============ MCP工具注册表 ============

def get_mcp_tool_registry(neo4j_client=None, qdrant_client=None, three_layer_engine=None, backend_client=None):
    """获取MCP工具注册表单例"""
    return get_container().get(
        "mcp_tool_registry",
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        three_layer_engine=three_layer_engine,
        backend_client=backend_client,
    )


# ============ MCP编排器 ============

def get_mcp_orchestrator(neo4j_client=None, qdrant_client=None, three_layer_engine=None, backend_client=None):
    """获取MCP编排器单例"""
    return get_container().get(
        "mcp_orchestrator",
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        three_layer_engine=three_layer_engine,
        backend_client=backend_client,
    )


# ============ 重置函数（用于测试） ============

def reset_all_singletons():
    """重置所有单例实例（委托到 DI 容器）"""
    reset_container()
    logger.info("🔄 所有单例实例已重置 (via Container)")


# ============ 获取工作流缓存实例 ============

def get_workflow_caches():
    """获取工作流缓存实例（供预热系统使用）"""
    container = get_container()
    return {
        "user_cache": container._instances.get("user_cache"),
        "membership_cache": container._instances.get("membership_cache"),
    }


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
    # 混合检索引擎
    "get_hybrid_search_engine",
    # Neo4j Cypher 直查
    "get_cypher_executor",
    # MCP编排器和工具注册表
    "get_mcp_orchestrator",
    "get_mcp_tool_registry",
    # 初始化
    "initialize_performance_components",
    # 测试
    "reset_all_singletons",
]
