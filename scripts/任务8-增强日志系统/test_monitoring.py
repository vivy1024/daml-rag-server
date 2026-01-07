#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
监控系统简单测试脚本

不依赖pytest，直接测试监控系统功能
"""

import sys
import time
sys.path.insert(0, '/app')

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
    print("=" * 60)
    print("测试1: 结构化日志")
    print("=" * 60)
    
    logger = get_logger("test_logger")
    
    # 设置trace_id
    trace_id = set_trace_id()
    print(f"✓ trace_id已设置: {trace_id}")
    assert trace_id is not None
    assert get_trace_id() == trace_id
    
    # 记录日志
    logger.info("测试信息", test_key="test_value")
    logger.warning("测试警告", warning_level=1)
    logger.error("测试错误", error_code=500)
    print("✓ 日志记录成功")
    
    print()


def test_metrics_collector():
    """测试指标收集"""
    print("=" * 60)
    print("测试2: 指标收集")
    print("=" * 60)
    
    metrics = get_metrics_collector()
    
    # 测试计数器
    counter = metrics.get_metric("requests_total")
    assert counter is not None
    print("✓ 计数器获取成功")
    
    initial_count = counter.get_count(labels={"endpoint": "/test", "method": "GET", "status": "200"})
    counter.inc(labels={"endpoint": "/test", "method": "GET", "status": "200"})
    new_count = counter.get_count(labels={"endpoint": "/test", "method": "GET", "status": "200"})
    assert new_count == initial_count + 1
    print(f"✓ 计数器递增成功: {initial_count} -> {new_count}")
    
    # 测试直方图
    histogram = metrics.get_metric("request_duration_seconds")
    assert histogram is not None
    print("✓ 直方图获取成功")
    
    histogram.observe(0.5, labels={"endpoint": "/test", "method": "GET", "status": "200"})
    stats = histogram.get_statistics(labels={"endpoint": "/test", "method": "GET", "status": "200"})
    assert stats["count"] > 0
    assert stats["mean"] > 0
    print(f"✓ 直方图统计: count={stats['count']}, mean={stats['mean']:.3f}s")
    
    # 测试仪表
    gauge = metrics.get_metric("cpu_usage_percent")
    assert gauge is not None
    print("✓ 仪表获取成功")
    
    gauge.set(75.5)
    value = gauge.get_value()
    assert value == 75.5
    print(f"✓ 仪表设置成功: {value}%")
    
    print()


def test_alert_system():
    """测试告警系统"""
    print("=" * 60)
    print("测试3: 告警系统")
    print("=" * 60)
    
    alert_system = get_alert_system()
    
    # 添加测试规则
    rule = AlertRule(
        name="test_high_value",
        description="测试值过高",
        metric_name="test_metric",
        condition="gt",
        threshold=100.0,
        severity=AlertSeverity.WARNING,
        duration_seconds=1,
        cooldown_seconds=5
    )
    alert_system.add_rule(rule)
    print("✓ 告警规则添加成功")
    
    # 触发告警
    alert_system.check_metric("test_metric", 150.0)
    print("✓ 第一次检查指标: 150.0 > 100.0")
    
    time.sleep(1.5)
    alert_system.check_metric("test_metric", 150.0)
    print("✓ 第二次检查指标（持续超过1秒）")
    
    # 检查活跃告警
    active_alerts = alert_system.get_active_alerts()
    print(f"✓ 活跃告警数量: {len(active_alerts)}")
    
    # 获取统计
    stats = alert_system.get_alert_statistics(time_window_seconds=3600)
    print(f"✓ 告警统计: 总数={stats['total_alerts']}, 活跃={stats['active_alerts']}")
    
    # 清理
    alert_system.remove_rule("test_high_value")
    print("✓ 告警规则清理成功")
    
    print()


def test_prometheus_export():
    """测试Prometheus格式导出"""
    print("=" * 60)
    print("测试4: Prometheus格式导出")
    print("=" * 60)
    
    metrics = get_metrics_collector()
    
    # 记录一些指标
    metrics.get_metric("requests_total").inc(
        labels={"endpoint": "/test", "method": "GET", "status": "200"}
    )
    print("✓ 指标记录成功")
    
    # 导出Prometheus格式
    prometheus_text = metrics.export_prometheus()
    assert prometheus_text is not None
    assert "requests_total" in prometheus_text
    assert "# HELP" in prometheus_text
    assert "# TYPE" in prometheus_text
    print("✓ Prometheus格式导出成功")
    print(f"✓ 导出内容长度: {len(prometheus_text)} 字符")
    
    # 显示部分内容
    lines = prometheus_text.split('\n')[:10]
    print("\n前10行内容:")
    for line in lines:
        if line.strip():
            print(f"  {line}")
    
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("DAML-RAG 监控系统测试")
    print("=" * 60)
    print()
    
    try:
        test_structured_logger()
        test_metrics_collector()
        test_alert_system()
        test_prometheus_export()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ 测试失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
