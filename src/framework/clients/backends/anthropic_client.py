# -*- coding: utf-8 -*-
"""
AnthropicClient - Anthropic Claude后端客户端

通过Kiro RS反向代理调用Claude API。

Task 45 - Phase 7 Batch 4
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from .base import IBackendClient

logger = logging.getLogger(__name__)


class AnthropicClient(IBackendClient):
    """Anthropic Claude后端（通过Kiro RS反向代理）"""

    async def call(self, request, timeout: int = 30) -> str:
        from ..llm_client import call_anthropic

        return await asyncio.wait_for(
            call_anthropic(
                query=request.query,
                few_shot_examples=request.few_shot_examples,
                tool_results=request.tool_results,
                system_prompt=request.system_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            ),
            timeout=timeout,
        )

    async def call_stream(self, request, timeout: int = 30) -> AsyncIterator[str]:
        from ..llm_client import call_anthropic_stream

        messages = request.messages or self._build_messages(request)
        async for chunk in call_anthropic_stream(
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            timeout=timeout,
        ):
            yield chunk

    async def health_check(self) -> bool:
        from ..llm_client import LLMConfig
        import httpx

        if not LLMConfig.ANTHROPIC_API_KEY or not LLMConfig.ANTHROPIC_ENABLED:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{LLMConfig.ANTHROPIC_BASE_URL}/v1/models",
                    headers={"Authorization": f"Bearer {LLMConfig.ANTHROPIC_API_KEY}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _build_messages(request):
        from ..llm_client import _format_tool_results

        messages = [{"role": "system", "content": request.system_prompt}]
        for ex in request.few_shot_examples:
            messages.append({"role": "user", "content": ex.get("query", "")})
            messages.append({"role": "assistant", "content": ex.get("response", "")})
        if request.tool_results:
            ctx = _format_tool_results(request.tool_results)
            if ctx:
                messages.append({"role": "system", "content": f"工具调用结果:\n{ctx}"})
        messages.append({"role": "user", "content": request.query})
        return messages
