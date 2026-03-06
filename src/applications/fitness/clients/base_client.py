# -*- coding: utf-8 -*-
"""
BackendClientBase — HTTP 核心基础设施

从 backend_client.py 拆分，包含配置、连接管理、请求重试等核心逻辑。
"""

import json
import httpx
import logging
from typing import Dict, Any, Optional

from src.framework.config.app_config import get_config

from .models import (
    BackendAPIError,
    BackendAuthError,
    BackendNotFoundError,
    BackendValidationError,
    BackendServerError,
)

logger = logging.getLogger(__name__)


class BackendConfig:
    """后端API配置 - 从 app_config 读取"""

    def __init__(self):
        cfg = get_config()
        self.base_url = cfg.backend.api_url
        self.internal_token = cfg.internal.api_token
        self.timeout = cfg.backend.api_timeout
        self.max_retries = cfg.backend.api_max_retries

        self.pool_max_connections = cfg.backend.pool_max_connections
        self.pool_max_keepalive = cfg.backend.pool_max_keepalive
        self.pool_keepalive_expiry = cfg.backend.pool_keepalive_expiry

        self.membership_timeout_ms = cfg.backend.membership_timeout_ms
        self.user_profile_timeout_ms = cfg.backend.user_profile_timeout_ms

        if not self.base_url:
            raise ValueError("BACKEND_API_URL environment variable is required")
        if not self.internal_token:
            raise ValueError("INTERNAL_API_TOKEN environment variable is required")

    def get_headers(self) -> Dict[str, str]:
        return {
            'X-Internal-Token': self.internal_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }


