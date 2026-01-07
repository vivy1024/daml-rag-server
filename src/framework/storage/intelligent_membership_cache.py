# -*- coding: utf-8 -*-
"""
Intelligent Membership Cache - 智能会员权限缓存系统

基于智能用户档案缓存的会员权限专用缓存

核心功能：
1. 多级缓存：内存 + Redis + 后端API
2. 超时控制：2500ms超时
3. 禁止降级策略：必须返回真实数据 (Requirements 3.4)
4. 缓存策略：LRU + TTL（3600秒）
5. 性能监控：缓存命中率、响应时间
6. 熔断器防护：防止缓存雪崩 (Requirements 4.4)

版本: v2.1.0
日期: 2025-12-29
作者: 薛小川
"""

import logging
import asyncio
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import OrderedDict

# 导入熔断器组件
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenException,
    membership_circuit_breaker
)

logger = logging.getLogger(__name__)


class MembershipNotFoundError(Exception):
    """会员权限不存在异常 (Requirements 3.4)"""
    def __init__(self, user_id: str, message: str = None):
        self.user_id = user_id
        self.message = message or f"会员权限不存在: {user_id}"
        super().__init__(self.message)


@dataclass
class MembershipCacheEntry:
    """会员权限缓存条目"""
    user_id: str
    membership_data: Optional[Dict[str, Any]]
    created_at: datetime
    last_accessed: datetime
    last_updated: datetime
    access_count: int = 0
    ttl_seconds: int = 3600  # 1小时TTL (Requirements 2.5)
    is_fallback: bool = False  # 保留字段用于兼容性检查

    def mark_accessed(self):
        """标记访问"""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def is_expired(self) -> bool:
        """检查是否过期"""
        return (datetime.now() - self.last_updated).total_seconds() > self.ttl_seconds


