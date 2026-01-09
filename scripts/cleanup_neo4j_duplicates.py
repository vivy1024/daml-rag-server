#!/usr/bin/env python3
"""清理远程Neo4j中的重复数据，使其与本地一致"""
from neo4j import GraphDatabase

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

def cleanup_duplicate_nodes(remote_driver, local_driver, label):
    """清理重复节点，保留与本地一致的数据"""
    # 获取本地节点的唯一标识
    with local_driver.session() as local_session:
        result = local_session.run(f"""
            MATCH (n:{label})
            RETURN n.id as id, n.name as name, n.name_zh as name_zh
        """)
        local_keys = set()
        for r in result:
            if r['id']:
                local_keys.add(('id', r['id']))
            elif r['name']:
                local_keys.add(('name', r['name']))
            elif r['name_zh']:
                local_keys.add(('name_zh', r['name_zh']))
    
    # 获取远程节点
    with remote_driver.session() as remote_session:
        result = remote_session.run(f"""
            MATCH (n:{label})
            RETURN elementId(n) as eid, n.id as id, n.name as name, n.name_zh as name_zh
        """)
        remote_nodes = list(result)
    
    # 找出需要删除的节点
    to_delete = []
    seen_keys = set()
    for node in remote_nodes:
        key = None
        if node['id']:
            key = ('id', node['id'])
        elif node['name']:
            key = ('name', node['name'])
        elif node['name_zh']:
            key = ('name_zh', node['name_zh'])
        
        if key:
            if key in seen_keys or key not in local_keys:
                to_delete.append(node['eid'])
            else:
                seen_keys.add(key)
    
    # 删除重复节点
    if to_delete:
        with remote_driver.session() as remote_session:
            for eid in to_delete:
                remote_session.run("MATCH (n) WHERE elementId(n) = $eid DETACH DELETE n", eid=eid)
        print(f"  {label}: 删除 {len(to_delete)} 个重复节点")
    else:
        print(f"  {label}: 无重复")
    
    return len(to_delete)

def cleanup_duplicate_relationships(remote_driver, rel_type):
    """删除重复关系，保留唯一的"""
    with remote_driver.session() as session:
        # 统计重复关系
        result = session.run(f"""
            MATCH (a)-[r:{rel_type}]->(b)
            WITH a, b, type(r) as rel_type, collect(r) as rels
            WHERE size(rels) > 1
            RETURN count(*) as duplicate_pairs
        """)
        dup_count = result.single()["duplicate_pairs"]
        
        if dup_count > 0:
            # 删除重复关系，保留第一个
            result = session.run(f"""
                MATCH (a)-[r:{rel_type}]->(b)
                WITH a, b, collect(r) as rels
                WHERE size(rels) > 1
                UNWIND rels[1..] as dup
                DELETE dup
                RETURN count(*) as deleted
            """)
            deleted = result.single()["deleted"]
            print(f"  {rel_type}: 删除 {deleted} 条重复关系")
            return deleted
        else:
            print(f"  {rel_type}: 无重复")
            return 0

def main():
    print("=" * 60)
    print("清理远程Neo4j重复数据")
    print("=" * 60)
    
    remote_driver = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    
    try:
        # 清理前统计
        print("\n清理前状态:")
        with remote_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            nodes_before = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            rels_before = result.single()["rels"]
            print(f"  远程: {nodes_before} 节点, {rels_before} 关系")
        
        # 清理重复节点
        print("\n【清理重复节点】")
        problem_labels = ['Muscle', 'TrainingParams']
        for label in problem_labels:
            cleanup_duplicate_nodes(remote_driver, local_driver, label)
        
        # 清理重复关系
        print("\n【清理重复关系】")
        problem_rels = ['TARGETS_PRIMARY', 'FOR_GOAL', 'FOR_LEVEL']
        for rel_type in problem_rels:
            cleanup_duplicate_relationships(remote_driver, rel_type)
        
        # 清理后统计
        print("\n清理后状态:")
        with remote_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            nodes_after = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            rels_after = result.single()["rels"]
            print(f"  远程: {nodes_after} 节点, {rels_after} 关系")
            print(f"  清理: {nodes_before - nodes_after} 节点, {rels_before - rels_after} 关系")
        
        # 与本地对比
        print("\n与本地对比:")
        with local_driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            local_nodes = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            local_rels = result.single()["rels"]
            print(f"  本地: {local_nodes} 节点, {local_rels} 关系")
            print(f"  远程: {nodes_after} 节点, {rels_after} 关系")
            print(f"  差异: 节点{local_nodes - nodes_after}, 关系{local_rels - rels_after}")
        
    finally:
        remote_driver.close()
        local_driver.close()

if __name__ == "__main__":
    main()
