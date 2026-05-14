"""
测试Food节点补充器

功能：
1. 测试血糖指数补充
2. 测试消化时间补充
3. 测试过敏原信息补充

作者：薛小川
日期：2025-12-15
"""

import asyncio
import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from neo4j import AsyncGraphDatabase
from src.applications.fitness.data_supplement.food_supplementer import FoodSupplementer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_food_supplementer():
    """测试Food节点补充器"""
    
    # Neo4j连接配置
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")
    
    logger.info("=" * 80)
    logger.info("开始测试Food节点补充器")
    logger.info("=" * 80)
    
    driver = None
    
    try:
        # 连接Neo4j
        logger.info(f"连接Neo4j: {NEO4J_URI}")
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        
        # 验证连接
        await driver.verify_connectivity()
        logger.info("✅ Neo4j连接成功")
        
        # 查询Food节点总数
        async with driver.session() as session:
            result = await session.run("MATCH (f:Food) RETURN count(f) as total")
            record = await result.single()
            total_foods = record["total"]
            logger.info(f"📊 数据库中共有 {total_foods} 个Food节点")
        
        # 创建补充器
        supplementer = FoodSupplementer(driver)
        
        # 执行补充
        logger.info("\n" + "=" * 80)
        logger.info("开始执行Food节点数据补充")
        logger.info("=" * 80)
        
        result = await supplementer.supplement()
        
        # 输出结果
        logger.info("\n" + "=" * 80)
        logger.info("补充结果")
        logger.info("=" * 80)
        logger.info(f"总节点数: {result.total_nodes}")
        logger.info(f"更新节点数: {result.updated_nodes}")
        logger.info(f"执行时间: {result.execution_time:.2f}秒")
        
        if result.errors:
            logger.error(f"错误数量: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"  - {error['stage']}: {error['error']}")
        else:
            logger.info("✅ 无错误")
        
        # 验证补充结果
        logger.info("\n" + "=" * 80)
        logger.info("验证补充结果")
        logger.info("=" * 80)
        
        async with driver.session() as session:
            # 检查血糖指数
            result = await session.run("""
                MATCH (f:Food)
                WHERE f.glycemic_index IS NOT NULL
                RETURN count(f) as count
            """)
            record = await result.single()
            gi_count = record["count"]
            logger.info(f"✅ 有血糖指数的Food节点: {gi_count}")
            
            # 检查血糖负荷
            result = await session.run("""
                MATCH (f:Food)
                WHERE f.glycemic_load IS NOT NULL
                RETURN count(f) as count
            """)
            record = await result.single()
            gl_count = record["count"]
            logger.info(f"✅ 有血糖负荷的Food节点: {gl_count}")
            
            # 检查消化时间
            result = await session.run("""
                MATCH (f:Food)
                WHERE f.digestion_time_minutes IS NOT NULL
                RETURN count(f) as count
            """)
            record = await result.single()
            digestion_count = record["count"]
            logger.info(f"✅ 有消化时间的Food节点: {digestion_count}")
            
            # 检查过敏原
            result = await session.run("""
                MATCH (f:Food)
                WHERE f.allergens IS NOT NULL
                RETURN count(f) as count
            """)
            record = await result.single()
            allergen_count = record["count"]
            logger.info(f"✅ 有过敏原信息的Food节点: {allergen_count}")
            
            # 显示一些示例
            logger.info("\n" + "=" * 80)
            logger.info("示例数据")
            logger.info("=" * 80)
            
            result = await session.run("""
                MATCH (f:Food)
                WHERE f.glycemic_index IS NOT NULL
                RETURN f.name as name, 
                       f.glycemic_index as gi, 
                       f.glycemic_load as gl,
                       f.digestion_time_minutes as digestion,
                       f.allergens as allergens
                LIMIT 10
            """)
            
            records = await result.data()
            for i, record in enumerate(records, 1):
                logger.info(f"\n示例 {i}:")
                logger.info(f"  食物名称: {record['name']}")
                logger.info(f"  血糖指数: {record['gi']}")
                logger.info(f"  血糖负荷: {record['gl']}")
                logger.info(f"  消化时间: {record['digestion']}分钟")
                logger.info(f"  过敏原: {record['allergens']}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ 测试完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False
    
    finally:
        if driver:
            await driver.close()
            logger.info("Neo4j连接已关闭")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_food_supplementer())
    sys.exit(0 if success else 1)
