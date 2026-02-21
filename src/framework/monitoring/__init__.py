# -*- coding: utf-8 -*-
"""
监控模块 - Monitoring Module

简化后的监控系统，只保留支持API接口所需的核心功能。

保留的5个核心模块：
1. structured_logger.py - 结构化日志记录
2. metrics_collector.py - 指标收集和管理
3. streaming_metrics.py - 流式会话监控
4. prometheus_integration.py - Prometheus格式导出
5. concurrency_limiter.py - 并发控制和限流

已删除的8个模块（共172KB）：
- performance_monitor.py (68KB) - 功能被metrics_collector覆盖
- daml_workflow_monitor.py (26KB) - 未使用
- dag_visualizer.py (23KB) - 可视化由前端负责
- alert_system.py (16KB) - 告警功能不需要
- enhanced_logging.py (13KB) - 功能重复
- workflow_metrics.py (11KB) - 未使用
- step_performance.py (9KB) - 未使用
- api_metrics.py (8KB) - 功能被metrics_collector覆盖

版本: v3.0.0 - 监控层简化版
日期: 2026-01-10
作者: 薛小川
"""

# 1. 结构化日志
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

# 2. 指标收集（已废弃：请使用 prometheus_integration 中的官方 prometheus_client 指标）
# DEPRECATED: metrics_collector 自定义实现将在未来版本移除。
# 请改用 prometheus_integration.py 中的 request_duration、errors_total 等官方指标。
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

# 3. 流式输出监控
from .streaming_metrics import (
    streaming_ttfb,
    streaming_duration,
    streaming_tokens_per_second,
    streaming_success,
    streaming_failure,
    StreamingSessionMetrics,
    record_streaming_metrics
)

# 4. Prometheus集成
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

# 5. 并发限制器
from .concurrency_limiter import (
    UserTier,
    TierConfig,
    ConnectionInfo,
    ConcurrencyLimiter
)

__version__ = "3.0.0"
__author__ = "薛小川"
__date__ = "2026-01-10"

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__date__",
    
    # 1. 结构化日志
    "StructuredLogger",
    "StructuredFormatter",
    "set_trace_id",
    "get_trace_id",
    "clear_trace_id",
    "with_trace_id",
    "log_performance",
    "get_logger",
    
    # 2. 指标收集
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
    
    # 3. 流式输出监控
    "streaming_ttfb",
    "streaming_duration",
    "streaming_tokens_per_second",
    "streaming_success",
    "streaming_failure",
    "StreamingSessionMetrics",
    "record_streaming_metrics",
    
    # 4. Prometheus集成
    "track_api_request",
    "track_workflow_step",
    "track_retrieval",
    "track_workflow_execution",
    "track_llm_call_async",
    "record_cache_operation",
    "record_workflow_step",
    "record_retrieval_operation",
    "initialize_prometheus_metrics",
    
    # 5. 并发限制器
    "UserTier",
    "TierConfig",
    "ConnectionInfo",
    "ConcurrencyLimiter",
]
