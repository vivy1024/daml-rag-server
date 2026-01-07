"""
检查所有Exercise节点的所有字段
"""

import asyncio
import os
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
from collections import Counter

load_dotenv()


async def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 检查所有Exercise节点的字段")
    print("="*80)
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    try:
        async with driver.session() as session:
            print("✅ 成功连接到Neo4j数据库\n")
            
            # 获取所有Exercise节点
            result = await session.run("MATCH (e:Exercise) RETURN e LIMIT 10")
            records = await result.data()
            
            print(f"📊 检查了 {len(records)} 个Exercise节点\n")
            
            # 统计所有字段
            all_fields = Counter()
            for record in records:
                exercise = record["e"]
                for field in exercise.keys():
                    all_fields[field] += 1
            
            print("="*80)
            print("所有字段及其出现次数:")
            print("="*80)
            for field, count in sorted(all_fields.items()):
                print(f"  {field}: {count}/{len(records)} ({count/len(records)*100:.0f}%)")
            
            # 显示一个完整的Exercise示例
            print("\n" + "="*80)
            print("完整的Exercise节点示例:")
            print("="*80)
            if records:
                exercise = records[0]["e"]
                print(f"\nExercise ID: {exercise.get('id', 'N/A')}")
                print(f"Name (ZH): {exercise.get('name_zh', 'N/A')}")
                print(f"Name (EN): {exercise.get('name_en', 'N/A')}")
                print(f"\n所有字段:")
                for key, value in sorted(exercise.items()):
                    print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"\n❌ 检查过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await driver.close()
        print("\n✅ 已关闭Neo4j连接")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
