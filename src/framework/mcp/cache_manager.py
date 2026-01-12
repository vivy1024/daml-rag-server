# -*- coding: utf-8 -*-
"""
MCP工具缓存管理器（统一版）

提供统一的缓存机制，包括：
1. 多种缓存策略（TTL、LRU）
2. 缓存失效管理
3. 缓存统计和监控
4. 异步缓存操作
5. 用户档案缓存（从orchestration/cache_manager合并）
6. 会员权限缓存（从orchestration/cache_manager合并）

Requirements: 3.1, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3, 7.4, 7.5
Version: 2.0.0
Date: 2026-01-12
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import asyncio
import logging
import json
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field


# ============ 缓存统计数据类（从orchestration/cache_manager合并） ============

@dataclass
class CacheStatistics:
    """
    缓存统计信息
    
    用于跟踪用户档案和会员权限缓存的命中率和性能指标。
    """
    # 用户档案统计
    user_profile_requests: int = 0
    user_profile_hits: int = 0
    user_profile_misses: int = 0
    
    # 会员权限统计
    membership_requests: int = 0
    membership_hits: int = 0
    membership_misses: int = 0
    
    # 性能统计
    total_requests: int = 0
    total_hits: int = 0
    total_misses: int = 0
    avg_response_time_ms: float = 0.0
    
    def update_hit_rate(self):
        """更新命中率"""
        self.total_requests = self.user_profile_requests + self.membership_requests
        self.total_hits = self.user_profile_hits + self.membership_hits
        self.total_misses = self.user_profile_misses + self.membership_misses
    
    def get_hit_rate(self) -> float:
        """获取总体命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.total_hits / self.total_requests
    
    def get_user_profile_hit_rate(self) -> float:
        """获取用户档案命中率"""
        if self.user_profile_requests == 0:
            return 0.0
        return self.user_profile_hits / self.user_profile_requests
    
    def get_membership_hit_rate(self) -> float:
        """获取会员权限命中率"""
        if self.membership_requests == 0:
            return 0.0
        return self.membership_hits / self.membership_requests


# ============ 缓存条目类 ============

