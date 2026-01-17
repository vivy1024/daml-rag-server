#!/usr/bin/env python3
"""Neo4j生产环境迁移脚本 v2 - 使用正确的唯一键"""
from neo4j import GraphDatabase
import sys
import argparse

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

PRODUCTION_URI = "bolt://182.92.78.183:32372"
PRODUCTION_USER = "neo4j"
PRODUCTION_PASSWORD = "build_body_2024"

# 节点唯一键配置
NODE_UNIQUE_KEYS = {
    'Exercise': 'id',  # 使用id而不是exercise_id
    'Muscle': 'name_en',  # 使用name_en而不是muscle_id
    'Equipment': 'name',  # 使用name而不是equipment_id
    'Food': 'food_code',
    'Nutrient': 'name',
    'NutrientCategory': 'name',
    'StrengthStandard': 'id',  # 使用id而不是name
    'ACSMStandard': 'id',  # 使用id而不是name
    'NSCAStandard': 'id',  # 使用id而不是name
    'TrainingParams': ['goal', 'level'],  # 复合键
    'TrainingGoal': 'name',
    'TrainingLevel': 'name',
    'TrainingPhase': 'name',
    'PeriodizationModel': 'name',
    'WorkoutProgram': 'name',
    'InjuryType': 'name',
    'PosturalIssue': 'name',
    'RehabilitationPhase': 'name',
    'Joint': 'name',
    'ForceType': 'name',
    'MechanicType': 'name',
    'KineticChain': 'name',
    'GripType': 'name',
}

def get_unique_key_value(props, label):
    """获取节点的唯一键值"""
    key_config = NODE_UNIQUE_KEYS.get(label)
    
    if not key_config:
        return None
    
    # 复合键
    if isinstance(key_config, list):
        values = []
        for key in key_config:
            val = props.get(key)
            if val is None:
                return None
            values.append(str(val))
        return '|'.join(values)
    
    # 单键
    return props.get(key_config)

def export_nodes_by_label(local_driver):
    """按标签导出节点"""
    print("\n📤 从本地导出节点...")
    
    nodes_by_label = {}
    
    with local_driver.session() as session:
        # 获取所有标签
        result = session.run("CALL db.labels()")
        labels = [r[0] for r in result]
        
        for label in labels:
            result = session.run(f"""
                MATCH (n:{label})
                RETURN elementId(n) as neo4j_id, properties(n) as props
            """)
            
            nodes = []
            for record in result:
                neo4j_id = record['neo4j_id']
                props = dict(record['props'])
                unique_key = get_unique_key_value(props, label)
                
                if unique_key:
                    nodes.append({
                        'neo4j_id': neo4j_id,
                        'props': props,
                        'unique_key': unique_key
                    })
            
            if nodes:
                nodes_by_label[label] = nodes
                print(f"  ✅ {label}: {len(nodes)} 个节点")
    
    return nodes_by_label

def import_nodes_by_label(production_driver, nodes_by_label):
    """按标签导入节点并建立映射"""
    print("\n📥 导入节点到生产环境...")
    
    # 本地neo4j_id -> 生产neo4j_id
    id_mapping = {}
    # label -> unique_key -> 生产neo4j_id
    key_mapping = {}
    
    with production_driver.session() as session:
        for label, nodes in nodes_by_label.items():
            print(f"  导入 {label}: {len(nodes)} 个")
            
            key_mapping[label] = {}
            
            for node in nodes:
                # 创建节点
                result = session.run(f"""
                    CREATE (n:{label})
                    SET n = $props
                    RETURN elementId(n) as new_id
                """, props=node['props'])
                
                new_id = result.single()['new_id']
                
                # 建立映射
                id_mapping[node['neo4j_id']] = new_id
                key_mapping[label][node['unique_key']] = new_id
            
            print(f"  ✅ 完成 {label}")
    
    return id_mapping, key_mapping

