#!/usr/bin/env python3
"""迁移Neo4j剩余的节点和关系"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

def migrate_missing_nodes(local, remote):
    """迁移缺失的节点"""
    print("\n1. 迁移缺失节点...")
    
    # 获取本地所有Food节点
    with local.session() as s:
        result = s.run("MATCH (f:Food) RETURN f.id as id, properties(f) as props")
        local_foods = {r['id']: r['props'] for r in result if r['id']}
    
    # 获取远程Food节点
    with remote.session() as s:
        result = s.run("MATCH (f:Food) RETURN f.id as id")
        remote_ids = set(r['id'] for r in result if r['id'])
    
    # 找出缺失的
    missing = set(local_foods.keys()) - remote_ids
    print(f"   缺失Food节点: {len(missing)}")
    
    # 迁移
    if missing:
        with remote.session() as s:
            for fid in missing:
                props = local_foods[fid]
                s.run("MERGE (f:Food {id: $id}) SET f = $props", id=fid, props=props)
        print(f"   已迁移 {len(missing)} 个Food节点")
    
    # 检查其他标签
    with local.session() as ls:
        result = ls.run("CALL db.labels()")
        labels = [r['label'] for r in result]
    
    for label in labels:
        with local.session() as ls:
            result = ls.run(f"MATCH (n:{label}) RETURN count(n) as c")
            local_count = result.single()['c']
        with remote.session() as rs:
            result = rs.run(f"MATCH (n:{label}) RETURN count(n) as c")
            remote_count = result.single()['c']
        
        if local_count > remote_count:
            print(f"   {label}: 本地{local_count} > 远程{remote_count}, 差{local_count - remote_count}")

def migrate_missing_relationships(local, remote):
    """迁移缺失的关系"""
    print("\n2. 迁移缺失关系...")
    
    # 主要是CONTAINS_NUTRIENT
    print("   迁移 CONTAINS_NUTRIENT...")
    
    with local.session() as s:
        result = s.run("""
            MATCH (f:Food)-[r:CONTAINS_NUTRIENT]->(n:Nutrient)
            RETURN f.id as food_id, n.name as nutrient_name, properties(r) as props
        """)
        local_rels = list(result)
    
    print(f"   本地共 {len(local_rels)} 条")
    
    migrated = 0
    with remote.session() as s:
        for rel in local_rels:
            try:
                s.run("""
                    MATCH (f:Food {id: $food_id})
                    MATCH (n:Nutrient {name: $nutrient_name})
                    MERGE (f)-[r:CONTAINS_NUTRIENT]->(n)
                    SET r = $props
                """, food_id=rel['food_id'], nutrient_name=rel['nutrient_name'], 
                   props=rel['props'] or {})
                migrated += 1
            except:
                pass
            
            if migrated % 5000 == 0 and migrated > 0:
                print(f"     进度: {migrated}/{len(local_rels)}")
    
    print(f"   完成: {migrated} 条")

def main():
    print("=" * 50)
    print("迁移Neo4j剩余数据")
    print("=" * 50)
    
    local = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    remote = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    
    try:
        migrate_missing_nodes(local, remote)
        migrate_missing_relationships(local, remote)
        
        # 最终验证
        print("\n3. 最终状态:")
        with local.session() as s:
            result = s.run("MATCH (n) RETURN count(n) as c")
            ln = result.single()['c']
            result = s.run("MATCH ()-[r]->() RETURN count(r) as c")
            lr = result.single()['c']
        
        with remote.session() as s:
            result = s.run("MATCH (n) RETURN count(n) as c")
            rn = result.single()['c']
            result = s.run("MATCH ()-[r]->() RETURN count(r) as c")
            rr = result.single()['c']
        
        print(f"   本地: {ln} 节点, {lr} 关系")
        print(f"   远程: {rn} 节点, {rr} 关系")
        print(f"   差异: 节点{ln-rn}, 关系{lr-rr}")
        
        if ln == rn and lr == rr:
            print("\n✅ 数据完全一致!")
        
    finally:
        local.close()
        remote.close()

if __name__ == "__main__":
    main()
