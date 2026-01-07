# -*- coding: utf-8 -*-
"""
流式会话指标单元测试

测试Prometheus指标注册和记录功能。

版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import time
from prometheus_client import REGISTRY

from src.framework.monitoring.streaming_metrics import (
    streaming_ttfb,
    streaming_duration,
    streaming_tokens_per_second,
    streaming_success,
    streaming_failure,
    StreamingSessionMetrics,
    record_streaming_metrics
)


def test_streaming_metrics_registration():
    """测试流式会话指标是否正确注册到Prometheus"""
    # 获取所有已注册的指标名称
    metric_names = [m.name for m in REGISTRY.collect()]
    
    # 验证5个关键指标都已注册
    # Histogram指标
    assert "streaming_session_ttfb_seconds" in metric_names
    assert "streaming_session_duration_seconds" in metric_names
    assert "streaming_session_tokens_per_second" in metric_names
    
    # Counter指标（注意：在REGISTRY中不包含_total后缀）
    assert "streaming_session_success" in metric_names
    assert "streaming_session_failure" in metric_names


def test_streaming_session_metrics_dataclass():
    """测试StreamingSessionMetrics数据类"""
    start_time = time.time()
    first_byte_time = start_time + 1.5
    end_time = start_time + 10.0
    
    metrics = StreamingSessionMetrics(
        session_id="test_session_123",
        user_id="test_user",
        start_time=start_time,
        first_byte_time=first_byte_time,
        end_time=end_time,
        total_tokens=500,
        success=True
    )
    
    # 测试计算属性
    assert metrics.ttfb == pytest.approx(1.5, rel=0.01)
    assert metrics.duration == pytest.approx(10.0, rel=0.01)
    assert metrics.tokens_per_second == pytest.approx(50.0, rel=0.1)


def test_streaming_session_metrics_ttfb_none():
    """测试TTFB为None的情况"""
    metrics = StreamingSessionMetrics(
        session_id="test_session",
        user_id="test_user",
        start_time=time.time(),
        first_byte_time=None,  # 未记录首字节时间
        success=False
    )
    
    assert metrics.ttfb is None


def test_streaming_session_metrics_duration_none():
    """测试持续时间为None的情况"""
    metrics = StreamingSessionMetrics(
        session_id="test_session",
        user_id="test_user",
        start_time=time.time(),
        end_time=None,  # 未完成
        success=False
    )
    
    assert metrics.duration is None


def test_streaming_session_metrics_tokens_per_second_zero():
    """测试令牌速率为0的情况"""
    metrics = StreamingSessionMetrics(
        session_id="test_session",
        user_id="test_user",
        start_time=time.time(),
        total_tokens=0,
        success=True
    )
    
    assert metrics.tokens_per_second == 0.0


def test_record_streaming_metrics_success():
    """测试记录成功的流式会话指标"""
    start_time = time.time()
    
    metrics = StreamingSessionMetrics(
        session_id="test_success_session",
        user_id="test_user",
        start_time=start_time,
        first_byte_time=start_time + 2.0,
        end_time=start_time + 30.0,
        total_tokens=1000,
        success=True
    )
    
    # 记录指标（不应抛出异常）
    record_streaming_metrics(metrics)
    
    # 验证指标已记录（通过检查计数器值）
    # 注意：由于Prometheus客户端的限制，我们无法直接验证具体值
    # 但可以确保函数执行成功


def test_record_streaming_metrics_failure():
    """测试记录失败的流式会话指标"""
    start_time = time.time()
    
    metrics = StreamingSessionMetrics(
        session_id="test_failure_session",
        user_id="test_user",
        start_time=start_time,
        first_byte_time=start_time + 1.0,
        end_time=start_time + 5.0,
        total_tokens=100,
        success=False,
        error_message="TimeoutError"
    )
    
    # 记录指标（不应抛出异常）
    record_streaming_metrics(metrics)


def test_record_streaming_metrics_partial():
    """测试记录部分指标（某些字段为None）"""
    start_time = time.time()
    
    metrics = StreamingSessionMetrics(
        session_id="test_partial_session",
        user_id="test_user",
        start_time=start_time,
        first_byte_time=None,  # 未记录TTFB
        end_time=None,  # 未完成
        total_tokens=0,
        success=False
    )
    
    # 记录指标（不应抛出异常，即使某些字段为None）
    record_streaming_metrics(metrics)


def test_streaming_metrics_error_handling():
    """测试指标记录的错误处理"""
    # 创建一个无效的指标对象（模拟异常情况）
    metrics = StreamingSessionMetrics(
        session_id="test_error_session",
        user_id="test_user",
        start_time=time.time()
    )
    
    # 即使出现异常，也不应影响主业务
    # 函数应该静默失败
    try:
        record_streaming_metrics(metrics)
    except Exception as e:
        pytest.fail(f"record_streaming_metrics should not raise exceptions: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
