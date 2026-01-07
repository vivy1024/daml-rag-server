# -*- coding: utf-8 -*-
"""
Prometheus流式会话指标验收测试

验证流式会话指标是否正确暴露到Prometheus端点。

版本: v1.0.0
日期: 2025-12-21
作者: BUILD_BODY Team
"""

import pytest
import time
from fastapi.testclient import TestClient

from src.api.main import app
from src.framework.monitoring.streaming_metrics import (
    streaming_ttfb,
    streaming_duration,
    streaming_tokens_per_second,
    streaming_success,
    streaming_failure,
    StreamingSessionMetrics,
    record_streaming_metrics
)


class TestPrometheusStreamingMetrics:
    """Prometheus流式会话指标验收测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    def test_prometheus_endpoint_accessible(self, client):
        """测试Prometheus端点可访问"""
        response = client.get("/api/health/metrics/prometheus")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
    
    def test_streaming_metrics_exposed(self, client):
        """测试流式会话指标被暴露"""
        # 先记录一些指标
        metrics = StreamingSessionMetrics(
            session_id="test-session-001",
            user_id="test-user",
            start_time=time.time()
        )
        metrics.first_byte_time = time.time() + 0.5
        metrics.end_time = time.time() + 2.0
        metrics.total_tokens = 100
        metrics.success = True
        
        record_streaming_metrics(metrics)
        
        # 获取Prometheus输出
        response = client.get("/api/health/metrics/prometheus")
        content = response.text
        
        # 验证5个流式会话指标存在
        assert "streaming_session_ttfb_seconds" in content, "TTFB指标未暴露"
        assert "streaming_session_duration_seconds" in content, "持续时间指标未暴露"
        assert "streaming_session_tokens_per_second" in content, "令牌速率指标未暴露"
        assert "streaming_session_success_total" in content, "成功计数指标未暴露"
        assert "streaming_session_failure_total" in content, "失败计数指标未暴露"
    
    def test_streaming_metrics_format(self, client):
        """测试流式会话指标格式正确"""
        # 记录测试指标
        metrics = StreamingSessionMetrics(
            session_id="test-session-002",
            user_id="test-user",
            start_time=time.time()
        )
        metrics.first_byte_time = time.time() + 0.3
        metrics.end_time = time.time() + 1.5
        metrics.total_tokens = 50
        metrics.success = True
        
        record_streaming_metrics(metrics)
        
        # 获取Prometheus输出
        response = client.get("/api/health/metrics/prometheus")
        content = response.text
        
        # 验证指标格式（Prometheus格式）
        # HELP注释
        assert "# HELP streaming_session_ttfb_seconds" in content
        assert "# HELP streaming_session_duration_seconds" in content
        assert "# HELP streaming_session_tokens_per_second" in content
        assert "# HELP streaming_session_success_total" in content
        assert "# HELP streaming_session_failure_total" in content
        
        # TYPE注释
        assert "# TYPE streaming_session_ttfb_seconds histogram" in content
        assert "# TYPE streaming_session_duration_seconds histogram" in content
        assert "# TYPE streaming_session_tokens_per_second histogram" in content
        assert "# TYPE streaming_session_success_total counter" in content
        assert "# TYPE streaming_session_failure_total counter" in content
    
    def test_streaming_metrics_values(self, client):
        """测试流式会话指标值正确"""
        # 获取初始值
        initial_response = client.get("/api/health/metrics/prometheus")
        initial_content = initial_response.text
        
        # 提取初始成功计数
        initial_success_count = self._extract_counter_value(
            initial_content,
            "streaming_session_success_total"
        )
        
        # 记录新的成功会话
        metrics = StreamingSessionMetrics(
            session_id="test-session-003",
            user_id="test-user",
            start_time=time.time()
        )
        metrics.first_byte_time = time.time() + 0.2
        metrics.end_time = time.time() + 1.0
        metrics.total_tokens = 80
        metrics.success = True
        
        record_streaming_metrics(metrics)
        
        # 获取更新后的值
        final_response = client.get("/api/health/metrics/prometheus")
        final_content = final_response.text
        
        final_success_count = self._extract_counter_value(
            final_content,
            "streaming_session_success_total"
        )
        
        # 验证计数器增加
        assert final_success_count == initial_success_count + 1, \
            f"成功计数器应该增加1，但从{initial_success_count}变为{final_success_count}"
    
    def test_streaming_metrics_failure_count(self, client):
        """测试流式会话失败计数"""
        # 获取初始失败计数
        initial_response = client.get("/api/health/metrics/prometheus")
        initial_content = initial_response.text
        
        initial_failure_count = self._extract_counter_value(
            initial_content,
            "streaming_session_failure_total"
        )
        
        # 记录失败会话
        metrics = StreamingSessionMetrics(
            session_id="test-session-004",
            user_id="test-user",
            start_time=time.time()
        )
        metrics.first_byte_time = time.time() + 0.1
        metrics.end_time = time.time() + 0.5
        metrics.total_tokens = 0
        metrics.success = False
        metrics.error_message = "测试错误"
        
        record_streaming_metrics(metrics)
        
        # 获取更新后的值
        final_response = client.get("/api/health/metrics/prometheus")
        final_content = final_response.text
        
        final_failure_count = self._extract_counter_value(
            final_content,
            "streaming_session_failure_total"
        )
        
        # 验证失败计数器增加
        assert final_failure_count == initial_failure_count + 1, \
            f"失败计数器应该增加1，但从{initial_failure_count}变为{final_failure_count}"
    
    def _extract_counter_value(self, content: str, metric_name: str) -> float:
        """从Prometheus输出中提取计数器值"""
        for line in content.split('\n'):
            # 跳过注释和空行
            if line.startswith('#') or not line.strip():
                continue
            
            # 查找指标行
            if line.startswith(metric_name):
                # 格式: metric_name value
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        return float(parts[-1])
                    except ValueError:
                        continue
        
        return 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
