# -*- coding: utf-8 -*-
"""
集成测试：降级链耗时 ≤ 30s

验证当主后端和备用后端都失败时，降级链能在 30 秒内走完并返回 template 响应。
使用 mock 后端模拟真实的失败场景（5xx 错误 + 指数退避）。

streaming-reliability-fix Task 2 验证项
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
import httpx

from src.framework.clients.llm_fallback_manager import (
    LLMFallbackManager,
    LLMRequest,
    BackendType,
)


class TestDegradationChainTiming:
    """降级链耗时测试"""

    @pytest.mark.asyncio
    async def test_full_degradation_within_30s(self):
        """所有后端 5xx 失败 → 降级到 template，总耗时 ≤ 30s

        降级链: deepseek(3 retries) → anthropic(3 retries) → template
        指数退避: 200ms → 400ms → 800ms（每个后端最多 1.4s 退避）
        预期总耗时: < 5s（mock 后端无网络延迟）
        """
        with patch.object(LLMFallbackManager, "_init_backends"):
            mgr = LLMFallbackManager(
                primary_backend="deepseek",
                fallback_backends=["anthropic", "template"],
                max_retries=3,
                enable_health_check=False,
            )
            mgr._clients = {}
            mgr._template_generator = None

        # mock: 所有非 template 后端都返回 502
        response_502 = httpx.Response(502, request=httpx.Request("POST", "https://api.test.com"))
        error_502 = httpx.HTTPStatusError("Bad Gateway", request=response_502.request, response=response_502)

        call_log = []

        async def mock_stream(backend, request):
            call_log.append(backend.value)
            raise error_502
            yield  # make it a generator

        mgr._call_backend_stream = mock_stream
        mgr.get_template_response = MagicMock(return_value="抱歉，系统繁忙，请稍后再试。")

        request = LLMRequest(
            query="帮我制定增肌计划",
            few_shot_examples=[],
            tool_results={},
        )

        start = time.monotonic()
        chunks = []
        async for chunk, meta in mgr.call_with_fallback_stream(request):
            chunks.append((chunk, meta))
        elapsed = time.monotonic() - start

        # 关键断言：总耗时 ≤ 30s
        assert elapsed < 30.0, f"降级链耗时 {elapsed:.1f}s 超过 30s 上限"

        # deepseek 3 retries + anthropic 3 retries = 6 次调用
        assert len(call_log) == 6, f"预期 6 次后端调用，实际 {len(call_log)}: {call_log}"
        assert call_log == ["deepseek"] * 3 + ["anthropic"] * 3

        # 最终降级到 template
        final_meta = chunks[-1][1]
        assert final_meta is not None
        assert final_meta.backend_used == BackendType.TEMPLATE
        assert "抱歉" in chunks[-2][0]

    @pytest.mark.asyncio
    async def test_4xx_fast_fail_much_faster(self):
        """4xx 错误不重试，降级链应该极快完成（< 2s）"""
        with patch.object(LLMFallbackManager, "_init_backends"):
            mgr = LLMFallbackManager(
                primary_backend="deepseek",
                fallback_backends=["anthropic", "template"],
                max_retries=3,
                enable_health_check=False,
            )
            mgr._clients = {}
            mgr._template_generator = None

        # 所有后端返回 400
        response_400 = httpx.Response(400, request=httpx.Request("POST", "https://api.test.com"))
        error_400 = httpx.HTTPStatusError("Bad Request", request=response_400.request, response=response_400)

        call_count = 0

        async def mock_stream(backend, request):
            nonlocal call_count
            call_count += 1
            raise error_400
            yield

        mgr._call_backend_stream = mock_stream
        mgr.get_template_response = MagicMock(return_value="请求格式有误")

        request = LLMRequest(
            query="test",
            few_shot_examples=[],
            tool_results={},
        )

        start = time.monotonic()
        chunks = []
        async for chunk, meta in mgr.call_with_fallback_stream(request):
            chunks.append((chunk, meta))
        elapsed = time.monotonic() - start

        # 4xx 不重试：每个后端只调用 1 次
        assert call_count == 2, f"4xx 不应重试，预期 2 次调用，实际 {call_count}"
        # 无退避等待，应该极快
        assert elapsed < 2.0, f"4xx 快速失败应 < 2s，实际 {elapsed:.1f}s"
