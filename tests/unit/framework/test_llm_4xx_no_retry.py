# -*- coding: utf-8 -*-
"""
单元测试：4xx 快速失败 — 验证 400 响应不触发重试

streaming-reliability-fix Task 2 验证项
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.framework.clients.llm_fallback_manager import (
    LLMFallbackManager,
    LLMRequest,
    BackendType,
)


class TestNonRetryableError:
    """_is_non_retryable_error 单元测试"""

    def _make_manager(self):
        """构造一个禁用健康检查的 manager（避免真实后端初始化）"""
        with patch.object(LLMFallbackManager, "_init_backends"):
            mgr = LLMFallbackManager(
                primary_backend="deepseek",
                fallback_backends=["template"],
                max_retries=3,
                enable_health_check=False,
            )
            mgr._clients = {}
            mgr._template_generator = None
            return mgr

    def _make_http_error(self, status_code: int) -> httpx.HTTPStatusError:
        """构造指定状态码的 HTTPStatusError"""
        response = httpx.Response(status_code=status_code, request=httpx.Request("POST", "https://api.test.com"))
        return httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=response.request,
            response=response,
        )

    def test_400_is_non_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(400)) is True

    def test_401_is_non_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(401)) is True

    def test_403_is_non_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(403)) is True

    def test_404_is_non_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(404)) is True

    def test_422_is_non_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(422)) is True

    def test_429_is_non_retryable(self):
        """429 Too Many Requests 也是 4xx，不重试"""
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(429)) is True

    def test_500_is_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(500)) is False

    def test_502_is_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(502)) is False

    def test_503_is_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(self._make_http_error(503)) is False

    def test_value_error_is_non_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(ValueError("bad input")) is True

    def test_runtime_error_is_retryable(self):
        mgr = self._make_manager()
        assert mgr._is_non_retryable_error(RuntimeError("something broke")) is False


class TestStreamNoRetryOn400:
    """call_with_fallback_stream 遇到 400 时不重试，直接降级到下一个后端"""

    @pytest.mark.asyncio
    async def test_400_skips_retry_goes_to_fallback(self):
        """400 错误应该 break 出 retry 循环，直接尝试下一个后端（template）"""
        with patch.object(LLMFallbackManager, "_init_backends"):
            mgr = LLMFallbackManager(
                primary_backend="deepseek",
                fallback_backends=["template"],
                max_retries=3,
                enable_health_check=False,
            )
            mgr._clients = {}
            mgr._template_generator = None

        # mock _call_backend_stream 抛出 400
        response_400 = httpx.Response(400, request=httpx.Request("POST", "https://api.test.com"))
        error_400 = httpx.HTTPStatusError("Bad Request", request=response_400.request, response=response_400)

        call_count = 0

        async def mock_stream(backend, request):
            nonlocal call_count
            call_count += 1
            raise error_400
            yield  # make it a generator

        # mock template fallback
        mgr.get_template_response = MagicMock(return_value="模板降级回复")
        mgr._call_backend_stream = mock_stream

        request = LLMRequest(
            query="帮我制定增肌计划",
            few_shot_examples=[],
            tool_results={},
        )

        chunks = []
        async for chunk, meta in mgr.call_with_fallback_stream(request):
            chunks.append((chunk, meta))

        # 关键断言：deepseek 只被调用 1 次（不重试）
        assert call_count == 1, f"400 应该不重试，但被调用了 {call_count} 次"

        # 应该降级到 template
        final_meta = chunks[-1][1]
        assert final_meta is not None
        assert final_meta.backend_used == BackendType.TEMPLATE
