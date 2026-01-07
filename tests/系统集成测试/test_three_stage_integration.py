# -*- coding: utf-8 -*-
"""
三段式编排器集成测试

验证LLM决策 → DAG执行 → LLM综合的完整工作流程

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.applications.fitness.three_stage_orchestrator import (
    ThreeStageOrchestrator,
    ThreeStageRequest,
    ThreeStageResult
)
from src.applications.fitness.dag_template_system import DAGTemplateManager
from src.applications.fitness.llm_decision_engine import (
    LLMDecisionEngine,
    DAGSelectionResult,
    SelectionConfidence
)
from src.applications.fitness.enhanced_dag_orchestrator import (
    EnhancedDAGOrchestrator,
    DAGExecutionResult
)
from src.applications.fitness.llm_analysis_engine import (
    LLMAnalysisEngine,
    AnalysisResult
)


@pytest.fixture
def mock_user_profile():
    """模拟用户档案"""
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
            "training_days_per_week": 4,
            "available_equipment": ["杠铃", "哑铃", "龙门架"]
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
def mock_llm_decision_engine():
    """模拟LLM决策引擎"""
    engine = Mock(spec=LLMDecisionEngine)
    engine.select_dag_template = AsyncMock(return_value=DAGSelectionResult(
        selected_template_id="complete_training_plan",
        selection_reason="用户需要完整的增肌训练计划",
        expected_tools=["get_user_profile", "contraindications_checker", "intelligent_exercise_selector"],
        confidence=0.95,
        confidence_level=SelectionConfidence.HIGH,
        fallback_used=False
    ))
    return engine


@pytest.fixture
def mock_dag_orchestrator():
    """模拟DAG编排器"""
    orchestrator = Mock(spec=EnhancedDAGOrchestrator)
    orchestrator.execute_template = AsyncMock(return_value=DAGExecutionResult(
        execution_id="test_exec_123",
        intent_pattern="complete_training_plan",
        success=True,
        total_time=5.0,
        levels_executed=3,
        tasks_completed=5,
        tasks_failed=0,
        results={
            "user_profile": {"user_id": "test_user_123"},
            "contraindications_checker": [],
            "intelligent_exercise_selector": [
                {"name": "深蹲", "sets": 4, "reps": 8},
                {"name": "卧推", "sets": 4, "reps": 8}
            ]
        }
    ))
    return orchestrator


@pytest.fixture
def mock_llm_analysis_engine():
    """模拟LLM分析引擎"""
    engine = Mock(spec=LLMAnalysisEngine)
    engine.analyze_results = AsyncMock(return_value=AnalysisResult(
        professional_analysis="基于您的档案，这是一个适合中级训练者的增肌计划。",
        personalized_recommendations=[
            "建议每周训练4次，每次60-90分钟",
            "重点关注复合动作，如深蹲、卧推、硬拉",
            "确保充足的蛋白质摄入（每公斤体重2g）"
        ],
        safety_reminders=[
            "训练前充分热身",
            "注意动作标准，避免受伤"
        ],
        reasoning_basis={
            "user_profile": ["训练水平：中级", "目标：增肌"],
            "intelligent_exercise_selector": ["推荐了5个核心动作"]
        },
        confidence=0.9,
        model_used="deepseek-chat"
    ))
    return engine


@pytest.mark.asyncio
async def test_three_stage_orchestrator_initialization():
    """测试三段式编排器初始化"""
    orchestrator = ThreeStageOrchestrator()
    
    assert orchestrator.template_manager is not None
    assert orchestrator.llm_decision_engine is not None
    assert orchestrator.dag_orchestrator is not None
    assert orchestrator.llm_analysis_engine is not None
    assert orchestrator.execution_stats["total_executions"] == 0


@pytest.mark.asyncio
async def test_three_stage_orchestrator_execute_success(
    mock_user_profile,
    mock_llm_decision_engine,
    mock_dag_orchestrator,
    mock_llm_analysis_engine
):
    """测试三段式编排器成功执行"""
    # 创建编排器（使用模拟的引擎）
    orchestrator = ThreeStageOrchestrator(
        llm_decision_engine=mock_llm_decision_engine,
        dag_orchestrator=mock_dag_orchestrator,
        llm_analysis_engine=mock_llm_analysis_engine
    )
    
    # 创建请求
    request = ThreeStageRequest(
        user_query="我想制定一个增肌训练计划",
        user_id="test_user_123",
        user_profile=mock_user_profile
    )
    
    # 执行三段式编排
    result = await orchestrator.execute(request)
    
    # 验证结果
    assert result.success is True
    assert result.execution_id is not None
    assert result.total_time > 0
    
    # 验证阶段1：LLM决策
    assert result.dag_selection is not None
    assert result.dag_selection.selected_template_id == "complete_training_plan"
    assert result.dag_selection.confidence == 0.95
    
    # 验证阶段2：DAG执行
    assert result.dag_execution is not None
    assert result.dag_execution.success is True
    assert result.dag_execution.tasks_completed == 5
    assert result.dag_execution.tasks_failed == 0
    
    # 验证阶段3：LLM分析
    assert result.llm_analysis is not None
    assert len(result.llm_analysis.personalized_recommendations) == 3
    assert len(result.llm_analysis.safety_reminders) == 2
    
    # 验证最终响应
    assert result.final_response != ""
    assert "增肌计划" in result.final_response
    assert "个性化建议" in result.final_response
    assert "安全提醒" in result.final_response
    
    # 验证元数据
    assert result.metadata["template_id"] == "complete_training_plan"
    assert result.metadata["tools_executed"] == 5
    assert result.metadata["recommendations_count"] == 3
    
    # 验证统计信息
    stats = orchestrator.get_execution_statistics()
    assert stats["total_executions"] == 1
    assert stats["successful_executions"] == 1
    assert stats["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_three_stage_orchestrator_stage1_failure(
    mock_user_profile,
    mock_dag_orchestrator,
    mock_llm_analysis_engine
):
    """测试阶段1失败的处理"""
    # 创建会失败的LLM决策引擎
    failing_engine = Mock(spec=LLMDecisionEngine)
    failing_engine.select_dag_template = AsyncMock(
        side_effect=Exception("LLM决策失败")
    )
    
    orchestrator = ThreeStageOrchestrator(
        llm_decision_engine=failing_engine,
        dag_orchestrator=mock_dag_orchestrator,
        llm_analysis_engine=mock_llm_analysis_engine
    )
    
    request = ThreeStageRequest(
        user_query="测试查询",
        user_id="test_user_123",
        user_profile=mock_user_profile
    )
    
    result = await orchestrator.execute(request)
    
    # 验证失败处理
    assert result.success is False
    assert "LLM决策失败" in result.errors.get("execution", "")
    assert result.final_response != ""  # 应该有错误响应
    
    # 验证统计信息
    stats = orchestrator.get_execution_statistics()
    assert stats["failed_executions"] == 1
    assert stats["stage_failures"]["stage1"] == 1


@pytest.mark.asyncio
async def test_three_stage_orchestrator_force_template(
    mock_user_profile,
    mock_dag_orchestrator,
    mock_llm_analysis_engine
):
    """测试强制指定模板"""
    orchestrator = ThreeStageOrchestrator(
        dag_orchestrator=mock_dag_orchestrator,
        llm_analysis_engine=mock_llm_analysis_engine
    )
    
    request = ThreeStageRequest(
        user_query="测试查询",
        user_id="test_user_123",
        user_profile=mock_user_profile,
        force_template_id="quick_consultation"  # 强制使用快速咨询模板
    )
    
    result = await orchestrator.execute(request)
    
    # 验证使用了强制指定的模板
    assert result.success is True
    assert result.dag_selection.selected_template_id == "quick_consultation"
    assert result.dag_selection.selection_reason == "强制指定模板（调试模式）"
    assert result.dag_selection.confidence == 1.0


@pytest.mark.asyncio
async def test_three_stage_orchestrator_with_contraindications(
    mock_user_profile,
    mock_llm_decision_engine,
    mock_llm_analysis_engine
):
    """测试包含禁忌动作的场景"""
    # 创建包含禁忌动作的DAG编排器
    orchestrator_with_contraindications = Mock(spec=EnhancedDAGOrchestrator)
    orchestrator_with_contraindications.execute_template = AsyncMock(
        return_value=DAGExecutionResult(
            execution_id="test_exec_456",
            intent_pattern="complete_training_plan",
            success=True,
            total_time=5.0,
            levels_executed=3,
            tasks_completed=5,
            tasks_failed=0,
            results={
                "user_profile": {"user_id": "test_user_123"},
                "contraindications_checker": [
                    {"name": "颈后深蹲", "reason": "颈椎问题"},
                    {"name": "直腿硬拉", "reason": "腰椎问题"}
                ],
                "intelligent_exercise_selector": [
                    {"name": "前蹲", "sets": 4, "reps": 8},
                    {"name": "罗马尼亚硬拉", "sets": 4, "reps": 8}
                ]
            }
        )
    )
    
    orchestrator = ThreeStageOrchestrator(
        llm_decision_engine=mock_llm_decision_engine,
        dag_orchestrator=orchestrator_with_contraindications,
        llm_analysis_engine=mock_llm_analysis_engine
    )
    
    request = ThreeStageRequest(
        user_query="我有腰椎问题，帮我制定训练计划",
        user_id="test_user_123",
        user_profile=mock_user_profile
    )
    
    result = await orchestrator.execute(request)
    
    # 验证成功执行
    assert result.success is True
    
    # 验证禁忌动作被正确传递到LLM分析引擎
    # （通过检查mock_llm_analysis_engine的调用参数）
    call_args = mock_llm_analysis_engine.analyze_results.call_args
    analysis_request = call_args[0][0]
    assert len(analysis_request.contraindications) == 2
    assert any("颈后深蹲" in str(c) for c in analysis_request.contraindications)


@pytest.mark.asyncio
async def test_three_stage_orchestrator_statistics():
    """测试统计信息的正确性"""
    orchestrator = ThreeStageOrchestrator()
    
    # 初始统计
    stats = orchestrator.get_execution_statistics()
    assert stats["total_executions"] == 0
    assert stats["success_rate"] == 0.0
    
    # 模拟多次执行（使用force_template避免实际LLM调用）
    mock_user_profile = {
        "user_id": "test_user",
        "basic_info": {"age": 25},
        "fitness_config": {"fitness_level": "beginner"}
    }
    
    # 注意：这个测试需要实际的模板系统，所以我们只验证统计结构
    # 实际执行会在集成测试中进行
    assert "average_total_time" in stats
    assert "average_stage1_time" in stats
    assert "average_stage2_time" in stats
    assert "average_stage3_time" in stats
    assert "stage_failures" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
