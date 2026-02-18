# -*- coding: utf-8 -*-
"""
Multi-Layer Cache System - 多层缓存系统

L1: 进程内LRU缓存（OrderedDict，零网络开销）
L2: Redis后端（UnifiedCache）

读取路径: L1 hit → 返回 | L1 miss → L2 hit → 回填L1 → 返回 | 都miss → None
写入路径: 同时写入L1 + L2
删除路径: 同时删除L1 + L2

特性:
- 缓存穿透保护（空值缓存30秒）
- LRU淘汰策略（L1满时淘汰最久未访问的条目）
- 分层统计（L1命中率、L2命中率、穿透保护命中率）

版本: v1.0.0
日期: 2026-02-19
作者: 薛小川
"""

import logging
import time
import threading
from collections import OrderedDict
from typing import Any, Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 空值哨兵对象，区分"缓存了None"和"未缓存"
_SENTINEL_NULL = object()


@dataclass
class MultiLayerCacheConfig:
    """多层缓存配置"""
    l1_max_items: int = 10000          # L1最大条目数
    l1_default_ttl: int = 60           # L1默认TTL（秒）
    null_cache_ttl: int = 30           # 空值缓存TTL（秒）- 防穿透
    enable_null_cache: bool = True     # 启用空值缓存


@dataclass
class MultiLayerCacheStats:
    """多层缓存统计"""
    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    null_cache_hits: int = 0           # 穿透保护命中
    total_requests: int = 0
    backfills: int = 0                 # L2→L1回填次数
    evictions: int = 0                 # L1淘汰次数

    @property
    def l1_hit_rate(self) -> float:
        return self.l1_hits / self.total_requests if self.total_requests > 0 else 0.0

    @property
    def l2_hit_rate(self) -> float:
        total_l2 = self.l2_hits + self.l2_misses
        return self.l2_hits / total_l2 if total_l2 > 0 else 0.0

    @property
    def overall_hit_rate(self) -> float:
        hits = self.l1_hits + self.l2_hits + self.null_cache_hits
        return hits / self.total_requests if self.total_requests > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "l1_hits": self.l1_hits,
            "l1_misses": self.l1_misses,
            "l2_hits": self.l2_hits,
            "l2_misses": self.l2_misses,
            "null_cache_hits": self.null_cache_hits,
            "total_requests": self.total_requests,
            "backfills": self.backfills,
            "evictions": self.evictions,
            "l1_hit_rate": round(self.l1_hit_rate, 4),
            "l2_hit_rate": round(self.l2_hit_rate, 4),
            "overall_hit_rate": round(self.overall_hit_rate, 4),
        }


