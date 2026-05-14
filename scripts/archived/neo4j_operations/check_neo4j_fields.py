"""
直接检查Neo4j数据库字段
"""

import asyncio
import os
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

load_dotenv()


async def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 检查Neo4j数据库字段")
    print("="*80)
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    try:
        async with driver.session() as session:
            print("✅ 成功连接到Neo4j数据库\n")
            
            # 1. 检查Exercise节点字段
            print("="*80)
            print("🔍 检查Exercise节点字段")
            print("="*80)
            
            result = await session.run("MATCH (e:Exercise) RETURN e LIMIT 1")
            record = await result.single()
            
            if record:
                exercise = record["e"]
                actual_fields = set(exercise.keys())
                print(f"\n📊 Exercise节点实际字段数量: {len(actual_fields)}")
                print(f"\n实际字段列表:")
                for field in sorted(actual_fields):
                    print(f"  - {field}")
                
                # 检查工具使用的字段
                print("\n" + "-"*80)
                print("检查IntelligentExerciseSelector使用的字段:")
                print("-"*80)
                selector_fields = {
                    "id", "name_zh", "name_en", "category", "difficulty",
                    "safety_level", "equipment_zh", "primary_muscle_zh",
                    "force", "mechanic", "rep_range", "set_range"
                }
                
                missing = selector_fields - actual_fields
                if missing:
                    print(f"\n❌ 缺失字段: {missing}")
                else:
                    print(f"\n✅ 所有字段都存在")
                
                print("\n" + "-"*80)
                print("检查InjuryRiskAssessor使用的字段:")
                print("-"*80)
                assessor_fields = {
                    "id", "name_zh", "name_en", "category", "difficulty",
                    "safety_level", "injury_risk_factors", "primary_muscle_zh"
                }
                
                missing = assessor_fields - actual_fields
                if missing:
                    print(f"\n❌ 缺失字段: {missing}")
                    print("\n⚠️  注意: 'injury_risk_factors'字段可能不存在于数据库中")
                    print("   建议检查是否应该使用其他字段或从关系中获取")
                else:
                    print(f"\n✅ 所有字段都存在")
                
                print("\n" + "-"*80)
                print("检查ContraindicationsChecker使用的字段:")
                print("-"*80)
                checker_fields = {
                    "id", "name_zh", "name_en", "category", "difficulty",
                    "safety_level", "equipment_zh"
                }
                
                missing = checker_fields - actual_fields
                if missing:
                    print(f"\n❌ 缺失字段: {missing}")
                else:
                    print(f"\n✅ 所有字段都存在")
            
            # 2. 检查Muscle节点字段
            print("\n" + "="*80)
            print("🔍 检查Muscle节点字段")
            print("="*80)
            
            result = await session.run("MATCH (m:Muscle) RETURN m LIMIT 1")
            record = await result.single()
            
            if record:
                muscle = record["m"]
                actual_fields = set(muscle.keys())
                print(f"\n📊 Muscle节点实际字段数量: {len(actual_fields)}")
                print(f"\n实际字段列表:")
                for field in sorted(actual_fields):
                    print(f"  - {field}")
            
            # 3. 检查关系
            print("\n" + "="*80)
            print("🔍 检查关系")
            print("="*80)
            
            # TARGETS_PRIMARY
            result = await session.run(
                "MATCH ()-[r:TARGETS_PRIMARY]->() RETURN count(r) as count"
            )
            record = await result.single()
            print(f"\n✅ TARGETS_PRIMARY关系: {record['count']}个")
            
            # TARGETS_SECONDARY
            result = await session.run(
                "MATCH ()-[r:TARGETS_SECONDARY]->() RETURN count(r) as count"
            )
            record = await result.single()
            print(f"✅ TARGETS_SECONDARY关系: {record['count']}个")
            
            # CONTRAINDICATED_FOR
            result = await session.run(
                "MATCH ()-[r:CONTRAINDICATED_FOR]->() RETURN count(r) as count"
            )
            record = await result.single()
            print(f"⚠️  CONTRAINDICATED_FOR关系: {record['count']}个 (极少)")
            
            # REQUIRES
            result = await session.run(
                "MATCH ()-[r:REQUIRES]->() RETURN count(r) as count"
            )
            record = await result.single()
            print(f"✅ REQUIRES关系: {record['count']}个")
            
            print("\n" + "="*80)
            print("✅ 检查完成！")
            print("="*80)
        
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
