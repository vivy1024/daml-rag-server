# -*- coding: utf-8 -*-
"""
验证会员权限与策略选择器集成

测试内容：
1. 会员控制器与策略选择器集成
2. 不同会员等级的策略权限
3. Agent模式权限限制
4. Feature Flag控制

版本: v1.0.0
日期: 2026-01-11
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.framework.auth.membership_controller import (
    MembershipController,
    MembershipLevel,
    create_membership_controller,
    get_membership_level_from_string,
)
from src.framework.orchestration.strategy_selector import (
    StrategySelector,
    ExecutionStrategy,
    QueryComplexity,
    create_strategy_selector,
)


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(test_name: str, passed: bool, details: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} - {test_name}")
    if details:
        print(f"         {details}")


async def test_membership_controller_integration():
    """测试1: 会员控制器与策略选择器集成"""
    print_header("测试1: 会员控制器与策略选择器集成")
    
    passed = 0
    total = 0
    
    # 创建会员控制器
    membership_controller = create_membership_controller()
    
    # 创建策略选择器（集成会员控制器）
    selector = create_strategy_selector(
        membership_controller=membership_controller
    )
    
    # 测试1.1: 策略选择器正确初始化
    total += 1
    if selector.membership_controller is not None:
        print_result("策略选择器集成会员控制器", True)
        passed += 1
    else:
        print_result("策略选择器集成会员控制器", False)
    
    # 测试1.2: 统计信息包含会员控制状态
    total += 1
    stats = selector.get_statistics()
    if "membership_controller_enabled" in stats:
        print_result("统计信息包含会员控制状态", True, 
                    f"enabled={stats['membership_controller_enabled']}")
        passed += 1
    else:
        print_result("统计信息包含会员控制状态", False)
    
    # 测试1.3: 可以动态设置会员控制器
    total += 1
    selector2 = create_strategy_selector()
    selector2.set_membership_controller(membership_controller)
    if selector2.membership_controller is not None:
        print_result("动态设置会员控制器", True)
        passed += 1
    else:
        print_result("动态设置会员控制器", False)
    
    print(f"\n  小计: {passed}/{total} 通过")
    return passed, total


async def test_free_user_strategy():
    """测试2: 免费用户策略权限"""
    print_header("测试2: 免费用户策略权限")
    
    passed = 0
    total = 0
    
    # 创建启用会员控制的控制器
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    membership_controller = MembershipController()
    
    selector = StrategySelector(
        membership_controller=membership_controller
    )
    
    # 测试2.1: 免费用户简单查询使用DAG
    total += 1
    decision = await selector.select_strategy(
        query="你好",
        user_profile={},
        membership_level="free"
    )
    if decision.strategy == ExecutionStrategy.DAG:
        print_result("免费用户简单查询使用DAG", True)
        passed += 1
    else:
        print_result("免费用户简单查询使用DAG", False, 
                    f"实际策略: {decision.strategy.value}")
    
    # 测试2.2: 免费用户复杂查询被降级到DAG
    total += 1
    decision = await selector.select_strategy(
        query="请帮我制定一个综合的增肌训练计划，包括每周的训练安排、营养建议、恢复策略，并且要考虑我的膝盖旧伤",
        user_profile={"goal": "增肌", "injuries": ["膝盖旧伤"]},
        membership_level="free"
    )
    if decision.strategy == ExecutionStrategy.DAG and decision.membership_restricted:
        print_result("免费用户复杂查询被降级到DAG", True,
                    f"原策略: {decision.original_strategy.value if decision.original_strategy else 'N/A'}")
        passed += 1
    else:
        print_result("免费用户复杂查询被降级到DAG", False,
                    f"策略: {decision.strategy.value}, restricted: {decision.membership_restricted}")
    
    # 测试2.3: 免费用户强制Agent被拒绝
    total += 1
    decision = await selector.select_strategy(
        query="测试查询",
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT,
        membership_level="free"
    )
    if decision.strategy == ExecutionStrategy.DAG and decision.membership_restricted:
        print_result("免费用户强制Agent被拒绝", True)
        passed += 1
    else:
        print_result("免费用户强制Agent被拒绝", False,
                    f"策略: {decision.strategy.value}")
    
    # 恢复环境变量
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    print(f"\n  小计: {passed}/{total} 通过")
    return passed, total


async def test_warmheart_user_strategy():
    """测试3: 暖心会员策略权限"""
    print_header("测试3: 暖心会员策略权限")
    
    passed = 0
    total = 0
    
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    membership_controller = MembershipController()
    
    selector = StrategySelector(
        membership_controller=membership_controller
    )
    
    # 测试3.1: 暖心会员可以使用DAG
    total += 1
    decision = await selector.select_strategy(
        query="推荐一些胸肌训练动作",
        user_profile={},
        membership_level="warmheart"
    )
    if decision.strategy == ExecutionStrategy.DAG:
        print_result("暖心会员可以使用DAG", True)
        passed += 1
    else:
        print_result("暖心会员可以使用DAG", False)
    
    # 测试3.2: 暖心会员复杂查询也被降级
    total += 1
    decision = await selector.select_strategy(
        query="请帮我制定一个综合的增肌训练计划，包括每周的训练安排、营养建议、恢复策略",
        user_profile={},
        membership_level="warmheart"
    )
    if decision.strategy == ExecutionStrategy.DAG:
        print_result("暖心会员复杂查询使用DAG", True,
                    f"restricted: {decision.membership_restricted}")
        passed += 1
    else:
        print_result("暖心会员复杂查询使用DAG", False)
    
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    print(f"\n  小计: {passed}/{total} 通过")
    return passed, total


async def test_energy_user_strategy():
    """测试4: 能量会员策略权限"""
    print_header("测试4: 能量会员策略权限")
    
    passed = 0
    total = 0
    
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    membership_controller = MembershipController()
    
    selector = StrategySelector(
        membership_controller=membership_controller
    )
    
    # 测试4.1: 能量会员可以使用DAG
    total += 1
    decision = await selector.select_strategy(
        query="推荐一些胸肌训练动作",
        user_profile={},
        membership_level="energy"
    )
    if decision.strategy == ExecutionStrategy.DAG:
        print_result("能量会员可以使用DAG", True)
        passed += 1
    else:
        print_result("能量会员可以使用DAG", False)
    
    # 测试4.2: 能量会员复杂查询可以使用Agent
    total += 1
    decision = await selector.select_strategy(
        query="请帮我制定一个综合的增肌训练计划，包括每周的训练安排、营养建议、恢复策略，并且要考虑我的膝盖旧伤",
        user_profile={"goal": "增肌"},
        membership_level="energy"
    )
    # 能量会员不应该被限制
    if not decision.membership_restricted:
        print_result("能量会员复杂查询不被限制", True,
                    f"策略: {decision.strategy.value}")
        passed += 1
    else:
        print_result("能量会员复杂查询不被限制", False)
    
    # 测试4.3: 能量会员可以强制使用Agent
    total += 1
    decision = await selector.select_strategy(
        query="测试查询",
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT,
        membership_level="energy"
    )
    if decision.strategy == ExecutionStrategy.AGENT and not decision.membership_restricted:
        print_result("能量会员可以强制使用Agent", True)
        passed += 1
    else:
        print_result("能量会员可以强制使用Agent", False,
                    f"策略: {decision.strategy.value}")
    
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    print(f"\n  小计: {passed}/{total} 通过")
    return passed, total


async def test_feature_flag_disabled():
    """测试5: Feature Flag禁用时所有用户享有energy权限"""
    print_header("测试5: Feature Flag禁用时所有用户享有energy权限")
    
    passed = 0
    total = 0
    
    # 确保Feature Flag禁用
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    membership_controller = MembershipController()
    
    selector = StrategySelector(
        membership_controller=membership_controller
    )
    
    # 测试5.1: 免费用户复杂查询不被限制
    total += 1
    decision = await selector.select_strategy(
        query="请帮我制定一个综合的增肌训练计划，包括每周的训练安排、营养建议、恢复策略",
        user_profile={},
        membership_level="free"
    )
    if not decision.membership_restricted:
        print_result("Feature Flag禁用时免费用户不被限制", True,
                    f"策略: {decision.strategy.value}")
        passed += 1
    else:
        print_result("Feature Flag禁用时免费用户不被限制", False)
    
    # 测试5.2: 免费用户可以强制使用Agent
    total += 1
    decision = await selector.select_strategy(
        query="测试查询",
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT,
        membership_level="free"
    )
    if decision.strategy == ExecutionStrategy.AGENT and not decision.membership_restricted:
        print_result("Feature Flag禁用时免费用户可用Agent", True)
        passed += 1
    else:
        print_result("Feature Flag禁用时免费用户可用Agent", False,
                    f"策略: {decision.strategy.value}")
    
    print(f"\n  小计: {passed}/{total} 通过")
    return passed, total


async def test_statistics():
    """测试6: 统计信息正确记录"""
    print_header("测试6: 统计信息正确记录")
    
    passed = 0
    total = 0
    
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    membership_controller = MembershipController()
    
    selector = StrategySelector(
        membership_controller=membership_controller
    )
    
    # 重置统计
    selector.reset_statistics()
    
    # 执行一些策略选择
    await selector.select_strategy("你好", {}, membership_level="free")
    await selector.select_strategy(
        "请帮我制定一个综合的增肌训练计划，包括每周的训练安排",
        {},
        membership_level="free"
    )
    await selector.select_strategy(
        "推荐胸肌动作",
        {},
        membership_level="energy"
    )
    
    stats = selector.get_statistics()
    
    # 测试6.1: 总选择次数正确
    total += 1
    if stats["total_selections"] == 3:
        print_result("总选择次数正确", True, f"count={stats['total_selections']}")
        passed += 1
    else:
        print_result("总选择次数正确", False, f"count={stats['total_selections']}")
    
    # 测试6.2: 会员限制次数记录
    total += 1
    if "membership_restricted_count" in stats:
        print_result("会员限制次数记录", True, 
                    f"count={stats['membership_restricted_count']}")
        passed += 1
    else:
        print_result("会员限制次数记录", False)
    
    # 测试6.3: 会员限制比例计算
    total += 1
    if "membership_restricted_ratio" in stats:
        print_result("会员限制比例计算", True,
                    f"ratio={stats['membership_restricted_ratio']}")
        passed += 1
    else:
        print_result("会员限制比例计算", False)
    
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    print(f"\n  小计: {passed}/{total} 通过")
    return passed, total


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  会员权限与策略选择器集成验证")
    print("  版本: v1.0.0")
    print("  日期: 2026-01-11")
    print("="*60)
    
    total_passed = 0
    total_tests = 0
    
    # 运行所有测试
    tests = [
        test_membership_controller_integration,
        test_free_user_strategy,
        test_warmheart_user_strategy,
        test_energy_user_strategy,
        test_feature_flag_disabled,
        test_statistics,
    ]
    
    for test in tests:
        try:
            passed, total = await test()
            total_passed += passed
            total_tests += total
        except Exception as e:
            print(f"\n❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    # 总结
    print("\n" + "="*60)
    print(f"  总计: {total_passed}/{total_tests} 测试通过")
    print("="*60)
    
    if total_passed == total_tests:
        print("\n🎉 所有测试通过！会员权限与策略选择器集成正常工作。")
        return 0
    else:
        print(f"\n⚠️ {total_tests - total_passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
