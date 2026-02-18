#!/usr/bin/env python3
"""迁移缺失的Food节点和CONTAINS_NUTRIENT关系"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

def main():
    print("=" * 60)
    print("迁移缺失的Food数据")
    print("=" * 60)
    
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    remote_driver = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    
    try:
        # 获取本地所有Food的id
        with local_driver.session() as session:
            result = session.run("MATCH (f:Food) RETURN f.id as id")
            local_food_ids = set(r['id'] for r in result if r['id'])
        
        # 获取远程所有Food的id
        with remote_driver.session() as session:
            result = session.run("MATCH (f:Food) RETURN f.id as id")
            remote_food_ids = set(r['id'] for r in result if r['id'])
        
        # 找出缺失的Food
        missing_ids = local_food_ids - remote_food_ids
        print(f"缺失Food: {len(missing_ids)} 个")
        
        if missing_ids:
            # 迁移缺失的Food节点
            with local_driver.session() as local_session:
                for food_id in missing_ids:
                    result = local_session.run(
                        "MATCH (f:Food {id: $id}) RETURN f",
                        id=food_id
                    )
                    record = result.single()
                    if record:
                        props = dict(record['f'])
                        with remote_driver.session() as remote_session:
                            remote_session.run(
                                "MERGE (f:Food {id: $id}) SET f = $props",
                                id=food_id, props=props
                            )
            print(f"  已迁移 {len(missing_ids)} 个Food节点")
        
        # 迁移CONTAINS_NUTRIENT关系
        print("\n迁移CONTAINS_NUTRIENT关系...")
        with local_driver.session() as local_session:
            result = local_session.run("""
                MATCH (f:Food)-[r:CONTAINS_NUTRIENT]->(n:Nutrient)
                RETURN f.id as food_id, n.name as nutrient_name, properties(r) as props
            """)
            all_rels = list(result)
        
        print(f"  本地共 {len(all_rels)} 条关系")
        
        migrated = 0
        with remote_driver.session() as remote_session:
            for rel in all_rels:
                try:
                    remote_session.run("""
                        MATCH (f:Food {id: $food_id})
                        MATCH (n:Nutrient {name: $nutrient_name})
                        MERGE (f)-[r:CONTAINS_NUTRIENT]->(n)
                        SET r = $props
                    """, food_id=rel['food_id'], nutrient_name=rel['nutrient_name'], props=rel['props'] or {})
                    migrated += 1
                except:
                    pass
                
                if migrated % 5000 == 0:
                    print(f"    进度: {migrated}/{len(all_rels)}")
        
        print(f"  完成: {migrated} 条")
        
        # 最终验证
        print("\n最终状态:")
        with remote_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            rels = result.single()["rels"]
            print(f"  远程: {nodes} 节点, {rels} 关系")
        
        with local_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            local_nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            local_rels = result.single()["rels"]
            print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
            print(f"  差异: 节点{local_nodes - nodes}, 关系{local_rels - rels}")
        
    finally:
        local_driver.close()
        remote_driver.close()

if __name__ == "__main__":
    main()
