"""
MCP工具缓存管理器

提供统一的缓存机制，包括：
1. 多种缓存策略（TTL、LRU）
2. 缓存失效管理
3. 缓存统计和监控
4. 异步缓存操作

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import logging
import json
import hashlib
from collections import OrderedDict


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


class CacheManager:
    """
    缓存管理器
    
    提供统一的缓存管理功能，支持：
    1. TTL（Time To Live）过期策略
    2. LRU（Least Recently Used）淘汰策略
    3. 缓存统计和监控
    4. 批量操作
    5. 模式匹配失效
    
    Usage:
        cache = CacheManager(max_size=1000)
        
        # 设置缓存
        await cache.set("key", value, ttl=3600)
        
        # 获取缓存
        value = await cache.get("key")
        
        # 失效缓存
        await cache.invalidate("key")
        
        # 模式失效
        await cache.invalidate_pattern("entity_*")
    """
    
    # 预定义的缓存配置（通用示例，具体领域配置由应用层定义）
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
        "user_profile": {
            "ttl": 1800,  # 30分钟
            "description": "用户档案"
        }
    }
    
    def __init__(
        self,
        max_size: int = 1000,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数（LRU淘汰）
            logger: 日志记录器
        """
        self.max_size = max_size
        self.logger = logger or logging.getLogger(__name__)
        
        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # 缓存统计
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "evictions": 0
        }
        
        # 锁（用于并发控制）
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                self.logger.debug(f"🔍 缓存未命中: {key}")
                return None
            
            if entry.is_expired():
                # 过期，删除并返回None
                del self._cache[key]
                self._stats["misses"] += 1
                self.logger.debug(f"⏰ 缓存已过期: {key}")
                return None
            
            # 命中，更新访问统计并移到末尾（LRU）
            self._cache.move_to_end(key)
            value = entry.access()
            self._stats["hits"] += 1
            self.logger.debug(
                f"✅ 缓存命中: {key} "
                f"(访问次数: {entry.access_count})"
            )
            return value
    
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
        获取缓存统计信息
        
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


# 全局缓存管理器实例（单例）
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


# 装饰器：自动缓存函数结果

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
