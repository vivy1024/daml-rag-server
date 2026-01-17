#!/usr/bin/env python3
"""从本地Neo4j完整迁移数据到远程Neo4j（修复版）
修复问题：
1. 使用MERGE避免重复创建
2. 修复WHERE条件的逻辑错误
3. 使用唯一标识符精确匹配节点
"""
from neo4j import GraphDatabase
import sys

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

def migrate_nodes(local_driver, remote_driver, label, batch_size=100):
    """迁移指定标签的所有节点"""
    with local_driver.session() as local_session:
        result = local_session.run(f"MATCH (n:{label}) RETURN count(n) as count")
        total = result.single()["count"]
        if total == 0:
            return 0
        
        print(f"  迁移 {label}: {total} 节点...")
        
        migrated = 0
        skip = 0
        while skip < total:
            result = local_session.run(
                f"MATCH (n:{label}) RETURN n SKIP $skip LIMIT $limit",
                skip=skip, limit=batch_size
            )
            nodes = list(result)
            
            if not nodes:
                break
            
            with remote_driver.session() as remote_session:
                for record in nodes:
                    node = record["n"]
                    props = dict(node)
                    for k, v in props.items():
                        if hasattr(v, 'iso_format'):
                            props[k] = v.iso_format()
                    
                    # 使用MERGE避免重复，基于id或name
                    if 'id' in props:
                        remote_session.run(
                            f"MERGE (n:{label} {{id: $id}}) SET n = $props",
                            id=props['id'], props=props
                        )
                    elif 'name' in props:
                        remote_session.run(
                            f"MERGE (n:{label} {{name: $name}}) SET n = $props",
                            name=props['name'], props=props
                        )
                    else:
                        remote_session.run(
                            f"CREATE (n:{label} $props)",
                            props=props
                        )
                    migrated += 1
            
            skip += batch_size
            if migrated % 500 == 0:
                print(f"    已迁移 {migrated}/{total}")
        
        print(f"    完成 {migrated}/{total}")
        return migrated

def migrate_relationships_by_type(local_driver, remote_driver, rel_type, batch_size=500):
    """迁移指定类型的关系"""
    with local_driver.session() as local_session:
        # 获取该类型关系总数
        result = local_session.run(
            f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        )
        total = result.single()["count"]
        if total == 0:
            return 0
        
        print(f"  {rel_type}: {total} 条...")
        
        migrated = 0
        failed = 0
        skip = 0
        
        while skip < total:
            result = local_session.run(
                f"""MATCH (a)-[r:{rel_type}]->(b) 
                RETURN 
                    labels(a)[0] as from_label, 
                    a.id as from_id, 
                    a.name as from_name,
                    labels(b)[0] as to_label, 
                    b.id as to_id, 
                    b.name as to_name,
                    properties(r) as props
                SKIP $skip LIMIT $limit""",
                skip=skip, limit=batch_size
            )
            rels = list(result)
            
            if not rels:
                break
            
            with remote_driver.session() as remote_session:
                for rel in rels:
                    try:
                        props = rel['props'] or {}
                        for k, v in props.items():
                            if hasattr(v, 'iso_format'):
                                props[k] = v.iso_format()
                        
                        # 构建精确匹配条件
                        from_label = rel['from_label']
                        to_label = rel['to_label']
                        
                        # 优先使用id匹配，否则用name
                        if rel['from_id'] is not None and rel['to_id'] is not None:
                            query = f"""
                            MATCH (a:{from_label} {{id: $from_id}})
                            MATCH (b:{to_label} {{id: $to_id}})
                            MERGE (a)-[r:{rel_type}]->(b)
                            SET r = $props
                            """
                            remote_session.run(query, 
                                from_id=rel['from_id'],
                                to_id=rel['to_id'],
                                props=props
                            )
                        elif rel['from_name'] and rel['to_name']:
                            query = f"""
                            MATCH (a:{from_label} {{name: $from_name}})
                            MATCH (b:{to_label} {{name: $to_name}})
                            MERGE (a)-[r:{rel_type}]->(b)
                            SET r = $props
                            """
                            remote_session.run(query, 
                                from_name=rel['from_name'],
                                to_name=rel['to_name'],
                                props=props
                            )
                        migrated += 1
                    except Exception as e:
                        failed += 1
            
            skip += batch_size
            if migrated % 1000 == 0:
                print(f"    进度: {migrated}/{total}")
        
        print(f"    完成: {migrated} 成功, {failed} 失败")
        return migrated

def main():
    print("=" * 60)
    print("Neo4j 数据迁移（修复版）")
    print("=" * 60)
    
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    remote_driver = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    
    try:
        # 检查远程状态
        print("\n检查远程数据库状态...")
        with remote_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            rels = result.single()["rels"]
            print(f"  远程: {nodes} 节点, {rels} 关系")
        
        # 检查本地状态
        print("\n检查本地数据库状态...")
        with local_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            local_nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            local_rels = result.single()["rels"]
            print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
        
        # 获取所有标签
        with local_driver.session() as session:
            result = session.run("CALL db.labels()")
            labels = [r["label"] for r in result]
        
        # 迁移节点
        print("\n" + "=" * 60)
        print("阶段1: 迁移节点")
        print("=" * 60)
        total_nodes = 0
        for label in labels:
            count = migrate_nodes(local_driver, remote_driver, label)
            total_nodes += count
        
        print(f"\n节点迁移完成: {total_nodes} 个")
        
        # 获取所有关系类型
        with local_driver.session() as session:
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [r["relationshipType"] for r in result]
        
        # 迁移关系
        print("\n" + "=" * 60)
        print("阶段2: 迁移关系")
        print("=" * 60)
        total_rels = 0
        for rel_type in rel_types:
            count = migrate_relationships_by_type(local_driver, remote_driver, rel_type)
            total_rels += count
        
        print(f"\n关系迁移完成: {total_rels} 条")
        
        # 最终验证
        print("\n" + "=" * 60)
        print("最终验证")
        print("=" * 60)
        with remote_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            final_nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            final_rels = result.single()["rels"]
            print(f"  远程数据库: {final_nodes} 节点, {final_rels} 关系")
            print(f"  本地数据库: {local_nodes} 节点, {local_rels} 关系")
            
            if final_nodes == local_nodes and final_rels == local_rels:
                print("\n✅ 迁移成功！数据完全一致")
            else:
                print(f"\n⚠️ 数据差异: 节点差{local_nodes - final_nodes}, 关系差{local_rels - final_rels}")
        
    finally:
        local_driver.close()
        remote_driver.close()

if __name__ == "__main__":
    main()