class LRULocalCache:
    """
    进程内LRU缓存（L1层）

    基于OrderedDict实现，线程安全。
    每个条目带TTL，过期自动失效。
    """

    def __init__(self, max_items: int = 10000):
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # key → (value, expire_at)
        self._max_items = max_items
        self._lock = threading.Lock()
        self._evictions = 0

    def get(self, key: str) -> Any:
        """
        获取缓存值。命中时移到末尾（最近使用）。

        Returns:
            缓存值，未命中返回 _SENTINEL_NULL 以区分 None 值
        """
        with self._lock:
            if key not in self._cache:
                return _SENTINEL_NULL

            value, expire_at = self._cache[key]

            # TTL过期
            if expire_at is not None and time.time() > expire_at:
                del self._cache[key]
                return _SENTINEL_NULL

            # 移到末尾（标记为最近使用）
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值，超出容量时淘汰最久未使用的条目"""
        expire_at = time.time() + ttl if ttl else None
        with self._lock:
            if key in self._cache:
                # 更新已有条目
                self._cache[key] = (value, expire_at)
                self._cache.move_to_end(key)
            else:
                # 新增条目，检查容量
                if len(self._cache) >= self._max_items:
                    self._cache.popitem(last=False)  # 淘汰最久未使用
                    self._evictions += 1
                self._cache[key] = (value, expire_at)

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def eviction_count(self) -> int:
        return self._evictions


class MultiLayerCache:
    """
    多层缓存系统

    L1: LRULocalCache（进程内，零延迟）
    L2: UnifiedCache（Redis后端，网络延迟）

    使用方式:
        cache = MultiLayerCache(unified_cache)
        value = await cache.get("key")
        await cache.set("key", value, ttl=300)
    """

    def __init__(
        self,
        l2_cache=None,
        config: Optional[MultiLayerCacheConfig] = None,
    ):
        """
        Args:
            l2_cache: UnifiedCache实例（L2层，可选）
            config: 多层缓存配置
        """
        self.config = config or MultiLayerCacheConfig()
        self._l1 = LRULocalCache(max_items=self.config.l1_max_items)
        self._l2 = l2_cache
        self.stats = MultiLayerCacheStats()

        logger.info(
            f"MultiLayerCache initialized: "
            f"L1 max={self.config.l1_max_items}, "
            f"L2={'enabled' if l2_cache else 'disabled'}, "
            f"null_cache={'on' if self.config.enable_null_cache else 'off'}"
        )

    async def get(self, key: str) -> Optional[Any]:
        """
        多层读取: L1 → L2 → None

        穿透保护: L2也miss时，缓存空值到L1防止重复穿透
        """
        self.stats.total_requests += 1

        # 1. 查L1
        l1_value = self._l1.get(key)
        if l1_value is not _SENTINEL_NULL:
            # L1命中（包括空值缓存命中）
            if l1_value is None and self.config.enable_null_cache:
                self.stats.null_cache_hits += 1
                return None
            self.stats.l1_hits += 1
            return l1_value

        self.stats.l1_misses += 1

        # 2. 查L2
        if self._l2 is not None:
            try:
                l2_value = await self._l2.get(key)
                if l2_value is not None:
                    # L2命中 → 回填L1
                    self.stats.l2_hits += 1
                    self._l1.set(key, l2_value, ttl=self.config.l1_default_ttl)
                    self.stats.backfills += 1
                    return l2_value
                else:
                    self.stats.l2_misses += 1
            except Exception as e:
                logger.warning(f"L2 cache get failed for key={key}: {e}")
                self.stats.l2_misses += 1

        # 3. 都miss → 穿透保护（缓存空值到L1）
        if self.config.enable_null_cache:
            self._l1.set(key, None, ttl=self.config.null_cache_ttl)

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """同时写入L1和L2"""
        l1_ttl = min(ttl, self.config.l1_default_ttl) if ttl else self.config.l1_default_ttl
        self._l1.set(key, value, ttl=l1_ttl)

        if self._l2 is not None:
            try:
                return await self._l2.set(key, value, ttl=ttl)
            except Exception as e:
                logger.warning(f"L2 cache set failed for key={key}: {e}")
                return False

        return True

    async def delete(self, key: str) -> bool:
        """同时删除L1和L2"""
        self._l1.delete(key)

        if self._l2 is not None:
            try:
                return await self._l2.delete(key)
            except Exception as e:
                logger.warning(f"L2 cache delete failed for key={key}: {e}")
                return False

        return True

    async def invalidate(self, pattern: str) -> int:
        """批量失效（仅L2支持模式匹配，L1全清）"""
        self._l1.clear()

        if self._l2 is not None:
            try:
                return await self._l2.invalidate(pattern)
            except Exception as e:
                logger.warning(f"L2 cache invalidate failed: {e}")
                return 0

        return 0

    def get_statistics(self) -> Dict[str, Any]:
        """获取分层统计"""
        stats = self.stats.to_dict()
        stats["l1_size"] = self._l1.size
        stats["l1_max_items"] = self.config.l1_max_items
        stats["l1_evictions"] = self._l1.eviction_count
        return stats
