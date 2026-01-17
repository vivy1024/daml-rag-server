#!/usr/bin/env python3
"""完整迁移Neo4j数据 - 使用多种匹配策略"""
from neo4j import GraphDatabase
import sys

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

def get_node_key(node, label):
    """获取节点的唯一标识键"""
    props = dict(node)
    # 优先级: id > name > name_zh > 所有属性组合
    if 'id' in props and props['id']:
        return ('id', props['id'])
    if 'name' in props and props['name']:
        return ('name', props['name'])
    if 'name_zh' in props and props['name_zh']:
        return ('name_zh', props['name_zh'])
    # 使用所有属性的hash作为key
    key_str = str(sorted([(k, str(v)[:50]) for k, v in props.items()]))
    return ('_hash', hash(key_str))

def migrate_missing_relationships(local_driver, remote_driver, rel_type, batch_size=200):
    """迁移缺失的关系类型"""
    with local_driver.session() as local_session:
        result = local_session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as c")
        total = result.single()["c"]
        if total == 0:
            return 0
        
        print(f"\n迁移 {rel_type}: {total} 条")
        
        # 获取所有关系及其完整节点信息
        result = local_session.run(f"""
            MATCH (a)-[r:{rel_type}]->(b)
            RETURN 
                labels(a)[0] as from_label,
                properties(a) as from_props,
                labels(b)[0] as to_label,
                properties(b) as to_props,
                properties(r) as rel_props
        """)
        all_rels = list(result)
    
    migrated = 0
    failed = 0
    
    with remote_driver.session() as remote_session:
        for rel in all_rels:
            try:
                from_label = rel['from_label']
                to_label = rel['to_label']
                from_props = rel['from_props'] or {}
                to_props = rel['to_props'] or {}
                rel_props = rel['rel_props'] or {}
                
                # 构建匹配条件
                from_match = build_match_condition(from_props, 'a')
                to_match = build_match_condition(to_props, 'b')
                
                if from_match and to_match:
                    query = f"""
                    MATCH (a:{from_label}) WHERE {from_match}
                    MATCH (b:{to_label}) WHERE {to_match}
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r = $rel_props
                    """
                    remote_session.run(query, rel_props=rel_props)
                    migrated += 1
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
            
            if (migrated + failed) % 500 == 0:
                print(f"  进度: {migrated} 成功, {failed} 失败")
    
    print(f"  完成: {migrated} 成功, {failed} 失败")
    return migrated

def build_match_condition(props, var):
    """构建节点匹配条件"""
    conditions = []
    
    # 优先使用唯一标识
    if 'id' in props and props['id']:
        return f"{var}.id = {repr(props['id'])}"
    
    if 'name' in props and props['name']:
        return f"{var}.name = {repr(props['name'])}"
    
    if 'name_zh' in props and props['name_zh']:
        return f"{var}.name_zh = {repr(props['name_zh'])}"
    
    # 使用多个属性组合匹配
    for key in ['name_en', 'exercise_id', 'food_id', 'muscle_id']:
        if key in props and props[key]:
            conditions.append(f"{var}.{key} = {repr(props[key])}")
    
    if conditions:
        return " AND ".join(conditions)
    
    # 最后尝试使用所有非空属性
    for key, val in props.items():
        if val and isinstance(val, (str, int, float)) and len(str(val)) < 100:
            conditions.append(f"{var}.{key} = {repr(val)}")
            if len(conditions) >= 3:
                break
    
    return " AND ".join(conditions) if conditions else None

def main():
    print("=" * 60)
    print("Neo4j 完整数据迁移")
    print("=" * 60)
    
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    remote_driver = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    
    try:
        # 需要迁移的关系类型（按缺失数量排序）
        missing_rel_types = [
            'REQUIRES',
            'SUITABLE_FOR_LEVEL', 
            'CONTRAINDICATED_FOR',
            'USES_FORCE',
            'HAS_MECHANIC',
            'HAS_KINETIC_CHAIN',
            'USES_GRIP',
            'FOR_GOAL',
            'FOR_LEVEL',
            'CORRECTS',
            'AGGRAVATES',
            'TARGETS_PRIMARY',
            'CONTAINS_NUTRIENT'
        ]
        
        total_migrated = 0
        for rel_type in missing_rel_types:
            count = migrate_missing_relationships(local_driver, remote_driver, rel_type)
            total_migrated += count
        
        # 最终验证
        print("\n" + "=" * 60)
        print("最终验证")
        print("=" * 60)
        
        with local_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            local_nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            local_rels = result.single()["rels"]
        
        with remote_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            remote_nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            remote_rels = result.single()["rels"]
        
        print(f"本地: {local_nodes} 节点, {local_rels} 关系")
        print(f"远程: {remote_nodes} 节点, {remote_rels} 关系")
        print(f"差异: 节点{local_nodes - remote_nodes}, 关系{local_rels - remote_rels}")
        
    finally:
        local_driver.close()
        remote_driver.close()

if __name__ == "__main__":
    main()
