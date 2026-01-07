# -*- coding: utf-8 -*-
"""
基础客户端接口

定义所有客户端的通用接口和行为。

版本: v2.0.0
日期: 2025-12-03
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ClientStatus(Enum):
    """客户端状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ClientConfig:
    """客户端配置基类"""
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_cache: bool = True
    cache_ttl: int = 300  # 5分钟

    # 日志配置
    log_level: str = "INFO"
    log_requests: bool = True
    log_responses: bool = False


class BaseClient(ABC):
    """
    基础客户端抽象类

    定义所有客户端必须实现的通用接口：
    - 连接管理
    - 请求处理
    - 错误处理
    - 缓存机制
    - 日志记录
    """

    def __init__(self, config: Optional[ClientConfig] = None):
        """
        初始化基础客户端

        Args:
            config: 客户端配置，如果为None则使用默认配置
        """
        self.config = config or ClientConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.status = ClientStatus.DISCONNECTED
        self._cache = {} if self.config.enable_cache else None
        self._setup_logging()

    def _setup_logging(self):
        """设置日志记录"""
        if self.config.log_level:
            self.logger.setLevel(getattr(logging, self.config.log_level.upper()))

    @abstractmethod
    async def connect(self) -> bool:
        """
        建立连接

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    async def _execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行请求的具体实现

        Args:
            request: 请求数据

        Returns:
            Dict[str, Any]: 响应数据
        """
        pass

    async def request(self, endpoint: str, data: Optional[Dict[str, Any]] = None,
                     method: str = "GET", **kwargs) -> Dict[str, Any]:
        """
        通用请求方法

        Args:
            endpoint: 请求端点或方法名
            data: 请求数据
            method: 请求方法（GET、POST等）
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 响应数据
        """
        if self.status != ClientStatus.CONNECTED:
            raise RuntimeError(f"客户端未连接，当前状态: {self.status.value}")

        # 构建请求
        request = {
            "endpoint": endpoint,
            "method": method,
            "data": data or {},
            **kwargs
        }

        # 缓存检查
        cache_key = self._get_cache_key(request)
        if self._cache and cache_key in self._cache:
            cached_response = self._cache[cache_key]
            if self._is_cache_valid(cached_response):
                if self.config.log_requests:
                    self.logger.debug(f"📦 使用缓存响应: {endpoint}")
                return cached_response["data"]

        # 执行请求
        if self.config.log_requests:
            self.logger.debug(f"🚀 发送请求: {endpoint}")

        try:
            response = await self._execute_request_with_retry(request)

            # 缓存响应
            if self._cache:
                self._cache[cache_key] = {
                    "data": response,
                    "timestamp": self._get_current_timestamp()
                }

            if self.config.log_responses:
                self.logger.debug(f"✅ 响应成功: {endpoint}")

            return response

        except Exception as e:
            self.logger.error(f"❌ 请求失败: {endpoint}, 错误: {str(e)}")
            self.status = ClientStatus.ERROR
            raise

    async def _execute_request_with_retry(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """带重试的请求执行"""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await self._execute_request(request)
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    self.logger.warning(f"⚠️ 请求失败，重试 {attempt + 1}/{self.config.max_retries}: {str(e)}")
                    await self._wait_retry_delay()
                else:
                    break

        raise last_exception

    async def _wait_retry_delay(self):
        """等待重试延迟"""
        import asyncio
        await asyncio.sleep(self.config.retry_delay)

    def _get_cache_key(self, request: Dict[str, Any]) -> str:
        """生成缓存键"""
        import json
        import hashlib

        # 只缓存GET请求
        if request.get("method", "GET").upper() != "GET":
            return None

        cache_data = {
            "endpoint": request["endpoint"],
            "data": sorted(request.get("data", {}).items())
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _is_cache_valid(self, cached_response: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if not cached_response or "timestamp" not in cached_response:
            return False

        current_time = self._get_current_timestamp()
        return (current_time - cached_response["timestamp"]) < self.config.cache_ttl

    def _get_current_timestamp(self) -> float:
        """获取当前时间戳"""
        import time
        return time.time()

    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
            self.logger.info("🧹 客户端缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self._cache:
            return {"cache_enabled": False}

        current_time = self._get_current_timestamp()
        valid_cache = sum(
            1 for cached in self._cache.values()
            if self._is_cache_valid(cached)
        )

        return {
            "cache_enabled": True,
            "total_entries": len(self._cache),
            "valid_entries": valid_cache,
            "expired_entries": len(self._cache) - valid_cache,
            "cache_ttl": self.config.cache_ttl
        }

    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态信息"""
        return {
            "status": self.status.value,
            "config": {
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
                "enable_cache": self.config.enable_cache,
                "log_level": self.config.log_level
            },
            "cache_stats": self.get_cache_stats()
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()