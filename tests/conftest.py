# -*- coding: utf-8 -*-
"""
Pytest 全局配置 + 共享Fixture库

1) 确保项目根目录在 sys.path 中
2) 提供共享的mock fixture（Neo4j, Qdrant, Redis, LLM等）

Task 47 - Phase 7 Batch 4
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest


def _ensure_project_root_on_syspath() -> None:
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


_ensure_project_root_on_syspath()


# ═══════════════════════════════════════════════════════════
# 共享Fixture - 数据库Mock
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def mock_neo4j():
    """Mock Neo4j客户端"""
    client = MagicMock()
    client.session.return_value.__enter__ = MagicMock()
    client.session.return_value.__exit__ = MagicMock()
    return client


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant客户端"""
    client = MagicMock()
    client.search = MagicMock(return_value=[])
    client.get_collections = MagicMock(return_value=MagicMock(collections=[]))
    return client


@pytest.fixture
def mock_redis():
    """Mock Redis客户端"""
    client = MagicMock()
    client.get = MagicMock(return_value=None)
    client.set = MagicMock(return_value=True)
    client.delete = MagicMock(return_value=True)
    client.ping = MagicMock(return_value=True)
    return client


# ═══════════════════════════════════════════════════════════
# 共享Fixture - LLM Mock
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def mock_llm():
    """Mock LLM客户端（返回固定响应）"""
    client = AsyncMock()
    client.call = AsyncMock(return_value="这是一个AI生成的健身建议。")
    client.call_stream = AsyncMock()
    client.health_check = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_three_layer_engine():
    """Mock三层检索引擎"""
    engine = MagicMock()
    mock_result = MagicMock()
    mock_result.final_results = []
    mock_result.total_confidence = 0.85
    mock_result.reasoning = "test"
    for layer in ("layer_1_result", "layer_2_result", "layer_3_result"):
        lr = MagicMock()
        lr.success = True
        lr.results = []
        lr.confidence = 0.9
        lr.execution_time_ms = 10.0
        setattr(mock_result, layer, lr)
    engine.execute_three_layer_query = AsyncMock(return_value=mock_result)
    return engine


# ═══════════════════════════════════════════════════════════
# 共享Fixture - 框架Mock
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def mock_framework_initializer():
    """Mock框架初始化器"""
    initializer = MagicMock()
    initializer.components = {
        "kg_full": MagicMock(),
        "mcp_client": MagicMock(),
        "domain_adapter": MagicMock(),
    }
    return initializer
