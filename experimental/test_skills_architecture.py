# -*- coding: utf-8 -*-
"""
Skills架构测试用例

测试内容：
1. DAG模式测试（技能匹配+执行）
2. Agent模式测试（load_skill+工具调用）
3. 会员权限测试（降级逻辑）
4. Token消耗对比测试

Requirements: Task 9.8

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# 导入被测试的模块
from src.framework.skills import (
    SkillCategory,
    SkillMetadata,
    SkillContent,
    SkillExecution,
    Skill,
    SkillManager,
    LoadSkillTool,
    LoadSkillInput,
    AgentAction,
    AgentDecision,
    AgentExecutionResult,
    SkillsAgentExecutor,
    is_skills_mode_enabled,
    is_agent_mode_enabled,
    get_skills_config,
)

from src.framework.orchestration.strategy_selector import (
    ExecutionStrategy,
    StrategyDecision,
    StrategySelector,
    SimpleQueryDetector,
)

from src.framework.auth.membership_controller import (
    MembershipLevel,
    MembershipController,
    MembershipConfig,
    PermissionCheckResult,
    get_membership_level_from_string,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_skill_metadata():
    """创建示例技能元数据"""
    return SkillMetadata(
        skill_id="complete_training_plan",
        name="完整训练计划",
        description="根据用户目标制定完整的训练计划",
        category=SkillCategory.TRAINING,
        keywords=["训练计划", "增肌", "减脂", "健身方案"]
    )


@pytest.fixture
def sample_skill_content():
    """创建示例技能内容"""
    return SkillContent(
        skill_id="complete_training_plan",
        full_description="根据用户的健身目标、身体状况和时间安排，制定个性化的训练计划。",
        applicable_intents=["制定训练计划", "健身方案", "增肌计划", "减脂计划"],
        required_tools=["professional_program_designer", "exercise_search"],
        optional_tools=["nutrition_calculator"],
        tool_dependencies={"professional_program_designer": ["exercise_search"]},
        parallel_groups=[["exercise_search"]],
        safety_constraints=["检查用户伤病史", "避免过度训练"],
        response_hint="提供详细的周训练安排和动作说明"
    )


@pytest.fixture
def sample_skill(sample_skill_metadata, sample_skill_content):
    """创建示例完整技能"""
    return Skill(
        metadata=sample_skill_metadata,
        content=sample_skill_content
    )


@pytest.fixture
def skill_manager(sample_skill):
    """创建带有示例技能的SkillManager"""
    manager = SkillManager()
    manager.register_skill(sample_skill)
    return manager


@pytest.fixture
def membership_controller():
    """创建MembershipController"""
    return MembershipController()


@pytest.fixture
def strategy_selector(skill_manager, membership_controller):
    """创建StrategySelector"""
    return StrategySelector(
        skill_manager=skill_manager,
        membership_controller=membership_controller
    )


# =============================================================================
# 1. DAG模式测试（技能匹配+执行）
# =============================================================================

class TestDAGMode:
    """DAG模式测试"""
    
    def test_skill_metadata_creation(self, sample_skill_metadata):
        """测试技能元数据创建"""
        assert sample_skill_metadata.skill_id == "complete_training_plan"
        assert sample_skill_metadata.category == SkillCategory.TRAINING
        assert len(sample_skill_metadata.keywords) == 4
    
    def test_skill_metadata_to_system_prompt(self, sample_skill_metadata):
        """测试技能元数据转换为system prompt格式"""
        prompt = sample_skill_metadata.to_system_prompt_format()
        assert "complete_training_plan" in prompt
        assert "根据用户目标制定完整的训练计划" in prompt
    
    def test_skill_content_to_skill_md(self, sample_skill_content):
        """测试技能内容转换为SKILL.md格式"""
        skill_md = sample_skill_content.to_skill_md()
        assert "complete_training_plan" in skill_md
        assert "professional_program_designer" in skill_md
        assert "检查用户伤病史" in skill_md
    
    def test_skill_manager_register(self, skill_manager):
        """测试技能注册"""
        assert skill_manager.get_skill_count() == 1
        assert "complete_training_plan" in skill_manager.list_skills()
    
    def test_skill_manager_get_system_prompt(self, skill_manager):
        """测试生成system prompt技能列表"""
        prompt = skill_manager.get_system_prompt_skills()
        assert "可用技能" in prompt
        assert "complete_training_plan" in prompt
        assert "load_skill" in prompt
    
    def test_skill_manager_load_skill(self, skill_manager):
        """测试加载技能内容"""
        content = skill_manager.load_skill("complete_training_plan")
        assert "complete_training_plan" in content
        assert "professional_program_designer" in content
        
        # 验证已加载
        assert "complete_training_plan" in skill_manager.get_loaded_skills()
    
    def test_skill_manager_load_nonexistent_skill(self, skill_manager):
        """测试加载不存在的技能"""
        content = skill_manager.load_skill("nonexistent_skill")
        assert "错误" in content or "不存在" in content
    
    def test_skill_manager_match_by_query(self, skill_manager):
        """测试根据查询匹配技能"""
        # 应该匹配到训练计划技能
        matched = skill_manager.match_skill_by_query("帮我制定一个增肌训练计划")
        assert matched == "complete_training_plan"
        
        # 不相关的查询不应该匹配
        matched = skill_manager.match_skill_by_query("今天天气怎么样")
        assert matched is None
    
    @pytest.mark.asyncio
    async def test_strategy_selector_dag_mode(self, strategy_selector):
        """测试策略选择器选择DAG模式"""
        decision = await strategy_selector.select_strategy(
            query="帮我制定一个增肌训练计划",
            user_profile={"goal": "增肌"},
            membership_level="warmheart"
        )
        
        assert decision.strategy == ExecutionStrategy.DAG
        assert decision.skill_id == "complete_training_plan"
    
    def test_simple_query_detector(self):
        """测试简单查询检测器"""
        detector = SimpleQueryDetector()
        
        # 简单查询
        assert detector.is_simple_query("你好") == True
        assert detector.is_simple_query("谢谢") == True
        assert detector.is_simple_query("好的") == True
        
        # 复杂查询
        assert detector.is_simple_query("帮我制定一个增肌训练计划") == False


# =============================================================================
# 2. Agent模式测试（load_skill+工具调用）
# =============================================================================

class TestAgentMode:
    """Agent模式测试"""
    
    def test_load_skill_tool_creation(self, skill_manager):
        """测试LoadSkillTool创建"""
        tool = LoadSkillTool(skill_manager)
        assert tool.get_name() == "load_skill"
        assert "加载技能" in tool.get_description()
    
    @pytest.mark.asyncio
    async def test_load_skill_tool_execute(self, skill_manager):
        """测试LoadSkillTool执行"""
        tool = LoadSkillTool(skill_manager)
        
        result = await tool.execute({"skill_id": "complete_training_plan"})
        
        assert result["success"] == True
        assert result["skill_id"] == "complete_training_plan"
        assert "content" in result
    
    @pytest.mark.asyncio
    async def test_load_skill_tool_execute_nonexistent(self, skill_manager):
        """测试LoadSkillTool执行不存在的技能"""
        tool = LoadSkillTool(skill_manager)
        
        result = await tool.execute({"skill_id": "nonexistent"})
        
        assert "error" in result
    
    def test_agent_decision_dataclass(self):
        """测试AgentDecision数据类"""
        decision = AgentDecision(
            action=AgentAction.LOAD_SKILL,
            skill_id="complete_training_plan",
            reasoning="用户需要训练计划"
        )
        
        assert decision.action == AgentAction.LOAD_SKILL
        assert decision.skill_id == "complete_training_plan"
    
    def test_agent_execution_result_dataclass(self):
        """测试AgentExecutionResult数据类"""
        result = AgentExecutionResult(
            success=True,
            response="这是您的训练计划...",
            iterations=3,
            skills_loaded=["complete_training_plan"],
            tool_calls=[{"tool": "exercise_search", "result": {}}],
            total_time_ms=1500.0
        )
        
        assert result.success == True
        assert result.iterations == 3
        assert len(result.skills_loaded) == 1


# =============================================================================
# 3. 会员权限测试（降级逻辑）
# =============================================================================

class TestMembershipPermission:
    """会员权限测试"""
    
    def test_membership_level_from_string(self):
        """测试从字符串获取会员等级"""
        assert get_membership_level_from_string("free") == MembershipLevel.FREE
        assert get_membership_level_from_string("warmheart") == MembershipLevel.WARMHEART
        assert get_membership_level_from_string("energy") == MembershipLevel.ENERGY
        assert get_membership_level_from_string("invalid") == MembershipLevel.FREE
    
    def test_membership_controller_dag_permission(self, membership_controller):
        """测试DAG模式权限（所有用户都可以）"""
        from src.framework.auth.membership_controller import ExecutionStrategy as MembershipStrategy
        
        # 所有等级都可以使用DAG
        for level in [MembershipLevel.FREE, MembershipLevel.WARMHEART, MembershipLevel.ENERGY]:
            result = membership_controller.can_use_strategy(level, MembershipStrategy.DAG)
            assert result.allowed == True
    
    @patch.dict('os.environ', {'USE_MEMBERSHIP_CONTROL': 'true'})
    def test_membership_controller_agent_permission_enabled(self):
        """测试Agent模式权限（启用会员控制）"""
        from src.framework.auth.membership_controller import ExecutionStrategy as MembershipStrategy
        
        # 重新创建控制器以应用环境变量
        controller = MembershipController()
        
        # FREE和WARMHEART不能使用Agent
        result = controller.can_use_strategy(MembershipLevel.FREE, MembershipStrategy.AGENT)
        assert result.allowed == False
        assert "升级" in result.upgrade_hint
        
        result = controller.can_use_strategy(MembershipLevel.WARMHEART, MembershipStrategy.AGENT)
        assert result.allowed == False
        
        # ENERGY可以使用Agent
        result = controller.can_use_strategy(MembershipLevel.ENERGY, MembershipStrategy.AGENT)
        assert result.allowed == True
    
    @pytest.mark.asyncio
    async def test_strategy_selector_membership_downgrade(self, skill_manager):
        """测试策略选择器会员降级逻辑"""
        with patch.dict('os.environ', {'USE_MEMBERSHIP_CONTROL': 'true'}):
            controller = MembershipController()
            selector = StrategySelector(
                skill_manager=skill_manager,
                membership_controller=controller
            )
            
            # WARMHEART用户强制使用Agent应该被降级
            decision = await selector.select_strategy(
                query="复杂查询",
                user_profile={},
                force_strategy=ExecutionStrategy.AGENT,
                membership_level="warmheart"
            )
            
            assert decision.strategy == ExecutionStrategy.DAG
            assert decision.membership_restricted == True
            assert decision.original_strategy == ExecutionStrategy.AGENT
    
    @pytest.mark.asyncio
    async def test_strategy_selector_energy_can_use_agent(self, skill_manager):
        """测试ENERGY会员可以使用Agent模式"""
        with patch.dict('os.environ', {'USE_MEMBERSHIP_CONTROL': 'true'}):
            controller = MembershipController()
            selector = StrategySelector(
                skill_manager=skill_manager,
                membership_controller=controller
            )
            
            # ENERGY用户强制使用Agent应该成功
            decision = await selector.select_strategy(
                query="复杂查询",
                user_profile={},
                force_strategy=ExecutionStrategy.AGENT,
                membership_level="energy"
            )
            
            assert decision.strategy == ExecutionStrategy.AGENT
            assert decision.membership_restricted == False


# =============================================================================
# 4. Token消耗对比测试
# =============================================================================

class TestTokenConsumption:
    """Token消耗对比测试"""
    
    def test_skill_metadata_token_estimate(self, sample_skill_metadata):
        """测试单个技能元数据的token估算"""
        prompt = sample_skill_metadata.to_system_prompt_format()
        # 每个技能元数据约50 tokens
        # 简单估算：中文字符约1.5 tokens
        estimated_tokens = len(prompt) * 1.5
        assert estimated_tokens < 100  # 应该小于100 tokens
    
    def test_skill_content_token_estimate(self, sample_skill_content):
        """测试技能内容的token估算"""
        skill_md = sample_skill_content.to_skill_md()
        # 完整技能内容约500 tokens
        estimated_tokens = len(skill_md) * 1.5
        assert estimated_tokens < 1000  # 应该小于1000 tokens
    
    def test_skill_manager_token_estimate(self, skill_manager):
        """测试SkillManager的token估算"""
        estimated = skill_manager.estimate_system_prompt_tokens()
        # 1个技能 + 基础开销 ≈ 100 tokens
        assert estimated < 200
    
    def test_skills_vs_traditional_token_comparison(self):
        """对比Skills模式和传统模式的token消耗"""
        # 创建多个技能
        manager = SkillManager()
        
        for i in range(13):  # 模拟13个DAG模板
            skill = Skill(
                metadata=SkillMetadata(
                    skill_id=f"skill_{i}",
                    name=f"技能{i}",
                    description=f"这是技能{i}的描述",
                    category=SkillCategory.TRAINING,
                    keywords=[f"关键词{i}"]
                ),
                content=SkillContent(
                    skill_id=f"skill_{i}",
                    full_description=f"这是技能{i}的完整描述" * 10,
                    applicable_intents=[f"意图{i}"],
                    required_tools=[f"tool_{i}"],
                    optional_tools=[],
                    tool_dependencies={},
                    parallel_groups=[],
                    safety_constraints=[f"约束{i}"],
                    response_hint=f"提示{i}"
                )
            )
            manager.register_skill(skill)
        
        # Skills模式：只加载元数据
        skills_tokens = manager.estimate_system_prompt_tokens()
        
        # 传统模式：所有模板 + 所有工具
        # 假设每个模板约300 tokens，每个工具约100 tokens
        traditional_tokens = 13 * 300 + 18 * 100  # ~5700 tokens
        
        # Skills模式应该显著更少
        assert skills_tokens < traditional_tokens
        
        # 打印对比结果
        print(f"\n📊 Token消耗对比:")
        print(f"   Skills模式: ~{skills_tokens} tokens")
        print(f"   传统模式: ~{traditional_tokens} tokens")
        print(f"   节省: ~{traditional_tokens - skills_tokens} tokens ({(1 - skills_tokens/traditional_tokens)*100:.1f}%)")


# =============================================================================
# 5. 集成测试
# =============================================================================

class TestIntegration:
    """集成测试"""
    
    def test_skills_config(self):
        """测试Skills配置获取"""
        config = get_skills_config()
        
        assert "skills_mode_enabled" in config
        assert "agent_mode_enabled" in config
        assert "feature_flags" in config
    
    def test_strategy_decision_to_dict(self):
        """测试StrategyDecision转换为字典"""
        decision = StrategyDecision(
            strategy=ExecutionStrategy.DAG,
            reasoning="匹配到技能",
            skill_id="complete_training_plan",
            template_id="complete_training_plan",
            confidence=0.85
        )
        
        d = decision.to_dict()
        
        assert d["strategy"] == "dag"
        assert d["skill_id"] == "complete_training_plan"
        assert d["confidence"] == 0.85
    
    def test_skill_manager_statistics(self, skill_manager):
        """测试SkillManager统计信息"""
        # 加载一个技能
        skill_manager.load_skill("complete_training_plan")
        
        stats = skill_manager.get_statistics()
        
        assert stats["total_skills"] == 1
        assert stats["loaded_skills_count"] == 1
        assert stats["total_load_count"] == 1
    
    def test_strategy_selector_statistics(self, strategy_selector):
        """测试StrategySelector统计信息"""
        stats = strategy_selector.get_statistics()
        
        assert "total_selections" in stats
        assert "dag_count" in stats
        assert "agent_count" in stats
        assert "skill_match_count" in stats


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
