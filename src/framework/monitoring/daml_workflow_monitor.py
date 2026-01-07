# -*- coding: utf-8 -*-
"""
DAML Workflow Performance Monitor - DAML工作流程性能监控器

完整的DAML-RAG工作流程性能跟踪和分析系统

核心功能：
1. 11步工作流程全链路跟踪
2. 每层检索耗时和成功率监控
3. 成本效益分析
4. 性能瓶颈识别
5. 实时性能仪表板

版本: v1.0.0
日期: 2025-12-03
作者: 薛小川
"""

import logging
import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import uuid

logger = logging.getLogger(__name__)


class WorkflowStep(Enum):
    """工作流程步骤枚举"""
    USER_PROFILE_LOADING = "user_profile_loading"
    SESSION_STORAGE = "session_storage"
    MEMBERSHIP_CHECK = "membership_check"
    BGE_COMPLEXITY_CLASSIFICATION = "bge_complexity_classification"
    MODEL_SELECTION = "model_selection"
    FEW_SHOT_RETRIEVAL = "few_shot_retrieval"
    DAG_ORCHESTRATION = "dag_orchestration"
    THREE_LAYER_RETRIEVAL = "three_layer_retrieval"
    TOOL_RESULT_AGGREGATION = "tool_result_aggregation"
    LLM_GENERATION = "llm_generation"
    INTERACTION_RECORDING = "interaction_recording"


class RetrievalLayer(Enum):
    """检索层级枚举"""
    LAYER1_VECTOR = "layer1_vector"
    LAYER2_GRAPH = "layer2_graph"
    LAYER3_RULES = "layer3_rules"


