#!/usr/bin/env python3
"""检查Neo4j节点标签分布"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
PRODUCTION_URI = "bolt://182.92.78.183:32372"
AUTH = ("neo4j", "build_body_2024")

def check_labels(uri, name):
    driver = GraphDatabase.driver(uri, auth=AUTH)
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC")
        print(f"\n{name} 节点分布:")
        for record in result:
            print(f"  {record['label']}: {record['count']}")
    driver.close()

check_labels(LOCAL_URI, "本地")
check_labels(PRODUCTION_URI, "生产")
