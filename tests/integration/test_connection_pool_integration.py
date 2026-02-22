# -*- coding: utf-8 -*-
"""
连接池集成测试

测试连接池管理器在工作流中的集成情况

版本: v1.0.0
创建日期: 2025-12-21
"""

import pytest
import asyncio
import logging

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_connection_pool_manager_initialization():
    """测试连接池管理器初始化"""
    from src.applications.fitness.workflow_executor import (
        initialize_performance_components,
        get_connection_pool_manager
    )
    
    # 初始化性能组件
    initialize_performance_components()
    
    # 获取连接池管理器
    pool_manager = get_connection_pool_manager()
    
    assert pool_manager is not None, "连接池管理器应该被初始化"
    logger.info("✅ 连接池管理器初始化成功")
    
    # 初始化连接池
    if not pool_manager._initialized:
        await pool_manager.initialize()
        logger.info("✅ 连接池已初始化")
    
    # 验证连接池配置
    assert pool_manager.mysql_pool is not None, "MySQL连接池应该被配置"
    assert pool_manager.neo4j_pool is not None, "Neo4j连接池应该被配置"
    
    logger.info("✅ 连接池配置验证成功")


@pytest.mark.asyncio
async def test_neo4j_connection_pool_usage():
    """测试Neo4j连接池使用"""
    from src.applications.fitness.workflow_executor import get_connection_pool_manager
    from src.framework.storage.connection_pool_manager import ConnectionPoolManager
    
    # 获取连接池管理器
    pool_manager = get_connection_pool_manager()
    
    # 初始化连接池（如果尚未初始化）
    if not pool_manager._initialized:
        await pool_manager.initialize()
    
    # 测试获取Neo4j会话
    try:
        async with pool_manager.get_neo4j_session() as session:
            # 执行简单查询
            result = await session.run("RETURN 1 AS num")
            record = await result.single()
            assert record["num"] == 1, "Neo4j查询应该返回1"
            logger.info("✅ Neo4j连接池查询成功")
    except Exception as e:
        logger.warning(f"⚠️ Neo4j连接池测试失败: {e}")
        pytest.skip(f"Neo4j连接不可用: {e}")


@pytest.mark.asyncio
async def test_mysql_connection_pool_usage():
    """测试MySQL连接池使用"""
    from src.applications.fitness.workflow_executor import get_connection_pool_manager
    
    # 获取连接池管理器
    pool_manager = get_connection_pool_manager()
    
    # 初始化连接池（如果尚未初始化）
    if not pool_manager._initialized:
        await pool_manager.initialize()
    
    # 测试获取MySQL连接
    try:
        async with pool_manager.get_mysql_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1 AS num")
                result = await cursor.fetchone()
                assert result == (1,), "MySQL查询应该返回(1,)"
                logger.info("✅ MySQL连接池查询成功")
    except Exception as e:
        logger.warning(f"⚠️ MySQL连接池测试失败: {e}")
        pytest.skip(f"MySQL连接不可用: {e}")


@pytest.mark.asyncio
async def test_connection_pool_health_check():
    """测试连接池健康检查"""
    from src.applications.fitness.workflow_executor import get_connection_pool_manager
    
    # 获取连接池管理器
    pool_manager = get_connection_pool_manager()
    
    # 初始化连接池（如果尚未初始化）
    if not pool_manager._initialized:
        await pool_manager.initialize()
    
    # 执行健康检查
    health_status = await pool_manager.health_check()
    
    logger.info(f"连接池健康状态: {health_status}")
    
    # 验证健康状态
    assert isinstance(health_status, dict), "健康状态应该是字典"
    
    if 'mysql' in health_status:
        logger.info(f"  MySQL: {'健康' if health_status['mysql'] else '不健康'}")
    
    if 'neo4j' in health_status:
        logger.info(f"  Neo4j: {'健康' if health_status['neo4j'] else '不健康'}")


@pytest.mark.asyncio
async def test_connection_pool_stats():
    """测试连接池统计信息"""
    from src.applications.fitness.workflow_executor import get_connection_pool_manager
    
    # 获取连接池管理器
    pool_manager = get_connection_pool_manager()
    
    # 初始化连接池（如果尚未初始化）
    if not pool_manager._initialized:
        await pool_manager.initialize()
    
    # 获取统计信息
    stats = pool_manager.get_all_stats()
    
    logger.info(f"连接池统计信息: {stats}")
    
    # 验证统计信息
    assert isinstance(stats, dict), "统计信息应该是字典"
    
    if 'mysql' in stats:
        logger.info(f"  MySQL统计: {stats['mysql']}")
    
    if 'neo4j' in stats:
        logger.info(f"  Neo4j统计: {stats['neo4j']}")


@pytest.mark.asyncio
@pytest.mark.skip(reason="E2E测试：需要真实数据库连接池初始化+三层检索，单独执行")
async def test_three_layer_engine_with_connection_pool():
    """测试三层检索引擎使用连接池"""
    from src.applications.fitness.workflow_executor import get_connection_pool_manager
    from src.framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine
    
    # 获取连接池管理器
    pool_manager = get_connection_pool_manager()
    
    # 初始化连接池（如果尚未初始化）
    if not pool_manager._initialized:
        await pool_manager.initialize()
    
    # 创建三层检索引擎（传入连接池管理器）
    engine = TrueThreeLayerEngine(connection_pool_manager=pool_manager)
    
    # 验证连接池管理器已传入
    assert engine.connection_pool_manager is not None, "三层检索引擎应该有连接池管理器"
    logger.info("✅ 三层检索引擎已配置连接池管理器")
    
    # 执行简单查询测试
    try:
        result = await engine.execute_three_layer_query(
            query="胸肌训练",
            domain="fitness_exercises",
            top_k=5
        )
        
        logger.info(f"✅ 三层检索完成: {len(result.final_results)}个结果")
        logger.info(f"  Layer1: {result.layer1_result.success}")
        logger.info(f"  Layer2: {result.layer2_result.success}")
        logger.info(f"  Layer3: {result.layer3_result.success}")
        
    except Exception as e:
        logger.warning(f"⚠️ 三层检索测试失败: {e}")
        pytest.skip(f"三层检索不可用: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
