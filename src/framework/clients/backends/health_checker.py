# -*- coding: utf-8 -*-
"""
BackendHealthChecker - 后端健康检查器

管理LLM后端的健康状态缓存和检查逻辑。

Task 45 - Phase 7 Batch 4
"""

import logging
import time
from typing import Dict, Optional

from .base import IBackendClient

logger = logging.getLogger(__name__)


class BackendHealthChecker:
    """
    后端健康检查器

    维护健康状态缓存（TTL 60秒），避免频繁探测。
    """

    def __init__(self, cache_ttl: float = 60.0):
        self._cache_ttl = cache_ttl
        self._health_cache: Dict[str, tuple[bool, float]] = {}

    async def is_healthy(
        self, backend_name: str, client: IBackendClient
    ) -> bool:
        """
        检查后端是否健康（带缓存）。

        Args:
            backend_name: 后端标识
            client: 后端客户端实例
        """
        if backend_name in self._health_cache:
            is_ok, last_check = self._health_cache[backend_name]
            if time.time() - last_check < self._cache_ttl:
                return is_ok

        try:
            is_ok = await client.health_check()
            self._health_cache[backend_name] = (is_ok, time.time())
            logger.debug(f"后端健康检查: {backend_name}={is_ok}")
            return is_ok
        except Exception as e:
            logger.warning(f"后端健康检查失败: {backend_name}, error={e}")
            self._health_cache[backend_name] = (False, time.time())
            return False

    def mark_unhealthy(self, backend_name: str) -> None:
        """标记后端为不健康"""
        self._health_cache[backend_name] = (False, time.time())
        logger.warning(f"标记后端为不健康: {backend_name}")

    def get_status(self) -> Dict[str, bool]:
        """返回所有后端的当前健康状态"""
        now = time.time()
        return {
            name: is_ok
            for name, (is_ok, ts) in self._health_cache.items()
            if now - ts < self._cache_ttl
        }
