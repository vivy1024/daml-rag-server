# -*- coding: utf-8 -*-
"""
性能监控系统 v2.0 - 工作流性能监控和Prometheus集成

提供全面的性能监控和统计功能，包括：
1. 工作流级别的性能监控
2. 步骤级别的性能记录
3. 性能瓶颈检测（阈值1000ms）
4. Prometheus指标导出
5. DAG执行性能监控
6. LLM调用统计
7. 缓存命中率统计
8. 工具执行时间分析
9. 性能趋势分析

版本: v2.0.0
日期: 2025-12-21
"""

import logging
import time
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
from contextlib import contextmanager
import statistics

logger = logging.getLogger(__name__)

# ========== Prometheus指标集成 ==========
# 延迟导入，避免循环依赖
_prometheus_metrics_initialized = False

def _sync_to_prometheus(step_name: str, duration_seconds: float, success: bool, is_bottleneck: bool = False):
    """
    同步步骤指标到Prometheus
    
    Args:
        step_name: 步骤名称
        duration_seconds: 耗时（秒）
        success: 是否成功
        is_bottleneck: 是否为性能瓶颈
    """
    global _prometheus_metrics_initialized
    try:
        from .workflow_metrics import (
            workflow_step_duration,
            workflow_bottleneck
        )
        
        # 记录步骤耗时
        workflow_step_duration.labels(step=step_name).observe(duration_seconds)
        
        # 记录性能瓶颈
        if is_bottleneck:
            workflow_bottleneck.labels(step=step_name, type="slow").inc()
        
        if not success:
            workflow_bottleneck.labels(step=step_name, type="error").inc()
            
        _prometheus_metrics_initialized = True
        
    except Exception as e:
        if not _prometheus_metrics_initialized:
            logger.debug(f"Prometheus指标同步跳过（首次）: {e}")
        else:
            logger.warning(f"Prometheus指标同步失败: {e}")


def _sync_workflow_to_prometheus(duration_seconds: float, success: bool):
    """
    同步工作流完成指标到Prometheus
    
    Args:
        duration_seconds: 总耗时（秒）
        success: 是否成功
    """
    try:
        from .workflow_metrics import (
            workflow_total_duration,
            workflow_success,
            workflow_failure,
            workflow_concurrent
        )
        
        # 记录总耗时
        workflow_total_duration.observe(duration_seconds)
        
        # 记录成功/失败
        if success:
            workflow_success.inc()
        else:
            workflow_failure.inc()
            
    except Exception as e:
        logger.debug(f"Prometheus工作流指标同步失败: {e}")


@dataclass
class WorkflowContext:
    """工作流上下文"""
    request_id: str
    user_id: str
    start_time: float
    steps: List['StepRecord'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_duration_ms(self) -> float:
        """获取当前持续时间（毫秒）"""
        return (time.time() - self.start_time) * 1000


@dataclass
class StepRecord:
    """步骤记录"""
    step_number: int
    step_name: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class PerformanceBottleneck:
    """性能瓶颈"""
    request_id: str
    step_number: int
    step_name: str
    duration_ms: float
    threshold_ms: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionMetrics:
    """工具执行指标"""
    tool_name: str
    execution_id: str
    user_id: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error_message: Optional[str] = None
    cache_hit: bool = False
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DAGExecutionMetrics:
    """DAG执行指标"""
    execution_id: str
    template_id: str
    template_name: str
    user_id: str
    start_time: float
    end_time: float
    total_duration: float
    tools_executed: int
    tools_succeeded: int
    tools_failed: int
    tools_cached: int
    parallel_groups: int
    max_parallel_degree: int
    cache_hit_rate: float
    success_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMCallMetrics:
    """LLM调用指标"""
    call_id: str
    call_type: str  # "decision" or "analysis"
    model_name: str
    user_id: str
    start_time: float
    end_time: float
    duration: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    success: bool
    error_message: Optional[str] = None
    confidence: float = 0.0
    fallback_used: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheMetrics:
    """缓存指标"""
    timestamp: float
    hits: int
    misses: int
    hit_rate: float
    preloads: int
    evictions: int
    total_size: int
    memory_cache_size: int
    tool_specific_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)


@dataclass
class PerformanceSnapshot:
    """性能快照"""
    timestamp: float
    period_seconds: int
    dag_executions: int
    avg_dag_duration: float
    llm_calls: int
    avg_llm_duration: float
    cache_hit_rate: float
    success_rate: float
    top_tools: List[Tuple[str, int]]
    top_errors: List[Tuple[str, int]]


