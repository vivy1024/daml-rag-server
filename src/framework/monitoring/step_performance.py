# -*- coding: utf-8 -*-
"""
步骤性能监控模块

提供工作流步骤级别的性能监控和分析功能。

版本：v1.0.0
创建日期：2025-12-20
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """步骤执行状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepPerformance:
    """
    步骤性能数据类
    
    记录单个工作流步骤的性能指标
    """
    step_number: int
    step_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: StepStatus = StepStatus.NOT_STARTED
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start(self):
        """开始步骤执行"""
        self.start_time = time.time()
        self.status = StepStatus.IN_PROGRESS
        logger.debug(f"⏱️ 步骤{self.step_number}开始: {self.step_name}")
    
    def finish(self, success: bool = True, error: Optional[str] = None, **metadata):
        """
        完成步骤执行
        
        Args:
            success: 是否成功
            error: 错误信息（如果失败）
            **metadata: 额外的元数据
        """
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error
        self.status = StepStatus.COMPLETED if success else StepStatus.FAILED
        self.metadata.update(metadata)
        
        if success:
            logger.info(
                f"✅ 步骤{self.step_number}完成: {self.step_name} "
                f"(耗时: {self.duration_ms:.2f}ms)"
            )
        else:
            logger.warning(
                f"❌ 步骤{self.step_number}失败: {self.step_name} "
                f"(耗时: {self.duration_ms:.2f}ms, 错误: {error})"
            )
    
    def skip(self, reason: str):
        """跳过步骤"""
        self.status = StepStatus.SKIPPED
        self.metadata["skip_reason"] = reason
        logger.debug(f"⏭️ 步骤{self.step_number}跳过: {self.step_name} (原因: {reason})")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


class WorkflowPerformanceMonitor:
    """
    工作流性能监控器
    
    监控整个工作流的步骤执行性能，识别瓶颈
    """
    
    def __init__(self, request_id: str):
        """
        初始化监控器
        
        Args:
            request_id: 请求ID
        """
        self.request_id = request_id
        self.steps: Dict[int, StepPerformance] = {}
        self.workflow_start_time = time.time()
        self.workflow_end_time: Optional[float] = None
        self.total_duration_ms: Optional[float] = None
    
    def create_step(self, step_number: int, step_name: str) -> StepPerformance:
        """
        创建步骤性能记录
        
        Args:
            step_number: 步骤编号
            step_name: 步骤名称
        
        Returns:
            StepPerformance: 步骤性能对象
        """
        step = StepPerformance(
            step_number=step_number,
            step_name=step_name,
            start_time=time.time()
        )
        self.steps[step_number] = step
        return step
    
    def get_step(self, step_number: int) -> Optional[StepPerformance]:
        """获取步骤性能记录"""
        return self.steps.get(step_number)
    
    def finish_workflow(self):
        """完成工作流"""
        self.workflow_end_time = time.time()
        self.total_duration_ms = (self.workflow_end_time - self.workflow_start_time) * 1000
        
        logger.info(
            f"🎉 [{self.request_id}] 工作流完成: "
            f"总耗时={self.total_duration_ms:.2f}ms, "
            f"步骤数={len(self.steps)}"
        )
    
    def identify_bottlenecks(self, threshold_ms: float = 1000.0) -> List[StepPerformance]:
        """
        识别性能瓶颈
        
        Args:
            threshold_ms: 瓶颈阈值（毫秒）
        
        Returns:
            List[StepPerformance]: 瓶颈步骤列表
        """
        bottlenecks = []
        
        for step in self.steps.values():
            if step.duration_ms and step.duration_ms > threshold_ms:
                bottlenecks.append(step)
        
        # 按耗时降序排序
        bottlenecks.sort(key=lambda s: s.duration_ms or 0, reverse=True)
        
        if bottlenecks:
            logger.warning(
                f"⚠️ [{self.request_id}] 发现{len(bottlenecks)}个性能瓶颈 "
                f"(阈值: {threshold_ms}ms):"
            )
            for step in bottlenecks:
                logger.warning(
                    f"   - 步骤{step.step_number}: {step.step_name} "
                    f"({step.duration_ms:.2f}ms)"
                )
        
        return bottlenecks
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取性能摘要
        
        Returns:
            Dict[str, Any]: 性能摘要
        """
        completed_steps = [s for s in self.steps.values() if s.status == StepStatus.COMPLETED]
        failed_steps = [s for s in self.steps.values() if s.status == StepStatus.FAILED]
        
        total_step_time = sum(s.duration_ms or 0 for s in completed_steps)
        avg_step_time = total_step_time / len(completed_steps) if completed_steps else 0
        
        slowest_step = max(completed_steps, key=lambda s: s.duration_ms or 0) if completed_steps else None
        fastest_step = min(completed_steps, key=lambda s: s.duration_ms or 0) if completed_steps else None
        
        return {
            "request_id": self.request_id,
            "total_duration_ms": self.total_duration_ms,
            "total_steps": len(self.steps),
            "completed_steps": len(completed_steps),
            "failed_steps": len(failed_steps),
            "total_step_time_ms": total_step_time,
            "avg_step_time_ms": avg_step_time,
            "slowest_step": {
                "number": slowest_step.step_number,
                "name": slowest_step.step_name,
                "duration_ms": slowest_step.duration_ms
            } if slowest_step else None,
            "fastest_step": {
                "number": fastest_step.step_number,
                "name": fastest_step.step_name,
                "duration_ms": fastest_step.duration_ms
            } if fastest_step else None,
            "steps": [step.to_dict() for step in self.steps.values()]
        }
    
    def send_metrics_to_prometheus(self):
        """发送指标到Prometheus"""
        try:
            from .streaming_metrics import streaming_monitor
            
            # 记录每个步骤的耗时
            for step in self.steps.values():
                if step.duration_ms is not None:
                    # 使用streaming_monitor的底层Prometheus客户端
                    # 这里我们可以扩展streaming_metrics.py来支持步骤级别的指标
                    logger.debug(
                        f"📊 [{self.request_id}] 步骤{step.step_number}指标: "
                        f"{step.step_name}={step.duration_ms:.2f}ms"
                    )
            
            # 记录总体工作流指标
            if self.total_duration_ms is not None:
                logger.info(
                    f"📊 [{self.request_id}] 工作流指标: "
                    f"total_duration={self.total_duration_ms:.2f}ms, "
                    f"steps={len(self.steps)}"
                )
        
        except Exception as e:
            logger.warning(f"⚠️ [{self.request_id}] 发送Prometheus指标失败: {e}")


# 导出
__all__ = [
    "StepStatus",
    "StepPerformance",
    "WorkflowPerformanceMonitor"
]
