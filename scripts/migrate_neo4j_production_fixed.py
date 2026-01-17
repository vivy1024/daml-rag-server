#!/usr/bin/env python3
"""迁移Neo4j数据到生产环境 - 支持复合唯一键"""
from neo4j import GraphDatabase
import sys
import argparse

LOCAL_URI = "bolt://fitness_neo4j:7687"
PRODUCTION_URI = "bolt://182.92.78.183:32372"
AUTH = ("neo4j", "build_body_2024")

# 定义每种节点类型的唯一标识属性
NODE_UNIQUE_KEYS = {
    'Exercise': ['id'],
    'Muscle': ['name_en'],
    'Equipment': ['name'],
    'Food': ['food_code'],
    'Nutrient': ['name'],
    'NutrientCategory': ['name'],
    'TrainingGoal': ['name'],
    'TrainingLevel': ['name'],
    'TrainingParams': ['goal', 'level'],  # 复合键
    'MechanicType': ['name'],
    'ForceType': ['name'],
    'GripType': ['name'],
    'KineticChain': ['name'],
    'InjuryType': ['name'],
    'PosturalIssue': ['name'],
    'Joint': ['name'],
    'StrengthStandard': ['id'],
    'WorkoutProgram': ['name'],
    'TrainingPhase': ['name'],
    'PeriodizationModel': ['name'],
    'RehabilitationPhase': ['name'],
    'ACSMStandard': ['id'],
    'NSCAStandard': ['id'],
}

def get_stats(driver):
    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
    return node_count, rel_count

def build_match_clause(label, keys, props):
    """构建MATCH子句（支持复合键）"""
    conditions = []
    params = {}
    for key in keys:
        value = props.get(key)
        if value is None:
            return None, None
        conditions.append(f"{key}: ${key}")
        params[key] = value
    
    match_str = ", ".join(conditions)
    return f"MERGE (n:{label} {{{match_str}}})", params

def import_nodes_by_label(production_driver, label, nodes, unique_keys):
    """导入节点（支持复合键）"""
    if not nodes:
        return 0
    
    success_count = 0
    with production_driver.session() as session:
        for props in nodes:
            try:
                merge_clause, params = build_match_clause(label, unique_keys, props)
                if merge_clause is None:
                    continue
                
                params['props'] = props
                session.run(f"{merge_clause} SET n = $props", **params)
                success_count += 1
            except Exception as e:
                if success_count == 0:  # 只打印第一个错误
                    print(f"    ⚠️  错误: {e}")
    
    return success_count

def import_relationships_by_type(production_driver, rel_type, rels):
    """导入关系（支持复合键）"""
    if not rels:
        return 0
    
    success_count = 0
    with production_driver.session() as session:
        for rel in rels:
            try:
                start_label = rel['start_label']
                end_label = rel['end_label']
                start_keys = NODE_UNIQUE_KEYS.get(start_label, ['name'])
                end_keys = NODE_UNIQUE_KEYS.get(end_label, ['name'])
                
                # 构建起始节点匹配条件
                start_conditions = []
                start_params = {}
                for key in start_keys:
                    value = rel['start_props'].get(key)
                    if value is None:
                        break
                    start_conditions.append(f"{key}: $start_{key}")
                    start_params[f"start_{key}"] = value
                
                if len(start_conditions) != len(start_keys):
                    continue
                
                # 构建结束节点匹配条件
                end_conditions = []
                end_params = {}
                for key in end_keys:
                    value = rel['end_props'].get(key)
                    if value is None:
                        break
                    end_conditions.append(f"{key}: $end_{key}")
                    end_params[f"end_{key}"] = value
                
                if len(end_conditions) != len(end_keys):
                    continue
                
                start_match = ", ".join(start_conditions)
                end_match = ", ".join(end_conditions)
                
                params = {**start_params, **end_params, 'rel_props': rel['rel_props']}
                
                session.run(f"""
                    MATCH (a:{start_label} {{{start_match}}})
                    MATCH (b:{end_label} {{{end_match}}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r = $rel_props
                """, **params)
                
                success_count += 1
            except Exception as e:
                if success_count % 10000 == 0:
                    print(f"    ⚠️  错误: {e}")
    
    return success_count

def main():
    parser = argparse.ArgumentParser(description='迁移Neo4j数据到生产环境')
    parser.add_argument('--force', action='store_true', help='强制清空生产环境')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Neo4j生产环境数据迁移（支持复合键）")
    print("=" * 60)
    
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=AUTH)
    production_driver = GraphDatabase.driver(PRODUCTION_URI, auth=AUTH)
    
    try:
        # 检查初始状态
        print("\n📊 初始状态:")
        local_nodes, local_rels = get_stats(local_driver)
        prod_nodes, prod_rels = get_stats(production_driver)
        print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
        print(f"  生产: {prod_nodes} 节点, {prod_rels} 关系")
        
        if prod_nodes > 0 and not args.force:
            print("\n⚠️  生产环境已有数据，使用 --force 强制清空")
            return
        
        if args.force and prod_nodes > 0:
            print("\n🗑️  清空生产环境...")
            with production_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            print("  ✅ 完成")
        
        # 获取所有标签
        with local_driver.session() as session:
            labels = [r[0] for r in session.run("CALL db.labels()")]
            rel_types = [r[0] for r in session.run("CALL db.relationshipTypes()")]
        
        print(f"\n📋 数据结构: {len(labels)} 节点类型, {len(rel_types)} 关系类型")
        
        # 导入节点
        print("\n📥 导入节点...")
        total_imported = 0
        for label in labels:
            unique_keys = NODE_UNIQUE_KEYS.get(label, ['name'])
            
            with local_driver.session() as session:
                nodes = [r['props'] for r in session.run(f"MATCH (n:{label}) RETURN properties(n) as props")]
            
            if nodes:
                count = import_nodes_by_label(production_driver, label, nodes, unique_keys)
                key_str = "+".join(unique_keys)
                print(f"  {label} ({key_str}): {len(nodes)} → {count}")
                total_imported += count
        
        print(f"\n  ✅ 总计: {total_imported} 节点")
        
        # 导入关系
        print("\n📥 导入关系...")
        total_rels = 0
        for rel_type in rel_types:
            with local_driver.session() as session:
                rels = []
                result = session.run(f"""
                    MATCH (a)-[r:{rel_type}]->(b)
                    RETURN labels(a)[0] as start_label, labels(b)[0] as end_label,
                           properties(a) as start_props, properties(b) as end_props,
                           properties(r) as rel_props
                """)
                for record in result:
                    rels.append({
                        'start_label': record['start_label'],
                        'end_label': record['end_label'],
                        'start_props': record['start_props'],
                        'end_props': record['end_props'],
                        'rel_props': record['rel_props'] or {}
                    })
            
            if rels:
                count = import_relationships_by_type(production_driver, rel_type, rels)
                print(f"  {rel_type}: {len(rels)} → {count}")
                total_rels += count
        
        print(f"\n  ✅ 总计: {total_rels} 关系")
        
        # 最终验证
        print("\n📊 最终状态:")
        local_nodes, local_rels = get_stats(local_driver)
        prod_nodes, prod_rels = get_stats(production_driver)
        print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
        print(f"  生产: {prod_nodes} 节点, {prod_rels} 关系")
        
        if local_nodes == prod_nodes and local_rels == prod_rels:
            print("\n✅ 迁移成功！")
        else:
            print(f"\n⚠️  差异: 节点 {prod_nodes}/{local_nodes}, 关系 {prod_rels}/{local_rels}")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        local_driver.close()
        production_driver.close()

if __name__ == "__main__":
    main()
