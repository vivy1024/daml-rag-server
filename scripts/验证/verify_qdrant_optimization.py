#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qdrant向量质量优化验证脚本

验证内容：
1. Layer1召回数提升（30→50个）
2. 质量评估机制工作正常
3. Layer2动态调整机制
4. 搜索相关性正确

版本: v1.0.0
日期: 2026-01-06
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine


async def test_layer1_recall_multiplier():
    """测试Layer1召回倍数提升"""
    print("\n" + "="*60)
    print("测试1: Layer1召回倍数提升（30→50个）")
    print("="*60)
    
    engine = TrueThreeLayerEngine(
        enable_neo4j_direct=False  # 只测试Layer1
    )
    
    # 测试查询
    query = "胸部训练"
    top_k = 10
    
    # 执行查询（使用默认layer1_multiplier=5）
    result = await engine.execute_three_layer_query(
        query=query,
        top_k=top_k,
        layer1_multiplier=5  # 明确指定5倍
    )
    
    layer1_count = len(result.layer_1_result.results)
    expected_count = top_k * 5  # 50个
    
    print(f"\n查询: {query}")
    print(f"top_k: {top_k}")
    print(f"Layer1召回倍数: 5")
    print(f"Layer1实际召回数: {layer1_count}")
    print(f"期望召回数: {expected_count}")
    
    if layer1_count == expected_count:
        print("✅ Layer1召回倍数验证通过")
        return True
    else:
        print(f"❌ Layer1召回倍数验证失败（期望{expected_count}，实际{layer1_count}）")
        return False


async def test_quality_assessment():
    """测试质量评估机制"""
    print("\n" + "="*60)
    print("测试2: Layer1质量评估机制")
    print("="*60)
    
    engine = TrueThreeLayerEngine(
        enable_neo4j_direct=False
    )
    
    # 测试5个查询
    test_queries = [
        "胸部训练",
        "背部训练",
        "腿部训练",
        "肩部训练",
        "核心训练"
    ]
    
    all_passed = True
    
    for query in test_queries:
        result = await engine.execute_three_layer_query(
            query=query,
            top_k=10
        )
        
        layer1_result = result.layer_1_result
        confidence = layer1_result.confidence
        is_low_quality = layer1_result.metadata.get("is_low_quality", False)
        
        print(f"\n查询: {query}")
        print(f"  置信度: {confidence:.2f}")
        print(f"  低质量标记: {is_low_quality}")
        
        # 验证质量评估逻辑
        if confidence < 0.70:
            if is_low_quality:
                print(f"  ✅ 质量评估正确（置信度{confidence:.2f} < 0.70，已标记为低质量）")
            else:
                print(f"  ❌ 质量评估错误（置信度{confidence:.2f} < 0.70，但未标记为低质量）")
                all_passed = False
        else:
            if not is_low_quality:
                print(f"  ✅ 质量评估正确（置信度{confidence:.2f} >= 0.70，未标记为低质量）")
            else:
                print(f"  ❌ 质量评估错误（置信度{confidence:.2f} >= 0.70，但标记为低质量）")
                all_passed = False
    
    if all_passed:
        print("\n✅ 质量评估机制验证通过")
    else:
        print("\n❌ 质量评估机制验证失败")
    
    return all_passed


