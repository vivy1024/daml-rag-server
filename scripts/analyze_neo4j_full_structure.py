#!/usr/bin/env python3
"""分析Neo4j完整结构"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://fitness_neo4j:7687', auth=('neo4j', 'build_body_2024'))
session = driver.session()

print('=== 当前Neo4j完整结构分析 ===\n')

# 所有节点类型
print('【节点类型及数量】')
result = session.run('''
    MATCH (n)
    RETURN DISTINCT labels(n) as labels, count(n) as count
    ORDER BY count DESC
''')
for r in result:
    print(f"  {r['labels']}: {r['count']}")

print('\n【关系类型及数量】')
result = session.run('''
    MATCH ()-[r]->()
    RETURN type(r) as type, count(r) as count
    ORDER BY count DESC
''')
for r in result:
    print(f"  {r['type']}: {r['count']}")

print('\n【TrainingLevel节点】')
result = session.run('MATCH (t:TrainingLevel) RETURN t.name as name, t.name_zh as name_zh')
for r in result:
    print(f"  {r['name']} / {r['name_zh']}")

print('\n【TrainingGoal节点】')
result = session.run('MATCH (t:TrainingGoal) RETURN t.name as name, t.name_zh as name_zh')
for r in result:
    print(f"  {r['name']} / {r['name_zh']}")

print('\n【Equipment节点】')
result = session.run('MATCH (e:Equipment) RETURN e.name_zh as name, e.name_en as name_en')
for r in result:
    print(f"  {r['name']} / {r['name_en']}")

print('\n【InjuryType节点】')
result = session.run('MATCH (i:InjuryType) RETURN i.name_zh as name LIMIT 10')
for r in result:
    print(f"  {r['name']}")

print('\n【WorkoutProgram节点】')
result = session.run('MATCH (w:WorkoutProgram) RETURN w.name as name')
for r in result:
    print(f"  {r['name']}")

print('\n【Exercise节点属性示例】')
result = session.run('MATCH (e:Exercise) RETURN keys(e) as keys LIMIT 1')
for r in result:
    print(f"  共{len(r['keys'])}个属性: {sorted(r['keys'])}")

session.close()
driver.close()
