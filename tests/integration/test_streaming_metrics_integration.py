# -*- coding: utf-8 -*-
"""
流式会话指标集成测试

测试流式会话指标在实际API调用中的记录功能。

版本: v1.0.0
日期: 2025-12-21
作者: BUILD_BODY Team
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
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


class TestStreamingMetricsIntegration:
    """流式会话指标集成测试"""
    
    @pytest.fixture
    def mock_workflow_stream(self):
        """模拟流式工作流执行器"""
        async def mock_stream(query_text, user_id, domain, user_profile, session_id):
            """模拟流式事件生成"""
            # 模拟首字节
            await asyncio.sleep(0.1)
            yield {"type": "start", "session_id": session_id}
            
            # 模拟内容块
            for i in range(5):
                await asyncio.sleep(0.05)
                yield {"type": "chunk", "content": f"测试内容{i}"}
            
            # 模拟完成
            yield {"type": "done", "success": True}
        
        return mock_stream
    
    @pytest.fixture
    def mock_workflow_stream_error(self):
        """模拟流式工作流失败"""
        async def mock_stream_error(query_text, user_id, domain, user_profile, session_id):
            """模拟流式错误"""
            await asyncio.sleep(0.1)
            yield {"type": "start", "session_id": session_id}
            raise Exception("模拟流式错误")
        
        return mock_stream_error
    
    @pytest.mark.asyncio
    async def test_streaming_metrics_recorded_on_success(self, mock_workflow_stream):
        """测试成功流式会话记录指标"""
        # 获取初始指标值
        initial_success = streaming_success._value.get()
        
        # 模拟流式会话
        session_id = "test-session-123"
        user_id = "test-user"
        
        metrics = StreamingSessionMetrics(
            session_id=session_id,
            user_id=user_id,
            start_time=time.time()
        )
        
        total_tokens = 0
        first_byte_sent = False
        
        # 执行流式工作流
        async for event in mock_workflow_stream(
            query_text="测试查询",
            user_id=user_id,
            domain="fitness",
            user_profile=None,
            session_id=session_id
        ):
            # 记录首字节时间
            if not first_byte_sent:
                metrics.first_byte_time = time.time()
                first_byte_sent = True
            
            # 统计令牌
            if event.get("type") == "chunk" and "content" in event:
                total_tokens += len(event["content"])
        
        # 完成会话
        metrics.end_time = time.time()
        metrics.total_tokens = total_tokens
        metrics.success = True
        
        # 记录指标
        record_streaming_metrics(metrics)
        
        # 验证指标
        assert metrics.ttfb is not None
        assert metrics.ttfb > 0
        assert metrics.duration is not None
        assert metrics.duration > 0
        assert metrics.tokens_per_second > 0
        
        # 验证成功计数器增加
        final_success = streaming_success._value.get()
        assert final_success == initial_success + 1
    
    @pytest.mark.asyncio
    async def test_streaming_metrics_recorded_on_failure(self, mock_workflow_stream_error):
        """测试失败流式会话记录指标"""
        # 获取初始指标值
        initial_failure = streaming_failure._value.get()
        
        # 模拟流式会话
        session_id = "test-session-456"
        user_id = "test-user"
        
        metrics = StreamingSessionMetrics(
            session_id=session_id,
            user_id=user_id,
            start_time=time.time()
        )
        
        first_byte_sent = False
        
        # 执行流式工作流（预期失败）
        try:
            async for event in mock_workflow_stream_error(
                query_text="测试查询",
                user_id=user_id,
                domain="fitness",
                user_profile=None,
                session_id=session_id
            ):
                # 记录首字节时间
                if not first_byte_sent:
                    metrics.first_byte_time = time.time()
                    first_byte_sent = True
        except Exception as e:
            # 记录失败
            metrics.end_time = time.time()
            metrics.success = False
            metrics.error_message = str(e)
        
        # 记录指标
        record_streaming_metrics(metrics)
        
        # 验证指标
        assert metrics.ttfb is not None
        assert metrics.duration is not None
        assert metrics.success is False
        assert metrics.error_message == "模拟流式错误"
        
        # 验证失败计数器增加
        final_failure = streaming_failure._value.get()
        assert final_failure == initial_failure + 1
    
    @pytest.mark.asyncio
    async def test_streaming_metrics_ttfb_accuracy(self, mock_workflow_stream):
        """测试TTFB指标准确性"""
        session_id = "test-session-789"
        user_id = "test-user"
        
        start_time = time.time()
        
        metrics = StreamingSessionMetrics(
            session_id=session_id,
            user_id=user_id,
            start_time=start_time
        )
        
        first_byte_sent = False
        
        # 执行流式工作流
        async for event in mock_workflow_stream(
            query_text="测试查询",
            user_id=user_id,
            domain="fitness",
            user_profile=None,
            session_id=session_id
        ):
            if not first_byte_sent:
                first_byte_time = time.time()
                metrics.first_byte_time = first_byte_time
                first_byte_sent = True
                
                # 验证TTFB在合理范围内（0.1秒左右）
                ttfb = first_byte_time - start_time
                assert 0.05 < ttfb < 0.2, f"TTFB {ttfb} 不在预期范围内"
                break
        
        # 验证metrics.ttfb属性
        assert metrics.ttfb is not None
        assert 0.05 < metrics.ttfb < 0.2
    
    @pytest.mark.asyncio
    async def test_streaming_metrics_tokens_per_second(self, mock_workflow_stream):
        """测试令牌速率计算"""
        session_id = "test-session-abc"
        user_id = "test-user"
        
        metrics = StreamingSessionMetrics(
            session_id=session_id,
            user_id=user_id,
            start_time=time.time()
        )
        
        total_tokens = 0
        first_byte_sent = False
        
        # 执行流式工作流
        async for event in mock_workflow_stream(
            query_text="测试查询",
            user_id=user_id,
            domain="fitness",
            user_profile=None,
            session_id=session_id
        ):
            if not first_byte_sent:
                metrics.first_byte_time = time.time()
                first_byte_sent = True
            
            if event.get("type") == "chunk" and "content" in event:
                total_tokens += len(event["content"])
        
        # 完成会话
        metrics.end_time = time.time()
        metrics.total_tokens = total_tokens
        metrics.success = True
        
        # 验证令牌速率
        assert metrics.tokens_per_second > 0
        assert metrics.duration > 0
        
        # 手动计算验证
        expected_rate = total_tokens / metrics.duration
        assert abs(metrics.tokens_per_second - expected_rate) < 0.01
    
    @pytest.mark.asyncio
    async def test_streaming_metrics_exception_handling(self):
        """测试指标记录异常不影响主业务"""
        session_id = "test-session-def"
        user_id = "test-user"
        
        metrics = StreamingSessionMetrics(
            session_id=session_id,
            user_id=user_id,
            start_time=time.time()
        )
        
        # 模拟指标记录失败（通过传入无效数据）
        metrics.first_byte_time = None  # 无效的首字节时间
        metrics.end_time = time.time()
        metrics.total_tokens = 100
        metrics.success = True
        
        # 记录指标不应抛出异常
        try:
            record_streaming_metrics(metrics)
            # 应该成功（静默失败）
            assert True
        except Exception as e:
            pytest.fail(f"指标记录不应抛出异常: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
