#!/usr/bin/env python3
"""检查Neo4j迁移进度"""
from neo4j import GraphDatabase
import time

LOCAL_URI = "bolt://fitness_neo4j:7687"
PRODUCTION_URI = "bolt://182.92.78.183:32372"
AUTH = ("neo4j", "build_body_2024")

def get_stats(uri):
    driver = GraphDatabase.driver(uri, auth=AUTH)
    with driver.session() as session:
        nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
    driver.close()
    return nodes, rels

print("检查迁移进度...\n")

local_nodes, local_rels = get_stats(LOCAL_URI)
print(f"本地目标: {local_nodes} 节点, {local_rels} 关系")

for i in range(5):
    prod_nodes, prod_rels = get_stats(PRODUCTION_URI)
    progress = (prod_rels / local_rels * 100) if local_rels > 0 else 0
    print(f"第{i+1}次: {prod_nodes} 节点, {prod_rels} 关系 ({progress:.1f}%)")
    
    if prod_rels >= local_rels:
        print("\n✅ 迁移完成！")
        break
    
    if i < 4:
        time.sleep(20)
