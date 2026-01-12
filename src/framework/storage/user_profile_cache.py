# -*- coding: utf-8 -*-
"""
User Profile Cache - 用户档案缓存

基于UnifiedCache的用户档案专用缓存

核心功能：
1. 用户档案缓存管理
2. TTL=5分钟
3. 缓存未命中时从数据库获取
4. 档案更新时缓存失效

版本: v1.0.0
日期: 2026-01-10
作者: 薛小川
"""

import logging
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


class UserProfileCache:
    """
    用户档案缓存
    
    基于UnifiedCache实现的用户档案专用缓存
    """
    
    def __init__(self, unified_cache, db_client=None):
        """
        初始化
        
        Args:
            unified_cache: 统一缓存实例
            db_client: 数据库客户端（可选）
        """
        self.cache = unified_cache
        self.db_client = db_client
        self.ttl = 300  # 5分钟
        
        logger.info("UserProfileCache initialized with TTL=300s")

    # ============ 兼容接口（供工作流与CacheManager使用） ============

    async def get_user_profile(
        self,
        user_id: Union[str, int],
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        兼容接口：获取用户档案

        说明：
        - 旧接口使用字符串user_id；这里统一转换为int
        - force_refresh=True 时先失效缓存再重新加载
        """
        try:
            user_id_int = int(user_id)
        except Exception:
            logger.warning(f"Invalid user_id for get_user_profile: {user_id!r}")
            return None

        if force_refresh:
            await self.invalidate_profile(user_id_int)

        return await self.get_profile(user_id_int)

    async def set_user_profile(
        self,
        user_id: Union[str, int],
        profile: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """兼容接口：写入用户档案缓存"""
        try:
            user_id_int = int(user_id)
        except Exception:
            logger.warning(f"Invalid user_id for set_user_profile: {user_id!r}")
            return

        cache_key = self._get_cache_key(user_id_int)
        cache_ttl = ttl if ttl is not None else self.ttl
        await self.cache.set(cache_key, profile, cache_ttl)

    async def invalidate_user(self, user_id: Union[str, int]) -> bool:
        """兼容接口：使指定用户缓存失效"""
        try:
            user_id_int = int(user_id)
        except Exception:
            logger.warning(f"Invalid user_id for invalidate_user: {user_id!r}")
            return False

        return await self.invalidate_profile(user_id_int)

    async def shutdown(self) -> None:
        """兼容接口：关闭缓存（当前无资源需要释放）"""
        return None
    
    async def get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户档案，不存在返回None
            
        行为：
        1. 先检查缓存
        2. 缓存命中：返回缓存数据
        3. 缓存未命中：从数据库获取，更新缓存，返回数据
        """
        try:
            # 生成缓存键
            cache_key = self._get_cache_key(user_id)
            
            # 1. 先检查缓存
            cached_profile = await self.cache.get(cache_key)
            
            if cached_profile is not None:
                logger.debug(f"User profile cache hit for user_id={user_id}")
                return cached_profile
            
            # 2. 缓存未命中，从数据库获取
            logger.debug(f"User profile cache miss for user_id={user_id}, fetching from database")
            
            profile = await self._fetch_from_database(user_id)
            
            if profile is None:
                logger.warning(f"User profile not found in database for user_id={user_id}")
                return None
            
            # 3. 更新缓存
            await self.cache.set(cache_key, profile, self.ttl)
            logger.debug(f"User profile cached for user_id={user_id}")
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting user profile for user_id={user_id}: {e}")
            return None
    
    async def invalidate_profile(self, user_id: int) -> bool:
        """
        失效用户档案缓存
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
            
        使用场景：用户档案更新时调用
        """
        try:
            cache_key = self._get_cache_key(user_id)
            result = await self.cache.delete(cache_key)
            
            if result:
                logger.info(f"User profile cache invalidated for user_id={user_id}")
            else:
                logger.debug(f"User profile cache not found for user_id={user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error invalidating user profile cache for user_id={user_id}: {e}")
            return False
    
    async def invalidate_all(self) -> int:
        """
        失效所有用户档案缓存
        
        Returns:
            失效的缓存数量
        """
        try:
            pattern = "user_profile:*"
            count = await self.cache.invalidate(pattern)
            logger.info(f"Invalidated {count} user profile caches")
            return count
            
        except Exception as e:
            logger.error(f"Error invalidating all user profile caches: {e}")
            return 0
    
    # ==================== 私有方法 ====================
    
    def _get_cache_key(self, user_id: int) -> str:
        """生成缓存键"""
        return f"user_profile:{user_id}"
    
    async def _fetch_from_database(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取用户档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户档案，不存在返回None
        """
        try:
            if self.db_client is None:
                logger.warning("Database client is None, cannot fetch user profile")
                return None
            
            # 检查db_client是否有get_user_profile方法
            if not hasattr(self.db_client, 'get_user_profile'):
                logger.error("Database client does not have 'get_user_profile' method")
                return None
            
            # 从数据库获取
            profile = await self.db_client.get_user_profile(user_id)
            
            if profile is None:
                logger.debug(f"User profile not found in database for user_id={user_id}")
                return None
            
            logger.debug(f"User profile fetched from database for user_id={user_id}")
            return profile
            
        except Exception as e:
            logger.error(f"Error fetching user profile from database for user_id={user_id}: {e}")
            return None
