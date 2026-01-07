#!/usr/bin/env python3
"""
获取有效的动作ID用于测试
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.clients.neo4j_client import Neo4jClient


async def get_valid_ids():
    """获取有效的动作ID"""
    
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    try:
        # 查询不同类型的动作用于测试
        queries = {
            "胸部动作（中等难度）": """
                MATCH (e:Exercise)
                WHERE e.primary_muscle_zh CONTAINS '胸' AND e.difficulty = '中级'
                RETURN e.id, e.name_zh, e.difficulty, e.safety_level
                LIMIT 3
            """,
            "肩部动作（新手）": """
                MATCH (e:Exercise)
                WHERE e.primary_muscle_zh CONTAINS '肩' AND e.difficulty = '新手'
                RETURN e.id, e.name_zh, e.difficulty, e.safety_level
                LIMIT 3
            """,
            "腿部动作（高级）": """
                MATCH (e:Exercise)
                WHERE e.primary_muscle_zh CONTAINS '腿' OR e.primary_muscle_zh CONTAINS '股'
                RETURN e.id, e.name_zh, e.difficulty, e.safety_level
                LIMIT 3
            """
        }
        
        for category, query in queries.items():
            print(f"\n{category}:")
            print("-" * 60)
            result = await neo4j_client.execute_query(query)
            
            if result:
                for record in result:
                    print(f"  记录: {record}")
                    print()
            else:
                print("  未找到匹配的动作")
        
        # 查询ID为1-10的动作
        print("\nID 1-10的动作:")
        print("-" * 60)
        query = """
            MATCH (e:Exercise)
            WHERE e.id IN ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
            RETURN e.id, e.name_zh, e.primary_muscle_zh, e.difficulty, e.safety_level
            ORDER BY toInteger(e.id)
        """
        result = await neo4j_client.execute_query(query)
        
        for record in result:
            print(f"ID: {record['id']}, 名称: {record['name_zh']}, "
                  f"肌群: {record['primary_muscle_zh']}, 难度: {record['difficulty']}")
        
    finally:
        print("\n查询完成")


if __name__ == "__main__":
    asyncio.run(get_valid_ids())
