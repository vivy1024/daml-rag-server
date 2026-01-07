# -*- coding: utf-8 -*-
"""
智能缓存管理器 - Intelligent Cache Manager

实现多层缓存架构，支持L1内存/L2 Redis/L3数据库的统一缓存管理。

核心特性：
1. 多层缓存架构 (L1内存 → L2 Redis → L3数据库)
2. 统一的缓存接口和失效机制
3. 缓存预热和统计功能
4. 自动降级策略（Redis不可用时使用内存缓存）
5. TTL管理和自动清理

版本: v1.0.0
日期: 2025-12-21
作者: 薛小川
"""

import asyncio
import logging
import time
import json
import hashlib
import pickle
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict, defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别枚举"""
    L1_MEMORY = "l1_memory"      # L1: 内存缓存（最快，50ms）
    L2_REDIS = "l2_redis"        # L2: Redis缓存（中等，100ms）
    L3_DATABASE = "l3_database"  # L3: 数据库（最慢，500ms）


@dataclass
class CacheConfig:
    """缓存配置"""
    # L1内存缓存配置
    l1_enabled: bool = True
    l1_max_size: int = 1000  # 最大条目数
    l1_max_memory_mb: int = 100  # 最大内存占用(MB)
    
    # L2 Redis缓存配置
    l2_enabled: bool = True
    l2_host: str = "localhost"
    l2_port: int = 6379
    l2_db: int = 0
    l2_password: Optional[str] = None
    
    # 默认TTL配置
    default_ttl: int = 300  # 5分钟
    
    # 预热配置
    warmup_enabled: bool = True
    warmup_batch_size: int = 10
    
    # 统计配置
    stats_enabled: bool = True


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    level: CacheLevel
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: int = 300
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return (time.time() - self.created_at) > self.ttl
    
    def mark_accessed(self):
        """标记访问"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStatistics:
    """缓存统计"""
    # 命中统计
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    misses: int = 0
    
    # 操作统计
    total_gets: int = 0
    total_puts: int = 0
    total_invalidations: int = 0
    total_warmups: int = 0
    
    # 性能统计
    avg_get_time_ms: float = 0.0
    l1_hit_rate: float = 0.0
    l2_hit_rate: float = 0.0
    overall_hit_rate: float = 0.0
    
    # 容量统计
    l1_size: int = 0
    l1_memory_mb: float = 0.0
    l2_size: int = 0
    
    def update_hit_rates(self):
        """更新命中率"""
        total_hits = self.l1_hits + self.l2_hits + self.l3_hits
        if self.total_gets > 0:
            self.l1_hit_rate = self.l1_hits / self.total_gets
            self.l2_hit_rate = self.l2_hits / self.total_gets
            self.overall_hit_rate = total_hits / self.total_gets


