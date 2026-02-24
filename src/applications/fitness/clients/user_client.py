# -*- coding: utf-8 -*-
"""UserMixin — 用户档案相关 API"""

import httpx
import logging
from typing import Dict, Any

from .models import BackendAPIError, BackendNotFoundError

logger = logging.getLogger(__name__)


class UserMixin:
    """用户档案 API 方法集"""

    async def get_user_profile(self, user_id: int, timeout: float = 5.0) -> Dict[str, Any]:
        """获取用户档案（带超时控制和降级机制，集成缓存）"""
        user_id_str = str(user_id)

        # 1. 尝试从缓存获取
        if self.cache_manager:
            try:
                cached_profile = await self.cache_manager.get_user_profile(user_id_str)
                if cached_profile is not None:
                    is_fallback = cached_profile.get('_fallback', False)
                    if is_fallback:
                        logger.info(
                            f"✅ 用户档案缓存命中（降级数据）: user_id={user_id}",
                            extra={'user_id': user_id, 'cache_hit': True, 'is_fallback': True}
                        )
                    else:
                        logger.info(
                            f"✅ 用户档案缓存命中: user_id={user_id}",
                            extra={'user_id': user_id, 'cache_hit': True}
                        )
                    return cached_profile
                else:
                    logger.debug(
                        f"❌ 用户档案缓存未命中: user_id={user_id}",
                        extra={'user_id': user_id, 'cache_hit': False}
                    )
            except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                logger.warning(f"缓存查询失败，将从API获取: {e}")

        # 2. 缓存未命中，从API获取
        endpoint = f"/api/internal/user-profile/{user_id}"

        try:
            original_timeout = self.config.timeout
            self.config.timeout = timeout

            data = await self._request("GET", endpoint)

            self.config.timeout = original_timeout

            # 3. 写入缓存
            if self.cache_manager and data:
                try:
                    await self.cache_manager.set_user_profile(user_id_str, data)
                    logger.debug(
                        f"💾 用户档案已缓存: user_id={user_id}",
                        extra={'user_id': user_id}
                    )
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                    logger.warning(f"缓存写入失败: {e}")

            return data

        except httpx.TimeoutException:
            logger.warning(
                f"用户档案加载超时（{timeout}秒），使用降级策略: user_id={user_id}"
            )
            fallback_profile = self._get_fallback_profile(user_id)

            if self.cache_manager:
                try:
                    await self.cache_manager.set_user_profile(user_id_str, fallback_profile)
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                    logger.warning(f"降级档案缓存失败: {e}")

            return fallback_profile

        except BackendNotFoundError:
            logger.info(f"用户档案不存在，使用降级策略: user_id={user_id}")
            fallback_profile = self._get_fallback_profile(user_id)

            if self.cache_manager:
                try:
                    await self.cache_manager.set_user_profile(user_id_str, fallback_profile)
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                    logger.warning(f"降级档案缓存失败: {e}")

            return fallback_profile

        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(
                f"用户档案加载失败，使用降级策略: user_id={user_id}, error={str(e)}"
            )
            fallback_profile = self._get_fallback_profile(user_id)

            if self.cache_manager:
                try:
                    await self.cache_manager.set_user_profile(user_id_str, fallback_profile)
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                    logger.warning(f"降级档案缓存失败: {e}")

            return fallback_profile

    def _get_fallback_profile(self, user_id: int) -> Dict[str, Any]:
        """获取降级用户档案"""
        return {
            'user_id': str(user_id),
            'basic_info': {
                'age': 25, 'gender': 'unknown', 'height': 170,
                'weight': 65, 'body_type': None, 'user_type': 'other',
            },
            'nutrition_profile': {
                'daily_calories': 2000, 'protein_g': 100,
                'carbs_g': 250, 'fat_g': 65
            },
            'fitness_config': {
                'training_experience': 'beginner', 'training_frequency': 3,
                'session_duration': 60, 'preferred_training_time': None,
                'preferred_rest_pattern': None,
            },
            'fitness_goals': {
                'primary_goal': 'general_fitness', 'target_weight': 65
            },
            'strength_data': {},
            'health_status': {
                'injuries': [], 'medical_conditions': []
            },
            'training_system': {
                'preferred_training_time': None, 'body_type': None,
                'user_type': 'other', 'campus_name': None,
                'personal_volume_multiplier': 1.0,
                'personal_recovery_factor': 1.0,
                'last_volume_adjusted_at': None,
                'consecutive_training_weeks': 0,
            },
            'created_at': None,
            'updated_at': None,
            '_fallback': True
        }
