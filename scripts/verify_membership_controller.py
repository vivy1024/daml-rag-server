# -*- coding: utf-8 -*-
"""
会员权限控制器验证脚本

验证MembershipController的核心功能：
1. 会员配置获取
2. 策略权限检查
3. 功能权限检查
4. 每日使用限制

运行方式：
docker exec fitness_daml_rag python scripts/verify_membership_controller.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.framework.auth.membership_controller import (
    MembershipController,
    MembershipLevel,
    Feature,
    ExecutionStrategy,
    create_membership_controller,
    get_membership_level_from_string,
    MEMBERSHIP_CONFIGS
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


def test_membership_configs():
    """测试会员配置"""
    print_header("测试1: 会员配置")
    
    passed = 0
    total = 3
    
    # 检查三个等级都有配置
    for level in [MembershipLevel.FREE, MembershipLevel.BASIC, MembershipLevel.PREMIUM]:
        if level in MEMBERSHIP_CONFIGS:
            config = MEMBERSHIP_CONFIGS[level]
            print_result(
                f"{level.value}等级配置",
                True,
                f"每日限制: {config.daily_limit}, 策略: {[s.value for s in config.allowed_strategies]}"
            )
            passed += 1
        else:
            print_result(f"{level.value}等级配置", False, "配置缺失")
    
    return passed, total


def test_strategy_permission():
    """测试策略权限"""
    print_header("测试2: 策略权限检查")
    
    controller = create_membership_controller()
    
    test_cases = [
        # (会员等级, 策略, 预期结果)
        (MembershipLevel.FREE, ExecutionStrategy.DAG, True),
        (MembershipLevel.FREE, ExecutionStrategy.AGENT, False),
        (MembershipLevel.BASIC, ExecutionStrategy.DAG, True),
        (MembershipLevel.BASIC, ExecutionStrategy.AGENT, False),
        (MembershipLevel.PREMIUM, ExecutionStrategy.DAG, True),
        (MembershipLevel.PREMIUM, ExecutionStrategy.AGENT, True),
    ]
    
    passed = 0
    for level, strategy, expected in test_cases:
        result = controller.can_use_strategy(level, strategy)
        if result.allowed == expected:
            passed += 1
            print_result(
                f"{level.value} + {strategy.value}",
                True,
                f"允许: {result.allowed}"
            )
        else:
            print_result(
                f"{level.value} + {strategy.value}",
                False,
                f"实际: {result.allowed}, 预期: {expected}"
            )
    
    return passed, len(test_cases)


def test_feature_permission():
    """测试功能权限"""
    print_header("测试3: 功能权限检查")
    
    controller = create_membership_controller()
    
    test_cases = [
        # (会员等级, 功能, 预期结果)
        (MembershipLevel.FREE, Feature.BASIC_TRAINING, True),
        (MembershipLevel.FREE, Feature.HISTORY, False),
        (MembershipLevel.FREE, Feature.AGENT_MODE, False),
        (MembershipLevel.BASIC, Feature.HISTORY, True),
        (MembershipLevel.BASIC, Feature.AGENT_MODE, False),
        (MembershipLevel.PREMIUM, Feature.AGENT_MODE, True),
        (MembershipLevel.PREMIUM, Feature.EXPORT_DATA, True),
    ]
    
    passed = 0
    for level, feature, expected in test_cases:
        result = controller.can_use_feature(level, feature)
        if result.allowed == expected:
            passed += 1
            print_result(
                f"{level.value} + {feature.value}",
                True,
                f"允许: {result.allowed}"
            )
        else:
            print_result(
                f"{level.value} + {feature.value}",
                False,
                f"实际: {result.allowed}, 预期: {expected}"
            )
    
    return passed, len(test_cases)


async def test_daily_limit():
    """测试每日使用限制"""
    print_header("测试4: 每日使用限制")
    
    controller = create_membership_controller()
    
    passed = 0
    total = 3
    
    # 测试FREE用户限制
    usage = await controller.check_daily_limit("test_user_1", MembershipLevel.FREE)
    if usage.limit == 10:
        passed += 1
        print_result("FREE用户限制", True, f"限制: {usage.limit}")
    else:
        print_result("FREE用户限制", False, f"实际: {usage.limit}, 预期: 10")
    
    # 测试BASIC用户限制
    usage = await controller.check_daily_limit("test_user_2", MembershipLevel.BASIC)
    if usage.limit == 100:
        passed += 1
        print_result("BASIC用户限制", True, f"限制: {usage.limit}")
    else:
        print_result("BASIC用户限制", False, f"实际: {usage.limit}, 预期: 100")
    
    # 测试PREMIUM用户无限制
    usage = await controller.check_daily_limit("test_user_3", MembershipLevel.PREMIUM)
    if usage.limit == -1:
        passed += 1
        print_result("PREMIUM用户无限制", True, f"限制: {usage.limit}")
    else:
        print_result("PREMIUM用户无限制", False, f"实际: {usage.limit}, 预期: -1")
    
    return passed, total


async def test_usage_increment():
    """测试使用次数增加"""
    print_header("测试5: 使用次数增加")
    
    controller = create_membership_controller()
    
    passed = 0
    total = 2
    
    # 增加使用次数
    user_id = "test_increment_user"
    
    # 第一次增加
    count1 = await controller.increment_usage(user_id)
    if count1 >= 1:
        passed += 1
        print_result("第一次增加", True, f"次数: {count1}")
    else:
        print_result("第一次增加", False, f"次数: {count1}")
    
    # 第二次增加
    count2 = await controller.increment_usage(user_id)
    if count2 == count1 + 1:
        passed += 1
        print_result("第二次增加", True, f"次数: {count2}")
    else:
        print_result("第二次增加", False, f"实际: {count2}, 预期: {count1 + 1}")
    
    return passed, total


def test_level_from_string():
    """测试字符串转会员等级"""
    print_header("测试6: 字符串转会员等级")
    
    test_cases = [
        ("free", MembershipLevel.FREE),
        ("basic", MembershipLevel.BASIC),
        ("premium", MembershipLevel.PREMIUM),
        ("普通用户", MembershipLevel.FREE),
        ("普通会员", MembershipLevel.BASIC),
        ("能量会员", MembershipLevel.PREMIUM),
        ("unknown", MembershipLevel.FREE),  # 默认返回FREE
    ]
    
    passed = 0
    for level_str, expected in test_cases:
        result = get_membership_level_from_string(level_str)
        if result == expected:
            passed += 1
            print_result(f"'{level_str}'", True, f"-> {result.value}")
        else:
            print_result(f"'{level_str}'", False, f"实际: {result.value}, 预期: {expected.value}")
    
    return passed, len(test_cases)


def test_level_comparison():
    """测试会员等级对比"""
    print_header("测试7: 会员等级对比")
    
    controller = create_membership_controller()
    comparison = controller.get_level_comparison()
    
    passed = 0
    total = 2
    
    # 检查返回3个等级
    if len(comparison) == 3:
        passed += 1
        print_result("等级数量", True, f"共{len(comparison)}个等级")
    else:
        print_result("等级数量", False, f"实际: {len(comparison)}, 预期: 3")
    
    # 检查包含必要字段
    required_fields = ["level", "level_name", "daily_limit", "strategies", "features"]
    all_fields_present = all(
        all(field in item for field in required_fields)
        for item in comparison
    )
    if all_fields_present:
        passed += 1
        print_result("必要字段", True, f"包含: {required_fields}")
    else:
        print_result("必要字段", False, "缺少必要字段")
    
    return passed, total


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("  会员权限控制器验证脚本")
    print("  MembershipController Verification")
    print("="*60)
    
    total_passed = 0
    total_tests = 0
    
    # 运行同步测试
    sync_tests = [
        test_membership_configs,
        test_strategy_permission,
        test_feature_permission,
        test_level_from_string,
        test_level_comparison,
    ]
    
    for test_func in sync_tests:
        try:
            passed, total = test_func()
            total_passed += passed
            total_tests += total
        except Exception as e:
            print(f"\n❌ 测试 {test_func.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 运行异步测试
    async_tests = [
        test_daily_limit,
        test_usage_increment,
    ]
    
    for test_func in async_tests:
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
        print("\n🎉 所有测试通过！会员权限控制器实现正确。")
        return 0
    else:
        print(f"\n⚠️ {total_tests - total_passed} 个测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
