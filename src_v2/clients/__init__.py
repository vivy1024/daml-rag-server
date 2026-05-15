"""
Laravel 后端内部 API 客户端

通过容器网络调用 Laravel 后端的 /api/internal/* 端点，
获取用户档案、训练记录等数据。

认证方式：X-Internal-Token header
"""

import logging
import os
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# 配置
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", os.getenv("BACKEND_API_URL", "http://fitness_nginx_v2:80"))
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")
TIMEOUT = float(os.getenv("BACKEND_API_TIMEOUT", "10.0"))
MAX_RETRIES = int(os.getenv("BACKEND_API_MAX_RETRIES", "2"))


class BackendClient:
    """Laravel 后端内部 API 客户端"""

    def __init__(
        self,
        base_url: str = BACKEND_BASE_URL,
        token: str = INTERNAL_API_TOKEN,
        timeout: float = TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "X-Internal-Token": self.token,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """发起请求，带重试和错误处理"""
        client = await self._get_client()
        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.request(method, path, **kwargs)

                if response.status_code == 200:
                    data = response.json()
                    # Laravel 统一响应格式: {"code": 200, "msg": "...", "data": {...}}
                    if isinstance(data, dict) and "data" in data:
                        return data["data"]
                    return data

                if response.status_code == 404:
                    logger.warning(f"Backend 404: {path}")
                    return None

                if response.status_code >= 500 and attempt < MAX_RETRIES:
                    logger.warning(
                        f"Backend {response.status_code} (attempt {attempt+1}): {path}"
                    )
                    continue

                logger.error(
                    f"Backend error {response.status_code}: {path} -> {response.text[:200]}"
                )
                return None

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    logger.warning(f"Backend timeout (attempt {attempt+1}): {path}")
                    continue
            except httpx.ConnectError as e:
                last_error = e
                logger.error(f"Backend connect error: {path} -> {e}")
                break
            except Exception as e:
                last_error = e
                logger.error(f"Backend unexpected error: {path} -> {e}")
                break

        logger.error(f"Backend request failed after {MAX_RETRIES+1} attempts: {path}, last_error={last_error}")
        return None

    # === 用户数据 API ===

    def _validate_user_id(self, user_id: str) -> str:
        """校验 user_id 格式，防止路径注入"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            raise ValueError(f"Invalid user_id format: {user_id}")
        return user_id

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户完整健身档案"""
        uid = self._validate_user_id(user_id)
        return await self._request("GET", f"/api/internal/users/{uid}/profile")

    async def get_training_records(
        self, user_id: str, days: int = 30, exercise_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """获取训练记录"""
        uid = self._validate_user_id(user_id)
        params = {"days": days}
        if exercise_name:
            params["exercise_name"] = exercise_name
        return await self._request(
            "GET", f"/api/internal/users/{uid}/training-records", params=params
        )

    async def get_active_plan(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取当前激活的训练计划"""
        uid = self._validate_user_id(user_id)
        return await self._request("GET", f"/api/internal/users/{uid}/active-plan")

    async def get_progress_data(
        self, user_id: str, metric: str = "weight", days: int = 90
    ) -> Optional[Dict[str, Any]]:
        """获取进度数据（体重/体脂/FFMI/力量趋势）"""
        uid = self._validate_user_id(user_id)
        params = {"metric": metric, "days": days}
        return await self._request(
            "GET", f"/api/internal/users/{uid}/progress", params=params
        )

    async def save_training_plan(
        self, user_id: str, plan_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """保存 AI 生成的训练计划"""
        return await self._request(
            "POST",
            "/api/internal/training-plans/import",
            json={"user_id": user_id, **plan_data},
        )


# 全局单例
_client: Optional[BackendClient] = None


def get_backend_client() -> BackendClient:
    """获取全局 BackendClient 单例"""
    global _client
    if _client is None:
        if not INTERNAL_API_TOKEN:
            logger.warning("INTERNAL_API_TOKEN 未设置，用户数据工具将无法认证")
        _client = BackendClient()
    return _client
