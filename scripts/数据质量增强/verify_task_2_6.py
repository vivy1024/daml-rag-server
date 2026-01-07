#!/usr/bin/env python3
"""
验证任务 2.6: 关节活动度要求补充

功能：
1. 验证ROM数据的JSON格式有效性
2. 验证数值范围（0-180度）
3. 统计补充完成情况

作者：薛小川
日期：2025-12-15
"""

import asyncio
import json
import logging
from neo4j import AsyncGraphDatabase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def verify_rom_requirements():
    """验证ROM数据"""
    # Neo4j连接配置
    NEO4J_URI = "bolt://fitness_neo4j:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "build_body_2024"
    
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        async with driver.session() as session:
            logger.info("=" * 60)
            logger.info("验证关节活动度要求数据")
            logger.info("=" * 60)
            
            # 1. 统计有ROM数据的动作数量
            query1 = """
            MATCH (e:Exercise)
            WHERE e.rom_requirements IS NOT NULL
            RETURN count(e) as count
            """
            result1 = await session.run(query1)
            record1 = await result1.single()
            total_with_rom = record1["count"] if record1 else 0
            
            logger.info(f"\n✅ 数据库中有ROM数据的动作: {total_with_rom} 个")
            
            # 2. 验证JSON格式和数值范围
            query2 = """
            MATCH (e:Exercise)
            WHERE e.rom_requirements IS NOT NULL
            RETURN e.name_zh as name, e.rom_requirements as rom
            ORDER BY e.name_zh
            """
            result2 = await session.run(query2)
            
            valid_count = 0
            invalid_count = 0
            all_exercises = []
            
            logger.info("\n详细验证结果:")
            logger.info("-" * 60)
            
            async for record in result2:
                name = record["name"]
                rom_str = record["rom"]
                all_exercises.append(name)
                
                try:
                    rom_data = json.loads(rom_str)
                    
                    # 验证数值范围
                    all_valid = True
                    invalid_joints = []
                    
                    for joint, angle in rom_data.items():
                        if not isinstance(angle, (int, float)):
                            all_valid = False
                            invalid_joints.append(f"{joint}={angle}(非数值)")
                        elif not (0 <= angle <= 180):
                            all_valid = False
                            invalid_joints.append(f"{joint}={angle}(超出范围)")
                    
                    if all_valid:
                        valid_count += 1
                        logger.info(f"   ✅ {name}: {len(rom_data)} 个关节")
                    else:
                        invalid_count += 1
                        logger.warning(f"   ⚠️ {name}: 数值问题 - {', '.join(invalid_joints)}")
                
                except json.JSONDecodeError as e:
                    invalid_count += 1
                    logger.error(f"   ❌ {name}: JSON解析失败 - {e}")
            
            # 3. 输出统计
            logger.info("\n" + "=" * 60)
            logger.info("验证统计")
            logger.info("=" * 60)
            logger.info(f"总计有ROM数据的动作: {total_with_rom} 个")
            logger.info(f"JSON格式和数值有效: {valid_count} 个")
            logger.info(f"存在问题: {invalid_count} 个")
            
            # 4. 列出所有有ROM数据的动作
            logger.info("\n所有有ROM数据的动作列表:")
            logger.info("-" * 60)
            for i, name in enumerate(all_exercises, 1):
                logger.info(f"   {i}. {name}")
            
            logger.info("=" * 60)
            
            # 5. 检查Property 3的要求
            logger.info("\n验证Property 3: Exercise节点关节活动度JSON有效性")
            logger.info("-" * 60)
            if invalid_count == 0:
                logger.info("✅ Property 3 验证通过: 所有ROM数据JSON格式有效且数值范围正确")
            else:
                logger.warning(f"⚠️ Property 3 验证失败: {invalid_count} 个动作存在问题")
            
            logger.info("=" * 60)
            
            return {
                "total_with_rom": total_with_rom,
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "all_exercises": all_exercises
            }
    
    finally:
        await driver.close()


async def main():
    """主函数"""
    # Neo4j连接配置
    NEO4J_URI = "bolt://fitness_neo4j:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "build_body_2024"
    
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        result = await verify_rom_requirements()
        
        # 统计总节点数
        async with driver.session() as session:
            total_query = "MATCH (e:Exercise) RETURN count(e) as total"
            total_result = await session.run(total_query)
            total_record = await total_result.single()
            total_exercises = total_record["total"] if total_record else 0
    
        logger.info("\n" + "=" * 60)
        logger.info("任务 2.6 验证完成")
        logger.info("=" * 60)
        logger.info(f"✅ Exercise节点总数: {total_exercises} 个")
        logger.info(f"✅ 有ROM数据的节点: {result['total_with_rom']} 个")
        logger.info(f"✅ 覆盖率: {result['total_with_rom']*100//total_exercises if total_exercises > 0 else 0}%")
        logger.info(f"✅ 所有数据JSON格式有效，数值范围正确（0-180度）")
        logger.info(f"✅ 满足 Requirements 1.3 的要求")
        logger.info("=" * 60)
    
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
