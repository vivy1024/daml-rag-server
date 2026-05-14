# -*- coding: utf-8 -*-
"""
Skills架构基础测试脚本
"""
import sys
sys.path.insert(0, '/app')

def main():
    # 测试1: 导入模块
    print('=== 测试1: 导入模块 ===')
    try:
        from src.framework.skills import (
            SkillCategory, SkillMetadata, SkillContent, Skill,
            SkillManager, LoadSkillTool,
            is_skills_mode_enabled, get_skills_config
        )
        from src.framework.orchestration.strategy_selector import (
            ExecutionStrategy, StrategyDecision, StrategySelector, SimpleQueryDetector
        )
        from src.framework.auth.membership_controller import (
            MembershipLevel, MembershipController, get_membership_level_from_string
        )
        print('✅ 所有模块导入成功')
    except Exception as e:
        print(f'❌ 导入失败: {e}')
        import traceback
        traceback.print_exc()
        return 1

    # 测试2: 创建技能元数据
    print('\n=== 测试2: 创建技能元数据 ===')
    metadata = SkillMetadata(
        skill_id='test_skill',
        name='测试技能',
        description='这是一个测试技能',
        category=SkillCategory.TRAINING,
        keywords=['测试', '训练']
    )
    print(f'✅ 技能元数据创建成功: {metadata.skill_id}')
    print(f'   System Prompt格式: {metadata.to_system_prompt_format()}')

    # 测试3: 创建技能内容
    print('\n=== 测试3: 创建技能内容 ===')
    content = SkillContent(
        skill_id='test_skill',
        full_description='这是测试技能的完整描述',
        applicable_intents=['测试意图'],
        required_tools=['tool1'],
        optional_tools=[],
        tool_dependencies={},
        parallel_groups=[],
        safety_constraints=['安全约束1'],
        response_hint='响应提示'
    )
    skill_md = content.to_skill_md()
    print(f'✅ 技能内容创建成功')
    print(f'   SKILL.md长度: {len(skill_md)} 字符')

    # 测试4: SkillManager
    print('\n=== 测试4: SkillManager ===')
    manager = SkillManager()
    skill = Skill(metadata=metadata, content=content)
    manager.register_skill(skill)
    print(f'✅ 技能注册成功: {manager.get_skill_count()} 个技能')

    # 测试5: 加载技能
    print('\n=== 测试5: 加载技能 ===')
    loaded = manager.load_skill('test_skill')
    print(f'✅ 技能加载成功')
    print(f'   已加载技能: {manager.get_loaded_skills()}')

    # 测试6: 技能匹配
    print('\n=== 测试6: 技能匹配 ===')
    matched = manager.match_skill_by_query('我想测试训练')
    print(f'✅ 技能匹配结果: {matched}')

    # 测试7: SimpleQueryDetector
    print('\n=== 测试7: SimpleQueryDetector ===')
    detector = SimpleQueryDetector()
    result1 = detector.is_simple_query('你好')
    result2 = detector.is_simple_query('帮我制定训练计划')
    print(f'   你好 是简单查询: {result1}')
    print(f'   帮我制定训练计划 是简单查询: {result2}')
    assert result1 == True, '你好应该是简单查询'
    assert result2 == False, '帮我制定训练计划不应该是简单查询'
    print('✅ SimpleQueryDetector测试通过')

    # 测试8: MembershipController
    print('\n=== 测试8: MembershipController ===')
    controller = MembershipController()
    print(f'✅ MembershipController创建成功')
    print(f'   会员控制启用: {controller.is_membership_control_enabled()}')

    # 测试9: 会员等级转换
    print('\n=== 测试9: 会员等级转换 ===')
    level_free = get_membership_level_from_string('free')
    level_warmheart = get_membership_level_from_string('warmheart')
    level_energy = get_membership_level_from_string('energy')
    print(f'   free -> {level_free}')
    print(f'   warmheart -> {level_warmheart}')
    print(f'   energy -> {level_energy}')
    assert level_free == MembershipLevel.FREE
    assert level_warmheart == MembershipLevel.WARMHEART
    assert level_energy == MembershipLevel.ENERGY
    print('✅ 会员等级转换测试通过')

    # 测试10: Skills配置
    print('\n=== 测试10: Skills配置 ===')
    config = get_skills_config()
    print(f'✅ Skills配置获取成功')
    print(f'   skills_mode_enabled: {config["skills_mode_enabled"]}')
    print(f'   agent_mode_enabled: {config["agent_mode_enabled"]}')

    # 测试11: Token估算
    print('\n=== 测试11: Token估算 ===')
    tokens = manager.estimate_system_prompt_tokens()
    print(f'✅ Token估算: {tokens} tokens')

    # 测试12: 统计信息
    print('\n=== 测试12: 统计信息 ===')
    stats = manager.get_statistics()
    print(f'✅ 统计信息:')
    print(f'   total_skills: {stats["total_skills"]}')
    print(f'   loaded_skills_count: {stats["loaded_skills_count"]}')
    print(f'   total_load_count: {stats["total_load_count"]}')

    print('\n🎉 所有测试通过!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
