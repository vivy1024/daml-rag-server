# -*- coding: utf-8 -*-
"""检查Neo4j Exercise difficulty分布"""

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

query = '''
MATCH (e:Exercise)
RETURN e.difficulty as difficulty, count(e) as count
ORDER BY count DESC
'''
results = manager.execute_query(query, {})

print('Neo4j Exercise difficulty分布:')
for r in results:
    diff = r.get('difficulty')
    count = r.get('count')
    print(f'  {diff}: {count}个')

manager.close()
