# -*- coding: utf-8 -*-
"""
LLM 模型池单元测试

测试内容：
- 模型池配置加载（环境变量）
- fallback 降级逻辑
- 健康检查机制
- 热重载
"""

import os
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.framework.models.llm_pool import (
    LLMPoolManager,
    LLMPoolConfig,
    LLMModelConfig,
    ModelProvider,
    ModelStatus,
)


class TestLLMPoolConfig:
    """LLMPoolConfig 配置加载测试"""

    def test_from_env_defaults(self):
        """默认值应为 DeepSeek"""
        with patch.dict(os.environ, {}, clear=True):
            config = LLMPoolConfig.from_env()
            assert config.primary_model == "deepseek-chat"
            assert config.primary_base_url == "https://api.deepseek.com/v1"
            assert config.primary_api_key == ""
            assert config.primary_provider == ModelProvider.DEEPSEEK
            assert config.template_fallback_enabled is True

    def test_from_env_custom(self):
        """环境变量应覆盖默认值"""
        env = {
            "PRIMARY_MODEL": "glm-4",
            "PRIMARY_BASE_URL": "https://open.bigmodel.cn/api/paas/v4",
            "PRIMARY_API_KEY": "test-key-123",
            "PRIMARY_PROVIDER": "glm",
            "FALLBACK_MODELS": "[]",
            "LLM_HEALTH_CHECK_INTERVAL": "30",
            "TEMPLATE_FALLBACK_ENABLED": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            config = LLMPoolConfig.from_env()
            assert config.primary_model == "glm-4"
            assert config.primary_api_key == "test-key-123"
            assert config.primary_provider == ModelProvider.GLM
            assert config.health_check_interval_s == 30.0
            assert config.template_fallback_enabled is False


class TestLLMPoolManager:
    """LLMPoolManager 核心逻辑测试"""

    def _make_config(self, api_key: str = "test-key") -> LLMPoolConfig:
        """创建测试用配置"""
        return LLMPoolConfig(
            primary_model="deepseek-chat",
            primary_base_url="https://api.deepseek.com/v1",
            primary_api_key=api_key,
            primary_provider=ModelProvider.DEEPSEEK,
            fallback_models_raw="",
        )

    def test_init_with_primary(self):
        """有 API key 时应初始化主模型"""
        config = self._make_config()
        manager = LLMPoolManager(config)
        assert manager.primary_model is not None
        assert manager.primary_model.name == "deepseek-chat"
        assert manager.primary_model.status == ModelStatus.HEALTHY

    def test_init_without_api_key(self):
        """无 API key 时主模型应为 None"""
        config = self._make_config(api_key="")
        manager = LLMPoolManager(config)
        assert manager.primary_model is None

    def test_get_active_model_primary_healthy(self):
        """主模型健康时应返回主模型"""
        config = self._make_config()
        manager = LLMPoolManager(config)
        active = manager.get_active_model()
        assert active is not None
        assert active.name == "deepseek-chat"

    def test_fallback_when_primary_unavailable(self):
        """主模型不可用时应降级到备用模型"""
        fallbacks = json.dumps([{
            "name": "glm-4",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key": "glm-key",
            "provider": "glm",
        }])
        config = LLMPoolConfig(
            primary_model="deepseek-chat",
            primary_base_url="https://api.deepseek.com/v1",
            primary_api_key="test-key",
            primary_provider=ModelProvider.DEEPSEEK,
            fallback_models_raw=fallbacks,
        )
        manager = LLMPoolManager(config)
        # 标记主模型不可用
        manager.primary_model.status = ModelStatus.UNAVAILABLE
        active = manager.get_active_model()
        assert active is not None
        assert active.name == "glm-4"

    def test_template_fallback_when_all_unavailable(self):
        """所有模型不可用时应返回 None（模板兜底）"""
        config = self._make_config()
        manager = LLMPoolManager(config)
        manager.primary_model.status = ModelStatus.UNAVAILABLE
        active = manager.get_active_model()
        assert active is None
        assert manager.is_template_fallback is True

    def test_report_failure_degrades_model(self):
        """连续失败应将模型标记为不可用"""
        config = self._make_config()
        manager = LLMPoolManager(config)
        # 默认 max_failures_before_degrade = 3
        manager.report_failure("deepseek-chat")
        manager.report_failure("deepseek-chat")
        assert manager.primary_model.status == ModelStatus.HEALTHY
        manager.report_failure("deepseek-chat")
        assert manager.primary_model.status == ModelStatus.UNAVAILABLE

    def test_report_success_resets_failures(self):
        """成功调用应重置失败计数"""
        config = self._make_config()
        manager = LLMPoolManager(config)
        manager.report_failure("deepseek-chat")
        manager.report_failure("deepseek-chat")
        manager.report_success("deepseek-chat")
        assert manager.primary_model.consecutive_failures == 0
        assert manager.primary_model.status == ModelStatus.HEALTHY

    def test_parse_fallback_models_invalid_json(self):
        """无效 JSON 应返回空列表"""
        result = LLMPoolManager._parse_fallback_models("not-json")
        assert result == []

    def test_parse_fallback_models_empty(self):
        """空字符串应返回空列表"""
        result = LLMPoolManager._parse_fallback_models("")
        assert result == []

    def test_reload_from_env(self):
        """热重载应更新模型配置"""
        config = self._make_config()
        manager = LLMPoolManager(config)
        assert manager.primary_model.name == "deepseek-chat"

        env = {
            "PRIMARY_MODEL": "qwen-max",
            "PRIMARY_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "PRIMARY_API_KEY": "new-key",
            "PRIMARY_PROVIDER": "qwen",
        }
        with patch.dict(os.environ, env, clear=True):
            manager.reload_from_env()
        assert manager.primary_model.name == "qwen-max"
        assert manager.primary_model.provider == ModelProvider.QWEN


@pytest.mark.asyncio
class TestLLMPoolHealthCheck:
    """健康检查异步测试"""

    async def test_health_check_success(self):
        """健康检查成功应返回 True"""
        config = LLMPoolConfig(
            primary_model="test-model",
            primary_base_url="https://api.test.com/v1",
            primary_api_key="key",
            primary_provider=ModelProvider.OPENAI_COMPATIBLE,
        )
        manager = LLMPoolManager(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await manager.health_check(manager.primary_model)
            assert result is True

    async def test_health_check_timeout(self):
        """健康检查超时应返回 False"""
        import httpx

        config = LLMPoolConfig(
            primary_model="test-model",
            primary_base_url="https://api.test.com/v1",
            primary_api_key="key",
            primary_provider=ModelProvider.OPENAI_COMPATIBLE,
        )
        manager = LLMPoolManager(config)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            result = await manager.health_check(manager.primary_model)
            assert result is False
