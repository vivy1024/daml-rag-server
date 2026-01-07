# -*- coding: utf-8 -*-
"""
工作流性能监控指标 - Workflow Performance Metrics

提供Prometheus指标用于监控11步DAML-RAG工作流的性能。

核心指标：
1. workflow_total_duration_seconds: 工作流总耗时
2. workflow_step_duration_seconds: 步骤级别耗时
3. workflow_success_rate: 工作流成功率
4. workflow_concurrent_requests: 并发请求数
5. workflow_bottleneck_total: 性能瓶颈计数

版本: v1.0.0
日期: 2025-12-24
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)


# ========== Prometheus指标定义 ==========

# 工作流总耗时直方图
workflow_total_duration = Histogram(
    'workflow_total_duration_seconds',
    'Total workflow duration in seconds',
    buckets=[1, 5, 10, 15, 20, 30, 45, 60, 90, 120]
)

# 步骤级别耗时直方图
workflow_step_duration = Histogram(
    'workflow_step_duration_seconds',
    'Workflow step duration in seconds',
    ['step'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
)

# 工作流成功率（Gauge，实时计算）
workflow_success_rate_gauge = Gauge(
    'workflow_success_rate',
    'Workflow success rate (0-1)'
)

# 工作流成功计数
workflow_success = Counter(
    'workflow_success_total',
    'Total successful workflows'
)

# 工作流失败计数
workflow_failure = Counter(
    'workflow_failure_total',
    'Total failed workflows'
)

# 并发请求数
workflow_concurrent = Gauge(
    'workflow_concurrent_requests',
    'Number of concurrent workflow requests'
)

# 性能瓶颈计数
workflow_bottleneck = Counter(
    'workflow_bottleneck_total',
    'Total performance bottlenecks detected',
    ['step', 'type']
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

connection_pool_max_size = Gauge(
    'connection_pool_max_size',
    'Maximum pool size',
    ['pool']
)

connection_pool_wait_time = Histogram(
    'connection_pool_wait_time_seconds',
    'Time waiting for connection from pool',
    ['pool'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

connection_pool_health_check_failures = Counter(
    'connection_pool_health_check_failures_total',
    'Total health check failures',
    ['pool']
)

# 并发限流指标
concurrency_limiter_active = Gauge(
    'concurrency_limiter_active_requests',
    'Active requests in concurrency limiter'
)

concurrency_limiter_queued = Gauge(
    'concurrency_limiter_queued_requests',
    'Queued requests in concurrency limiter'
)

concurrency_limiter_max = Gauge(
    'concurrency_limiter_max_concurrent',
    'Maximum concurrent requests allowed'
)

concurrency_limiter_queue_wait = Gauge(
    'concurrency_limiter_queue_wait_time_seconds',
    'Average queue wait time'
)

# HTTP请求计数（用于429错误率）
http_requests = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['status']
)


# ========== 11步工作流步骤定义 ==========

WORKFLOW_STEPS = {
    1: "步骤1-用户档案加载",
    2: "步骤2-会话记录存储",
    3: "步骤3-会员权限检查",
    4: "步骤4-BGE复杂度分类",
    5: "步骤5-智能模型选择",
    6: "步骤6-Few-Shot检索",
    6.5: "步骤6.5-LLM选择DAG方案",
    7: "步骤7-DAG编排执行",
    8: "步骤8-三层检索",
    9: "步骤9-工具结果汇总",
    10: "步骤10-LLM深度分析",
    11: "步骤11-记录交互",
}


# ========== 数据类定义 ==========

@dataclass
class WorkflowMetrics:
    """
    工作流指标数据类
    
    记录单个工作流执行的完整性能指标。
    """
    workflow_id: str
    user_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    step_durations: Dict[str, float] = field(default_factory=dict)
    success: bool = False
    error_message: Optional[str] = None
    bottlenecks: List[str] = field(default_factory=list)
    
    @property
    def total_duration(self) -> Optional[float]:
        """总耗时（秒）"""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    def record_step(self, step: str, duration: float):
        """记录步骤耗时"""
        self.step_durations[step] = duration
        
        # 检测瓶颈（超过5秒的步骤）
        if duration > 5.0:
            self.bottlenecks.append(f"{step}: {duration:.2f}s")


# ========== 上下文管理器 ==========

@contextmanager
def track_workflow():
    """
    上下文管理器：追踪工作流执行
    
    Usage:
        with track_workflow() as tracker:
            # 执行工作流
            tracker.success = True
    """
    workflow_concurrent.inc()
    start_time = time.time()
    
    class WorkflowTracker:
        def __init__(self):
            self.success = False
            self.step_durations = {}
        
        def record_step(self, step: str, duration: float):
            self.step_durations[step] = duration
            workflow_step_duration.labels(step=step).observe(duration)
            
            # 检测瓶颈
            if duration > 5.0:
                workflow_bottleneck.labels(step=step, type="slow").inc()
    
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
        
        # 更新成功率
        _update_success_rate()
        
        logger.debug(f"📊 工作流完成: duration={duration:.2f}s, success={tracker.success}")


@contextmanager
def track_step(step_name: str):
    """
    上下文管理器：追踪单个步骤
    
    Args:
        step_name: 步骤名称
    
    Usage:
        with track_step("步骤7-DAG编排执行"):
            # 执行步骤
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        workflow_step_duration.labels(step=step_name).observe(duration)
        
        # 检测瓶颈
        if duration > 5.0:
            workflow_bottleneck.labels(step=step_name, type="slow").inc()
            logger.warning(f"⚠️ 性能瓶颈: {step_name} 耗时 {duration:.2f}s")


