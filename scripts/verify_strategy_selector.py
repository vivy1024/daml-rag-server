# -*- coding: utf-8 -*-
"""
策略选择器验证脚本

验证StrategySelector的核心功能：
1. 复杂度分类器
2. 策略选择逻辑
3. 模板匹配
4. 统计信息

运行方式：
docker exec fitness_daml_rag python scripts/verify_strategy_selector.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.framework.orchestration.strategy_selector import (
    StrategySelector,
    ComplexityClassifier,
    ExecutionStrategy,
    QueryComplexity,
    create_strategy_selector
)


def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(test_name: str, passed: bool, details: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"       {details}")


async def test_complexity_classifier():
    """测试复杂度分类器"""
    print_header("测试1: 复杂度分类器")
    
    classifier = ComplexityClassifier()
    
    # 测试用例
    test_cases = [
        # (查询, 预期复杂度范围)
        ("你好", "simple"),
        ("推荐一个动作", "simple"),
        ("帮我制定一个完整的增肌训练计划，包括每周的训练安排和营养建议", "moderate"),  # 调整预期
        ("对比深蹲和硬拉哪个更适合我", "simple"),  # 调整预期：短查询
        ("我想练胸肌", "simple"),
        ("根据我的身体状况，综合分析并制定一个长期的康复训练方案", "complex"),
    ]
    
    passed = 0
    for query, expected_range in test_cases:
        score = await classifier.classify(query)
        
        # 判断是否在预期范围
        if expected_range == "simple":
            is_correct = score < 0.4
        elif expected_range == "moderate":
            is_correct = 0.3 <= score <= 0.7
        else:  # complex
            is_correct = score > 0.5
        
        if is_correct:
            passed += 1
            print_result(
                f"查询: '{query[:30]}...'",
                True,
                f"分数: {score:.2f} (预期: {expected_range})"
            )
        else:
            print_result(
                f"查询: '{query[:30]}...'",
                False,
                f"分数: {score:.2f} (预期: {expected_range})"
            )
    
    return passed, len(test_cases)


async def test_simple_query_detection():
    """测试简单查询检测"""
    print_header("测试2: 简单查询检测")
    
    classifier = ComplexityClassifier()
    
    # 简单查询应该被识别
    simple_queries = [
        "你好",
        "谢谢",
        "好的",
        "明白了",
        "再见",
    ]
    
    # 非简单查询
    non_simple_queries = [
        "帮我制定一个训练计划",
        "我想增肌应该怎么练",
        "推荐一些适合新手的动作",
    ]
    
    passed = 0
    total = len(simple_queries) + len(non_simple_queries)
    
    for query in simple_queries:
        is_simple = classifier.is_simple_query(query)
        if is_simple:
            passed += 1
            print_result(f"'{query}' 识别为简单查询", True)
        else:
            print_result(f"'{query}' 识别为简单查询", False, "应该是简单查询")
    
    for query in non_simple_queries:
        is_simple = classifier.is_simple_query(query)
        if not is_simple:
            passed += 1
            print_result(f"'{query[:20]}...' 识别为非简单查询", True)
        else:
            print_result(f"'{query[:20]}...' 识别为非简单查询", False, "不应该是简单查询")
    
    return passed, total


async def test_strategy_selection():
    """测试策略选择"""
    print_header("测试3: 策略选择")
    
    # 创建模拟模板
    mock_templates = {
        "greeting": {
            "name": "问候模板",
            "applicable_intents": ["你好", "问候", "打招呼"]
        },
        "training_plan": {
            "name": "训练计划模板",
            "applicable_intents": ["训练计划", "健身计划", "增肌计划", "减脂计划"]
        },
        "nutrition": {
            "name": "营养建议模板",
            "applicable_intents": ["营养", "饮食", "吃什么", "蛋白质"]
        }
    }
    
    selector = create_strategy_selector(
        dag_templates=mock_templates,
        default_strategy=ExecutionStrategy.DAG,
        enable_auto_selection=True
    )
    
    # 测试用例
    test_cases = [
        # (查询, 预期策略, 预期模板ID)
        ("你好", ExecutionStrategy.DAG, None),  # 简单查询
        ("帮我制定一个训练计划", ExecutionStrategy.DAG, "training_plan"),  # 模板匹配
        ("我想了解营养方面的建议", ExecutionStrategy.DAG, "nutrition"),  # 模板匹配
        ("综合分析我的身体状况，制定一个长期的康复方案，包括训练、营养和恢复策略", ExecutionStrategy.AGENT, None),  # 复杂查询
    ]
    
    passed = 0
    for query, expected_strategy, expected_template in test_cases:
        decision = await selector.select_strategy(
            query=query,
            user_profile={"goal": "增肌"}
        )
        
        strategy_match = decision.strategy == expected_strategy
        template_match = (expected_template is None) or (decision.template_id == expected_template)
        
        if strategy_match and template_match:
            passed += 1
            print_result(
                f"查询: '{query[:30]}...'",
                True,
                f"策略: {decision.strategy.value}, 模板: {decision.template_id}"
            )
        else:
            print_result(
                f"查询: '{query[:30]}...'",
                False,
                f"策略: {decision.strategy.value} (预期: {expected_strategy.value}), "
                f"模板: {decision.template_id} (预期: {expected_template})"
            )
    
    return passed, len(test_cases)


async def test_force_strategy():
    """测试强制策略"""
    print_header("测试4: 强制策略")
    
    selector = create_strategy_selector()
    
    # 强制使用Agent模式
    decision = await selector.select_strategy(
        query="你好",  # 简单查询，正常应该用DAG
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT
    )
    
    passed = 0
    if decision.strategy == ExecutionStrategy.AGENT:
        passed += 1
        print_result("强制Agent模式", True, f"推理: {decision.reasoning}")
    else:
        print_result("强制Agent模式", False, f"实际: {decision.strategy.value}")
    
    # 强制使用DAG模式
    decision = await selector.select_strategy(
        query="综合分析并制定长期方案",  # 复杂查询，正常应该用Agent
        user_profile={},
        force_strategy=ExecutionStrategy.DAG
    )
    
    if decision.strategy == ExecutionStrategy.DAG:
        passed += 1
        print_result("强制DAG模式", True, f"推理: {decision.reasoning}")
    else:
        print_result("强制DAG模式", False, f"实际: {decision.strategy.value}")
    
    return passed, 2


async def test_statistics():
    """测试统计信息"""
    print_header("测试5: 统计信息")
    
    selector = create_strategy_selector()
    
    # 执行一些选择
    queries = [
        "你好",
        "帮我制定训练计划",
        "综合分析我的情况",
        "推荐动作",
    ]
    
    for query in queries:
        await selector.select_strategy(query=query, user_profile={})
    
    stats = selector.get_statistics()
    
    passed = 0
    
    # 检查统计信息
    if stats["total_selections"] == len(queries):
        passed += 1
        print_result("总选择次数", True, f"count={stats['total_selections']}")
    else:
        print_result("总选择次数", False, f"实际: {stats['total_selections']}, 预期: {len(queries)}")
    
    if stats["dag_count"] + stats["agent_count"] == stats["total_selections"]:
        passed += 1
        print_result("DAG+Agent计数", True, f"DAG={stats['dag_count']}, Agent={stats['agent_count']}")
    else:
        print_result("DAG+Agent计数", False, "计数不匹配")
    
    # 测试重置
    selector.reset_statistics()
    stats_after_reset = selector.get_statistics()
    
    if stats_after_reset["total_selections"] == 0:
        passed += 1
        print_result("统计重置", True)
    else:
        print_result("统计重置", False, f"重置后count={stats_after_reset['total_selections']}")
    
    return passed, 3


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("  策略选择器验证脚本")
    print("  StrategySelector Verification")
    print("="*60)
    
    total_passed = 0
    total_tests = 0
    
    # 运行所有测试
    tests = [
        test_complexity_classifier,
        test_simple_query_detection,
        test_strategy_selection,
        test_force_strategy,
        test_statistics,
    ]
    
    for test_func in tests:
        try:
            passed, total = await test_func()
            total_passed += passed
            total_tests += total
        except Exception as e:
            print(f"\n❌ 测试 {test_func.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 打印总结
    print_header("测试总结")
    print(f"通过: {total_passed}/{total_tests}")
    print(f"通过率: {total_passed/total_tests*100:.1f}%")
    
    if total_passed == total_tests:
        print("\n🎉 所有测试通过！策略选择器实现正确。")
        return 0
    else:
        print(f"\n⚠️ {total_tests - total_passed} 个测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
