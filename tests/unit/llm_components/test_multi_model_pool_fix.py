# -*- coding: utf-8 -*-
"""
多模型蓝绿池修复 - 单元测试

覆盖:
- _auto_register_from_yaml_pool(): 有/无 API_KEY、已注册不覆盖
- select_from_yaml_pool(): 内部自检 API_KEY 过滤
- call_with_fallback_stream(): 空内容触发降级
- _call_backend_stream_inline(): 未知后端 raise ValueError
"""

import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass

import pytest


# ─── 辅助数据 ──────────────────────────────────────────

@dataclass
class FakePoolEntry:
    backend: str
    model: str
    weight: int
    api_base: str
    cost_tier: str
    note: str = ""


FAKE_POOL = [
    FakePoolEntry("glm", "glm-4-flash", 20, "https://open.bigmodel.cn/api/paas/v4", "free"),
    FakePoolEntry("siliconflow", "Qwen/Qwen3-8B", 15, "https://api.siliconflow.cn/v1", "free"),
    FakePoolEntry("qwen", "qwen-turbo", 10, "https://dashscope.aliyuncs.com/compatible-mode/v1", "free_quota"),
]


# ─── Test 1: _auto_register_from_yaml_pool ─────────────

class TestAutoRegisterFromYamlPool:
    """测试 YAML 池自动注册后端客户端"""

    def _make_manager(self):
        """创建一个最小化的 LLMFallbackManager 用于测试"""
        from src.framework.clients.llm_fallback_manager import LLMFallbackManager
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test-key",
        }):
            manager = LLMFallbackManager(
                primary_backend="deepseek",
                fallback_backends=["template"],
                max_retries=1,
                timeout=10,
            )
        return manager

    @patch("src.framework.clients.llm_fallback_manager.LLMFallbackManager._init_backends")
    def test_auto_register_with_api_key(self, mock_init):
        """有 API_KEY 时应自动注册"""
        from src.framework.clients.llm_fallback_manager import LLMFallbackManager, BackendType

        manager = LLMFallbackManager.__new__(LLMFallbackManager)
        manager._clients = {}

        with patch("src.framework.clients.llm_fallback_manager.os.getenv") as mock_getenv:
            mock_getenv.return_value = "fake-glm-key"

            with patch(
                "src.applications.fitness.config.model_routing._get_yaml_pool",
                return_value=(True, [FAKE_POOL[0]]),
            ):
                manager._auto_register_from_yaml_pool()

        assert BackendType.GLM in manager._clients

    @patch("src.framework.clients.llm_fallback_manager.LLMFallbackManager._init_backends")
    def test_auto_register_skip_no_api_key(self, mock_init):
        """无 API_KEY 时应跳过"""
        from src.framework.clients.llm_fallback_manager import LLMFallbackManager, BackendType

        manager = LLMFallbackManager.__new__(LLMFallbackManager)
        manager._clients = {}

        with patch("src.framework.clients.llm_fallback_manager.os.getenv", return_value=""):
            with patch(
                "src.applications.fitness.config.model_routing._get_yaml_pool",
                return_value=(True, [FAKE_POOL[0]]),
            ):
                manager._auto_register_from_yaml_pool()

        assert BackendType.GLM not in manager._clients

    @patch("src.framework.clients.llm_fallback_manager.LLMFallbackManager._init_backends")
    def test_auto_register_no_override(self, mock_init):
        """已注册的后端不应被覆盖"""
        from src.framework.clients.llm_fallback_manager import LLMFallbackManager, BackendType

        manager = LLMFallbackManager.__new__(LLMFallbackManager)
        existing_client = MagicMock()
        manager._clients = {BackendType.GLM: existing_client}

        with patch("src.framework.clients.llm_fallback_manager.os.getenv", return_value="fake-key"):
            with patch(
                "src.applications.fitness.config.model_routing._get_yaml_pool",
                return_value=(True, [FAKE_POOL[0]]),
            ):
                manager._auto_register_from_yaml_pool()

        # 应保持原有客户端
        assert manager._clients[BackendType.GLM] is existing_client


