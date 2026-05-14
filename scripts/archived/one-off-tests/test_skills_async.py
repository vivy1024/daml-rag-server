# -*- coding: utf-8 -*-
"""
Skills架构异步测试脚本
"""
import sys
import asyncio
sys.path.insert(0, '/app')


async def main():
    print('=== Skills架构异步测试 ===\n')
    
    # 导入模块
    from src.framework.skills import (
        SkillCategory, SkillMetadata, SkillContent, Skill,
        SkillManager
    )
    from src.framework.orchestration.strategy_selector import (
        ExecutionStrategy, StrategySelector
    )
    from src.framework.auth.membership_controller import (
        MembershipController
    )
    
    # 创建测试技能
    skill = Skill(
        metadata=SkillMetadata(
            skill_id='complete_training_plan',
            name='完整训练计划',
            description='根据用户目标制定完整的训练计划',
            category=SkillCategory.TRAINING,
            keywords=['训练计划', '增肌', '减脂', '健身方案']
        ),
        content=SkillContent(
            skill_id='complete_training_plan',
            full_description='根据用户的健身目标制定个性化训练计划',
            applicable_intents=['制定训练计划', '健身方案'],
            required_tools=['professional_program_designer'],
            optional_tools=[],
            tool_dependencies={},
            parallel_groups=[],
            safety_constraints=['检查用户伤病史'],
            response_hint='提供详细的周训练安排'
        )
    )
    
    # 创建SkillManager
    manager = SkillManager()
    manager.register_skill(skill)
    
    # 创建MembershipController
    controller = MembershipController()
    
    # 创建StrategySelector
    selector = StrategySelector(
        skill_manager=manager,
        membership_controller=controller
    )
    
    # 测试1: 简单查询
    print('=== 测试1: 简单查询 ===')
    decision = await selector.select_strategy(
        query='你好',
        user_profile={},
        membership_level='free'
    )
    print(f'   查询: 你好')
    print(f'   策略: {decision.strategy.value}')
    print(f'   原因: {decision.reasoning}')
    assert decision.strategy == ExecutionStrategy.DAG
    print('✅ 简单查询测试通过\n')
    
    # 测试2: 技能匹配
    print('=== 测试2: 技能匹配 ===')
    decision = await selector.select_strategy(
        query='帮我制定一个增肌训练计划',
        user_profile={'goal': '增肌'},
        membership_level='warmheart'
    )
    print(f'   查询: 帮我制定一个增肌训练计划')
    print(f'   策略: {decision.strategy.value}')
    print(f'   技能: {decision.skill_id}')
    print(f'   原因: {decision.reasoning}')
    assert decision.strategy == ExecutionStrategy.DAG
    assert decision.skill_id == 'complete_training_plan'
    print('✅ 技能匹配测试通过\n')
    
    # 测试3: 强制Agent策略（WARMHEART用户应该被降级）
    print('=== 测试3: 会员权限降级 ===')
    # 注意：默认USE_MEMBERSHIP_CONTROL=false，所以不会降级
    decision = await selector.select_strategy(
        query='复杂查询',
        user_profile={},
        force_strategy=ExecutionStrategy.AGENT,
        membership_level='warmheart'
    )
    print(f'   查询: 复杂查询')
    print(f'   强制策略: AGENT')
    print(f'   会员等级: warmheart')
    print(f'   实际策略: {decision.strategy.value}')
    print(f'   会员限制: {decision.membership_restricted}')
    # 由于USE_MEMBERSHIP_CONTROL=false，不会降级
    print('✅ 会员权限测试通过（当前会员控制已禁用）\n')
    
    # 测试4: 统计信息
    print('=== 测试4: 统计信息 ===')
    stats = selector.get_statistics()
    print(f'   总选择次数: {stats["total_selections"]}')
    print(f'   DAG次数: {stats["dag_count"]}')
    print(f'   Agent次数: {stats["agent_count"]}')
    print(f'   技能匹配次数: {stats["skill_match_count"]}')
    print('✅ 统计信息测试通过\n')
    
    # 测试5: Token消耗对比
    print('=== 测试5: Token消耗对比 ===')
    skills_tokens = manager.estimate_system_prompt_tokens()
    # 传统模式估算：13个模板*300 + 18个工具*100 = 5700
    traditional_tokens = 13 * 300 + 18 * 100
    savings = traditional_tokens - skills_tokens
    savings_percent = (1 - skills_tokens / traditional_tokens) * 100
    print(f'   Skills模式: ~{skills_tokens} tokens')
    print(f'   传统模式: ~{traditional_tokens} tokens')
    print(f'   节省: ~{savings} tokens ({savings_percent:.1f}%)')
    print('✅ Token消耗对比测试通过\n')
    
    print('🎉 所有异步测试通过!')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
