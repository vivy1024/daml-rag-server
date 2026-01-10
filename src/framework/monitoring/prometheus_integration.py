# -*- coding: utf-8 -*-
"""
Prometheus指标集成模块 - Prometheus Metrics Integration

将Prometheus指标集成到现有的监控系统中，
在不修改大量现有代码的情况下自动记录指标。

功能：
1. 自动记录API请求指标
2. 自动记录工作流步骤指标
3. 自动记录缓存操作指标
4. 自动记录LLM调用指标

版本: v2.0.0
日期: 2026-01-10
更新: 整合api_metrics模块的指标定义
"""

import logging
import time
import asyncio
import psutil
from functools import wraps
from typing import Callable, Optional, Any
from contextlib import contextmanager, asynccontextmanager
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)


# ========== Prometheus指标定义 ==========

# 请求耗时直方图（支持P50, P95, P99计算）
request_duration = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# 错误计数器
errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'component']
)

# 缓存命中计数器
cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type', 'level']
)

# 缓存未命中计数器
cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type', 'level']
)

# 检索耗时直方图
retrieval_duration = Histogram(
    'retrieval_duration_seconds',
    'Retrieval duration in seconds',
    ['layer', 'query_type'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# LLM调用耗时直方图
llm_call_duration = Histogram(
    'llm_call_duration_seconds',
    'LLM call duration in seconds',
    ['model', 'call_type', 'backend'],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0]
)

# LLM调用成功计数器
llm_call_success = Counter(
    'llm_call_success_total',
    'Total successful LLM calls',
    ['backend']
)

# LLM调用失败计数器
llm_call_failure = Counter(
    'llm_call_failure_total',
    'Total failed LLM calls',
    ['backend']
)

# LLM降级计数器
llm_fallback = Counter(
    'llm_fallback_total',
    'Total LLM fallback events',
    ['from', 'to']
)

# LLM令牌计数器
llm_tokens = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['type']  # prompt/completion
)

