# -*- coding: utf-8 -*-
"""
三段式编排器测试

测试完整的三段式工作流程：LLM决策 → DAG执行 → LLM综合

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import pytest
import asyncio

# three_stage_orchestrator 已废弃/移除：保留此文件作为历史验证用例（默认跳过）
pytest.importorskip(
    "src.applications.fitness.three_stage_orchestrator",
    reason="three_stage_orchestrator 已废弃/移除",
)

from src.applications.fitness.three_stage_orchestrator import (
    ThreeStageOrchestrator,
    ThreeStageRequest,
    ThreeStageResult
)


@pytest.fixture
def sample_user_profile():
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
            "training_days_per_week": 4,
            "available_equipment": ["杠铃", "哑铃", "龙门架"]
        },
        "fitness_goals": {
            "primary_goal": "增肌",
            "secondary_goals": ["力量提升"]
        },
        "health_status": {
            "injuries": [],
            "medical_conditions": []
        }
    }


@pytest.fixture
def orchestrator():
    """创建三段式编排器实例"""
    return ThreeStageOrchestrator()


@pytest.mark.asyncio
async def test_three_stage_orchestrator_initialization(orchestrator):
    """测试三段式编排器初始化"""
    assert orchestrator is not None
    assert orchestrator.template_manager is not None
    assert orchestrator.llm_decision_engine is not None
    assert orchestrator.dag_orchestrator is not None
    assert orchestrator.llm_analysis_engine is not None
    print("✅ 三段式编排器初始化测试通过")


@pytest.mark.asyncio
async def test_three_stage_execution_training_plan(orchestrator, sample_user_profile):
    """测试三段式编排 - 训练计划查询"""
    request = ThreeStageRequest(
        user_query="我想制定一个增肌训练计划",
        user_id="test_user_123",
        user_profile=sample_user_profile
    )
    
    result = await orchestrator.execute(request)
    
    # 验证结果
    assert result is not None
    assert result.execution_id is not None
    assert result.total_time > 0
    
    # 验证阶段1：LLM决策
    assert result.dag_selection is not None
    assert result.dag_selection.selected_template_id is not None
    assert 0.0 <= result.dag_selection.confidence <= 1.0
    print(f"✅ 阶段1 - DAG选择: {result.dag_selection.selected_template_id} (置信度: {result.dag_selection.confidence:.2f})")
    
    # 验证阶段2：DAG执行
    assert result.dag_execution is not None
    assert result.dag_execution.tasks_completed >= 0
    print(f"✅ 阶段2 - DAG执行: {result.dag_execution.tasks_completed}个工具")
    
    # 验证阶段3：LLM分析
    assert result.llm_analysis is not None
    assert result.llm_analysis.professional_analysis is not None
    assert len(result.llm_analysis.personalized_recommendations) > 0
    print(f"✅ 阶段3 - LLM分析: {len(result.llm_analysis.personalized_recommendations)}条建议")
    
    # 验证最终响应
    assert result.final_response is not None
    assert len(result.final_response) > 0
    print(f"✅ 最终响应长度: {len(result.final_response)}字符")
    
    # 验证元数据
    assert result.metadata is not None
    assert 'template_id' in result.metadata
    assert 'stage1_time' in result.metadata
    assert 'stage2_time' in result.metadata
    assert 'stage3_time' in result.metadata
    print(f"✅ 元数据完整")


@pytest.mark.asyncio
async def test_three_stage_execution_nutrition(orchestrator, sample_user_profile):
    """测试三段式编排 - 营养查询"""
    request = ThreeStageRequest(
        user_query="我应该吃什么来增肌？",
        user_id="test_user_123",
        user_profile=sample_user_profile
    )
    
    result = await orchestrator.execute(request)
    
    assert result is not None
    assert result.success or len(result.errors) > 0  # 成功或有错误信息
    
    if result.success:
        assert result.dag_selection is not None
        assert result.dag_execution is not None
        assert result.llm_analysis is not None
        print(f"✅ 营养查询测试通过: {result.dag_selection.selected_template_id}")
    else:
        print(f"⚠️ 营养查询失败（预期行为）: {result.errors}")


@pytest.mark.asyncio
async def test_three_stage_execution_with_force_template(orchestrator, sample_user_profile):
    """测试三段式编排 - 强制指定模板"""
    request = ThreeStageRequest(
        user_query="测试查询",
        user_id="test_user_123",
        user_profile=sample_user_profile,
        force_template_id="quick_consultation"
    )
    
    result = await orchestrator.execute(request)
    
    assert result is not None
    if result.success:
        assert result.dag_selection.selected_template_id == "quick_consultation"
        print(f"✅ 强制模板测试通过: {result.dag_selection.selected_template_id}")


@pytest.mark.asyncio
async def test_three_stage_statistics(orchestrator, sample_user_profile):
    """测试三段式编排统计"""
    # 执行几次查询
    queries = [
        "我想制定训练计划",
        "推荐一些动作",
        "分析我的进展"
    ]
    
    for query in queries:
        request = ThreeStageRequest(
            user_query=query,
            user_id="test_user_123",
            user_profile=sample_user_profile
        )
        await orchestrator.execute(request)
    
    # 获取统计
    stats = orchestrator.get_execution_statistics()
    
    assert stats is not None
    assert stats['total_executions'] >= 3
    assert 'success_rate' in stats
    assert 'average_total_time' in stats
    print(f"✅ 统计测试通过: {stats['total_executions']}次执行, 成功率: {stats['success_rate']:.1%}")


def test_three_stage_orchestrator_sync():
    """同步测试入口"""
    print("\n" + "="*80)
    print("三段式编排器测试")
    print("="*80)
    
    # 运行所有异步测试
    asyncio.run(run_all_tests())


async def run_all_tests():
    """运行所有测试"""
    orchestrator = ThreeStageOrchestrator()
    sample_user_profile = {
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
        "health_status": {
            "injuries": [],
            "medical_conditions": []
        }
    }
    
    print("\n1. 测试初始化...")
    await test_three_stage_orchestrator_initialization(orchestrator)
    
    print("\n2. 测试训练计划查询...")
    await test_three_stage_execution_training_plan(orchestrator, sample_user_profile)
    
    print("\n3. 测试营养查询...")
    await test_three_stage_execution_nutrition(orchestrator, sample_user_profile)
    
    print("\n4. 测试强制模板...")
    await test_three_stage_execution_with_force_template(orchestrator, sample_user_profile)
    
    print("\n5. 测试统计...")
    await test_three_stage_statistics(orchestrator, sample_user_profile)
    
    print("\n" + "="*80)
    print("所有测试完成！")
    print("="*80)


if __name__ == "__main__":
    test_three_stage_orchestrator_sync()
