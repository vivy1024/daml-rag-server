#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心监控模块验证脚本

验证保留的5个核心监控模块是否存在且功能正常：
1. streaming_metrics.py - 流式监控
2. metrics_collector.py - 指标收集
3. structured_logger.py - 结构化日志
4. concurrency_limiter.py - 并发控制
5. prometheus_integration.py - Prometheus集成

Requirements: 2.1, 2.2, 2.3, 2.4, 3.2
"""

import sys
import time
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_streaming_metrics():
    """验证streaming_metrics.py模块"""
    print("\n" + "="*60)
    print("测试 1: streaming_metrics.py")
    print("="*60)
    
    # 1. 验证文件存在
    module_path = Path("src/framework/monitoring/streaming_metrics.py")
    assert module_path.exists(), "❌ streaming_metrics.py文件不存在"
    print("✅ 文件存在: streaming_metrics.py")
    
    # 2. 导入模块
    from framework.monitoring.streaming_metrics import StreamingMonitor
    print("✅ 成功导入StreamingMonitor类")
    
    # 3. 测试StreamingMonitor类
    monitor = StreamingMonitor(max_sessions=100)
    assert monitor is not None
    print("✅ 成功创建StreamingMonitor实例")
    
    # 4. 测试活跃连接数管理
    initial_count = monitor.active_connections
    assert initial_count == 0, f"初始连接数应为0，实际为{initial_count}"
    
    count = monitor.increment_active_connections()
    assert count == 1, f"增加后连接数应为1，实际为{count}"
    
    count = monitor.decrement_active_connections()
    assert count == 0, f"减少后连接数应为0，实际为{count}"
    print("✅ 活跃连接数管理功能正常")
    
    # 5. 测试record_streaming_session方法
    monitor.record_streaming_session(
        user_id="test_user",
        session_id="test_session_1",
        request_id="req_1",
        ttfb_ms=100.0,
        total_duration_ms=1000.0,
        tokens_generated=50,
        success=True
    )
    print("✅ record_streaming_session方法正常")
    
    # 6. 测试get_statistics方法
    stats = monitor.get_statistics(time_window_seconds=60)
    assert stats["total_sessions"] == 1, f"会话数应为1，实际为{stats['total_sessions']}"
    assert stats["successful_sessions"] == 1
    assert stats["failed_sessions"] == 0
    print("✅ get_statistics方法正常")
    print(f"   统计数据: {stats['total_sessions']}个会话, 成功率: {stats['success_rate']*100:.1f}%")
    
    print("\n✅ streaming_metrics.py 所有测试通过")


def test_metrics_collector():
    """验证metrics_collector.py模块"""
    print("\n" + "="*60)
    print("测试 2: metrics_collector.py")
    print("="*60)
    
    # 1. 验证文件存在
    module_path = Path("src/framework/monitoring/metrics_collector.py")
    assert module_path.exists(), "❌ metrics_collector.py文件不存在"
    print("✅ 文件存在: metrics_collector.py")
    
    # 2. 导入模块
    from framework.monitoring.metrics_collector import MetricsCollector
    print("✅ 成功导入MetricsCollector类")
    
    # 3. 测试MetricsCollector类
    collector = MetricsCollector()
    assert collector is not None
    print("✅ 成功创建MetricsCollector实例")
    
    # 4. 测试get_metric方法
    metric = collector.get_metric("requests_total")
    assert metric is not None, "requests_total指标不存在"
    assert metric.name == "requests_total"
    print("✅ get_metric方法正常")
    print(f"   找到指标: {metric.name}")
    
    # 5. 测试export_prometheus方法
    prometheus_text = collector.export_prometheus()
    assert isinstance(prometheus_text, str)
    assert len(prometheus_text) > 0
    assert "# HELP" in prometheus_text
    assert "# TYPE" in prometheus_text
    print("✅ export_prometheus方法正常")
    print(f"   导出文本长度: {len(prometheus_text)} 字符")
    
    print("\n✅ metrics_collector.py 所有测试通过")


def test_structured_logger():
    """验证structured_logger.py模块"""
    print("\n" + "="*60)
    print("测试 3: structured_logger.py")
    print("="*60)
    
    # 1. 验证文件存在
    module_path = Path("src/framework/monitoring/structured_logger.py")
    assert module_path.exists(), "❌ structured_logger.py文件不存在"
    print("✅ 文件存在: structured_logger.py")
    
    # 2. 导入模块
    from framework.monitoring.structured_logger import (
        StructuredLogger,
        set_trace_id,
        get_trace_id,
        clear_trace_id
    )
    print("✅ 成功导入StructuredLogger类和trace_id函数")
    
    # 3. 测试StructuredLogger类
    logger = StructuredLogger("test_logger")
    assert logger is not None
    print("✅ 成功创建StructuredLogger实例")
    
    # 4. 测试日志记录方法
    logger.debug("Debug message", extra_field="value")
    logger.info("Info message", extra_field="value")
    logger.warning("Warning message", extra_field="value")
    logger.error("Error message", extra_field="value")
    print("✅ 日志记录方法正常 (debug, info, warning, error)")
    
    # 5. 测试trace_id功能
    trace_id = set_trace_id("test_trace_123")
    assert trace_id == "test_trace_123"
    
    current_trace_id = get_trace_id()
    assert current_trace_id == "test_trace_123"
    
    clear_trace_id()
    assert get_trace_id() is None
    print("✅ trace_id功能正常 (set, get, clear)")
    
    print("\n✅ structured_logger.py 所有测试通过")


def test_concurrency_limiter():
    """验证concurrency_limiter.py模块"""
    print("\n" + "="*60)
    print("测试 4: concurrency_limiter.py")
    print("="*60)
    
    # 1. 验证文件存在
    module_path = Path("src/framework/monitoring/concurrency_limiter.py")
    assert module_path.exists(), "❌ concurrency_limiter.py文件不存在"
    print("✅ 文件存在: concurrency_limiter.py")
    
    # 2. 导入模块
    from framework.monitoring.concurrency_limiter import (
        ConcurrencyLimiter,
        concurrency_limiter
    )
    print("✅ 成功导入ConcurrencyLimiter类和全局实例")
    
    # 3. 测试ConcurrencyLimiter类
    limiter = ConcurrencyLimiter(max_concurrent=10, max_queue_size=20)
    assert limiter is not None
    print("✅ 成功创建ConcurrencyLimiter实例")
    
    # 4. 测试get_stats方法
    stats = limiter.get_stats()
    assert isinstance(stats, dict)
    assert "max_concurrent" in stats
    assert "active_connections" in stats
    assert stats["max_concurrent"] == 10
    print("✅ get_stats方法正常")
    print(f"   最大并发: {stats['max_concurrent']}, 当前活跃: {stats['active_connections']}")
    
    # 5. 测试全局实例
    assert concurrency_limiter is not None
    global_stats = concurrency_limiter.get_stats()
    assert global_stats["max_concurrent"] == 100
    print("✅ 全局concurrency_limiter实例正常")
    print(f"   全局最大并发: {global_stats['max_concurrent']}")
    
    print("\n✅ concurrency_limiter.py 所有测试通过")


def test_prometheus_integration():
    """验证prometheus_integration.py模块"""
    print("\n" + "="*60)
    print("测试 5: prometheus_integration.py")
    print("="*60)
    
    # 1. 验证文件存在
    module_path = Path("src/framework/monitoring/prometheus_integration.py")
    assert module_path.exists(), "❌ prometheus_integration.py文件不存在"
    print("✅ 文件存在: prometheus_integration.py")
    
    # 2. 导入模块
    from framework.monitoring.prometheus_integration import (
        request_duration,
        errors_total,
        cache_hits,
        cache_misses,
        record_error,
        record_cache_hit,
        record_cache_miss,
        initialize_prometheus_metrics
    )
    print("✅ 成功导入Prometheus指标和函数")
    
    # 3. 验证指标对象存在
    assert request_duration is not None
    assert errors_total is not None
    assert cache_hits is not None
    assert cache_misses is not None
    print("✅ Prometheus指标对象存在")
    
    # 4. 测试记录函数
    record_error("test_error", "test_component")
    record_cache_hit("test_cache", "L1")
    record_cache_miss("test_cache", "L1")
    print("✅ 记录函数正常 (record_error, record_cache_hit, record_cache_miss)")
    
    # 5. 测试初始化函数
    initialize_prometheus_metrics()
    print("✅ initialize_prometheus_metrics函数正常")
    
    print("\n✅ prometheus_integration.py 所有测试通过")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("核心监控模块验证")
    print("="*60)
    print("验证保留的5个核心监控模块是否存在且功能正常")
    
    try:
        # 测试1: streaming_metrics.py
        test_streaming_metrics()
        
        # 测试2: metrics_collector.py
        test_metrics_collector()
        
        # 测试3: structured_logger.py
        test_structured_logger()
        
        # 测试4: concurrency_limiter.py
        test_concurrency_limiter()
        
        # 测试5: prometheus_integration.py
        test_prometheus_integration()
        
        # 总结
        print("\n" + "="*60)
        print("✅ 所有核心监控模块验证通过")
        print("="*60)
        print("\n保留的核心模块:")
        print("  1. ✅ streaming_metrics.py - 流式监控")
        print("  2. ✅ metrics_collector.py - 指标收集")
        print("  3. ✅ structured_logger.py - 结构化日志")
        print("  4. ✅ concurrency_limiter.py - 并发控制")
        print("  5. ✅ prometheus_integration.py - Prometheus集成")
        print("\n所有模块功能正常，可以支持监控API端点。")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
