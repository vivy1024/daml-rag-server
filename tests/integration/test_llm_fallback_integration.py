# -*- coding: utf-8 -*-
"""
LLM降级管理器集成测试

测试LLM降级管理器在工作流中的集成情况：
1. 步骤6.5：LLM选择DAG模板
2. 步骤10：LLM生成回答

版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import asyncio
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLLMFallbackIntegration:
    """LLM降级管理器集成测试"""
    
    @pytest.mark.asyncio
    async def test_llm_decision_engine_uses_fallback_manager(self):
        """测试LLMDecisionEngine关键词匹配优先策略

        当前架构：关键词匹配置信度>=0.8时直接返回，不调用LLM。
        此测试验证高置信度查询走关键词匹配路径。
        """
        from src.applications.fitness.llm_decision_engine import (
            LLMDecisionEngine,
            DAGSelectionRequest
        )
        from src.applications.fitness.dag_template_system import DAGTemplateManager

        template_manager = DAGTemplateManager()
        decision_engine = LLMDecisionEngine(template_manager)

        request = DAGSelectionRequest(
            user_query="我想增肌，帮我设计一个训练计划",
            user_profile={
                "basic_info": {"age": 25, "gender": "male"},
                "fitness_config": {"fitness_level": "intermediate", "training_days_per_week": 4},
                "fitness_goals": {"primary_goals": ["增肌"]}
            },
            available_templates=template_manager.get_all_templates()
        )

        result = await decision_engine.select_dag_template(request)

        # 关键词匹配应返回 complete_training_plan，置信度 >= 0.8
        assert result.selected_template_id == "complete_training_plan"
        assert result.confidence >= 0.8
        assert any(kw in result.matched_keywords for kw in ["增肌", "训练计划", "训练", "计划"])
        # 关键词匹配路径不使用LLM降级
        assert result.fallback_used is False

        logger.info(f"✅ 关键词匹配: template={result.selected_template_id}, confidence={result.confidence}")
    
    @pytest.mark.asyncio
    async def test_llm_decision_engine_handles_fallback(self):
        """测试LLMDecisionEngine对不同查询的关键词匹配

        验证"推荐一些动作"类查询也能通过关键词匹配正确路由到 exercise_optimization。
        """
        from src.applications.fitness.llm_decision_engine import (
            LLMDecisionEngine,
            DAGSelectionRequest
        )
        from src.applications.fitness.dag_template_system import DAGTemplateManager

        template_manager = DAGTemplateManager()
        decision_engine = LLMDecisionEngine(template_manager)

        request = DAGSelectionRequest(
            user_query="推荐一些动作",
            user_profile={
                "basic_info": {"age": 30, "gender": "female"},
                "fitness_config": {"fitness_level": "beginner", "training_days_per_week": 3},
                "fitness_goals": {"primary_goals": ["减脂"]}
            },
            available_templates=template_manager.get_all_templates()
        )

        result = await decision_engine.select_dag_template(request)

        # 关键词匹配应路由到 exercise_optimization
        assert result.selected_template_id == "exercise_optimization"
        assert result.confidence >= 0.6
        assert any(kw in result.matched_keywords for kw in ["动作", "推荐"])

        logger.info(f"✅ 关键词匹配: template={result.selected_template_id}, confidence={result.confidence}")
    
    @pytest.mark.asyncio
    async def test_workflow_step10_uses_fallback_manager(self):
        """测试工作流步骤10使用降级管理器

        workflow_executor.py 已重构为兼容层，实际实现在 workflow/ 模块中。
        验证 nodes.py 和 stream_executor.py 通过 DI 容器获取 LLMFallbackManager 单例。
        """
        import os

        workflow_dir = os.path.join(
            os.path.dirname(__file__),
            "../../src/applications/fitness/workflow"
        )

        # 检查 nodes.py（同步执行路径）— 通过 DI 容器获取单例
        nodes_file = os.path.join(workflow_dir, "nodes.py")
        with open(nodes_file, 'r', encoding='utf-8') as f:
            nodes_content = f.read()

        assert "get_llm_degradation_manager" in nodes_content, "nodes.py 应通过 DI 容器获取 LLM 降级管理器"

        # 检查 stream_executor.py（流式执行路径）— 通过 DI 容器获取单例
        stream_file = os.path.join(workflow_dir, "stream_executor.py")
        with open(stream_file, 'r', encoding='utf-8') as f:
            stream_content = f.read()

        assert "get_llm_degradation_manager" in stream_content, "stream_executor.py 应通过 DI 容器获取 LLM 降级管理器"
        assert "call_with_fallback_stream" in stream_content, "stream_executor.py 应使用流式降级调用"

        logger.info("✅ workflow/nodes.py 和 stream_executor.py 均已通过 DI 容器集成 LLMFallbackManager")
    
    def test_llm_fallback_configuration(self):
        """测试LLM降级配置"""
        import yaml
        import os
        
        # 读取配置文件
        config_file = os.path.join(
            os.path.dirname(__file__),
            "../../config/performance_optimization.yaml"
        )
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 验证LLM降级配置
        assert 'llm_fallback' in config
        llm_config = config['llm_fallback']
        
        assert llm_config['primary_backend'] == 'deepseek'
        assert 'ollama' in llm_config['fallback_backends']
        assert 'template' in llm_config['fallback_backends']
        assert llm_config['max_retries'] == 3
        assert llm_config['timeout'] == 30
        
        logger.info("✅ LLM降级配置正确")
        logger.info(f"   - 主要后端: {llm_config['primary_backend']}")
        logger.info(f"   - 降级后端: {llm_config['fallback_backends']}")
        logger.info(f"   - 最大重试: {llm_config['max_retries']}")
        logger.info(f"   - 超时时间: {llm_config['timeout']}秒")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
