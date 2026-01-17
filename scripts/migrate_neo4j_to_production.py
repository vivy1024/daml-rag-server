
#!/usr/bin/env python3
"""迁移Neo4j数据到生产环境（使用正确端口32372）"""
from neo4j import GraphDatabase
import sys
import argparse

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

PRODUCTION_URI = "bolt://182.92.78.183:32372"
PRODUCTION_USER = "neo4j"
PRODUCTION_PASSWORD = "build_body_2024"

def get_stats(driver, env_name):
    """获取数据库统计信息"""
    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
    return node_count, rel_count

def export_all_data(local_driver):
    """从本地导出所有数据"""
    print("\n📤 从本地导出数据...")
    
    with local_driver.session() as session:
        # 导出所有节点
        print("  导出节点...")
        nodes_result = session.run("""
            MATCH (n)
            RETURN id(n) as id, labels(n) as labels, properties(n) as props
        """)
        nodes = list(nodes_result)
        print(f"  ✅ 导出 {len(nodes)} 个节点")
        
        # 导出所有关系
        print("  导出关系...")
        rels_result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN id(a) as start_id, id(b) as end_id, 
                   type(r) as type, properties(r) as props
        """)
        rels = list(rels_result)
        print(f"  ✅ 导出 {len(rels)} 条关系")
    
    return nodes, rels

def import_nodes(production_driver, nodes):
    """导入节点到生产环境"""
    print("\n📥 导入节点到生产环境...")
    
    # 按节点类型分组
    nodes_by_label = {}
    for node in nodes:
        label = node['labels'][0] if node['labels'] else 'Unknown'
        if label not in nodes_by_label:
            nodes_by_label[label] = []
        nodes_by_label[label].append(node)
    
    id_mapping = {}  # 本地ID -> 生产环境ID映射
    
    with production_driver.session() as session:
        for label, label_nodes in nodes_by_label.items():
            print(f"  导入 {label} 节点: {len(label_nodes)} 个")
            
            for node in label_nodes:
                # 创建节点并获取新ID
                result = session.run(f"""
                    CREATE (n:{label})
                    SET n = $props
                    RETURN id(n) as new_id
                """, props=node['props'])
                
                new_id = result.single()['new_id']
                id_mapping[node['id']] = new_id
            
            print(f"  ✅ 完成 {label}")
    
    return id_mapping

def import_relationships(production_driver, rels, id_mapping):
    """导入关系到生产环境"""
    print("\n📥 导入关系到生产环境...")
    
    # 按关系类型分组
    rels_by_type = {}
    for rel in rels:
        rel_type = rel['type']
        if rel_type not in rels_by_type:
            rels_by_type[rel_type] = []
        rels_by_type[rel_type].append(rel)
    
    with production_driver.session() as session:
        for rel_type, type_rels in rels_by_type.items():
            print(f"  导入 {rel_type} 关系: {len(type_rels)} 条")
            
            success_count = 0
            for rel in type_rels:
                try:
                    # 使用映射后的ID创建关系
                    start_id = id_mapping.get(rel['start_id'])
                    end_id = id_mapping.get(rel['end_id'])
                    
                    if start_id is None or end_id is None:
                        continue
                    
                    session.run(f"""
                        MATCH (a), (b)
                        WHERE id(a) = $start_id AND id(b) = $end_id
                        CREATE (a)-[r:{rel_type}]->(b)
                        SET r = $props
                    """, start_id=start_id, end_id=end_id, props=rel['props'] or {})
                    
                    success_count += 1
                except Exception as e:
                    print(f"    ⚠️  跳过关系: {e}")
            
            print(f"  ✅ 完成 {rel_type}: {success_count}/{len(type_rels)}")

def main():
    parser = argparse.ArgumentParser(description='迁移Neo4j数据到生产环境')
    parser.add_argument('--force', action='store_true', help='强制清空生产环境并重新导入')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Neo4j生产环境数据迁移")
    print("=" * 60)
    print(f"本地: {LOCAL_URI}")
    print(f"生产: {PRODUCTION_URI}")
    print("=" * 60)
    
    # 连接数据库
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    production_driver = GraphDatabase.driver(PRODUCTION_URI, auth=(PRODUCTION_USER, PRODUCTION_PASSWORD))
    
    try:
        # 检查初始状态
        print("\n📊 初始状态:")
        local_nodes, local_rels = get_stats(local_driver, "本地")
        prod_nodes, prod_rels = get_stats(production_driver, "生产")
        print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
        print(f"  生产: {prod_nodes} 节点, {prod_rels} 关系")
        
        if prod_nodes > 0:
            if not args.force:
                print("\n⚠️  生产环境已有数据，使用 --force 参数强制清空并重新导入")
                print("❌ 取消迁移")
                return
            
            print("\n🗑️  清空生产环境数据...")
            with production_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            print("  ✅ 清空完成")
        
        # 导出本地数据
        nodes, rels = export_all_data(local_driver)
        
        # 导入到生产环境
        id_mapping = import_nodes(production_driver, nodes)
        import_relationships(production_driver, rels, id_mapping)
        
        # 验证最终状态
        print("\n📊 最终状态:")
        local_nodes, local_rels = get_stats(local_driver, "本地")
        prod_nodes, prod_rels = get_stats(production_driver, "生产")
        print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
        print(f"  生产: {prod_nodes} 节点, {prod_rels} 关系")
        
        if local_nodes == prod_nodes and local_rels == prod_rels:
            print("\n✅ 迁移成功！数据完全一致")
        else:
            print(f"\n⚠️  数据不完全一致")
            print(f"  节点差异: {local_nodes - prod_nodes}")
            print(f"  关系差异: {local_rels - prod_rels}")
        
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
