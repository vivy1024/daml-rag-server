# -*- coding: utf-8 -*-
"""
性能测试 conftest — 运行时环境检测

性能/压力测试需要完整的运行环境（API服务、LLM后端、数据库）。
自动检测 localhost:8001 服务可用性，不可用时跳过。
"""

import pytest


def _service_available() -> bool:
    """检测 DAML-RAG 服务是否可达"""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:8001/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


_AVAILABLE = _service_available()
_SKIP_REASON = "性能测试跳过：DAML-RAG 服务不可达（localhost:8001）"


@pytest.fixture(autouse=True)
def _skip_performance_tests():
    """服务不可达时自动跳过性能测试"""
    if not _AVAILABLE:
        pytest.skip(_SKIP_REASON)
