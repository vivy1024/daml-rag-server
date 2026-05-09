# -*- coding: utf-8 -*-
"""
IBackendClient - LLM后端抽象接口

所有LLM后端（DeepSeek等）必须实现此接口。
LLMFallbackManager通过此接口统一调用不同后端。

Task 45 - Phase 7 Batch 4
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from framework.clients.llm_fallback_manager import LLMRequest


class IBackendClient(ABC):
    """
    LLM后端客户端抽象接口

    每个后端实现三个方法：
    - call: 非流式调用
    - call_stream: 流式调用
    - health_check: 健康检查
    """

    @abstractmethod
    async def call(self, request: LLMRequest, timeout: int = 30) -> str:
        ...

    @abstractmethod
    async def call_stream(
        self, request: LLMRequest, timeout: int = 30
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