class CacheEntry:
    """
    缓存条目
    
    Attributes:
        key: 缓存键
        value: 缓存值
        created_at: 创建时间
        expires_at: 过期时间
        access_count: 访问次数
        last_accessed: 最后访问时间
    """
    
    def __init__(
        self,
        key: str,
        value: Any,
        ttl_seconds: int
    ):
        """
        初始化缓存条目
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: 生存时间（秒）
        """
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.expires_at
    
    def access(self) -> Any:
        """访问缓存（更新访问统计）"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "key": self.key,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
            "is_expired": self.is_expired()
        }


# ============ 缓存管理器类 ============

class CacheManager:
    """
    统一缓存管理器
    
    提供统一的缓存管理功能，支持：
    1. TTL（Time To Live）过期策略
    2. LRU（Least Recently Used）淘汰策略
    3. 缓存统计和监控
    4. 批量操作
    5. 模式匹配失效
    6. 用户档案缓存（从orchestration/cache_manager合并）
    7. 会员权限缓存（从orchestration/cache_manager合并）
    
    Usage:
        # 通用缓存用法
        cache = CacheManager(max_size=1000)
        await cache.set("key", value, ttl=3600)
        value = await cache.get("key")
        await cache.invalidate("key")
        
        # 用户档案/会员权限缓存用法
        cache = CacheManager(
            user_cache=user_cache_instance,
            membership_cache=membership_cache_instance
        )
        profile = await cache.get_user_profile(user_id)
        membership = await cache.get_membership_permissions(user_id)
    """
    
    # 预定义的缓存配置
    CACHE_CONFIG = {
        "entity_data": {
            "ttl": 86400,  # 24小时
            "description": "实体数据缓存"
        },
        "alias_mapping": {
            "ttl": 604800,  # 7天
            "description": "别名映射缓存"
        },
        "rule_data": {
            "ttl": 86400,  # 24小时
            "description": "规则数据缓存"
        },
        "metadata": {
            "ttl": 3600,  # 1小时
            "description": "元数据缓存"
        },
        # 用户档案和会员权限配置（从orchestration/cache_manager合并）
        "user_profile": {
            "ttl": 300,  # 5分钟
            "description": "用户档案缓存"
        },
        "membership": {
            "ttl": 600,  # 10分钟
            "description": "会员权限缓存"
        }
    }
    
    def __init__(
        self,
        max_size: int = 1000,
        logger: Optional[logging.Logger] = None,
        # 用户档案/会员权限缓存参数（从orchestration/cache_manager合并）
        user_cache=None,
        membership_cache=None,
        user_profile_ttl: int = 300,  # 5分钟
        membership_ttl: int = 600  # 10分钟
    ):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数（LRU淘汰）
            logger: 日志记录器
            user_cache: 用户档案缓存实例（IntelligentUserCache）
            membership_cache: 会员权限缓存实例（IntelligentMembershipCache）
            user_profile_ttl: 用户档案缓存TTL（秒）
            membership_ttl: 会员权限缓存TTL（秒）
        """
        self.max_size = max_size
        self.logger = logger or logging.getLogger(__name__)
        
        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # 缓存统计（通用）
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "evictions": 0
        }
        
        # 锁（用于并发控制）
        self._lock = asyncio.Lock()
        
        # 用户档案/会员权限缓存（从orchestration/cache_manager合并）
        self.user_cache = user_cache
        self.membership_cache = membership_cache
        self.user_profile_ttl = user_profile_ttl
        self.membership_ttl = membership_ttl
        
        # 用户档案/会员权限统计信息
        self.stats = CacheStatistics()
        
        # 响应时间记录（用于计算平均值）
        self.response_times = []
        
        if user_cache or membership_cache:
            self.logger.info(
                f"CacheManager initialized with user/membership cache: "
                f"user_profile_ttl={user_profile_ttl}s, "
                f"membership_ttl={membership_ttl}s"
            )

    # ============ 通用缓存方法 ============
    
    async def get(
        self,
        key: str,
        fetch_func: Optional[Callable[[], Any]] = None,
        ttl: Optional[int] = None,
    ) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            fetch_func: 缓存未命中时的回源函数（可选，可为async或sync）
            ttl: 回源写入缓存的TTL（秒，可选）
        
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is not None and not entry.is_expired():
                # 命中，更新访问统计并移到末尾（LRU）
                self._cache.move_to_end(key)
                value = entry.access()
                self._stats["hits"] += 1
                self.logger.debug(
                    f"✅ 缓存命中: {key} "
                    f"(访问次数: {entry.access_count})"
                )
                return value

            # 未命中或已过期
            if entry is None:
                self._stats["misses"] += 1
                self.logger.debug(f"🔍 缓存未命中: {key}")
            else:
                del self._cache[key]
                self._stats["misses"] += 1
                self.logger.debug(f"⏰ 缓存已过期: {key}")

        # 未命中且无回源函数
        if fetch_func is None:
            return None

        # 回源（避免持锁执行）
        try:
            fetched = fetch_func()
            if asyncio.iscoroutine(fetched):
                fetched = await fetched
        except Exception as e:
            self.logger.error(f"回源函数执行失败: key={key}, error={e}")
            return None

        if fetched is None:
            return None

        await self.set(key, fetched, ttl=ttl)
        return fetched
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），如果为None则使用默认配置
        
        Returns:
            是否设置成功
        """
        async with self._lock:
            # 确定TTL
            if ttl is None:
                ttl = self._get_default_ttl(key)
            
            # 检查是否需要淘汰
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            # 创建缓存条目
            entry = CacheEntry(key, value, ttl)
            self._cache[key] = entry
            self._cache.move_to_end(key)
            
            self._stats["sets"] += 1
            self.logger.debug(
                f"💾 缓存已设置: {key} "
                f"(TTL: {ttl}秒, 过期时间: {entry.expires_at.isoformat()})"
            )
            return True

    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """兼容别名：put == set"""
        return await self.set(key, value, ttl=ttl)

    async def invalidate(self, key: str) -> bool:
        """
        使缓存失效
        
        Args:
            key: 缓存键
        
        Returns:
            是否成功失效
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["invalidations"] += 1
                self.logger.debug(f"🗑️ 缓存已失效: {key}")
                return True
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        按模式使缓存失效
        
        支持通配符 * 匹配
        
        Args:
            pattern: 缓存键模式（如 "muscle_*"）
        
        Returns:
            失效的缓存条目数
        """
        async with self._lock:
            # 转换为正则表达式
            import re
            regex_pattern = pattern.replace("*", ".*")
            regex = re.compile(f"^{regex_pattern}$")
            
            # 查找匹配的键
            keys_to_delete = [
                key for key in self._cache.keys()
                if regex.match(key)
            ]
            
            # 删除
            for key in keys_to_delete:
                del self._cache[key]
                self._stats["invalidations"] += 1
            
            if keys_to_delete:
                self.logger.info(
                    f"🗑️ 批量失效缓存: 模式={pattern}, "
                    f"数量={len(keys_to_delete)}"
                )
            
            return len(keys_to_delete)
    
    async def clear(self) -> int:
        """
        清空所有缓存
        
        Returns:
            清空的缓存条目数
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"🗑️ 清空所有缓存: 数量={count}")
            return count

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息（通用缓存）
        
        Returns:
            统计信息字典
        """
        async with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests
                if total_requests > 0 else 0
            )
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": f"{hit_rate:.2%}",
                "sets": self._stats["sets"],
                "invalidations": self._stats["invalidations"],
                "evictions": self._stats["evictions"]
            }
    
    async def get_entries(self) -> List[Dict[str, Any]]:
        """
        获取所有缓存条目信息
        
        Returns:
            缓存条目列表
        """
        async with self._lock:
            return [
                entry.to_dict()
                for entry in self._cache.values()
            ]
    
    def _get_default_ttl(self, key: str) -> int:
        """
        获取默认TTL
        
        根据键名前缀匹配预定义配置
        
        Args:
            key: 缓存键
        
        Returns:
            TTL（秒）
        """
        for config_key, config in self.CACHE_CONFIG.items():
            if key.startswith(config_key):
                return config["ttl"]
        
        # 默认1小时
        return 3600
    
    def _evict_lru(self) -> None:
        """
        淘汰最少使用的缓存条目（LRU）
        """
        if self._cache:
            # OrderedDict的第一个元素是最少使用的
            key, entry = self._cache.popitem(last=False)
            self._stats["evictions"] += 1
            self.logger.debug(
                f"🔄 LRU淘汰缓存: {key} "
                f"(访问次数: {entry.access_count})"
            )

    async def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目
        
        Returns:
            清理的条目数
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self.logger.info(
                    f"🧹 清理过期缓存: 数量={len(expired_keys)}"
                )
            
            return len(expired_keys)
    
    @staticmethod
    def generate_cache_key(
        prefix: str,
        params: Dict[str, Any]
    ) -> str:
        """
        生成缓存键
        
        基于前缀和参数生成唯一的缓存键
        
        Args:
            prefix: 键前缀（如 "muscle_training_data"）
            params: 参数字典
        
        Returns:
            缓存键
        """
        # 排序参数以确保一致性
        sorted_params = sorted(params.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        
        # 生成哈希
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"{prefix}:{params_hash}"
    
    # ============ 用户档案/会员权限缓存方法（从orchestration/cache_manager合并） ============
    
    def _record_response_time(self, response_time_ms: float):
        """
        记录响应时间
        
        Args:
            response_time_ms: 响应时间（毫秒）
        """
        self.response_times.append(response_time_ms)
        
        # 保留最近1000次记录
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
        
        # 更新平均响应时间
        if self.response_times:
            self.stats.avg_response_time_ms = sum(self.response_times) / len(self.response_times)

    async def get_user_profile(
        self,
        user_id: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        从缓存获取用户档案
        
        Args:
            user_id: 用户ID
            force_refresh: 是否强制刷新缓存
            
        Returns:
            Optional[Dict[str, Any]]: 用户档案数据，如果未找到返回None
        """
        start_time = time.time()
        self.stats.user_profile_requests += 1
        
        try:
            if not self.user_cache:
                self.logger.warning("用户档案缓存未初始化")
                self.stats.user_profile_misses += 1
                return None
            
            # 从缓存获取
            profile = await self.user_cache.get_user_profile(
                user_id=user_id,
                force_refresh=force_refresh
            )
            
            # 更新统计
            if profile is not None:
                self.stats.user_profile_hits += 1
                is_fallback = profile.get('_fallback', False)
                
                if is_fallback:
                    self.logger.warning(
                        f"📦 用户档案缓存命中（降级数据）: user_id={user_id}"
                    )
                else:
                    self.logger.debug(
                        f"✅ 用户档案缓存命中: user_id={user_id}"
                    )
            else:
                self.stats.user_profile_misses += 1
                self.logger.debug(
                    f"❌ 用户档案缓存未命中: user_id={user_id}"
                )
            
            # 记录响应时间
            response_time = (time.time() - start_time) * 1000
            self._record_response_time(response_time)
            
            return profile
            
        except Exception as e:
            self.stats.user_profile_misses += 1
            self.logger.error(f"获取用户档案缓存失败: user_id={user_id}, error={e}")
            return None

    async def set_user_profile(
        self,
        user_id: str,
        profile: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        缓存用户档案
        
        Args:
            user_id: 用户ID
            profile: 用户档案数据
            ttl: 缓存过期时间（秒），默认使用配置的TTL
        """
        try:
            if not self.user_cache:
                self.logger.warning("用户档案缓存未初始化")
                return
            
            # 使用默认TTL或指定的TTL
            cache_ttl = ttl if ttl is not None else self.user_profile_ttl
            
            self.logger.debug(
                f"💾 缓存用户档案: user_id={user_id}, ttl={cache_ttl}s"
            )
            
            # 由于IntelligentUserCache在get时会自动缓存，
            # 这里主要用于手动更新缓存的场景
            # 我们可以通过invalidate + get的方式来强制更新
            await self.user_cache.invalidate_user(user_id)
            
        except Exception as e:
            self.logger.error(f"缓存用户档案失败: user_id={user_id}, error={e}")
    
    async def get_membership_permissions(
        self,
        user_id: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        从缓存获取会员权限
        
        Args:
            user_id: 用户ID
            force_refresh: 是否强制刷新缓存
            
        Returns:
            Optional[Dict[str, Any]]: 会员权限数据，如果未找到返回None
        """
        start_time = time.time()
        self.stats.membership_requests += 1
        
        try:
            if not self.membership_cache:
                self.logger.warning("会员权限缓存未初始化")
                self.stats.membership_misses += 1
                return None
            
            # 从缓存获取
            membership = await self.membership_cache.get_user_membership(
                user_id=user_id,
                force_refresh=force_refresh
            )
            
            # 更新统计
            if membership is not None:
                self.stats.membership_hits += 1
                is_fallback = membership.get('_fallback', False)
                
                if is_fallback:
                    self.logger.warning(
                        f"📦 会员权限缓存命中（降级数据）: user_id={user_id}"
                    )
                else:
                    self.logger.debug(
                        f"✅ 会员权限缓存命中: user_id={user_id}"
                    )
            else:
                self.stats.membership_misses += 1
                self.logger.debug(
                    f"❌ 会员权限缓存未命中: user_id={user_id}"
                )
            
            # 记录响应时间
            response_time = (time.time() - start_time) * 1000
            self._record_response_time(response_time)
            
            return membership
            
        except Exception as e:
            self.stats.membership_misses += 1
            self.logger.error(f"获取会员权限缓存失败: user_id={user_id}, error={e}")
            return None

    async def set_membership_permissions(
        self,
        user_id: str,
        membership: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        缓存会员权限
        
        Args:
            user_id: 用户ID
            membership: 会员权限数据
            ttl: 缓存过期时间（秒），默认使用配置的TTL
        """
        try:
            if not self.membership_cache:
                self.logger.warning("会员权限缓存未初始化")
                return
            
            # 使用默认TTL或指定的TTL
            cache_ttl = ttl if ttl is not None else self.membership_ttl
            
            self.logger.debug(
                f"💾 缓存会员权限: user_id={user_id}, ttl={cache_ttl}s"
            )
            
            # 由于IntelligentMembershipCache在get时会自动缓存，
            # 这里主要用于手动更新缓存的场景
            await self.membership_cache.invalidate_user(user_id)
            
        except Exception as e:
            self.logger.error(f"缓存会员权限失败: user_id={user_id}, error={e}")
    
    async def invalidate_user_profile(self, user_id: str):
        """
        使用户档案缓存失效
        
        Args:
            user_id: 用户ID
        """
        try:
            if self.user_cache:
                await self.user_cache.invalidate_user(user_id)
                self.logger.info(f"✅ 用户档案缓存已失效: user_id={user_id}")
        except Exception as e:
            self.logger.error(f"使用户档案缓存失效失败: user_id={user_id}, error={e}")
    
    async def invalidate_membership(self, user_id: str):
        """
        使会员权限缓存失效
        
        Args:
            user_id: 用户ID
        """
        try:
            if self.membership_cache:
                await self.membership_cache.invalidate_user(user_id)
                self.logger.info(f"✅ 会员权限缓存已失效: user_id={user_id}")
        except Exception as e:
            self.logger.error(f"使会员权限缓存失效失败: user_id={user_id}, error={e}")
    
    async def invalidate_all(self, user_id: str):
        """
        使指定用户的所有缓存失效
        
        Args:
            user_id: 用户ID
        """
        await self.invalidate_user_profile(user_id)
        await self.invalidate_membership(user_id)
        self.logger.info(f"✅ 所有缓存已失效: user_id={user_id}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取用户档案/会员权限缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计数据
        """
        # 更新统计
        self.stats.update_hit_rate()
        
        return {
            "total_requests": self.stats.total_requests,
            "total_hits": self.stats.total_hits,
            "total_misses": self.stats.total_misses,
            "hit_rate": round(self.stats.get_hit_rate() * 100, 2),
            "user_profile_requests": self.stats.user_profile_requests,
            "user_profile_hits": self.stats.user_profile_hits,
            "user_profile_misses": self.stats.user_profile_misses,
            "user_profile_hit_rate": round(self.stats.get_user_profile_hit_rate() * 100, 2),
            "membership_requests": self.stats.membership_requests,
            "membership_hits": self.stats.membership_hits,
            "membership_misses": self.stats.membership_misses,
            "membership_hit_rate": round(self.stats.get_membership_hit_rate() * 100, 2),
            "avg_response_time_ms": round(self.stats.avg_response_time_ms, 2)
        }
    
    async def shutdown(self):
        """关闭缓存管理器"""
        if self.user_cache:
            await self.user_cache.shutdown()
        
        if self.membership_cache:
            await self.membership_cache.shutdown()
        
        self.logger.info("✅ CacheManager已关闭")


# ============ 全局缓存管理器实例（单例） ============

_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    获取全局缓存管理器实例
    
    Returns:
        CacheManager实例
    """
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


# ============ 装饰器：自动缓存函数结果 ============

def cached(
    prefix: str,
    ttl: Optional[int] = None,
    key_params: Optional[List[str]] = None
):
    """
    缓存装饰器
    
    自动缓存函数结果
    
    Args:
        prefix: 缓存键前缀
        ttl: 生存时间（秒）
        key_params: 用于生成缓存键的参数名列表
    
    Example:
        @cached(prefix="muscle_training_data", ttl=86400, key_params=["muscle_id"])
        async def get_muscle_training_data(muscle_id: int):
            # 查询数据库...
            return data
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # 生成缓存键
            if key_params:
                params = {k: kwargs.get(k) for k in key_params if k in kwargs}
            else:
                params = kwargs
            
            cache_key = CacheManager.generate_cache_key(prefix, params)
            
            # 尝试从缓存获取
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            await cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# ============ 导出 ============

__all__ = [
    "CacheManager",
    "CacheEntry",
    "CacheStatistics",
    "get_cache_manager",
    "cached"
]
