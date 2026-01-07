#!/usr/bin/env python3
"""检查Neo4j数据"""
import os
os.environ['NEO4J_PASSWORD'] = 'build_body_2024'

from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'build_body_2024'))

with driver.session() as session:
    # 查询Exercise的difficulty分布
    result = session.run('MATCH (e:Exercise) RETURN DISTINCT e.difficulty as difficulty, count(*) as cnt ORDER BY cnt DESC LIMIT 10')
    print('=== Exercise difficulty ===')
    for r in result:
        print(f"  {r['difficulty']}: {r['cnt']}")
    
    # 查询Muscle节点
    result = session.run('MATCH (m:Muscle) RETURN m.name_zh as name LIMIT 20')
    print('\n=== Muscle name_zh ===')
    for r in result:
        print(f"  {r['name']}")
    
    # 查询Exercise和Muscle的关系
    result = session.run('''
        MATCH (e:Exercise)-[r:TARGETS_PRIMARY]->(m:Muscle)
        WHERE m.name_zh = '胸大肌'
        RETURN e.name_zh as exercise, m.name_zh as muscle, e.difficulty as difficulty
        LIMIT 5
    ''')
    print('\n=== 胸大肌相关动作 ===')
    for r in result:
        print(f"  {r['exercise']} -> {r['muscle']} (difficulty: {r['difficulty']})")
    
    # 查询胸部相关
    result = session.run('''
        MATCH (e:Exercise)-[r:TARGETS_PRIMARY]->(m:Muscle)
        WHERE m.name_zh = '胸部'
        RETURN e.name_zh as exercise, m.name_zh as muscle, e.difficulty as difficulty
        LIMIT 5
    ''')
    print('\n=== 胸部相关动作 ===')
    for r in result:
        print(f"  {r['exercise']} -> {r['muscle']} (difficulty: {r['difficulty']})")

driver.close()