# 工作流步骤耗时
workflow_step_duration = Histogram(
    'workflow_step_duration_seconds',
    'Workflow step duration in seconds',
    ['step'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

# 工作流瓶颈计数器
workflow_bottleneck = Counter(
    'workflow_bottleneck_total',
    'Workflow bottleneck events',
    ['step', 'type']  # type: slow/error
)

# 工作流总耗时
workflow_total_duration = Histogram(
    'workflow_total_duration_seconds',
    'Total workflow duration in seconds',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# 工作流并发数
workflow_concurrent = Gauge(
    'workflow_concurrent',
    'Number of concurrent workflows'
)

# 工作流成功计数器
workflow_success = Counter(
    'workflow_success_total',
    'Total successful workflows'
)

# 工作流失败计数器
workflow_failure = Counter(
    'workflow_failure_total',
    'Total failed workflows'
)

# 连接池指标
connection_pool_active = Gauge(
    'connection_pool_active',
    'Active connections in pool',
    ['pool']
)

connection_pool_idle = Gauge(
    'connection_pool_idle',
    'Idle connections in pool',
    ['pool']
)

connection_pool_max = Gauge(
    'connection_pool_max',
    'Maximum connections in pool',
    ['pool']
)

# 系统指标
cpu_usage = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)


# ========== 辅助记录函数 ==========

def record_error(error_type: str, component: str):
    """记录错误"""
    errors_total.labels(error_type=error_type, component=component).inc()


def record_cache_hit(cache_type: str, level: str = "L1"):
    """记录缓存命中"""
    cache_hits.labels(cache_type=cache_type, level=level).inc()


def record_cache_miss(cache_type: str, level: str = "L1"):
    """记录缓存未命中"""
    cache_misses.labels(cache_type=cache_type, level=level).inc()


def record_llm_call(backend: str, duration: float, success: bool, model: str = "default", call_type: str = "chat"):
    """记录LLM调用"""
    llm_call_duration.labels(model=model, call_type=call_type, backend=backend).observe(duration)
    if success:
        llm_call_success.labels(backend=backend).inc()
    else:
        llm_call_failure.labels(backend=backend).inc()


def record_llm_tokens(prompt_tokens: int, completion_tokens: int):
    """记录LLM令牌使用"""
    llm_tokens.labels(type="prompt").inc(prompt_tokens)
    llm_tokens.labels(type="completion").inc(completion_tokens)


def record_llm_fallback(from_backend: str, to_backend: str):
    """记录LLM降级"""
    llm_fallback.labels(**{"from": from_backend, "to": to_backend}).inc()


def record_http_request(status_code: int):
    """记录HTTP请求（用于兼容性）"""
    pass  # 已由request_duration处理


def update_connection_pool_metrics(pool: str, active: int, idle: int, max_size: int):
    """更新连接池指标"""
    connection_pool_active.labels(pool=pool).set(active)
    connection_pool_idle.labels(pool=pool).set(idle)
    connection_pool_max.labels(pool=pool).set(max_size)


def update_system_metrics():
    """更新系统指标"""
    try:
        cpu_usage.set(psutil.cpu_percent())
        memory_usage.set(psutil.virtual_memory().used)
    except Exception as e:
        logger.warning(f"⚠️ 更新系统指标失败: {e}")


# ========== 装饰器 ==========

def track_api_request(endpoint: str, method: str = "POST"):
    """
    装饰器：追踪API请求（同时支持同步和异步函数）
    
    Args:
        endpoint: API端点名称
        method: HTTP方法
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                status_code = 200
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    status_code = 500
                    record_error("exception", "api")
                    raise
                finally:
                    duration = time.time() - start_time
                    request_duration.labels(endpoint=endpoint, method=method).observe(duration)
                    record_http_request(status_code)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                status_code = 200
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status_code = 500
                    record_error("exception", "api")
                    raise
                finally:
                    duration = time.time() - start_time
                    request_duration.labels(endpoint=endpoint, method=method).observe(duration)
                    record_http_request(status_code)
            return sync_wrapper
    return decorator


def track_workflow_step(step_name: str):
    """
    装饰器：追踪工作流步骤（同时支持同步和异步函数）
    
    Args:
        step_name: 步骤名称（如"步骤1-用户档案加载"）
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    workflow_step_duration.labels(step=step_name).observe(duration)
                    
                    # 检测瓶颈（超过5秒）
                    if duration > 5.0:
                        workflow_bottleneck.labels(step=step_name, type="slow").inc()
                        logger.warning(f"⚠️ 性能瓶颈: {step_name} 耗时 {duration:.2f}s")
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    workflow_step_duration.labels(step=step_name).observe(duration)
                    
                    if duration > 5.0:
                        workflow_bottleneck.labels(step=step_name, type="slow").inc()
            return sync_wrapper
    return decorator


def track_retrieval(layer: str, query_type: str = "default"):
    """
    装饰器：追踪检索操作
    
    Args:
        layer: 检索层级 (vector/graph/constraint)
        query_type: 查询类型
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    retrieval_duration.labels(layer=layer, query_type=query_type).observe(duration)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    retrieval_duration.labels(layer=layer, query_type=query_type).observe(duration)
            return sync_wrapper
    return decorator


# ========== 上下文管理器 ==========

@contextmanager
def track_workflow_execution():
    """
    上下文管理器：追踪完整工作流执行
    
    Usage:
        with track_workflow_execution() as tracker:
            # 执行工作流
            tracker.mark_success()
    """
    workflow_concurrent.inc()
    start_time = time.time()
    
    class WorkflowTracker:
        def __init__(self):
            self.success = False
            self.step_durations = {}
        
        def mark_success(self):
            self.success = True
        
        def record_step(self, step_name: str, duration: float):
            self.step_durations[step_name] = duration
            workflow_step_duration.labels(step=step_name).observe(duration)
    
    tracker = WorkflowTracker()
    
    try:
        yield tracker
    finally:
        workflow_concurrent.dec()
        duration = time.time() - start_time
        workflow_total_duration.observe(duration)
        
        if tracker.success:
            workflow_success.inc()
        else:
            workflow_failure.inc()


@asynccontextmanager
async def track_llm_call_async(backend: str, model: str = "default", call_type: str = "chat"):
    """
    异步上下文管理器：追踪LLM调用
    
    Args:
        backend: 后端名称 (deepseek/ollama/template)
        model: 模型名称
        call_type: 调用类型
    
    Usage:
        async with track_llm_call_async("deepseek", "deepseek-chat") as tracker:
            result = await llm.chat(...)
            tracker.set_tokens(prompt_tokens, completion_tokens)
            tracker.mark_success()
    """
    start_time = time.time()
    
    class LLMTracker:
        def __init__(self):
            self.success = False
            self.prompt_tokens = 0
            self.completion_tokens = 0
        
        def mark_success(self):
            self.success = True
        
        def set_tokens(self, prompt: int, completion: int):
            self.prompt_tokens = prompt
            self.completion_tokens = completion
    
    tracker = LLMTracker()
    
    try:
        yield tracker
    finally:
        duration = time.time() - start_time
        record_llm_call(backend, duration, tracker.success, model, call_type)
        
        if tracker.prompt_tokens > 0 or tracker.completion_tokens > 0:
            record_llm_tokens(tracker.prompt_tokens, tracker.completion_tokens)


# ========== 辅助函数 ==========

def record_cache_operation(cache_type: str, hit: bool, level: str = "L1"):
    """
    记录缓存操作
    
    Args:
        cache_type: 缓存类型 (user_profile/embedding/response/etc.)
        hit: 是否命中
        level: 缓存层级 (L1/L2/L3)
    """
    if hit:
        record_cache_hit(cache_type, level)
    else:
        record_cache_miss(cache_type, level)


def record_workflow_step(step_name: str, duration: float, success: bool = True):
    """
    记录工作流步骤
    
    Args:
        step_name: 步骤名称
        duration: 耗时（秒）
        success: 是否成功
    """
    workflow_step_duration.labels(step=step_name).observe(duration)
    
    if duration > 5.0:
        workflow_bottleneck.labels(step=step_name, type="slow").inc()
    
    if not success:
        workflow_bottleneck.labels(step=step_name, type="error").inc()


def record_retrieval_operation(layer: str, duration: float, query_type: str = "default"):
    """
    记录检索操作
    
    Args:
        layer: 检索层级
        duration: 耗时（秒）
        query_type: 查询类型
    """
    retrieval_duration.labels(layer=layer, query_type=query_type).observe(duration)


# ========== 初始化函数 ==========

_initialized = False

def initialize_prometheus_metrics():
    """
    初始化Prometheus指标
    
    在应用启动时调用一次，确保所有指标都被注册。
    """
    global _initialized
    if _initialized:
        return
    
    # 初始化系统指标
    try:
        update_system_metrics()
    except Exception as e:
        logger.warning(f"⚠️ 系统指标初始化失败: {e}")
    
    # 初始化连接池指标（默认值）
    for pool in ["mysql", "neo4j", "http"]:
        update_connection_pool_metrics(pool, 0, 0, 10)
    
    _initialized = True
    logger.info("✅ Prometheus指标初始化完成")


# 导出
__all__ = [
    # 装饰器
    "track_api_request",
    "track_workflow_step",
    "track_retrieval",
    # 上下文管理器
    "track_workflow_execution",
    "track_llm_call_async",
    # 辅助函数
    "record_cache_operation",
    "record_workflow_step",
    "record_retrieval_operation",
    "record_error",
    "record_llm_fallback",
    # 初始化
    "initialize_prometheus_metrics",
]
