#!/usr/bin/env python3
"""
查询Neo4j数据库中的动作数据
用于修复测试脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.clients.neo4j_client import Neo4jClient


async def query_exercise_data():
    """查询动作数据"""
    
    print("\n" + "="*80)
    print("查询Neo4j数据库中的动作数据")
    print("="*80)
    
    # 初始化Neo4j连接
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    try:
        # 1. 查询前10个动作的ID和基本信息
        print("\n1. 查询前10个动作的ID和基本信息:")
        print("-" * 80)
        
        query1 = """
        MATCH (e:Exercise)
        RETURN e.id AS id, e.name_zh AS name_zh, e.name_en AS name_en, 
               e.difficulty AS difficulty, e.safety_level AS safety_level
        LIMIT 10
        """
        
        result1 = await neo4j_client.execute_query(query1)
        
        if result1:
            for record in result1:
                print(f"ID: {record['id']}")
                print(f"  中文名: {record['name_zh']}")
                print(f"  英文名: {record['name_en']}")
                print(f"  难度: {record['difficulty']}")
                print(f"  安全等级: {record['safety_level']}")
                print()
        
        # 2. 查询有SIMILAR_TO关系的动作
        print("\n2. 查询有SIMILAR_TO关系的动作:")
        print("-" * 80)
        
        query2 = """
        MATCH (e1:Exercise)-[r:SIMILAR_TO]->(e2:Exercise)
        RETURN e1.id AS source_id, e1.name_zh AS source_name,
               e2.id AS target_id, e2.name_zh AS target_name,
               r.similarity_score AS score
        LIMIT 10
        """
        
        result2 = await neo4j_client.execute_query(query2)
        
        if result2:
            print(f"找到 {len(result2)} 个SIMILAR_TO关系:")
            for record in result2:
                print(f"{record['source_name']} (ID: {record['source_id']}) -> "
                      f"{record['target_name']} (ID: {record['target_id']}) "
                      f"[相似度: {record.get('score', 'N/A')}]")
        else:
            print("⚠️ 未找到SIMILAR_TO关系")
        
        # 3. 查询有CONTRAINDICATED_FOR关系的动作
        print("\n3. 查询有CONTRAINDICATED_FOR关系的动作:")
        print("-" * 80)
        
        query3 = """
        MATCH (e:Exercise)-[r:CONTRAINDICATED_FOR]->(condition)
        RETURN e.id AS exercise_id, e.name_zh AS exercise_name,
               condition.name_zh AS condition_name
        LIMIT 10
        """
        
        result3 = await neo4j_client.execute_query(query3)
        
        if result3:
            print(f"找到 {len(result3)} 个CONTRAINDICATED_FOR关系:")
            for record in result3:
                print(f"{record['exercise_name']} (ID: {record['exercise_id']}) -> "
                      f"禁忌: {record['condition_name']}")
        else:
            print("⚠️ 未找到CONTRAINDICATED_FOR关系")
        
        # 4. 统计动作总数和关系总数
        print("\n4. 统计数据:")
        print("-" * 80)
        
        query4 = """
        MATCH (e:Exercise)
        RETURN count(e) AS total_exercises
        """
        
        result4 = await neo4j_client.execute_query(query4)
        if result4:
            print(f"动作总数: {result4[0]['total_exercises']}")
        
        query5 = """
        MATCH ()-[r:SIMILAR_TO]->()
        RETURN count(r) AS total_similar
        """
        
        result5 = await neo4j_client.execute_query(query5)
        if result5:
            print(f"SIMILAR_TO关系总数: {result5[0]['total_similar']}")
        
        # 5. 查询特定类型的动作（用于测试）
        print("\n5. 查询适合测试的动作（胸部、中等难度）:")
        print("-" * 80)
        
        query6 = """
        MATCH (e:Exercise)-[:TARGETS_PRIMARY]->(m:Muscle)
        WHERE m.name_zh CONTAINS '胸' AND e.difficulty = 'intermediate'
        RETURN e.id AS id, e.name_zh AS name_zh, e.difficulty AS difficulty,
               e.safety_level AS safety_level
        LIMIT 5
        """
        
        result6 = await neo4j_client.execute_query(query6)
        
        if result6:
            print(f"找到 {len(result6)} 个适合测试的动作:")
            for record in result6:
                print(f"ID: {record['id']}, 名称: {record['name_zh']}, "
                      f"难度: {record['difficulty']}, 安全等级: {record['safety_level']}")
        
        # 6. 查询动作的完整字段
        print("\n6. 查询一个动作的完整字段:")
        print("-" * 80)
        
        query7 = """
        MATCH (e:Exercise)
        RETURN e
        LIMIT 1
        """
        
        result7 = await neo4j_client.execute_query(query7)
        
        if result7:
            exercise = result7[0]['e']
            print(f"动作字段: {list(exercise.keys())}")
        
    finally:
        print("\n" + "="*80)
        print("查询完成")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(query_exercise_data())