class PerformanceMonitor:
    """性能监控系统"""
    
    # 类型特定的性能阈值（毫秒）- Requirements 6.3
    TYPE_SPECIFIC_THRESHOLDS = {
        "user_profile": 2000,      # 用户档案阈值 2000ms
        "membership": 3000,        # 会员权限阈值 3000ms
        "llm": 5000,               # LLM调用阈值 5000ms
        "preload_user_profile": 2000,  # 预加载用户档案
        "check_membership": 3000,      # 检查会员权限
        "llm_decision": 5000,          # LLM决策
        "llm_analysis": 5000,          # LLM分析
        "default": 1000            # 默认阈值 1000ms
    }
    
    def __init__(self, max_history_size: int = 1000, bottleneck_threshold_ms: float = 1000.0):
        """
        初始化性能监控系统
        
        Args:
            max_history_size: 最大历史记录数量
            bottleneck_threshold_ms: 默认性能瓶颈阈值（毫秒）
        """
        self.max_history_size = max_history_size
        self.bottleneck_threshold_ms = bottleneck_threshold_ms
        
        # 类型特定阈值（可动态配置）
        self.type_thresholds = dict(self.TYPE_SPECIFIC_THRESHOLDS)
        
        # 工作流上下文（活跃的工作流）
        self.active_workflows: Dict[str, WorkflowContext] = {}
        
        # 完成的工作流历史
        self.completed_workflows: deque = deque(maxlen=max_history_size)
        
        # 性能瓶颈历史
        self.bottlenecks: deque = deque(maxlen=max_history_size)
        
        # 工具执行历史
        self.tool_executions: deque = deque(maxlen=max_history_size)
        
        # DAG执行历史
        self.dag_executions: deque = deque(maxlen=max_history_size)
        
        # LLM调用历史
        self.llm_calls: deque = deque(maxlen=max_history_size)
        
        # 缓存指标历史
        self.cache_metrics_history: deque = deque(maxlen=100)
        
        # 实时统计
        self.tool_stats = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        })
        
        self.llm_stats = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration": 0.0,
            "total_tokens": 0,
            "fallback_count": 0
        })
        
        # 错误统计
        self.error_counts = defaultdict(int)
        
        # 新增：操作统计（用于measure上下文管理器）
        self._operation_stats: Dict[str, List[float]] = {}
        self._active_timers: Dict[str, Dict[str, Any]] = {}
        
        # Prometheus指标
        self.prometheus_metrics = {
            "workflow_total_duration_seconds": [],
            "workflow_step_duration_seconds": defaultdict(list),
            "workflow_success_total": 0,
            "workflow_failure_total": 0,
            "workflow_bottleneck_total": 0,
            "workflow_concurrent_requests": 0,
            # 缓存指标 - Requirements 6.1, 6.2
            "cache_hits_total": defaultdict(int),      # 按cache_type分类的命中计数
            "cache_misses_total": defaultdict(int),    # 按cache_type分类的未命中计数
            "cache_response_time_seconds": defaultdict(list),  # 按cache_type分类的响应时间直方图
        }
        
        # 缓存类型列表
        self.cache_types = ["user_profile", "membership", "few_shot", "query_analysis"]
        
        logger.info("✅ 性能监控系统初始化完成（v2.0）")
    
    # ========== 阈值管理 ==========
    
    def get_threshold_for_step(self, step_name: str) -> float:
        """
        获取步骤的性能阈值
        
        根据步骤名称返回对应的阈值，支持类型特定阈值。
        
        Args:
            step_name: 步骤名称
            
        Returns:
            float: 阈值（毫秒）
        """
        # 直接匹配步骤名称
        if step_name in self.type_thresholds:
            return self.type_thresholds[step_name]
        
        # 模糊匹配类型
        step_lower = step_name.lower()
        if "user_profile" in step_lower or "preload_user" in step_lower:
            return self.type_thresholds.get("user_profile", self.bottleneck_threshold_ms)
        elif "membership" in step_lower:
            return self.type_thresholds.get("membership", self.bottleneck_threshold_ms)
        elif "llm" in step_lower or "decision" in step_lower or "analysis" in step_lower:
            return self.type_thresholds.get("llm", self.bottleneck_threshold_ms)
        
        # 返回默认阈值
        return self.type_thresholds.get("default", self.bottleneck_threshold_ms)
    
    def set_threshold(self, step_type: str, threshold_ms: float):
        """
        设置类型特定的阈值
        
        Args:
            step_type: 步骤类型（user_profile, membership, llm, default等）
            threshold_ms: 阈值（毫秒）
        """
        self.type_thresholds[step_type] = threshold_ms
        logger.info(f"📊 设置阈值: {step_type} = {threshold_ms}ms")
    
    def get_all_thresholds(self) -> Dict[str, float]:
        """
        获取所有阈值配置
        
        Returns:
            Dict[str, float]: 阈值配置字典
        """
        return dict(self.type_thresholds)
    
    # ========== 工作流监控 ==========
    
    def start_workflow(self, request_id: Optional[str] = None, user_id: str = "unknown") -> WorkflowContext:
        """
        开始工作流监控
        
        Args:
            request_id: 请求ID（可选，不提供则自动生成）
            user_id: 用户ID
            
        Returns:
            WorkflowContext: 工作流上下文
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        context = WorkflowContext(
            request_id=request_id,
            user_id=user_id,
            start_time=time.time()
        )
        
        self.active_workflows[request_id] = context
        self.prometheus_metrics["workflow_concurrent_requests"] = len(self.active_workflows)
        
        logger.debug(f"📊 开始工作流监控: {request_id}")
        return context
    
    def record_step(
        self,
        context: WorkflowContext,
        step_number: int,
        step_name: str,
        duration_ms: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        记录步骤性能
        
        Args:
            context: 工作流上下文
            step_number: 步骤编号
            step_name: 步骤名称
            duration_ms: 持续时间（毫秒）
            success: 是否成功
            metadata: 元数据
            error: 错误信息
        """
        current_time = time.time()
        
        step_record = StepRecord(
            step_number=step_number,
            step_name=step_name,
            start_time=current_time - (duration_ms / 1000),
            end_time=current_time,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {},
            error=error
        )
        
        context.steps.append(step_record)
        
        # 记录内部Prometheus指标
        self.prometheus_metrics["workflow_step_duration_seconds"][step_name].append(duration_ms / 1000)
        
        # 检测性能瓶颈 - 使用类型特定阈值
        threshold_ms = self.get_threshold_for_step(step_name)
        is_bottleneck = duration_ms > threshold_ms
        if is_bottleneck:
            bottleneck = PerformanceBottleneck(
                request_id=context.request_id,
                step_number=step_number,
                step_name=step_name,
                duration_ms=duration_ms,
                threshold_ms=threshold_ms,
                timestamp=current_time,
                metadata=metadata or {}
            )
            self.bottlenecks.append(bottleneck)
            self.prometheus_metrics["workflow_bottleneck_total"] += 1
            
            logger.warning(
                f"⚠️ 性能瓶颈检测: 步骤{step_number} {step_name} "
                f"耗时 {duration_ms:.0f}ms (阈值: {threshold_ms:.0f}ms)"
            )
        
        # ✅ 新增：同步到真正的Prometheus指标
        _sync_to_prometheus(
            step_name=step_name,
            duration_seconds=duration_ms / 1000,
            success=success,
            is_bottleneck=is_bottleneck
        )
        
        logger.debug(
            f"📊 记录步骤: {step_number}. {step_name}, "
            f"耗时: {duration_ms:.0f}ms, 成功: {success}"
        )
    
    def finish_workflow(
        self,
        context: WorkflowContext,
        success: bool,
        total_duration_ms: Optional[float] = None
    ):
        """
        完成工作流监控
        
        Args:
            context: 工作流上下文
            success: 是否成功
            total_duration_ms: 总持续时间（毫秒），不提供则自动计算
        """
        if total_duration_ms is None:
            total_duration_ms = context.get_duration_ms()
        
        # 从活跃列表移除
        if context.request_id in self.active_workflows:
            del self.active_workflows[context.request_id]
        
        # 添加到完成历史
        context.metadata["success"] = success
        context.metadata["total_duration_ms"] = total_duration_ms
        self.completed_workflows.append(context)
        
        # 更新内部Prometheus指标
        self.prometheus_metrics["workflow_total_duration_seconds"].append(total_duration_ms / 1000)
        if success:
            self.prometheus_metrics["workflow_success_total"] += 1
        else:
            self.prometheus_metrics["workflow_failure_total"] += 1
        
        self.prometheus_metrics["workflow_concurrent_requests"] = len(self.active_workflows)
        
        # ✅ 新增：同步到真正的Prometheus指标
        _sync_workflow_to_prometheus(
            duration_seconds=total_duration_ms / 1000,
            success=success
        )
        
        logger.info(
            f"✅ 工作流完成: {context.request_id}, "
            f"总耗时: {total_duration_ms:.0f}ms, "
            f"步骤数: {len(context.steps)}, "
            f"成功: {success}"
        )
    
    def get_bottlenecks(
        self,
        threshold_ms: Optional[float] = None,
        time_window_seconds: Optional[int] = None
    ) -> List[PerformanceBottleneck]:
        """
        获取性能瓶颈
        
        Args:
            threshold_ms: 阈值（毫秒），不提供则使用默认阈值
            time_window_seconds: 时间窗口（秒）
            
        Returns:
            List[PerformanceBottleneck]: 性能瓶颈列表
        """
        if threshold_ms is None:
            threshold_ms = self.bottleneck_threshold_ms
        
        bottlenecks = list(self.bottlenecks)
        
        # 过滤阈值
        bottlenecks = [b for b in bottlenecks if b.duration_ms >= threshold_ms]
        
        # 过滤时间窗口
        if time_window_seconds:
            cutoff_time = time.time() - time_window_seconds
            bottlenecks = [b for b in bottlenecks if b.timestamp >= cutoff_time]
        
        # 按持续时间降序排序
        bottlenecks.sort(key=lambda b: b.duration_ms, reverse=True)
        
        return bottlenecks
    
    def export_metrics(self, format: str = "prometheus") -> str:
        """
        导出Prometheus指标
        
        Args:
            format: 导出格式（prometheus或json）
            
        Returns:
            str: 导出的指标
        """
        if format == "prometheus":
            return self._export_prometheus_metrics()
        elif format == "json":
            return self._export_json_metrics()
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    def _export_prometheus_metrics(self) -> str:
        """导出Prometheus格式的指标"""
        lines = []
        
        # 工作流总耗时
        if self.prometheus_metrics["workflow_total_duration_seconds"]:
            durations = self.prometheus_metrics["workflow_total_duration_seconds"]
            lines.append("# HELP workflow_total_duration_seconds 工作流总耗时（秒）")
            lines.append("# TYPE workflow_total_duration_seconds histogram")
            lines.append(f"workflow_total_duration_seconds_sum {sum(durations)}")
            lines.append(f"workflow_total_duration_seconds_count {len(durations)}")
            
            # 计算分位数
            if durations:
                sorted_durations = sorted(durations)
                lines.append(f'workflow_total_duration_seconds{{quantile="0.5"}} {self._calculate_percentile(sorted_durations, 0.5)}')
                lines.append(f'workflow_total_duration_seconds{{quantile="0.9"}} {self._calculate_percentile(sorted_durations, 0.9)}')
                lines.append(f'workflow_total_duration_seconds{{quantile="0.95"}} {self._calculate_percentile(sorted_durations, 0.95)}')
                lines.append(f'workflow_total_duration_seconds{{quantile="0.99"}} {self._calculate_percentile(sorted_durations, 0.99)}')
        
        # 步骤耗时
        for step_name, durations in self.prometheus_metrics["workflow_step_duration_seconds"].items():
            if durations:
                lines.append(f"# HELP workflow_step_duration_seconds 步骤耗时（秒）")
                lines.append(f"# TYPE workflow_step_duration_seconds histogram")
                lines.append(f'workflow_step_duration_seconds_sum{{step="{step_name}"}} {sum(durations)}')
                lines.append(f'workflow_step_duration_seconds_count{{step="{step_name}"}} {len(durations)}')
        
        # 成功率
        lines.append("# HELP workflow_success_total 工作流成功总数")
        lines.append("# TYPE workflow_success_total counter")
        lines.append(f"workflow_success_total {self.prometheus_metrics['workflow_success_total']}")
        
        lines.append("# HELP workflow_failure_total 工作流失败总数")
        lines.append("# TYPE workflow_failure_total counter")
        lines.append(f"workflow_failure_total {self.prometheus_metrics['workflow_failure_total']}")
        
        # 成功率计算
        total = self.prometheus_metrics['workflow_success_total'] + self.prometheus_metrics['workflow_failure_total']
        success_rate = self.prometheus_metrics['workflow_success_total'] / total if total > 0 else 0.0
        lines.append("# HELP workflow_success_rate 工作流成功率")
        lines.append("# TYPE workflow_success_rate gauge")
        lines.append(f"workflow_success_rate {success_rate}")
        
        # 性能瓶颈
        lines.append("# HELP workflow_bottleneck_total 性能瓶颈总数")
        lines.append("# TYPE workflow_bottleneck_total counter")
        lines.append(f"workflow_bottleneck_total {self.prometheus_metrics['workflow_bottleneck_total']}")
        
        # 并发请求数
        lines.append("# HELP workflow_concurrent_requests 当前并发请求数")
        lines.append("# TYPE workflow_concurrent_requests gauge")
        lines.append(f"workflow_concurrent_requests {self.prometheus_metrics['workflow_concurrent_requests']}")
        
        # 缓存命中计数 - Requirements 6.1
        lines.append("")
        lines.append("# HELP cache_hits_total 缓存命中总数")
        lines.append("# TYPE cache_hits_total counter")
        for cache_type, count in self.prometheus_metrics["cache_hits_total"].items():
            lines.append(f'cache_hits_total{{cache_type="{cache_type}"}} {count}')
        
        # 缓存未命中计数 - Requirements 6.1
        lines.append("")
        lines.append("# HELP cache_misses_total 缓存未命中总数")
        lines.append("# TYPE cache_misses_total counter")
        for cache_type, count in self.prometheus_metrics["cache_misses_total"].items():
            lines.append(f'cache_misses_total{{cache_type="{cache_type}"}} {count}')
        
        # 缓存响应时间直方图 - Requirements 6.2
        lines.append("")
        lines.append("# HELP cache_response_time_seconds 缓存响应时间（秒）")
        lines.append("# TYPE cache_response_time_seconds histogram")
        for cache_type, response_times in self.prometheus_metrics["cache_response_time_seconds"].items():
            if response_times:
                lines.append(f'cache_response_time_seconds_sum{{cache_type="{cache_type}"}} {sum(response_times)}')
                lines.append(f'cache_response_time_seconds_count{{cache_type="{cache_type}"}} {len(response_times)}')
                sorted_times = sorted(response_times)
                lines.append(f'cache_response_time_seconds{{cache_type="{cache_type}",quantile="0.5"}} {self._calculate_percentile(sorted_times, 0.5)}')
                lines.append(f'cache_response_time_seconds{{cache_type="{cache_type}",quantile="0.95"}} {self._calculate_percentile(sorted_times, 0.95)}')
                lines.append(f'cache_response_time_seconds{{cache_type="{cache_type}",quantile="0.99"}} {self._calculate_percentile(sorted_times, 0.99)}')
        
        return "\n".join(lines)
    
    def _export_json_metrics(self) -> str:
        """导出JSON格式的指标"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "workflow": {
                "total_completed": len(self.completed_workflows),
                "total_success": self.prometheus_metrics["workflow_success_total"],
                "total_failure": self.prometheus_metrics["workflow_failure_total"],
                "success_rate": (
                    self.prometheus_metrics["workflow_success_total"] / 
                    (self.prometheus_metrics["workflow_success_total"] + self.prometheus_metrics["workflow_failure_total"])
                    if (self.prometheus_metrics["workflow_success_total"] + self.prometheus_metrics["workflow_failure_total"]) > 0
                    else 0.0
                ),
                "concurrent_requests": self.prometheus_metrics["workflow_concurrent_requests"],
                "bottleneck_count": self.prometheus_metrics["workflow_bottleneck_total"]
            },
            "duration": {
                "total_workflows": len(self.prometheus_metrics["workflow_total_duration_seconds"]),
                "avg_duration_seconds": (
                    statistics.mean(self.prometheus_metrics["workflow_total_duration_seconds"])
                    if self.prometheus_metrics["workflow_total_duration_seconds"] else 0.0
                ),
                "p50_duration_seconds": (
                    self._calculate_percentile(self.prometheus_metrics["workflow_total_duration_seconds"], 0.5)
                    if self.prometheus_metrics["workflow_total_duration_seconds"] else 0.0
                ),
                "p95_duration_seconds": (
                    self._calculate_percentile(self.prometheus_metrics["workflow_total_duration_seconds"], 0.95)
                    if self.prometheus_metrics["workflow_total_duration_seconds"] else 0.0
                ),
                "p99_duration_seconds": (
                    self._calculate_percentile(self.prometheus_metrics["workflow_total_duration_seconds"], 0.99)
                    if self.prometheus_metrics["workflow_total_duration_seconds"] else 0.0
                )
            },
            "steps": {}
        }
        
        # 步骤统计
        for step_name, durations in self.prometheus_metrics["workflow_step_duration_seconds"].items():
            if durations:
                metrics["steps"][step_name] = {
                    "count": len(durations),
                    "avg_duration_seconds": statistics.mean(durations),
                    "p95_duration_seconds": self._calculate_percentile(durations, 0.95)
                }
        
        return json.dumps(metrics, indent=2, ensure_ascii=False)
    
    def get_workflow_summary(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流摘要
        
        Args:
            request_id: 请求ID
            
        Returns:
            Optional[Dict[str, Any]]: 工作流摘要
        """
        # 查找工作流
        workflow = None
        for w in self.completed_workflows:
            if w.request_id == request_id:
                workflow = w
                break
        
        if workflow is None:
            # 检查活跃工作流
            if request_id in self.active_workflows:
                workflow = self.active_workflows[request_id]
            else:
                return None
        
        # 生成摘要
        total_duration_ms = workflow.metadata.get("total_duration_ms", workflow.get_duration_ms())
        
        summary = {
            "request_id": workflow.request_id,
            "user_id": workflow.user_id,
            "start_time": datetime.fromtimestamp(workflow.start_time).isoformat(),
            "total_duration_ms": total_duration_ms,
            "total_steps": len(workflow.steps),
            "success": workflow.metadata.get("success", None),
            "steps": []
        }
        
        # 步骤详情
        for step in workflow.steps:
            step_threshold = self.get_threshold_for_step(step.step_name)
            summary["steps"].append({
                "step_number": step.step_number,
                "step_name": step.step_name,
                "duration_ms": step.duration_ms,
                "success": step.success,
                "is_bottleneck": step.duration_ms > step_threshold,
                "threshold_ms": step_threshold,
                "error": step.error
            })
        
        # 性能瓶颈
        bottlenecks = [
            {
                "step_number": step.step_number,
                "step_name": step.step_name,
                "duration_ms": step.duration_ms,
                "threshold_ms": self.get_threshold_for_step(step.step_name)
            }
            for step in workflow.steps
            if step.duration_ms > self.get_threshold_for_step(step.step_name)
        ]
        
        summary["bottlenecks"] = bottlenecks
        summary["bottleneck_count"] = len(bottlenecks)
        
        return summary
    
    # ========== 操作性能监控（上下文管理器）==========
    
    @contextmanager
    def measure(self, operation: str):
        """
        性能测量上下文管理器
        
        Args:
            operation: 操作名称
            
        Usage:
            with performance_monitor.measure("database_query"):
                result = await db.query(...)
        """
        timer_id = str(uuid.uuid4())
        start_time = time.time()
        
        # 记录开始
        self._active_timers[timer_id] = {
            "operation": operation,
            "start_time": start_time
        }
        
        try:
            yield timer_id
        finally:
            # 记录结束
            end_time = time.time()
            duration = end_time - start_time
            
            # 存储到统计数据
            if operation not in self._operation_stats:
                self._operation_stats[operation] = []
            
            self._operation_stats[operation].append(duration)
            
            # 保留最近1000次记录
            if len(self._operation_stats[operation]) > 1000:
                self._operation_stats[operation] = self._operation_stats[operation][-1000:]
            
            # 清理活跃计时器
            if timer_id in self._active_timers:
                del self._active_timers[timer_id]
            
            logger.debug(f"📊 操作完成: {operation}, 耗时: {duration*1000:.2f}ms")
    
    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """
        获取操作统计数据
        
        Args:
            operation: 操作名称
            
        Returns:
            Dict[str, Any]: 统计数据
                - operation: 操作名称
                - count: 操作执行次数
                - avg: 平均持续时间（秒）
                - min: 最小持续时间（秒）
                - max: 最大持续时间（秒）
                - median: 中位数持续时间（秒）
                - p95: 95百分位持续时间（秒）
                - p99: 99百分位持续时间（秒）
        """
        if operation not in self._operation_stats:
            return {
                "operation": operation,
                "count": 0,
                "message": "没有找到该操作的统计数据"
            }
        
        durations = self._operation_stats[operation]
        
        return {
            "operation": operation,
            "count": len(durations),
            "avg": statistics.mean(durations),
            "min": min(durations),
            "max": max(durations),
            "median": statistics.median(durations),
            "p95": self._calculate_percentile(durations, 0.95),
            "p99": self._calculate_percentile(durations, 0.99)
        }
    
    # ========== 工具执行监控 ==========
    
    def record_tool_execution(self, metrics: ToolExecutionMetrics):
        """
        记录工具执行指标
        
        Args:
            metrics: 工具执行指标
        """
        # 添加到历史记录
        self.tool_executions.append(metrics)
        
        # 更新实时统计
        stats = self.tool_stats[metrics.tool_name]
        stats["total_calls"] += 1
        
        if metrics.success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
            if metrics.error_message:
                self.error_counts[metrics.error_message] += 1
        
        stats["total_duration"] += metrics.duration
        
        if metrics.cache_hit:
            stats["cache_hits"] += 1
        else:
            stats["cache_misses"] += 1
        
        logger.debug(
            f"📊 记录工具执行: {metrics.tool_name}, "
            f"耗时: {metrics.duration:.2f}s, "
            f"成功: {metrics.success}"
        )
    
    def get_tool_statistics(
        self,
        tool_name: Optional[str] = None,
        time_window_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取工具统计信息
        
        Args:
            tool_name: 工具名称（可选，不指定则返回所有工具）
            time_window_seconds: 时间窗口（秒）
            
        Returns:
            Dict[str, Any]: 工具统计信息
        """
        # 过滤时间窗口
        if time_window_seconds:
            cutoff_time = time.time() - time_window_seconds
            filtered_executions = [
                m for m in self.tool_executions
                if m.start_time >= cutoff_time
            ]
        else:
            filtered_executions = list(self.tool_executions)
        
        # 过滤工具名称
        if tool_name:
            filtered_executions = [
                m for m in filtered_executions
                if m.tool_name == tool_name
            ]
        
        if not filtered_executions:
            return {
                "tool_name": tool_name,
                "total_calls": 0,
                "message": "没有找到匹配的执行记录"
            }
        
        # 计算统计
        total_calls = len(filtered_executions)
        successful_calls = sum(1 for m in filtered_executions if m.success)
        failed_calls = total_calls - successful_calls
        cache_hits = sum(1 for m in filtered_executions if m.cache_hit)
        
        durations = [m.duration for m in filtered_executions]
        
        return {
            "tool_name": tool_name or "all",
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0.0,
            "cache_hits": cache_hits,
            "cache_misses": total_calls - cache_hits,
            "cache_hit_rate": cache_hits / total_calls if total_calls > 0 else 0.0,
            "duration_stats": {
                "min": min(durations) if durations else 0.0,
                "max": max(durations) if durations else 0.0,
                "avg": statistics.mean(durations) if durations else 0.0,
                "median": statistics.median(durations) if durations else 0.0,
                "p95": self._calculate_percentile(durations, 0.95) if durations else 0.0,
                "p99": self._calculate_percentile(durations, 0.99) if durations else 0.0
            },
            "time_window_seconds": time_window_seconds
        }
    
    # ========== DAG执行监控 ==========
    
    def record_dag_execution(self, metrics: DAGExecutionMetrics):
        """
        记录DAG执行指标
        
        Args:
            metrics: DAG执行指标
        """
        self.dag_executions.append(metrics)
        
        logger.debug(
            f"📊 记录DAG执行: {metrics.template_name}, "
            f"耗时: {metrics.total_duration:.2f}s, "
            f"成功率: {metrics.success_rate:.1%}"
        )
    
    def get_dag_statistics(
        self,
        template_id: Optional[str] = None,
        time_window_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取DAG统计信息
        
        Args:
            template_id: 模板ID（可选）
            time_window_seconds: 时间窗口（秒）
            
        Returns:
            Dict[str, Any]: DAG统计信息
        """
        # 过滤时间窗口
        if time_window_seconds:
            cutoff_time = time.time() - time_window_seconds
            filtered_executions = [
                m for m in self.dag_executions
                if m.start_time >= cutoff_time
            ]
        else:
            filtered_executions = list(self.dag_executions)
        
        # 过滤模板ID
        if template_id:
            filtered_executions = [
                m for m in filtered_executions
                if m.template_id == template_id
            ]
        
        if not filtered_executions:
            return {
                "template_id": template_id,
                "total_executions": 0,
                "message": "没有找到匹配的执行记录"
            }
        
        # 计算统计
        total_executions = len(filtered_executions)
        durations = [m.total_duration for m in filtered_executions]
        success_rates = [m.success_rate for m in filtered_executions]
        cache_hit_rates = [m.cache_hit_rate for m in filtered_executions]
        
        return {
            "template_id": template_id or "all",
            "total_executions": total_executions,
            "duration_stats": {
                "min": min(durations) if durations else 0.0,
                "max": max(durations) if durations else 0.0,
                "avg": statistics.mean(durations) if durations else 0.0,
                "median": statistics.median(durations) if durations else 0.0,
                "p95": self._calculate_percentile(durations, 0.95) if durations else 0.0
            },
            "success_rate": {
                "avg": statistics.mean(success_rates) if success_rates else 0.0,
                "min": min(success_rates) if success_rates else 0.0,
                "max": max(success_rates) if success_rates else 0.0
            },
            "cache_hit_rate": {
                "avg": statistics.mean(cache_hit_rates) if cache_hit_rates else 0.0,
                "min": min(cache_hit_rates) if cache_hit_rates else 0.0,
                "max": max(cache_hit_rates) if cache_hit_rates else 0.0
            },
            "avg_tools_executed": statistics.mean([m.tools_executed for m in filtered_executions]) if filtered_executions else 0.0,
            "avg_parallel_groups": statistics.mean([m.parallel_groups for m in filtered_executions]) if filtered_executions else 0.0,
            "time_window_seconds": time_window_seconds
        }
    
    # ========== LLM调用监控 ==========
    
    def record_llm_call(self, metrics: LLMCallMetrics):
        """
        记录LLM调用指标
        
        Args:
            metrics: LLM调用指标
        """
        self.llm_calls.append(metrics)
        
        # 更新实时统计
        stats = self.llm_stats[metrics.call_type]
        stats["total_calls"] += 1
        
        if metrics.success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        stats["total_duration"] += metrics.duration
        stats["total_tokens"] += metrics.total_tokens
        
        if metrics.fallback_used:
            stats["fallback_count"] += 1
        
        logger.debug(
            f"📊 记录LLM调用: {metrics.call_type}, "
            f"耗时: {metrics.duration:.2f}s, "
            f"tokens: {metrics.total_tokens}"
        )
    
    def get_llm_statistics(
        self,
        call_type: Optional[str] = None,
        time_window_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取LLM统计信息
        
        Args:
            call_type: 调用类型（可选）
            time_window_seconds: 时间窗口（秒）
            
        Returns:
            Dict[str, Any]: LLM统计信息
        """
        # 过滤时间窗口
        if time_window_seconds:
            cutoff_time = time.time() - time_window_seconds
            filtered_calls = [
                m for m in self.llm_calls
                if m.start_time >= cutoff_time
            ]
        else:
            filtered_calls = list(self.llm_calls)
        
        # 过滤调用类型
        if call_type:
            filtered_calls = [
                m for m in filtered_calls
                if m.call_type == call_type
            ]
        
        if not filtered_calls:
            return {
                "call_type": call_type,
                "total_calls": 0,
                "message": "没有找到匹配的调用记录"
            }
        
        # 计算统计
        total_calls = len(filtered_calls)
        successful_calls = sum(1 for m in filtered_calls if m.success)
        fallback_calls = sum(1 for m in filtered_calls if m.fallback_used)
        
        durations = [m.duration for m in filtered_calls]
        total_tokens = sum(m.total_tokens for m in filtered_calls)
        prompt_tokens = sum(m.prompt_tokens for m in filtered_calls)
        completion_tokens = sum(m.completion_tokens for m in filtered_calls)
        
        return {
            "call_type": call_type or "all",
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": total_calls - successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0.0,
            "fallback_calls": fallback_calls,
            "fallback_rate": fallback_calls / total_calls if total_calls > 0 else 0.0,
            "duration_stats": {
                "min": min(durations) if durations else 0.0,
                "max": max(durations) if durations else 0.0,
                "avg": statistics.mean(durations) if durations else 0.0,
                "median": statistics.median(durations) if durations else 0.0,
                "p95": self._calculate_percentile(durations, 0.95) if durations else 0.0
            },
            "token_stats": {
                "total_tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "avg_tokens_per_call": total_tokens / total_calls if total_calls > 0 else 0.0
            },
            "time_window_seconds": time_window_seconds
        }
    
    # ========== 缓存监控 ==========
    
    def record_cache_access(
        self,
        cache_type: str,
        hit: bool,
        response_time_seconds: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录缓存访问 - Requirements 6.1, 6.2
        
        Args:
            cache_type: 缓存类型（user_profile, membership, few_shot, query_analysis）
            hit: 是否命中
            response_time_seconds: 响应时间（秒）
            metadata: 额外元数据
        """
        # 更新命中/未命中计数
        if hit:
            self.prometheus_metrics["cache_hits_total"][cache_type] += 1
        else:
            self.prometheus_metrics["cache_misses_total"][cache_type] += 1
        
        # 记录响应时间
        self.prometheus_metrics["cache_response_time_seconds"][cache_type].append(response_time_seconds)
        
        # 保留最近1000次记录
        if len(self.prometheus_metrics["cache_response_time_seconds"][cache_type]) > 1000:
            self.prometheus_metrics["cache_response_time_seconds"][cache_type] = \
                self.prometheus_metrics["cache_response_time_seconds"][cache_type][-1000:]
        
        logger.debug(
            f"📊 缓存访问: {cache_type}, 命中={hit}, 响应时间={response_time_seconds*1000:.2f}ms"
        )
    
    def get_cache_hit_rate(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """
        获取缓存命中率
        
        Args:
            cache_type: 缓存类型（可选，不指定则返回所有类型）
            
        Returns:
            Dict[str, Any]: 缓存命中率统计
        """
        if cache_type:
            hits = self.prometheus_metrics["cache_hits_total"].get(cache_type, 0)
            misses = self.prometheus_metrics["cache_misses_total"].get(cache_type, 0)
            total = hits + misses
            hit_rate = hits / total if total > 0 else 0.0
            
            response_times = self.prometheus_metrics["cache_response_time_seconds"].get(cache_type, [])
            
            return {
                "cache_type": cache_type,
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": hit_rate,
                "response_time_stats": {
                    "avg": statistics.mean(response_times) if response_times else 0.0,
                    "min": min(response_times) if response_times else 0.0,
                    "max": max(response_times) if response_times else 0.0,
                    "p50": self._calculate_percentile(response_times, 0.5) if response_times else 0.0,
                    "p95": self._calculate_percentile(response_times, 0.95) if response_times else 0.0,
                    "p99": self._calculate_percentile(response_times, 0.99) if response_times else 0.0
                }
            }
        else:
            # 返回所有缓存类型的统计
            all_stats = {}
            total_hits = 0
            total_misses = 0
            
            for ct in self.cache_types:
                stats = self.get_cache_hit_rate(ct)
                all_stats[ct] = stats
                total_hits += stats["hits"]
                total_misses += stats["misses"]
            
            total = total_hits + total_misses
            overall_hit_rate = total_hits / total if total > 0 else 0.0
            
            return {
                "overall": {
                    "total_hits": total_hits,
                    "total_misses": total_misses,
                    "total_requests": total,
                    "hit_rate": overall_hit_rate
                },
                "by_type": all_stats
            }
    
    def record_cache_metrics(self, metrics: CacheMetrics):
        """
        记录缓存指标
        
        Args:
            metrics: 缓存指标
        """
        self.cache_metrics_history.append(metrics)
        
        logger.debug(
            f"📊 记录缓存指标: 命中率={metrics.hit_rate:.1%}, "
            f"预加载={metrics.preloads}, 淘汰={metrics.evictions}"
        )
    
    def get_cache_statistics(
        self,
        time_window_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Args:
            time_window_seconds: 时间窗口（秒）
            
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        # 过滤时间窗口
        if time_window_seconds:
            cutoff_time = time.time() - time_window_seconds
            filtered_metrics = [
                m for m in self.cache_metrics_history
                if m.timestamp >= cutoff_time
            ]
        else:
            filtered_metrics = list(self.cache_metrics_history)
        
        if not filtered_metrics:
            return {
                "message": "没有缓存指标记录"
            }
        
        # 获取最新指标
        latest_metrics = filtered_metrics[-1]
        
        # 计算趋势
        hit_rates = [m.hit_rate for m in filtered_metrics]
        
        return {
            "current": {
                "hits": latest_metrics.hits,
                "misses": latest_metrics.misses,
                "hit_rate": latest_metrics.hit_rate,
                "preloads": latest_metrics.preloads,
                "evictions": latest_metrics.evictions,
                "total_size": latest_metrics.total_size,
                "memory_cache_size": latest_metrics.memory_cache_size
            },
            "trends": {
                "avg_hit_rate": statistics.mean(hit_rates) if hit_rates else 0.0,
                "min_hit_rate": min(hit_rates) if hit_rates else 0.0,
                "max_hit_rate": max(hit_rates) if hit_rates else 0.0,
                "total_preloads": sum(m.preloads for m in filtered_metrics),
                "total_evictions": sum(m.evictions for m in filtered_metrics)
            },
            "tool_specific": latest_metrics.tool_specific_stats,
            "time_window_seconds": time_window_seconds
        }
    
    # ========== 综合统计和分析 ==========
    
    def get_performance_snapshot(
        self,
        time_window_seconds: int = 3600
    ) -> PerformanceSnapshot:
        """
        获取性能快照
        
        Args:
            time_window_seconds: 时间窗口（秒），默认1小时
            
        Returns:
            PerformanceSnapshot: 性能快照
        """
        cutoff_time = time.time() - time_window_seconds
        
        # 过滤DAG执行
        recent_dag_executions = [
            m for m in self.dag_executions
            if m.start_time >= cutoff_time
        ]
        
        # 过滤LLM调用
        recent_llm_calls = [
            m for m in self.llm_calls
            if m.start_time >= cutoff_time
        ]
        
        # 过滤工具执行
        recent_tool_executions = [
            m for m in self.tool_executions
            if m.start_time >= cutoff_time
        ]
        
        # 计算平均DAG执行时间
        avg_dag_duration = (
            statistics.mean([m.total_duration for m in recent_dag_executions])
            if recent_dag_executions else 0.0
        )
        
        # 计算平均LLM调用时间
        avg_llm_duration = (
            statistics.mean([m.duration for m in recent_llm_calls])
            if recent_llm_calls else 0.0
        )
        
        # 计算缓存命中率
        cache_hits = sum(1 for m in recent_tool_executions if m.cache_hit)
        total_tool_calls = len(recent_tool_executions)
        cache_hit_rate = cache_hits / total_tool_calls if total_tool_calls > 0 else 0.0
        
        # 计算成功率
        successful_dag = sum(1 for m in recent_dag_executions if m.success_rate > 0.9)
        success_rate = successful_dag / len(recent_dag_executions) if recent_dag_executions else 0.0
        
        # 统计最常用工具
        tool_counts = defaultdict(int)
        for m in recent_tool_executions:
            tool_counts[m.tool_name] += 1
        top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 统计最常见错误
        error_counts_recent = defaultdict(int)
        for m in recent_tool_executions:
            if not m.success and m.error_message:
                error_counts_recent[m.error_message] += 1
        top_errors = sorted(error_counts_recent.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return PerformanceSnapshot(
            timestamp=time.time(),
            period_seconds=time_window_seconds,
            dag_executions=len(recent_dag_executions),
            avg_dag_duration=avg_dag_duration,
            llm_calls=len(recent_llm_calls),
            avg_llm_duration=avg_llm_duration,
            cache_hit_rate=cache_hit_rate,
            success_rate=success_rate,
            top_tools=top_tools,
            top_errors=top_errors
        )
    
    def get_performance_trends(
        self,
        time_window_seconds: int = 86400,  # 24小时
        interval_seconds: int = 3600  # 1小时间隔
    ) -> Dict[str, Any]:
        """
        获取性能趋势分析
        
        Args:
            time_window_seconds: 时间窗口（秒）
            interval_seconds: 间隔（秒）
            
        Returns:
            Dict[str, Any]: 性能趋势数据
        """
        current_time = time.time()
        start_time = current_time - time_window_seconds
        
        # 生成时间点
        time_points = []
        t = start_time
        while t <= current_time:
            time_points.append(t)
            t += interval_seconds
        
        # 为每个时间点计算指标
        trends = {
            "time_points": [datetime.fromtimestamp(t).isoformat() for t in time_points],
            "dag_execution_counts": [],
            "avg_dag_durations": [],
            "llm_call_counts": [],
            "avg_llm_durations": [],
            "cache_hit_rates": [],
            "success_rates": []
        }
        
        for i in range(len(time_points) - 1):
            interval_start = time_points[i]
            interval_end = time_points[i + 1]
            
            # 过滤该时间段的数据
            interval_dag_executions = [
                m for m in self.dag_executions
                if interval_start <= m.start_time < interval_end
            ]
            
            interval_llm_calls = [
                m for m in self.llm_calls
                if interval_start <= m.start_time < interval_end
            ]
            
            interval_tool_executions = [
                m for m in self.tool_executions
                if interval_start <= m.start_time < interval_end
            ]
            
            # 计算指标
            trends["dag_execution_counts"].append(len(interval_dag_executions))
            trends["avg_dag_durations"].append(
                statistics.mean([m.total_duration for m in interval_dag_executions])
                if interval_dag_executions else 0.0
            )
            
            trends["llm_call_counts"].append(len(interval_llm_calls))
            trends["avg_llm_durations"].append(
                statistics.mean([m.duration for m in interval_llm_calls])
                if interval_llm_calls else 0.0
            )
            
            cache_hits = sum(1 for m in interval_tool_executions if m.cache_hit)
            total_calls = len(interval_tool_executions)
            trends["cache_hit_rates"].append(
                cache_hits / total_calls if total_calls > 0 else 0.0
            )
            
            successful = sum(1 for m in interval_dag_executions if m.success_rate > 0.9)
            trends["success_rates"].append(
                successful / len(interval_dag_executions)
                if interval_dag_executions else 0.0
            )
        
        return trends
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        获取性能优化建议 - Requirements 6.4
        
        为每种瓶颈类型提供具体优化建议
        
        Returns:
            List[Dict[str, Any]]: 优化建议列表
        """
        recommendations = []
        
        # ========== 分析瓶颈类型并提供具体建议 ==========
        
        # 1. 分析用户档案瓶颈 (user_profile)
        user_profile_bottlenecks = [
            b for b in self.bottlenecks
            if "user_profile" in b.step_name.lower() or "preload_user" in b.step_name.lower()
        ]
        if user_profile_bottlenecks:
            avg_duration = statistics.mean([b.duration_ms for b in user_profile_bottlenecks])
            recommendations.append({
                "type": "user_profile_bottleneck",
                "severity": "high" if avg_duration > 3000 else "medium",
                "bottleneck_count": len(user_profile_bottlenecks),
                "avg_duration_ms": avg_duration,
                "threshold_ms": self.type_thresholds.get("user_profile", 2000),
                "recommendation": "用户档案加载慢",
                "specific_actions": [
                    "1. 检查MySQL用户表索引是否正确（user_id应有索引）",
                    "2. 增加Redis缓存TTL（当前建议3600秒）",
                    "3. 启用启动时预热（ProgressiveWarmup）",
                    "4. 检查网络延迟（MySQL/Redis连接）",
                    "5. 考虑增加内存缓存容量（max_memory_entries）"
                ]
            })
        
        # 2. 分析会员权限瓶颈 (membership)
        membership_bottlenecks = [
            b for b in self.bottlenecks
            if "membership" in b.step_name.lower()
        ]
        if membership_bottlenecks:
            avg_duration = statistics.mean([b.duration_ms for b in membership_bottlenecks])
            recommendations.append({
                "type": "membership_bottleneck",
                "severity": "high" if avg_duration > 4000 else "medium",
                "bottleneck_count": len(membership_bottlenecks),
                "avg_duration_ms": avg_duration,
                "threshold_ms": self.type_thresholds.get("membership", 3000),
                "recommendation": "会员权限检查慢",
                "specific_actions": [
                    "1. 启用智能预热（步骤1预热步骤3）",
                    "2. 检查会员表索引（user_id应有索引）",
                    "3. 增加Redis缓存TTL",
                    "4. 检查Laravel后端API响应时间",
                    "5. 考虑本地缓存会员状态"
                ]
            })
        
        # 3. 分析LLM瓶颈
        llm_bottlenecks = [
            b for b in self.bottlenecks
            if "llm" in b.step_name.lower() or "decision" in b.step_name.lower() or "analysis" in b.step_name.lower()
        ]
        if llm_bottlenecks:
            avg_duration = statistics.mean([b.duration_ms for b in llm_bottlenecks])
            recommendations.append({
                "type": "llm_bottleneck",
                "severity": "high" if avg_duration > 8000 else "medium",
                "bottleneck_count": len(llm_bottlenecks),
                "avg_duration_ms": avg_duration,
                "threshold_ms": self.type_thresholds.get("llm", 5000),
                "recommendation": "LLM调用慢",
                "specific_actions": [
                    "1. 优化提示词长度（减少token数量）",
                    "2. 使用更快的模型（如gpt-4o-mini替代gpt-4）",
                    "3. 启用流式输出减少感知延迟",
                    "4. 检查LLM服务商API状态",
                    "5. 考虑使用本地模型（如Ollama）",
                    "6. 增加Few-Shot缓存命中率"
                ]
            })
        
        # 4. 分析缓存命中率
        cache_stats = self.get_cache_hit_rate()
        if "overall" in cache_stats:
            overall_hit_rate = cache_stats["overall"]["hit_rate"]
            if overall_hit_rate < 0.5:
                recommendations.append({
                    "type": "low_overall_cache_hit_rate",
                    "severity": "high" if overall_hit_rate < 0.3 else "medium",
                    "hit_rate": overall_hit_rate,
                    "recommendation": f"整体缓存命中率低（{overall_hit_rate:.1%}）",
                    "specific_actions": [
                        "1. 启用启动时渐进式预热",
                        "2. 增加缓存TTL",
                        "3. 增加内存缓存容量",
                        "4. 分析热门用户并优先预热",
                        "5. 检查缓存淘汰策略"
                    ]
                })
            
            # 分析各类型缓存
            for cache_type, stats in cache_stats.get("by_type", {}).items():
                if stats["total"] > 10 and stats["hit_rate"] < 0.4:
                    recommendations.append({
                        "type": f"low_{cache_type}_cache_hit_rate",
                        "severity": "medium",
                        "cache_type": cache_type,
                        "hit_rate": stats["hit_rate"],
                        "recommendation": f"{cache_type}缓存命中率低（{stats['hit_rate']:.1%}）",
                        "specific_actions": self._get_cache_specific_actions(cache_type)
                    })
        
        # ========== 原有的工具和LLM分析 ==========
        
        # 分析工具性能
        for tool_name, stats in self.tool_stats.items():
            if stats["total_calls"] < 10:
                continue
            
            avg_duration = stats["total_duration"] / stats["total_calls"]
            cache_hit_rate = (
                stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"])
                if (stats["cache_hits"] + stats["cache_misses"]) > 0 else 0.0
            )
            
            # 慢工具建议
            if avg_duration > 2.0:
                recommendations.append({
                    "type": "slow_tool",
                    "severity": "high",
                    "tool_name": tool_name,
                    "avg_duration": avg_duration,
                    "recommendation": f"工具 {tool_name} 平均执行时间 {avg_duration:.2f}s",
                    "specific_actions": [
                        f"1. 检查{tool_name}的数据库查询是否有索引",
                        "2. 增加工具结果缓存",
                        "3. 优化工具内部逻辑",
                        "4. 考虑异步执行"
                    ]
                })
            
            # 低缓存命中率建议
            if cache_hit_rate < 0.3 and stats["total_calls"] > 20:
                recommendations.append({
                    "type": "low_cache_hit_rate",
                    "severity": "medium",
                    "tool_name": tool_name,
                    "cache_hit_rate": cache_hit_rate,
                    "recommendation": f"工具 {tool_name} 缓存命中率仅 {cache_hit_rate:.1%}",
                    "specific_actions": [
                        "1. 增加缓存TTL",
                        "2. 启用预加载",
                        "3. 检查缓存键设计是否合理"
                    ]
                })
            
            # 高失败率建议
            failure_rate = stats["failed_calls"] / stats["total_calls"]
            if failure_rate > 0.1:
                recommendations.append({
                    "type": "high_failure_rate",
                    "severity": "high",
                    "tool_name": tool_name,
                    "failure_rate": failure_rate,
                    "recommendation": f"工具 {tool_name} 失败率 {failure_rate:.1%}",
                    "specific_actions": [
                        "1. 检查错误日志定位问题",
                        "2. 增加重试机制",
                        "3. 检查依赖服务状态",
                        "4. 增加熔断器保护"
                    ]
                })
        
        # 分析LLM性能
        for call_type, stats in self.llm_stats.items():
            if stats["total_calls"] < 5:
                continue
            
            avg_duration = stats["total_duration"] / stats["total_calls"]
            fallback_rate = stats["fallback_count"] / stats["total_calls"]
            
            # LLM慢调用建议
            if avg_duration > 5.0:
                recommendations.append({
                    "type": "slow_llm_call",
                    "severity": "medium",
                    "call_type": call_type,
                    "avg_duration": avg_duration,
                    "recommendation": f"LLM {call_type} 调用平均耗时 {avg_duration:.2f}s",
                    "specific_actions": [
                        "1. 优化提示词减少token",
                        "2. 使用更快的模型",
                        "3. 启用流式输出",
                        "4. 检查网络延迟"
                    ]
                })
            
            # 高降级率建议
            if fallback_rate > 0.2:
                recommendations.append({
                    "type": "high_fallback_rate",
                    "severity": "high",
                    "call_type": call_type,
                    "fallback_rate": fallback_rate,
                    "recommendation": f"LLM {call_type} 降级率 {fallback_rate:.1%}",
                    "specific_actions": [
                        "1. 检查主LLM服务状态",
                        "2. 增加重试次数",
                        "3. 检查API配额",
                        "4. 考虑增加备用LLM"
                    ]
                })
        
        # 按严重程度排序
        severity_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return recommendations
    
    def _get_cache_specific_actions(self, cache_type: str) -> List[str]:
        """
        获取特定缓存类型的优化建议
        
        Args:
            cache_type: 缓存类型
            
        Returns:
            List[str]: 优化建议列表
        """
        actions = {
            "user_profile": [
                "1. 启用用户档案预热",
                "2. 增加Redis TTL到3600秒",
                "3. 增加内存缓存容量到1000",
                "4. 分析热门用户并优先预热"
            ],
            "membership": [
                "1. 启用智能预热（步骤1预热步骤3）",
                "2. 增加会员缓存TTL",
                "3. 检查会员API响应时间"
            ],
            "few_shot": [
                "1. 预热常用查询的Few-Shot示例",
                "2. 增加Few-Shot缓存容量",
                "3. 优化向量检索索引"
            ],
            "query_analysis": [
                "1. 缓存常见查询的分析结果",
                "2. 增加查询分析缓存TTL",
                "3. 优化查询分类模型"
            ]
        }
        return actions.get(cache_type, ["1. 增加缓存TTL", "2. 启用预热", "3. 增加缓存容量"])
    
    def reset_statistics(self):
        """重置所有统计数据"""
        self.tool_executions.clear()
        self.dag_executions.clear()
        self.llm_calls.clear()
        self.cache_metrics_history.clear()
        self.tool_stats.clear()
        self.llm_stats.clear()
        self.error_counts.clear()
        
        # 重置工作流历史
        self.active_workflows.clear()
        self.completed_workflows.clear()
        self.bottlenecks.clear()
        
        # 重置操作统计
        self._operation_stats.clear()
        self._active_timers.clear()
        
        # 重置Prometheus指标
        self.prometheus_metrics = {
            "workflow_total_duration_seconds": [],
            "workflow_step_duration_seconds": defaultdict(list),
            "workflow_success_total": 0,
            "workflow_failure_total": 0,
            "workflow_bottleneck_total": 0,
            "workflow_concurrent_requests": 0,
            # 缓存指标 - Requirements 6.1, 6.2
            "cache_hits_total": defaultdict(int),
            "cache_misses_total": defaultdict(int),
            "cache_response_time_seconds": defaultdict(list),
        }
        
        logger.info("🔄 性能统计已重置")
    
    # ========== 辅助方法 ==========
    
    def _calculate_percentile(self, data: List[float], percentile: float) -> float:
        """
        计算百分位数
        
        Args:
            data: 数据列表
            percentile: 百分位（0-1）
            
        Returns:
            float: 百分位值
        """
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]


# 全局性能监控实例
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor


def set_performance_monitor(monitor: PerformanceMonitor):
    """设置全局性能监控实例"""
    global _global_performance_monitor
    _global_performance_monitor = monitor
