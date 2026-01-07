# -*- coding: utf-8 -*-
"""
并发限制器模块

功能：
- 限制流式连接的最大并发数
- 提供连接计数和管理
- 支持排队等待机制
- 支持用户分级限流策略
- 支持429错误响应

版本：v2.0.0
创建日期：2025-12-18
更新日期：2025-12-21
"""

import logging
import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class UserTier(Enum):
    """用户等级"""
    FREE = "free"
    PAID = "paid"
    VIP = "vip"
    SYSTEM = "system"


@dataclass
class TierConfig:
    """等级配置"""
    max_concurrent: int
    max_queue_size: int
    timeout: int


@dataclass
class ConnectionInfo:
    """连接信息"""
    user_id: str
    session_id: str
    user_tier: UserTier
    start_time: float


class ConcurrencyLimiter:
    """并发限制器"""
    
    # 默认等级配置
    DEFAULT_TIER_CONFIGS = {
        UserTier.FREE: TierConfig(max_concurrent=10, max_queue_size=20, timeout=30),
        UserTier.PAID: TierConfig(max_concurrent=50, max_queue_size=100, timeout=60),
        UserTier.VIP: TierConfig(max_concurrent=100, max_queue_size=200, timeout=120),
        UserTier.SYSTEM: TierConfig(max_concurrent=999999, max_queue_size=999999, timeout=999999),
    }
    
    def __init__(
        self,
        max_concurrent: int = 100,
        max_queue_size: int = 200,
        timeout: int = 30,
        tier_configs: Optional[Dict[UserTier, TierConfig]] = None
    ):
        """
        初始化并发限制器
        
        Args:
            max_concurrent: 全局最大并发连接数
            max_queue_size: 全局最大队列大小
            timeout: 全局默认超时时间（秒）
            tier_configs: 用户等级配置字典
        """
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.default_timeout = timeout
        self.tier_configs = tier_configs or self.DEFAULT_TIER_CONFIGS
        
        self._active_connections: Dict[str, ConnectionInfo] = {}
        self._user_connections: Dict[str, set] = {}  # user_id -> set of session_ids
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 统计信息
        self._total_connections = 0
        self._rejected_connections = 0
        self._queued_connections = 0
        self._tier_stats: Dict[UserTier, Dict[str, int]] = {
            tier: {"total": 0, "rejected": 0, "queued": 0}
            for tier in UserTier
        }
    
    def _get_user_tier(self, user_id: str) -> UserTier:
        """
        获取用户等级
        
        Args:
            user_id: 用户ID
        
        Returns:
            UserTier: 用户等级
        """
        # TODO: 从数据库或缓存中获取用户等级
        # 目前默认返回免费用户
        if user_id.startswith("system_"):
            return UserTier.SYSTEM
        return UserTier.FREE
    
    def _check_user_limit(self, user_id: str, user_tier: UserTier) -> bool:
        """
        检查用户是否超过其等级限制
        
        Args:
            user_id: 用户ID
            user_tier: 用户等级
        
        Returns:
            bool: 是否在限制内
        """
        tier_config = self.tier_configs[user_tier]
        user_sessions = self._user_connections.get(user_id, set())
        return len(user_sessions) < tier_config.max_concurrent
    
    async def acquire(
        self,
        user_id: str,
        session_id: str,
        timeout: Optional[float] = None,
        user_tier: Optional[UserTier] = None
    ) -> bool:
        """
        获取连接许可
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            timeout: 超时时间（秒），None表示使用默认超时
            user_tier: 用户等级，None表示自动检测
        
        Returns:
            bool: 是否成功获取许可
        """
        # 确定用户等级
        if user_tier is None:
            user_tier = self._get_user_tier(user_id)
        
        tier_config = self.tier_configs[user_tier]
        actual_timeout = timeout if timeout is not None else tier_config.timeout
        
        # 更新统计
        self._total_connections += 1
        self._tier_stats[user_tier]["total"] += 1
        
        # 检查用户等级限制（在获取锁之前）
        async with self._lock:
            if not self._check_user_limit(user_id, user_tier):
                self._rejected_connections += 1
                self._tier_stats[user_tier]["rejected"] += 1
                logger.warning(
                    f"⚠️ 并发限制：用户等级限制已满，拒绝连接 "
                    f"(用户并发: {len(self._user_connections.get(user_id, set()))}/{tier_config.max_concurrent}), "
                    f"user={user_id}, tier={user_tier.value}, session={session_id[:8]}..."
                )
                return False
            
            # 检查队列大小
            current_count = len(self._active_connections)
            if current_count >= self.max_concurrent and self._queued_connections >= self.max_queue_size:
                self._rejected_connections += 1
                self._tier_stats[user_tier]["rejected"] += 1
                logger.warning(
                    f"⚠️ 并发限制：队列已满，拒绝连接 "
                    f"(队列: {self._queued_connections}/{self.max_queue_size}), "
                    f"user={user_id}, tier={user_tier.value}, session={session_id[:8]}..."
                )
                return False
            
            # 如果当前连接数接近限制，进入队列
            if current_count >= self.max_concurrent * 0.8:
                self._queued_connections += 1
                self._tier_stats[user_tier]["queued"] += 1
                logger.info(
                    f"⏳ 并发限制：连接排队等待 "
                    f"(当前: {current_count}/{self.max_concurrent}), "
                    f"user={user_id}, tier={user_tier.value}, session={session_id[:8]}..."
                )
        
        # 尝试获取信号量（带超时）
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=actual_timeout
            )
            
            # 记录连接
            async with self._lock:
                self._active_connections[session_id] = ConnectionInfo(
                    user_id=user_id,
                    session_id=session_id,
                    user_tier=user_tier,
                    start_time=time.time()
                )
                
                # 更新用户连接集合
                if user_id not in self._user_connections:
                    self._user_connections[user_id] = set()
                self._user_connections[user_id].add(session_id)
                
                if self._queued_connections > 0:
                    self._queued_connections -= 1
                    if self._tier_stats[user_tier]["queued"] > 0:
                        self._tier_stats[user_tier]["queued"] -= 1
                
                logger.info(
                    f"✅ 并发限制：连接已建立 "
                    f"(当前: {len(self._active_connections)}/{self.max_concurrent}), "
                    f"user={user_id}, tier={user_tier.value}, session={session_id[:8]}..."
                )
            
            return True
            
        except asyncio.TimeoutError:
            # 等待超时
            self._rejected_connections += 1
            self._tier_stats[user_tier]["rejected"] += 1
            async with self._lock:
                if self._queued_connections > 0:
                    self._queued_connections -= 1
                if self._tier_stats[user_tier]["queued"] > 0:
                    self._tier_stats[user_tier]["queued"] -= 1
            
            logger.warning(
                f"⏱️ 并发限制：等待超时 "
                f"(超时: {actual_timeout}秒), "
                f"user={user_id}, tier={user_tier.value}, session={session_id[:8]}..."
            )
            return False
    
    async def release(self, session_id: str):
        """
        释放连接许可
        
        Args:
            session_id: 会话ID
        """
        async with self._lock:
            if session_id in self._active_connections:
                conn_info = self._active_connections.pop(session_id)
                duration = time.time() - conn_info.start_time
                
                # 更新用户连接集合
                if conn_info.user_id in self._user_connections:
                    self._user_connections[conn_info.user_id].discard(session_id)
                    if not self._user_connections[conn_info.user_id]:
                        del self._user_connections[conn_info.user_id]
                
                logger.info(
                    f"🔓 并发限制：连接已释放 "
                    f"(当前: {len(self._active_connections)}/{self.max_concurrent}), "
                    f"user={conn_info.user_id}, "
                    f"tier={conn_info.user_tier.value}, "
                    f"session={session_id[:8]}..., "
                    f"持续时间={duration:.1f}秒"
                )
        
        # 释放信号量
        self._semaphore.release()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息字典
        """
        return {
            "max_concurrent": self.max_concurrent,
            "max_queue_size": self.max_queue_size,
            "active_connections": len(self._active_connections),
            "queued_connections": self._queued_connections,
            "total_connections": self._total_connections,
            "rejected_connections": self._rejected_connections,
            "rejection_rate": (
                self._rejected_connections / self._total_connections 
                if self._total_connections > 0 else 0.0
            ),
            "tier_stats": {
                tier.value: {
                    "total": stats["total"],
                    "rejected": stats["rejected"],
                    "queued": stats["queued"],
                    "rejection_rate": (
                        stats["rejected"] / stats["total"]
                        if stats["total"] > 0 else 0.0
                    )
                }
                for tier, stats in self._tier_stats.items()
            }
        }
    
    def get_statistics(self) -> dict:
        """获取统计信息（向后兼容）"""
        return self.get_stats()
    
    def get_active_connections(self) -> list[dict]:
        """获取活跃连接列表"""
        now = time.time()
        return [
            {
                "user_id": conn.user_id,
                "session_id": conn.session_id,
                "user_tier": conn.user_tier.value,
                "duration_seconds": now - conn.start_time
            }
            for conn in self._active_connections.values()
        ]
    
    def get_user_connections(self, user_id: str) -> list[dict]:
        """
        获取指定用户的活跃连接
        
        Args:
            user_id: 用户ID
        
        Returns:
            list: 用户的活跃连接列表
        """
        now = time.time()
        session_ids = self._user_connections.get(user_id, set())
        return [
            {
                "session_id": session_id,
                "user_tier": self._active_connections[session_id].user_tier.value,
                "duration_seconds": now - self._active_connections[session_id].start_time
            }
            for session_id in session_ids
            if session_id in self._active_connections
        ]
    
    def should_reject_with_429(self) -> bool:
        """
        判断是否应该返回429错误
        
        Returns:
            bool: 是否应该返回429
        """
        current_count = len(self._active_connections)
        return current_count >= self.max_concurrent or self._queued_connections >= self.max_queue_size


# 全局并发限制器实例
# 默认限制100个并发连接
concurrency_limiter = ConcurrencyLimiter(
    max_concurrent=100,
    max_queue_size=200,
    timeout=30
)
