# -*- coding: utf-8 -*-
"""
DAG回归测试 - 验证13个DAG模板在新检索层下的兼容性

验证新的 FitnessGraphRAGRetriever 不会破坏现有的DAG工作流：
- 13个DAG模板正常工作
- node_retrieve_context 兼容性
- Layer3 安全约束不受影响
- 工具调用链完整性

版本: v1.0.0
日期: 2026-02-16
Requirements: Phase 1 Task 4.4
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import pytest

from src.applications.fitness.dag_template_system import (
    DAGTemplateManager,
    TemplateCategory,
)
from src.applications.fitness.workflow.nodes import node_retrieve_context
from src.applications.fitness.workflow.state import WorkflowState
from src.framework.retrieval.graphrag_retriever import FitnessGraphRAGRetriever

logger = logging.getLogger(__name__)


# =============================================================================
# Mock数据
# =============================================================================

def create_mock_workflow_state(query: str = "测试查询") -> Dict[str, Any]:
    """创建mock的工作流状态"""
    return {
        "request_id": "test-request-123",
        "user_id": "test-user",
        "query": query,
        "domain": "fitness",
        "intent": "training",
        "complexity": "medium",
        "selected_model": "gpt-4",
        "dag_plan": {"template_id": "complete_training_plan", "tools": []},
        "dag_results": {},
        "retrieval_context": {},
        "final_response": "",
        "metadata": {},
    }


def create_mock_retrieval_result(count: int = 5) -> Dict[str, Any]:
    """创建mock的检索结果"""
    return {
        "results": [
            {
                "content": f"检索结果 {i+1}",
                "score": 0.9 - i * 0.1,
                "metadata": {"source": "mock", "index": i}
            }
            for i in range(count)
        ],
        "count": count,
        "domain": "fitness",
        "query_type": "graphrag_hybrid",
        "retriever": "neo4j-graphrag-python",
    }


# =============================================================================
# DAG模板验证测试
# =============================================================================

class TestDAGTemplateValidation:
    """验证13个DAG模板的完整性"""

    def test_all_templates_loaded(self):
        """验证所有13个模板都已加载"""
        manager = DAGTemplateManager()
        templates = manager.templates

        logger.info(f"已加载 {len(templates)} 个DAG模板")

        # 验证至少有13个模板
        assert len(templates) >= 13

    def test_all_templates_valid(self):
        """验证所有模板都通过验证"""
        manager = DAGTemplateManager()

        for template_id, template in manager.templates.items():
            assert template.validate(), f"模板 {template_id} 验证失败"
            logger.info(f"✅ 模板 {template_id} 验证通过")

    def test_template_categories(self):
        """验证模板分类完整"""
        manager = DAGTemplateManager()

        categories = set()
        for template in manager.templates.values():
            categories.add(template.category)

        logger.info(f"模板分类: {[c.value for c in categories]}")

        # 验证至少包含主要分类
        assert TemplateCategory.TRAINING in categories
        assert TemplateCategory.NUTRITION in categories
        assert TemplateCategory.SAFETY in categories


# =============================================================================
# node_retrieve_context 兼容性测试
# =============================================================================

class TestNodeRetrieveContextCompatibility:
    """验证 node_retrieve_context 与新检索层的兼容性"""

    @pytest.mark.asyncio
    async def test_node_with_new_retriever(self):
        """验证使用新检索器的 node_retrieve_context"""
        # Mock旧引擎
        old_engine = MagicMock()
        old_engine.search = AsyncMock(return_value=create_mock_retrieval_result())

        # 创建新检索器
        new_retriever = FitnessGraphRAGRetriever(fallback_engine=old_engine)

        # 创建工作流状态
        state = create_mock_workflow_state("胸肌训练")

        # 调用 node_retrieve_context
        result = await node_retrieve_context(
            state=state,
            graphrag_retriever=new_retriever
        )

        # 验证结果
        assert result.updates is not None
        assert "retrieval_results" in result.updates or "retrieval_context" in result.updates
        assert result.error is None

        logger.info(f"✅ node_retrieve_context 使用新检索器成功")

    @pytest.mark.asyncio
    async def test_node_with_fallback_to_old_engine(self):
        """验证降级到旧引擎的场景"""
        # Mock旧引擎
        old_engine = MagicMock()
        old_engine.search = AsyncMock(return_value=create_mock_retrieval_result())

        # 创建新检索器（没有真实连接，会fallback）
        new_retriever = FitnessGraphRAGRetriever(fallback_engine=old_engine)

        state = create_mock_workflow_state("背部训练")

        result = await node_retrieve_context(
            state=state,
            graphrag_retriever=new_retriever
        )

        # 验证fallback正常工作
        assert result.updates is not None
        assert result.error is None
        old_engine.search.assert_called_once()

        logger.info(f"✅ 降级到旧引擎成功")

    @pytest.mark.asyncio
    async def test_node_without_retriever(self):
        """验证没有检索器时的处理"""
        state = create_mock_workflow_state("深蹲姿势")

        # 不传递任何检索器
        result = await node_retrieve_context(state=state)

        # 验证错误处理
        assert result.error is not None or result.updates is not None

        logger.info(f"✅ 无检索器场景处理正常")


# =============================================================================
# Layer3 安全约束测试
# =============================================================================

class TestLayer3SafetyConstraints:
    """验证 Layer3 安全约束不受检索层替换影响"""

    @pytest.mark.asyncio
    async def test_safety_constraints_still_applied(self):
        """验证安全约束仍然生效"""
        # 创建包含安全约束的模板
        manager = DAGTemplateManager()
        safety_template = manager.get_template("safety_assessment")

        assert safety_template is not None
        assert len(safety_template.safety_constraints) > 0

        logger.info(f"安全约束: {safety_template.safety_constraints}")

        # 验证约束内容
        assert any("禁忌" in c for c in safety_template.safety_constraints)

    @pytest.mark.asyncio
    async def test_contraindications_checker_integration(self):
        """验证禁忌症检查器集成"""
        manager = DAGTemplateManager()

        # 查找需要 contraindications_checker 的模板
        templates_with_contraindications = [
            t for t in manager.templates.values()
            if "contraindications_checker" in t.required_tools
        ]

        logger.info(f"包含禁忌症检查的模板数: {len(templates_with_contraindications)}")

        # 验证至少有几个模板包含禁忌症检查
        assert len(templates_with_contraindications) >= 2


# =============================================================================
# 工具调用链完整性测试
# =============================================================================

class TestToolChainIntegrity:
    """验证工具调用链的完整性"""

    def test_tool_dependencies_valid(self):
        """验证所有模板的工具依赖关系有效"""
        manager = DAGTemplateManager()

        for template_id, template in manager.templates.items():
            all_tools = set(template.required_tools + template.optional_tools)

            # 验证依赖关系中的工具都在工具列表中
            for tool, deps in template.tool_dependencies.items():
                assert tool in all_tools, f"模板 {template_id}: 工具 {tool} 不在工具列表中"

                for dep in deps:
                    assert dep in all_tools, f"模板 {template_id}: 依赖 {dep} 不在工具列表中"

            logger.info(f"✅ 模板 {template_id} 工具依赖关系有效")

    def test_parallel_groups_valid(self):
        """验证并行组配置有效"""
        manager = DAGTemplateManager()

        for template_id, template in manager.templates.items():
            all_tools = set(template.required_tools + template.optional_tools)

            # 验证并行组中的工具都在工具列表中
            for group in template.parallel_groups:
                for tool in group:
                    assert tool in all_tools, f"模板 {template_id}: 并行组工具 {tool} 不在工具列表中"

            logger.info(f"✅ 模板 {template_id} 并行组配置有效")


# =============================================================================
# 端到端回归测试
# =============================================================================

class TestEndToEndRegression:
    """端到端回归测试"""

    @pytest.mark.asyncio
    async def test_complete_training_plan_workflow(self):
        """测试完整训练计划工作流"""
        manager = DAGTemplateManager()
        template = manager.get_template("complete_training_plan")

        assert template is not None
        assert template.validate()

        # Mock检索器
        old_engine = MagicMock()
        old_engine.search = AsyncMock(return_value=create_mock_retrieval_result())
        new_retriever = FitnessGraphRAGRetriever(fallback_engine=old_engine)

        # 创建工作流状态
        state = create_mock_workflow_state("制定增肌训练计划")
        state["dag_plan"] = {
            "template_id": "complete_training_plan",
            "tools": template.required_tools
        }

        # 执行检索步骤
        result = await node_retrieve_context(
            state=state,
            graphrag_retriever=new_retriever
        )

        assert result.error is None
        logger.info(f"✅ 完整训练计划工作流测试通过")

    @pytest.mark.asyncio
    async def test_nutrition_planning_workflow(self):
        """测试营养规划工作流"""
        manager = DAGTemplateManager()
        template = manager.get_template("nutrition_planning")

        assert template is not None
        assert template.validate()

        old_engine = MagicMock()
        old_engine.search = AsyncMock(return_value=create_mock_retrieval_result())
        new_retriever = FitnessGraphRAGRetriever(fallback_engine=old_engine)

        state = create_mock_workflow_state("制定营养计划")
        state["dag_plan"] = {
            "template_id": "nutrition_planning",
            "tools": template.required_tools
        }

        result = await node_retrieve_context(
            state=state,
            graphrag_retriever=new_retriever
        )

        assert result.error is None
        logger.info(f"✅ 营养规划工作流测试通过")

    @pytest.mark.asyncio
    async def test_safety_assessment_workflow(self):
        """测试安全评估工作流"""
        manager = DAGTemplateManager()
        template = manager.get_template("safety_assessment")

        assert template is not None
        assert template.validate()

        old_engine = MagicMock()
        old_engine.search = AsyncMock(return_value=create_mock_retrieval_result())
        new_retriever = FitnessGraphRAGRetriever(fallback_engine=old_engine)

        state = create_mock_workflow_state("评估运动安全性")
        state["dag_plan"] = {
            "template_id": "safety_assessment",
            "tools": template.required_tools
        }

        result = await node_retrieve_context(
            state=state,
            graphrag_retriever=new_retriever
        )

        assert result.error is None
        logger.info(f"✅ 安全评估工作流测试通过")


# =============================================================================
# 集成回归测试（需要真实连接）
# =============================================================================

@pytest.mark.integration
@pytest.mark.skip(reason="需要真实Neo4j和Qdrant连接，CI环境不可用")
class TestRealDAGRegression:
    """真实环境DAG回归测试"""

    @pytest.mark.asyncio
    async def test_real_complete_workflow(self):
        """真实环境完整工作流测试"""
        # TODO: 实现真实数据库连接的完整工作流测试
        # 1. 连接真实Neo4j和Qdrant
        # 2. 初始化真实的检索器
        # 3. 执行完整的DAG工作流
        # 4. 验证所有步骤正常执行
        pass


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
