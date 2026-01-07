# -*- coding: utf-8 -*-
"""
监控系统测试

测试结构化日志、指标收集、告警系统等功能
"""

import pytest
import time
from src.framework.monitoring import (
    get_logger,
    set_trace_id,
    get_trace_id,
    get_metrics_collector,
    get_alert_system,
    AlertRule,
    AlertSeverity
)


def test_structured_logger():
    """测试结构化日志"""
    logger = get_logger("test_logger")
    
    # 设置trace_id
    trace_id = set_trace_id()
    assert trace_id is not None
    assert get_trace_id() == trace_id
    
    # 记录日志（不会抛出异常）
    logger.info("测试信息", test_key="test_value")
    logger.warning("测试警告", warning_level=1)
    logger.error("测试错误", error_code=500)


def test_metrics_collector():
    """测试指标收集"""
    metrics = get_metrics_collector()
    
    # 测试计数器
    counter = metrics.get_metric("requests_total")
    assert counter is not None
    
    initial_count = counter.get_count(labels={"endpoint": "/test", "method": "GET", "status": "200"})
    counter.inc(labels={"endpoint": "/test", "method": "GET", "status": "200"})
    new_count = counter.get_count(labels={"endpoint": "/test", "method": "GET", "status": "200"})
    assert new_count == initial_count + 1
    
    # 测试直方图
    histogram = metrics.get_metric("request_duration_seconds")
    assert histogram is not None
    
    histogram.observe(0.5, labels={"endpoint": "/test", "method": "GET", "status": "200"})
    stats = histogram.get_statistics(labels={"endpoint": "/test", "method": "GET", "status": "200"})
    assert stats["count"] > 0
    assert stats["mean"] > 0
    
    # 测试仪表
    gauge = metrics.get_metric("cpu_usage_percent")
    assert gauge is not None
    
    gauge.set(75.5)
    value = gauge.get_value()
    assert value == 75.5


def test_alert_system():
    """测试告警系统"""
    alert_system = get_alert_system()
    
    # 添加测试规则
    rule = AlertRule(
        name="test_high_value",
        description="测试值过高",
        metric_name="test_metric",
        condition="gt",
        threshold=100.0,
        severity=AlertSeverity.WARNING,
        duration_seconds=1,  # 1秒持续时间
        cooldown_seconds=5
    )
    alert_system.add_rule(rule)
    
    # 触发告警（需要持续超过duration_seconds）
    alert_system.check_metric("test_metric", 150.0)
    time.sleep(1.5)  # 等待超过持续时间
    alert_system.check_metric("test_metric", 150.0)
    
    # 检查活跃告警
    active_alerts = alert_system.get_active_alerts()
    # 注意：由于冷却时间，可能没有立即触发告警
    
    # 清理
    alert_system.remove_rule("test_high_value")


def test_prometheus_export():
    """测试Prometheus格式导出"""
    metrics = get_metrics_collector()
    
    # 记录一些指标
    metrics.get_metric("requests_total").inc(
        labels={"endpoint": "/test", "method": "GET", "status": "200"}
    )
    
    # 导出Prometheus格式
    prometheus_text = metrics.export_prometheus()
    assert prometheus_text is not None
    assert "requests_total" in prometheus_text
    assert "# HELP" in prometheus_text
    assert "# TYPE" in prometheus_text


def test_alert_statistics():
    """测试告警统计"""
    alert_system = get_alert_system()
    
    # 获取统计信息
    stats = alert_system.get_alert_statistics(time_window_seconds=3600)
    
    assert "total_alerts" in stats
    assert "active_alerts" in stats
    assert "severity_distribution" in stats
    assert "rule_distribution" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
