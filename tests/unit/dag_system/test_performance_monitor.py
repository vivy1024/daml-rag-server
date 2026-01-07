# -*- coding: utf-8 -*-
"""
性能监控系统测试

测试性能监控系统的各项功能。

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import pytest
import time
from src.framework.monitoring.performance_monitor import (
    PerformanceMonitor,
    ToolExecutionMetrics,
    DAGExecutionMetrics,
    LLMCallMetrics,
    CacheMetrics
)


@pytest.fixture
def performance_monitor():
    """创建性能监控实例"""
    return PerformanceMonitor(max_history_size=100)


def test_record_tool_execution(performance_monitor):
    """测试记录工具执行"""
    # 创建工具执行指标
    metrics = ToolExecutionMetrics(
        tool_name="test_tool",
        execution_id="exec_001",
        user_id="user_123",
        start_time=time.time(),
        end_time=time.time() + 1.5,
        duration=1.5,
        success=True,
        cache_hit=False
    )
    
    # 记录指标
    performance_monitor.record_tool_execution(metrics)
    
    # 验证统计
    stats = performance_monitor.get_tool_statistics(tool_name="test_tool")
    assert stats["total_calls"] == 1
    assert stats["successful_calls"] == 1
    assert stats["failed_calls"] == 0
    assert stats["cache_misses"] == 1


def test_record_dag_execution(performance_monitor):
    """测试记录DAG执行"""
    # 创建DAG执行指标
    metrics = DAGExecutionMetrics(
        execution_id="dag_001",
        template_id="template_001",
        template_name="测试模板",
        user_id="user_123",
        start_time=time.time(),
        end_time=time.time() + 5.0,
        total_duration=5.0,
        tools_executed=10,
        tools_succeeded=9,
        tools_failed=1,
        tools_cached=3,
        parallel_groups=3,
        max_parallel_degree=4,
        cache_hit_rate=0.3,
        success_rate=0.9
    )
    
    # 记录指标
    performance_monitor.record_dag_execution(metrics)
    
    # 验证统计
    stats = performance_monitor.get_dag_statistics(template_id="template_001")
    assert stats["total_executions"] == 1
    assert stats["duration_stats"]["avg"] == 5.0



def test_record_llm_call(performance_monitor):
    """测试记录LLM调用"""
    # 创建LLM调用指标
    metrics = LLMCallMetrics(
        call_id="llm_001",
        call_type="decision",
        model_name="gpt-4",
        user_id="user_123",
        start_time=time.time(),
        end_time=time.time() + 2.0,
        duration=2.0,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        success=True,
        confidence=0.95,
        fallback_used=False
    )
    
    # 记录指标
    performance_monitor.record_llm_call(metrics)
    
    # 验证统计
    stats = performance_monitor.get_llm_statistics(call_type="decision")
    assert stats["total_calls"] == 1
    assert stats["successful_calls"] == 1
    assert stats["token_stats"]["total_tokens"] == 150


def test_record_cache_metrics(performance_monitor):
    """测试记录缓存指标"""
    # 创建缓存指标
    metrics = CacheMetrics(
        timestamp=time.time(),
        hits=80,
        misses=20,
        hit_rate=0.8,
        preloads=5,
        evictions=2,
        total_size=1024000,
        memory_cache_size=100
    )
    
    # 记录指标
    performance_monitor.record_cache_metrics(metrics)
    
    # 验证统计
    stats = performance_monitor.get_cache_statistics()
    assert stats["current"]["hit_rate"] == 0.8
    assert stats["current"]["preloads"] == 5


def test_performance_snapshot(performance_monitor):
    """测试性能快照"""
    # 添加一些测试数据
    for i in range(5):
        tool_metrics = ToolExecutionMetrics(
            tool_name=f"tool_{i}",
            execution_id=f"exec_{i}",
            user_id="user_123",
            start_time=time.time(),
            end_time=time.time() + 1.0,
            duration=1.0,
            success=True,
            cache_hit=(i % 2 == 0)
        )
        performance_monitor.record_tool_execution(tool_metrics)
    
    # 获取快照
    snapshot = performance_monitor.get_performance_snapshot(time_window_seconds=3600)
    
    # 验证快照
    assert snapshot.dag_executions >= 0
    assert snapshot.cache_hit_rate >= 0.0
    assert len(snapshot.top_tools) > 0


def test_optimization_recommendations(performance_monitor):
    """测试优化建议"""
    # 添加一些慢工具
    for i in range(15):
        metrics = ToolExecutionMetrics(
            tool_name="slow_tool",
            execution_id=f"exec_{i}",
            user_id="user_123",
            start_time=time.time(),
            end_time=time.time() + 3.0,  # 慢工具
            duration=3.0,
            success=True,
            cache_hit=False
        )
        performance_monitor.record_tool_execution(metrics)
    
    # 获取优化建议
    recommendations = performance_monitor.get_optimization_recommendations()
    
    # 验证建议
    assert len(recommendations) > 0
    assert any(r["type"] == "slow_tool" for r in recommendations)


def test_export_metrics(performance_monitor):
    """测试导出指标"""
    # 添加一些测试数据
    metrics = ToolExecutionMetrics(
        tool_name="test_tool",
        execution_id="exec_001",
        user_id="user_123",
        start_time=time.time(),
        end_time=time.time() + 1.0,
        duration=1.0,
        success=True,
        cache_hit=False
    )
    performance_monitor.record_tool_execution(metrics)
    
    # 导出JSON - 新版本使用workflow/duration/steps结构
    json_export = performance_monitor.export_metrics(format="json")
    assert json_export is not None
    assert "workflow" in json_export or "timestamp" in json_export
    
    # 导出Prometheus格式
    prometheus_export = performance_monitor.export_metrics(format="prometheus")
    assert prometheus_export is not None
    assert "workflow" in prometheus_export


def test_reset_statistics(performance_monitor):
    """测试重置统计"""
    # 添加一些数据
    metrics = ToolExecutionMetrics(
        tool_name="test_tool",
        execution_id="exec_001",
        user_id="user_123",
        start_time=time.time(),
        end_time=time.time() + 1.0,
        duration=1.0,
        success=True,
        cache_hit=False
    )
    performance_monitor.record_tool_execution(metrics)
    
    # 验证有数据
    assert len(performance_monitor.tool_executions) > 0
    
    # 重置
    performance_monitor.reset_statistics()
    
    # 验证已清空
    assert len(performance_monitor.tool_executions) == 0
    assert len(performance_monitor.dag_executions) == 0
    assert len(performance_monitor.llm_calls) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
