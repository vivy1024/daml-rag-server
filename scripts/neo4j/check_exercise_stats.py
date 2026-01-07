"""检查Exercise统计"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "build_body_2024"))
session = driver.session()

# 检查没有primary_muscle_zh的Exercise
r1 = session.run('MATCH (e:Exercise) WHERE e.primary_muscle_zh IS NULL OR e.primary_muscle_zh = "" RETURN count(e) as cnt')
print(f"没有primary_muscle_zh: {r1.single()['cnt']}")

# 检查总数
r2 = session.run('MATCH (e:Exercise) RETURN count(e) as cnt')
print(f"Exercise总数: {r2.single()['cnt']}")

# 检查有TARGETS_PRIMARY关系的
r3 = session.run('MATCH (e:Exercise)-[:TARGETS_PRIMARY]->() RETURN count(DISTINCT e) as cnt')
print(f"有TARGETS_PRIMARY关系: {r3.single()['cnt']}")

# 检查Muscle节点总数
r4 = session.run('MATCH (m:Muscle) RETURN count(m) as cnt')
print(f"Muscle节点总数: {r4.single()['cnt']}")

driver.close()
