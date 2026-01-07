# -*- coding: utf-8 -*-
"""检查Neo4j Exercise节点属性分布"""

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

# 1. 查看Exercise节点的所有属性
print("=" * 60)
print("1. Exercise节点属性列表")
print("=" * 60)
query = '''
MATCH (e:Exercise)
RETURN keys(e) as properties
LIMIT 1
'''
result = manager.execute_query(query, {})
if result:
    props = sorted(result[0]['properties'])
    for prop in props:
        print(f"  - {prop}")

# 2. 查看force属性分布
print("\n" + "=" * 60)
print("2. force属性分布")
print("=" * 60)
query = '''
MATCH (e:Exercise)
RETURN e.force as value, count(e) as count
ORDER BY count DESC
'''
results = manager.execute_query(query, {})
for r in results:
    print(f"  {r['value']}: {r['count']}个")

# 3. 查看mechanic属性分布
print("\n" + "=" * 60)
print("3. mechanic属性分布")
print("=" * 60)
query = '''
MATCH (e:Exercise)
RETURN e.mechanic as value, count(e) as count
ORDER BY count DESC
'''
results = manager.execute_query(query, {})
for r in results:
    print(f"  {r['value']}: {r['count']}个")

# 4. 查看difficulty属性分布
print("\n" + "=" * 60)
print("4. difficulty属性分布")
print("=" * 60)
query = '''
MATCH (e:Exercise)
RETURN e.difficulty as value, count(e) as count
ORDER BY count DESC
'''
results = manager.execute_query(query, {})
for r in results:
    print(f"  {r['value']}: {r['count']}个")

# 5. 查看一个样本Exercise的完整属性
print("\n" + "=" * 60)
print("5. 样本Exercise完整属性")
print("=" * 60)
query = '''
MATCH (e:Exercise)
RETURN e
LIMIT 1
'''
results = manager.execute_query(query, {})
if results:
    exercise = dict(results[0]['e'])
    for key, value in sorted(exercise.items()):
        print(f"  {key}: {value}")

manager.close()
