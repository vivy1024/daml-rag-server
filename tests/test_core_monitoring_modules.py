# -*- coding: utf-8 -*-
"""
核心监控模块验证测试

验证保留的4个核心监控模块是否存在且功能正常：
1. streaming_metrics.py - 流式监控
2. metrics_collector.py - 指标收集
3. structured_logger.py - 结构化日志
4. prometheus_integration.py - Prometheus集成

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import pytest
import time
from pathlib import Path


class TestStreamingMetrics:
    """测试streaming_metrics.py模块"""
    
    def test_module_exists(self):
        """验证streaming_metrics.py文件存在"""
        module_path = Path("src/framework/monitoring/streaming_metrics.py")
        assert module_path.exists(), "streaming_metrics.py should exist"
    
    def test_streaming_monitor_class(self):
        """测试StreamingMonitor类"""
        from src.framework.monitoring.streaming_metrics import StreamingMonitor
        
        # 创建监控器实例
        monitor = StreamingMonitor(max_sessions=100)
        assert monitor is not None
        
        # 测试活跃连接数管理
        initial_count = monitor.active_connections
        assert initial_count == 0
        
        # 增加连接
        count = monitor.increment_active_connections()
        assert count == 1
        assert monitor.active_connections == 1
        
        # 减少连接
        count = monitor.decrement_active_connections()
        assert count == 0
        assert monitor.active_connections == 0
    
    def test_record_session(self):
        """测试record_streaming_session方法"""
        from src.framework.monitoring.streaming_metrics import StreamingMonitor
        
        monitor = StreamingMonitor()
        
        # 记录一个成功的会话
        monitor.record_streaming_session(
            user_id="test_user",
            session_id="test_session_1",
            request_id="req_1",
            ttfb_ms=100.0,
            total_duration_ms=1000.0,
            tokens_generated=50,
            success=True
        )
        
        # 获取统计数据
        stats = monitor.get_statistics(time_window_seconds=60)
        assert stats["total_sessions"] == 1
        assert stats["successful_sessions"] == 1
        assert stats["failed_sessions"] == 0
    
    def test_get_statistics(self):
        """测试get_statistics方法"""
        from src.framework.monitoring.streaming_metrics import StreamingMonitor
        
        monitor = StreamingMonitor()
        
        # 记录多个会话
        for i in range(5):
            monitor.record_streaming_session(
                user_id=f"user_{i}",
                session_id=f"session_{i}",
                ttfb_ms=100.0 + i * 10,
                total_duration_ms=1000.0 + i * 100,
                tokens_generated=50 + i * 5,
                success=True
            )
        
        # 获取统计
        stats = monitor.get_statistics()
        assert stats["total_sessions"] == 5
        assert stats["successful_sessions"] == 5
        assert stats["avg_ttfb_ms"] > 0
        assert stats["avg_duration_ms"] > 0


class TestMetricsCollector:
    """测试metrics_collector.py模块"""
    
    def test_module_exists(self):
        """验证metrics_collector.py文件存在"""
        module_path = Path("src/framework/monitoring/metrics_collector.py")
        assert module_path.exists(), "metrics_collector.py should exist"
    
    def test_metrics_collector_class(self):
        """测试MetricsCollector类"""
        from src.framework.monitoring.metrics_collector import MetricsCollector
        
        collector = MetricsCollector()
        assert collector is not None
    
    def test_get_metric(self):
        """测试get_metric方法"""
        from src.framework.monitoring.metrics_collector import MetricsCollector
        
        collector = MetricsCollector()
        
        # 获取预定义的指标
        metric = collector.get_metric("requests_total")
        assert metric is not None
        assert metric.name == "requests_total"
    
    def test_export_prometheus(self):
        """测试export_prometheus方法"""
        from src.framework.monitoring.metrics_collector import MetricsCollector
        
        collector = MetricsCollector()
        
        # 导出Prometheus格式
        prometheus_text = collector.export_prometheus()
        assert isinstance(prometheus_text, str)
        assert len(prometheus_text) > 0
        
        # 验证包含HELP和TYPE行
        assert "# HELP" in prometheus_text
        assert "# TYPE" in prometheus_text


class TestStructuredLogger:
    """测试structured_logger.py模块"""
    
    def test_module_exists(self):
        """验证structured_logger.py文件存在"""
        module_path = Path("src/framework/monitoring/structured_logger.py")
        assert module_path.exists(), "structured_logger.py should exist"
    
    def test_structured_logger_class(self):
        """测试StructuredLogger类"""
        from src.framework.monitoring.structured_logger import StructuredLogger
        
        logger = StructuredLogger("test_logger")
        assert logger is not None
    
    def test_logging_methods(self):
        """测试日志记录方法"""
        from src.framework.monitoring.structured_logger import StructuredLogger
        
        logger = StructuredLogger("test_logger")
        
        # 测试各种日志级别（不应抛出异常）
        logger.debug("Debug message", extra_field="value")
        logger.info("Info message", extra_field="value")
        logger.warning("Warning message", extra_field="value")
        logger.error("Error message", extra_field="value")
    
    def test_trace_id_functionality(self):
        """测试trace_id功能"""
        from src.framework.monitoring.structured_logger import (
            set_trace_id,
            get_trace_id,
            clear_trace_id
        )
        
        # 设置trace_id
        trace_id = set_trace_id("test_trace_123")
        assert trace_id == "test_trace_123"
        
        # 获取trace_id
        current_trace_id = get_trace_id()
        assert current_trace_id == "test_trace_123"
        
        # 清除trace_id
        clear_trace_id()
        assert get_trace_id() is None


class TestPrometheusIntegration:
    """测试prometheus_integration.py模块"""
    
    def test_module_exists(self):
        """验证prometheus_integration.py文件存在"""
        module_path = Path("src/framework/monitoring/prometheus_integration.py")
        assert module_path.exists(), "prometheus_integration.py should exist"
    
    def test_prometheus_metrics_defined(self):
        """测试Prometheus指标是否定义"""
        from src.framework.monitoring.prometheus_integration import (
            request_duration,
            errors_total,
            cache_hits,
            cache_misses
        )
        
        # 验证指标对象存在
        assert request_duration is not None
        assert errors_total is not None
        assert cache_hits is not None
        assert cache_misses is not None
    
    def test_record_functions(self):
        """测试记录函数"""
        from src.framework.monitoring.prometheus_integration import (
            record_error,
            record_cache_hit,
            record_cache_miss
        )
        
        # 测试记录函数（不应抛出异常）
        record_error("test_error", "test_component")
        record_cache_hit("test_cache", "L1")
        record_cache_miss("test_cache", "L1")
    
    def test_initialize_function(self):
        """测试initialize_prometheus_metrics函数"""
        from src.framework.monitoring.prometheus_integration import (
            initialize_prometheus_metrics
        )
        
        # 调用初始化函数（不应抛出异常）
        initialize_prometheus_metrics()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