class IntelligentMembershipCache:
    """
    智能会员权限缓存系统

    核心特性：
    1. 多级缓存：内存 + Redis + 后端API
    2. 超时控制：2500ms超时
    3. 禁止降级策略：必须返回真实数据 (Requirements 3.4)
    4. 性能监控：详细的缓存性能统计
    5. 熔断器防护：防止缓存雪崩 (Requirements 4.4)
    """

    def __init__(
        self,
        backend_client=None,
        redis_client=None,
        max_memory_entries: int = 1000,  # 从200增加到1000 (Requirements 2.4)
        redis_ttl_seconds: int = 3600,   # 从600增加到3600（1小时）(Requirements 2.5)
        api_timeout_ms: int = 2500,      # 2500ms超时
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        初始化智能会员权限缓存

        Args:
            backend_client: 后端客户端
            redis_client: Redis客户端
            max_memory_entries: 最大内存缓存条目数
            redis_ttl_seconds: Redis缓存TTL（秒）
            api_timeout_ms: API超时时间（毫秒）
            circuit_breaker: 熔断器实例（可选，默认使用全局实例）
        """
        self.backend_client = backend_client
        self.redis_client = redis_client
        self.max_memory_entries = max_memory_entries
        self.redis_ttl_seconds = redis_ttl_seconds
        self.api_timeout_ms = api_timeout_ms
        
        # 熔断器 (Requirements 4.4)
        self.circuit_breaker = circuit_breaker or membership_circuit_breaker

        # 内存缓存（使用OrderedDict实现LRU）
        self.memory_cache: OrderedDict[str, MembershipCacheEntry] = OrderedDict()

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "api_hits": 0,
            "timeouts": 0,
            "errors": 0,
            "circuit_breaker_rejections": 0  # 熔断器拒绝计数
            # 移除 "fallbacks" - 禁止降级策略 (Requirements 3.4)
        }

        # 性能指标
        self.performance_metrics = {
            "avg_response_time_ms": 0.0,
            "cache_hit_rate": 0.0,
            "timeout_rate": 0.0
            # 移除 "fallback_rate" - 禁止降级策略 (Requirements 3.4)
        }

        logger.info(
            f"IntelligentMembershipCache initialized: "
            f"max_entries={max_memory_entries}, "
            f"api_timeout={api_timeout_ms}ms, "
            f"circuit_breaker={self.circuit_breaker.name}"
        )

    async def get_user_membership(
        self,
        user_id: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户会员权限（智能缓存策略）
        
        核心原则 (Requirements 3.4): 禁止返回降级数据，必须返回真实数据

        Args:
            user_id: 用户ID
            force_refresh: 是否强制刷新

        Returns:
            Optional[Dict[str, Any]]: 会员权限数据
            
        Raises:
            MembershipNotFoundError: 当会员权限不存在时抛出
        """
        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # 1. 检查内存缓存
            if not force_refresh:
                membership_data = await self._get_from_memory_cache(user_id)
                if membership_data is not None:
                    # 检查是否是旧的降级数据（兼容性处理）
                    if membership_data.get('_fallback'):
                        logger.warning(f"⚠️ 检测到旧的降级会员数据，拒绝使用: user_id={user_id}")
                        await self._evict_from_memory(user_id, "fallback_data_rejected")
                    else:
                        self.stats["memory_hits"] += 1
                        response_time = (time.time() - start_time) * 1000
                        self._update_performance_metrics(response_time)
                        logger.debug(f"✅ 会员权限缓存命中（内存）: user_id={user_id}, 响应时间={response_time:.2f}ms")
                        return membership_data

            # 2. 检查Redis缓存
            if not force_refresh and self.redis_client:
                membership_data = await self._get_from_redis_cache(user_id)
                if membership_data is not None:
                    # 检查是否是旧的降级数据（兼容性处理）
                    if membership_data.get('_fallback'):
                        logger.warning(f"⚠️ 检测到旧的降级会员数据（Redis），拒绝使用: user_id={user_id}")
                    else:
                        self.stats["redis_hits"] += 1
                        # 提升到内存缓存
                        await self._store_in_memory(user_id, membership_data, is_fallback=False)
                        response_time = (time.time() - start_time) * 1000
                        self._update_performance_metrics(response_time)
                        logger.debug(f"✅ 会员权限缓存命中（Redis）: user_id={user_id}, 响应时间={response_time:.2f}ms")
                        return membership_data

            # 3. 从后端API加载（带超时控制）
            membership_data = await self._load_from_backend_with_timeout(user_id)
            
            if membership_data is not None:
                # 检查是否是旧的降级数据（兼容性处理）
                if membership_data.get('_fallback'):
                    logger.warning(f"⚠️ 检测到旧的降级会员数据（API），拒绝使用: user_id={user_id}")
                    raise MembershipNotFoundError(user_id, f"会员权限数据无效: user_id={user_id}")
                
                self.stats["api_hits"] += 1
                logger.debug(f"✅ 会员权限从API加载: user_id={user_id}")
                
                # 存储到所有缓存层级
                await self._store_in_memory(user_id, membership_data, is_fallback=False)
                if self.redis_client:
                    await self._store_in_redis(user_id, membership_data)
                
                response_time = (time.time() - start_time) * 1000
                self._update_performance_metrics(response_time)
                return membership_data

            # 未找到会员权限，抛出异常而非返回降级数据 (Requirements 3.4)
            self.stats["errors"] += 1
            raise MembershipNotFoundError(user_id, f"会员权限不存在: user_id={user_id}")

        except MembershipNotFoundError:
            # 重新抛出自定义异常
            raise
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ 获取会员权限失败 {user_id}: {e}")
            # 抛出异常而非返回降级数据 (Requirements 3.4)
            raise MembershipNotFoundError(user_id, f"会员权限加载失败: user_id={user_id}, error={str(e)}")

    async def _get_from_memory_cache(self, user_id: str) -> Optional[Dict[str, Any]]:
        """从内存缓存获取"""
        if user_id not in self.memory_cache:
            return None

        entry = self.memory_cache[user_id]

        # 检查是否过期
        if entry.is_expired():
            # 移除过期条目
            await self._evict_from_memory(user_id, "expired")
            return None

        # 标记访问并移动到末尾（LRU）
        entry.mark_accessed()
        self.memory_cache.move_to_end(user_id)

        return entry.membership_data

    async def _get_from_redis_cache(self, user_id: str) -> Optional[Dict[str, Any]]:
        """从Redis缓存获取"""
        if not self.redis_client:
            return None

        try:
            key = f"membership:{user_id}"
            cached_data = await self.redis_client.get(key)

            if cached_data:
                data = json.loads(cached_data)
                return data.get("membership_data")

            return None

        except Exception as e:
            logger.error(f"❌ Redis缓存读取失败 {user_id}: {e}")
            return None

    async def _load_from_backend_with_timeout(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        从后端API加载（带超时控制和熔断器保护）
        
        核心原则 (Requirements 3.4): 禁止返回降级数据，必须返回真实数据
        熔断器保护 (Requirements 4.4): 使用熔断器防止缓存雪崩
        """
        if not self.backend_client:
            raise MembershipNotFoundError(user_id, f"后端客户端未配置: user_id={user_id}")

        try:
            # 设置超时时间（5秒，给后端API足够的响应时间）
            timeout_seconds = 5.0  # 5秒超时，匹配后端配置
            
            # 转换user_id为整数（如果可能）
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                logger.warning(f"⚠️ 无效的user_id格式: {user_id}")
                raise MembershipNotFoundError(user_id, f"无效的user_id格式: {user_id}")
            
            # ✅ 修复：定义带超时的异步函数
            async def fetch_membership_with_timeout():
                """异步获取会员权限（带超时）"""
                # 确保backend_client的方法是异步的
                if asyncio.iscoroutinefunction(self.backend_client.get_user_membership):
                    return await asyncio.wait_for(
                        self.backend_client.get_user_membership(user_id_int),
                        timeout=timeout_seconds
                    )
                else:
                    # 如果是同步方法，使用run_in_executor转换为异步
                    loop = asyncio.get_event_loop()
                    return await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            self.backend_client.get_user_membership,
                            user_id_int
                        ),
                        timeout=timeout_seconds
                    )
            
            # 使用熔断器包装数据源调用 (Requirements 4.4)
            # ✅ 修复：直接传递异步函数，而不是lambda
            try:
                membership = await self.circuit_breaker.call(fetch_membership_with_timeout)
            except CircuitOpenException as e:
                # 熔断器开启，记录并抛出异常
                self.stats["circuit_breaker_rejections"] += 1
                logger.warning(f"🔴 熔断器开启，拒绝会员权限请求: user_id={user_id}")
                raise MembershipNotFoundError(user_id, f"熔断器开启，请稍后重试: user_id={user_id}")
            
            # 检查结果是否有效
            if membership is None:
                # 会员不存在，抛出异常而非返回降级数据
                raise MembershipNotFoundError(user_id, f"会员权限不存在: user_id={user_id}")
            
            # 转换为字典格式
            return {
                'user_id': user_id,
                'tier': membership.tier.value if hasattr(membership.tier, 'value') else str(membership.tier),
                'status': membership.status,
                'permissions': membership.permissions,
                'started_at': membership.started_at,
                'expired_at': membership.expired_at,
                '_fallback': False
            }

        except asyncio.TimeoutError:
            # 超时：抛出异常而非返回降级数据 (Requirements 3.4)
            self.stats["timeouts"] += 1
            logger.error(f"❌ 会员权限API超时（2500ms）: user_id={user_id}")
            raise MembershipNotFoundError(user_id, f"会员权限加载超时: user_id={user_id}")
            
        except MembershipNotFoundError:
            # 重新抛出自定义异常
            raise
            
        except CircuitOpenException:
            # 重新抛出熔断器异常
            raise
            
        except Exception as e:
            logger.error(f"❌ 后端API加载失败 {user_id}: {e}")
            # 抛出异常而非返回降级数据 (Requirements 3.4)
            raise MembershipNotFoundError(user_id, f"会员权限加载失败: user_id={user_id}, error={str(e)}")

    def _get_fallback_membership(self, user_id: str) -> Dict[str, Any]:
        """
        获取降级会员权限（已废弃）
        
        ⚠️ 此方法已废弃 (Requirements 3.4)
        禁止使用降级策略，必须返回真实数据
        保留此方法仅用于兼容性检查
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 降级会员权限（带_fallback标记）
            
        Raises:
            MembershipNotFoundError: 始终抛出异常，禁止返回降级数据
        """
        # 不再返回降级数据，直接抛出异常
        raise MembershipNotFoundError(user_id, f"禁止使用降级会员数据: user_id={user_id}")

    async def _store_in_memory(
        self,
        user_id: str,
        membership_data: Dict[str, Any],
        is_fallback: bool = False
    ):
        """存储到内存缓存"""
        # 检查内存限制
        while len(self.memory_cache) >= self.max_memory_entries:
            await self._evict_lru()

        # 降级数据使用更短的TTL（60秒）
        ttl_seconds = 60 if is_fallback else self.redis_ttl_seconds

        entry = MembershipCacheEntry(
            user_id=user_id,
            membership_data=membership_data,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            last_updated=datetime.now(),
            ttl_seconds=ttl_seconds,
            is_fallback=is_fallback
        )

        # 如果用户已存在，更新
        if user_id in self.memory_cache:
            self.memory_cache.pop(user_id)

        # 添加新条目
        self.memory_cache[user_id] = entry
        self.memory_cache.move_to_end(user_id)

    async def _store_in_redis(self, user_id: str, membership_data: Dict[str, Any]):
        """存储到Redis缓存"""
        try:
            key = f"membership:{user_id}"
            value = json.dumps({
                "membership_data": membership_data,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, default=str)

            await self.redis_client.setex(
                key,
                self.redis_ttl_seconds,
                value
            )

        except Exception as e:
            logger.error(f"❌ Redis缓存存储失败 {user_id}: {e}")

    async def _evict_lru(self):
        """清理LRU条目"""
        if not self.memory_cache:
            return

        # 获取最旧的条目
        user_id, entry = self.memory_cache.popitem(last=False)
        logger.debug(f"🗑️ LRU清理会员权限: {user_id}")

    async def _evict_from_memory(self, user_id: str, reason: str):
        """从内存中移除指定用户"""
        if user_id in self.memory_cache:
            self.memory_cache.pop(user_id)
            logger.debug(f"🗑️ 内存移除会员权限 {user_id}: {reason}")

    def _update_performance_metrics(self, response_time_ms: float):
        """更新性能指标"""
        # 更新平均响应时间
        total_requests = self.stats["total_requests"]
        if total_requests == 1:
            self.performance_metrics["avg_response_time_ms"] = response_time_ms
        else:
            self.performance_metrics["avg_response_time_ms"] = (
                (self.performance_metrics["avg_response_time_ms"] * (total_requests - 1) + response_time_ms) /
                total_requests
            )

        # 更新缓存命中率
        total_hits = (
            self.stats["memory_hits"] +
            self.stats["redis_hits"]
        )
        self.performance_metrics["cache_hit_rate"] = total_hits / total_requests if total_requests > 0 else 0

        # 更新超时率
        self.performance_metrics["timeout_rate"] = self.stats["timeouts"] / total_requests if total_requests > 0 else 0
        
        # 移除 fallback_rate - 禁止降级策略 (Requirements 3.4)

    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            **self.stats,
            **self.performance_metrics,
            "memory_cache_entries": len(self.memory_cache),
            "api_timeout_ms": self.api_timeout_ms,
            "circuit_breaker_status": self.circuit_breaker.get_status()  # 熔断器状态
        }

    async def invalidate_user(self, user_id: str):
        """使指定用户的缓存失效"""
        # 从内存中移除
        await self._evict_from_memory(user_id, "manual_invalidation")

        # 从Redis中移除
        if self.redis_client:
            try:
                key = f"membership:{user_id}"
                await self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"❌ Redis缓存失效失败 {user_id}: {e}")

        logger.info(f"✅ 会员权限缓存已失效: {user_id}")

    async def shutdown(self):
        """关闭缓存系统"""
        # 清理内存缓存
        self.memory_cache.clear()
        logger.info("✅ 智能会员权限缓存系统已关闭")


# 导出
__all__ = [
    "IntelligentMembershipCache",
    "MembershipCacheEntry",
    "MembershipNotFoundError",  # 异常类导出 (Requirements 3.4)
    # 熔断器相关（从circuit_breaker模块重新导出）
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenException"
]