@dataclass
class StepMetrics:
    """单步性能指标"""
    step_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    input_size: int = 0
    output_size: int = 0
    cache_hit: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self, success: bool = True, error_message: Optional[str] = None):
        """完成步骤记录"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "step_name": self.step_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "input_size": self.input_size,
            "output_size": self.output_size,
            "cache_hit": self.cache_hit,
            "metadata": self.metadata
        }


@dataclass
class LayerMetrics:
    """检索层级性能指标"""
    layer_name: RetrievalLayer
    step_metrics: StepMetrics
    candidates_in: int = 0
    candidates_out: int = 0
    confidence_score: float = 0.0
    filter_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "layer_name": self.layer_name.value,
            **self.step_metrics.to_dict(),
            "candidates_in": self.candidates_in,
            "candidates_out": self.candidates_out,
            "confidence_score": self.confidence_score,
            "filter_reason": self.filter_reason
        }


@dataclass
class WorkflowSession:
    """完整工作流程会话"""
    session_id: str
    user_id: Optional[str]
    query: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    steps: Dict[WorkflowStep, StepMetrics] = field(default_factory=dict)
    retrieval_layers: Dict[RetrievalLayer, LayerMetrics] = field(default_factory=dict)
    final_success: bool = True
    error_message: Optional[str] = None
    cost_estimate: float = 0.0
    model_used: str = ""
    quality_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start_step(self, step: WorkflowStep) -> StepMetrics:
        """开始一个步骤"""
        step_metrics = StepMetrics(step_name=step.value, start_time=datetime.now())
        self.steps[step] = step_metrics
        return step_metrics

    def start_retrieval_layer(self, layer: RetrievalLayer) -> LayerMetrics:
        """开始一个检索层级"""
        step_metrics = StepMetrics(step_name=f"retrieval_{layer.value}", start_time=datetime.now())
        layer_metrics = LayerMetrics(layer_name=layer, step_metrics=step_metrics)
        self.retrieval_layers[layer] = layer_metrics
        return layer_metrics

    def finish(self, success: bool = True, error_message: Optional[str] = None):
        """完成工作流程会话"""
        self.end_time = datetime.now()
        self.total_duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.final_success = success
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "query": self.query,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.total_duration_ms,
            "final_success": self.final_success,
            "error_message": self.error_message,
            "cost_estimate": self.cost_estimate,
            "model_used": self.model_used,
            "quality_score": self.quality_score,
            "steps": {step.value: metrics.to_dict() for step, metrics in self.steps.items()},
            "retrieval_layers": {layer.value: metrics.to_dict() for layer, metrics in self.retrieval_layers.items()},
            "metadata": self.metadata
        }


class DAMLWorkflowMonitor:
    """
    DAML工作流程性能监控器

    核心特性：
    1. 完整的11步工作流程跟踪
    2. 三层检索详细监控
    3. 实时性能统计
    4. 成本效益分析
    5. 性能瓶颈识别
    6. 历史趋势分析
    """

    def __init__(
        self,
        max_sessions: int = 1000,
        aggregation_window_minutes: int = 60,
        alert_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        初始化工作流程监控器

        Args:
            max_sessions: 最大会话缓存数量
            aggregation_window_minutes: 聚合窗口时间（分钟）
            alert_thresholds: 告警阈值配置
        """
        self.max_sessions = max_sessions
        self.aggregation_window = timedelta(minutes=aggregation_window_minutes)
        self.alert_thresholds = alert_thresholds or {
            "max_total_duration_ms": 5000,
            "max_single_step_duration_ms": 2000,
            "min_success_rate": 0.9,
            "max_error_rate": 0.1
        }

        # 会话存储
        self.active_sessions: Dict[str, WorkflowSession] = {}
        self.completed_sessions: deque = deque(maxlen=max_sessions)

        # 聚合统计
        self.aggregated_stats = defaultdict(lambda: defaultdict(list))
        self.last_aggregation_time = datetime.now()

        # 实时指标
        self.real_time_metrics = {
            "current_sessions": 0,
            "total_sessions": 0,
            "avg_duration_ms": 0.0,
            "success_rate": 1.0,
            "error_rate": 0.0,
            "layer_success_rates": {layer.value: 1.0 for layer in RetrievalLayer},
            "step_success_rates": {step.value: 1.0 for step in WorkflowStep}
        }

        # 性能基准
        self.performance_benchmarks = {
            "target_total_duration_ms": 3000,
            "target_layer_duration_ms": 500,
            "target_step_duration_ms": 1000,
            "target_success_rate": 0.95
        }

        logger.info("DAMLWorkflowMonitor initialized")

    def start_session(
        self,
        user_id: Optional[str],
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        开始新的工作流程会话

        Args:
            user_id: 用户ID
            query: 查询文本
            metadata: 额外元数据

        Returns:
            str: 会话ID
        """
        session_id = str(uuid.uuid4())

        session = WorkflowSession(
            session_id=session_id,
            user_id=user_id,
            query=query,
            start_time=datetime.now(),
            metadata=metadata or {}
        )

        self.active_sessions[session_id] = session
        self.real_time_metrics["current_sessions"] += 1
        self.real_time_metrics["total_sessions"] += 1

        logger.debug(f"开始工作流程会话: {session_id}")
        return session_id

    def start_step(self, session_id: str, step: WorkflowStep) -> Optional[StepMetrics]:
        """
        开始工作流程步骤

        Args:
            session_id: 会话ID
            step: 工作流程步骤

        Returns:
            Optional[StepMetrics]: 步骤指标对象
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"未找到活动会话: {session_id}")
            return None

        step_metrics = session.start_step(step)
        logger.debug(f"开始步骤: {step.value} (会话: {session_id})")
        return step_metrics

    def start_retrieval_layer(
        self,
        session_id: str,
        layer: RetrievalLayer
    ) -> Optional[LayerMetrics]:
        """
        开始检索层级

        Args:
            session_id: 会话ID
            layer: 检索层级

        Returns:
            Optional[LayerMetrics]: 层级指标对象
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"未找到活动会话: {session_id}")
            return None

        layer_metrics = session.start_retrieval_layer(layer)
        logger.debug(f"开始检索层级: {layer.value} (会话: {session_id})")
        return layer_metrics

    def finish_step(
        self,
        session_id: str,
        step: WorkflowStep,
        success: bool = True,
        error_message: Optional[str] = None,
        input_size: int = 0,
        output_size: int = 0,
        cache_hit: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        完成工作流程步骤

        Args:
            session_id: 会话ID
            step: 工作流程步骤
            success: 是否成功
            error_message: 错误信息
            input_size: 输入大小
            output_size: 输出大小
            cache_hit: 是否缓存命中
            metadata: 额外元数据
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"未找到活动会话: {session_id}")
            return

        step_metrics = session.steps.get(step)
        if step_metrics:
            step_metrics.finish(success, error_message)
            step_metrics.input_size = input_size
            step_metrics.output_size = output_size
            step_metrics.cache_hit = cache_hit
            if metadata:
                step_metrics.metadata.update(metadata)

            logger.debug(f"完成步骤: {step.value} (会话: {session_id}, 耗时: {step_metrics.duration_ms:.1f}ms)")

    def finish_retrieval_layer(
        self,
        session_id: str,
        layer: RetrievalLayer,
        success: bool = True,
        error_message: Optional[str] = None,
        candidates_in: int = 0,
        candidates_out: int = 0,
        confidence_score: float = 0.0,
        filter_reason: str = ""
    ):
        """
        完成检索层级

        Args:
            session_id: 会话ID
            layer: 检索层级
            success: 是否成功
            error_message: 错误信息
            candidates_in: 输入候选数量
            candidates_out: 输出候选数量
            confidence_score: 置信度
            filter_reason: 过滤原因
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"未找到活动会话: {session_id}")
            return

        layer_metrics = session.retrieval_layers.get(layer)
        if layer_metrics:
            layer_metrics.step_metrics.finish(success, error_message)
            layer_metrics.candidates_in = candidates_in
            layer_metrics.candidates_out = candidates_out
            layer_metrics.confidence_score = confidence_score
            layer_metrics.filter_reason = filter_reason

            logger.debug(f"完成检索层级: {layer.value} (会话: {session_id}, 候选: {candidates_in}->{candidates_out})")

    def finish_session(
        self,
        session_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        cost_estimate: float = 0.0,
        model_used: str = "",
        quality_score: Optional[float] = None,
        final_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        完成工作流程会话

        Args:
            session_id: 会话ID
            success: 是否成功
            error_message: 错误信息
            cost_estimate: 成本估算
            model_used: 使用的模型
            quality_score: 质量评分
            final_metadata: 最终元数据
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"未找到活动会话: {session_id}")
            return

        session.finish(success, error_message)
        session.cost_estimate = cost_estimate
        session.model_used = model_used
        session.quality_score = quality_score

        if final_metadata:
            session.metadata.update(final_metadata)

        # 移动到已完成会话
        self.completed_sessions.append(session)
        del self.active_sessions[session_id]

        # 更新实时指标
        self.real_time_metrics["current_sessions"] -= 1
        self._update_real_time_metrics()

        # 检查告警
        self._check_alerts(session)

        logger.info(
            f"完成工作流程会话: {session_id}, "
            f"成功={success}, "
            f"耗时={session.total_duration_ms:.1f}ms, "
            f"成本=${cost_estimate:.4f}"
        )

    def _update_real_time_metrics(self):
        """更新实时指标"""
        if not self.completed_sessions:
            return

        # 最近100个会话的统计
        recent_sessions = list(self.completed_sessions)[-100:]

        # 成功率
        successful_sessions = sum(1 for s in recent_sessions if s.final_success)
        session_count = len(recent_sessions)
        self.real_time_metrics["success_rate"] = successful_sessions / session_count if session_count > 0 else 0
        self.real_time_metrics["error_rate"] = 1 - self.real_time_metrics["success_rate"]

        # 平均耗时
        durations = [s.total_duration_ms for s in recent_sessions if s.total_duration_ms]
        if durations:
            self.real_time_metrics["avg_duration_ms"] = sum(durations) / len(durations)

        # 步骤成功率
        for step in WorkflowStep:
            step_success_count = sum(
                1 for s in recent_sessions
                if step in s.steps and s.steps[step].success
            )
            step_total_count = sum(
                1 for s in recent_sessions
                if step in s.steps
            )
            if step_total_count > 0:
                self.real_time_metrics["step_success_rates"][step.value] = (
                    step_success_count / step_total_count
                )

        # 检索层级成功率
        for layer in RetrievalLayer:
            layer_success_count = sum(
                1 for s in recent_sessions
                if layer in s.retrieval_layers and s.retrieval_layers[layer].step_metrics.success
            )
            layer_total_count = sum(
                1 for s in recent_sessions
                if layer in s.retrieval_layers
            )
            if layer_total_count > 0:
                self.real_time_metrics["layer_success_rates"][layer.value] = (
                    layer_success_count / layer_total_count
                )

    def _check_alerts(self, session: WorkflowSession):
        """检查性能告警"""
        alerts = []

        # 总耗时告警
        if (session.total_duration_ms and
            session.total_duration_ms > self.alert_thresholds["max_total_duration_ms"]):
            alerts.append({
                "type": "slow_workflow",
                "message": f"工作流程耗时过长: {session.total_duration_ms:.1f}ms",
                "severity": "warning"
            })

        # 单步耗时告警
        for step, metrics in session.steps.items():
            if (metrics.duration_ms and
                metrics.duration_ms > self.alert_thresholds["max_single_step_duration_ms"]):
                alerts.append({
                    "type": "slow_step",
                    "message": f"步骤 {step.value} 耗时过长: {metrics.duration_ms:.1f}ms",
                    "severity": "warning"
                })

        # 成功率告警
        if self.real_time_metrics["success_rate"] < self.alert_thresholds["min_success_rate"]:
            alerts.append({
                "type": "low_success_rate",
                "message": f"成功率过低: {self.real_time_metrics['success_rate']:.1%}",
                "severity": "critical"
            })

        # 记录告警
        for alert in alerts:
            logger.warning(f"性能告警: {alert['message']}")

    def get_performance_summary(
        self,
        time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        获取性能摘要

        Args:
            time_window_minutes: 时间窗口（分钟）

        Returns:
            Dict[str, Any]: 性能摘要
        """
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        recent_sessions = [
            s for s in self.completed_sessions
            if s.start_time >= cutoff_time
        ]

        if not recent_sessions:
            return {
                "time_window_minutes": time_window_minutes,
                "total_sessions": 0,
                "message": "指定时间窗口内无会话数据"
            }

        # 基础统计
        total_sessions = len(recent_sessions)
        successful_sessions = sum(1 for s in recent_sessions if s.final_success)

        durations = [s.total_duration_ms for s in recent_sessions if s.total_duration_ms]
        costs = [s.cost_estimate for s in recent_sessions]

        # 步骤统计
        step_stats = {}
        for step in WorkflowStep:
            step_sessions = [s for s in recent_sessions if step in s.steps]
            if step_sessions:
                step_durations = [s.steps[step].duration_ms for s in step_sessions if s.steps[step].duration_ms]
                step_successes = sum(1 for s in step_sessions if s.steps[step].success)

                session_count = len(step_sessions)
                step_stats[step.value] = {
                    "count": session_count,
                    "success_rate": step_successes / session_count if session_count > 0 else 0,
                    "avg_duration_ms": sum(step_durations) / len(step_durations) if step_durations else 0,
                    "max_duration_ms": max(step_durations) if step_durations else 0,
                    "cache_hit_rate": sum(1 for s in step_sessions if s.steps[step].cache_hit) / session_count if session_count > 0 else 0
                }

        # 检索层级统计
        layer_stats = {}
        for layer in RetrievalLayer:
            layer_sessions = [s for s in recent_sessions if layer in s.retrieval_layers]
            if layer_sessions:
                layer_successes = sum(
                    1 for s in layer_sessions
                    if s.retrieval_layers[layer].step_metrics.success
                )
                candidates_reduction = sum(
                    s.retrieval_layers[layer].candidates_in - s.retrieval_layers[layer].candidates_out
                    for s in layer_sessions
                )

                layer_session_count = len(layer_sessions)
                layer_stats[layer.value] = {
                    "count": layer_session_count,
                    "success_rate": layer_successes / layer_session_count if layer_session_count > 0 else 0,
                    "avg_candidates_in": sum(
                        s.retrieval_layers[layer].candidates_in for s in layer_sessions
                    ) / layer_session_count if layer_session_count > 0 else 0,
                    "avg_candidates_out": sum(
                        s.retrieval_layers[layer].candidates_out for s in layer_sessions
                    ) / layer_session_count if layer_session_count > 0 else 0,
                    "total_candidates_reduced": candidates_reduction,
                    "avg_confidence": sum(
                        s.retrieval_layers[layer].confidence_score for s in layer_sessions
                    ) / layer_session_count if layer_session_count > 0 else 0
                }

        return {
            "time_window_minutes": time_window_minutes,
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "success_rate": successful_sessions / total_sessions if total_sessions > 0 else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "total_cost": sum(costs),
            "avg_cost_per_session": sum(costs) / len(costs) if costs else 0,
            "step_statistics": step_stats,
            "retrieval_layer_statistics": layer_stats,
            "performance_vs_benchmark": {
                "duration_ratio": (sum(durations) / len(durations) / self.performance_benchmarks["target_total_duration_ms"]) if durations else 0,
                "success_rate_ratio": ((successful_sessions / total_sessions) / self.performance_benchmarks["target_success_rate"]) if total_sessions > 0 else 0
            },
            "real_time_metrics": self.real_time_metrics.copy()
        }

    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话详细信息"""
        # 先在活动会话中查找
        if session_id in self.active_sessions:
            return self.active_sessions[session_id].to_dict()

        # 再在已完成会话中查找
        for session in reversed(self.completed_sessions):
            if session.session_id == session_id:
                return session.to_dict()

        return None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """获取当前活动会话列表"""
        return [
            {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "query": session.query,
                "start_time": session.start_time.isoformat(),
                "duration_ms": (datetime.now() - session.start_time).total_seconds() * 1000,
                "completed_steps": [step.value for step in session.steps.keys()]
            }
            for session in self.active_sessions.values()
        ]

    def export_metrics(
        self,
        format: str = "json",
        time_window_minutes: int = 60
    ) -> Union[str, Dict[str, Any]]:
        """
        导出性能指标

        Args:
            format: 导出格式 ("json", "csv", "prometheus")
            time_window_minutes: 时间窗口

        Returns:
            Union[str, Dict[str, Any]]: 导出的指标数据
        """
        summary = self.get_performance_summary(time_window_minutes)

        if format == "json":
            return json.dumps(summary, indent=2, ensure_ascii=False, default=str)
        elif format == "csv":
            # CSV格式导出逻辑
            return self._export_to_csv(summary)
        elif format == "prometheus":
            # Prometheus格式导出逻辑
            return self._export_to_prometheus(summary)
        else:
            return summary

    def _export_to_csv(self, summary: Dict[str, Any]) -> str:
        """导出为CSV格式"""
        lines = []
        lines.append("Metric,Value")
        lines.append(f"Total Sessions,{summary['total_sessions']}")
        lines.append(f"Success Rate,{summary['success_rate']:.2%}")
        lines.append(f"Avg Duration (ms),{summary['avg_duration_ms']:.1f}")
        lines.append(f"Avg Cost,${summary['avg_cost_per_session']:.4f}")
        return "\n".join(lines)

    def _export_to_prometheus(self, summary: Dict[str, Any]) -> str:
        """导出为Prometheus格式"""
        lines = []

        lines.append("# HELP daml_workflow_sessions_total Total number of workflow sessions")
        lines.append(f"# TYPE daml_workflow_sessions_total counter")
        lines.append(f"daml_workflow_sessions_total {summary['total_sessions']}")

        lines.append("# HELP daml_workflow_success_rate Success rate of workflows")
        lines.append(f"# TYPE daml_workflow_success_rate gauge")
        lines.append(f"daml_workflow_success_rate {summary['success_rate']:.3f}")

        lines.append("# HELP daml_workflow_duration_ms Average workflow duration")
        lines.append(f"# TYPE daml_workflow_duration_ms gauge")
        lines.append(f"daml_workflow_duration_ms {summary['avg_duration_ms']:.1f}")

        return "\n".join(lines)


# 导出
__all__ = [
    "DAMLWorkflowMonitor",
    "WorkflowSession",
    "StepMetrics",
    "LayerMetrics",
    "WorkflowStep",
    "RetrievalLayer"
]