# -*- coding: utf-8 -*-
"""
Skills架构综合测试

测试内容：
1. DAG模式测试（技能匹配+执行）
2. Agent模式测试（load_skill+工具调用）
3. 会员权限测试（降级逻辑）
4. Token消耗对比测试

Requirements: 8.1-8.7
"""

import pytest
import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.framework.skills.skill_definition import (
    Skill,
    SkillMetadata,
    SkillContent,
    SkillExecution,
    SkillCategory,
)
from src.framework.skills.skill_manager import SkillManager, create_skill_manager
from src.framework.skills.load_skill_tool import LoadSkillTool, LoadSkillInput
from src.framework.skills.skills_agent_executor import SkillsAgentExecutor
from src.framework.skills.skills_integration import (
    SkillsIntegration,
    get_skills_integration,
    is_skills_mode_enabled,
    is_agent_mode_enabled,
)
from src.framework.orchestration.strategy_selector import (
    StrategySelector,
    ExecutionStrategy,
    create_strategy_selector,
)
from src.framework.auth.membership_controller import (
    MembershipController,
    MembershipLevel,
    create_membership_controller,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def skill_manager():
    """创建技能管理器"""
    manager = SkillManager()
    
    # 注册测试技能
    skills = [
        Skill(
            metadata=SkillMetadata(
                skill_id="greeting",
                name="问候",
                description="友好回应用户的问候",
                category=SkillCategory.QUICK,
                keywords=["你好", "问候", "打招呼"]
            ),
            content=SkillContent(
                skill_id="greeting",
                full_description="友好回应用户的问候和简单闲聊",
                applicable_intents=["问候", "打招呼"],
                required_tools=[],
                optional_tools=[],
                tool_dependencies={},
                parallel_groups=[],
                safety_constraints=[],
                response_hint="友好、热情地回应"
            )
        ),
        Skill(
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
                required_tools=["intelligent_exercise_selector", "professional_program_designer"],
                optional_tools=["injury_risk_assessor"],
                tool_dependencies={"professional_program_designer": ["intelligent_exercise_selector"]},
                parallel_groups=[],
                safety_constraints=["检查用户健康状况", "评估运动风险"],
                response_hint="提供详细的训练计划"
            )
        ),
        Skill(
            metadata=SkillMetadata(
                skill_id="nutrition_planning",
                name="营养规划",
                description="制定营养方案",
                category=SkillCategory.NUTRITION,
                keywords=["营养", "饮食", "食谱", "热量", "蛋白质"]
            ),
            content=SkillContent(
                skill_id="nutrition_planning",
                full_description="制定营养方案，计算热量和宏量营养素",
                applicable_intents=["营养规划", "饮食计划"],
                required_tools=["tdee_calculator", "meal_plan_designer"],
                optional_tools=[],
                tool_dependencies={},
                parallel_groups=[],
                safety_constraints=[],
                response_hint="提供营养建议"
            )
        ),
    ]
    
    for skill in skills:
        manager.register_skill(skill)
    
    return manager


@pytest.fixture
def membership_controller():
    """创建会员控制器"""
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'true'
    controller = MembershipController()
    yield controller
    os.environ['USE_MEMBERSHIP_CONTROL'] = 'false'


@pytest.fixture
def strategy_selector(skill_manager, membership_controller):
    """创建策略选择器"""
    return create_strategy_selector(
        skill_manager=skill_manager,
        membership_controller=membership_controller
    )


# =============================================================================
# DAG模式测试（技能匹配+执行）
# =============================================================================

