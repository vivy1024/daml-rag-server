# -*- coding: utf-8 -*-
"""
多层缓存系统 - 单元测试

覆盖场景:
- L1命中
- L2命中 + L1回填
- 穿透保护（空值缓存）
- LRU淘汰
- L2不可用时降级
- 统计数据准确性

Task 41 - Phase 7 Batch 3 性能与可观测性
"""

import pytest
import asyncio
import sys
import os
import time
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from framework.storage.multi_layer_cache import (
    LRULocalCache,
    MultiLayerCache,
    MultiLayerCacheConfig,
    _SENTINEL_NULL,
)


def run_async(coro):
    """在同步测试中运行async函数（每次创建新loop，避免跨测试污染）"""
    return asyncio.run(coro)


class TestLRULocalCache:
    """L1 LRU缓存测试"""

    def test_basic_get_set(self):
        cache = LRULocalCache(max_items=100)
        cache.set("k1", "v1", ttl=60)
        assert cache.get("k1") == "v1"

    def test_miss_returns_sentinel(self):
        cache = LRULocalCache(max_items=100)
        assert cache.get("nonexistent") is _SENTINEL_NULL

    def test_ttl_expiry(self):
        cache = LRULocalCache(max_items=100)
        cache.set("k1", "v1", ttl=-1)  # 负TTL = 已过期
        assert cache.get("k1") is _SENTINEL_NULL

    def test_no_ttl_never_expires(self):
        cache = LRULocalCache(max_items=100)
        cache.set("k1", "v1")  # 无TTL
        assert cache.get("k1") == "v1"

    def test_lru_eviction(self):
        cache = LRULocalCache(max_items=3)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        # k1是最久未使用的，插入k4时应被淘汰
        cache.set("k4", "v4")
        assert cache.get("k1") is _SENTINEL_NULL
        assert cache.get("k4") == "v4"
        assert cache.eviction_count == 1

    def test_lru_access_refreshes_order(self):
        cache = LRULocalCache(max_items=3)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        # 访问k1，使其变为最近使用
        cache.get("k1")
        # 插入k4，应淘汰k2（最久未使用）
        cache.set("k4", "v4")
        assert cache.get("k1") == "v1"
        assert cache.get("k2") is _SENTINEL_NULL

    def test_delete(self):
        cache = LRULocalCache(max_items=100)
        cache.set("k1", "v1")
        assert cache.delete("k1") is True
        assert cache.get("k1") is _SENTINEL_NULL
        assert cache.delete("k1") is False

    def test_clear(self):
        cache = LRULocalCache(max_items=100)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.size == 0

    def test_size(self):
        cache = LRULocalCache(max_items=100)
        assert cache.size == 0
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        assert cache.size == 2

    def test_update_existing_key(self):
        cache = LRULocalCache(max_items=100)
        cache.set("k1", "v1")
        cache.set("k1", "v2")
        assert cache.get("k1") == "v2"
        assert cache.size == 1


