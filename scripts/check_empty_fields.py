#!/usr/bin/env python3
"""检查Neo4j Exercise节点的空值字段"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"

fields = [
    'difficulty_zh', 'difficulty_en', 
    'force_zh', 'force_en', 
    'mechanic_zh', 'mechanic_en',
    'rep_range', 'set_range', 'rest_period',
    'intensity_percentage', 'safety_level',
    'primary_muscle_zh', 'primary_muscle_en'
]

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    print("=== 关键字段空值统计 ===")
    for field in fields:
        query = f'MATCH (e:Exercise) WHERE e.{field} IS NULL OR e.{field} = "" RETURN count(e) as cnt'
        result = session.run(query)
        cnt = result.single()['cnt']
        if cnt > 0:
            print(f"  {field}: {cnt} 个空值")
    
    # 总数
    result = session.run("MATCH (e:Exercise) RETURN count(e) as cnt")
    total = result.single()['cnt']
    print(f"\n总Exercise数量: {total}")

driver.close()