class BackendClientBase:
    """后端API客户端 — 核心 HTTP 基础设施"""

    def __init__(self, config: Optional[BackendConfig] = None, cache_manager=None):
        self.config = config or BackendConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._is_warmed_up = False
        self.cache_manager = cache_manager

        self._pool_stats = {
            'total_requests': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'warmup_time_ms': 0.0
        }

        logger.info(
            f"Backend client initialized: {self.config.base_url}",
            extra={
                'base_url': self.config.base_url,
                'timeout': self.config.timeout,
                'max_retries': self.config.max_retries,
                'pool_max_connections': self.config.pool_max_connections,
                'pool_max_keepalive': self.config.pool_max_keepalive,
                'cache_enabled': cache_manager is not None
            }
        )

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=self.config.get_headers(),
            timeout=self.config.timeout,
            limits=httpx.Limits(
                max_connections=self.config.pool_max_connections,
                max_keepalive_connections=self.config.pool_max_keepalive,
                keepalive_expiry=self.config.pool_keepalive_expiry
            )
        )
        await self._warmup_connection_pool()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=self.config.get_headers(),
                timeout=self.config.timeout,
                limits=httpx.Limits(
                    max_connections=self.config.pool_max_connections,
                    max_keepalive_connections=self.config.pool_max_keepalive,
                    keepalive_expiry=self.config.pool_keepalive_expiry
                )
            )
        return self._client

    async def _warmup_connection_pool(self):
        if self._is_warmed_up:
            return

        import time
        start_time = time.time()

        try:
            logger.info("🔥 开始预热连接池...")
            client = self._get_client()
            try:
                response = await client.get("/api/health", timeout=2.0)
                if response.is_success:
                    logger.info("✅ 连接池预热成功")
                else:
                    logger.warning(f"⚠️ 连接池预热响应异常: {response.status_code}")
            except httpx.TimeoutException:
                logger.warning("⚠️ 连接池预热超时，但连接已建立")
            except (httpx.HTTPError, ConnectionError, OSError) as e:
                logger.warning(f"⚠️ 连接池预热失败: {e}")

            self._is_warmed_up = True
            warmup_time = (time.time() - start_time) * 1000
            self._pool_stats['warmup_time_ms'] = warmup_time

            logger.info(
                f"🔥 连接池预热完成: {warmup_time:.2f}ms",
                extra={'warmup_time_ms': warmup_time}
            )

        except (httpx.HTTPError, ConnectionError, OSError, RuntimeError) as e:
            logger.error(f"连接池预热异常: {e}")

    def get_pool_stats(self) -> Dict[str, Any]:
        return {
            'total_requests': self._pool_stats['total_requests'],
            'warmup_time_ms': self._pool_stats['warmup_time_ms'],
            'is_warmed_up': self._is_warmed_up,
            'config': {
                'max_connections': self.config.pool_max_connections,
                'max_keepalive': self.config.pool_max_keepalive,
                'keepalive_expiry': self.config.pool_keepalive_expiry
            }
        }

    def _handle_response_error(self, response: httpx.Response) -> None:
        try:
            error_data = response.json()
            error_message = error_data.get('message', response.text)
        except (json.JSONDecodeError, ValueError):
            error_message = response.text

        if response.status_code == 401:
            raise BackendAuthError(f"认证失败: {error_message}")
        elif response.status_code == 404:
            raise BackendNotFoundError(f"资源未找到: {error_message}")
        elif response.status_code in (400, 422):
            raise BackendValidationError(f"验证失败: {error_message}")
        elif response.status_code >= 500:
            raise BackendServerError(f"服务器错误: {error_message}")
        else:
            raise BackendAPIError(f"API错误 ({response.status_code}): {error_message}")

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        client = self._get_client()
        self._pool_stats['total_requests'] += 1

        for attempt in range(self.config.max_retries):
            try:
                logger.debug(
                    f"Backend API request: {method} {endpoint} (attempt {attempt + 1})",
                    extra={
                        'method': method,
                        'endpoint': endpoint,
                        'attempt': attempt + 1,
                    }
                )

                response = await client.request(method, endpoint, **kwargs)

                if not response.is_success:
                    self._handle_response_error(response)

                result = response.json()

                if 'code' in result:
                    if result.get('code') != 200:
                        error_msg = result.get('msg', 'Unknown error')
                        raise BackendAPIError(f"API业务错误: {error_msg}")
                elif not result.get('success', False):
                    error_msg = result.get('message', 'Unknown error')
                    raise BackendAPIError(f"API业务错误: {error_msg}")

                logger.info(
                    f"Backend API success: {method} {endpoint}",
                    extra={
                        'method': method,
                        'endpoint': endpoint,
                        'status': response.status_code,
                    }
                )

                return result.get('data', {})

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < self.config.max_retries - 1:
                    logger.warning(
                        f"Backend API network error, retrying: {e}",
                        extra={
                            'method': method,
                            'endpoint': endpoint,
                            'attempt': attempt + 1,
                            'error': str(e),
                        }
                    )
                    continue
                else:
                    logger.error(
                        f"Backend API failed after {self.config.max_retries} retries",
                        extra={
                            'method': method,
                            'endpoint': endpoint,
                            'error': str(e),
                        }
                    )
                    raise BackendAPIError(f"网络错误: {e}")

            except BackendAPIError:
                raise

            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                logger.error(
                    f"Backend API unexpected error: {e}",
                    extra={
                        'method': method,
                        'endpoint': endpoint,
                        'error': str(e),
                    },
                    exc_info=True
                )
                raise BackendAPIError(f"未知错误: {e}")

        raise BackendAPIError("请求失败")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def log_cache_statistics(self):
        if self.cache_manager:
            stats = self.cache_manager.get_statistics()
            logger.info(
                f"📊 缓存统计: "
                f"总请求={stats['total_requests']}, "
                f"命中率={stats['hit_rate']}%, "
                f"用户档案命中率={stats['user_profile_hit_rate']}%, "
                f"会员权限命中率={stats['membership_hit_rate']}%, "
                f"平均响应时间={stats['avg_response_time_ms']}ms",
                extra=stats
            )
            return stats
        else:
            logger.warning("缓存管理器未初始化，无法获取统计信息")
            return None
