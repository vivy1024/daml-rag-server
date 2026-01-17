#!/usr/bin/env python3
"""最终迁移Neo4j - 使用正确的属性匹配"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

def migrate_food_nodes(local, remote):
    """迁移Food节点（使用food_code匹配）"""
    print("\n1. 迁移Food节点...")
    
    # 获取本地所有Food
    with local.session() as s:
        result = s.run("MATCH (f:Food) RETURN f.food_code as code, properties(f) as props")
        local_foods = {r['code']: r['props'] for r in result if r['code']}
    print(f"   本地Food: {len(local_foods)}")
    
    # 获取远程Food
    with remote.session() as s:
        result = s.run("MATCH (f:Food) RETURN f.food_code as code")
        remote_codes = set(r['code'] for r in result if r['code'])
    print(f"   远程Food: {len(remote_codes)}")
    
    # 迁移缺失的
    missing = set(local_foods.keys()) - remote_codes
    print(f"   缺失: {len(missing)}")
    
    if missing:
        with remote.session() as s:
            for code in missing:
                props = local_foods[code]
                s.run("CREATE (f:Food) SET f = $props", props=props)
        print(f"   已迁移 {len(missing)} 个Food节点")

def migrate_training_params(local, remote):
    """迁移TrainingParams节点"""
    print("\n2. 迁移TrainingParams节点...")
    
    # 获取本地所有TrainingParams
    with local.session() as s:
        result = s.run("MATCH (t:TrainingParams) RETURN properties(t) as props")
        local_params = [r['props'] for r in result]
    print(f"   本地: {len(local_params)}")
    
    # 清空远程并重新创建
    with remote.session() as s:
        s.run("MATCH (t:TrainingParams) DETACH DELETE t")
        for props in local_params:
            s.run("CREATE (t:TrainingParams) SET t = $props", props=props)
    print(f"   已迁移 {len(local_params)} 个TrainingParams节点")

def migrate_contains_nutrient(local, remote):
    """迁移CONTAINS_NUTRIENT关系"""
    print("\n3. 迁移CONTAINS_NUTRIENT关系...")
    
    with local.session() as s:
        result = s.run("""
            MATCH (f:Food)-[r:CONTAINS_NUTRIENT]->(n:Nutrient)
            RETURN f.food_code as food_code, n.name as nutrient_name, properties(r) as props
        """)
        local_rels = list(result)
    print(f"   本地: {len(local_rels)} 条")
    
    migrated = 0
    with remote.session() as s:
        for rel in local_rels:
            try:
                s.run("""
                    MATCH (f:Food {food_code: $food_code})
                    MATCH (n:Nutrient {name: $nutrient_name})
                    MERGE (f)-[r:CONTAINS_NUTRIENT]->(n)
                    SET r = $props
                """, food_code=rel['food_code'], nutrient_name=rel['nutrient_name'],
                   props=rel['props'] or {})
                migrated += 1
            except:
                pass
            if migrated % 5000 == 0 and migrated > 0:
                print(f"     进度: {migrated}")
    print(f"   完成: {migrated} 条")

def main():
    print("=" * 50)
    print("Neo4j最终数据迁移")
    print("=" * 50)
    
    local = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    remote = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    
    try:
        migrate_food_nodes(local, remote)
        migrate_training_params(local, remote)
        migrate_contains_nutrient(local, remote)
        
        # 最终验证
        print("\n4. 最终状态:")
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
        
        if ln == rn and lr == rr:
            print("\n✅ 数据完全一致!")
        else:
            print(f"   差异: 节点{ln-rn}, 关系{lr-rr}")
        
    finally:
        local.close()
        remote.close()

if __name__ == "__main__":
    main()
