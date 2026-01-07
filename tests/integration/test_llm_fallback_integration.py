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
from unittest.mock import Mock, AsyncMock, patch

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLLMFallbackIntegration:
    """LLM降级管理器集成测试"""
    
    @pytest.mark.asyncio
    async def test_llm_decision_engine_uses_fallback_manager(self):
        """测试LLMDecisionEngine使用降级管理器"""
        from src.applications.fitness.llm_decision_engine import (
            LLMDecisionEngine,
            DAGSelectionRequest
        )
        from src.applications.fitness.dag_template_system import DAGTemplateManager
        
        # 初始化
        template_manager = DAGTemplateManager()
        decision_engine = LLMDecisionEngine(template_manager)
        
        # 准备测试请求
        request = DAGSelectionRequest(
            user_query="我想增肌，帮我设计一个训练计划",
            user_profile={
                "basic_info": {"age": 25, "gender": "male"},
                "fitness_config": {"fitness_level": "intermediate", "training_days_per_week": 4},
                "fitness_goals": {"primary_goals": ["增肌"]}
            },
            available_templates=template_manager.get_all_templates()
        )
        
        # Mock LLM响应
        mock_llm_response = """```json
{
    "selected_template_id": "complete_training_plan",
    "selection_reason": "用户需要完整的增肌训练计划",
    "expected_tools": ["professional_program_designer", "intelligent_exercise_selector"],
    "confidence": 0.9,
    "alternative_templates": ["quick_exercise_recommendation"],
    "matched_keywords": ["增肌", "训练计划"]
}
```"""
        
        # Mock LLMFallbackManager（在正确的导入路径）
        with patch('src.framework.clients.llm_fallback_manager.LLMFallbackManager') as MockFallbackManager:
            # 创建mock实例
            mock_manager = Mock()
            mock_response = Mock()
            mock_response.content = mock_llm_response
            mock_response.backend_used = Mock(value="deepseek")
            mock_response.fallback_used = False
            mock_response.attempt_count = 1
            mock_response.duration_ms = 1500.0
            mock_response.error = None
            
            mock_manager.call_with_fallback = AsyncMock(return_value=mock_response)
            MockFallbackManager.return_value = mock_manager
            
            # 执行选择
            result = await decision_engine.select_dag_template(request)
            
            # 验证结果
            assert result.selected_template_id == "complete_training_plan"
            assert result.confidence == 0.9
            assert "增肌" in result.matched_keywords
            
            # 验证LLMFallbackManager被调用
            MockFallbackManager.assert_called_once()
            mock_manager.call_with_fallback.assert_called_once()
            
            logger.info("✅ LLMDecisionEngine正确使用了LLMFallbackManager")
    
    @pytest.mark.asyncio
    async def test_llm_decision_engine_handles_fallback(self):
        """测试LLMDecisionEngine处理降级场景"""
        from src.applications.fitness.llm_decision_engine import (
            LLMDecisionEngine,
            DAGSelectionRequest
        )
        from src.applications.fitness.dag_template_system import DAGTemplateManager
        
        # 初始化
        template_manager = DAGTemplateManager()
        decision_engine = LLMDecisionEngine(template_manager)
        
        # 准备测试请求
        request = DAGSelectionRequest(
            user_query="推荐一些动作",
            user_profile={
                "basic_info": {"age": 30, "gender": "female"},
                "fitness_config": {"fitness_level": "beginner", "training_days_per_week": 3},
                "fitness_goals": {"primary_goals": ["减脂"]}
            },
            available_templates=template_manager.get_all_templates()
        )
        
        # Mock降级响应（使用template后端，但返回有效的JSON）
        mock_llm_response = """```json
{
    "selected_template_id": "exercise_optimization",
    "selection_reason": "降级策略：使用动作优化模板",
    "expected_tools": ["intelligent_exercise_selector"],
    "confidence": 0.3,
    "alternative_templates": [],
    "matched_keywords": ["动作", "推荐"]
}
```"""
        
        # Mock LLMFallbackManager（模拟降级）（在正确的导入路径）
        with patch('src.framework.clients.llm_fallback_manager.LLMFallbackManager') as MockFallbackManager:
            # 创建mock实例
            mock_manager = Mock()
            mock_response = Mock()
            mock_response.content = mock_llm_response
            mock_response.backend_used = Mock(value="template")
            mock_response.fallback_used = True
            mock_response.attempt_count = 4
            mock_response.duration_ms = 5000.0
            mock_response.error = "所有LLM后端都失败"
            
            mock_manager.call_with_fallback = AsyncMock(return_value=mock_response)
            MockFallbackManager.return_value = mock_manager
            
            # 执行选择（应该使用降级策略）
            result = await decision_engine.select_dag_template(request)
            
            # 验证结果（即使使用了降级，仍然应该返回有效的选择）
            assert result.selected_template_id == "exercise_optimization"
            assert result.confidence == 0.3
            
            # 验证LLMFallbackManager被调用
            MockFallbackManager.assert_called_once()
            mock_manager.call_with_fallback.assert_called_once()
            
            logger.info("✅ LLMDecisionEngine正确处理了降级场景")
    
    @pytest.mark.asyncio
    async def test_workflow_step10_uses_fallback_manager(self):
        """测试工作流步骤10使用降级管理器"""
        # 这个测试验证步骤10已经集成了LLMFallbackManager
        # 从workflow_executor.py的代码可以看到，步骤10已经使用了降级管理器
        
        # 读取workflow_executor.py验证
        import os
        workflow_file = os.path.join(
            os.path.dirname(__file__),
            "../../src/applications/fitness/workflow_executor.py"
        )
        
        with open(workflow_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证步骤10使用了LLMFallbackManager
        assert "from ...framework.clients.llm_fallback_manager import LLMFallbackManager" in content
        assert "fallback_manager = LLMFallbackManager(" in content
        assert "llm_response = await fallback_manager.call_with_fallback(llm_request)" in content
        
        logger.info("✅ 工作流步骤10已正确集成LLMFallbackManager")
    
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
