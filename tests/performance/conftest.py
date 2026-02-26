# -*- coding: utf-8 -*-
"""
性能测试 conftest — 统一 skip 条件

性能/压力测试需要完整的运行环境（LLM后端、数据库、足够的内存/CPU）。
默认跳过，设置 RUN_PERFORMANCE_TESTS=1 环境变量时才执行。

用法：
  RUN_PERFORMANCE_TESTS=1 python -m pytest tests/performance/
"""

import os
import pytest


_SKIP_REASON = (
    "性能测试默认跳过（需要完整运行环境 + LLM后端）。"
    "设置 RUN_PERFORMANCE_TESTS=1 启用。"
)

_ENABLED = os.getenv("RUN_PERFORMANCE_TESTS", "").strip() in ("1", "true", "yes")


@pytest.fixture(autouse=True)
def _skip_performance_tests():
    """自动跳过性能测试（除非 RUN_PERFORMANCE_TESTS=1）"""
    if not _ENABLED:
        pytest.skip(_SKIP_REASON)
