#!/usr/bin/env python3
"""强制清空Neo4j生产环境数据（无需确认）"""
from neo4j import GraphDatabase

PRODUCTION_URI = "bolt://182.92.78.183:32372"
PRODUCTION_USER = "neo4j"
PRODUCTION_PASSWORD = "build_body_2024"

def main():
    print("=" * 60)
    print("强制清空Neo4j生产环境")
    print("=" * 60)
    print(f"连接: {PRODUCTION_URI}")
    print("=" * 60)
    
    driver = GraphDatabase.driver(PRODUCTION_URI, auth=(PRODUCTION_USER, PRODUCTION_PASSWORD))
    
    try:
        with driver.session() as session:
            # 检查当前状态
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            print(f"\n清空前状态:")
            print(f"  节点: {node_count}")
            print(f"  关系: {rel_count}")
            
            if node_count == 0:
                print("\n✅ 数据库已经是空的")
                return
            
            print("\n🗑️  开始清空...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # 验证
            result = session.run("MATCH (n) RETURN count(n) as count")
            final_count = result.single()["count"]
            
            print(f"\n清空后状态:")
            print(f"  节点: {final_count}")
            
            if final_count == 0:
                print("\n✅ 清空成功")
            else:
                print(f"\n⚠️  警告: 仍有 {final_count} 个节点")
    
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
