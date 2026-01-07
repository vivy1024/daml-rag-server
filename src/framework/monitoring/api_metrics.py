# -*- coding: utf-8 -*-
"""
API性能监控指标 - API Performance Metrics

提供Prometheus指标用于监控DAML-RAG API的性能。

核心指标：
1. request_duration_seconds: 请求耗时直方图
2. requests_total: 请求总数计数器（已存在，这里导入）
3. errors_total: 错误总数计数器
4. cache_hits_total: 缓存命中计数器
5. cache_misses_total: 缓存未命中计数器
6. active_connections: 活跃连接数
7. retrieval_duration_seconds: 检索耗时直方图
8. llm_call_duration_seconds: LLM调用耗时直方图

版本: v1.0.0
日期: 2025-12-24
"""

import logging
import time
from functools import wraps
from typing import Optional, Callable
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

# 缓存淘汰计数器
cache_evictions = Counter(
    'cache_evictions_total',
    'Total cache evictions',
    ['cache_type']
)

# 活跃连接数
active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# CPU使用率（模拟，实际应从系统获取）
cpu_usage = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

# 内存使用量
memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
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

# LLM Token使用计数器
llm_tokens = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['type']
)


# ========== 装饰器 ==========

def track_request_duration(endpoint: str, method: str = "POST"):
    """
    装饰器：追踪请求耗时
    
    Args:
        endpoint: API端点名称
        method: HTTP方法
    
    Usage:
        @track_request_duration("/api/chat", "POST")
        async def chat_endpoint():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                request_duration.labels(endpoint=endpoint, method=method).observe(duration)
                logger.debug(f"📊 请求耗时: {duration:.3f}s, endpoint={endpoint}")
        return wrapper
    return decorator


def track_retrieval_duration(layer: str, query_type: str = "default"):
    """
    装饰器：追踪检索耗时
    
    Args:
        layer: 检索层级 (vector/graph/constraint)
        query_type: 查询类型
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                retrieval_duration.labels(layer=layer, query_type=query_type).observe(duration)
                logger.debug(f"📊 检索耗时: {duration:.3f}s, layer={layer}")
        return wrapper
    return decorator


# ========== 辅助函数 ==========

def record_error(error_type: str, component: str):
    """
    记录错误
    
    Args:
        error_type: 错误类型 (timeout/validation/internal/etc.)
        component: 组件名称 (api/retrieval/llm/etc.)
    """
    errors_total.labels(error_type=error_type, component=component).inc()
    logger.debug(f"❌ 记录错误: type={error_type}, component={component}")


def record_cache_hit(cache_type: str, level: str = "L1"):
    """
    记录缓存命中
    
    Args:
        cache_type: 缓存类型 (user_profile/embedding/response/etc.)
        level: 缓存层级 (L1/L2/L3)
    """
    cache_hits.labels(cache_type=cache_type, level=level).inc()


def record_cache_miss(cache_type: str, level: str = "L1"):
    """
    记录缓存未命中
    
    Args:
        cache_type: 缓存类型
        level: 缓存层级
    """
    cache_misses.labels(cache_type=cache_type, level=level).inc()


def record_llm_call(backend: str, duration: float, success: bool, 
                    model: str = "default", call_type: str = "chat"):
    """
    记录LLM调用
    
    Args:
        backend: 后端名称 (deepseek/ollama/template)
        duration: 调用耗时（秒）
        success: 是否成功
        model: 模型名称
        call_type: 调用类型 (chat/completion/embedding)
    """
    llm_call_duration.labels(model=model, call_type=call_type, backend=backend).observe(duration)
    
    if success:
        llm_call_success.labels(backend=backend).inc()
    else:
        llm_call_failure.labels(backend=backend).inc()


def record_llm_tokens(prompt_tokens: int, completion_tokens: int):
    """
    记录LLM Token使用
    
    Args:
        prompt_tokens: 提示词Token数
        completion_tokens: 生成Token数
    """
    llm_tokens.labels(type="prompt").inc(prompt_tokens)
    llm_tokens.labels(type="completion").inc(completion_tokens)
    llm_tokens.labels(type="total").inc(prompt_tokens + completion_tokens)


def record_llm_fallback(from_backend: str, to_backend: str):
    """
    记录LLM降级事件
    
    Args:
        from_backend: 原后端
        to_backend: 降级后端
    """
    llm_fallback.labels(**{"from": from_backend, "to": to_backend}).inc()
    logger.warning(f"⚠️ LLM降级: {from_backend} → {to_backend}")


def update_system_metrics():
    """
    更新系统指标（CPU、内存）
    
    应该定期调用此函数更新系统资源指标
    """
    import psutil
    
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_usage.set(cpu_percent)
        
        # 内存使用量
        memory_info = psutil.Process().memory_info()
        memory_usage.set(memory_info.rss)
        
    except Exception as e:
        logger.warning(f"⚠️ 系统指标更新失败: {e}")


# 导出
__all__ = [
    # 指标
    "request_duration",
    "errors_total",
    "cache_hits",
    "cache_misses",
    "cache_evictions",
    "active_connections",
    "cpu_usage",
    "memory_usage",
    "retrieval_duration",
    "llm_call_duration",
    "llm_call_success",
    "llm_call_failure",
    "llm_fallback",
    "llm_tokens",
    # 装饰器
    "track_request_duration",
    "track_retrieval_duration",
    # 辅助函数
    "record_error",
    "record_cache_hit",
    "record_cache_miss",
    "record_llm_call",
    "record_llm_tokens",
    "record_llm_fallback",
    "update_system_metrics",
]
