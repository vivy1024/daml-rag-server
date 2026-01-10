# -*- coding: utf-8 -*-
"""
超时管理器 - 统一超时配置和中断机制

Requirements: 3.6 - 统一超时配置

功能：
1. 从config.toml加载超时配置
2. 提供超时装饰器
3. 实现超时中断机制
4. 支持动态调整超时

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class TimeoutConfig:
    """超时配置数据类"""
    # 三层检索引擎超时（毫秒）
    layer1_timeout_ms: int = 5000
    layer2_timeout_ms: int = 10000
    layer3_timeout_ms: int = 3000
    total_retrieval_timeout_ms: int = 30000
    
    # HTTP客户端超时（毫秒）
    http_connect_timeout_ms: int = 5000
    http_read_timeout_ms: int = 60000
    http_total_timeout_ms: int = 120000
    
    # 数据库连接超时（毫秒）
    neo4j_connection_timeout_ms: int = 30000
    qdrant_timeout_ms: int = 10000
    redis_timeout_ms: int = 5000
    
    # MCP工具执行超时（毫秒）
    mcp_tool_timeout_ms: int = 30000
    mcp_dag_timeout_ms: int = 60000
    
    # LLM调用超时（毫秒）
    llm_timeout_ms: int = 120000
    llm_streaming_timeout_ms: int = 180000
    
    def get_seconds(self, key: str) -> float:
        """获取超时配置（秒）"""
        ms_value = getattr(self, key, 30000)
        return ms_value / 1000.0
    
    def get_ms(self, key: str) -> int:
        """获取超时配置（毫秒）"""
        return getattr(self, key, 30000)


class TimeoutManager:
    """
    超时管理器 - 单例模式
    
    使用方式：
    ```python
    # 获取实例
    timeout_mgr = TimeoutManager.get_instance()
    
    # 获取超时配置
    layer1_timeout = timeout_mgr.get_timeout("layer1_timeout_ms")
    
    # 使用装饰器
    @timeout_mgr.with_timeout("layer1_timeout_ms")
    async def my_async_function():
        ...
    ```
    """
    
    _instance: Optional['TimeoutManager'] = None
    _config: Optional[TimeoutConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'TimeoutManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _load_config(self) -> None:
        """从config.toml加载超时配置"""
        config_path = Path(__file__).parent.parent.parent.parent / "config.toml"
        
        try:
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config_data = tomllib.load(f)
                
                timeout_section = config_data.get("timeout", {})
                self._config = TimeoutConfig(**{
                    k: v for k, v in timeout_section.items()
                    if hasattr(TimeoutConfig, k)
                })
                logger.info(f"超时配置加载成功: {config_path}")
            else:
                self._config = TimeoutConfig()
                logger.warning(f"配置文件不存在，使用默认超时配置: {config_path}")
        except Exception as e:
            self._config = TimeoutConfig()
            logger.error(f"加载超时配置失败，使用默认值: {e}")
    
    def reload_config(self) -> None:
        """重新加载配置"""
        self._load_config()
    
    @property
    def config(self) -> TimeoutConfig:
        """获取配置对象"""
        if self._config is None:
            self._load_config()
        return self._config
    
    def get_timeout(self, key: str, default_ms: int = 30000) -> float:
        """
        获取超时配置（秒）
        
        Args:
            key: 配置键名（如 "layer1_timeout_ms"）
            default_ms: 默认值（毫秒）
            
        Returns:
            超时时间（秒）
        """
        ms_value = getattr(self.config, key, default_ms)
        return ms_value / 1000.0
    
    def get_timeout_ms(self, key: str, default_ms: int = 30000) -> int:
        """
        获取超时配置（毫秒）
        
        Args:
            key: 配置键名
            default_ms: 默认值（毫秒）
            
        Returns:
            超时时间（毫秒）
        """
        return getattr(self.config, key, default_ms)
    
    def with_timeout(
        self,
        timeout_key: str,
        default_ms: int = 30000,
        on_timeout: Optional[Callable[[], Any]] = None
    ):
        """
        超时装饰器
        
        Args:
            timeout_key: 超时配置键名
            default_ms: 默认超时（毫秒）
            on_timeout: 超时时的回调函数
            
        Example:
            @timeout_mgr.with_timeout("layer1_timeout_ms")
            async def search_vectors():
                ...
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                timeout_seconds = self.get_timeout(timeout_key, default_ms)
                
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    func_name = func.__name__
                    logger.warning(
                        f"函数 {func_name} 超时 ({timeout_seconds}s), "
                        f"配置: {timeout_key}={self.get_timeout_ms(timeout_key)}ms"
                    )
                    
                    if on_timeout:
                        return on_timeout()
                    
                    raise TimeoutError(
                        f"{func_name} 执行超时 ({timeout_seconds}s)"
                    )
            
            return wrapper
        return decorator
    
    async def run_with_timeout(
        self,
        coro,
        timeout_key: str,
        default_ms: int = 30000,
        fallback_value: Any = None
    ) -> Any:
        """
        带超时执行协程
        
        Args:
            coro: 要执行的协程
            timeout_key: 超时配置键名
            default_ms: 默认超时（毫秒）
            fallback_value: 超时时的返回值
            
        Returns:
            协程结果或fallback_value
        """
        timeout_seconds = self.get_timeout(timeout_key, default_ms)
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning(
                f"协程执行超时 ({timeout_seconds}s), "
                f"配置: {timeout_key}={self.get_timeout_ms(timeout_key)}ms"
            )
            return fallback_value


class LayerTimeoutContext:
    """
    层级超时上下文管理器
    
    用于三层检索引擎的超时控制
    
    Example:
        async with LayerTimeoutContext("Layer1", timeout_mgr, "layer1_timeout_ms") as ctx:
            result = await search_vectors()
            if ctx.is_timeout:
                return fallback_result
    """
    
    def __init__(
        self,
        layer_name: str,
        timeout_manager: TimeoutManager,
        timeout_key: str,
        default_ms: int = 5000
    ):
        self.layer_name = layer_name
        self.timeout_manager = timeout_manager
        self.timeout_key = timeout_key
        self.default_ms = default_ms
        self.is_timeout = False
        self.start_time: Optional[float] = None
        self.elapsed_ms: float = 0
    
    async def __aenter__(self):
        import time
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        import time
        if self.start_time:
            self.elapsed_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is asyncio.TimeoutError:
            self.is_timeout = True
            logger.warning(
                f"{self.layer_name} 超时: "
                f"配置={self.timeout_manager.get_timeout_ms(self.timeout_key)}ms, "
                f"实际={self.elapsed_ms:.1f}ms"
            )
            return True  # 抑制异常
        
        return False
    
    def get_remaining_ms(self) -> float:
        """获取剩余超时时间（毫秒）"""
        import time
        if self.start_time is None:
            return self.timeout_manager.get_timeout_ms(self.timeout_key, self.default_ms)
        
        elapsed = (time.time() - self.start_time) * 1000
        timeout_ms = self.timeout_manager.get_timeout_ms(self.timeout_key, self.default_ms)
        return max(0, timeout_ms - elapsed)


# 全局超时管理器实例
timeout_manager = TimeoutManager.get_instance()


def get_timeout_manager() -> TimeoutManager:
    """获取全局超时管理器"""
    return TimeoutManager.get_instance()
