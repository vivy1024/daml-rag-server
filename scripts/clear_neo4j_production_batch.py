#!/usr/bin/env python3
"""分批清空Neo4j生产环境数据（避免内存溢出）"""
from neo4j import GraphDatabase
import time

PRODUCTION_URI = "bolt://182.92.78.183:32372"
PRODUCTION_USER = "neo4j"
PRODUCTION_PASSWORD = "build_body_2024"

BATCH_SIZE = 1000  # 每批删除1000个节点

def main():
    print("=" * 60)
    print("分批清空Neo4j生产环境")
    print("=" * 60)
    print(f"连接: {PRODUCTION_URI}")
    print(f"批次大小: {BATCH_SIZE}")
    print("=" * 60)
    
    driver = GraphDatabase.driver(PRODUCTION_URI, auth=(PRODUCTION_USER, PRODUCTION_PASSWORD))
    
    try:
        with driver.session() as session:
            # 检查初始状态
            result = session.run("MATCH (n) RETURN count(n) as count")
            initial_count = result.single()["count"]
            
            print(f"\n初始节点数: {initial_count}")
            
            if initial_count == 0:
                print("\n✅ 数据库已经是空的")
                return
            
            print("\n🗑️  开始分批删除...")
            
            batch_num = 0
            total_deleted = 0
            
            while True:
                # 删除一批节点（包括关系）
                result = session.run(f"""
                    MATCH (n)
                    WITH n LIMIT {BATCH_SIZE}
                    DETACH DELETE n
                    RETURN count(n) as deleted
                """)
                
                deleted = result.single()["deleted"]
                
                if deleted == 0:
                    break
                
                batch_num += 1
                total_deleted += deleted
                
                # 检查剩余节点
                result = session.run("MATCH (n) RETURN count(n) as count")
                remaining = result.single()["count"]
                
                print(f"  批次 {batch_num}: 删除 {deleted} 个节点, 剩余 {remaining}")
                
                # 短暂休息，让数据库释放内存
                time.sleep(0.5)
            
            print(f"\n✅ 清空完成")
            print(f"  总共删除: {total_deleted} 个节点")
            print(f"  批次数: {batch_num}")
            
            # 最终验证
            result = session.run("MATCH (n) RETURN count(n) as count")
            final_count = result.single()["count"]
            
            if final_count == 0:
                print(f"\n✅ 验证成功: 数据库已清空")
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