class TestDAGMode:
    """DAG模式测试"""
    
    def test_skill_matching_training(self, skill_manager):
        """测试训练相关技能匹配"""
        queries = [
            ("帮我制定一个训练计划", "complete_training_plan"),
            ("我想增肌", "complete_training_plan"),
            ("健身计划怎么安排", "complete_training_plan"),
        ]
        
        for query, expected_skill in queries:
            matched = skill_manager.match_skill_by_query(query)
            assert matched == expected_skill, f"Query '{query}' should match '{expected_skill}', got '{matched}'"
    
    def test_skill_matching_nutrition(self, skill_manager):
        """测试营养相关技能匹配"""
        queries = [
            ("每天应该吃多少蛋白质", "nutrition_planning"),
            ("帮我制定饮食计划", "nutrition_planning"),
            ("热量怎么计算", "nutrition_planning"),
        ]
        
        for query, expected_skill in queries:
            matched = skill_manager.match_skill_by_query(query)
            assert matched == expected_skill, f"Query '{query}' should match '{expected_skill}', got '{matched}'"
    
    def test_skill_matching_greeting(self, skill_manager):
        """测试问候技能匹配"""
        # 使用更精确的关键词匹配
        queries = [
            ("你好", "greeting"),
            ("问候一下", "greeting"),
        ]
        
        for query, expected_skill in queries:
            matched = skill_manager.match_skill_by_query(query)
            assert matched == expected_skill, f"Query '{query}' should match '{expected_skill}', got '{matched}'"
    
    def test_dag_strategy_selection(self, strategy_selector):
        """测试DAG策略选择"""
        decision = asyncio.get_event_loop().run_until_complete(
            strategy_selector.select_strategy(
                query="帮我制定一个训练计划",
                user_profile={},
                membership_level="warmheart"
            )
        )
        
        assert decision.strategy == ExecutionStrategy.DAG
        assert decision.skill_id == "complete_training_plan"
    
    def test_skill_content_loading(self, skill_manager):
        """测试技能内容加载"""
        content = skill_manager.load_skill("complete_training_plan")
        
        assert "complete_training_plan" in content or "训练计划" in content
        assert "intelligent_exercise_selector" in content or "工具" in content


# =============================================================================
# Agent模式测试（load_skill+工具调用）
# =============================================================================

class TestAgentMode:
    """Agent模式测试"""
    
    def test_load_skill_tool_creation(self, skill_manager):
        """测试load_skill工具创建"""
        tool = LoadSkillTool(skill_manager=skill_manager)
        
        assert tool.get_name() == "load_skill"
        assert tool.get_description() is not None
    
    def test_load_skill_tool_execution(self, skill_manager):
        """测试load_skill工具执行"""
        tool = LoadSkillTool(skill_manager=skill_manager)
        
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute({"skill_id": "complete_training_plan"})
        )
        
        assert result["success"] == True
        # 返回字段是content而不是skill_content
        assert "content" in result
        assert len(result["content"]) > 0
    
    def test_load_skill_tool_invalid_skill(self, skill_manager):
        """测试load_skill工具处理无效技能"""
        tool = LoadSkillTool(skill_manager=skill_manager)
        
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute({"skill_id": "nonexistent_skill"})
        )
        
        assert result["success"] == False
        assert "error" in result
    
    def test_agent_strategy_selection_energy_member(self, strategy_selector):
        """测试ENERGY会员可以使用Agent模式"""
        decision = asyncio.get_event_loop().run_until_complete(
            strategy_selector.select_strategy(
                query="复杂的健身问题",
                user_profile={},
                force_strategy=ExecutionStrategy.AGENT,
                membership_level="energy"
            )
        )
        
        assert decision.strategy == ExecutionStrategy.AGENT
        assert decision.membership_restricted == False


# =============================================================================
# 会员权限测试（降级逻辑）
# =============================================================================

class TestMembershipPermissions:
    """会员权限测试"""
    
    def test_free_user_agent_downgrade(self, strategy_selector):
        """测试FREE用户Agent模式降级"""
        decision = asyncio.get_event_loop().run_until_complete(
            strategy_selector.select_strategy(
                query="复杂问题",
                user_profile={},
                force_strategy=ExecutionStrategy.AGENT,
                membership_level="free"
            )
        )
        
        assert decision.strategy == ExecutionStrategy.DAG
        assert decision.membership_restricted == True
        assert decision.original_strategy == ExecutionStrategy.AGENT
    
    def test_warmheart_user_agent_downgrade(self, strategy_selector):
        """测试WARMHEART用户Agent模式降级"""
        decision = asyncio.get_event_loop().run_until_complete(
            strategy_selector.select_strategy(
                query="复杂问题",
                user_profile={},
                force_strategy=ExecutionStrategy.AGENT,
                membership_level="warmheart"
            )
        )
        
        assert decision.strategy == ExecutionStrategy.DAG
        assert decision.membership_restricted == True
    
    def test_energy_user_agent_allowed(self, strategy_selector):
        """测试ENERGY用户可以使用Agent模式"""
        decision = asyncio.get_event_loop().run_until_complete(
            strategy_selector.select_strategy(
                query="复杂问题",
                user_profile={},
                force_strategy=ExecutionStrategy.AGENT,
                membership_level="energy"
            )
        )
        
        assert decision.strategy == ExecutionStrategy.AGENT
        assert decision.membership_restricted == False
    
    def test_all_users_can_use_dag(self, strategy_selector):
        """测试所有用户都可以使用DAG模式"""
        for level in ["free", "warmheart", "energy"]:
            decision = asyncio.get_event_loop().run_until_complete(
                strategy_selector.select_strategy(
                    query="训练计划",
                    user_profile={},
                    force_strategy=ExecutionStrategy.DAG,
                    membership_level=level
                )
            )
            
            assert decision.strategy == ExecutionStrategy.DAG
            assert decision.membership_restricted == False


