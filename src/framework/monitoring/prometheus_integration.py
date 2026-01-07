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

版本: v1.0.0
日期: 2025-12-24
"""

import logging
import time
import asyncio
from functools import wraps
from typing import Callable, Optional, Any
from contextlib import contextmanager, asynccontextmanager

# 导入Prometheus指标
from .api_metrics import (
    request_duration,
    errors_total,
    cache_hits,
    cache_misses,
    retrieval_duration,
    llm_call_duration,
    llm_call_success,
    llm_call_failure,
    llm_fallback,
    llm_tokens,
    record_error,
    record_cache_hit,
    record_cache_miss,
    record_llm_call,
    record_llm_tokens,
    record_llm_fallback,
    update_system_metrics
)

from .workflow_metrics import (
    workflow_total_duration,
    workflow_step_duration,
    workflow_success,
    workflow_failure,
    workflow_concurrent,
    workflow_bottleneck,
    record_workflow_complete,
    update_connection_pool_metrics,
    record_http_request,
    WORKFLOW_STEPS
)

logger = logging.getLogger(__name__)


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
