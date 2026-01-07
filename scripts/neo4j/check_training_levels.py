# -*- coding: utf-8 -*-
"""检查训练等级数据"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager

manager = Neo4jManager(
    uri='bolt://neo4j:7687',
    user='neo4j',
    password='build_body_2024',
    database='neo4j'
)

# 查看所有TrainingLevel节点
query = '''
MATCH (n:TrainingLevel)
RETURN n.name as name, n.name_zh as name_zh, n.name_en as name_en
ORDER BY n.name
'''
results = manager.execute_query(query, {})
print('现有TrainingLevel节点:')
for r in results:
    name = r.get('name')
    name_zh = r.get('name_zh')
    name_en = r.get('name_en')
    print(f'  name={name}, name_zh={name_zh}, name_en={name_en}')

# 查看Exercise的difficulty字段分布
query2 = '''
MATCH (e:Exercise)
RETURN e.difficulty as difficulty, count(e) as count
ORDER BY count DESC
'''
results2 = manager.execute_query(query2, {})
print()
print('Exercise difficulty分布:')
for r in results2:
    diff = r.get('difficulty')
    cnt = r.get('count')
    print(f'  "{diff}": {cnt}个')

# 查看几个样本
query3 = '''
MATCH (e:Exercise)
RETURN e.id as id, e.name_zh as name, e.difficulty as difficulty
LIMIT 5
'''
results3 = manager.execute_query(query3, {})
print()
print('样本Exercise:')
for r in results3:
    print(f'  id={r.get("id")}, name={r.get("name_zh")}, difficulty={r.get("difficulty")}')

manager.close()