class IntelligentCacheManager:
    """
    智能缓存管理器
    
    实现三层缓存架构：
    - L1: 内存缓存（最快，容量小）
    - L2: Redis缓存（中等速度，容量中等）
    - L3: 数据库（最慢，容量大）
    
    特性：
    - 统一的缓存接口
    - 自动降级策略
    - TTL管理
    - 缓存预热
    - 统计监控
    """
    
    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        redis_client=None,
        database_client=None
    ):
        """
        初始化智能缓存管理器
        
        Args:
            config: 缓存配置
            redis_client: Redis客户端
            database_client: 数据库客户端
        """
        self.config = config or CacheConfig()
        self.redis_client = redis_client
        self.database_client = database_client
        
        # L1内存缓存（使用OrderedDict实现LRU）
        self.l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.l1_memory_bytes = 0
        
        # 统计信息
        self.stats = CacheStatistics()
        
        # 访问时间记录（用于性能统计）
        self.access_times: List[float] = []
        
        # 启动清理任务
        self._cleanup_task = None
        if self.config.l1_enabled:
            self._start_cleanup_task()
        
        logger.info(
            f"IntelligentCacheManager initialized: "
            f"L1={self.config.l1_enabled}, "
            f"L2={self.config.l2_enabled}, "
            f"max_size={self.config.l1_max_size}"
        )
    
    async def get(
        self,
        key: str,
        fetch_func: Optional[Callable] = None,
        ttl: Optional[int] = None,
        cache_levels: Optional[List[CacheLevel]] = None
    ) -> Optional[Any]:
        """
        多层缓存获取
        
        Args:
            key: 缓存键
            fetch_func: 数据获取函数（缓存未命中时调用）
            ttl: 缓存过期时间（秒）
            cache_levels: 缓存层级列表（默认：L1→L2→L3）
        
        Returns:
            缓存数据或从数据源获取的数据
        """
        start_time = time.time()
        self.stats.total_gets += 1
        
        if cache_levels is None:
            cache_levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DATABASE]
        
        if ttl is None:
            ttl = self.config.default_ttl
        
        try:
            # 1. 尝试L1内存缓存
            if CacheLevel.L1_MEMORY in cache_levels and self.config.l1_enabled:
                value = await self._get_from_l1(key)
                if value is not None:
                    self.stats.l1_hits += 1
                    self._record_access_time(start_time)
                    logger.debug(f"💾 L1缓存命中: {key}")
                    return value
            
            # 2. 尝试L2 Redis缓存
            if CacheLevel.L2_REDIS in cache_levels and self.config.l2_enabled and self.redis_client:
                value = await self._get_from_l2(key)
                if value is not None:
                    self.stats.l2_hits += 1
                    # 回填L1缓存
                    if self.config.l1_enabled:
                        await self._put_to_l1(key, value, ttl)
                    self._record_access_time(start_time)
                    logger.debug(f"💾 L2缓存命中: {key}")
                    return value
            
            # 3. 尝试L3数据库
            if CacheLevel.L3_DATABASE in cache_levels and self.database_client and fetch_func:
                value = await fetch_func()
                if value is not None:
                    self.stats.l3_hits += 1
                    # 回填L1和L2缓存
                    if self.config.l1_enabled:
                        await self._put_to_l1(key, value, ttl)
                    if self.config.l2_enabled and self.redis_client:
                        await self._put_to_l2(key, value, ttl)
                    self._record_access_time(start_time)
                    logger.debug(f"💾 L3数据库命中: {key}")
                    return value
            
            # 4. 缓存未命中，执行fetch_func
            if fetch_func:
                value = await fetch_func()
                if value is not None:
                    # 存储到所有可用的缓存层
                    await self.put(key, value, ttl, cache_levels)
                    self._record_access_time(start_time)
                    return value
            
            # 完全未命中
            self.stats.misses += 1
            self._record_access_time(start_time)
            logger.debug(f"❌ 缓存未命中: {key}")
            return None
            
        except Exception as e:
            logger.error(f"缓存获取异常: {key}, {e}")
            self.stats.misses += 1
            return None
    
    async def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_levels: Optional[List[CacheLevel]] = None
    ):
        """
        存储到缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            cache_levels: 缓存层级列表
        """
        self.stats.total_puts += 1
        
        if cache_levels is None:
            cache_levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]
        
        if ttl is None:
            ttl = self.config.default_ttl
        
        try:
            # 存储到L1内存缓存
            if CacheLevel.L1_MEMORY in cache_levels and self.config.l1_enabled:
                await self._put_to_l1(key, value, ttl)
            
            # 存储到L2 Redis缓存
            if CacheLevel.L2_REDIS in cache_levels and self.config.l2_enabled and self.redis_client:
                await self._put_to_l2(key, value, ttl)
            
            logger.debug(f"✅ 缓存存储成功: {key}")
            
        except Exception as e:
            logger.error(f"缓存存储异常: {key}, {e}")
    
    async def invalidate(self, key: str, pattern: bool = False):
        """
        失效缓存
        
        Args:
            key: 缓存键或模式
            pattern: 是否为模式匹配
        """
        self.stats.total_invalidations += 1
        
        try:
            if pattern:
                # 模式匹配失效
                await self._invalidate_pattern(key)
            else:
                # 精确匹配失效
                await self._invalidate_exact(key)
            
            logger.debug(f"🗑️ 缓存失效: {key}")
            
        except Exception as e:
            logger.error(f"缓存失效异常: {key}, {e}")
    
    async def warm_up(self, keys: List[str], fetch_func: Callable):
        """
        预热缓存
        
        Args:
            keys: 要预热的键列表
            fetch_func: 数据获取函数
        """
        if not self.config.warmup_enabled:
            return
        
        self.stats.total_warmups += len(keys)
        
        logger.info(f"🔥 开始缓存预热: {len(keys)} 个键")
        
        # 分批预热
        batch_size = self.config.warmup_batch_size
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            tasks = [self._warmup_single(key, fetch_func) for key in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"✅ 缓存预热完成: {len(keys)} 个键")
    
    async def _warmup_single(self, key: str, fetch_func: Callable):
        """预热单个键"""
        try:
            # 检查是否已在缓存中
            cached = await self.get(key)
            if cached is not None:
                return
            
            # 获取数据并存储
            value = await fetch_func(key)
            if value is not None:
                await self.put(key, value)
                
        except Exception as e:
            logger.warning(f"预热失败: {key}, {e}")
    
    async def _get_from_l1(self, key: str) -> Optional[Any]:
        """从L1内存缓存获取"""
        if key not in self.l1_cache:
            return None
        
        entry = self.l1_cache[key]
        
        # 检查是否过期
        if entry.is_expired():
            await self._remove_from_l1(key)
            return None
        
        # 标记访问并移动到末尾（LRU）
        entry.mark_accessed()
        self.l1_cache.move_to_end(key)
        
        return entry.value
    
    async def _put_to_l1(self, key: str, value: Any, ttl: int):
        """存储到L1内存缓存"""
        # 计算大小
        size_bytes = self._calculate_size(value)
        
        # 检查容量限制
        while (len(self.l1_cache) >= self.config.l1_max_size or
               self.l1_memory_bytes + size_bytes > self.config.l1_max_memory_mb * 1024 * 1024):
            await self._evict_from_l1()
        
        # 如果键已存在，更新大小统计
        if key in self.l1_cache:
            old_entry = self.l1_cache[key]
            self.l1_memory_bytes -= old_entry.size_bytes
        
        # 创建新条目
        entry = CacheEntry(
            key=key,
            value=value,
            level=CacheLevel.L1_MEMORY,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=ttl,
            size_bytes=size_bytes
        )
        
        self.l1_cache[key] = entry
        self.l1_cache.move_to_end(key)
        self.l1_memory_bytes += size_bytes
    
    async def _get_from_l2(self, key: str) -> Optional[Any]:
        """从L2 Redis缓存获取"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(key)
            if cached_data:
                return pickle.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis获取失败: {key}, {e}")
        
        return None
    
    async def _put_to_l2(self, key: str, value: Any, ttl: int):
        """存储到L2 Redis缓存"""
        if not self.redis_client:
            return
        
        try:
            serialized_data = pickle.dumps(value)
            await self.redis_client.setex(key, ttl, serialized_data)
        except Exception as e:
            logger.warning(f"Redis存储失败: {key}, {e}")
    
    async def _evict_from_l1(self):
        """从L1缓存淘汰（LRU策略）"""
        if not self.l1_cache:
            return
        
        # 移除最旧的条目
        key, entry = self.l1_cache.popitem(last=False)
        self.l1_memory_bytes -= entry.size_bytes
        
        logger.debug(f"🗑️ L1 LRU淘汰: {key}")
    
    async def _remove_from_l1(self, key: str):
        """从L1缓存移除"""
        if key in self.l1_cache:
            entry = self.l1_cache.pop(key)
            self.l1_memory_bytes -= entry.size_bytes
    
    async def _invalidate_exact(self, key: str):
        """精确匹配失效"""
        # 从L1移除
        await self._remove_from_l1(key)
        
        # 从L2移除
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis删除失败: {key}, {e}")
    
    async def _invalidate_pattern(self, pattern: str):
        """模式匹配失效"""
        # 从L1移除匹配的键
        keys_to_remove = [k for k in self.l1_cache.keys() if self._match_pattern(k, pattern)]
        for key in keys_to_remove:
            await self._remove_from_l1(key)
        
        # 从L2移除匹配的键
        if self.redis_client:
            try:
                # Redis SCAN命令查找匹配的键
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis模式删除失败: {pattern}, {e}")
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """简单的模式匹配"""
        import re
        # 将通配符模式转换为正则表达式
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        return re.match(f"^{regex_pattern}$", key) is not None
    
    def _calculate_size(self, value: Any) -> int:
        """计算值的大小"""
        try:
            return len(pickle.dumps(value))
        except:
            return 0
    
    def _record_access_time(self, start_time: float):
        """记录访问时间"""
        access_time = (time.time() - start_time) * 1000  # 转换为毫秒
        self.access_times.append(access_time)
        
        # 保留最近1000次访问记录
        if len(self.access_times) > 1000:
            self.access_times = self.access_times[-1000:]
        
        # 更新平均访问时间
        if self.access_times:
            self.stats.avg_get_time_ms = sum(self.access_times) / len(self.access_times)
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # 每分钟清理一次
                    await self._cleanup_expired()
                except Exception as e:
                    logger.error(f"缓存清理异常: {e}")
        
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = asyncio.create_task(cleanup_loop())
        except RuntimeError:
            self._cleanup_task = None
            logger.debug("缓存清理任务将在事件循环可用时启动")
    
    async def _cleanup_expired(self):
        """清理过期条目"""
        expired_keys = []
        
        for key, entry in self.l1_cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            await self._remove_from_l1(key)
        
        if expired_keys:
            logger.debug(f"🧹 清理过期缓存: {len(expired_keys)} 个条目")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计数据（简化版）
        
        Returns:
            Dict[str, Any]: 缓存统计信息
                - hit_rate: 总体缓存命中率（百分比）
                - l1_hit_rate: L1缓存命中率（百分比）
                - l2_hit_rate: L2缓存命中率（百分比）
                - total_requests: 总请求数
                - l1_size: L1缓存条目数
                - l1_memory_mb: L1缓存内存使用量（MB）
                - l1_hits: L1命中数
                - l2_hits: L2命中数
                - l3_hits: L3命中数
                - misses: 未命中数
        """
        # 更新统计信息
        self.stats.l1_size = len(self.l1_cache)
        self.stats.l1_memory_mb = self.l1_memory_bytes / (1024 * 1024)
        self.stats.update_hit_rates()
        
        return {
            "hit_rate": round(self.stats.overall_hit_rate * 100, 2),
            "l1_hit_rate": round(self.stats.l1_hit_rate * 100, 2),
            "l2_hit_rate": round(self.stats.l2_hit_rate * 100, 2),
            "total_requests": self.stats.total_gets,
            "l1_size": self.stats.l1_size,
            "l1_memory_mb": round(self.stats.l1_memory_mb, 2),
            "l1_hits": self.stats.l1_hits,
            "l2_hits": self.stats.l2_hits,
            "l3_hits": self.stats.l3_hits,
            "misses": self.stats.misses
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计（详细版，保留向后兼容）
        
        Returns:
            Dict[str, Any]: 详细的缓存统计信息
        """
        # 更新统计信息
        self.stats.l1_size = len(self.l1_cache)
        self.stats.l1_memory_mb = self.l1_memory_bytes / (1024 * 1024)
        self.stats.update_hit_rates()
        
        return {
            "l1_hits": self.stats.l1_hits,
            "l2_hits": self.stats.l2_hits,
            "l3_hits": self.stats.l3_hits,
            "misses": self.stats.misses,
            "total_gets": self.stats.total_gets,
            "total_puts": self.stats.total_puts,
            "total_invalidations": self.stats.total_invalidations,
            "total_warmups": self.stats.total_warmups,
            "avg_get_time_ms": round(self.stats.avg_get_time_ms, 2),
            "l1_hit_rate": round(self.stats.l1_hit_rate * 100, 2),
            "l2_hit_rate": round(self.stats.l2_hit_rate * 100, 2),
            "overall_hit_rate": round(self.stats.overall_hit_rate * 100, 2),
            "l1_size": self.stats.l1_size,
            "l1_memory_mb": round(self.stats.l1_memory_mb, 2),
            "l1_max_size": self.config.l1_max_size,
            "l1_max_memory_mb": self.config.l1_max_memory_mb
        }
    
    async def shutdown(self):
        """关闭缓存管理器"""
        # 停止清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 清理内存缓存
        self.l1_cache.clear()
        self.l1_memory_bytes = 0
        
        logger.info("IntelligentCacheManager已关闭")


# 导出
__all__ = [
    "IntelligentCacheManager",
    "CacheConfig",
    "CacheLevel",
    "CacheEntry",
    "CacheStatistics"
]
