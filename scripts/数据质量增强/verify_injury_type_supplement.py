#!/usr/bin/env python3
"""
验证InjuryType节点数据补充结果

执行方式：
docker exec fitness_daml_rag python scripts/data_supplement/verify_injury_type_supplement.py

作者：薛小川
日期：2025-12-15
"""

import asyncio
import sys
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


async def verify_injury_type_supplement():
    """验证InjuryType节点补充结果"""
    
    # Neo4j配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://fitness_neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        async with driver.session() as session:
            print("=" * 60)
            print("InjuryType节点数据补充验证")
            print("=" * 60)
            
            # 1. 统计总数
            query_total = """
            MATCH (it:InjuryType)
            RETURN count(it) as total
            """
            result = await session.run(query_total)
            record = await result.single()
            total_count = record["total"]
            print(f"\n1. 总节点数: {total_count}")
            
            # 2. 统计有severity_level的节点
            query_with_severity = """
            MATCH (it:InjuryType)
            WHERE it.severity_level IS NOT NULL
            RETURN count(it) as count
            """
            result = await session.run(query_with_severity)
            record = await result.single()
            with_severity = record["count"]
            coverage = (with_severity / total_count * 100) if total_count > 0 else 0
            print(f"2. 有severity_level的节点: {with_severity} ({coverage:.1f}%)")
            
            # 3. 按严重程度统计
            query_by_level = """
            MATCH (it:InjuryType)
            WHERE it.severity_level IS NOT NULL
            RETURN it.severity_level as level, 
                   count(it) as count,
                   collect(it.name_zh) as names
            ORDER BY level
            """
            result = await session.run(query_by_level)
            records = await result.data()
            
            print("\n3. 按严重程度分布:")
            for record in records:
                level = record["level"]
                count = record["count"]
                names = record["names"]
                print(f"   {level}: {count} 个")
                for name in names:
                    print(f"      - {name}")
            
            # 4. 检查枚举值是否合法
            query_invalid = """
            MATCH (it:InjuryType)
            WHERE it.severity_level IS NOT NULL
              AND NOT (it.severity_level IN ['mild', 'moderate', 'severe'])
            RETURN count(it) as invalid_count,
                   collect(it.name_zh) as invalid_names
            """
            result = await session.run(query_invalid)
            record = await result.single()
            invalid_count = record["invalid_count"]
            
            print(f"\n4. 非法枚举值数量: {invalid_count}")
            if invalid_count > 0:
                print(f"   非法值节点: {record['invalid_names']}")
            
            # 5. 检查未补充的节点
            query_missing = """
            MATCH (it:InjuryType)
            WHERE it.severity_level IS NULL
            RETURN count(it) as missing_count,
                   collect(it.name_zh) as missing_names
            """
            result = await session.run(query_missing)
            record = await result.single()
            missing_count = record["missing_count"]
            
            print(f"\n5. 未补充的节点: {missing_count}")
            if missing_count > 0:
                print(f"   未补充节点: {record['missing_names']}")
            
            # 6. 验证结果
            print("\n" + "=" * 60)
            print("验证结果")
            print("=" * 60)
            
            if with_severity == total_count and invalid_count == 0:
                print("✅ 验证通过：所有InjuryType节点都有合法的severity_level字段")
                print(f"   - 总节点数: {total_count}")
                print(f"   - 覆盖率: 100%")
                print(f"   - 枚举值合法性: 通过")
                return 0
            else:
                print("⚠️ 验证失败：")
                if with_severity < total_count:
                    print(f"   - 覆盖率不足: {coverage:.1f}% (期望100%)")
                if invalid_count > 0:
                    print(f"   - 存在非法枚举值: {invalid_count} 个")
                return 1
    
    finally:
        await driver.close()


if __name__ == "__main__":
    exit_code = asyncio.run(verify_injury_type_supplement())
    sys.exit(exit_code)
