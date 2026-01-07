# -*- coding: utf-8 -*-
"""
Circuit Breaker - 熔断器组件

防止缓存雪崩的熔断器实现

核心功能：
1. 状态转换：CLOSED → OPEN → HALF_OPEN
2. 失败阈值：5次连续失败后开启熔断
3. 超时恢复：60秒后进入半开状态
4. 并发限制：使用Semaphore限制并发为10

版本: v1.0.0
日期: 2025-12-29
作者: 薛小川

Requirements:
- 4.1: 5次连续失败后开启熔断
- 4.2: 60秒后进入半开状态
- 4.3: 限制并发请求为10
- 4.4: 熔断器开启时返回缓存数据（非降级默认值）
"""

import logging
import asyncio
import time
from typing import Any, Callable, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """熔断器状态枚举"""
    CLOSED = "closed"       # 关闭状态（正常工作）
    OPEN = "open"           # 开启状态（熔断中）
    HALF_OPEN = "half_open" # 半开状态（尝试恢复）


class CircuitOpenException(Exception):
    """熔断器开启异常"""
    def __init__(self, message: str = "熔断器已开启，请稍后重试"):
        self.message = message
        super().__init__(self.message)


class CircuitBreakerError(Exception):
    """熔断器错误基类"""
    pass


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    # 失败阈值配置 (Requirements 4.1)
    failure_threshold: int = 5          # 连续失败次数阈值
    
    # 超时配置 (Requirements 4.2)
    timeout_seconds: int = 60           # 熔断超时时间（秒）
    
    # 并发限制配置 (Requirements 4.3)
    max_concurrent_requests: int = 10   # 最大并发请求数
    
    # 半开状态配置
    half_open_max_calls: int = 3        # 半开状态最大尝试次数
    
    # 成功阈值（半开状态恢复到关闭状态需要的成功次数）
    success_threshold: int = 2          # 连续成功次数阈值
    
    # 监控配置
    enable_metrics: bool = True         # 是否启用指标收集


