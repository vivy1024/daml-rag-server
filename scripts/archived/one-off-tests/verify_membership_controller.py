#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
会员权限控制器验证脚本

验证MembershipController的核心功能：
1. 会员配置获取
2. 策略权限检查
3. 功能权限检查
4. Feature Flag支持

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
    print(f"  {status} - {test_name}")
    if details:
        print(f"         {details}")


def test_membership_configs():
    """测试会员配置"""
    print_header("测试1: 会员配置")
    
    passed = 0
    total = 0
    
    # 检查三个等级都有配置
    for level in [MembershipLevel.FREE, MembershipLevel.WARMHEART, MembershipLevel.ENERGY]:
        total += 1
        if level in MEMBERSHIP_CONFIGS:
            config = MEMBERSHIP_CONFIGS[level]
            print_result(
                f"{level.value}等级配置存在",
                True,
                f"display_name={config.display_name}, daily_limit={config.daily_limit}"
            )
            passed += 1
        else:
            print_result(f"{level.value}等级配置存在", False)
    
    # 检查配置字段完整性
    for level, config in MEMBERSHIP_CONFIGS.items():
        total += 1
        has_all_fields = all([
            hasattr(config, 'level'),
            hasattr(config, 'display_name'),
            hasattr(config, 'allowed_strategies'),
            hasattr(config, 'daily_limit'),
            hasattr(config, 'features'),
        ])
        print_result(f"{level.value}配置字段完整", has_all_fields)
        if has_all_fields:
            passed += 1
    
    return passed, total


def test_strategy_permission():
    """测试策略权限检查"""
    print_header("测试2: 策略权限检查")
    
    controller = MembershipController()
    passed = 0
    total = 0
    
    # 测试用例
    test_cases = [
        (MembershipLevel.FREE, ExecutionStrategy.DAG, True),
        (MembershipLevel.FREE, ExecutionStrategy.AGENT, False),
        (MembershipLevel.WARMHEART, ExecutionStrategy.DAG, True),
        (MembershipLevel.WARMHEART, ExecutionStrategy.AGENT, False),
        (MembershipLevel.ENERGY, ExecutionStrategy.DAG, True),
        (MembershipLevel.ENERGY, ExecutionStrategy.AGENT, True),
    ]
    
    for level, strategy, expected in test_cases:
        total += 1
        result = controller.can_use_strategy(level, strategy)
        # 如果会员控制禁用，所有策略都允许
        if not controller.is_membership_control_enabled():
            expected = True
        
        test_passed = result.allowed == expected
        print_result(
            f"{level.value} + {strategy.value}",
            test_passed,
            f"expected={expected}, actual={result.allowed}"
        )
        if test_passed:
            passed += 1
    
    return passed, total


def test_feature_permission():
    """测试功能权限检查"""
    print_header("测试3: 功能权限检查")
    
    controller = MembershipController()
    passed = 0
    total = 0
    
    # 测试用例
    test_cases = [
        (MembershipLevel.FREE, Feature.BASIC_TRAINING, True),
        (MembershipLevel.FREE, Feature.AGENT_MODE, False),
        (MembershipLevel.WARMHEART, Feature.HISTORY, True),
        (MembershipLevel.WARMHEART, Feature.AGENT_MODE, False),
        (MembershipLevel.ENERGY, Feature.AGENT_MODE, True),
        (MembershipLevel.ENERGY, Feature.EXPORT_DATA, True),
    ]
    
    for level, feature, expected in test_cases:
        total += 1
        result = controller.can_use_feature(level, feature)
        # 如果会员控制禁用，所有功能都允许
        if not controller.is_membership_control_enabled():
            expected = True
        
        test_passed = result.allowed == expected
        print_result(
            f"{level.value} + {feature.value}",
            test_passed,
            f"expected={expected}, actual={result.allowed}"
        )
        if test_passed:
            passed += 1
    
    return passed, total


