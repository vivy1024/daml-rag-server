# -*- coding: utf-8 -*-
"""
监控模块 - Monitoring Module

提供完整的系统监控功能，包括：
1. 结构化日志
2. 指标收集
3. 性能监控
4. 告警系统
5. 工作流程监控

版本: v2.0.0
日期: 2025-12-16
作者: 薛小川
"""

# 结构化日志
from .structured_logger import (
    StructuredLogger,
    StructuredFormatter,
    set_trace_id,
    get_trace_id,
    clear_trace_id,
    with_trace_id,
    log_performance,
    get_logger
)

# 指标收集
from .metrics_collector import (
    MetricType,
    MetricValue,
    MetricSnapshot,
    Metric,
    Counter,
    Gauge,
    Histogram,
    Summary,
    MetricsCollector,
    get_metrics_collector
)

# 性能监控
from .performance_monitor import (
    ToolExecutionMetrics,
    DAGExecutionMetrics,
    LLMCallMetrics,
    CacheMetrics,
    PerformanceSnapshot,
    PerformanceMonitor,
    get_performance_monitor
)

# 工作流程监控
from .daml_workflow_monitor import (
    WorkflowStep,
    RetrievalLayer,
    StepMetrics,
    LayerMetrics,
    WorkflowSession,
    DAMLWorkflowMonitor
)

# 告警系统
from .alert_system import (
    AlertSeverity,
    AlertStatus,
    AlertRule,
    Alert,
    AlertSystem,
    get_alert_system
)

# 流式输出监控
from .streaming_metrics import (
    streaming_ttfb,
    streaming_duration,
    streaming_tokens_per_second,
    streaming_success,
    streaming_failure,
    StreamingSessionMetrics,
    record_streaming_metrics
)

# API性能监控（Prometheus指标）
from .api_metrics import (
    request_duration,
    errors_total,
    cache_hits,
    cache_misses,
    cache_evictions,
    active_connections,
    cpu_usage,
    memory_usage,
    retrieval_duration,
    llm_call_duration,
    llm_call_success,
    llm_call_failure,
    llm_fallback,
    llm_tokens,
    track_request_duration,
    track_retrieval_duration,
    record_error,
    record_cache_hit,
    record_cache_miss,
    record_llm_call,
    record_llm_tokens,
    record_llm_fallback,
    update_system_metrics
)

# 工作流性能监控（Prometheus指标）
from .workflow_metrics import (
    workflow_total_duration,
    workflow_step_duration,
    workflow_success_rate_gauge,
    workflow_success,
    workflow_failure,
    workflow_concurrent,
    workflow_bottleneck,
    connection_pool_active,
    connection_pool_idle,
    connection_pool_max_size,
    connection_pool_wait_time,
    connection_pool_health_check_failures,
    concurrency_limiter_active,
    concurrency_limiter_queued,
    concurrency_limiter_max,
    concurrency_limiter_queue_wait,
    http_requests,
    WORKFLOW_STEPS,
    WorkflowMetrics,
    track_workflow,
    track_step,
    record_workflow_complete,
    update_connection_pool_metrics,
    record_connection_wait,
    record_health_check_failure,
    update_concurrency_limiter_metrics,
    record_http_request
)

# Prometheus集成模块（便捷装饰器和辅助函数）
from .prometheus_integration import (
    track_api_request,
    track_workflow_step,
    track_retrieval,
    track_workflow_execution,
    track_llm_call_async,
    record_cache_operation,
    record_workflow_step,
    record_retrieval_operation,
    initialize_prometheus_metrics
)

__all__ = [
    # 结构化日志
    "StructuredLogger",
    "StructuredFormatter",
    "set_trace_id",
    "get_trace_id",
    "clear_trace_id",
    "with_trace_id",
    "log_performance",
    "get_logger",
    
    # 指标收集
    "MetricType",
    "MetricValue",
    "MetricSnapshot",
    "Metric",
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "MetricsCollector",
    "get_metrics_collector",
    
    # 性能监控
    "ToolExecutionMetrics",
    "DAGExecutionMetrics",
    "LLMCallMetrics",
    "CacheMetrics",
    "PerformanceSnapshot",
    "PerformanceMonitor",
    "get_performance_monitor",
    
    # 工作流程监控
    "WorkflowStep",
    "RetrievalLayer",
    "StepMetrics",
    "LayerMetrics",
    "WorkflowSession",
    "DAMLWorkflowMonitor",
    
    # 告警系统
    "AlertSeverity",
    "AlertStatus",
    "AlertRule",
    "Alert",
    "AlertSystem",
    "get_alert_system",
    
    # 流式输出监控（Prometheus）
    "streaming_ttfb",
    "streaming_duration",
    "streaming_tokens_per_second",
    "streaming_success",
    "streaming_failure",
    "StreamingSessionMetrics",
    "record_streaming_metrics",
    
    # API性能监控（Prometheus）
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
    "track_request_duration",
    "track_retrieval_duration",
    "record_error",
    "record_cache_hit",
    "record_cache_miss",
    "record_llm_call",
    "record_llm_tokens",
    "record_llm_fallback",
    "update_system_metrics",
    
    # 工作流性能监控（Prometheus）
    "workflow_total_duration",
    "workflow_step_duration",
    "workflow_success_rate_gauge",
    "workflow_success",
    "workflow_failure",
    "workflow_concurrent",
    "workflow_bottleneck",
    "connection_pool_active",
    "connection_pool_idle",
    "connection_pool_max_size",
    "connection_pool_wait_time",
    "connection_pool_health_check_failures",
    "concurrency_limiter_active",
    "concurrency_limiter_queued",
    "concurrency_limiter_max",
    "concurrency_limiter_queue_wait",
    "http_requests",
    "WORKFLOW_STEPS",
    "WorkflowMetrics",
    "track_workflow",
    "track_step",
    "record_workflow_complete",
    "update_connection_pool_metrics",
    "record_connection_wait",
    "record_health_check_failure",
    "update_concurrency_limiter_metrics",
    "record_http_request",
    
    # Prometheus集成模块
    "track_api_request",
    "track_workflow_step",
    "track_retrieval",
    "track_workflow_execution",
    "track_llm_call_async",
    "record_cache_operation",
    "record_workflow_step",
    "record_retrieval_operation",
    "initialize_prometheus_metrics"
]
