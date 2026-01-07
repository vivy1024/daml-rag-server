# -*- coding: utf-8 -*-
"""
API Package

DAML-RAG API服务包，提供：
- 统一的HTTP接口
- 三层检索架构集成
- 字段标准化处理
- 反幻觉验证
- 性能监控

版本：v2.0.0
更新日期：2025-11-17
"""

from .main import app, create_app
from .routes import api_router

__all__ = [
    'app',
    'create_app',
    'api_router'
]