async def test_daily_limit():
    """测试每日使用限制"""
    print_header("测试4: 每日使用限制")
    
    controller = MembershipController()
    passed = 0
    total = 0
    
    # 测试免费用户限制
    total += 1
    usage = await controller.check_daily_limit("test_user_1", MembershipLevel.FREE)
    if controller.is_membership_control_enabled():
        test_passed = usage.limit == 5
    else:
        test_passed = usage.limit == -1  # 禁用时无限制
    print_result(
        "免费用户每日限制",
        test_passed,
        f"limit={usage.limit}"
    )
    if test_passed:
        passed += 1
    
    # 测试能量会员无限制
    total += 1
    usage = await controller.check_daily_limit("test_user_2", MembershipLevel.ENERGY)
    test_passed = usage.limit == -1
    print_result(
        "能量会员无限制",
        test_passed,
        f"limit={usage.limit}"
    )
    if test_passed:
        passed += 1
    
    return passed, total


def test_level_from_string():
    """测试字符串转等级"""
    print_header("测试5: 字符串转等级")
    
    passed = 0
    total = 0
    
    test_cases = [
        ("free", MembershipLevel.FREE),
        ("warmheart", MembershipLevel.WARMHEART),
        ("energy", MembershipLevel.ENERGY),
        ("FREE", MembershipLevel.FREE),
        ("WARMHEART", MembershipLevel.WARMHEART),
        ("ENERGY", MembershipLevel.ENERGY),
        ("unknown", MembershipLevel.FREE),  # 未知等级默认FREE
        ("", MembershipLevel.FREE),
    ]
    
    for input_str, expected in test_cases:
        total += 1
        result = get_membership_level_from_string(input_str)
        test_passed = result == expected
        print_result(
            f"'{input_str}' -> {expected.value}",
            test_passed,
            f"actual={result.value}"
        )
        if test_passed:
            passed += 1
    
    return passed, total


def test_feature_flag():
    """测试Feature Flag"""
    print_header("测试6: Feature Flag")
    
    controller = MembershipController()
    passed = 0
    total = 0
    
    # 检查Feature Flag状态
    total += 1
    enabled = controller.is_membership_control_enabled()
    env_value = os.getenv('USE_MEMBERSHIP_CONTROL', 'false')
    expected = env_value.lower() in ('true', '1', 'yes')
    test_passed = enabled == expected
    print_result(
        f"Feature Flag状态",
        test_passed,
        f"env={env_value}, enabled={enabled}"
    )
    if test_passed:
        passed += 1
    
    # 如果禁用，检查是否返回energy配置
    total += 1
    if not enabled:
        config = controller.get_config(MembershipLevel.FREE)
        test_passed = config.level == MembershipLevel.ENERGY
        print_result(
            "禁用时返回energy配置",
            test_passed,
            f"actual_level={config.level.value}"
        )
    else:
        config = controller.get_config(MembershipLevel.FREE)
        test_passed = config.level == MembershipLevel.FREE
        print_result(
            "启用时返回实际配置",
            test_passed,
            f"actual_level={config.level.value}"
        )
    if test_passed:
        passed += 1
    
    return passed, total


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("  会员权限控制器验证")
    print("="*60)
    
    total_passed = 0
    total_tests = 0
    
    # 运行所有测试
    p, t = test_membership_configs()
    total_passed += p
    total_tests += t
    
    p, t = test_strategy_permission()
    total_passed += p
    total_tests += t
    
    p, t = test_feature_permission()
    total_passed += p
    total_tests += t
    
    p, t = await test_daily_limit()
    total_passed += p
    total_tests += t
    
    p, t = test_level_from_string()
    total_passed += p
    total_tests += t
    
    p, t = test_feature_flag()
    total_passed += p
    total_tests += t
    
    # 打印总结
    print_header("测试总结")
    print(f"  通过: {total_passed}/{total_tests}")
    print(f"  成功率: {total_passed/total_tests*100:.1f}%")
    
    if total_passed == total_tests:
        print("\n  🎉 所有测试通过！")
        return 0
    else:
        print(f"\n  ⚠️ {total_tests - total_passed}个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
