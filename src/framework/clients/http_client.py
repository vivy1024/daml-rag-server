# -*- coding: utf-8 -*-
"""
HTTP客户端

用于与REST API通信的客户端，基于httpx实现异步请求。
替代原有的backend_client.py，提供更统一的接口。

版本: v2.0.0
日期: 2025-12-03
"""

import httpx
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from urllib.parse import urljoin

from .base_client import BaseClient, ClientConfig, ClientStatus


@dataclass
class HTTPClientConfig(ClientConfig):
    """HTTP客户端配置"""
    base_url: str = ""
    headers: Optional[Dict[str, str]] = None
    verify_ssl: bool = True
    follow_redirects: bool = True
    max_connections: int = 100
    max_keepalive_connections: int = 20


class HTTPClient(BaseClient):
    """
    HTTP客户端

    用于与REST API通信，支持：
    - 异步请求
    - 自动重试
    - 响应缓存
    - 错误处理
    - 连接池管理
    """

    def __init__(self, config: Optional[HTTPClientConfig] = None):
        """
        初始化HTTP客户端

        Args:
            config: HTTP客户端配置
        """
        self.http_config = config or HTTPClientConfig()
        super().__init__(self.http_config)

        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """
        建立HTTP连接

        Returns:
            bool: 连接是否成功
        """
        try:
            self.status = ClientStatus.CONNECTING

            # 创建httpx客户端
            self._client = httpx.AsyncClient(
                base_url=self.http_config.base_url,
                headers=self.http_config.headers or {},
                timeout=self.http_config.timeout,
                verify=self.http_config.verify_ssl,
                follow_redirects=self.http_config.follow_redirects,
                limits=httpx.Limits(
                    max_connections=self.http_config.max_connections,
                    max_keepalive_connections=self.http_config.max_keepalive_connections
                )
            )

            self.status = ClientStatus.CONNECTED
            self.logger.info(f"✅ HTTP客户端已连接: {self.http_config.base_url}")
            return True

        except Exception as e:
            self.status = ClientStatus.ERROR
            self.logger.error(f"❌ HTTP客户端连接失败: {str(e)}")
            return False

    async def disconnect(self):
        """断开HTTP连接"""
        if self._client:
            await self._client.aclose()
            self._client = None

        self.status = ClientStatus.DISCONNECTED
        self.logger.info("🔌 HTTP客户端已断开连接")

    async def _execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行HTTP请求

        Args:
            request: 请求数据，包含endpoint、method、data等

        Returns:
            Dict[str, Any]: 响应数据
        """
        if not self._client:
            raise RuntimeError("HTTP客户端未初始化")

        endpoint = request["endpoint"]
        method = request.get("method", "GET").upper()
        data = request.get("data", {})

        # 构建请求参数
        url = self._build_url(endpoint)
        kwargs = {
            "method": method,
            "url": url
        }

        # 添加请求数据
        if method in ["POST", "PUT", "PATCH"]:
            if isinstance(data, dict):
                kwargs["json"] = data
            else:
                kwargs["content"] = data

        elif method == "GET" and data:
            kwargs["params"] = data

        # 执行请求
        response = await self._client.request(**kwargs)

        # 检查响应状态
        response.raise_for_status()

        # 解析响应
        try:
            return response.json()
        except Exception:
            # 如果不是JSON，返回文本
            return {"text": response.text}

    def _build_url(self, endpoint: str) -> str:
        """构建完整的URL"""
        if self.http_config.base_url:
            return urljoin(self.http_config.base_url, endpoint)
        return endpoint

    # 便捷方法
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET请求"""
        return await self.request(endpoint, data=params, method="GET")

    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST请求"""
        return await self.request(endpoint, data=data, method="POST")

    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """PUT请求"""
        return await self.request(endpoint, data=data, method="PUT")

    async def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """PATCH请求"""
        return await self.request(endpoint, data=data, method="PATCH")

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE请求"""
        return await self.request(endpoint, method="DELETE")


# 便捷工厂函数
def create_backend_client(
    base_url: str,
    internal_token: str,
    timeout: float = 30.0,
    max_retries: int = 3
) -> HTTPClient:
    """
    创建后端API客户端

    Args:
        base_url: 后端API基础URL
        internal_token: 内部认证令牌
        timeout: 请求超时时间
        max_retries: 最大重试次数

    Returns:
        HTTPClient: 配置好的HTTP客户端
    """
    config = HTTPClientConfig(
        base_url=base_url,
        headers={
            'X-Internal-Token': internal_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        timeout=timeout,
        max_retries=max_retries
    )

    return HTTPClient(config)