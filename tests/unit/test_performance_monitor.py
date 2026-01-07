# -*- coding: utf-8 -*-
"""
性能监控器单元测试

测试内容：
1. 步骤性能记录
2. 性能瓶颈检测
3. 指标导出格式（Prometheus和JSON）

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import time
import json
from src.framework.monitoring.performance_monitor import (
    PerformanceMonitor,
    WorkflowContext,
    StepRecord,
    PerformanceBottleneck
)


class TestPerformanceMonitor:
    """性能监控器测试类"""
    
    @pytest.fixture
    def monitor(self):
        """创建性能监控器实例"""
        return PerformanceMonitor(
            max_history_size=100,
            bottleneck_threshold_ms=1000.0
        )
    
    # ========== 步骤性能记录测试 ==========
    
    def test_start_workflow(self, monitor):
        """测试开始工作流监控"""
        context = monitor.start_workflow(request_id="test-001", user_id="user-123")
        
        assert context.request_id == "test-001"
        assert context.user_id == "user-123"
        assert context.start_time > 0
        assert len(context.steps) == 0
        assert "test-001" in monitor.active_workflows
    
    def test_start_workflow_auto_id(self, monitor):
        """测试自动生成请求ID"""
        context = monitor.start_workflow(user_id="user-123")
        
        assert context.request_id is not None
        assert len(context.request_id) > 0
        assert context.user_id == "user-123"
    
    def test_record_step(self, monitor):
        """测试记录步骤性能"""
        context = monitor.start_workflow(request_id="test-002", user_id="user-123")
        
        # 记录步骤1
        monitor.record_step(
            context=context,
            step_number=1,
            step_name="用户档案加载",
            duration_ms=500.0,
            success=True,
            metadata={"cache_hit": True}
        )
        
        assert len(context.steps) == 1
        step = context.steps[0]
        assert step.step_number == 1
        assert step.step_name == "用户档案加载"
        assert step.duration_ms == 500.0
        assert step.success is True
        assert step.metadata["cache_hit"] is True
        
        # 记录步骤2
        monitor.record_step(
            context=context,
            step_number=2,
            step_name="会员权限检查",
            duration_ms=300.0,
            success=True
        )
        
        assert len(context.steps) == 2
    
    def test_record_step_with_error(self, monitor):
        """测试记录失败的步骤"""
        context = monitor.start_workflow(request_id="test-003", user_id="user-123")
        
        monitor.record_step(
            context=context,
            step_number=1,
            step_name="数据库查询",
            duration_ms=2000.0,
            success=False,
            error="连接超时"
        )
        
        assert len(context.steps) == 1
        step = context.steps[0]
        assert step.success is False
        assert step.error == "连接超时"
    
    def test_finish_workflow(self, monitor):
        """测试完成工作流监控"""
        context = monitor.start_workflow(request_id="test-004", user_id="user-123")
        
        # 记录几个步骤
        monitor.record_step(context, 1, "步骤1", 100.0, True)
        monitor.record_step(context, 2, "步骤2", 200.0, True)
        
        # 完成工作流
        monitor.finish_workflow(context, success=True, total_duration_ms=300.0)
        
        # 验证工作流已从活跃列表移除
        assert "test-004" not in monitor.active_workflows
        
        # 验证工作流已添加到完成历史
        assert len(monitor.completed_workflows) == 1
        completed = monitor.completed_workflows[0]
        assert completed.request_id == "test-004"
        assert completed.metadata["success"] is True
        assert completed.metadata["total_duration_ms"] == 300.0
        
        # 验证Prometheus指标更新
        assert monitor.prometheus_metrics["workflow_success_total"] == 1
        assert len(monitor.prometheus_metrics["workflow_total_duration_seconds"]) == 1
    
    def test_finish_workflow_auto_duration(self, monitor):
        """测试自动计算工作流持续时间"""
        context = monitor.start_workflow(request_id="test-005", user_id="user-123")
        
        # 等待一小段时间
        time.sleep(0.1)
        
        # 完成工作流（不提供total_duration_ms）
        monitor.finish_workflow(context, success=True)
        
        # 验证自动计算的持续时间
        completed = monitor.completed_workflows[0]
        assert completed.metadata["total_duration_ms"] >= 100.0  # 至少100ms
    
    # ========== 性能瓶颈检测测试 ==========
    
    def test_bottleneck_detection(self, monitor):
        """测试性能瓶颈检测"""
        context = monitor.start_workflow(request_id="test-006", user_id="user-123")
        
        # 记录一个超过阈值的步骤
        monitor.record_step(
            context=context,
            step_number=1,
            step_name="慢查询",
            duration_ms=1500.0,  # 超过1000ms阈值
            success=True
        )
        
        # 验证瓶颈被记录
        assert len(monitor.bottlenecks) == 1
        bottleneck = monitor.bottlenecks[0]
        assert bottleneck.request_id == "test-006"
        assert bottleneck.step_number == 1
        assert bottleneck.step_name == "慢查询"
        assert bottleneck.duration_ms == 1500.0
        assert bottleneck.threshold_ms == 1000.0
        
        # 验证Prometheus指标更新
        assert monitor.prometheus_metrics["workflow_bottleneck_total"] == 1
    
    def test_no_bottleneck_for_fast_step(self, monitor):
        """测试快速步骤不触发瓶颈检测"""
        context = monitor.start_workflow(request_id="test-007", user_id="user-123")
        
        # 记录一个低于阈值的步骤
        monitor.record_step(
            context=context,
            step_number=1,
            step_name="快速查询",
            duration_ms=500.0,  # 低于1000ms阈值
            success=True
        )
        
        # 验证没有瓶颈被记录
        assert len(monitor.bottlenecks) == 0
        assert monitor.prometheus_metrics["workflow_bottleneck_total"] == 0
    
    def test_get_bottlenecks(self, monitor):
        """测试获取性能瓶颈列表"""
        context = monitor.start_workflow(request_id="test-008", user_id="user-123")
        
        # 记录多个步骤，其中一些超过阈值
        monitor.record_step(context, 1, "步骤1", 500.0, True)
        monitor.record_step(context, 2, "步骤2", 1200.0, True)
        monitor.record_step(context, 3, "步骤3", 800.0, True)
        monitor.record_step(context, 4, "步骤4", 1500.0, True)
        
        # 获取所有瓶颈
        bottlenecks = monitor.get_bottlenecks()
        
        assert len(bottlenecks) == 2
        # 验证按持续时间降序排序
        assert bottlenecks[0].duration_ms == 1500.0
        assert bottlenecks[1].duration_ms == 1200.0
    
    def test_get_bottlenecks_with_custom_threshold(self, monitor):
        """测试使用自定义阈值获取瓶颈"""
        context = monitor.start_workflow(request_id="test-009", user_id="user-123")
        
        # 记录多个步骤
        monitor.record_step(context, 1, "步骤1", 1200.0, True)
        monitor.record_step(context, 2, "步骤2", 1500.0, True)
        
        # 使用更高的阈值
        bottlenecks = monitor.get_bottlenecks(threshold_ms=1300.0)
        
        # 只有1500ms的步骤应该被返回
        assert len(bottlenecks) == 1
        assert bottlenecks[0].duration_ms == 1500.0
    
    def test_get_bottlenecks_with_time_window(self, monitor):
        """测试使用时间窗口获取瓶颈"""
        context = monitor.start_workflow(request_id="test-010", user_id="user-123")
        
        # 记录一个瓶颈
        monitor.record_step(context, 1, "步骤1", 1200.0, True)
        
        # 等待一小段时间
        time.sleep(0.1)
        
        # 记录另一个瓶颈
        monitor.record_step(context, 2, "步骤2", 1500.0, True)
        
        # 获取最近0.05秒的瓶颈（应该只有步骤2）
        bottlenecks = monitor.get_bottlenecks(time_window_seconds=0.05)
        
        assert len(bottlenecks) == 1
        assert bottlenecks[0].step_number == 2
    
    # ========== 指标导出测试 ==========
    
    def test_export_prometheus_metrics(self, monitor):
        """测试导出Prometheus格式的指标"""
        # 创建一些工作流数据
        context1 = monitor.start_workflow(request_id="test-011", user_id="user-123")
        monitor.record_step(context1, 1, "步骤1", 500.0, True)
        monitor.record_step(context1, 2, "步骤2", 300.0, True)
        monitor.finish_workflow(context1, success=True, total_duration_ms=800.0)
        
        context2 = monitor.start_workflow(request_id="test-012", user_id="user-456")
        monitor.record_step(context2, 1, "步骤1", 600.0, True)
        monitor.finish_workflow(context2, success=False, total_duration_ms=600.0)
        
        # 导出Prometheus指标
        metrics = monitor.export_metrics(format="prometheus")
        
        # 验证指标格式
        assert "workflow_total_duration_seconds" in metrics
        assert "workflow_step_duration_seconds" in metrics
        assert "workflow_success_total" in metrics
        assert "workflow_failure_total" in metrics
        assert "workflow_success_rate" in metrics
        assert "workflow_bottleneck_total" in metrics
        assert "workflow_concurrent_requests" in metrics
        
        # 验证指标值
        assert "workflow_success_total 1" in metrics
        assert "workflow_failure_total 1" in metrics
        assert "workflow_success_rate 0.5" in metrics
        
        # 验证HELP和TYPE注释
        assert "# HELP workflow_total_duration_seconds" in metrics
        assert "# TYPE workflow_total_duration_seconds histogram" in metrics
    
    def test_export_json_metrics(self, monitor):
        """测试导出JSON格式的指标"""
        # 创建一些工作流数据
        context = monitor.start_workflow(request_id="test-013", user_id="user-123")
        monitor.record_step(context, 1, "步骤1", 500.0, True)
        monitor.record_step(context, 2, "步骤2", 1200.0, True)  # 瓶颈
        monitor.finish_workflow(context, success=True, total_duration_ms=1700.0)
        
        # 导出JSON指标
        metrics_str = monitor.export_metrics(format="json")
        metrics = json.loads(metrics_str)
        
        # 验证JSON结构
        assert "timestamp" in metrics
        assert "workflow" in metrics
        assert "duration" in metrics
        assert "steps" in metrics
        
        # 验证工作流指标
        assert metrics["workflow"]["total_completed"] == 1
        assert metrics["workflow"]["total_success"] == 1
        assert metrics["workflow"]["total_failure"] == 0
        assert metrics["workflow"]["success_rate"] == 1.0
        assert metrics["workflow"]["bottleneck_count"] == 1
        
        # 验证持续时间指标
        assert metrics["duration"]["total_workflows"] == 1
        assert metrics["duration"]["avg_duration_seconds"] == 1.7
        
        # 验证步骤指标
        assert "步骤1" in metrics["steps"]
        assert "步骤2" in metrics["steps"]
        assert metrics["steps"]["步骤1"]["count"] == 1
        assert metrics["steps"]["步骤1"]["avg_duration_seconds"] == 0.5
    
    def test_export_unsupported_format(self, monitor):
        """测试导出不支持的格式"""
        with pytest.raises(ValueError, match="不支持的导出格式"):
            monitor.export_metrics(format="xml")
    
    def test_get_workflow_summary(self, monitor):
        """测试获取工作流摘要"""
        context = monitor.start_workflow(request_id="test-014", user_id="user-123")
        
        # 记录步骤
        monitor.record_step(context, 1, "步骤1", 500.0, True)
        monitor.record_step(context, 2, "步骤2", 1200.0, True)  # 瓶颈
        monitor.record_step(context, 3, "步骤3", 300.0, True)
        
        # 完成工作流
        monitor.finish_workflow(context, success=True, total_duration_ms=2000.0)
        
        # 获取摘要
        summary = monitor.get_workflow_summary("test-014")
        
        assert summary is not None
        assert summary["request_id"] == "test-014"
        assert summary["user_id"] == "user-123"
        assert summary["total_duration_ms"] == 2000.0
        assert summary["total_steps"] == 3
        assert summary["success"] is True
        
        # 验证步骤详情
        assert len(summary["steps"]) == 3
        assert summary["steps"][0]["step_number"] == 1
        assert summary["steps"][0]["is_bottleneck"] is False
        assert summary["steps"][1]["step_number"] == 2
        assert summary["steps"][1]["is_bottleneck"] is True
        
        # 验证瓶颈统计
        assert summary["bottleneck_count"] == 1
        assert len(summary["bottlenecks"]) == 1
        assert summary["bottlenecks"][0]["step_number"] == 2
        assert summary["bottlenecks"][0]["duration_ms"] == 1200.0
    
    def test_get_workflow_summary_not_found(self, monitor):
        """测试获取不存在的工作流摘要"""
        summary = monitor.get_workflow_summary("non-existent")
        assert summary is None
    
    def test_get_workflow_summary_active_workflow(self, monitor):
        """测试获取活跃工作流的摘要"""
        context = monitor.start_workflow(request_id="test-015", user_id="user-123")
        monitor.record_step(context, 1, "步骤1", 500.0, True)
        
        # 不完成工作流，直接获取摘要
        summary = monitor.get_workflow_summary("test-015")
        
        assert summary is not None
        assert summary["request_id"] == "test-015"
        assert summary["total_steps"] == 1
        assert summary["success"] is None  # 未完成
    
    # ========== 并发和边界测试 ==========
    
    def test_multiple_concurrent_workflows(self, monitor):
        """测试多个并发工作流"""
        # 启动多个工作流
        context1 = monitor.start_workflow(request_id="test-016", user_id="user-1")
        context2 = monitor.start_workflow(request_id="test-017", user_id="user-2")
        context3 = monitor.start_workflow(request_id="test-018", user_id="user-3")
        
        assert len(monitor.active_workflows) == 3
        assert monitor.prometheus_metrics["workflow_concurrent_requests"] == 3
        
        # 完成一个工作流
        monitor.finish_workflow(context1, success=True)
        
        assert len(monitor.active_workflows) == 2
        assert monitor.prometheus_metrics["workflow_concurrent_requests"] == 2
        
        # 完成剩余工作流
        monitor.finish_workflow(context2, success=True)
        monitor.finish_workflow(context3, success=False)
        
        assert len(monitor.active_workflows) == 0
        assert monitor.prometheus_metrics["workflow_concurrent_requests"] == 0
        assert len(monitor.completed_workflows) == 3
    
    def test_workflow_context_duration(self, monitor):
        """测试工作流上下文持续时间计算"""
        context = monitor.start_workflow(request_id="test-019", user_id="user-123")
        
        # 等待一小段时间
        time.sleep(0.1)
        
        # 获取持续时间
        duration_ms = context.get_duration_ms()
        
        assert duration_ms >= 100.0  # 至少100ms
        assert duration_ms < 200.0   # 不应该超过200ms
    
    def test_max_history_size(self, monitor):
        """测试历史记录大小限制"""
        # 创建超过max_history_size的工作流
        for i in range(150):  # max_history_size=100
            context = monitor.start_workflow(request_id=f"test-{i}", user_id="user-123")
            monitor.finish_workflow(context, success=True)
        
        # 验证历史记录被限制
        assert len(monitor.completed_workflows) == 100
    
    def test_prometheus_metrics_percentiles(self, monitor):
        """测试Prometheus指标的分位数计算"""
        # 创建多个工作流，持续时间不同
        durations = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        
        for i, duration in enumerate(durations):
            context = monitor.start_workflow(request_id=f"test-{i}", user_id="user-123")
            monitor.finish_workflow(context, success=True, total_duration_ms=duration)
        
        # 导出Prometheus指标
        metrics = monitor.export_metrics(format="prometheus")
        
        # 验证分位数存在
        assert 'quantile="0.5"' in metrics  # 中位数
        assert 'quantile="0.9"' in metrics  # P90
        assert 'quantile="0.95"' in metrics  # P95
        assert 'quantile="0.99"' in metrics  # P99
    
    # ========== 操作性能监控测试（上下文管理器）==========
    
    def test_measure_context_manager(self, monitor):
        """测试性能监控上下文管理器"""
        # 使用上下文管理器
        with monitor.measure("test_operation"):
            time.sleep(0.1)
        
        # 获取统计
        stats = monitor.get_operation_stats("test_operation")
        
        assert stats["count"] == 1
        assert stats["avg"] >= 0.1
        assert stats["min"] >= 0.1
        assert stats["max"] >= 0.1
        assert "median" in stats
        assert "p95" in stats
        assert "p99" in stats
    
    def test_measure_multiple_operations(self, monitor):
        """测试多次操作测量"""
        # 执行多次操作
        for i in range(5):
            with monitor.measure("database_query"):
                time.sleep(0.05)
        
        # 获取统计
        stats = monitor.get_operation_stats("database_query")
        
        assert stats["count"] == 5
        assert stats["avg"] >= 0.05
        assert stats["min"] >= 0.05
        assert stats["max"] >= 0.05
    
    def test_measure_different_operations(self, monitor):
        """测试不同操作的测量"""
        # 测量不同的操作
        with monitor.measure("operation_a"):
            time.sleep(0.1)
        
        with monitor.measure("operation_b"):
            time.sleep(0.2)
        
        # 获取统计
        stats_a = monitor.get_operation_stats("operation_a")
        stats_b = monitor.get_operation_stats("operation_b")
        
        assert stats_a["count"] == 1
        assert stats_b["count"] == 1
        assert stats_a["avg"] < stats_b["avg"]
    
    def test_measure_with_exception(self, monitor):
        """测试上下文管理器中的异常处理"""
        # 即使发生异常，也应该记录时间
        try:
            with monitor.measure("failing_operation"):
                time.sleep(0.05)
                raise ValueError("测试异常")
        except ValueError:
            pass
        
        # 验证操作仍然被记录
        stats = monitor.get_operation_stats("failing_operation")
        
        assert stats["count"] == 1
        assert stats["avg"] >= 0.05
    
    def test_get_operation_stats_not_found(self, monitor):
        """测试获取不存在的操作统计"""
        stats = monitor.get_operation_stats("non_existent_operation")
        
        assert stats["operation"] == "non_existent_operation"
        assert stats["count"] == 0
        assert "message" in stats
        assert "没有找到该操作的统计数据" in stats["message"]
    
    def test_measure_max_history_size(self, monitor):
        """测试操作统计的历史记录限制"""
        # 执行超过1000次操作
        for i in range(1100):
            with monitor.measure("frequent_operation"):
                pass
        
        # 验证只保留最近1000次记录
        stats = monitor.get_operation_stats("frequent_operation")
        assert stats["count"] == 1000
    
    def test_measure_percentile_calculation(self, monitor):
        """测试百分位数计算"""
        # 创建一系列持续时间不同的操作
        durations = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
        
        for duration in durations:
            with monitor.measure("varied_operation"):
                time.sleep(duration)
        
        # 获取统计
        stats = monitor.get_operation_stats("varied_operation")
        
        assert stats["count"] == 10
        assert stats["min"] >= 0.01
        assert stats["max"] >= 0.10
        assert stats["median"] >= 0.05
        assert stats["p95"] >= 0.09
        assert stats["p99"] >= 0.09
    
    def test_reset_statistics_clears_operations(self, monitor):
        """测试重置统计数据会清除操作记录"""
        # 记录一些操作
        with monitor.measure("test_operation"):
            time.sleep(0.05)
        
        # 验证操作被记录
        stats_before = monitor.get_operation_stats("test_operation")
        assert stats_before["count"] == 1
        
        # 重置统计
        monitor.reset_statistics()
        
        # 验证操作记录被清除
        stats_after = monitor.get_operation_stats("test_operation")
        assert stats_after["count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
