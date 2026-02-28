# -*- coding: utf-8 -*-
"""
UnifiedCache L1 进程内缓存测试

验证：
1. Redis=None 时 L1 缓存命中
2. L1 过期后重新从 API 加载
3. Redis 不可用时不再每次都打 WARNING（L1 命中时静默）
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.framework.storage.unified_cache import UnifiedCache, CacheConfig


@pytest.fixture
def cache_no_redis():
    """Redis=None 的缓存实例"""
    return UnifiedCache(redis_client=None, config=CacheConfig(default_ttl=300))


@pytest.fixture
def cache_with_redis():
    """带 mock Redis 的缓存实例"""
    mock_redis = AsyncMock()
    return UnifiedCache(redis_client=mock_redis, config=CacheConfig(default_ttl=300))


# ── L1 基本功能 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_l1_set_and_get_without_redis(cache_no_redis):
    """Redis=None 时，set 写 L1，get 从 L1 命中"""
    result = await cache_no_redis.set("user:1:profile", {"name": "test"})
    assert result is True  # L1 写入成功

    value = await cache_no_redis.get("user:1:profile")
    assert value == {"name": "test"}
    assert cache_no_redis.statistics.cache_hits == 1


@pytest.mark.asyncio
async def test_l1_hit_no_redis_call(cache_with_redis):
    """L1 命中时不查 Redis"""
    cache_with_redis._l1_set("key1", "value1")

    value = await cache_with_redis.get("key1")

    assert value == "value1"
    # Redis.get 不应被调用
    cache_with_redis.redis.get.assert_not_called()


# ── L1 过期 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_l1_expiry(cache_no_redis):
    """L1 过期后返回 None"""
    # 设置 1 秒 TTL
    await cache_no_redis.set("short_ttl", "data", ttl=1)

    # 立即读取应命中
    assert await cache_no_redis.get("short_ttl") == "data"

    # 等待过期
    await asyncio.sleep(1.1)

    # 过期后应返回 None
    assert await cache_no_redis.get("short_ttl") is None


# ── Redis 回填 L1 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_redis_hit_backfills_l1(cache_with_redis):
    """Redis 命中后回填 L1，后续请求直接走 L1"""
    import json

    cache_with_redis.redis.get = AsyncMock(
        return_value=json.dumps({"name": "from_redis"})
    )

    # 第一次：L1 miss → Redis hit → 回填 L1
    value1 = await cache_with_redis.get("user:2:profile")
    assert value1 == {"name": "from_redis"}
    cache_with_redis.redis.get.assert_called_once()

    # 第二次：L1 hit → 不查 Redis
    cache_with_redis.redis.get.reset_mock()
    value2 = await cache_with_redis.get("user:2:profile")
    assert value2 == {"name": "from_redis"}
    cache_with_redis.redis.get.assert_not_called()


# ── WARNING 抑制 ────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_redis_warning_suppressed_after_first(cache_no_redis):
    """Redis 不可用时只打一次 WARNING，后续 L1 命中时静默"""
    with patch("src.framework.storage.unified_cache.logger") as mock_logger:
        # 第一次 set：应打 WARNING
        await cache_no_redis.set("k1", "v1")
        warning_calls_1 = mock_logger.warning.call_count

        # 第二次 set：不应再打 WARNING
        await cache_no_redis.set("k2", "v2")
        warning_calls_2 = mock_logger.warning.call_count

        assert warning_calls_1 == 1
        assert warning_calls_2 == 1  # 没有新增 WARNING


# ── delete 清理 L1 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_clears_l1(cache_no_redis):
    """delete 同时清理 L1"""
    await cache_no_redis.set("to_delete", "data")
    assert await cache_no_redis.get("to_delete") == "data"

    await cache_no_redis.delete("to_delete")
    assert await cache_no_redis.get("to_delete") is None


# ── set 同时写 L1 + Redis ───────────────────────────────


@pytest.mark.asyncio
async def test_set_writes_both_l1_and_redis(cache_with_redis):
    """set 同时写 L1 和 Redis"""
    cache_with_redis.redis.setex = AsyncMock(return_value=True)

    await cache_with_redis.set("dual_key", "dual_value", ttl=60)

    # L1 应有值
    assert cache_with_redis._l1_get("dual_key") == "dual_value"
    # Redis 也应被调用
    cache_with_redis.redis.setex.assert_called_once()


# ── 容量限制 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_l1_capacity_limit(cache_no_redis):
    """L1 超过 maxsize 时自动清理"""
    cache_no_redis._l1_maxsize = 10

    for i in range(15):
        await cache_no_redis.set(f"key_{i}", f"value_{i}")

    # 缓存条目数不应超过 maxsize
    assert len(cache_no_redis._l1_cache) <= 10
