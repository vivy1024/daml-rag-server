#!/usr/bin/env python3
"""检查Neo4j统计信息"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://fitness_neo4j:7687', auth=('neo4j', 'build_body_2024'))
session = driver.session()

print('=== Neo4j 节点统计 ===')
result = session.run('MATCH (n) RETURN DISTINCT labels(n) as labels, count(*) as count ORDER BY count DESC')
for r in result:
    print(f'{r["labels"]}: {r["count"]}')

print()
print('=== Neo4j 关系统计 ===')
result = session.run('MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC')
for r in result:
    print(f'{r["type"]}: {r["count"]}')

session.close()
driver.close()
