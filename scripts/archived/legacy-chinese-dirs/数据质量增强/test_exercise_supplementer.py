#!/usr/bin/env python3
"""
测试Exercise补充器

测试内容：
1. 数据质量检查
2. 运动链类型补充
3. 技术检查点补充
4. 关节活动度补充
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.data_supplement.exercise_supplementer import ExerciseSupplementer
from dotenv import load_dotenv


async def test_data_quality_check():
    """测试数据质量检查"""
    print("=" * 60)
    print("测试1：数据质量检查")
    print("=" * 60)
    
    load_dotenv()
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    supplementer = ExerciseSupplementer(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        async with supplementer.driver.session() as session:
            quality_report = await supplementer._check_data_quality(session)
            
            print(f"\n📊 数据质量报告：")
            print(f"   总动作数: {quality_report['total_exercises']}")
            print(f"   重复数: {quality_report['duplicate_description_steps']}")
            print(f"   重复比例: {quality_report['duplicate_percentage']}%")
            
            return quality_report['total_exercises'] > 0
    finally:
        await supplementer.close()


async def test_kinetic_chain_supplement():
    """测试运动链类型补充"""
    print("\n" + "=" * 60)
    print("测试2：运动链类型补充")
    print("=" * 60)
    
    load_dotenv()
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    supplementer = ExerciseSupplementer(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        async with supplementer.driver.session() as session:
            # 补充运动链类型
            await supplementer._supplement_kinetic_chain_type(session)
            
            # 验证结果
            query = """
            MATCH (e:Exercise)
            WHERE e.kinetic_chain_type IS NOT NULL
            RETURN e.kinetic_chain_type as type, count(e) as count
            ORDER BY count DESC
            """
            result = await session.run(query)
            records = await result.data()
            
            print(f"\n📊 运动链类型分布：")
            for record in records:
                print(f"   {record['type']}: {record['count']} 个")
            
            return len(records) > 0
    finally:
        await supplementer.close()


async def test_technique_checkpoints():
    """测试技术检查点补充"""
    print("\n" + "=" * 60)
    print("测试3：技术检查点补充")
    print("=" * 60)
    
    load_dotenv()
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    supplementer = ExerciseSupplementer(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        async with supplementer.driver.session() as session:
            # 补充技术检查点
            await supplementer._supplement_technique_checkpoints_manual(session)
            
            # 验证结果
            query = """
            MATCH (e:Exercise)
            WHERE e.technique_checkpoints IS NOT NULL
            RETURN e.name_zh as name, e.technique_checkpoints as checkpoints
            LIMIT 5
            """
            result = await session.run(query)
            records = await result.data()
            
            print(f"\n📊 技术检查点示例：")
            for record in records:
                print(f"\n   {record['name']}:")
                import json
                checkpoints = json.loads(record['checkpoints'])
                for i, cp in enumerate(checkpoints, 1):
                    print(f"      {i}. {cp}")
            
            return len(records) > 0
    finally:
        await supplementer.close()


async def test_rom_requirements():
    """测试关节活动度补充"""
    print("\n" + "=" * 60)
    print("测试4：关节活动度补充")
    print("=" * 60)
    
    load_dotenv()
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    supplementer = ExerciseSupplementer(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        async with supplementer.driver.session() as session:
            # 补充关节活动度
            await supplementer._supplement_rom_requirements(session)
            
            # 验证结果
            query = """
            MATCH (e:Exercise)
            WHERE e.rom_requirements IS NOT NULL
            RETURN e.name_zh as name, e.rom_requirements as rom
            """
            result = await session.run(query)
            records = await result.data()
            
            print(f"\n📊 关节活动度示例：")
            for record in records:
                print(f"\n   {record['name']}:")
                import json
                rom = json.loads(record['rom'])
                for joint, angle in rom.items():
                    print(f"      {joint}: {angle}°")
            
            return len(records) > 0
    finally:
        await supplementer.close()


async def main():
    """主测试流程"""
    print("\n🚀 开始测试Exercise补充器")
    print("=" * 60)
    
    results = []
    
    # 测试1：数据质量检查
    try:
        result1 = await test_data_quality_check()
        results.append(("数据质量检查", result1))
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        results.append(("数据质量检查", False))
    
    # 测试2：运动链类型补充
    try:
        result2 = await test_kinetic_chain_supplement()
        results.append(("运动链类型补充", result2))
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        results.append(("运动链类型补充", False))
    
    # 测试3：技术检查点补充
    try:
        result3 = await test_technique_checkpoints()
        results.append(("技术检查点补充", result3))
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        results.append(("技术检查点补充", False))
    
    # 测试4：关节活动度补充
    try:
        result4 = await test_rom_requirements()
        results.append(("关节活动度补充", result4))
    except Exception as e:
        print(f"❌ 测试4失败: {e}")
        results.append(("关节活动度补充", False))
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
