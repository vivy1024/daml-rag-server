# -*- coding: utf-8 -*-
"""
验证MembershipController会员权限

测试内容：
1. 会员等级定义（FREE/WARMHEART/ENERGY）
2. 策略权限控制
3. 功能特性控制
4. Feature Flag支持

Requirements: 8.6
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.framework.auth.membership_controller import (
    MembershipController,
    MembershipLevel,
    ExecutionStrategy,
    Feature,
    MEMBERSHIP_CONFIGS,
    create_membership_controller,
    get_membership_level_from_string
)


def test_membership_levels():
    """测试会员等级定义"""
    print("\n" + "="*60)
    print("测试1: 会员等级定义")
    print("="*60)
    
    # 验证三个等级存在
    assert MembershipLevel.FREE.value == "free"
    assert MembershipLevel.WARMHEART.value == "warmheart"
    assert MembershipLevel.ENERGY.value == "energy"
    print("✅ 三个会员等级定义正确: FREE, WARMHEART, ENERGY")
    
    # 验证配置存在
    assert MembershipLevel.FREE in MEMBERSHIP_CONFIGS
    assert MembershipLevel.WARMHEART in MEMBERSHIP_CONFIGS
    assert MembershipLevel.ENERGY in MEMBERSHIP_CONFIGS
    print("✅ 三个等级配置存在")
    
    # 验证字符串转换
    assert get_membership_level_from_string("free") == MembershipLevel.FREE
    assert get_membership_level_from_string("warmheart") == MembershipLevel.WARMHEART
    assert get_membership_level_from_string("energy") == MembershipLevel.ENERGY
    assert get_membership_level_from_string("unknown") == MembershipLevel.FREE  # 默认FREE
    print("✅ 字符串转换正确")
    
    return True


def test_strategy_permissions():
    """测试策略权限"""
    print("\n" + "="*60)
    print("测试2: 策略权限控制")
    print("="*60)
    
    # 启用会员控制
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    controller = MembershipController()
    
    # FREE用户
    free_config = MEMBERSHIP_CONFIGS[MembershipLevel.FREE]
    assert ExecutionStrategy.DAG in free_config.allowed_strategies
    assert ExecutionStrategy.AGENT not in free_config.allowed_strategies
    print("✅ FREE用户: 只能用DAG模式")
    
    # WARMHEART用户
    warmheart_config = MEMBERSHIP_CONFIGS[MembershipLevel.WARMHEART]
    assert ExecutionStrategy.DAG in warmheart_config.allowed_strategies
    assert ExecutionStrategy.AGENT not in warmheart_config.allowed_strategies
    print("✅ WARMHEART用户: 只能用DAG模式")
    
    # ENERGY用户
    energy_config = MEMBERSHIP_CONFIGS[MembershipLevel.ENERGY]
    assert ExecutionStrategy.DAG in energy_config.allowed_strategies
    assert ExecutionStrategy.AGENT in energy_config.allowed_strategies
    print("✅ ENERGY用户: 可用DAG和Agent模式")
    
    # 测试can_use_strategy方法
    result = controller.can_use_strategy(MembershipLevel.FREE, ExecutionStrategy.AGENT)
    assert not result.allowed
    assert "升级" in result.upgrade_hint
    print("✅ FREE用户请求Agent: 被拒绝，提示升级")
    
    result = controller.can_use_strategy(MembershipLevel.WARMHEART, ExecutionStrategy.AGENT)
    assert not result.allowed
    print("✅ WARMHEART用户请求Agent: 被拒绝")
    
    result = controller.can_use_strategy(MembershipLevel.ENERGY, ExecutionStrategy.AGENT)
    assert result.allowed
    print("✅ ENERGY用户请求Agent: 允许")
    
    # 恢复环境变量
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    return True


def test_feature_permissions():
    """测试功能特性权限"""
    print("\n" + "="*60)
    print("测试3: 功能特性控制")
    print("="*60)
    
    # 启用会员控制
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    controller = MembershipController()
    
    # FREE用户功能
    free_config = MEMBERSHIP_CONFIGS[MembershipLevel.FREE]
    assert Feature.BASIC_TRAINING in free_config.features
    assert Feature.BASIC_NUTRITION in free_config.features
    assert Feature.AGENT_MODE not in free_config.features
    assert Feature.HISTORY not in free_config.features
    print("✅ FREE用户: 基础训练+营养，无Agent/历史")
    
    # WARMHEART用户功能
    warmheart_config = MEMBERSHIP_CONFIGS[MembershipLevel.WARMHEART]
    assert Feature.BASIC_TRAINING in warmheart_config.features
    assert Feature.HISTORY in warmheart_config.features
    assert Feature.CUSTOM_PLANS in warmheart_config.features
    assert Feature.AGENT_MODE not in warmheart_config.features
    print("✅ WARMHEART用户: 基础+历史+自定义计划，无Agent")
    
    # ENERGY用户功能
    energy_config = MEMBERSHIP_CONFIGS[MembershipLevel.ENERGY]
    assert Feature.AGENT_MODE in energy_config.features
    assert Feature.ADVANCED_ANALYTICS in energy_config.features
    assert Feature.EXPORT_DATA in energy_config.features
    assert Feature.PRIORITY_SUPPORT in energy_config.features
    print("✅ ENERGY用户: 全部功能")
    
    # 测试can_use_feature方法
    result = controller.can_use_feature(MembershipLevel.FREE, Feature.AGENT_MODE)
    assert not result.allowed
    print("✅ FREE用户请求Agent功能: 被拒绝")
    
    result = controller.can_use_feature(MembershipLevel.ENERGY, Feature.AGENT_MODE)
    assert result.allowed
    print("✅ ENERGY用户请求Agent功能: 允许")
    
    # 恢复环境变量
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    return True


def test_daily_limits():
    """测试每日使用限制"""
    print("\n" + "="*60)
    print("测试4: 每日使用限制")
    print("="*60)
    
    # FREE用户: 5次/天
    free_config = MEMBERSHIP_CONFIGS[MembershipLevel.FREE]
    assert free_config.daily_limit == 5
    print("✅ FREE用户: 5次/天")
    
    # WARMHEART用户: 30次/天
    warmheart_config = MEMBERSHIP_CONFIGS[MembershipLevel.WARMHEART]
    assert warmheart_config.daily_limit == 30
    print("✅ WARMHEART用户: 30次/天")
    
    # ENERGY用户: 无限制
    energy_config = MEMBERSHIP_CONFIGS[MembershipLevel.ENERGY]
    assert energy_config.daily_limit == -1
    print("✅ ENERGY用户: 无限制")
    
    return True


def test_feature_flag():
    """测试Feature Flag"""
    print("\n" + "="*60)
    print("测试5: Feature Flag支持")
    print("="*60)
    
    # 禁用会员控制
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    controller = MembershipController()
    
    assert not controller.is_membership_control_enabled()
    print("✅ USE_MEMBERSHIP_CONTROL=false: 会员控制禁用")
    
    # 禁用时，所有用户都可以使用Agent
    result = controller.can_use_strategy(MembershipLevel.FREE, ExecutionStrategy.AGENT)
    assert result.allowed
    print("✅ 禁用时FREE用户可用Agent")
    
    # 启用会员控制
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    controller = MembershipController()
    
    assert controller.is_membership_control_enabled()
    print("✅ USE_MEMBERSHIP_CONTROL=true: 会员控制启用")
    
    # 启用时，FREE用户不能使用Agent
    result = controller.can_use_strategy(MembershipLevel.FREE, ExecutionStrategy.AGENT)
    assert not result.allowed
    print("✅ 启用时FREE用户不可用Agent")
    
    # 恢复环境变量
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    return True


def test_level_comparison():
    """测试等级对比信息"""
    print("\n" + "="*60)
    print("测试6: 等级对比信息")
    print("="*60)
    
    controller = MembershipController()
    comparison = controller.get_level_comparison()
    
    assert len(comparison) == 3
    print(f"✅ 返回3个等级的对比信息")
    
    # 验证每个等级的信息完整
    for level_info in comparison:
        assert "level" in level_info
        assert "display_name" in level_info
        assert "allowed_strategies" in level_info
        assert "daily_limit" in level_info
        assert "features" in level_info
        print(f"   - {level_info['display_name']}: {level_info['level']}")
    
    return True


def main():
    """运行所有测试"""
    print("="*60)
    print("MembershipController会员权限验证测试")
    print("="*60)
    
    tests = [
        ("会员等级定义", test_membership_levels),
        ("策略权限控制", test_strategy_permissions),
        ("功能特性控制", test_feature_permissions),
        ("每日使用限制", test_daily_limits),
        ("Feature Flag支持", test_feature_flag),
        ("等级对比信息", test_level_comparison),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"❌ {name} 失败")
        except Exception as e:
            failed += 1
            print(f"❌ {name} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"测试结果: {passed}/{passed+failed} 通过")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