# ─── Test 2: select_from_yaml_pool 内部自检 ────────────

class TestSelectFromYamlPool:
    """测试 YAML 池选择时的 API_KEY 自检"""

    @patch("src.applications.fitness.config.model_routing._get_yaml_pool")
    def test_filter_no_api_key(self, mock_get_pool):
        """无 API_KEY 的后端应被过滤"""
        from src.applications.fitness.config.model_routing import select_from_yaml_pool

        mock_get_pool.return_value = (True, FAKE_POOL)

        with patch.dict(os.environ, {
            "GLM_API_KEY": "fake-key",
            # SILICONFLOW_API_KEY 和 QWEN_API_KEY 不设置
        }, clear=False):
            # 移除可能存在的环境变量
            os.environ.pop("SILICONFLOW_API_KEY", None)
            os.environ.pop("QWEN_API_KEY", None)

            result = select_from_yaml_pool()

        # 只有 glm 有 API_KEY，应该选中 glm
        assert result is not None
        assert result.backend == "glm"

    @patch("src.applications.fitness.config.model_routing._get_yaml_pool")
    def test_all_filtered_returns_none(self, mock_get_pool):
        """所有后端都无 API_KEY 时应返回 None"""
        from src.applications.fitness.config.model_routing import select_from_yaml_pool

        mock_get_pool.return_value = (True, FAKE_POOL)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GLM_API_KEY", None)
            os.environ.pop("SILICONFLOW_API_KEY", None)
            os.environ.pop("QWEN_API_KEY", None)

            result = select_from_yaml_pool()

        assert result is None


# ─── Test 3: 空响应检测 ────────────────────────────────

class TestEmptyResponseDetection:
    """测试空响应触发降级"""

    @pytest.mark.asyncio
    async def test_empty_stream_triggers_fallback(self):
        """流式调用返回空内容应触发降级"""
        from src.framework.clients.llm_fallback_manager import (
            LLMFallbackManager, BackendType, LLMRequest,
        )

        manager = LLMFallbackManager.__new__(LLMFallbackManager)
        manager.primary_backend = BackendType.GLM
        manager.fallback_backends = [BackendType.TEMPLATE]
        manager.max_retries = 1
        manager.timeout = 10
        manager.enable_health_check = False
        manager._clients = {}
        manager._health_checker = None
        manager._template_generator = MagicMock()
        manager._template_generator.generate.return_value = "模板响应"
        manager._health_cache = {}
        manager._health_cache_ttl = 60.0

        # GLM 返回空流
        async def empty_stream(*args, **kwargs):
            return
            yield  # noqa: make it an async generator

        manager._call_backend_stream = AsyncMock(side_effect=empty_stream)

        request = LLMRequest(
            query="测试", few_shot_examples=[], tool_results={},
        )

        chunks = []
        async for chunk, response in manager.call_with_fallback_stream(request):
            chunks.append((chunk, response))

        # 应该降级到 TEMPLATE
        final_response = chunks[-1][1]
        assert final_response is not None
        assert final_response.backend_used == BackendType.TEMPLATE


# ─── Test 4: 未知后端 raise ValueError ──────────────────

class TestUnknownBackendRaise:
    """测试未知后端抛出 ValueError"""

    @pytest.mark.asyncio
    async def test_inline_stream_raises_for_unknown(self):
        """_call_backend_stream_inline 对未知后端应 raise ValueError"""
        from src.framework.clients.llm_fallback_manager import (
            LLMFallbackManager, BackendType, LLMRequest,
        )

        manager = LLMFallbackManager.__new__(LLMFallbackManager)

        request = LLMRequest(
            query="测试", few_shot_examples=[], tool_results={},
            messages=[{"role": "user", "content": "test"}],
        )

        with pytest.raises(ValueError, match="未注册且无内联实现"):
            async for _ in manager._call_backend_stream_inline(
                BackendType.GLM, request
            ):
                pass
