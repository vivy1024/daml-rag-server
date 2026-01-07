# -*- coding: utf-8 -*-
"""
性能优化组件初始化测试

测试任务7：初始化性能优化组件

版本：v1.0.0
创建日期：2025-12-21
"""

import pytest
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_initialize_performance_components():
    """测试性能优化组件初始化"""
    from src.applications.fitness.workflow_executor import initialize_performance_components
    
    # 调用初始化函数
    initialize_performance_components()
    
    logger.info("✅ 性能优化组件初始化测试通过")


def test_get_cache_manager():
    """测试获取智能缓存管理器"""
    from src.applications.fitness.workflow_executor import get_cache_manager
    
    cache_manager = get_cache_manager()
    
    assert cache_manager is not None
    assert hasattr(cache_manager, 'get')
    assert hasattr(cache_manager, 'put')
    assert hasattr(cache_manager, 'get_stats')
    
    logger.info("✅ 智能缓存管理器获取测试通过")


def test_get_connection_pool_manager():
    """测试获取连接池管理器"""
    from src.applications.fitness.workflow_executor import get_connection_pool_manager
    
    pool_manager = get_connection_pool_manager()
    
    assert pool_manager is not None
    assert hasattr(pool_manager, 'get_mysql_connection')
    assert hasattr(pool_manager, 'get_neo4j_session')
    
    logger.info("✅ 连接池管理器获取测试通过")


def test_get_llm_degradation_manager():
    """测试获取LLM降级管理器"""
    from src.applications.fitness.workflow_executor import get_llm_degradation_manager
    
    degradation_manager = get_llm_degradation_manager()
    
    assert degradation_manager is not None
    assert hasattr(degradation_manager, 'call_with_fallback')
    
    logger.info("✅ LLM降级管理器获取测试通过")


def test_get_concurrency_limiter():
    """测试获取并发限流器"""
    from src.applications.fitness.workflow_executor import get_concurrency_limiter
    
    limiter = get_concurrency_limiter()
    
    assert limiter is not None
    assert hasattr(limiter, 'acquire')
    assert hasattr(limiter, 'release')
    
    logger.info("✅ 并发限流器获取测试通过")


def test_singleton_pattern():
    """测试单例模式"""
    from src.applications.fitness.workflow_executor import (
        get_cache_manager,
        get_connection_pool_manager,
        get_llm_degradation_manager,
        get_concurrency_limiter
    )
    
    # 获取两次实例，应该是同一个对象
    cache_manager_1 = get_cache_manager()
    cache_manager_2 = get_cache_manager()
    assert cache_manager_1 is cache_manager_2
    
    pool_manager_1 = get_connection_pool_manager()
    pool_manager_2 = get_connection_pool_manager()
    assert pool_manager_1 is pool_manager_2
    
    degradation_manager_1 = get_llm_degradation_manager()
    degradation_manager_2 = get_llm_degradation_manager()
    assert degradation_manager_1 is degradation_manager_2
    
    limiter_1 = get_concurrency_limiter()
    limiter_2 = get_concurrency_limiter()
    assert limiter_1 is limiter_2
    
    logger.info("✅ 单例模式测试通过")


def test_workflow_initialization():
    """测试工作流中的组件初始化"""
    from src.applications.fitness.workflow_executor import initialize_performance_components
    from src.applications.fitness.workflow_executor import (
        get_cache_manager,
        get_connection_pool_manager,
        get_llm_degradation_manager,
        get_concurrency_limiter
    )
    
    # 初始化组件
    initialize_performance_components()
    
    # 验证所有组件都已初始化
    cache_manager = get_cache_manager()
    pool_manager = get_connection_pool_manager()
    degradation_manager = get_llm_degradation_manager()
    limiter = get_concurrency_limiter()
    
    assert cache_manager is not None
    assert pool_manager is not None
    assert degradation_manager is not None
    assert limiter is not None
    
    logger.info("✅ 工作流组件初始化测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
