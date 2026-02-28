# -*- coding: utf-8 -*-
"""CreditMixin — 会员权限 + 用量统计 API"""

import httpx
import logging
from typing import Dict, Any, Optional

from .models import (
    BackendAPIError,
    MembershipFeature,
    MembershipTier,
    MembershipPermissions,
)

logger = logging.getLogger(__name__)


class CreditMixin:
    """会员权限与用量统计 API 方法集"""

    async def check_permission(self, user_id: int, feature: MembershipFeature) -> bool:
        """检查用户是否有指定功能的权限"""
        endpoint = "/api/internal/membership/check-permission"

        timeout = self.config.membership_timeout_ms / 1000.0
        original_timeout = self.config.timeout
        self.config.timeout = timeout

        try:
            data = await self._request(
                "POST", endpoint,
                json={'user_id': user_id, 'feature': feature.value}
            )
            return data.get('has_permission', False)
        finally:
            self.config.timeout = original_timeout

    async def get_user_permissions(
        self, user_id: int, feature: Optional[MembershipFeature] = None
    ) -> Dict[str, Any]:
        """获取用户的完整权限信息"""
        endpoint = "/api/internal/membership/check-permission"

        request_data = {'user_id': user_id}
        if feature:
            request_data['feature'] = feature.value
        else:
            request_data['feature'] = MembershipFeature.AI_RECOMMENDATION.value

        timeout = self.config.membership_timeout_ms / 1000.0
        original_timeout = self.config.timeout
        self.config.timeout = timeout

        try:
            data = await self._request("POST", endpoint, json=request_data)
            return data
        finally:
            self.config.timeout = original_timeout

    async def get_user_membership(self, user_id: int) -> MembershipPermissions:
        """获取用户完整会员信息"""
        endpoint = f"/api/internal/membership/user/{user_id}"

        timeout = self.config.membership_timeout_ms / 1000.0
        original_timeout = self.config.timeout
        self.config.timeout = timeout

        try:
            data = await self._request("GET", endpoint)
            return MembershipPermissions(
                user_id=user_id,
                tier=MembershipTier(data.get('tier', 'free')),
                status=data.get('status', 'active'),
                permissions=data.get('permissions', {}),
                started_at=data.get('started_at'),
                expired_at=data.get('expired_at'),
            )
        finally:
            self.config.timeout = original_timeout

    async def get_membership_permissions_cached(self, user_id: int) -> Dict[str, Any]:
        """获取用户会员权限（集成缓存）"""
        user_id_str = str(user_id)

        if self.cache_manager:
            try:
                cached_membership = await self.cache_manager.get_membership_permissions(user_id_str)
                if cached_membership is not None:
                    is_fallback = cached_membership.get('_fallback', False)
                    if is_fallback:
                        logger.info(
                            f"✅ 会员权限缓存命中（降级数据）: user_id={user_id}",
                            extra={'user_id': user_id, 'cache_hit': True, 'is_fallback': True}
                        )
                    else:
                        logger.info(
                            f"✅ 会员权限缓存命中: user_id={user_id}",
                            extra={'user_id': user_id, 'cache_hit': True}
                        )
                    return cached_membership
                else:
                    logger.debug(
                        f"❌ 会员权限缓存未命中: user_id={user_id}",
                        extra={'user_id': user_id, 'cache_hit': False}
                    )
            except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                logger.warning(f"缓存查询失败，将从API获取: {e}")

        try:
            membership = await self.get_user_membership(user_id)
            membership_dict = membership.to_dict()

            if self.cache_manager and membership_dict:
                try:
                    await self.cache_manager.set_membership_permissions(user_id_str, membership_dict)
                    logger.debug(f"💾 会员权限已缓存: user_id={user_id}", extra={'user_id': user_id})
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                    logger.warning(f"缓存写入失败: {e}")

            return membership_dict

        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"会员权限加载失败，使用降级策略: user_id={user_id}, error={str(e)}")
            fallback_membership = self._get_fallback_membership(user_id)

            if self.cache_manager:
                try:
                    await self.cache_manager.set_membership_permissions(user_id_str, fallback_membership)
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                    logger.warning(f"降级权限缓存失败: {e}")

            return fallback_membership

    def _get_fallback_membership(self, user_id: int) -> Dict[str, Any]:
        """获取降级会员权限"""
        return {
            'user_id': user_id,
            'tier': 'free',
            'status': 'active',
            'permissions': {
                'ai_recommendation': False,
                'data_analysis': False,
                'coach_service': False
            },
            'started_at': None,
            'expired_at': None,
            '_fallback': True
        }

    async def get_permissions(self, user_id: int) -> Dict[str, Any]:
        """获取用户权限信息（用于PermissionChecker）"""
        endpoint = f"/api/internal/membership/user/{user_id}"

        timeout = self.config.membership_timeout_ms / 1000.0
        original_timeout = self.config.timeout
        self.config.timeout = timeout

        try:
            data = await self._request("GET", endpoint)
            result = {
                'user_id': user_id,
                'tier': data.get('tier', 'free'),
                'status': data.get('status', 'active'),
                'permissions': data.get('permissions', {}),
                'started_at': data.get('started_at'),
                'expired_at': data.get('expired_at'),
            }
            logger.info(
                f"✅ 获取用户权限成功: user_id={user_id}, tier={result['tier']}",
                extra={'user_id': user_id, 'tier': result['tier']}
            )
            return result
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.warning(f"⚠️ 获取用户权限失败，使用降级数据: user_id={user_id}, error={e}")
            return self._get_fallback_membership(user_id)
        finally:
            self.config.timeout = original_timeout

    async def check_usage(self, user_id: int, mode: str = "dag") -> Dict[str, Any]:
        """检查用户用量"""
        endpoint = "/api/internal/usage/check"
        try:
            data = await self._request("POST", endpoint, json={'user_id': user_id, 'mode': mode})
            result = {
                'can_execute': data.get('can_execute', True),
                'dag_used': data.get('dag_used', 0),
                'dag_limit': data.get('dag_limit', -1),
                'dag_remaining': data.get('dag_remaining', -1),
                'agent_used': data.get('agent_used', 0),
                'agent_limit': data.get('agent_limit', -1),
                'agent_remaining': data.get('agent_remaining', -1),
                'dag_credits': data.get('dag_credits', 0),
                'agent_credits': data.get('agent_credits', 0),
                'message': data.get('message', ''),
            }
            logger.debug(
                f"✅ 用量检查成功: user_id={user_id}, mode={mode}, can_execute={result['can_execute']}",
                extra={'user_id': user_id, 'mode': mode, 'usage': result}
            )
            return result
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.warning(f"⚠️ 用量检查失败，允许执行: user_id={user_id}, mode={mode}, error={e}")
            return {
                'can_execute': True, 'dag_used': 0, 'dag_limit': -1, 'dag_remaining': -1,
                'agent_used': 0, 'agent_limit': -1, 'agent_remaining': -1,
                'dag_credits': 0, 'agent_credits': 0,
                'message': '用量检查失败，暂时允许执行',
            }

    async def increment_usage(self, user_id: int, mode: str = "dag") -> Dict[str, Any]:
        """增加用量计数"""
        endpoint = "/api/internal/membership/increment-usage"
        try:
            data = await self._request("POST", endpoint, json={'user_id': user_id, 'mode': mode})
            result = {
                'success': data.get('success', True),
                'dag_used': data.get('dag_used', 0),
                'dag_remaining': data.get('dag_remaining', -1),
                'agent_used': data.get('agent_used', 0),
                'agent_remaining': data.get('agent_remaining', -1),
            }
            logger.info(
                f"✅ 用量增加成功: user_id={user_id}, mode={mode}, "
                f"dag_used={result['dag_used']}, agent_used={result['agent_used']}",
                extra={'user_id': user_id, 'mode': mode, 'usage': result}
            )
            return result
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"❌ 用量增加失败: user_id={user_id}, mode={mode}, error={e}")
            return {
                'success': False, 'error': str(e),
                'dag_used': 0, 'dag_remaining': -1,
                'agent_used': 0, 'agent_remaining': -1,
            }

    async def get_today_usage(self, user_id: int) -> Dict[str, Any]:
        """获取用户今日用量统计"""
        endpoint = "/api/usage/today"
        try:
            data = await self._request("GET", endpoint, params={'user_id': user_id})
            result = {
                'dag_used': data.get('dag_used', 0),
                'dag_limit': data.get('dag_limit', -1),
                'dag_remaining': data.get('dag_remaining', -1),
                'agent_used': data.get('agent_used', 0),
                'agent_limit': data.get('agent_limit', -1),
                'agent_remaining': data.get('agent_remaining', -1),
                'dag_credits': data.get('dag_credits', 0),
                'agent_credits': data.get('agent_credits', 0),
                'reset_time': data.get('reset_time'),
            }
            logger.debug(f"✅ 获取今日用量成功: user_id={user_id}", extra={'user_id': user_id, 'usage': result})
            return result
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.warning(f"⚠️ 获取今日用量失败: user_id={user_id}, error={e}")
            return {
                'dag_used': 0, 'dag_limit': -1, 'dag_remaining': -1,
                'agent_used': 0, 'agent_limit': -1, 'agent_remaining': -1,
                'dag_credits': 0, 'agent_credits': 0, 'reset_time': None,
            }