def export_relationships(local_driver):
    """导出所有关系"""
    print("\n📤 从本地导出关系...")
    
    with local_driver.session() as session:
        result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN 
                elementId(a) as start_neo4j_id,
                labels(a) as start_labels,
                properties(a) as start_props,
                elementId(b) as end_neo4j_id,
                labels(b) as end_labels,
                properties(b) as end_props,
                type(r) as rel_type,
                properties(r) as rel_props
        """)
        
        rels = []
        for record in result:
            start_label = record['start_labels'][0] if record['start_labels'] else None
            end_label = record['end_labels'][0] if record['end_labels'] else None
            
            start_key = get_unique_key_value(dict(record['start_props']), start_label)
            end_key = get_unique_key_value(dict(record['end_props']), end_label)
            
            rels.append({
                'start_neo4j_id': record['start_neo4j_id'],
                'start_label': start_label,
                'start_key': start_key,
                'end_neo4j_id': record['end_neo4j_id'],
                'end_label': end_label,
                'end_key': end_key,
                'rel_type': record['rel_type'],
                'rel_props': dict(record['rel_props']) if record['rel_props'] else {}
            })
        
        print(f"  ✅ 导出 {len(rels)} 条关系")
    
    return rels

def import_relationships(production_driver, rels, id_mapping, key_mapping):
    """导入关系到生产环境"""
    print("\n📥 导入关系到生产环境...")
    
    rels_by_type = {}
    for rel in rels:
        rel_type = rel['rel_type']
        if rel_type not in rels_by_type:
            rels_by_type[rel_type] = []
        rels_by_type[rel_type].append(rel)
    
    total_success = 0
    total_failed = 0
    
    with production_driver.session() as session:
        for rel_type, type_rels in rels_by_type.items():
            print(f"  导入 {rel_type}: {len(type_rels)} 条")
            
            success = 0
            failed = 0
            
            for rel in type_rels:
                try:
                    # 优先使用唯一键映射
                    start_id = None
                    end_id = None
                    
                    if rel['start_key'] and rel['start_label'] in key_mapping:
                        start_id = key_mapping[rel['start_label']].get(rel['start_key'])
                    
                    if rel['end_key'] and rel['end_label'] in key_mapping:
                        end_id = key_mapping[rel['end_label']].get(rel['end_key'])
                    
                    # 回退到ID映射
                    if not start_id:
                        start_id = id_mapping.get(rel['start_neo4j_id'])
                    if not end_id:
                        end_id = id_mapping.get(rel['end_neo4j_id'])
                    
                    if not start_id or not end_id:
                        failed += 1
                        continue
                    
                    # 创建关系
                    session.run(f"""
                        MATCH (a), (b)
                        WHERE elementId(a) = $start_id AND elementId(b) = $end_id
                        CREATE (a)-[r:{rel_type}]->(b)
                        SET r = $props
                    """, start_id=start_id, end_id=end_id, props=rel['rel_props'])
                    
                    success += 1
                    
                except Exception as e:
                    failed += 1
            
            print(f"  ✅ {rel_type}: 成功 {success}, 失败 {failed}")
            total_success += success
            total_failed += failed
    
    print(f"\n  总计: 成功 {total_success}, 失败 {total_failed}")
    return total_success, total_failed

def main():
    parser = argparse.ArgumentParser(description='Neo4j生产环境迁移 v2')
    parser.add_argument('--force', action='store_true', help='强制清空生产环境')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Neo4j生产环境迁移 v2 - 使用正确唯一键")
    print("=" * 60)
    
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    prod_driver = GraphDatabase.driver(PRODUCTION_URI, auth=(PRODUCTION_USER, PRODUCTION_PASSWORD))
    
    try:
        # 检查初始状态
        print("\n📊 初始状态:")
        local_nodes, local_rels = get_stats(local_driver, "本地")
        prod_nodes, prod_rels = get_stats(prod_driver, "生产")
        print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
        print(f"  生产: {prod_nodes} 节点, {prod_rels} 关系")
        
        if prod_nodes > 0:
            if not args.force:
                print("\n⚠️  生产环境已有数据，使用 --force 强制清空")
                return
            
            print("\n🗑️  清空生产环境...")
            with prod_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            print("  ✅ 清空完成")
        
        # 导出本地数据
        nodes_by_label = export_nodes_by_label(local_driver)
        rels = export_relationships(local_driver)
        
        # 导入到生产环境
        id_mapping, key_mapping = import_nodes_by_label(prod_driver, nodes_by_label)
        success, failed = import_relationships(prod_driver, rels, id_mapping, key_mapping)
        
        # 验证最终状态
        print("\n📊 最终状态:")
        local_nodes, local_rels = get_stats(local_driver, "本地")
        prod_nodes, prod_rels = get_stats(prod_driver, "生产")
        print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
        print(f"  生产: {prod_nodes} 节点, {prod_rels} 关系")
        
        if local_nodes == prod_nodes:
            print(f"\n✅ 节点迁移成功: {prod_nodes}/{local_nodes} (100%)")
        else:
            print(f"\n⚠️  节点差异: {prod_nodes}/{local_nodes}")
        
        success_rate = (success / local_rels * 100) if local_rels > 0 else 0
        print(f"✅ 关系迁移: {success}/{local_rels} ({success_rate:.1f}%)")
        
        if failed > 0:
            print(f"⚠️  失败关系: {failed} 条")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        local_driver.close()
        prod_driver.close()

def get_stats(driver, env_name):
    """获取数据库统计信息"""
    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
    return node_count, rel_count

def get_element_id(session, node_id):
    """将旧的id()转换为elementId()"""
    # Neo4j 5.x使用elementId()替代id()
    return node_id

if __name__ == "__main__":
    main()
