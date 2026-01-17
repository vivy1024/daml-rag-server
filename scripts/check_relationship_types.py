#!/usr/bin/env python3
"""检查Neo4j关系类型分布"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
PRODUCTION_URI = "bolt://182.92.78.183:32372"
AUTH = ("neo4j", "build_body_2024")

def check_relationships(uri, name):
    driver = GraphDatabase.driver(uri, auth=AUTH)
    with driver.session() as session:
        result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC")
        print(f"\n{name} 关系分布:")
        total = 0
        for record in result:
            count = record['count']
            total += count
            print(f"  {record['type']}: {count}")
        print(f"  总计: {total}")
    driver.close()

check_relationships(LOCAL_URI, "本地")
check_relationships(PRODUCTION_URI, "生产")
