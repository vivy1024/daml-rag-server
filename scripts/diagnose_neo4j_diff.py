#!/usr/bin/env python3
"""诊断Neo4j本地和远程数据库的差异"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

REMOTE_URI = "bolt://182.92.78.183:32633"
REMOTE_USER = "neo4j"
REMOTE_PASSWORD = "build_body_2024"

def main():
    print("=" * 60)
    print("Neo4j 数据差异诊断")
    print("=" * 60)
    
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    remote_driver = GraphDatabase.driver(REMOTE_URI, auth=(REMOTE_USER, REMOTE_PASSWORD))
    
    try:
        # 1. 按标签统计节点
        print("\n【节点统计】")
        print("-" * 40)
        with local_driver.session() as local_session:
            result = local_session.run("CALL db.labels()")
            labels = [r["label"] for r in result]
        
        for label in labels:
            with local_driver.session() as local_session:
                result = local_session.run(f"MATCH (n:{label}) RETURN count(n) as c")
                local_count = result.single()["c"]
            
            with remote_driver.session() as remote_session:
                result = remote_session.run(f"MATCH (n:{label}) RETURN count(n) as c")
                remote_count = result.single()["c"]
            
            diff = local_count - remote_count
            status = "✅" if diff == 0 else f"⚠️ 差{diff}"
            print(f"  {label}: 本地{local_count} / 远程{remote_count} {status}")
        
        # 2. 按类型统计关系
        print("\n【关系统计】")
        print("-" * 40)
        with local_driver.session() as local_session:
            result = local_session.run("CALL db.relationshipTypes()")
            rel_types = [r["relationshipType"] for r in result]
        
        missing_types = []
        for rel_type in rel_types:
            with local_driver.session() as local_session:
                result = local_session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as c")
                local_count = result.single()["c"]
            
            with remote_driver.session() as remote_session:
                result = remote_session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as c")
                remote_count = result.single()["c"]
            
            diff = local_count - remote_count
            status = "✅" if diff == 0 else f"⚠️ 差{diff}"
            print(f"  {rel_type}: 本地{local_count} / 远程{remote_count} {status}")
            
            if diff > 0:
                missing_types.append((rel_type, diff, local_count))
        
        # 3. 分析缺失关系的原因
        if missing_types:
            print("\n【缺失关系分析】")
            print("-" * 40)
            for rel_type, diff, total in missing_types[:3]:  # 只分析前3个
                print(f"\n  {rel_type} (缺失{diff}条):")
                with local_driver.session() as local_session:
                    # 检查关系两端节点的属性情况
                    result = local_session.run(f"""
                        MATCH (a)-[r:{rel_type}]->(b)
                        RETURN 
                            labels(a)[0] as from_label,
                            labels(b)[0] as to_label,
                            count(*) as cnt
                        LIMIT 5
                    """)
                    for r in result:
                        print(f"    {r['from_label']} -> {r['to_label']}: {r['cnt']}条")
                    
                    # 检查有多少关系的节点没有id/name
                    result = local_session.run(f"""
                        MATCH (a)-[r:{rel_type}]->(b)
                        WHERE a.id IS NULL AND a.name IS NULL
                        RETURN count(r) as cnt
                    """)
                    no_id_from = result.single()["cnt"]
                    
                    result = local_session.run(f"""
                        MATCH (a)-[r:{rel_type}]->(b)
                        WHERE b.id IS NULL AND b.name IS NULL
                        RETURN count(r) as cnt
                    """)
                    no_id_to = result.single()["cnt"]
                    
                    if no_id_from > 0 or no_id_to > 0:
                        print(f"    ⚠️ 起点无id/name: {no_id_from}, 终点无id/name: {no_id_to}")
        
        print("\n" + "=" * 60)
        
    finally:
        local_driver.close()
        remote_driver.close()

if __name__ == "__main__":
    main()
