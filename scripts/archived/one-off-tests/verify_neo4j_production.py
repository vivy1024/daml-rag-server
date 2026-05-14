#!/usr/bin/env python3
"""验证生产环境Neo4j数据"""
import sys
from neo4j import GraphDatabase

def verify_neo4j(uri, user, password, env_name):
    """验证Neo4j数据"""
    print("=" * 60)
    print(f"Neo4j {env_name} 数据验证")
    print("=" * 60)
    print(f"连接: {uri}")
    print(f"用户: {user}")
    print("=" * 60)
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # 1. 统计所有节点类型
            print("\n📊 节点类型统计:")
            result = session.run("MATCH (n) RETURN labels(n) as NodeType, count(n) as Count ORDER BY Count DESC")
            total_nodes = 0
            for record in result:
                node_type = record["NodeType"][0] if record["NodeType"] else "Unknown"
                count = record["Count"]
                total_nodes += count
                print(f"  {node_type}: {count}")
            
            print(f"\n  总节点数: {total_nodes}")
            
            # 2. 统计关系类型
            print("\n🔗 关系类型统计:")
            result = session.run("MATCH ()-[r]->() RETURN type(r) as RelationType, count(r) as Count ORDER BY Count DESC")
            total_rels = 0
            for record in result:
                rel_type = record["RelationType"]
                count = record["Count"]
                total_rels += count
                print(f"  {rel_type}: {count}")
            
            print(f"\n  总关系数: {total_rels}")
            
            # 3. 验证核心数据
            print("\n✅ 核心数据验证:")
            
            # Exercise节点
            result = session.run("MATCH (e:Exercise) RETURN count(e) as Count")
            exercise_count = result.single()["Count"]
            print(f"  Exercise节点: {exercise_count} (预期: 1790)")
            
            # Muscle节点
            result = session.run("MATCH (m:Muscle) RETURN count(m) as Count")
            muscle_count = result.single()["Count"]
            print(f"  Muscle节点: {muscle_count} (预期: 40)")
            
            # 示例Exercise
            print("\n📝 示例Exercise节点:")
            result = session.run("MATCH (e:Exercise) RETURN e.name_zh, e.name_en LIMIT 3")
            for record in result:
                print(f"  - {record['e.name_zh']} ({record['e.name_en']})")
            
            print("\n" + "=" * 60)
            print("✅ 验证完成！")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    # 检查本地环境
    print("\n🔍 检查本地Neo4j...")
    verify_neo4j(
        uri="bolt://fitness_neo4j:7687",
        user="neo4j",
        password="build_body_2024",
        env_name="本地环境"
    )
    
    print("\n\n🔍 检查生产环境Neo4j...")
    verify_neo4j(
        uri="bolt://182.92.78.183:32372",
        user="neo4j",
        password="build_body_2024",
        env_name="生产环境"
    )

