# -*- coding: utf-8 -*-
"""
Membership Cache - 会员缓存

基于UnifiedCache的会员信息专用缓存

核心功能：
1. 会员信息缓存管理
2. TTL=10分钟
3. 缓存未命中时从后端获取
4. 会员变更时缓存失效

版本: v1.0.0
日期: 2026-01-10
作者: 薛小川
"""

import logging
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


class MembershipCache:
    """
    会员缓存
    
    基于UnifiedCache实现的会员信息专用缓存
    """
    
    def __init__(self, unified_cache, backend_client=None):
        """
        初始化
        
        Args:
            unified_cache: 统一缓存实例
            backend_client: 后端客户端（可选）
        """
        self.cache = unified_cache
        self.backend_client = backend_client
        self.ttl = 600  # 10分钟
        
        logger.info("MembershipCache initialized with TTL=600s")
    
    async def get_membership(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取会员信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            会员信息，不存在返回None
            
        行为：
        1. 先检查缓存
        2. 缓存命中：返回缓存数据
        3. 缓存未命中：从后端获取，更新缓存，返回数据
        """
        try:
            # 生成缓存键
            cache_key = self._get_cache_key(user_id)
            
            # 1. 先检查缓存
            cached_membership = await self.cache.get(cache_key)
            
            if cached_membership is not None:
                logger.debug(f"Membership cache hit for user_id={user_id}")
                return cached_membership
            
            # 2. 缓存未命中，从后端获取
            logger.debug(f"Membership cache miss for user_id={user_id}, fetching from backend")
            
            membership = await self._fetch_from_backend(user_id)
            
            if membership is None:
                logger.warning(f"Membership not found in backend for user_id={user_id}")
                return None
            
            # 3. 更新缓存
            await self.cache.set(cache_key, membership, self.ttl)
            logger.debug(f"Membership cached for user_id={user_id}")
            
            return membership
            
        except Exception as e:
            logger.error(f"Error getting membership for user_id={user_id}: {e}")
            return None
    
    async def invalidate_membership(self, user_id: int) -> bool:
        """
        失效会员缓存
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
            
        使用场景：会员状态变更时调用
        """
        try:
            cache_key = self._get_cache_key(user_id)
            result = await self.cache.delete(cache_key)
            
            if result:
                logger.info(f"Membership cache invalidated for user_id={user_id}")
            else:
                logger.debug(f"Membership cache not found for user_id={user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error invalidating membership cache for user_id={user_id}: {e}")
            return False
    
    async def invalidate_all(self) -> int:
        """
        失效所有会员缓存
        
        Returns:
            失效的缓存数量
        """
        try:
            pattern = "membership:*"
            count = await self.cache.invalidate(pattern)
            logger.info(f"Invalidated {count} membership caches")
            return count
            
        except Exception as e:
            logger.error(f"Error invalidating all membership caches: {e}")
            return 0
    
    # ==================== 私有方法 ====================
    
    def _get_cache_key(self, user_id: int) -> str:
        """生成缓存键"""
        return f"membership:{user_id}"
    
    async def _fetch_from_backend(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        从后端获取会员信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            会员信息，不存在返回None
        """
        try:
            if self.backend_client is None:
                logger.warning("Backend client is None, cannot fetch membership")
                return None
            
            # 兼容不同后端客户端方法名
            if hasattr(self.backend_client, "get_user_membership"):
                membership = await self.backend_client.get_user_membership(user_id)
            elif hasattr(self.backend_client, "get_membership"):
                membership = await self.backend_client.get_membership(user_id)
            else:
                logger.error("Backend client does not have membership fetch method")
                return None
            
            if membership is None:
                logger.debug(f"Membership not found in backend for user_id={user_id}")
                return None
            
            logger.debug(f"Membership fetched from backend for user_id={user_id}")
            return membership
            
        except Exception as e:
            logger.error(f"Error fetching membership from backend for user_id={user_id}: {e}")
            return None

    # ============ 兼容接口（供工作流与CacheManager使用） ============

    async def get_user_membership(
        self,
        user_id: Union[str, int],
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """兼容接口：获取会员信息（旧接口名）"""
        try:
            user_id_int = int(user_id)
        except Exception:
            logger.warning(f"Invalid user_id for get_user_membership: {user_id!r}")
            return None

        if force_refresh:
            await self.invalidate_membership(user_id_int)

        return await self.get_membership(user_id_int)

    async def get_membership_permissions(
        self,
        user_id: Union[str, int],
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """兼容接口：供CacheManager使用的会员权限获取方法"""
        return await self.get_user_membership(user_id, force_refresh=force_refresh)

    async def set_membership_permissions(
        self,
        user_id: Union[str, int],
        membership: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """兼容接口：写入会员权限缓存"""
        try:
            user_id_int = int(user_id)
        except Exception:
            logger.warning(f"Invalid user_id for set_membership_permissions: {user_id!r}")
            return

        cache_key = self._get_cache_key(user_id_int)
        cache_ttl = ttl if ttl is not None else self.ttl
        await self.cache.set(cache_key, membership, cache_ttl)

    async def invalidate_user(self, user_id: Union[str, int]) -> bool:
        """兼容接口：使指定用户的会员缓存失效"""
        try:
            user_id_int = int(user_id)
        except Exception:
            logger.warning(f"Invalid user_id for invalidate_user: {user_id!r}")
            return False

        return await self.invalidate_membership(user_id_int)

    async def shutdown(self) -> None:
        """兼容接口：关闭缓存（当前无资源需要释放）"""
        return None
