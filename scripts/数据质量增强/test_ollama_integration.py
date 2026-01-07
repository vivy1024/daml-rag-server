#!/usr/bin/env python3
"""
测试Ollama集成生成技术检查点

测试内容：
1. 测试Ollama连接
2. 测试单个动作生成
3. 测试批量生成（10个动作）
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.data_supplement.exercise_supplementer import ExerciseSupplementer
from dotenv import load_dotenv


async def test_ollama_connection():
    """测试Ollama连接"""
    print("=" * 60)
    print("测试1：Ollama连接")
    print("=" * 60)
    
    try:
        from ollama import AsyncClient
        
        ollama_host = "http://host.docker.internal:11434"
        client = AsyncClient(host=ollama_host)
        
        # 测试连接
        response = await client.generate(
            model='qwen3:8b',
            prompt='你好，请回复"测试成功"',
            options={'temperature': 0.3}
        )
        
        print(f"✅ Ollama连接成功")
        print(f"📝 测试响应: {response['response'][:50]}")
        return True
    except Exception as e:
        print(f"❌ Ollama连接失败: {e}")
        return False


async def test_single_generation():
    """测试单个动作生成"""
    print("\n" + "=" * 60)
    print("测试2：单个动作生成")
    print("=" * 60)
    
    load_dotenv()
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    supplementer = ExerciseSupplementer(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        async with supplementer.driver.session() as session:
            # 查询一个没有技术检查点的动作
            query = """
            MATCH (e:Exercise)
            WHERE e.technique_checkpoints IS NULL
              AND e.description_zh IS NOT NULL
            RETURN e.exercise_id as id, 
                   e.name_zh as name, 
                   e.description_zh as description
            LIMIT 1
            """
            result = await session.run(query)
            record = await result.single()
            
            if not record:
                print("ℹ️ 所有动作都已有技术检查点")
                return True
            
            print(f"📝 测试动作: {record['name']}")
            print(f"📝 动作描述: {record['description'][:50]}...")
            
            # 使用Ollama生成
            await supplementer._supplement_technique_checkpoints_with_llm(session, batch_size=1)
            
            # 验证结果
            verify_query = """
            MATCH (e:Exercise {exercise_id: $id})
            RETURN e.technique_checkpoints as checkpoints,
                   e.checkpoints_source as source
            """
            verify_result = await session.run(verify_query, {"id": record['id']})
            verify_record = await verify_result.single()
            
            if verify_record and verify_record['checkpoints']:
                import json
                checkpoints = json.loads(verify_record['checkpoints'])
                print(f"\n✅ 生成成功 ({verify_record['source']})")
                print(f"📋 技术检查点:")
                for i, cp in enumerate(checkpoints, 1):
                    print(f"   {i}. {cp}")
                return True
            else:
                print("❌ 生成失败")
                return False
    finally:
        await supplementer.close()


async def test_batch_generation():
    """测试批量生成"""
    print("\n" + "=" * 60)
    print("测试3：批量生成（10个动作）")
    print("=" * 60)
    
    load_dotenv()
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    supplementer = ExerciseSupplementer(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        async with supplementer.driver.session() as session:
            # 统计生成前的数量
            before_query = """
            MATCH (e:Exercise)
            WHERE e.technique_checkpoints IS NOT NULL
            RETURN count(e) as count
            """
            before_result = await session.run(before_query)
            before_record = await before_result.single()
            before_count = before_record['count']
            
            print(f"📊 生成前: {before_count} 个动作有技术检查点")
            
            # 批量生成
            await supplementer._supplement_technique_checkpoints_with_llm(session, batch_size=10)
            
            # 统计生成后的数量
            after_result = await session.run(before_query)
            after_record = await after_result.single()
            after_count = after_record['count']
            
            print(f"📊 生成后: {after_count} 个动作有技术检查点")
            print(f"📈 新增: {after_count - before_count} 个")
            
            return after_count > before_count
    finally:
        await supplementer.close()


async def main():
    """主测试流程"""
    print("\n🚀 开始测试Ollama集成")
    print("=" * 60)
    
    results = []
    
    # 测试1：Ollama连接
    try:
        result1 = await test_ollama_connection()
        results.append(("Ollama连接", result1))
        
        if not result1:
            print("\n❌ Ollama连接失败，跳过后续测试")
            return False
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        results.append(("Ollama连接", False))
        return False
    
    # 测试2：单个动作生成
    try:
        result2 = await test_single_generation()
        results.append(("单个动作生成", result2))
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        results.append(("单个动作生成", False))
    
    # 测试3：批量生成
    try:
        result3 = await test_batch_generation()
        results.append(("批量生成", result3))
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        results.append(("批量生成", False))
    
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
