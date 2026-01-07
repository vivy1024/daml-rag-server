# -*- coding: utf-8 -*-
"""
上下文工程模块

多轮对话上下文管理，参考 LangChain Memory 设计模式。

主要组件:
- ContextEngineering: 上下文工程主类
- ContextConfig: 上下文配置
- ContextResult: 上下文构建结果
- ConversationMemory: 对话记忆管理
- TokenCompressor: Token智能压缩
- ProfileInjector: 用户档案注入

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5

版本: v1.0.0
日期: 2025-12-31
"""

from .context_engineering import ContextEngineering, ContextConfig, ContextResult
from .conversation_memory import ConversationMemory, Message, MessageRole
from .token_compressor import TokenCompressor, CompressionStrategy
from .profile_injector import ProfileInjector

__all__ = [
    "ContextEngineering",
    "ContextConfig",
    "ContextResult",
    "ConversationMemory",
    "Message",
    "MessageRole",
    "TokenCompressor",
    "CompressionStrategy",
    "ProfileInjector",
]
