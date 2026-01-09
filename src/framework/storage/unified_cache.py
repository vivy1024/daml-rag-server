# -*- coding: utf-8 -*-
"""
Unified Cache System - 统一缓存系统

提供统一的缓存接口，支持Redis后端存储

核心功能：
1. 统一缓存接口：get, set, delete, invalidate
2. Redis后端存储
3. TTL管理
4. 缓存统计
5. 错误处理和降级

版本: v1.0.0
日期: 2026-01-10
作者: 薛小川
"""

import logging
import json
import time
from typing import Any, Optional, Dict
from dataclasses import dataclass, field, asdict
from datetime import datetime
import pickle

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """缓存配置"""
    default_ttl: int = 300  # 默认TTL（秒）- 5分钟
    max_memory: int = 1024 * 1024  # 最大内存（字节）- 1MB
    eviction_policy: str = "lru"  # 淘汰策略
    enable_statistics: bool = True  # 启用统计


@dataclass
class CacheStatistics:
    """缓存统计信息"""
    total_requests: int = 0  # 总请求数
    cache_hits: int = 0  # 缓存命中数
    cache_misses: int = 0  # 缓存未命中数
    hit_rate: float = 0.0  # 命中率
    avg_response_time: float = 0.0  # 平均响应时间（毫秒）
    memory_usage: int = 0  # 内存使用（字节）
    
    def update_hit_rate(self):
        """更新命中率"""
        if self.total_requests > 0:
            self.hit_rate = self.cache_hits / self.total_requests
        else:
            self.hit_rate = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class UnifiedCache:
    """
    统一缓存系统
    
    提供统一的缓存接口，支持Redis后端存储
    """
    
    def __init__(self, redis_client, config: Optional[CacheConfig] = None):
        """
        初始化缓存
        
        Args:
            redis_client: Redis客户端
            config: 缓存配置
        """
        self.redis = redis_client
        self.config = config or CacheConfig()
        self.statistics = CacheStatistics()
        self._response_times = []  # 用于计算平均响应时间
        
        logger.info(f"UnifiedCache initialized with config: {self.config}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在返回None
        """
        start_time = time.time()
        
        try:
            # 更新统计
            self.statistics.total_requests += 1
            
            # 从Redis获取
            if self.redis is None:
                logger.warning("Redis client is None, cache disabled")
                self.statistics.cache_misses += 1
                self.statistics.update_hit_rate()
                return None
            
            value = await self._get_from_redis(key)
            
            # 更新统计
            if value is not None:
                self.statistics.cache_hits += 1
                logger.debug(f"Cache hit for key: {key}")
            else:
                self.statistics.cache_misses += 1
                logger.debug(f"Cache miss for key: {key}")
            
            self.statistics.update_hit_rate()
            
            # 记录响应时间
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            self._update_response_time(response_time)
            
            return value
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            self.statistics.cache_misses += 1
            self.statistics.update_hit_rate()
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认使用配置的default_ttl
            
        Returns:
            是否成功
        """
        try:
            if self.redis is None:
                logger.warning("Redis client is None, cache disabled")
                return False
            
            # 使用配置的TTL或传入的TTL
            cache_ttl = ttl if ttl is not None else self.config.default_ttl
            
            # 存储到Redis
            success = await self._set_to_redis(key, value, cache_ttl)
            
            if success:
                logger.debug(f"Cache set for key: {key}, ttl: {cache_ttl}s")
            else:
                logger.warning(f"Failed to set cache for key: {key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        try:
            if self.redis is None:
                logger.warning("Redis client is None, cache disabled")
                return False
            
            # 从Redis删除
            result = await self._delete_from_redis(key)
            
            if result:
                logger.debug(f"Cache deleted for key: {key}")
            else:
                logger.debug(f"Cache key not found: {key}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def invalidate(self, pattern: str) -> int:
        """
        批量失效缓存
        
        Args:
            pattern: 键模式（支持通配符，如 "user:*"）
            
        Returns:
            失效的键数量
        """
        try:
            if self.redis is None:
                logger.warning("Redis client is None, cache disabled")
                return 0
            
            # 查找匹配的键
            keys = await self._scan_keys(pattern)
            
            if not keys:
                logger.debug(f"No keys found for pattern: {pattern}")
                return 0
            
            # 批量删除
            deleted_count = 0
            for key in keys:
                if await self._delete_from_redis(key):
                    deleted_count += 1
            
            logger.info(f"Invalidated {deleted_count} keys for pattern: {pattern}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0
    
    def get_statistics(self) -> CacheStatistics:
        """获取缓存统计信息"""
        return self.statistics
    
    # ==================== 私有方法 ====================
    
    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """从Redis获取值"""
        try:
            # 检查Redis是否可用
            if not hasattr(self.redis, 'get'):
                logger.error("Redis client does not have 'get' method")
                return None
            
            # 获取原始值
            raw_value = await self.redis.get(key)
            
            if raw_value is None:
                return None
            
            # 尝试反序列化
            try:
                # 先尝试JSON
                return json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                # 如果JSON失败，尝试pickle
                try:
                    return pickle.loads(raw_value)
                except Exception:
                    # 如果都失败，返回原始字符串
                    return raw_value.decode('utf-8') if isinstance(raw_value, bytes) else raw_value
                    
        except Exception as e:
            logger.error(f"Error getting from Redis: {e}")
            return None
    
    async def _set_to_redis(self, key: str, value: Any, ttl: int) -> bool:
        """存储到Redis"""
        try:
            # 检查Redis是否可用
            if not hasattr(self.redis, 'setex'):
                logger.error("Redis client does not have 'setex' method")
                return False
            
            # 序列化值
            try:
                # 先尝试JSON序列化
                serialized_value = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                # 如果JSON失败，使用pickle
                try:
                    serialized_value = pickle.dumps(value)
                except Exception as e:
                    logger.error(f"Failed to serialize value: {e}")
                    return False
            
            # 存储到Redis（使用setex设置TTL）
            await self.redis.setex(key, ttl, serialized_value)
            return True
            
        except Exception as e:
            logger.error(f"Error setting to Redis: {e}")
            return False
    
    async def _delete_from_redis(self, key: str) -> bool:
        """从Redis删除"""
        try:
            # 检查Redis是否可用
            if not hasattr(self.redis, 'delete'):
                logger.error("Redis client does not have 'delete' method")
                return False
            
            result = await self.redis.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Error deleting from Redis: {e}")
            return False
    
    async def _scan_keys(self, pattern: str) -> list:
        """扫描匹配的键"""
        try:
            # 检查Redis是否可用
            if not hasattr(self.redis, 'scan'):
                logger.error("Redis client does not have 'scan' method")
                return []
            
            keys = []
            cursor = 0
            
            # 使用SCAN命令遍历键（避免阻塞）
            while True:
                cursor, partial_keys = await self.redis.scan(cursor, match=pattern, count=100)
                keys.extend(partial_keys)
                
                if cursor == 0:
                    break
            
            return keys
            
        except Exception as e:
            logger.error(f"Error scanning keys: {e}")
            return []
    
    def _update_response_time(self, response_time: float):
        """更新平均响应时间"""
        self._response_times.append(response_time)
        
        # 只保留最近100次的响应时间
        if len(self._response_times) > 100:
            self._response_times.pop(0)
        
        # 计算平均值
        if self._response_times:
            self.statistics.avg_response_time = sum(self._response_times) / len(self._response_times)