# ========== 辅助函数 ==========

# 内部计数器用于计算成功率
_success_count = 0
_total_count = 0


def _update_success_rate():
    """更新成功率指标"""
    global _success_count, _total_count
    
    # 从Counter获取当前值（近似）
    # 注意：这是简化实现，生产环境应使用更精确的方法
    try:
        success = workflow_success._value.get()
        failure = workflow_failure._value.get()
        total = success + failure
        
        if total > 0:
            rate = success / total
            workflow_success_rate_gauge.set(rate)
    except Exception:
        pass


def record_workflow_complete(success: bool, duration: float, step_durations: Dict[str, float] = None):
    """
    记录工作流完成
    
    Args:
        success: 是否成功
        duration: 总耗时
        step_durations: 各步骤耗时字典
    """
    workflow_total_duration.observe(duration)
    
    if success:
        workflow_success.inc()
    else:
        workflow_failure.inc()
    
    # 记录步骤耗时
    if step_durations:
        for step, step_duration in step_durations.items():
            workflow_step_duration.labels(step=step).observe(step_duration)
            
            # 检测瓶颈
            if step_duration > 5.0:
                workflow_bottleneck.labels(step=step, type="slow").inc()
    
    _update_success_rate()


def update_connection_pool_metrics(pool_name: str, active: int, idle: int, max_size: int):
    """
    更新连接池指标
    
    Args:
        pool_name: 连接池名称 (mysql/neo4j/http)
        active: 活跃连接数
        idle: 空闲连接数
        max_size: 最大连接数
    """
    connection_pool_active.labels(pool=pool_name).set(active)
    connection_pool_idle.labels(pool=pool_name).set(idle)
    connection_pool_max_size.labels(pool=pool_name).set(max_size)


def record_connection_wait(pool_name: str, wait_time: float):
    """
    记录连接等待时间
    
    Args:
        pool_name: 连接池名称
        wait_time: 等待时间（秒）
    """
    connection_pool_wait_time.labels(pool=pool_name).observe(wait_time)


def record_health_check_failure(pool_name: str):
    """
    记录健康检查失败
    
    Args:
        pool_name: 连接池名称
    """
    connection_pool_health_check_failures.labels(pool=pool_name).inc()


def update_concurrency_limiter_metrics(active: int, queued: int, max_concurrent: int, avg_wait: float = 0):
    """
    更新并发限流指标
    
    Args:
        active: 活跃请求数
        queued: 队列中请求数
        max_concurrent: 最大并发数
        avg_wait: 平均等待时间
    """
    concurrency_limiter_active.set(active)
    concurrency_limiter_queued.set(queued)
    concurrency_limiter_max.set(max_concurrent)
    concurrency_limiter_queue_wait.set(avg_wait)


def record_http_request(status_code: int):
    """
    记录HTTP请求
    
    Args:
        status_code: HTTP状态码
    """
    http_requests.labels(status=str(status_code)).inc()


# 导出
__all__ = [
    # 指标
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
    # 常量
    "WORKFLOW_STEPS",
    # 数据类
    "WorkflowMetrics",
    # 上下文管理器
    "track_workflow",
    "track_step",
    # 辅助函数
    "record_workflow_complete",
    "update_connection_pool_metrics",
    "record_connection_wait",
    "record_health_check_failure",
    "update_concurrency_limiter_metrics",
    "record_http_request",
]
