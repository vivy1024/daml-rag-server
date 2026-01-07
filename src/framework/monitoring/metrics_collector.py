# -*- coding: utf-8 -*-
"""
指标收集系统 - Metrics Collector

收集系统性能指标，包括：
1. 延迟指标（latency）
2. 吞吐量指标（throughput）
3. 错误率指标（error_rate）
4. 资源使用指标（resource_usage）
5. 业务指标（business_metrics）

版本: v1.0.0
日期: 2025-12-16
作者: 薛小川
"""

import time
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import statistics


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"  # 计数器（只增不减）
    GAUGE = "gauge"  # 仪表（可增可减）
    HISTOGRAM = "histogram"  # 直方图（分布统计）
    SUMMARY = "summary"  # 摘要（百分位数）


@dataclass
class MetricValue:
    """指标值"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSnapshot:
    """指标快照"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Metric:
    """基础指标类"""
    
    def __init__(
        self,
        name: str,
        metric_type: MetricType,
        description: str = "",
        labels: Optional[List[str]] = None
    ):
        """
        初始化指标
        
        Args:
            name: 指标名称
            metric_type: 指标类型
            description: 指标描述
            labels: 标签列表
        """
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.label_names = labels or []
        self.values: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
    
    def _make_key(self, labels: Dict[str, str]) -> str:
        """生成标签键"""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    def record(self, value: float, labels: Optional[Dict[str, str]] = None):
        """
        记录指标值
        
        Args:
            value: 指标值
            labels: 标签
        """
        labels = labels or {}
        key = self._make_key(labels)
        
        metric_value = MetricValue(
            timestamp=time.time(),
            value=value,
            labels=labels
        )
        
        self.values[key].append(metric_value)
    
    def get_current_value(self, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """
        获取当前值
        
        Args:
            labels: 标签
            
        Returns:
            Optional[float]: 当前值
        """
        key = self._make_key(labels or {})
        values = self.values.get(key)
        
        if not values:
            return None
        
        return values[-1].value
    
    def get_snapshot(self, labels: Optional[Dict[str, str]] = None) -> Optional[MetricSnapshot]:
        """
        获取指标快照
        
        Args:
            labels: 标签
            
        Returns:
            Optional[MetricSnapshot]: 指标快照
        """
        current_value = self.get_current_value(labels)
        
        if current_value is None:
            return None
        
        return MetricSnapshot(
            name=self.name,
            metric_type=self.metric_type,
            value=current_value,
            timestamp=time.time(),
            labels=labels or {},
            metadata={"description": self.description}
        )


class Counter(Metric):
    """计数器指标（只增不减）"""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        super().__init__(name, MetricType.COUNTER, description, labels)
        self.counts: Dict[str, float] = defaultdict(float)
    
    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """
        增加计数
        
        Args:
            amount: 增加量
            labels: 标签
        """
        key = self._make_key(labels or {})
        self.counts[key] += amount
        self.record(self.counts[key], labels)
    
    def get_count(self, labels: Optional[Dict[str, str]] = None) -> float:
        """
        获取计数
        
        Args:
            labels: 标签
            
        Returns:
            float: 计数值
        """
        key = self._make_key(labels or {})
        return self.counts.get(key, 0.0)


class Gauge(Metric):
    """仪表指标（可增可减）"""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        super().__init__(name, MetricType.GAUGE, description, labels)
        self.gauges: Dict[str, float] = defaultdict(float)
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """
        设置值
        
        Args:
            value: 值
            labels: 标签
        """
        key = self._make_key(labels or {})
        self.gauges[key] = value
        self.record(value, labels)
    
    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """
        增加值
        
        Args:
            amount: 增加量
            labels: 标签
        """
        key = self._make_key(labels or {})
        self.gauges[key] += amount
        self.record(self.gauges[key], labels)
    
    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """
        减少值
        
        Args:
            amount: 减少量
            labels: 标签
        """
        key = self._make_key(labels or {})
        self.gauges[key] -= amount
        self.record(self.gauges[key], labels)
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """
        获取值
        
        Args:
            labels: 标签
            
        Returns:
            float: 值
        """
        key = self._make_key(labels or {})
        return self.gauges.get(key, 0.0)


class Histogram(Metric):
    """直方图指标（分布统计）"""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None
    ):
        super().__init__(name, MetricType.HISTOGRAM, description, labels)
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.observations: Dict[str, List[float]] = defaultdict(list)
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """
        观察值
        
        Args:
            value: 观察值
            labels: 标签
        """
        key = self._make_key(labels or {})
        self.observations[key].append(value)
        self.record(value, labels)
    
    def get_statistics(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            labels: 标签
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        key = self._make_key(labels or {})
        observations = self.observations.get(key, [])
        
        if not observations:
            return {
                "count": 0,
                "sum": 0.0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0
            }
        
        sorted_obs = sorted(observations)
        count = len(observations)
        
        return {
            "count": count,
            "sum": sum(observations),
            "min": min(observations),
            "max": max(observations),
            "mean": statistics.mean(observations),
            "median": statistics.median(observations),
            "p50": sorted_obs[int(count * 0.50)],
            "p95": sorted_obs[int(count * 0.95)] if count > 1 else sorted_obs[0],
            "p99": sorted_obs[int(count * 0.99)] if count > 1 else sorted_obs[0]
        }


class Summary(Metric):
    """摘要指标（百分位数）"""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        max_age_seconds: int = 600
    ):
        super().__init__(name, MetricType.SUMMARY, description, labels)
        self.max_age = max_age_seconds
        self.observations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """
        观察值
        
        Args:
            value: 观察值
            labels: 标签
        """
        key = self._make_key(labels or {})
        self.observations[key].append((time.time(), value))
        self.record(value, labels)
    
    def get_quantiles(
        self,
        quantiles: List[float],
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[float, float]:
        """
        获取分位数
        
        Args:
            quantiles: 分位数列表（0-1）
            labels: 标签
            
        Returns:
            Dict[float, float]: 分位数映射
        """
        key = self._make_key(labels or {})
        observations = self.observations.get(key, deque())
        
        # 过滤过期数据
        current_time = time.time()
        cutoff_time = current_time - self.max_age
        valid_observations = [
            value for timestamp, value in observations
            if timestamp >= cutoff_time
        ]
        
        if not valid_observations:
            return {q: 0.0 for q in quantiles}
        
        sorted_obs = sorted(valid_observations)
        count = len(sorted_obs)
        
        result = {}
        for q in quantiles:
            index = int(count * q)
            index = min(index, count - 1)
            result[q] = sorted_obs[index]
        
        return result


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        """初始化指标收集器"""
        self.metrics: Dict[str, Metric] = {}
        
        # 预定义核心指标
        self._register_core_metrics()
    
    def _register_core_metrics(self):
        """注册核心指标"""
        # 延迟指标
        self.register_histogram(
            "request_duration_seconds",
            "请求处理时间（秒）",
            labels=["endpoint", "method", "status"]
        )
        
        self.register_histogram(
            "retrieval_duration_seconds",
            "检索耗时（秒）",
            labels=["layer", "query_type"]
        )
        
        self.register_histogram(
            "llm_call_duration_seconds",
            "LLM调用耗时（秒）",
            labels=["model", "call_type"]
        )
        
        # 吞吐量指标
        self.register_counter(
            "requests_total",
            "请求总数",
            labels=["endpoint", "method", "status"]
        )
        
        self.register_counter(
            "retrieval_requests_total",
            "检索请求总数",
            labels=["layer", "success"]
        )
        
        # 错误率指标
        self.register_counter(
            "errors_total",
            "错误总数",
            labels=["error_type", "component"]
        )
        
        self.register_gauge(
            "error_rate",
            "错误率",
            labels=["component"]
        )
        
        # 资源使用指标
        self.register_gauge(
            "cpu_usage_percent",
            "CPU使用率（%）"
        )
        
        self.register_gauge(
            "memory_usage_bytes",
            "内存使用量（字节）"
        )
        
        self.register_gauge(
            "active_connections",
            "活跃连接数"
        )
        
        # 业务指标
        self.register_counter(
            "cache_hits_total",
            "缓存命中总数",
            labels=["cache_type"]
        )
        
        self.register_counter(
            "cache_misses_total",
            "缓存未命中总数",
            labels=["cache_type"]
        )
        
        self.register_gauge(
            "cache_hit_rate",
            "缓存命中率",
            labels=["cache_type"]
        )
    
    def register_counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None
    ) -> Counter:
        """
        注册计数器
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            
        Returns:
            Counter: 计数器
        """
        if name in self.metrics:
            return self.metrics[name]
        
        counter = Counter(name, description, labels)
        self.metrics[name] = counter
        return counter
    
    def register_gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None
    ) -> Gauge:
        """
        注册仪表
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            
        Returns:
            Gauge: 仪表
        """
        if name in self.metrics:
            return self.metrics[name]
        
        gauge = Gauge(name, description, labels)
        self.metrics[name] = gauge
        return gauge
    
    def register_histogram(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None
    ) -> Histogram:
        """
        注册直方图
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            buckets: 桶边界
            
        Returns:
            Histogram: 直方图
        """
        if name in self.metrics:
            return self.metrics[name]
        
        histogram = Histogram(name, description, labels, buckets)
        self.metrics[name] = histogram
        return histogram
    
    def register_summary(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        max_age_seconds: int = 600
    ) -> Summary:
        """
        注册摘要
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            max_age_seconds: 最大保留时间（秒）
            
        Returns:
            Summary: 摘要
        """
        if name in self.metrics:
            return self.metrics[name]
        
        summary = Summary(name, description, labels, max_age_seconds)
        self.metrics[name] = summary
        return summary
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """
        获取指标
        
        Args:
            name: 指标名称
            
        Returns:
            Optional[Metric]: 指标对象
        """
        return self.metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Metric]:
        """
        获取所有指标
        
        Returns:
            Dict[str, Metric]: 所有指标
        """
        return self.metrics.copy()
    
    def get_snapshots(self) -> List[MetricSnapshot]:
        """
        获取所有指标快照
        
        Returns:
            List[MetricSnapshot]: 指标快照列表
        """
        snapshots = []
        
        for metric in self.metrics.values():
            snapshot = metric.get_snapshot()
            if snapshot:
                snapshots.append(snapshot)
        
        return snapshots
    
    def export_prometheus(self) -> str:
        """
        导出Prometheus格式指标
        
        Returns:
            str: Prometheus格式文本
        """
        lines = []
        
        for metric in self.metrics.values():
            # HELP行
            lines.append(f"# HELP {metric.name} {metric.description}")
            
            # TYPE行
            type_map = {
                MetricType.COUNTER: "counter",
                MetricType.GAUGE: "gauge",
                MetricType.HISTOGRAM: "histogram",
                MetricType.SUMMARY: "summary"
            }
            lines.append(f"# TYPE {metric.name} {type_map[metric.metric_type]}")
            
            # 指标值
            if isinstance(metric, (Counter, Gauge)):
                for key, value in metric.values.items():
                    if value:
                        latest = value[-1]
                        label_str = ""
                        if latest.labels:
                            label_pairs = [f'{k}="{v}"' for k, v in latest.labels.items()]
                            label_str = "{" + ",".join(label_pairs) + "}"
                        lines.append(f"{metric.name}{label_str} {latest.value}")
            
            lines.append("")  # 空行分隔
        
        return "\n".join(lines)


# 全局指标收集器实例
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    获取全局指标收集器
    
    Returns:
        MetricsCollector: 指标收集器
    """
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector


# 导出
__all__ = [
    "MetricType",
    "MetricValue",
    "MetricSnapshot",
    "Metric",
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "MetricsCollector",
    "get_metrics_collector"
]
