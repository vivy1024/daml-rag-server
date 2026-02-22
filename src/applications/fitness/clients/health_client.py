# -*- coding: utf-8 -*-
"""HealthMixin — 健康检查 + 训练日志 + 个人最佳记录 API"""

import httpx
import logging
from typing import Dict, Any, Optional, List

from .models import BackendAPIError, BackendNotFoundError

logger = logging.getLogger(__name__)


class HealthMixin:
    """健康检查与训练数据 API 方法集"""

    async def health_check(self) -> Dict[str, Any]:
        """检查后端健康状态"""
        try:
            client = self._get_client()
            response = await client.get("/api/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Backend health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}

    async def get_active_user_ids(self, limit: int = 20) -> List[int]:
        """获取活跃用户ID列表（用于预热缓存）"""
        try:
            client = self._get_client()

            try:
                response = await client.get(
                    "/api/internal/users/active", params={"limit": limit}, timeout=3.0
                )
                if response.is_success:
                    data = response.json()
                    user_ids = data.get('data', [])
                    if user_ids:
                        return [int(uid) for uid in user_ids[:limit]]
            except Exception:
                pass

            try:
                response = await client.get(
                    "/api/internal/users/recent", params={"limit": limit}, timeout=3.0
                )
                if response.is_success:
                    data = response.json()
                    users = data.get('data', [])
                    if users:
                        return [int(u.get('id', u)) for u in users[:limit] if u]
            except Exception:
                pass

            logger.info("ℹ️ 后端暂无活跃用户API，将按需加载用户档案")
            return []

        except Exception as e:
            logger.warning(f"⚠️ 获取活跃用户ID失败: {e}")
            return []

    async def get_training_logs(
        self, user_id: int, start_date: Optional[str] = None,
        end_date: Optional[str] = None, mesocycle_id: Optional[str] = None,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """获取用户训练日志列表"""
        endpoint = f"/api/internal/training-logs/{user_id}"
        params = {'per_page': per_page}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if mesocycle_id:
            params['mesocycle_id'] = mesocycle_id

        try:
            data = await self._request("GET", endpoint, params=params)
            logs = data.get('rows', [])
            logger.info(
                f"获取训练日志成功: user_id={user_id}, count={len(logs)}",
                extra={'user_id': user_id, 'start_date': start_date, 'end_date': end_date, 'logs_count': len(logs)}
            )
            return logs
        except BackendNotFoundError:
            logger.info(f"用户训练日志不存在: user_id={user_id}")
            return []
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"获取训练日志失败: user_id={user_id}, error={e}")
            return []

    async def get_training_log_stats(
        self, user_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户训练统计"""
        endpoint = f"/api/internal/training-logs/{user_id}/stats"
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        try:
            data = await self._request("GET", endpoint, params=params)
            logger.info(f"获取训练统计成功: user_id={user_id}", extra={'user_id': user_id, 'stats': data})
            return data
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"获取训练统计失败: user_id={user_id}, error={e}")
            return {
                'total_sessions': 0, 'avg_completion_rate': 0.0,
                'avg_rpe': 0.0, 'total_exercises': 0, 'total_sets': 0
            }

    async def get_personal_bests(self, user_id: int, per_page: int = 100) -> List[Dict[str, Any]]:
        """获取用户所有个人最佳记录"""
        endpoint = f"/api/internal/personal-bests/{user_id}"
        try:
            data = await self._request("GET", endpoint, params={'per_page': per_page})
            records = data.get('rows', [])
            logger.info(
                f"获取个人最佳记录成功: user_id={user_id}, count={len(records)}",
                extra={'user_id': user_id, 'records_count': len(records)}
            )
            return records
        except BackendNotFoundError:
            logger.info(f"用户个人最佳记录不存在: user_id={user_id}")
            return []
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"获取个人最佳记录失败: user_id={user_id}, error={e}")
            return []

    async def get_personal_best(self, user_id: int, exercise_id: str) -> Optional[Dict[str, Any]]:
        """获取用户特定动作的个人最佳记录"""
        endpoint = f"/api/internal/personal-bests/{user_id}/{exercise_id}"
        try:
            data = await self._request("GET", endpoint)
            logger.info(
                f"获取个人最佳记录成功: user_id={user_id}, exercise_id={exercise_id}",
                extra={'user_id': user_id, 'exercise_id': exercise_id}
            )
            return data
        except BackendNotFoundError:
            logger.info(f"个人最佳记录不存在: user_id={user_id}, exercise_id={exercise_id}")
            return None
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"获取个人最佳记录失败: user_id={user_id}, exercise_id={exercise_id}, error={e}")
            return None

    async def update_personal_best(
        self, user_id: int, exercise_id: str, weight: float,
        reps: int, exercise_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新个人最佳记录"""
        endpoint = f"/api/internal/personal-bests/{user_id}/update"
        payload = {'exercise_id': exercise_id, 'weight': weight, 'reps': reps}
        if exercise_name:
            payload['exercise_name'] = exercise_name

        try:
            data = await self._request("POST", endpoint, json=payload)
            is_new_record = data.get('is_new_record', False)
            logger.info(
                f"更新个人最佳记录: user_id={user_id}, exercise_id={exercise_id}, is_new_record={is_new_record}",
                extra={
                    'user_id': user_id, 'exercise_id': exercise_id,
                    'weight': weight, 'reps': reps, 'is_new_record': is_new_record
                }
            )
            return data
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"更新个人最佳记录失败: user_id={user_id}, exercise_id={exercise_id}, error={e}")
            raise BackendAPIError(f"更新个人最佳记录失败: {e}")

    async def get_strength_leaderboard(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """获取用户力量排行榜"""
        endpoint = f"/api/internal/personal-bests/{user_id}/leaderboard"
        try:
            data = await self._request("GET", endpoint, params={'limit': limit})
            leaderboard = data.get('leaderboard', [])
            logger.info(
                f"获取力量排行榜成功: user_id={user_id}, count={len(leaderboard)}",
                extra={'user_id': user_id, 'leaderboard_count': len(leaderboard)}
            )
            return leaderboard
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"获取力量排行榜失败: user_id={user_id}, error={e}")
            return []

    async def update_volume_multiplier(
        self, user_id: int, new_multiplier: float, adjustment: float, reason: str
    ) -> Dict[str, Any]:
        """更新用户的容量系数"""
        endpoint = f"/api/internal/user-profile/{user_id}/volume-multiplier"
        payload = {'new_multiplier': new_multiplier, 'adjustment': adjustment, 'reason': reason}

        try:
            data = await self._request("PUT", endpoint, json=payload)
            logger.info(
                f"更新容量系数成功: user_id={user_id}, new_multiplier={new_multiplier}, adjustment={adjustment:+.2f}",
                extra={'user_id': user_id, 'new_multiplier': new_multiplier, 'adjustment': adjustment, 'reason': reason}
            )

            if self.cache_manager:
                try:
                    await self.cache_manager.invalidate_user_profile(str(user_id))
                    logger.debug(f"已清除用户档案缓存: user_id={user_id}")
                except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                    logger.warning(f"清除缓存失败: {e}")

            return data
        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"更新容量系数失败: user_id={user_id}, error={e}")
            raise BackendAPIError(f"更新容量系数失败: {e}")
