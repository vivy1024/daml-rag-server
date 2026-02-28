# -*- coding: utf-8 -*-
"""
UserMemoryService 冒烟测试

验证 recall/remember 基本功能和 import 链完整性。
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass
from typing import List


# ── import 链完整性测试 ──────────────────────────────────


def test_import_user_memory_service():
    """验证 UserMemoryService 可以正常 import（模拟生产环境路径）"""
    from src.applications.fitness.services.user_memory import (
        UserMemoryService,
        get_user_memory_service,
        COLLECTION_NAME,
        MEMORY_CATEGORIES,
    )
    assert UserMemoryService is not None
    assert COLLECTION_NAME == "user_memory"
    assert "general" in MEMORY_CATEGORIES


def test_import_from_context_engineering():
    """验证 context_engineering 的 import 链完整"""
    from src.applications.fitness.context.context_engineering import ContextEngineering
    assert ContextEngineering is not None


# ── recall 测试 ──────────────────────────────────────────


@dataclass
class FakePoint:
    id: str
    score: float
    payload: dict


@dataclass
class FakeQueryResponse:
    points: List[FakePoint]


@pytest.fixture
def memory_service():
    """创建带 mock 依赖的 UserMemoryService"""
    from src.applications.fitness.services.user_memory import UserMemoryService

    mock_qdrant = MagicMock()
    mock_embed = MagicMock(return_value=[0.1] * 1024)
    return UserMemoryService(qdrant_client=mock_qdrant, embedding_fn=mock_embed)


@pytest.mark.asyncio
async def test_recall_returns_results(memory_service):
    """recall 正常返回记忆列表"""
    fake_points = [
        FakePoint(
            id="abc-123",
            score=0.85,
            payload={
                "content": "用户喜欢深蹲",
                "category": "exercise_preference",
                "created_at": "2026-01-01T00:00:00Z",
            },
        )
    ]
    memory_service._get_qdrant().query_points.return_value = FakeQueryResponse(
        points=fake_points
    )

    results = await memory_service.recall(user_id=1, query="深蹲偏好")

    assert len(results) == 1
    assert results[0]["content"] == "用户喜欢深蹲"
    assert results[0]["score"] == 0.85
    assert results[0]["category"] == "exercise_preference"


@pytest.mark.asyncio
async def test_recall_graceful_degradation(memory_service):
    """recall 失败时优雅降级，返回空列表"""
    memory_service._get_qdrant().query_points.side_effect = ConnectionError(
        "Qdrant 不可用"
    )

    results = await memory_service.recall(user_id=2, query="测试")

    assert results == []


@pytest.mark.asyncio
async def test_recall_empty_results(memory_service):
    """recall 无匹配时返回空列表"""
    memory_service._get_qdrant().query_points.return_value = FakeQueryResponse(
        points=[]
    )

    results = await memory_service.recall(user_id=1, query="不存在的查询")

    assert results == []


# ── remember 测试 ────────────────────────────────────────


@pytest.mark.asyncio
async def test_remember_new_memory(memory_service):
    """remember 存储新记忆"""
    # 模拟无相似记忆
    memory_service._get_qdrant().query_points.return_value = FakeQueryResponse(
        points=[]
    )
    memory_service._get_qdrant().upsert.return_value = None

    point_id = await memory_service.remember(
        user_id=1, content="我喜欢卧推", category="exercise_preference"
    )

    assert point_id is not None
    memory_service._get_qdrant().upsert.assert_called_once()


@pytest.mark.asyncio
async def test_remember_dedup_update(memory_service):
    """remember 去重：相似度 > 0.9 时更新而非新增"""
    existing_point = FakePoint(
        id="existing-id",
        score=0.95,
        payload={"content": "旧内容", "category": "general", "created_at": "2026-01-01"},
    )
    memory_service._get_qdrant().query_points.return_value = FakeQueryResponse(
        points=[existing_point]
    )
    memory_service._get_qdrant().set_payload.return_value = None

    point_id = await memory_service.remember(
        user_id=1, content="更新内容"
    )

    assert point_id == "existing-id"
    memory_service._get_qdrant().set_payload.assert_called_once()
    # 不应该调用 upsert（因为是更新）
    memory_service._get_qdrant().upsert.assert_not_called()


@pytest.mark.asyncio
async def test_remember_invalid_category_fallback(memory_service):
    """remember 无效 category 自动降级为 general"""
    memory_service._get_qdrant().query_points.return_value = FakeQueryResponse(
        points=[]
    )
    memory_service._get_qdrant().upsert.return_value = None

    await memory_service.remember(
        user_id=1, content="测试", category="invalid_category"
    )

    # 验证 upsert 调用中 category 被修正为 general
    call_args = memory_service._get_qdrant().upsert.call_args
    points = call_args.kwargs.get("points") or call_args[1].get("points")
    assert points[0].payload["category"] == "general"
