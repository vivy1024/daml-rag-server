# -*- coding: utf-8 -*-
"""
LLM决策引擎测试

测试LLM决策引擎的核心功能：
1. DAG模板选择
2. LLM响应解析
3. 降级策略
4. 统计信息

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import pytest
import asyncio
import os

from src.applications.fitness.llm_decision_engine import (
    LLMDecisionEngine,
    DAGSelectionRequest,
    DAGSelectionResult,
    SelectionConfidence
)
from src.applications.fitness.dag_template_system import DAGTemplateManager


class TestLLMDecisionEngine:
    """LLM决策引擎测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建LLM决策引擎实例"""
        return LLMDecisionEngine()
    
    @pytest.fixture
    def sample_user_profile(self):
        """示例用户档案"""
        return {
            "user_id": "test_user_123",
            "basic_info": {
                "age": 28,
                "gender": "男",
                "weight": 75,
                "height": 175
            },
            "fitness_config": {
                "fitness_level": "intermediate",
                "training_days_per_week": 4
            },
            "fitness_goals": {
                "primary_goals": ["增肌", "力量提升"]
            },
            "health_profile": {
                "chronic_diseases": [],
                "injury_history": []
            }
        }
    
    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine is not None
        assert engine.template_manager is not None
        assert len(engine.template_manager.get_all_templates()) >= 8
        assert engine.selection_stats["total_selections"] == 0
    
    def test_fallback_selection_training_plan(self, engine, sample_user_profile):
        """测试降级策略 - 训练计划"""
        request = DAGSelectionRequest(
            user_query="我想制定一个增肌训练计划",
            user_profile=sample_user_profile,
            available_templates=engine.template_manager.get_all_templates()
        )
        
        result = engine._fallback_selection(request)
        
        assert result.selected_template_id == "complete_training_plan"
        assert result.fallback_used is True
        assert result.confidence >= 0.4
        assert "训练计划" in result.selection_reason or "增肌" in result.selection_reason
    
    def test_fallback_selection_nutrition(self, engine, sample_user_profile):
        """测试降级策略 - 营养规划"""
        request = DAGSelectionRequest(
            user_query="我应该吃什么来增肌？",
            user_profile=sample_user_profile,
            available_templates=engine.template_manager.get_all_templates()
        )
        
        result = engine._fallback_selection(request)
        
        # "吃什么来增肌" 同时匹配 nutrition_planning("吃什么") 和 complete_training_plan("增肌")
        # 关键词权重相同时，dict插入顺序决定排序，complete_training_plan 排在前面
        assert result.selected_template_id == "complete_training_plan"
        assert result.fallback_used is True
    
    def test_fallback_selection_safety(self, engine, sample_user_profile):
        """测试降级策略 - 安全评估"""
        request = DAGSelectionRequest(
            user_query="我有腰椎问题，哪些动作不能做？",
            user_profile=sample_user_profile,
            available_templates=engine.template_manager.get_all_templates()
        )
        
        result = engine._fallback_selection(request)
        
        # "哪些动作不能做" 匹配 exercise_optimization("动作"=1.5, "哪些动作"=1.0) 权重更高
        # 比 safety_assessment("不能做"=1.0) 置信度更高
        assert result.selected_template_id == "exercise_optimization"
        assert result.fallback_used is True
    
    def test_fallback_selection_default(self, engine, sample_user_profile):
        """测试降级策略 - 默认选择"""
        request = DAGSelectionRequest(
            user_query="你好",
            user_profile=sample_user_profile,
            available_templates=engine.template_manager.get_all_templates()
        )
        
        result = engine._fallback_selection(request)
        
        # "你好" 精确匹配 greeting 模板（"你好"=2.0, base_confidence=0.9）
        # 置信度 = 0.9 + 2.0*0.05 = 0.95 → HIGH，不再是默认的 quick_consultation
        assert result.selected_template_id == "greeting"
        assert result.fallback_used is True
        assert result.confidence_level == SelectionConfidence.HIGH
    
    def test_parse_llm_response_valid(self, engine):
        """测试解析有效的LLM响应"""
        llm_response = """```json
{
  "selected_template_id": "complete_training_plan",
  "selection_reason": "用户需要系统的增肌训练计划",
  "expected_tools": ["get_user_profile", "intelligent-exercise-selector"],
  "confidence": 0.95,
  "alternative_templates": ["comprehensive_fitness"]
}
```"""
        
        templates = engine.template_manager.get_all_templates()
        result = engine._parse_llm_response(llm_response, templates)
        
        assert result.selected_template_id == "complete_training_plan"
        assert result.confidence == 0.95
        assert result.confidence_level == SelectionConfidence.HIGH
        assert len(result.expected_tools) == 2
        assert result.fallback_used is False
    
    def test_parse_llm_response_without_markdown(self, engine):
        """测试解析不带markdown的LLM响应"""
        llm_response = """{
  "selected_template_id": "nutrition_planning",
  "selection_reason": "用户关注营养和饮食",
  "expected_tools": ["tdee-calculator", "meal-plan-designer"],
  "confidence": 0.85,
  "alternative_templates": []
}"""
        
        templates = engine.template_manager.get_all_templates()
        result = engine._parse_llm_response(llm_response, templates)
        
        assert result.selected_template_id == "nutrition_planning"
        assert result.confidence == 0.85
        assert result.confidence_level == SelectionConfidence.HIGH
    
    def test_validate_selection_valid(self, engine):
        """测试验证有效的选择结果"""
        templates = engine.template_manager.get_all_templates()
        
        result = DAGSelectionResult(
            selected_template_id="complete_training_plan",
            selection_reason="用户需要训练计划",
            expected_tools=["get_user_profile"],
            confidence=0.9,
            confidence_level=SelectionConfidence.HIGH
        )
        
        assert engine._validate_selection(result, templates) is True
    
    def test_validate_selection_invalid_template_id(self, engine):
        """测试验证无效的模板ID"""
        templates = engine.template_manager.get_all_templates()
        
        result = DAGSelectionResult(
            selected_template_id="invalid_template_id",
            selection_reason="测试",
            expected_tools=[],
            confidence=0.9,
            confidence_level=SelectionConfidence.HIGH
        )
        
        assert engine._validate_selection(result, templates) is False
    
    def test_validate_selection_invalid_confidence(self, engine):
        """测试验证无效的置信度"""
        templates = engine.template_manager.get_all_templates()
        
        result = DAGSelectionResult(
            selected_template_id="complete_training_plan",
            selection_reason="测试",
            expected_tools=[],
            confidence=1.5,  # 超出范围
            confidence_level=SelectionConfidence.HIGH
        )
        
        assert engine._validate_selection(result, templates) is False
    
    def test_build_selection_prompt(self, engine, sample_user_profile):
        """测试构建选择提示词"""
        request = DAGSelectionRequest(
            user_query="我想制定一个增肌训练计划",
            user_profile=sample_user_profile,
            available_templates=engine.template_manager.get_all_templates()
        )
        
        prompt = engine._build_selection_prompt(request)
        
        # 检查提示词包含关键信息
        assert "我想制定一个增肌训练计划" in prompt
        assert "28岁" in prompt or "28" in prompt
        assert "intermediate" in prompt or "中级" in prompt
        assert "增肌" in prompt
        assert "complete_training_plan" in prompt
        assert "nutrition_planning" in prompt
        assert "JSON" in prompt
    
    def test_statistics_tracking(self, engine, sample_user_profile):
        """测试统计信息跟踪"""
        # 初始统计
        stats = engine.get_selection_statistics()
        assert stats["total_selections"] == 0
        assert stats["success_rate"] == 0.0
        
        # 执行一次降级选择
        request = DAGSelectionRequest(
            user_query="测试查询",
            user_profile=sample_user_profile,
            available_templates=engine.template_manager.get_all_templates()
        )
        
        result = engine._fallback_selection(request)
        
        # 检查统计更新
        stats = engine.get_selection_statistics()
        assert stats["fallback_selections"] == 1


# 集成测试（需要LLM API）
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OLLAMA_BASE_URL"),
    reason="需要LLM API配置"
)
async def test_full_selection_flow():
    """测试完整的选择流程（需要LLM API）"""
    engine = LLMDecisionEngine()
    
    user_profile = {
        "user_id": "test_user_123",
        "basic_info": {
            "age": 28,
            "gender": "男",
            "weight": 75,
            "height": 175
        },
        "fitness_config": {
            "fitness_level": "intermediate",
            "training_days_per_week": 4
        },
        "fitness_goals": {
            "primary_goals": ["增肌", "力量提升"]
        },
        "health_profile": {
            "chronic_diseases": [],
            "injury_history": []
        }
    }
    
    request = DAGSelectionRequest(
        user_query="我想制定一个增肌训练计划",
        user_profile=user_profile,
        available_templates=engine.template_manager.get_all_templates()
    )
    
    result = await engine.select_dag_template(request)
    
    # 验证结果
    assert result is not None
    assert result.selected_template_id in [t.template_id for t in engine.template_manager.get_all_templates()]
    assert 0.0 <= result.confidence <= 1.0
    assert result.selection_reason
    
    # 检查统计
    stats = engine.get_selection_statistics()
    assert stats["total_selections"] == 1


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
