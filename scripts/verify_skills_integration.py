# -*- coding: utf-8 -*-
"""
验证Skills架构集成

测试内容：
1. SkillsIntegration初始化
2. 从领域适配器加载技能
3. 策略选择集成
4. Feature Flag控制

Requirements: 8.5, 8.6, 8.7
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.framework.skills.skills_integration import (
    SkillsIntegration,
    get_skills_integration,
    initialize_skills_from_adapter,
    is_skills_mode_enabled,
    is_agent_mode_enabled,
)
from src.framework.skills.skill_manager import SkillManager
from src.framework.skills.skill_definition import Skill, SkillMetadata, SkillContent, SkillCategory
from src.framework.auth.membership_controller import MembershipController


def test_skills_integration_initialization():
    """测试SkillsIntegration初始化"""
    print("\n" + "="*60)
    print("测试1: SkillsIntegration初始化")
    print("="*60)
    
    # 重置单例
    SkillsIntegration.reset_instance()
    
    # 1. 通过单例获取
    integration = get_skills_integration()
    assert integration is not None
    assert not integration.is_initialized()
    print("✅ 基本初始化成功")
    
    # 2. 单例模式
    integration2 = get_skills_integration()
    assert integration2 is integration
    print("✅ 单例模式正常")
    
    # 3. Feature Flags
    print(f"   Skills模式: {'启用' if integration.is_skills_mode_enabled() else '禁用'}")
    print(f"   Agent模式: {'启用' if integration.is_agent_mode_enabled() else '禁用'}")
    
    return True


def test_initialize_with_skill_manager():
    """测试使用SkillManager初始化"""
    print("\n" + "="*60)
    print("测试2: 使用SkillManager初始化")
    print("="*60)
    
    # 重置单例
    SkillsIntegration.reset_instance()
    
    # 创建SkillManager并注册技能
    skill_manager = SkillManager()
    
    # 注册测试技能
    training_skill = Skill(
        metadata=SkillMetadata(
            skill_id="complete_training_plan",
            name="完整训练计划",
            description="制定完整的训练计划",
            category=SkillCategory.TRAINING,
            keywords=["训练计划", "健身计划", "增肌", "减脂"]
        ),
        content=SkillContent(
            skill_id="complete_training_plan",
            full_description="制定完整的训练计划",
            applicable_intents=["训练计划"],
            required_tools=["intelligent_exercise_selector"],
            optional_tools=[],
            tool_dependencies={},
            parallel_groups=[],
            safety_constraints=[],
            response_hint="提供详细的训练计划"
        )
    )
    skill_manager.register_skill(training_skill)
    
    # 初始化集成器
    integration = get_skills_integration()
    integration.initialize_with_skill_manager(skill_manager)
    
    assert integration.is_initialized()
    assert integration.get_skill_manager() is skill_manager
    assert integration.get_strategy_selector() is not None
    print("✅ 使用SkillManager初始化成功")
    
    # 测试技能访问
    skills_prompt = integration.get_skills_prompt()
    assert "complete_training_plan" in skills_prompt
    print("✅ 技能列表生成成功")
    
    # 测试技能加载
    skill_content = integration.load_skill("complete_training_plan")
    assert "complete_training_plan" in skill_content or "训练计划" in skill_content
    print("✅ 技能加载成功")
    
    # 测试技能匹配
    matched = integration.match_skill("帮我制定训练计划")
    assert matched == "complete_training_plan"
    print("✅ 技能匹配成功")
    
    return True


async def test_strategy_selection():
    """测试策略选择集成"""
    print("\n" + "="*60)
    print("测试3: 策略选择集成")
    print("="*60)
    
    # 重置单例
    SkillsIntegration.reset_instance()
    
    # 创建SkillManager
    skill_manager = SkillManager()
    training_skill = Skill(
        metadata=SkillMetadata(
            skill_id="complete_training_plan",
            name="完整训练计划",
            description="制定完整的训练计划",
            category=SkillCategory.TRAINING,
            keywords=["训练计划", "健身计划"]
        ),
        content=SkillContent(
            skill_id="complete_training_plan",
            full_description="制定完整的训练计划",
            applicable_intents=["训练计划"],
            required_tools=["intelligent_exercise_selector"],
            optional_tools=[],
            tool_dependencies={},
            parallel_groups=[],
            safety_constraints=[],
            response_hint="提供详细的训练计划"
        )
    )
    skill_manager.register_skill(training_skill)
    
    # 初始化集成器
    integration = get_skills_integration()
    integration.initialize_with_skill_manager(skill_manager)
    
    # 测试策略选择
    decision = await integration.select_strategy(
        query="帮我制定一个训练计划",
        user_profile={}
    )
    
    assert decision["strategy"] == "dag"
    assert decision["skill_id"] == "complete_training_plan"
    print(f"✅ 策略选择成功: {decision['strategy']}, 技能: {decision['skill_id']}")
    
    return True


def test_feature_flags():
    """测试Feature Flag控制"""
    print("\n" + "="*60)
    print("测试4: Feature Flag控制")
    print("="*60)
    
    # 重置单例
    SkillsIntegration.reset_instance()
    
    integration = get_skills_integration()
    
    # 测试运行时设置
    integration.set_skills_mode(True)
    assert integration.is_skills_mode_enabled()
    print("✅ Skills模式启用成功")
    
    integration.set_skills_mode(False)
    assert not integration.is_skills_mode_enabled()
    print("✅ Skills模式禁用成功")
    
    integration.set_agent_mode(True)
    assert integration.is_agent_mode_enabled()
    print("✅ Agent模式启用成功")
    
    integration.set_agent_mode(False)
    assert not integration.is_agent_mode_enabled()
    print("✅ Agent模式禁用成功")
    
    return True


def test_statistics():
    """测试统计信息"""
    print("\n" + "="*60)
    print("测试5: 统计信息")
    print("="*60)
    
    # 重置单例
    SkillsIntegration.reset_instance()
    
    # 创建并初始化
    skill_manager = SkillManager()
    integration = get_skills_integration()
    integration.initialize_with_skill_manager(skill_manager)
    
    stats = integration.get_statistics()
    
    assert "initialized" in stats
    assert stats["initialized"] == True
    assert "skills_mode_enabled" in stats
    assert "agent_mode_enabled" in stats
    print(f"✅ 统计信息: {stats}")
    
    return True


async def main():
    """运行所有测试"""
    print("="*60)
    print("Skills架构集成验证测试")
    print("="*60)
    
    tests = [
        ("初始化测试", test_skills_integration_initialization),
        ("SkillManager初始化", test_initialize_with_skill_manager),
        ("策略选择集成", test_strategy_selection),
        ("Feature Flag控制", test_feature_flags),
        ("统计信息", test_statistics),
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