# =============================================================================
# Token消耗对比测试
# =============================================================================

class TestTokenConsumption:
    """Token消耗对比测试"""
    
    def test_system_prompt_token_estimation(self, skill_manager):
        """测试system prompt token估算"""
        estimated_tokens = skill_manager.estimate_system_prompt_tokens()
        
        # 3个技能，每个约50 tokens + 50 base = 200 tokens
        assert estimated_tokens > 0
        assert estimated_tokens < 500  # 应该远小于传统模式
    
    def test_skills_prompt_length(self, skill_manager):
        """测试技能列表长度"""
        prompt = skill_manager.get_system_prompt_skills()
        
        # 技能列表应该比完整DAG模板短很多
        assert len(prompt) < 2000  # 字符数
    
    def test_compact_prompt_shorter(self, skill_manager):
        """测试紧凑格式更短"""
        full_prompt = skill_manager.get_system_prompt_skills()
        compact_prompt = skill_manager.get_system_prompt_skills_compact()
        
        assert len(compact_prompt) < len(full_prompt)
    
    def test_skill_content_loaded_on_demand(self, skill_manager):
        """测试技能内容按需加载"""
        # 初始状态没有加载任何技能
        assert len(skill_manager.get_loaded_skills()) == 0
        
        # 加载一个技能
        skill_manager.load_skill("complete_training_plan")
        
        # 只有一个技能被加载
        assert len(skill_manager.get_loaded_skills()) == 1
        assert "complete_training_plan" in skill_manager.get_loaded_skills()
    
    def test_token_savings_calculation(self, skill_manager):
        """测试Token节省计算"""
        # 传统模式：假设每个DAG模板500 tokens
        traditional_tokens = 3 * 500  # 3个模板
        
        # Skills模式：只有元数据
        skills_tokens = skill_manager.estimate_system_prompt_tokens()
        
        # 节省比例
        savings = (traditional_tokens - skills_tokens) / traditional_tokens
        
        # 应该节省至少50%
        assert savings > 0.5, f"Token savings should be > 50%, got {savings*100:.1f}%"


# =============================================================================
# 集成测试
# =============================================================================

class TestSkillsIntegration:
    """Skills架构集成测试"""
    
    def test_integration_initialization(self, skill_manager):
        """测试集成器初始化"""
        SkillsIntegration.reset_instance()
        
        integration = get_skills_integration()
        integration.initialize_with_skill_manager(skill_manager)
        
        assert integration.is_initialized()
        assert integration.get_skill_manager() is skill_manager
    
    def test_feature_flags(self):
        """测试Feature Flag"""
        SkillsIntegration.reset_instance()
        
        integration = get_skills_integration()
        
        # 默认禁用
        assert not integration.is_skills_mode_enabled()
        assert not integration.is_agent_mode_enabled()
        
        # 运行时启用
        integration.set_skills_mode(True)
        assert integration.is_skills_mode_enabled()
        
        integration.set_agent_mode(True)
        assert integration.is_agent_mode_enabled()
    
    def test_statistics(self, skill_manager):
        """测试统计信息"""
        SkillsIntegration.reset_instance()
        
        integration = get_skills_integration()
        integration.initialize_with_skill_manager(skill_manager)
        
        stats = integration.get_statistics()
        
        assert "initialized" in stats
        assert "skill_manager" in stats
        assert stats["skill_manager"]["total_skills"] == 3


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
