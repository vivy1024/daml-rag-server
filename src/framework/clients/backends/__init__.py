# -*- coding: utf-8 -*-
"""
LLM后端客户端模块

将LLMFallbackManager的后端调用逻辑拆分为独立客户端：
- IBackendClient: 抽象接口
- AnthropicClient: Anthropic Claude (Kiro RS)
- DeepSeekClient: DeepSeek API
- BackendHealthChecker: 健康检查
- TemplateResponseGenerator: 模板降级

Task 45 - Phase 7 Batch 4 架构重构
"""

from .base import IBackendClient
from .anthropic_client import AnthropicClient
from .deepseek_client import DeepSeekClient
from .health_checker import BackendHealthChecker
from .template_generator import TemplateResponseGenerator

__all__ = [
    "IBackendClient",
    "AnthropicClient",
    "DeepSeekClient",
    "BackendHealthChecker",
    "TemplateResponseGenerator",
]
