# -*- coding: utf-8 -*-
"""
Core Module - 核心模块（v3.0）

模块：
- simple_framework_initializer.py: 简化的框架初始化器
- query.py: 统一查询接口（集成三层检索）
"""

from .simple_framework_initializer import (
    SimpleFrameworkInitializer,
    get_framework_initializer,
    initialize_framework,
    InitResult
)

__all__ = [
    "SimpleFrameworkInitializer",
    "get_framework_initializer",
    "initialize_framework",
    "InitResult",
]