class TestMultiLayerCache:
    """多层缓存集成测试"""

    def _make_l2_mock(self):
        """创建L2 mock"""
        l2 = AsyncMock()
        l2.get = AsyncMock(return_value=None)
        l2.set = AsyncMock(return_value=True)
        l2.delete = AsyncMock(return_value=True)
        l2.invalidate = AsyncMock(return_value=0)
        return l2

    def test_l1_hit(self):
        """L1命中，不查L2"""
        l2 = self._make_l2_mock()
        cache = MultiLayerCache(l2_cache=l2)
        # 预热L1
        cache._l1.set("k1", "v1", ttl=60)
        result = run_async(cache.get("k1"))
        assert result == "v1"
        assert cache.stats.l1_hits == 1
        l2.get.assert_not_called()

    def test_l2_hit_backfills_l1(self):
        """L1 miss → L2 hit → 回填L1"""
        l2 = self._make_l2_mock()
        l2.get = AsyncMock(return_value="from_redis")
        cache = MultiLayerCache(l2_cache=l2)

        result = run_async(cache.get("k1"))
        assert result == "from_redis"
        assert cache.stats.l2_hits == 1
        assert cache.stats.backfills == 1
        # 验证L1已回填
        assert cache._l1.get("k1") == "from_redis"

    def test_both_miss(self):
        """L1和L2都miss"""
        l2 = self._make_l2_mock()
        cache = MultiLayerCache(l2_cache=l2)

        result = run_async(cache.get("k1"))
        assert result is None
        assert cache.stats.l1_misses == 1
        assert cache.stats.l2_misses == 1

    def test_null_cache_protection(self):
        """穿透保护：第一次miss后缓存空值，第二次直接返回"""
        l2 = self._make_l2_mock()
        config = MultiLayerCacheConfig(enable_null_cache=True, null_cache_ttl=30)
        cache = MultiLayerCache(l2_cache=l2, config=config)

        # 第一次：L1 miss + L2 miss → 缓存空值
        run_async(cache.get("k1"))
        assert cache.stats.l2_misses == 1

        # 第二次：L1命中空值 → 不查L2
        run_async(cache.get("k1"))
        assert cache.stats.null_cache_hits == 1
        assert l2.get.call_count == 1  # L2只被调用了1次

    def test_null_cache_disabled(self):
        """禁用穿透保护时，每次miss都查L2"""
        l2 = self._make_l2_mock()
        config = MultiLayerCacheConfig(enable_null_cache=False)
        cache = MultiLayerCache(l2_cache=l2, config=config)

        run_async(cache.get("k1"))
        run_async(cache.get("k1"))
        assert l2.get.call_count == 2

    def test_set_writes_both_layers(self):
        """set同时写入L1和L2"""
        l2 = self._make_l2_mock()
        cache = MultiLayerCache(l2_cache=l2)

        run_async(cache.set("k1", "v1", ttl=300))
        assert cache._l1.get("k1") == "v1"
        l2.set.assert_called_once_with("k1", "v1", ttl=300)

    def test_delete_removes_both_layers(self):
        """delete同时删除L1和L2"""
        l2 = self._make_l2_mock()
        cache = MultiLayerCache(l2_cache=l2)
        cache._l1.set("k1", "v1")

        run_async(cache.delete("k1"))
        assert cache._l1.get("k1") is _SENTINEL_NULL
        l2.delete.assert_called_once_with("k1")

    def test_l2_failure_degrades_gracefully(self):
        """L2异常时降级到仅L1"""
        l2 = self._make_l2_mock()
        l2.get = AsyncMock(side_effect=Exception("Redis down"))
        cache = MultiLayerCache(l2_cache=l2)

        result = run_async(cache.get("k1"))
        assert result is None  # 降级返回None
        assert cache.stats.l2_misses == 1

    def test_no_l2_works_as_pure_l1(self):
        """无L2时作为纯L1缓存"""
        cache = MultiLayerCache(l2_cache=None)

        run_async(cache.set("k1", "v1"))
        result = run_async(cache.get("k1"))
        assert result == "v1"
        assert cache.stats.l1_hits == 1

    def test_statistics(self):
        """统计数据准确性"""
        l2 = self._make_l2_mock()
        l2.get = AsyncMock(return_value="val")
        cache = MultiLayerCache(l2_cache=l2)

        # L2 hit
        run_async(cache.get("k1"))
        # L1 hit (回填后)
        run_async(cache.get("k1"))

        stats = cache.get_statistics()
        assert stats["l1_hits"] == 1
        assert stats["l2_hits"] == 1
        assert stats["backfills"] == 1
        assert stats["total_requests"] == 2
        assert stats["overall_hit_rate"] == 1.0

    def test_invalidate_clears_l1(self):
        """invalidate清空L1并调用L2"""
        l2 = self._make_l2_mock()
        l2.invalidate = AsyncMock(return_value=5)
        cache = MultiLayerCache(l2_cache=l2)
        cache._l1.set("k1", "v1")

        count = run_async(cache.invalidate("k*"))
        assert count == 5
        assert cache._l1.size == 0