async def test_layer2_dynamic_adjustment():
    """测试Layer2动态调整机制"""
    print("\n" + "="*60)
    print("测试3: Layer2动态调整机制")
    print("="*60)
    
    engine = TrueThreeLayerEngine(
        enable_neo4j_direct=True  # 启用Neo4j测试Layer2
    )
    
    # 测试查询
    query = "胸部训练"
    top_k = 10
    
    result = await engine.execute_three_layer_query(
        query=query,
        top_k=top_k
    )
    
    layer1_result = result.layer_1_result
    layer2_result = result.layer_2_result
    
    is_low_quality = layer1_result.metadata.get("is_low_quality", False)
    layer2_count = len(layer2_result.results)
    
    print(f"\n查询: {query}")
    print(f"Layer1质量: {'低' if is_low_quality else '正常'}")
    print(f"Layer2召回数: {layer2_count}")
    
    # 验证动态调整逻辑
    if is_low_quality:
        expected_min = top_k * 3  # 低质量时应该是3倍
        if layer2_count >= expected_min * 0.8:  # 允许80%的容差
            print(f"✅ Layer2动态调整正确（低质量时召回数{layer2_count} >= {expected_min}*0.8）")
            return True
        else:
            print(f"❌ Layer2动态调整错误（低质量时召回数{layer2_count} < {expected_min}*0.8）")
            return False
    else:
        expected_min = top_k * 2  # 正常质量时应该是2倍
        if layer2_count >= expected_min * 0.8:  # 允许80%的容差
            print(f"✅ Layer2动态调整正确（正常质量时召回数{layer2_count} >= {expected_min}*0.8）")
            return True
        else:
            print(f"❌ Layer2动态调整错误（正常质量时召回数{layer2_count} < {expected_min}*0.8）")
            return False


async def test_search_relevance():
    """测试搜索相关性"""
    print("\n" + "="*60)
    print("测试4: 搜索相关性验证")
    print("="*60)
    
    engine = TrueThreeLayerEngine(
        enable_neo4j_direct=False
    )
    
    # 测试查询和期望关键词
    test_cases = [
        {
            "query": "胸部训练",
            "expected_keywords": ["胸", "卧推", "飞鸟", "夹胸"],
            "muscle": "胸大肌"
        },
        {
            "query": "背部训练",
            "expected_keywords": ["背", "划船", "引体", "下拉"],
            "muscle": "背阔肌"
        },
        {
            "query": "腿部训练",
            "expected_keywords": ["腿", "深蹲", "腿举", "弓步"],
            "muscle": "股四头肌"
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        query = test_case["query"]
        expected_keywords = test_case["expected_keywords"]
        
        result = await engine.execute_three_layer_query(
            query=query,
            top_k=10
        )
        
        layer1_results = result.layer_1_result.results[:3]  # 只检查前3个
        
        print(f"\n查询: {query}")
        print(f"前3个结果:")
        
        relevant_count = 0
        for i, res in enumerate(layer1_results, 1):
            name = res.get("payload", {}).get("name_zh", "")
            score = res.get("score", 0)
            
            # 检查是否包含期望关键词
            is_relevant = any(keyword in name for keyword in expected_keywords)
            
            print(f"  {i}. {name} (分数: {score:.2f}) {'✅' if is_relevant else '❌'}")
            
            if is_relevant:
                relevant_count += 1
        
        # 至少2/3的结果应该相关
        if relevant_count >= 2:
            print(f"✅ 搜索相关性验证通过（{relevant_count}/3相关）")
        else:
            print(f"❌ 搜索相关性验证失败（{relevant_count}/3相关，期望至少2/3）")
            all_passed = False
    
    if all_passed:
        print("\n✅ 搜索相关性验证通过")
    else:
        print("\n❌ 搜索相关性验证失败")
    
    return all_passed


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("Qdrant向量质量优化验证")
    print("="*60)
    
    results = {
        "Layer1召回倍数": False,
        "质量评估机制": False,
        "Layer2动态调整": False,
        "搜索相关性": False
    }
    
    try:
        # 测试1: Layer1召回倍数
        results["Layer1召回倍数"] = await test_layer1_recall_multiplier()
        
        # 测试2: 质量评估机制
        results["质量评估机制"] = await test_quality_assessment()
        
        # 测试3: Layer2动态调整
        results["Layer2动态调整"] = await test_layer2_dynamic_adjustment()
        
        # 测试4: 搜索相关性
        results["搜索相关性"] = await test_search_relevance()
        
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 汇总结果
    print("\n" + "="*60)
    print("验证结果汇总")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for passed in results.values() if passed)
    pass_rate = (passed_tests / total_tests) * 100
    
    print(f"\n总计: {passed_tests}/{total_tests} 通过 ({pass_rate:.0f}%)")
    
    if passed_tests == total_tests:
        print("\n🎉 所有验证项通过！Qdrant优化成功！")
        return 0
    else:
        print(f"\n⚠️ {total_tests - passed_tests}个验证项失败，需要进一步优化")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
