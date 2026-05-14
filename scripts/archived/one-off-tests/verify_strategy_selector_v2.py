# -*- coding: utf-8 -*-
"""
验证简化版StrategySelector

测试内容：
1. 技能匹配功能
2. 会员权限控制
3. 策略选择逻辑
4. 统计信息

Requirements: 8.5, 8.6
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.framework.orchestration.strategy_selector import (
    StrategySelector,
    ExecutionStrategy,
    StrategyDecision,
    create_strategy_selector
)
from src.framework.auth.membership_controller import (
    MembershipController,
    MembershipLevel,
    create_membership_controller,
    get_membership_level_from_string
)
from src.framework.skills.skill_manager import SkillManager


def test_strategy_selector_initialization():
    """测试StrategySelector初始化"""
    print("\n" + "="*60)
    print("测试1: StrategySelector初始化")
    print("="*60)
    
    # 1. 基本初始化
    selector = StrategySelector()
    assert selector is not None
    print("✅ 基本初始化成功")
    
    # 2. 带SkillManager初始化
    skill_manager = SkillManager()
    selector = StrategySelector(skill_manager=skill_manager)
    assert selector.skill_manager is not None
    print("✅ 带SkillManager初始化成功")
    
    # 3. 带MembershipController初始化
    membership_controller = MembershipController()
    selector = StrategySelector(
        skill_manager=skill_manager,
        membership_controller=membership_controller
    )
    assert selector.membership_controller is not None
    print("✅ 带MembershipController初始化成功")
    
    # 4. 使用工厂函数
    selector = create_strategy_selector(
        skill_manager=skill_manager,
        membership_controller=membership_controller
    )
    assert selector is not None
    print("✅ 工厂函数创建成功")
    
    return True


async def test_simple_query_detection():
    """测试简单查询检测"""
    print("\n" + "="*60)
    print("测试2: 简单查询检测")
    print("="*60)
    
    selector = StrategySelector()
    
    # 简单查询应该使用DAG模式
    simple_queries = [
        "你好",
        "谢谢",
        "好的",
        "嗯",
        "是的"
    ]
    
    for query in simple_queries:
        decision = await selector.select_strategy(
            query=query,
            user_profile={}
        )
        assert decision.strategy == ExecutionStrategy.DAG
        assert decision.metadata.get("simple_query", False)
        print(f"✅ '{query}' -> DAG模式（简单查询）")
    
    return True


async def test_skill_matching():
    """测试技能匹配"""
    print("\n" + "="*60)
    print("测试3: 技能匹配")
    print("="*60)
    
    # 创建SkillManager并注册一些测试技能
    from src.framework.skills.skill_definition import Skill, SkillMetadata, SkillContent, SkillCategory
    
    skill_manager = SkillManager()
    
    # 注册测试技能
    training_skill = Skill(
        metadata=SkillMetadata(
            skill_id="complete_training_plan",
            name="完整训练计划",
            description="制定完整的训练计划",
            category=SkillCategory.TRAINING,
            keywords=["训练计划", "健身计划", "增肌", "减脂", "训练"]
        ),
        content=SkillContent(
            skill_id="complete_training_plan",
            full_description="制定完整的训练计划，包括动作选择、组数、次数等",
            applicable_intents=["训练计划", "健身计划"],
            required_tools=["intelligent_exercise_selector"],
            optional_tools=[],
            tool_dependencies={},
            parallel_groups=[],
            safety_constraints=["检查用户健康状况"],
            response_hint="提供详细的训练计划"
        )
    )
    skill_manager.register_skill(training_skill)
    
    nutrition_skill = Skill(
        metadata=SkillMetadata(
            skill_id="nutrition_planning",
            name="营养规划",
            description="制定营养方案",
            category=SkillCategory.NUTRITION,
            keywords=["营养", "饮食", "食谱", "热量", "蛋白质"]
        ),
        content=SkillContent(
            skill_id="nutrition_planning",
            full_description="制定营养方案",
            applicable_intents=["营养规划", "饮食计划"],
            required_tools=["tdee_calculator"],
            optional_tools=[],
            tool_dependencies={},
            parallel_groups=[],
            safety_constraints=[],
            response_hint="提供营养建议"
        )
    )
    skill_manager.register_skill(nutrition_skill)
    
    selector = StrategySelector(skill_manager=skill_manager)
    
    # 测试技能匹配
    test_cases = [
        ("帮我制定一个训练计划", "complete_training_plan"),
        ("我想增肌，请帮我制定计划", "complete_training_plan"),
        ("请帮我制定营养方案", "nutrition_planning"),
        ("每天应该吃多少蛋白质", "nutrition_planning"),
    ]
    
    for query, expected_skill in test_cases:
        decision = await selector.select_strategy(
            query=query,
            user_profile={}
        )
        assert decision.strategy == ExecutionStrategy.DAG
        assert decision.skill_id == expected_skill, f"Expected {expected_skill}, got {decision.skill_id}"
        print(f"✅ '{query}' -> 技能: {decision.skill_id}")
    
    return True


async def test_membership_permission():
    """测试会员权限控制"""
    print("\n" + "="*60)
    print("测试4: 会员权限控制")
    print("="*60)
    
    # 设置环境变量启用会员控制
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    
    membership_controller = MembershipController()
    selector = StrategySelector(membership_controller=membership_controller)
    
    # 测试FREE用户强制使用Agent模式（应该被降级）
    decision = await selector.select_strategy(
        query="复杂问题",
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT,
        membership_level="free"
    )
    assert decision.strategy == ExecutionStrategy.DAG
    assert decision.membership_restricted == True
    print("✅ FREE用户强制Agent -> 降级到DAG")
    
    # 测试WARMHEART用户强制使用Agent模式（应该被降级）
    decision = await selector.select_strategy(
        query="复杂问题",
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT,
        membership_level="warmheart"
    )
    assert decision.strategy == ExecutionStrategy.DAG
    assert decision.membership_restricted == True
    print("✅ WARMHEART用户强制Agent -> 降级到DAG")
    
    # 测试ENERGY用户强制使用Agent模式（应该允许）
    decision = await selector.select_strategy(
        query="复杂问题",
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT,
        membership_level="energy"
    )
    assert decision.strategy == ExecutionStrategy.AGENT
    assert decision.membership_restricted == False
    print("✅ ENERGY用户强制Agent -> 允许Agent")
    
    # 恢复环境变量
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    return True


async def test_statistics():
    """测试统计信息"""
    print("\n" + "="*60)
    print("测试5: 统计信息")
    print("="*60)
    
    selector = StrategySelector()
    
    # 执行一些策略选择
    await selector.select_strategy(query="你好", user_profile={})
    await selector.select_strategy(query="训练计划", user_profile={})
    await selector.select_strategy(query="谢谢", user_profile={})
    
    stats = selector.get_statistics()
    
    assert stats["total_selections"] == 3
    assert stats["dag_count"] == 3  # 所有都应该是DAG模式
    print(f"✅ 统计信息: {stats}")
    
    # 重置统计
    selector.reset_statistics()
    stats = selector.get_statistics()
    assert stats["total_selections"] == 0
    print("✅ 统计信息重置成功")
    
    return True


async def test_membership_disabled():
    """测试会员控制禁用时的行为"""
    print("\n" + "="*60)
    print("测试6: 会员控制禁用")
    print("="*60)
    
    # 确保会员控制禁用
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'
    
    membership_controller = MembershipController()
    selector = StrategySelector(membership_controller=membership_controller)
    
    # 禁用时，FREE用户也可以使用Agent模式
    decision = await selector.select_strategy(
        query="复杂问题",
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT,
        membership_level="free"
    )
    assert decision.strategy == ExecutionStrategy.AGENT
    assert decision.membership_restricted == False
    print("✅ 会员控制禁用时，FREE用户可使用Agent")
    
    return True


async def main():
    """运行所有测试"""
    print("="*60)
    print("StrategySelector简化版验证测试")
    print("="*60)
    
    tests = [
        ("初始化测试", test_strategy_selector_initialization),
        ("简单查询检测", test_simple_query_detection),
        ("技能匹配", test_skill_matching),
        ("会员权限控制", test_membership_permission),
        ("统计信息", test_statistics),
        ("会员控制禁用", test_membership_disabled),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
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
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
