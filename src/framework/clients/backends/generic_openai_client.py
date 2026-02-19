# -*- coding: utf-8 -*-
"""
GenericOpenAIClient - 通用OpenAI兼容后端客户端

支持所有OpenAI兼容API（Qwen、SiliconFlow、GLM等），
通过 base_url/api_key/model 参数化实现一个客户端覆盖多个后端。

多模型集成 - Task 1
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from .base import IBackendClient

logger = logging.getLogger(__name__)


class GenericOpenAIClient(IBackendClient):
    """通用OpenAI兼容后端客户端"""

    def __init__(self, backend_name: str, base_url: str, api_key: str, model: str):
        self.backend_name = backend_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def call(self, request, timeout: int = 30) -> str:
        model = getattr(request, "model_override", None) or self.model
        messages = request.messages or self._build_messages(request)
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def call_stream(self, request, timeout: int = 30) -> AsyncIterator[str]:
        model = getattr(request, "model_override", None) or self.model
        messages = request.messages or self._build_messages(request)
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def _build_messages(self, request) -> list:
        messages = [{"role": "system", "content": request.system_prompt}]
        for ex in request.few_shot_examples:
            messages.append({"role": "user", "content": ex.get("query", "")})
            messages.append({"role": "assistant", "content": ex.get("response", "")})
        if request.tool_results:
            from ..llm_client import _format_tool_results
            ctx = _format_tool_results(request.tool_results)
            if ctx:
                messages.append({"role": "system", "content": f"工具调用结果:\n{ctx}"})
        messages.append({"role": "user", "content": request.query})
        return messages

    def __repr__(self) -> str:
        return f"GenericOpenAIClient(name={self.backend_name}, model={self.model})"
