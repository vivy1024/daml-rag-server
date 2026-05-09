# -*- coding: utf-8 -*-
"""
Persistence Layer - 持久化层

提供 LangGraph Checkpointer 工厂，支持：
- Redis 持久化（生产环境）
- InMemorySaver（开发/测试环境）
"""

from .checkpointer import get_checkpointer, CheckpointerConfig

__all__ = ["get_checkpointer", "CheckpointerConfig"]
