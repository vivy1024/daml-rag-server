#!/usr/bin/env python3
"""专门迁移Neo4j关系的脚本 - 优化版"""
from neo4j import GraphDatabase
import time

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

def get_node_key(node_labels, node_props):
    """获取节点的唯一标识键"""
    # 优先使用id，其次name，最后name_zh
    if 'id' in node_props and node_props['id'] is not None:
        return ('id', node_props['id'])
    if 'name' in node_props and node_props['name']:
        return ('name', node_props['name'])
    if 'name_zh' in node_props and node_props['name_zh']:
        return ('name_zh', node_props['name_zh'])
    return None

def migrate_relationships_by_type(local_driver, remote_driver, rel_type, batch_size=200):
    """迁移指定类型的所有关系"""
    with local_driver.session() as local_session:
        # 获取该类型关系总数
        result = local_session.run(
            f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        )
        total = result.single()["count"]
        
        if total == 0:
            return 0
        
        print(f"  {rel_type}: {total} 条关系")
        
        migrated = 0
        errors = 0
        skip = 0
        
        while skip < total:
            # 获取一批关系
            result = local_session.run(f"""
                MATCH (a)-[r:{rel_type}]->(b)
                RETURN 
                    labels(a) as from_labels,
                    properties(a) as from_props,
                    labels(b) as to_labels,
                    properties(b) as to_props,
                    properties(r) as rel_props
                SKIP $skip LIMIT $limit
            """, skip=skip, limit=batch_size)
            
            rels = list(result)
            if not rels:
                break
            
            # 批量创建关系
            with remote_driver.session() as remote_session:
                for rel in rels:
                    try:
                        from_label = rel['from_labels'][0] if rel['from_labels'] else 'Node'
                        to_label = rel['to_labels'][0] if rel['to_labels'] else 'Node'
                        from_key = get_node_key(rel['from_labels'], rel['from_props'])
                        to_key = get_node_key(rel['to_labels'], rel['to_props'])
                        
                        if not from_key or not to_key:
                            errors += 1
                            continue
                        
                        # 处理属性中的特殊类型
                        rel_props = rel['rel_props'] or {}
                        for k, v in list(rel_props.items()):
                            if hasattr(v, 'iso_format'):
                                rel_props[k] = v.iso_format()
                        
                        # 构建查询
                        query = f"""
                        MATCH (a:{from_label} {{{from_key[0]}: $from_val}})
                        MATCH (b:{to_label} {{{to_key[0]}: $to_val}})
                        MERGE (a)-[r:{rel_type}]->(b)
                        SET r = $props
                        """
                        
                        remote_session.run(query,
                            from_val=from_key[1],
                            to_val=to_key[1],
                            props=rel_props
                        )
                        migrated += 1
                        
                    except Exception as e:
                        errors += 1
            
            skip += batch_size
            print(f"    进度: {skip}/{total}, 成功: {migrated}, 失败: {errors}")
        
        return migrated

def main():
    print("连接数据库...")
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    remote_driver = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    
    try:
        # 检查当前状态
        print("\n检查远程数据库当前状态...")
        with remote_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            rels = result.single()["rels"]
            print(f"远程: {nodes} 节点, {rels} 关系")
        
        with local_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            local_nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            local_rels = result.single()["rels"]
            print(f"本地: {local_nodes} 节点, {local_rels} 关系")
        
        # 获取所有关系类型
        with local_driver.session() as session:
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [r["relationshipType"] for r in result]
        
        print(f"\n关系类型: {rel_types}")
        print("\n开始迁移关系...")
        
        total_migrated = 0
        start_time = time.time()
        
        for rel_type in rel_types:
            count = migrate_relationships_by_type(local_driver, remote_driver, rel_type)
            total_migrated += count
        
        elapsed = time.time() - start_time
        print(f"\n关系迁移完成!")
        print(f"总计迁移: {total_migrated} 条关系")
        print(f"耗时: {elapsed:.1f} 秒")
        
        # 最终验证
        print("\n最终验证...")
        with remote_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            rels = result.single()["rels"]
            print(f"远程数据库: {nodes} 节点, {rels} 关系")
        
    finally:
        local_driver.close()
        remote_driver.close()

if __name__ == "__main__":
    main()