@dataclass
class CircuitBreakerMetrics:
    """熔断器指标"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0             # 被熔断拒绝的调用
    timeout_calls: int = 0              # 超时调用
    state_transitions: int = 0          # 状态转换次数
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_state_change_time: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "timeout_calls": self.timeout_calls,
            "state_transitions": self.state_transitions,
            "success_rate": self.successful_calls / self.total_calls if self.total_calls > 0 else 0,
            "failure_rate": self.failed_calls / self.total_calls if self.total_calls > 0 else 0,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_state_change_time": self.last_state_change_time.isoformat() if self.last_state_change_time else None
        }


class CircuitBreaker:
    """
    熔断器 - 防止缓存雪崩
    
    核心特性：
    1. 状态机：CLOSED → OPEN → HALF_OPEN → CLOSED
    2. 失败计数：连续失败达到阈值后开启熔断
    3. 超时恢复：熔断超时后进入半开状态尝试恢复
    4. 并发控制：使用Semaphore限制并发请求数
    
    状态转换规则：
    - CLOSED → OPEN: 连续失败次数 >= failure_threshold
    - OPEN → HALF_OPEN: 熔断时间 >= timeout_seconds
    - HALF_OPEN → CLOSED: 连续成功次数 >= success_threshold
    - HALF_OPEN → OPEN: 任何失败
    
    Requirements:
    - 4.1: THE Circuit_Breaker SHALL open after 5 consecutive failures
    - 4.2: WHEN Circuit_Breaker is open, THE DAML_RAG_System SHALL wait 60 seconds before half-open state
    - 4.3: THE Circuit_Breaker SHALL limit concurrent cache requests to 10 using semaphore
    - 4.4: WHEN Circuit_Breaker is open, THE DAML_RAG_System SHALL return cached fallback data
    """
    
    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitBreakerConfig] = None,
        failure_threshold: int = 5,
        timeout: int = 60,
        max_concurrent: int = 10
    ):
        """
        初始化熔断器
        
        Args:
            name: 熔断器名称（用于日志和监控）
            config: 熔断器配置（优先使用）
            failure_threshold: 失败阈值（当config为None时使用）
            timeout: 超时时间（秒）（当config为None时使用）
            max_concurrent: 最大并发数（当config为None时使用）
        """
        self.name = name
        
        # 使用配置或默认参数
        if config:
            self.config = config
        else:
            self.config = CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                timeout_seconds=timeout,
                max_concurrent_requests=max_concurrent
            )
        
        # 状态管理
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        
        # 并发控制 (Requirements 4.3)
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        # 线程安全锁
        self._lock = asyncio.Lock()
        
        # 指标收集
        self._metrics = CircuitBreakerMetrics()
        
        logger.info(
            f"🔌 CircuitBreaker '{name}' initialized: "
            f"failure_threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout_seconds}s, "
            f"max_concurrent={self.config.max_concurrent_requests}"
        )
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """是否处于关闭状态（正常工作）"""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """是否处于开启状态（熔断中）"""
        return self._state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """是否处于半开状态"""
        return self._state == CircuitState.HALF_OPEN
    
    @property
    def failure_count(self) -> int:
        """获取当前失败计数"""
        return self._failure_count
    
    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """获取指标"""
        return self._metrics
    
    async def _check_state_transition(self):
        """
        检查并执行状态转换
        
        状态转换规则 (Requirements 4.1, 4.2):
        - OPEN → HALF_OPEN: 当熔断时间超过timeout_seconds
        """
        if self._state == CircuitState.OPEN:
            # 检查是否应该进入半开状态 (Requirements 4.2)
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout_seconds:
                    await self._transition_to(CircuitState.HALF_OPEN)
                    logger.info(
                        f"🔄 CircuitBreaker '{self.name}': OPEN → HALF_OPEN "
                        f"(elapsed={elapsed:.1f}s >= timeout={self.config.timeout_seconds}s)"
                    )
    
    async def _transition_to(self, new_state: CircuitState):
        """
        转换到新状态
        
        Args:
            new_state: 新状态
        """
        old_state = self._state
        self._state = new_state
        
        # 重置计数器
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
        
        # 更新指标
        self._metrics.state_transitions += 1
        self._metrics.last_state_change_time = datetime.now()
        
        logger.info(f"🔄 CircuitBreaker '{self.name}': {old_state.value} → {new_state.value}")
    
    async def _record_success(self):
        """记录成功调用"""
        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.successful_calls += 1
            self._metrics.last_success_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                # 检查是否应该恢复到关闭状态
                if self._success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
                    logger.info(
                        f"✅ CircuitBreaker '{self.name}': 恢复正常 "
                        f"(连续成功={self._success_count})"
                    )
            elif self._state == CircuitState.CLOSED:
                # 关闭状态下成功，重置失败计数
                self._failure_count = 0
    
    async def _record_failure(self, error: Exception = None):
        """
        记录失败调用
        
        Args:
            error: 异常信息
        """
        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.failed_calls += 1
            self._metrics.last_failure_time = datetime.now()
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # 半开状态下失败，立即回到开启状态
                await self._transition_to(CircuitState.OPEN)
                logger.warning(
                    f"⚠️ CircuitBreaker '{self.name}': 半开状态失败，重新熔断 "
                    f"(error={error})"
                )
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                # 检查是否应该开启熔断 (Requirements 4.1)
                if self._failure_count >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)
                    logger.warning(
                        f"🔴 CircuitBreaker '{self.name}': 熔断开启 "
                        f"(连续失败={self._failure_count} >= 阈值={self.config.failure_threshold})"
                    )
    
    async def call(
        self,
        func: Callable[..., Any],
        *args,
        fallback: Optional[Callable[..., Any]] = None,
        **kwargs
    ) -> Any:
        """
        带熔断器保护的调用
        
        Args:
            func: 要调用的函数（同步或异步）
            *args: 函数参数
            fallback: 熔断时的回退函数（可选）
            **kwargs: 函数关键字参数
            
        Returns:
            函数返回值或回退值
            
        Raises:
            CircuitOpenException: 当熔断器开启且无回退函数时
        """
        # 检查状态转换
        await self._check_state_transition()
        
        # 检查熔断状态
        if self._state == CircuitState.OPEN:
            self._metrics.rejected_calls += 1
            
            # 如果有回退函数，使用回退 (Requirements 4.4)
            if fallback is not None:
                logger.debug(f"🔴 CircuitBreaker '{self.name}': 熔断中，使用回退函数")
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                else:
                    return fallback(*args, **kwargs)
            
            # 无回退函数，抛出异常
            raise CircuitOpenException(
                f"熔断器 '{self.name}' 已开启，请等待 {self.config.timeout_seconds} 秒后重试"
            )
        
        # 半开状态下限制调用次数
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                self._metrics.rejected_calls += 1
                if fallback is not None:
                    logger.debug(f"🟡 CircuitBreaker '{self.name}': 半开状态调用已满，使用回退函数")
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    else:
                        return fallback(*args, **kwargs)
                raise CircuitOpenException(
                    f"熔断器 '{self.name}' 半开状态调用已满，请稍后重试"
                )
            self._half_open_calls += 1
        
        # 使用Semaphore限制并发 (Requirements 4.3)
        async with self._semaphore:
            try:
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # 同步函数在executor中执行
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                
                # 记录成功
                await self._record_success()
                return result
                
            except Exception as e:
                # 记录失败
                await self._record_failure(e)
                raise
    
    def __call__(self, func: Callable) -> Callable:
        """
        装饰器模式使用熔断器
        
        Usage:
            @circuit_breaker
            async def my_function():
                ...
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    async def reset(self):
        """重置熔断器状态"""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            logger.info(f"🔄 CircuitBreaker '{self.name}': 已重置")
    
    async def force_open(self):
        """强制开启熔断器（用于测试或紧急情况）"""
        async with self._lock:
            await self._transition_to(CircuitState.OPEN)
            self._last_failure_time = time.time()
            logger.warning(f"🔴 CircuitBreaker '{self.name}': 强制开启熔断")
    
    async def force_close(self):
        """强制关闭熔断器（用于测试或紧急情况）"""
        async with self._lock:
            await self._transition_to(CircuitState.CLOSED)
            logger.info(f"🟢 CircuitBreaker '{self.name}': 强制关闭熔断")
    
    def get_status(self) -> dict:
        """获取熔断器状态"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout_seconds": self.config.timeout_seconds,
                "max_concurrent_requests": self.config.max_concurrent_requests,
                "success_threshold": self.config.success_threshold
            },
            "metrics": self._metrics.to_dict()
        }


class CircuitBreakerRegistry:
    """
    熔断器注册表
    
    管理多个熔断器实例，支持按名称获取
    """
    
    _instance: Optional['CircuitBreakerRegistry'] = None
    _breakers: dict = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._breakers = {}
        return cls._instance
    
    @classmethod
    def get_or_create(
        cls,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> CircuitBreaker:
        """
        获取或创建熔断器
        
        Args:
            name: 熔断器名称
            config: 熔断器配置
            **kwargs: 其他参数
            
        Returns:
            CircuitBreaker: 熔断器实例
        """
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name=name, config=config, **kwargs)
        return cls._breakers[name]
    
    @classmethod
    def get(cls, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return cls._breakers.get(name)
    
    @classmethod
    def remove(cls, name: str):
        """移除熔断器"""
        if name in cls._breakers:
            del cls._breakers[name]
    
    @classmethod
    def get_all_status(cls) -> dict:
        """获取所有熔断器状态"""
        return {
            name: breaker.get_status()
            for name, breaker in cls._breakers.items()
        }
    
    @classmethod
    async def reset_all(cls):
        """重置所有熔断器"""
        for breaker in cls._breakers.values():
            await breaker.reset()


# 预定义的熔断器实例（用于缓存系统）
user_profile_circuit_breaker = CircuitBreaker(
    name="user_profile",
    failure_threshold=5,
    timeout=60,
    max_concurrent=10
)

membership_circuit_breaker = CircuitBreaker(
    name="membership",
    failure_threshold=5,
    timeout=60,
    max_concurrent=10
)


# 导出
__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "CircuitBreakerRegistry",
    "CircuitState",
    "CircuitOpenException",
    "CircuitBreakerError",
    "user_profile_circuit_breaker",
    "membership_circuit_breaker"
]
