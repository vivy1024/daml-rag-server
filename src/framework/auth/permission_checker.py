# -*- coding: utf-8 -*-
"""
权限检查器 - DAML-RAG权限检查集成

⚠️ DEPRECATED - 将在v10.0删除
请使用 FailClosedPermissionChecker 替代。

在DAML-RAG执行查询前检查用户权限和用量配额。
实现本地缓存（5分钟TTL）以减少API调用。

核心功能：
1. 检查用户会员等级和权限
2. 检查用户每日用量配额
3. 本地缓存权限数据（5分钟TTL）
4. 查询完成后增加用量计数

Requirements: 7.1-7.6

版本: v1.1.0
日期: 2026-02-19
作者: 薛小川
"""

import logging
import time
import warnings
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# 数据类定义
# =============================================================================

class QueryMode(str, Enum):
    """查询模式"""
    DAG = "dag"
    AGENT = "agent"


@dataclass
class PermissionResult:
    """
    权限检查结果
    
    Attributes:
        allowed: 是否允许执行
        tier: 会员等级
        remaining: 剩余次数（-1表示无限制）
        message: 提示消息
        upgrade_hint: 升级提示（可选）
    """
    allowed: bool
    tier: str
    remaining: int
    message: str
    upgrade_hint: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "allowed": self.allowed,
            "tier": self.tier,
            "remaining": self.remaining,
            "message": self.message,
            "upgrade_hint": self.upgrade_hint
        }


@dataclass
class UsageInfo:
    """
    用量信息
    
    Attributes:
        can_execute: 是否可以执行
        dag_used: DAG已使用次数
        dag_limit: DAG每日限制
        dag_remaining: DAG剩余次数
        agent_used: Agent已使用次数
        agent_limit: Agent每日限制
        agent_remaining: Agent剩余次数
        dag_credits: DAG额外额度
        agent_credits: Agent额外额度
        message: 提示消息
    """
    can_execute: bool
    dag_used: int
    dag_limit: int
    dag_remaining: int
    agent_used: int
    agent_limit: int
    agent_remaining: int
    dag_credits: int = 0
    agent_credits: int = 0
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "can_execute": self.can_execute,
            "dag_used": self.dag_used,
            "dag_limit": self.dag_limit,
            "dag_remaining": self.dag_remaining,
            "agent_used": self.agent_used,
            "agent_limit": self.agent_limit,
            "agent_remaining": self.agent_remaining,
            "dag_credits": self.dag_credits,
            "agent_credits": self.agent_credits,
            "message": self.message
        }


@dataclass
class CachedPermission:
    """
    缓存的权限数据
    
    Attributes:
        tier: 会员等级
        permissions: 权限字典
        expire_time: 过期时间戳
    """
    tier: str
    permissions: Dict[str, Any]
    expire_time: float


# =============================================================================
# 权限检查器
# =============================================================================

