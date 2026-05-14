#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DAG编排层优化验证脚本

验证任务10的实现：
- 条件分支执行器
- DAG重试处理器
- DAG模板扩展

版本: v1.0.0
日期: 2026-01-05
"""

import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.framework.dag import (
    ConditionalBranchExecutor,
    ConditionalBranch,
    DAGRetryHandler,
    RetryConfig,
    RetryStrategy
)
from src.applications.fitness.dag_template_system import DAGTemplateManager


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_conditional_branch():
    """测试条件分支执行器"""
    print_section("测试1: 条件分支执行器")
    
    executor = ConditionalBranchExecutor()
    
    # 测试用例1: 相等比较
    result1 = {"risk_level": "high", "score": 0.85}
    condition1 = "result.risk_level == 'high'"
    test1 = executor.evaluate_condition(condition1, result1)
    print(f"✅ 测试1.1 - 相等比较: {condition1} = {test1}")
    assert test1 == True, "相等比较失败"
    
    # 测试用例2: 数值比较
    condition2 = "result.score > 0.8"
    test2 = executor.evaluate_condition(condition2, result1)
    print(f"✅ 测试1.2 - 数值比较: {condition2} = {test2}")
    assert test2 == True, "数值比较失败"
    
    # 测试用例3: in 运算符
    result3 = {"status": "processing"}
    condition3 = "result.status in ['pending', 'processing']"
    test3 = executor.evaluate_condition(condition3, result3)
    print(f"✅ 测试1.3 - in运算符: {condition3} = {test3}")
    assert test3 == True, "in运算符失败"
    
    # 测试用例4: 分支选择
    branches = [
        ConditionalBranch(
            condition="result.risk_level == 'high'",
            branch_to="safe_exercise_modifier",
            priority=1
        ),
        ConditionalBranch(
            condition="result.risk_level == 'low'",
            branch_to="intelligent_exercise_selector",
            priority=2
        )
    ]
    
    selected = executor.select_branch(branches, result1)
    print(f"✅ 测试1.4 - 分支选择: {selected}")
    assert selected == "safe_exercise_modifier", "分支选择失败"
    
    print(f"\n✅ 条件分支执行器测试通过（4/4）")
    return True


async def test_retry_handler():
    """测试DAG重试处理器"""
    print_section("测试2: DAG重试处理器")
    
    handler = DAGRetryHandler()
    
    # 模拟工具函数
    call_count = {"count": 0}
    
    async def mock_tool_success(tool_name: str, params: dict):
        """模拟成功的工具"""
        call_count["count"] += 1
        return {"tool": tool_name, "status": "success", "data": params}
    
    async def mock_tool_fail_then_success(tool_name: str, params: dict):
        """模拟第一次失败，第二次成功的工具"""
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise Exception("第一次调用失败")
        return {"tool": tool_name, "status": "success"}
    
    # 测试用例1: 成功执行
    call_count["count"] = 0
    config1 = RetryConfig(max_retries=2, timeout_seconds=2.0)
    result1 = await handler.execute_with_retry(
        mock_tool_success,
        "test_tool",
        {"param1": "value1"},
        config1
    )
    print(f"✅ 测试2.1 - 成功执行: success={result1.success}, attempts={result1.attempts}")
    assert result1.success == True, "成功执行测试失败"
    assert result1.attempts == 1, "尝试次数错误"
    
    # 测试用例2: 重试后成功
    call_count["count"] = 0
    config2 = RetryConfig(
        max_retries=2,
        timeout_seconds=2.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )
    result2 = await handler.execute_with_retry(
        mock_tool_fail_then_success,
        "test_tool",
        {"param1": "value1"},
        config2
    )
    print(f"✅ 测试2.2 - 重试后成功: success={result2.success}, attempts={result2.attempts}")
    assert result2.success == True, "重试后成功测试失败"
    assert result2.attempts == 2, "重试次数错误"
    
    # 测试用例3: 统计信息
    stats = handler.get_statistics()
    print(f"✅ 测试2.3 - 统计信息: total={stats['total_executions']}, success_rate={stats['success_rate']:.2f}")
    assert stats['total_executions'] == 2, "总执行次数错误"
    assert stats['successful_executions'] == 2, "成功次数错误"
    
    print(f"\n✅ DAG重试处理器测试通过（3/3）")
    return True


def test_dag_templates():
    """测试DAG模板扩展"""
    print_section("测试3: DAG模板扩展")
    
    manager = DAGTemplateManager()
    
    # 测试用例1: 模板总数
    total_templates = len(manager.templates)
    print(f"✅ 测试3.1 - 模板总数: {total_templates}个")
    assert total_templates == 13, f"模板总数错误，期望13个，实际{total_templates}个"
    
    # 测试用例2: 训练计划调整模板
    template1 = manager.get_template("plan_adjustment")
    print(f"✅ 测试3.2 - 训练计划调整: {template1.name}")
    assert template1 is not None, "训练计划调整模板不存在"
    assert template1.name == "训练计划调整", "模板名称错误"
    assert template1.complexity_level == 2, "复杂度错误"
    
    # 测试用例3: 减脂专项模板
    template2 = manager.get_template("fat_loss_program")
    print(f"✅ 测试3.3 - 减脂专项: {template2.name}")
    assert template2 is not None, "减脂专项模板不存在"
    assert template2.name == "减脂专项", "模板名称错误"
    assert template2.complexity_level == 3, "复杂度错误"
    
    # 测试用例4: 力量专项模板
    template3 = manager.get_template("strength_program")
    print(f"✅ 测试3.4 - 力量专项: {template3.name}")
    assert template3 is not None, "力量专项模板不存在"
    assert template3.name == "力量专项", "模板名称错误"
    assert template3.complexity_level == 3, "复杂度错误"
    
    # 测试用例5: 模板验证
    validation1 = manager.validate_template_dependencies("plan_adjustment")
    validation2 = manager.validate_template_dependencies("fat_loss_program")
    validation3 = manager.validate_template_dependencies("strength_program")
    print(f"✅ 测试3.5 - 模板验证: 全部通过")
    assert validation1['valid'] == True, "训练计划调整模板验证失败"
    assert validation2['valid'] == True, "减脂专项模板验证失败"
    assert validation3['valid'] == True, "力量专项模板验证失败"
    
    print(f"\n✅ DAG模板扩展测试通过（5/5）")
    return True


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  DAG编排层优化验证")
    print("  版本: v1.0.0")
    print("  日期: 2026-01-05")
    print("=" * 60)
    
    try:
        # 测试1: 条件分支执行器
        test1_passed = test_conditional_branch()
        
        # 测试2: DAG重试处理器
        test2_passed = await test_retry_handler()
        
        # 测试3: DAG模板扩展
        test3_passed = test_dag_templates()
        
        # 总结
        print_section("验证总结")
        
        total_tests = 12  # 4 + 3 + 5
        passed_tests = 12
        
        print(f"总测试项: {total_tests}")
        print(f"通过项: {passed_tests}")
        print(f"失败项: {total_tests - passed_tests}")
        print(f"通过率: {passed_tests / total_tests * 100:.1f}%")
        
        print("\n" + "=" * 60)
        print("  ✅ DAG编排层优化验证完成")
        print("=" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
