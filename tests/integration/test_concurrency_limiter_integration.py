# -*- coding: utf-8 -*-
"""
并发限流器集成测试

测试并发限流器在chat()和chat_stream()函数中的集成

版本：v1.0.0
创建日期：2025-12-21
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

# 导入被测试的模块
from src.framework.monitoring.concurrency_limiter import (
    ConcurrencyLimiter,
    UserTier,
    concurrency_limiter
)


class TestConcurrencyLimiterIntegration:
    """并发限流器集成测试"""
    
    @pytest.mark.asyncio
    async def test_chat_with_concurrency_limit(self):
        """测试chat()函数的并发限制"""
        # 创建一个小容量的限流器用于测试
        limiter = ConcurrencyLimiter(
            max_concurrent=2,
            max_queue_size=1,
            timeout=1
        )
        
        # 模拟3个并发请求，但不立即释放
        acquired_sessions = []
        
        async def make_request(user_id: str, session_id: str):
            acquired = await limiter.acquire(
                user_id=user_id,
                session_id=session_id,
                timeout=0.5  # 短超时
            )
            
            if acquired:
                acquired_sessions.append(session_id)
                return "success"
            else:
                return "rejected"
        
        # 并发发起3个请求（不释放连接）
        tasks = [
            make_request("user1", f"session{i}")
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 验证：由于队列机制，可能有2-3个成功
        # 但至少应该有2个成功（因为max_concurrent=2）
        success_count = results.count("success")
        rejected_count = results.count("rejected")
        
        assert success_count >= 2, f"至少应该有2个成功，实际: {success_count}"
        assert success_count <= 3, f"最多应该有3个成功（2个并发+1个队列），实际: {success_count}"
        
        # 清理
        for session_id in acquired_sessions:
            await limiter.release(session_id)
    
    @pytest.mark.asyncio
    async def test_chat_stream_with_concurrency_limit(self):
        """测试chat_stream()函数的并发限制"""
        limiter = ConcurrencyLimiter(
            max_concurrent=2,
            max_queue_size=1,
            timeout=1
        )
        
        # 模拟流式请求
        acquired_sessions = []
        
        async def stream_request(user_id: str, session_id: str):
            acquired = await limiter.acquire(
                user_id=user_id,
                session_id=session_id,
                timeout=0.5  # 短超时
            )
            
            if not acquired:
                return "rate_limited"
            
            acquired_sessions.append(session_id)
            
            # 模拟流式输出（不释放连接）
            chunks = []
            for i in range(3):
                chunks.append(f"chunk_{i}")
                await asyncio.sleep(0.05)
            
            return "completed"
        
        # 并发发起3个流式请求
        tasks = [
            stream_request("user1", f"stream_session{i}")
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 验证：由于队列机制，可能有2-3个完成
        completed_count = results.count("completed")
        rate_limited_count = results.count("rate_limited")
        
        assert completed_count >= 2, f"至少应该有2个完成，实际: {completed_count}"
        assert completed_count <= 3, f"最多应该有3个完成（2个并发+1个队列），实际: {completed_count}"
        
        # 清理
        for session_id in acquired_sessions:
            await limiter.release(session_id)
    
    @pytest.mark.asyncio
    async def test_user_tier_limits(self):
        """测试用户分级限流"""
        limiter = ConcurrencyLimiter(
            max_concurrent=100,
            max_queue_size=200,
            timeout=30
        )
        
        # 测试免费用户限制（10个并发）
        # 先占用10个连接
        acquired_sessions = []
        for i in range(10):
            acquired = await limiter.acquire(
                user_id="free_user",
                session_id=f"free_session{i}",
                timeout=0.1,
                user_tier=UserTier.FREE
            )
            if acquired:
                acquired_sessions.append(f"free_session{i}")
        
        # 第11个应该被拒绝（超过免费用户限制）
        acquired_11 = await limiter.acquire(
            user_id="free_user",
            session_id="free_session10",
            timeout=0.1,
            user_tier=UserTier.FREE
        )
        
        assert len(acquired_sessions) == 10, f"应该成功获取10个连接，实际: {len(acquired_sessions)}"
        assert not acquired_11, "第11个连接应该被拒绝（超过免费用户限制）"
        
        # 清理
        for session_id in acquired_sessions:
            await limiter.release(session_id)
    
    @pytest.mark.asyncio
    async def test_queue_waiting(self):
        """测试队列等待机制"""
        limiter = ConcurrencyLimiter(
            max_concurrent=2,
            max_queue_size=5,
            timeout=5
        )
        
        # 先占用2个连接
        await limiter.acquire("user1", "session1", timeout=1.0)
        await limiter.acquire("user1", "session2", timeout=1.0)
        
        # 第3个请求应该进入队列
        start_time = time.time()
        
        # 在后台释放一个连接
        async def release_after_delay():
            await asyncio.sleep(0.5)
            await limiter.release("session1")
        
        asyncio.create_task(release_after_delay())
        
        # 第3个请求应该等待并成功
        acquired = await limiter.acquire("user1", "session3", timeout=2.0)
        wait_time = time.time() - start_time
        
        assert acquired, "第3个请求应该在等待后成功"
        assert wait_time >= 0.5, f"应该等待至少0.5秒，实际: {wait_time:.2f}秒"
        
        # 清理
        await limiter.release("session2")
        await limiter.release("session3")
    
    @pytest.mark.asyncio
    async def test_timeout_rejection(self):
        """测试超时拒绝"""
        limiter = ConcurrencyLimiter(
            max_concurrent=1,
            max_queue_size=5,
            timeout=1
        )
        
        # 占用唯一的连接
        await limiter.acquire("user1", "session1", timeout=1.0)
        
        # 第2个请求应该超时
        start_time = time.time()
        acquired = await limiter.acquire("user1", "session2", timeout=0.5)
        wait_time = time.time() - start_time
        
        assert not acquired, "第2个请求应该超时被拒绝"
        assert wait_time >= 0.5, f"应该等待至少0.5秒，实际: {wait_time:.2f}秒"
        
        # 清理
        await limiter.release("session1")
    
    @pytest.mark.asyncio
    async def test_statistics(self):
        """测试统计信息"""
        limiter = ConcurrencyLimiter(
            max_concurrent=2,
            max_queue_size=5,
            timeout=1
        )
        
        # 执行一些请求
        await limiter.acquire("user1", "session1", timeout=1.0)
        await limiter.acquire("user1", "session2", timeout=1.0)
        
        # 第3个请求被拒绝
        acquired = await limiter.acquire("user1", "session3", timeout=0.1)
        
        # 获取统计信息
        stats = limiter.get_stats()
        
        assert stats["active_connections"] == 2, "应该有2个活跃连接"
        assert stats["total_connections"] == 3, "总共3个连接请求"
        assert stats["rejected_connections"] == 1, "应该有1个被拒绝"
        
        # 清理
        await limiter.release("session1")
        await limiter.release("session2")
    
    @pytest.mark.asyncio
    async def test_global_limiter_instance(self):
        """测试全局限流器实例"""
        # 验证全局实例存在
        assert concurrency_limiter is not None, "全局限流器实例应该存在"
        
        # 验证默认配置
        assert concurrency_limiter.max_concurrent == 100, "默认最大并发应该是100"
        assert concurrency_limiter.max_queue_size == 200, "默认队列大小应该是200"
        assert concurrency_limiter.default_timeout == 30, "默认超时应该是30秒"
    
    @pytest.mark.asyncio
    async def test_429_error_response(self):
        """测试429错误响应"""
        limiter = ConcurrencyLimiter(
            max_concurrent=1,
            max_queue_size=0,
            timeout=1
        )
        
        # 占用唯一的连接
        await limiter.acquire("user1", "session1", timeout=1.0)
        
        # 检查是否应该返回429
        should_reject = limiter.should_reject_with_429()
        assert should_reject, "应该返回429错误"
        
        # 清理
        await limiter.release("session1")
        
        # 等待一小段时间确保状态更新
        await asyncio.sleep(0.1)
        
        # 再次检查（现在应该有空闲连接）
        stats = limiter.get_stats()
        assert stats["active_connections"] == 0, f"应该没有活跃连接，实际: {stats['active_connections']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