class PermissionChecker:
    """
    权限检查器

    ⚠️ DEPRECATED - 将在v10.0删除。
    请使用 FailClosedPermissionChecker 替代。

    在DAML-RAG执行查询前检查用户权限和用量配额。
    实现本地缓存（5分钟TTL）以减少API调用。

    Requirements: 7.1-7.6
    """

    # 缓存TTL（秒）
    DEFAULT_CACHE_TTL = 300  # 5分钟

    def __init__(
        self,
        backend_client=None,
        cache_ttl: int = DEFAULT_CACHE_TTL
    ):
        warnings.warn(
            "PermissionChecker已废弃，将在v10.0删除。"
            "请使用 FailClosedPermissionChecker 替代。",
            DeprecationWarning,
            stacklevel=2,
        )
        self.backend_client = backend_client
        self.cache_ttl = cache_ttl

        # 本地缓存：{user_id: CachedPermission}
        self._permission_cache: Dict[str, CachedPermission] = {}

        logger.info(
            f"⚠️ PermissionChecker初始化(DEPRECATED): "
            f"backend_client={'已连接' if backend_client else '未连接'}, "
            f"cache_ttl={cache_ttl}秒"
        )
    
    def _get_cached_permission(self, user_id: str) -> Optional[CachedPermission]:
        """
        获取缓存的权限数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            CachedPermission: 缓存的权限数据，如果不存在或已过期返回None
        """
        cached = self._permission_cache.get(user_id)
        if cached is None:
            return None
        
        # 检查是否过期
        if time.time() > cached.expire_time:
            # 删除过期缓存
            del self._permission_cache[user_id]
            logger.debug(f"🗑️ 权限缓存已过期: user_id={user_id}")
            return None
        
        return cached
    
    def _set_cached_permission(
        self,
        user_id: str,
        tier: str,
        permissions: Dict[str, Any]
    ) -> None:
        """
        设置权限缓存
        
        Args:
            user_id: 用户ID
            tier: 会员等级
            permissions: 权限字典
        """
        expire_time = time.time() + self.cache_ttl
        self._permission_cache[user_id] = CachedPermission(
            tier=tier,
            permissions=permissions,
            expire_time=expire_time
        )
        logger.debug(
            f"💾 权限已缓存: user_id={user_id}, tier={tier}, "
            f"expire_in={self.cache_ttl}秒"
        )
    
    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """
        清除缓存
        
        Args:
            user_id: 用户ID，如果为None则清除所有缓存
        """
        if user_id:
            if user_id in self._permission_cache:
                del self._permission_cache[user_id]
                logger.info(f"🗑️ 已清除用户权限缓存: user_id={user_id}")
        else:
            self._permission_cache.clear()
            logger.info("🗑️ 已清除所有权限缓存")
    
    async def check_permission(
        self,
        user_id: int,
        mode: str = "dag"
    ) -> PermissionResult:
        """
        检查用户权限和用量
        
        Requirements: 7.1, 7.2, 7.3
        
        流程：
        1. 检查本地缓存
        2. 如果缓存未命中，调用PHP后端API获取权限
        3. 检查用量（实时，不缓存）
        4. 返回权限检查结果
        
        Args:
            user_id: 用户ID
            mode: 查询模式（dag或agent）
            
        Returns:
            PermissionResult: 权限检查结果
        """
        user_id_str = str(user_id)
        
        try:
            # 1. 检查缓存
            cached = self._get_cached_permission(user_id_str)
            
            if cached:
                tier = cached.tier
                permissions = cached.permissions
                logger.debug(f"✅ 权限缓存命中: user_id={user_id}, tier={tier}")
            else:
                # 2. 缓存未命中，从PHP后端获取权限
                if self.backend_client is None:
                    # 无后端客户端，使用默认权限（允许所有）
                    logger.warning(
                        f"⚠️ 无后端客户端，使用默认权限: user_id={user_id}"
                    )
                    return PermissionResult(
                        allowed=True,
                        tier="energy",
                        remaining=-1,
                        message="后端未连接，使用默认权限"
                    )
                
                # 调用后端API获取权限
                permissions_data = await self.backend_client.get_permissions(user_id)
                tier = permissions_data.get("tier", "free")
                permissions = permissions_data.get("permissions", {})
                
                # 缓存权限
                self._set_cached_permission(user_id_str, tier, permissions)
                logger.info(f"📡 从后端获取权限: user_id={user_id}, tier={tier}")
            
            # 3. 检查用量（实时，不缓存）
            usage = await self._check_usage(user_id, mode)

            if not usage.can_execute:
                # 积分/次数不足
                return PermissionResult(
                    allowed=False,
                    tier=tier,
                    remaining=0,
                    message=usage.message,
                    upgrade_hint="充值积分可继续使用"
                )

            # 计算剩余次数
            remaining = usage.dag_remaining if mode == "dag" else usage.agent_remaining
            
            return PermissionResult(
                allowed=True,
                tier=tier,
                remaining=remaining,
                message=f"权限检查通过，剩余{remaining}次"
            )
            
        except Exception as e:
            logger.error(f"❌ 权限检查失败: user_id={user_id}, error={e}")
            
            # 降级策略：如果后端不可用，使用缓存或拒绝访问
            # Requirements: 7.6
            cached = self._get_cached_permission(user_id_str)
            if cached:
                logger.warning(
                    f"⚠️ 后端不可用，使用缓存权限: user_id={user_id}, tier={cached.tier}"
                )
                return PermissionResult(
                    allowed=True,
                    tier=cached.tier,
                    remaining=-1,
                    message="使用缓存权限（后端暂时不可用）"
                )
            
            # 无缓存，拒绝访问
            return PermissionResult(
                allowed=False,
                tier="unknown",
                remaining=0,
                message="权限检查失败，请稍后重试"
            )
    
    async def _check_usage(self, user_id: int, mode: str) -> UsageInfo:
        """
        检查用量（实时，不缓存）
        
        Args:
            user_id: 用户ID
            mode: 查询模式
            
        Returns:
            UsageInfo: 用量信息
        """
        if self.backend_client is None:
            # 无后端客户端，返回无限制
            return UsageInfo(
                can_execute=True,
                dag_used=0,
                dag_limit=-1,
                dag_remaining=-1,
                agent_used=0,
                agent_limit=-1,
                agent_remaining=-1,
                message="后端未连接，无用量限制"
            )
        
        try:
            # 调用后端API检查用量
            usage_data = await self.backend_client.check_usage(user_id, mode)
            
            can_execute = usage_data.get("can_execute", True)
            dag_used = usage_data.get("dag_used", 0)
            dag_limit = usage_data.get("dag_limit", -1)
            dag_remaining = usage_data.get("dag_remaining", -1)
            agent_used = usage_data.get("agent_used", 0)
            agent_limit = usage_data.get("agent_limit", -1)
            agent_remaining = usage_data.get("agent_remaining", -1)
            dag_credits = usage_data.get("dag_credits", 0)
            agent_credits = usage_data.get("agent_credits", 0)
            message = usage_data.get("message", "")
            
            return UsageInfo(
                can_execute=can_execute,
                dag_used=dag_used,
                dag_limit=dag_limit,
                dag_remaining=dag_remaining,
                agent_used=agent_used,
                agent_limit=agent_limit,
                agent_remaining=agent_remaining,
                dag_credits=dag_credits,
                agent_credits=agent_credits,
                message=message
            )
            
        except Exception as e:
            logger.warning(f"⚠️ 用量检查失败，允许执行: user_id={user_id}, error={e}")
            # 用量检查失败时，允许执行（避免阻塞用户）
            return UsageInfo(
                can_execute=True,
                dag_used=0,
                dag_limit=-1,
                dag_remaining=-1,
                agent_used=0,
                agent_limit=-1,
                agent_remaining=-1,
                message="用量检查失败，暂时允许执行"
            )
    
    async def increment_usage(self, user_id: int, mode: str = "dag") -> bool:
        """
        增加用量计数
        
        Requirements: 7.4
        
        在查询完成后调用，增加用户的用量计数。
        
        Args:
            user_id: 用户ID
            mode: 查询模式（dag或agent）
            
        Returns:
            bool: 是否成功
        """
        if self.backend_client is None:
            logger.warning(f"⚠️ 无后端客户端，跳过用量增加: user_id={user_id}")
            return False
        
        try:
            await self.backend_client.increment_usage(user_id, mode)
            logger.info(f"✅ 用量已增加: user_id={user_id}, mode={mode}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 用量增加失败: user_id={user_id}, mode={mode}, error={e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计
        """
        now = time.time()
        valid_count = sum(
            1 for cached in self._permission_cache.values()
            if cached.expire_time > now
        )
        expired_count = len(self._permission_cache) - valid_count
        
        return {
            "total_cached": len(self._permission_cache),
            "valid_count": valid_count,
            "expired_count": expired_count,
            "cache_ttl": self.cache_ttl
        }


# =============================================================================
# 工厂函数
# =============================================================================

def create_permission_checker(
    backend_client=None,
    cache_ttl: int = PermissionChecker.DEFAULT_CACHE_TTL
) -> PermissionChecker:
    """
    创建权限检查器实例
    
    Args:
        backend_client: BackendClient实例
        cache_ttl: 缓存TTL（秒）
        
    Returns:
        PermissionChecker: 权限检查器实例
    """
    return PermissionChecker(
        backend_client=backend_client,
        cache_ttl=cache_ttl
    )


# 单例实例
_permission_checker_instance: Optional[PermissionChecker] = None


def get_permission_checker() -> PermissionChecker:
    """
    获取权限检查器单例
    
    Returns:
        PermissionChecker: 权限检查器实例
    """
    global _permission_checker_instance
    if _permission_checker_instance is None:
        _permission_checker_instance = create_permission_checker()
    return _permission_checker_instance


def set_permission_checker(checker: PermissionChecker) -> None:
    """
    设置权限检查器单例
    
    Args:
        checker: 权限检查器实例
    """
    global _permission_checker_instance
    _permission_checker_instance = checker


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "PermissionChecker",
    "PermissionResult",
    "UsageInfo",
    "QueryMode",
    "create_permission_checker",
    "get_permission_checker",
    "set_permission_checker",
]
