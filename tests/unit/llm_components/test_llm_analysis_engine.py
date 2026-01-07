# -*- coding: utf-8 -*-
"""
LLM综合分析引擎测试

测试LLM综合分析引擎的核心功能

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import pytest
import asyncio
from src.applications.fitness.llm_analysis_engine import (
    LLMAnalysisEngine,
    AnalysisRequest,
    AnalysisResult
)


@pytest.fixture
def sample_user_profile():
    """示例用户档案"""
    return {
        "basic_info": {
            "age": 28,
            "gender": "男",
            "weight": 75,
            "height": 175
        },
        "fitness_config": {
            "fitness_level": "intermediate",
            "training_days_per_week": 4,
            "available_equipment": ["杠铃", "哑铃", "固定器械"]
        },
        "fitness_goals": {
            "primary_goal": "增肌",
            "secondary_goals": ["力量提升"]
        },
        "health_profile": {
            "injuries": [],
            "medical_conditions": []
        }
    }


@pytest.fixture
def sample_tool_results():
    """示例工具结果"""
    return {
        "intelligent_exercise_selector": {
            "recommended_exercises": [
                {"name": "杠铃深蹲", "muscle_group": "腿部", "difficulty": "intermediate"},
                {"name": "杠铃卧推", "muscle_group": "胸部", "difficulty": "intermediate"},
                {"name": "硬拉", "muscle_group": "背部", "difficulty": "advanced"}
            ]
        },
        "muscle_group_volume_calculator": {
            "chest": {"min_sets": 12, "max_sets": 18},
            "back": {"min_sets": 14, "max_sets": 20},
            "legs": {"min_sets": 16, "max_sets": 22}
        },
        "professional_program_designer": {
            "program_name": "4天增肌训练计划",
            "total_weeks": 12,
            "training_days": 4
        }
    }


@pytest.fixture
def sample_contraindications():
    """示例禁忌动作"""
    return [
        {
            "name": "颈后推举",
            "reason": "肩部损伤风险高"
        },
        {
            "name": "直腿硬拉",
            "reason": "腰部压力过大"
        }
    ]


class TestLLMAnalysisEngine:
    """LLM综合分析引擎测试类"""

    def test_initialization(self):
        """测试初始化"""
        engine = LLMAnalysisEngine(prefer_teacher_model=True)
        assert engine is not None
        assert engine.prefer_teacher_model is True

    def test_build_analysis_prompt(self, sample_user_profile, sample_tool_results, sample_contraindications):
        """测试构建分析提示词"""
        engine = LLMAnalysisEngine()
        
        request = AnalysisRequest(
            user_query="帮我制定一个增肌训练计划",
            user_profile=sample_user_profile,
            tool_results=sample_tool_results,
            contraindications=sample_contraindications,
            safety_constraints=["避免过度训练", "注意热身"]
        )
        
        prompt = engine.build_analysis_prompt(request)
        
        # 验证提示词包含关键内容
        assert "专业分析" in prompt
        assert "个性化建议" in prompt
        assert "安全提醒" in prompt
        assert "推理依据" in prompt
        assert "禁忌动作" in prompt
        assert "颈后推举" in prompt
        assert "杠铃深蹲" in prompt

    def test_format_user_profile(self, sample_user_profile):
        """测试格式化用户档案"""
        engine = LLMAnalysisEngine()
        
        formatted = engine._format_user_profile(sample_user_profile)
        
        assert "28岁" in formatted
        assert "男" in formatted
        assert "75kg" in formatted
        assert "intermediate" in formatted
        assert "增肌" in formatted

    def test_format_tool_results(self, sample_tool_results):
        """测试格式化工具结果"""
        engine = LLMAnalysisEngine()
        
        formatted = engine._format_tool_results(sample_tool_results)
        
        assert "intelligent_exercise_selector" in formatted
        assert "杠铃深蹲" in formatted
        assert "muscle_group_volume_calculator" in formatted

    def test_parse_recommendations(self):
        """测试解析建议列表"""
        engine = LLMAnalysisEngine()
        
        text = """
1. 每周训练4次，每次60-90分钟
2. 优先进行复合动作训练
3. 确保充足的蛋白质摄入
- 额外建议：保持良好睡眠
• 注意训练后拉伸
"""
        
        recommendations = engine._parse_recommendations(text)
        
        assert len(recommendations) >= 3
        assert any("每周训练4次" in rec for rec in recommendations)
        assert any("复合动作" in rec for rec in recommendations)

    def test_calculate_confidence(self):
        """测试计算置信度"""
        engine = LLMAnalysisEngine()
        
        # 完整的分析结果
        confidence = engine._calculate_confidence(
            professional_analysis="这是一个详细的专业分析，包含了用户状况评估、训练计划科学性分析等内容。" * 5,
            recommendations=["建议1", "建议2", "建议3", "建议4"],
            safety_reminders=["提醒1", "提醒2"],
            reasoning_basis={"tool1": ["依据1"], "tool2": ["依据2"]}
        )
        
        assert 0.8 <= confidence <= 1.0
        
        # 不完整的分析结果
        confidence_low = engine._calculate_confidence(
            professional_analysis="简短分析",
            recommendations=[],
            safety_reminders=[],
            reasoning_basis={}
        )
        
        assert confidence_low < 0.5

    def test_create_fallback_response(self, sample_user_profile, sample_tool_results):
        """测试创建降级响应"""
        engine = LLMAnalysisEngine()
        
        request = AnalysisRequest(
            user_query="测试查询",
            user_profile=sample_user_profile,
            tool_results=sample_tool_results
        )
        
        fallback = engine._create_fallback_response(request, "测试错误")
        
        assert isinstance(fallback, AnalysisResult)
        assert "错误" in fallback.professional_analysis
        assert len(fallback.personalized_recommendations) > 0
        assert len(fallback.safety_reminders) > 0
        assert fallback.confidence == 0.0
        assert fallback.model_used == "fallback"

    @pytest.mark.asyncio
    async def test_analyze_results_mock(self, sample_user_profile, sample_tool_results, sample_contraindications):
        """测试分析结果（使用mock，不实际调用LLM）"""
        # 注意：这个测试需要mock LLM调用，否则会实际调用API
        # 在实际环境中，应该使用pytest-mock或unittest.mock
        
        engine = LLMAnalysisEngine(prefer_teacher_model=False)
        
        request = AnalysisRequest(
            user_query="帮我制定一个增肌训练计划",
            user_profile=sample_user_profile,
            tool_results=sample_tool_results,
            contraindications=sample_contraindications
        )
        
        # 这里应该mock call_ollama或call_deepseek
        # 由于没有mock，这个测试会实际调用LLM（如果配置了的话）
        # 在CI/CD环境中应该跳过或mock
        
        # result = await engine.analyze_results(request)
        # assert isinstance(result, AnalysisResult)
        # assert result.professional_analysis
        # assert len(result.personalized_recommendations) > 0
        
        # 暂时跳过实际调用
        pytest.skip("需要mock LLM调用")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
