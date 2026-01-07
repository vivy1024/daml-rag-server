# -*- coding: utf-8 -*-
"""
CacheManager - 缓存管理器

统一的缓存管理接口，用于DAG编排器中的用户档案和会员权限缓存

核心功能：
1. 用户档案缓存：TTL 5分钟（300秒）
2. 会员权限缓存：TTL 10分钟（600秒）
3. 缓存命中率统计
4. 详细的缓存日志记录
5. 自动降级策略

版本: v1.0.0
日期: 2025-12-22
作者: 薛小川
"""

import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheStatistics:
    """缓存统计信息"""
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


class CacheManager:
    """
    缓存管理器
    
    统一管理用户档案和会员权限的缓存，提供简单的接口给DAG编排器使用
    
    特性：
    - 用户档案缓存：TTL 5分钟
    - 会员权限缓存：TTL 10分钟
    - 缓存命中率统计
    - 详细的日志记录
    - 自动降级策略
    """
    
    def __init__(
        self,
        user_cache=None,
        membership_cache=None,
        user_profile_ttl: int = 300,  # 5分钟
        membership_ttl: int = 600  # 10分钟
    ):
        """
        初始化缓存管理器
        
        Args:
            user_cache: 用户档案缓存实例（IntelligentUserCache）
            membership_cache: 会员权限缓存实例（IntelligentMembershipCache）
            user_profile_ttl: 用户档案缓存TTL（秒）
            membership_ttl: 会员权限缓存TTL（秒）
        """
        self.user_cache = user_cache
        self.membership_cache = membership_cache
        self.user_profile_ttl = user_profile_ttl
        self.membership_ttl = membership_ttl
        
        # 统计信息
        self.stats = CacheStatistics()
        
        # 响应时间记录（用于计算平均值）
        self.response_times = []
        
        logger.info(
            f"CacheManager initialized: "
            f"user_profile_ttl={user_profile_ttl}s, "
            f"membership_ttl={membership_ttl}s"
        )
    
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
                logger.warning("用户档案缓存未初始化")
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
                    logger.warning(
                        f"📦 用户档案缓存命中（降级数据）: user_id={user_id}"
                    )
                else:
                    logger.debug(
                        f"✅ 用户档案缓存命中: user_id={user_id}"
                    )
            else:
                self.stats.user_profile_misses += 1
                logger.debug(
                    f"❌ 用户档案缓存未命中: user_id={user_id}"
                )
            
            # 记录响应时间
            response_time = (time.time() - start_time) * 1000
            self._record_response_time(response_time)
            
            return profile
            
        except Exception as e:
            self.stats.user_profile_misses += 1
            logger.error(f"获取用户档案缓存失败: user_id={user_id}, error={e}")
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
                logger.warning("用户档案缓存未初始化")
                return
            
            # 使用默认TTL或指定的TTL
            cache_ttl = ttl if ttl is not None else self.user_profile_ttl
            
            # 存储到缓存（使用底层缓存的存储方法）
            # 注意：IntelligentUserCache会自动管理缓存存储
            # 这里我们只需要确保数据被正确传递
            logger.debug(
                f"💾 缓存用户档案: user_id={user_id}, ttl={cache_ttl}s"
            )
            
            # 由于IntelligentUserCache在get时会自动缓存，
            # 这里主要用于手动更新缓存的场景
            # 我们可以通过invalidate + get的方式来强制更新
            await self.user_cache.invalidate_user(user_id)
            
        except Exception as e:
            logger.error(f"缓存用户档案失败: user_id={user_id}, error={e}")
    
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
                logger.warning("会员权限缓存未初始化")
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
                    logger.warning(
                        f"📦 会员权限缓存命中（降级数据）: user_id={user_id}"
                    )
                else:
                    logger.debug(
                        f"✅ 会员权限缓存命中: user_id={user_id}"
                    )
            else:
                self.stats.membership_misses += 1
                logger.debug(
                    f"❌ 会员权限缓存未命中: user_id={user_id}"
                )
            
            # 记录响应时间
            response_time = (time.time() - start_time) * 1000
            self._record_response_time(response_time)
            
            return membership
            
        except Exception as e:
            self.stats.membership_misses += 1
            logger.error(f"获取会员权限缓存失败: user_id={user_id}, error={e}")
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
                logger.warning("会员权限缓存未初始化")
                return
            
            # 使用默认TTL或指定的TTL
            cache_ttl = ttl if ttl is not None else self.membership_ttl
            
            logger.debug(
                f"💾 缓存会员权限: user_id={user_id}, ttl={cache_ttl}s"
            )
            
            # 由于IntelligentMembershipCache在get时会自动缓存，
            # 这里主要用于手动更新缓存的场景
            # 我们可以通过invalidate + get的方式来强制更新
            await self.membership_cache.invalidate_user(user_id)
            
        except Exception as e:
            logger.error(f"缓存会员权限失败: user_id={user_id}, error={e}")
    
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计数据
                - total_requests: 总请求数
                - total_hits: 总命中数
                - total_misses: 总未命中数
                - hit_rate: 总体命中率（百分比）
                - user_profile_requests: 用户档案请求数
                - user_profile_hits: 用户档案命中数
                - user_profile_hit_rate: 用户档案命中率（百分比）
                - membership_requests: 会员权限请求数
                - membership_hits: 会员权限命中数
                - membership_hit_rate: 会员权限命中率（百分比）
                - avg_response_time_ms: 平均响应时间（毫秒）
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
    
    async def invalidate_user_profile(self, user_id: str):
        """
        使用户档案缓存失效
        
        Args:
            user_id: 用户ID
        """
        try:
            if self.user_cache:
                await self.user_cache.invalidate_user(user_id)
                logger.info(f"✅ 用户档案缓存已失效: user_id={user_id}")
        except Exception as e:
            logger.error(f"使用户档案缓存失效失败: user_id={user_id}, error={e}")
    
    async def invalidate_membership(self, user_id: str):
        """
        使会员权限缓存失效
        
        Args:
            user_id: 用户ID
        """
        try:
            if self.membership_cache:
                await self.membership_cache.invalidate_user(user_id)
                logger.info(f"✅ 会员权限缓存已失效: user_id={user_id}")
        except Exception as e:
            logger.error(f"使会员权限缓存失效失败: user_id={user_id}, error={e}")
    
    async def invalidate_all(self, user_id: str):
        """
        使指定用户的所有缓存失效
        
        Args:
            user_id: 用户ID
        """
        await self.invalidate_user_profile(user_id)
        await self.invalidate_membership(user_id)
        logger.info(f"✅ 所有缓存已失效: user_id={user_id}")
    
    async def shutdown(self):
        """关闭缓存管理器"""
        if self.user_cache:
            await self.user_cache.shutdown()
        
        if self.membership_cache:
            await self.membership_cache.shutdown()
        
        logger.info("✅ CacheManager已关闭")


# 导出
__all__ = [
    "CacheManager",
    "CacheStatistics"
]
