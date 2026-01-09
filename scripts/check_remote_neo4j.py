#!/usr/bin/env python3
"""检查并清理远程Neo4j数据库"""
from neo4j import GraphDatabase

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

def main():
    driver = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    
    try:
        with driver.session() as session:
            # 检查节点数
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            nodes = result.single()["nodes"]
            
            # 检查关系数
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            rels = result.single()["rels"]
            
            print(f"远程Neo4j状态:")
            print(f"  节点: {nodes}")
            print(f"  关系: {rels}")
            
            # 检查各类型关系数量
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY count DESC
            """)
            print(f"\n关系类型分布:")
            for record in result:
                print(f"  {record['rel_type']}: {record['count']}")
            
    finally:
        driver.close()

if __name__ == "__main__":
    main()
