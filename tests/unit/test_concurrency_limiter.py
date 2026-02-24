# -*- coding: utf-8 -*-
"""
并发限流器单元测试

测试内容：
- 测试并发限制的执行
- 测试队列机制和超时
- 测试用户分级限流
- 测试429错误响应

版本：v1.0.0
创建日期：2025-12-21
"""

import pytest
import asyncio
from src.framework.monitoring.concurrency_limiter import (
    ConcurrencyLimiter,
    UserTier,
    TierConfig
)


class TestConcurrencyLimiter:
    """并发限流器测试类"""
    
    @pytest.fixture
    def limiter(self):
        """创建测试用的限流器实例"""
        return ConcurrencyLimiter(
            max_concurrent=5,
            max_queue_size=10,
            timeout=1
        )
    
    @pytest.mark.asyncio
    async def test_basic_acquire_release(self, limiter):
        """测试基本的获取和释放功能"""
        # 获取许可
        success = await limiter.acquire("user1", "session1")
        assert success is True
        
        # 检查统计
        stats = limiter.get_stats()
        assert stats["active_connections"] == 1
        assert stats["total_connections"] == 1
        
        # 释放许可
        await limiter.release("session1")
        
        # 检查统计
        stats = limiter.get_stats()
        assert stats["active_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_limit(self, limiter):
        """测试并发限制的执行"""
        # 获取5个许可（达到限制）
        sessions = []
        for i in range(5):
            success = await limiter.acquire(f"user{i}", f"session{i}")
            assert success is True
            sessions.append(f"session{i}")
        
        # 检查统计
        stats = limiter.get_stats()
        assert stats["active_connections"] == 5
        
        # 尝试获取第6个许可（应该被拒绝）
        success = await limiter.acquire("user6", "session6", timeout=0.1)
        assert success is False
        
        # 检查统计
        stats = limiter.get_stats()
        assert stats["rejected_connections"] == 1
        
        # 释放所有许可
        for session_id in sessions:
            await limiter.release(session_id)
    
    @pytest.mark.asyncio
    async def test_queue_mechanism(self, limiter):
        """测试队列机制"""
        # 获取5个许可（达到限制）
        sessions = []
        for i in range(5):
            success = await limiter.acquire(f"user{i}", f"session{i}")
            assert success is True
            sessions.append(f"session{i}")
        
        # 创建一个等待任务
        async def wait_and_acquire():
            return await limiter.acquire("user_wait", "session_wait", timeout=2)
        
        wait_task = asyncio.create_task(wait_and_acquire())
        
        # 等待一小段时间，确保任务进入队列
        await asyncio.sleep(0.1)
        
        # 释放一个许可
        await limiter.release("session0")
        
        # 等待任务应该成功
        success = await wait_task
        assert success is True
        
        # 清理
        await limiter.release("session_wait")
        for session_id in sessions[1:]:
            await limiter.release(session_id)
    
    @pytest.mark.asyncio
    async def test_timeout(self, limiter):
        """测试超时机制"""
        # 获取5个许可（达到限制）
        sessions = []
        for i in range(5):
            success = await limiter.acquire(f"user{i}", f"session{i}")
            assert success is True
            sessions.append(f"session{i}")
        
        # 尝试获取许可，设置短超时
        success = await limiter.acquire("user_timeout", "session_timeout", timeout=0.5)
        assert success is False
        
        # 检查统计
        stats = limiter.get_stats()
        assert stats["rejected_connections"] == 1
        
        # 清理
        for session_id in sessions:
            await limiter.release(session_id)
    
    @pytest.mark.asyncio
    async def test_user_tier_limits(self):
        """测试用户分级限流"""
        # 创建自定义等级配置
        tier_configs = {
            UserTier.FREE: TierConfig(max_concurrent=2, max_queue_size=5, timeout=30),
            UserTier.WARMHEART: TierConfig(max_concurrent=5, max_queue_size=10, timeout=60),
            UserTier.ENERGY: TierConfig(max_concurrent=10, max_queue_size=20, timeout=120),
            UserTier.SYSTEM: TierConfig(max_concurrent=999999, max_queue_size=999999, timeout=999999),
        }
        
        limiter = ConcurrencyLimiter(
            max_concurrent=20,
            max_queue_size=50,
            timeout=30,
            tier_configs=tier_configs
        )
        
        # 测试免费用户限制（最多2个并发）
        success1 = await limiter.acquire("free_user", "session1", user_tier=UserTier.FREE)
        assert success1 is True
        
        success2 = await limiter.acquire("free_user", "session2", user_tier=UserTier.FREE)
        assert success2 is True
        
        # 第3个应该被拒绝
        success3 = await limiter.acquire("free_user", "session3", user_tier=UserTier.FREE, timeout=0.1)
        assert success3 is False
        
        # 检查统计
        stats = limiter.get_stats()
        assert stats["tier_stats"]["free"]["rejected"] == 1
        
        # 清理
        await limiter.release("session1")
        await limiter.release("session2")
    
    @pytest.mark.asyncio
    async def test_429_error_response(self, limiter):
        """测试429错误响应"""
        # 获取5个许可（达到限制）
        sessions = []
        for i in range(5):
            success = await limiter.acquire(f"user{i}", f"session{i}")
            assert success is True
            sessions.append(f"session{i}")
        
        # 检查是否应该返回429
        should_reject = limiter.should_reject_with_429()
        assert should_reject is True
        
        # 释放所有许可
        for session_id in sessions:
            await limiter.release(session_id)
        
        # 检查是否不应该返回429
        should_reject = limiter.should_reject_with_429()
        assert should_reject is False
    
    @pytest.mark.asyncio
    async def test_get_active_connections(self, limiter):
        """测试获取活跃连接列表"""
        # 获取3个许可
        await limiter.acquire("user1", "session1")
        await limiter.acquire("user2", "session2")
        await limiter.acquire("user3", "session3")
        
        # 获取活跃连接
        active = limiter.get_active_connections()
        assert len(active) == 3
        
        # 检查连接信息
        assert all("user_id" in conn for conn in active)
        assert all("session_id" in conn for conn in active)
        assert all("user_tier" in conn for conn in active)
        assert all("duration_seconds" in conn for conn in active)
        
        # 清理
        await limiter.release("session1")
        await limiter.release("session2")
        await limiter.release("session3")
    
    @pytest.mark.asyncio
    async def test_get_user_connections(self, limiter):
        """测试获取指定用户的连接"""
        # 同一用户获取多个许可
        await limiter.acquire("user1", "session1")
        await limiter.acquire("user1", "session2")
        await limiter.acquire("user2", "session3")
        
        # 获取user1的连接
        user1_conns = limiter.get_user_connections("user1")
        assert len(user1_conns) == 2
        
        # 获取user2的连接
        user2_conns = limiter.get_user_connections("user2")
        assert len(user2_conns) == 1
        
        # 清理
        await limiter.release("session1")
        await limiter.release("session2")
        await limiter.release("session3")
    
    @pytest.mark.asyncio
    async def test_statistics(self, limiter):
        """测试统计信息"""
        # 执行一些操作
        await limiter.acquire("user1", "session1")
        await limiter.acquire("user2", "session2")
        await limiter.acquire("user3", "session3", timeout=0.1)  # 可能失败
        
        # 获取统计
        stats = limiter.get_stats()
        
        # 检查统计字段
        assert "max_concurrent" in stats
        assert "max_queue_size" in stats
        assert "active_connections" in stats
        assert "total_connections" in stats
        assert "rejected_connections" in stats
        assert "rejection_rate" in stats
        assert "tier_stats" in stats
        
        # 清理
        await limiter.release("session1")
        await limiter.release("session2")
    
    @pytest.mark.asyncio
    async def test_queue_size_limit(self):
        """测试队列大小限制"""
        limiter = ConcurrencyLimiter(
            max_concurrent=2,
            max_queue_size=3,
            timeout=1
        )
        
        # 获取2个许可（达到并发限制）
        await limiter.acquire("user1", "session1")
        await limiter.acquire("user2", "session2")
        
        # 创建3个等待任务（填满队列）
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                limiter.acquire(f"user_wait{i}", f"session_wait{i}", timeout=5)
            )
            tasks.append(task)
        
        # 等待任务进入队列
        await asyncio.sleep(0.1)
        
        # 尝试再获取一个（应该被拒绝，因为队列已满）
        success = await limiter.acquire("user_overflow", "session_overflow", timeout=0.1)
        assert success is False
        
        # 清理
        await limiter.release("session1")
        await limiter.release("session2")
        
        # 等待队列中的任务完成
        for task in tasks:
            try:
                await task
            except:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
