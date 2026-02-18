#!/usr/bin/env python3
"""清理远程Neo4j所有重复数据"""
from neo4j import GraphDatabase

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

def main():
    print("=" * 50)
    print("清理Neo4j重复数据")
    print("=" * 50)
    
    remote = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    local = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    
    try:
        # 1. 清理重复的TrainingParams节点
        print("\n1. 清理TrainingParams重复节点...")
        with local.session() as s:
            result = s.run("MATCH (n:TrainingParams) RETURN n.id as id, n.name as name")
            local_keys = set((r['id'], r['name']) for r in result)
        
        with remote.session() as s:
            # 删除不在本地的节点
            result = s.run("""
                MATCH (n:TrainingParams)
                WITH n, n.id as id, n.name as name
                WITH collect({node: n, key: [id, name]}) as nodes
                UNWIND nodes as item
                WITH item.node as n, item.key as key
                WITH key, collect(n) as duplicates
                WHERE size(duplicates) > 1
                UNWIND duplicates[1..] as dup
                DETACH DELETE dup
                RETURN count(*) as deleted
            """)
            deleted = result.single()["deleted"]
            print(f"   删除 {deleted} 个重复TrainingParams")
        
        # 2. 清理重复关系
        print("\n2. 清理重复关系...")
        rel_types = ['FOR_GOAL', 'FOR_LEVEL']
        for rel_type in rel_types:
            with remote.session() as s:
                result = s.run(f"""
                    MATCH (a)-[r:{rel_type}]->(b)
                    WITH a, b, collect(r) as rels
                    WHERE size(rels) > 1
                    UNWIND rels[1..] as dup
                    DELETE dup
                    RETURN count(*) as deleted
                """)
                deleted = result.single()["deleted"]
                print(f"   {rel_type}: 删除 {deleted} 条重复")
        
        # 3. 最终对比
        print("\n3. 最终状态:")
        with local.session() as s:
            result = s.run("MATCH (n) RETURN count(n) as c")
            local_nodes = result.single()["c"]
            result = s.run("MATCH ()-[r]->() RETURN count(r) as c")
            local_rels = result.single()["c"]
        
        with remote.session() as s:
            result = s.run("MATCH (n) RETURN count(n) as c")
            remote_nodes = result.single()["c"]
            result = s.run("MATCH ()-[r]->() RETURN count(r) as c")
            remote_rels = result.single()["c"]
        
        print(f"   本地: {local_nodes} 节点, {local_rels} 关系")
        print(f"   远程: {remote_nodes} 节点, {remote_rels} 关系")
        print(f"   差异: 节点{local_nodes - remote_nodes}, 关系{local_rels - remote_rels}")
        
    finally:
        remote.close()
        local.close()

if __name__ == "__main__":
    main()
