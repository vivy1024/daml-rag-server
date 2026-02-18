# -*- coding: utf-8 -*-
"""
LLMFallbackManager 策略模式重构 - 单元测试

验证：
- IBackendClient接口
- BackendHealthChecker缓存逻辑
- TemplateResponseGenerator输出
- LLMFallbackManager编排（委托到客户端）

Task 45 - Phase 7 Batch 4
"""

import pytest
import asyncio
import sys
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from framework.clients.backends.health_checker import BackendHealthChecker
from framework.clients.backends.template_generator import TemplateResponseGenerator
from framework.clients.llm_fallback_manager import (
    LLMFallbackManager, LLMRequest, LLMResponse, BackendType,
)


def run_async(coro):
    return asyncio.run(coro)


def _make_request(**kwargs):
    defaults = dict(
        query="推荐一个增肌训练计划",
        few_shot_examples=[],
        tool_results={},
    )
    defaults.update(kwargs)
    return LLMRequest(**defaults)


# ═══════════════════════════════════════════════════════════
# BackendHealthChecker 测试
# ═══════════════════════════════════════════════════════════

class TestBackendHealthChecker:
    def test_healthy_client(self):
        checker = BackendHealthChecker()
        client = AsyncMock()
        client.health_check = AsyncMock(return_value=True)
        assert run_async(checker.is_healthy("test", client)) is True

    def test_unhealthy_client(self):
        checker = BackendHealthChecker()
        client = AsyncMock()
        client.health_check = AsyncMock(return_value=False)
        assert run_async(checker.is_healthy("test", client)) is False

    def test_cache_hit(self):
        checker = BackendHealthChecker(cache_ttl=60.0)
        client = AsyncMock()
        client.health_check = AsyncMock(return_value=True)
        # 第一次调用
        run_async(checker.is_healthy("test", client))
        # 第二次应命中缓存
        run_async(checker.is_healthy("test", client))
        assert client.health_check.call_count == 1

    def test_mark_unhealthy(self):
        checker = BackendHealthChecker()
        client = AsyncMock()
        client.health_check = AsyncMock(return_value=True)
        run_async(checker.is_healthy("test", client))
        checker.mark_unhealthy("test")
        # 标记后应返回False（缓存被覆盖）
        assert run_async(checker.is_healthy("test", client)) is False
        # 但会重新检查（因为缓存值为False，下次调用会重新check）
        # 实际上缓存TTL内直接返回False
        assert client.health_check.call_count == 1

    def test_exception_marks_unhealthy(self):
        checker = BackendHealthChecker()
        client = AsyncMock()
        client.health_check = AsyncMock(side_effect=Exception("connection refused"))
        assert run_async(checker.is_healthy("test", client)) is False

    def test_get_status(self):
        checker = BackendHealthChecker()
        client = AsyncMock()
        client.health_check = AsyncMock(return_value=True)
        run_async(checker.is_healthy("anthropic", client))
        status = checker.get_status()
        assert "anthropic" in status
        assert status["anthropic"] is True


# ═══════════════════════════════════════════════════════════
# TemplateResponseGenerator 测试
# ═══════════════════════════════════════════════════════════

class TestTemplateResponseGenerator:
    def test_basic_response(self):
        gen = TemplateResponseGenerator()
        result = gen.generate("增肌计划", {"error": "服务不可用"})
        assert "增肌计划" in result
        assert "服务不可用" in result

    def test_with_user_profile(self):
        gen = TemplateResponseGenerator()
        result = gen.generate("训练建议", {
            "tool_results": {
                "step1_user_profile": {
                    "age": 25,
                    "primary_goal": "增肌",
                    "fitness_level": "中级",
                }
            }
        })
        assert "25" in result
        assert "增肌" in result

    def test_with_retrieval_results(self):
        gen = TemplateResponseGenerator()
        result = gen.generate("深蹲替代", {
            "tool_results": {
                "step8_retrieval_results": {"count": 5}
            }
        })
        assert "5" in result

    def test_empty_context(self):
        gen = TemplateResponseGenerator()
        result = gen.generate("test", {})
        assert "test" in result
        assert "建议" in result


# ═══════════════════════════════════════════════════════════
# LLMFallbackManager 编排测试
# ═══════════════════════════════════════════════════════════

class TestLLMFallbackManagerOrchestration:
    def test_primary_success(self):
        """主后端成功时直接返回"""
        manager = LLMFallbackManager(enable_health_check=False)
        mock_client = AsyncMock()
        mock_client.call = AsyncMock(return_value="AI回复内容")
        manager._clients[BackendType.ANTHROPIC] = mock_client

        request = _make_request()
        response = run_async(manager.call_with_fallback(request))
        assert response.content == "AI回复内容"
        assert response.backend_used == BackendType.ANTHROPIC
        assert response.fallback_used is False

    def test_fallback_to_template(self):
        """所有后端失败时降级到模板"""
        manager = LLMFallbackManager(
            max_retries=1, enable_health_check=False
        )
        mock_client = AsyncMock()
        mock_client.call = AsyncMock(side_effect=Exception("API error"))
        manager._clients[BackendType.ANTHROPIC] = mock_client
        manager._clients[BackendType.DEEPSEEK] = mock_client

        request = _make_request()
        response = run_async(manager.call_with_fallback(request))
        assert response.backend_used == BackendType.TEMPLATE
        assert response.fallback_used is True
        assert response.error is not None

    def test_template_response_method(self):
        """get_template_response委托给TemplateResponseGenerator"""
        manager = LLMFallbackManager()
        result = manager.get_template_response("test query", {"error": "test"})
        assert "test query" in result

    def test_backend_type_enum(self):
        """BackendType枚举值正确"""
        assert BackendType.ANTHROPIC.value == "anthropic"
        assert BackendType.DEEPSEEK.value == "deepseek"
        assert BackendType.TEMPLATE.value == "template"

    def test_request_dataclass(self):
        """LLMRequest数据类默认值"""
        req = _make_request()
        assert req.max_tokens == 2000
        assert req.temperature == 0.7
        assert req.stream is False

    def test_response_dataclass(self):
        """LLMResponse数据类"""
        resp = LLMResponse(
            content="test", backend_used=BackendType.ANTHROPIC,
            fallback_used=False, attempt_count=1, duration_ms=100.0,
        )
        assert resp.error is None
        assert resp.partial_success is False
