# -*- coding: utf-8 -*-
"""
步骤性能监控模块测试

测试StepPerformance和WorkflowPerformanceMonitor的功能
"""

import pytest
import time
from src.framework.monitoring.step_performance import (
    StepStatus,
    StepPerformance,
    WorkflowPerformanceMonitor
)


def test_step_performance_lifecycle():
    """测试步骤性能记录的完整生命周期"""
    # 创建步骤
    step = StepPerformance(
        step_number=1,
        step_name="测试步骤",
        start_time=time.time()
    )
    
    # 验证初始状态
    assert step.step_number == 1
    assert step.step_name == "测试步骤"
    assert step.status == StepStatus.NOT_STARTED
    assert step.success is False
    assert step.error is None
    
    # 开始步骤
    step.start()
    assert step.status == StepStatus.IN_PROGRESS
    
    # 模拟执行
    time.sleep(0.1)
    
    # 完成步骤
    step.finish(success=True, test_data="test_value")
    assert step.status == StepStatus.COMPLETED
    assert step.success is True
    assert step.duration_ms is not None
    assert step.duration_ms >= 100  # 至少100ms
    assert step.metadata["test_data"] == "test_value"


def test_step_performance_failure():
    """测试步骤失败场景"""
    step = StepPerformance(
        step_number=2,
        step_name="失败步骤",
        start_time=time.time()
    )
    
    step.start()
    time.sleep(0.05)
    step.finish(success=False, error="测试错误")
    
    assert step.status == StepStatus.FAILED
    assert step.success is False
    assert step.error == "测试错误"
    assert step.duration_ms is not None


def test_step_performance_skip():
    """测试步骤跳过场景"""
    step = StepPerformance(
        step_number=3,
        step_name="跳过步骤",
        start_time=time.time()
    )
    
    step.skip("条件不满足")
    
    assert step.status == StepStatus.SKIPPED
    assert step.metadata["skip_reason"] == "条件不满足"


def test_workflow_performance_monitor():
    """测试工作流性能监控器"""
    monitor = WorkflowPerformanceMonitor(request_id="test_request_123")
    
    # 创建并执行步骤1
    step1 = monitor.create_step(1, "步骤1")
    step1.start()
    time.sleep(0.05)
    step1.finish(success=True)
    
    # 创建并执行步骤2
    step2 = monitor.create_step(2, "步骤2")
    step2.start()
    time.sleep(0.1)
    step2.finish(success=True)
    
    # 创建并执行步骤3（失败）
    step3 = monitor.create_step(3, "步骤3")
    step3.start()
    time.sleep(0.02)
    step3.finish(success=False, error="测试错误")
    
    # 完成工作流
    monitor.finish_workflow()
    
    # 验证监控器状态
    assert len(monitor.steps) == 3
    assert monitor.total_duration_ms is not None
    assert monitor.total_duration_ms >= 170  # 至少170ms
    
    # 获取性能摘要
    summary = monitor.get_summary()
    assert summary["request_id"] == "test_request_123"
    assert summary["total_steps"] == 3
    assert summary["completed_steps"] == 2
    assert summary["failed_steps"] == 1
    assert summary["slowest_step"]["number"] == 2  # 步骤2最慢（100ms）
    # 注意：fastest_step只统计completed的步骤，步骤3是failed状态
    assert summary["fastest_step"]["number"] == 1  # 步骤1最快（50ms，在completed步骤中）


def test_identify_bottlenecks():
    """测试性能瓶颈识别"""
    monitor = WorkflowPerformanceMonitor(request_id="test_bottleneck")
    
    # 创建快速步骤
    step1 = monitor.create_step(1, "快速步骤")
    step1.start()
    time.sleep(0.05)
    step1.finish(success=True)
    
    # 创建慢速步骤（瓶颈）
    step2 = monitor.create_step(2, "慢速步骤")
    step2.start()
    time.sleep(1.1)  # 超过1000ms阈值
    step2.finish(success=True)
    
    # 创建另一个快速步骤
    step3 = monitor.create_step(3, "快速步骤2")
    step3.start()
    time.sleep(0.05)
    step3.finish(success=True)
    
    # 识别瓶颈
    bottlenecks = monitor.identify_bottlenecks(threshold_ms=1000.0)
    
    # 验证瓶颈识别
    assert len(bottlenecks) == 1
    assert bottlenecks[0].step_number == 2
    assert bottlenecks[0].step_name == "慢速步骤"
    assert bottlenecks[0].duration_ms >= 1100


def test_step_to_dict():
    """测试步骤转换为字典"""
    step = StepPerformance(
        step_number=1,
        step_name="测试步骤",
        start_time=time.time()
    )
    
    step.start()
    time.sleep(0.05)
    step.finish(success=True, custom_field="custom_value")
    
    step_dict = step.to_dict()
    
    assert step_dict["step_number"] == 1
    assert step_dict["step_name"] == "测试步骤"
    assert step_dict["status"] == "completed"
    assert step_dict["success"] is True
    assert step_dict["duration_ms"] is not None
    assert step_dict["metadata"]["custom_field"] == "custom_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
