# -*- coding: utf-8 -*-
"""
CacheManager单元测试

测试缓存管理器的核心功能：
1. 用户档案缓存获取和设置
2. 会员权限缓存获取和设置
3. 缓存命中率统计
4. 缓存失效操作
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.framework.mcp.cache_manager import CacheManager, CacheStatistics


class TestCacheManager:
    """CacheManager单元测试"""
    
    @pytest.fixture
    def mock_user_cache(self):
        """模拟用户档案缓存"""
        cache = Mock()
        cache.get_user_profile = AsyncMock()
        cache.invalidate_user = AsyncMock()
        cache.shutdown = AsyncMock()
        return cache
    
    @pytest.fixture
    def mock_membership_cache(self):
        """模拟会员权限缓存"""
        cache = Mock()
        cache.get_user_membership = AsyncMock()
        cache.invalidate_user = AsyncMock()
        cache.shutdown = AsyncMock()
        return cache
    
    @pytest.fixture
    def cache_manager(self, mock_user_cache, mock_membership_cache):
        """创建CacheManager实例"""
        return CacheManager(
            user_cache=mock_user_cache,
            membership_cache=mock_membership_cache,
            user_profile_ttl=300,
            membership_ttl=600
        )
    
    @pytest.mark.asyncio
    async def test_get_user_profile_hit(self, cache_manager, mock_user_cache):
        """测试用户档案缓存命中"""
        # 准备测试数据
        user_id = "123"
        profile_data = {
            "user_id": user_id,
            "basic_info": {"age": 25, "gender": "male"},
            "fitness_goals": {"primary_goal": "hypertrophy"}
        }
        
        # 模拟缓存命中
        mock_user_cache.get_user_profile.return_value = profile_data
        
        # 执行测试
        result = await cache_manager.get_user_profile(user_id)
        
        # 验证结果
        assert result == profile_data
        assert cache_manager.stats.user_profile_requests == 1
        assert cache_manager.stats.user_profile_hits == 1
        assert cache_manager.stats.user_profile_misses == 0
        
        # 验证调用
        mock_user_cache.get_user_profile.assert_called_once_with(
            user_id=user_id,
            force_refresh=False
        )
    
    @pytest.mark.asyncio
    async def test_get_user_profile_miss(self, cache_manager, mock_user_cache):
        """测试用户档案缓存未命中"""
        # 准备测试数据
        user_id = "123"
        
        # 模拟缓存未命中
        mock_user_cache.get_user_profile.return_value = None
        
        # 执行测试
        result = await cache_manager.get_user_profile(user_id)
        
        # 验证结果
        assert result is None
        assert cache_manager.stats.user_profile_requests == 1
        assert cache_manager.stats.user_profile_hits == 0
        assert cache_manager.stats.user_profile_misses == 1
    
    @pytest.mark.asyncio
    async def test_get_user_profile_fallback(self, cache_manager, mock_user_cache):
        """测试用户档案降级数据"""
        # 准备测试数据
        user_id = "123"
        fallback_data = {
            "user_id": user_id,
            "basic_info": {"age": 25},
            "_fallback": True
        }
        
        # 模拟返回降级数据
        mock_user_cache.get_user_profile.return_value = fallback_data
        
        # 执行测试
        result = await cache_manager.get_user_profile(user_id)
        
        # 验证结果
        assert result == fallback_data
        assert result["_fallback"] is True
        assert cache_manager.stats.user_profile_hits == 1
    
    @pytest.mark.asyncio
    async def test_get_membership_permissions_hit(self, cache_manager, mock_membership_cache):
        """测试会员权限缓存命中"""
        # 准备测试数据
        user_id = "123"
        membership_data = {
            "user_id": user_id,
            "tier": "premium",
            "status": "active",
            "permissions": {"max_queries_per_day": 100}
        }
        
        # 模拟缓存命中
        mock_membership_cache.get_user_membership.return_value = membership_data
        
        # 执行测试
        result = await cache_manager.get_membership_permissions(user_id)
        
        # 验证结果
        assert result == membership_data
        assert cache_manager.stats.membership_requests == 1
        assert cache_manager.stats.membership_hits == 1
        assert cache_manager.stats.membership_misses == 0
        
        # 验证调用
        mock_membership_cache.get_user_membership.assert_called_once_with(
            user_id=user_id,
            force_refresh=False
        )
    
    @pytest.mark.asyncio
    async def test_get_membership_permissions_miss(self, cache_manager, mock_membership_cache):
        """测试会员权限缓存未命中"""
        # 准备测试数据
        user_id = "123"
        
        # 模拟缓存未命中
        mock_membership_cache.get_user_membership.return_value = None
        
        # 执行测试
        result = await cache_manager.get_membership_permissions(user_id)
        
        # 验证结果
        assert result is None
        assert cache_manager.stats.membership_requests == 1
        assert cache_manager.stats.membership_hits == 0
        assert cache_manager.stats.membership_misses == 1
    
    @pytest.mark.asyncio
    async def test_set_user_profile(self, cache_manager, mock_user_cache):
        """测试设置用户档案缓存"""
        # 准备测试数据
        user_id = "123"
        profile_data = {
            "user_id": user_id,
            "basic_info": {"age": 25}
        }
        
        # 执行测试
        await cache_manager.set_user_profile(user_id, profile_data)
        
        # 验证调用（应该调用invalidate来强制更新）
        mock_user_cache.invalidate_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_set_membership_permissions(self, cache_manager, mock_membership_cache):
        """测试设置会员权限缓存"""
        # 准备测试数据
        user_id = "123"
        membership_data = {
            "user_id": user_id,
            "tier": "premium"
        }
        
        # 执行测试
        await cache_manager.set_membership_permissions(user_id, membership_data)
        
        # 验证调用（应该调用invalidate来强制更新）
        mock_membership_cache.invalidate_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_invalidate_user_profile(self, cache_manager, mock_user_cache):
        """测试使用户档案缓存失效"""
        user_id = "123"
        
        # 执行测试
        await cache_manager.invalidate_user_profile(user_id)
        
        # 验证调用
        mock_user_cache.invalidate_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_invalidate_membership(self, cache_manager, mock_membership_cache):
        """测试使会员权限缓存失效"""
        user_id = "123"
        
        # 执行测试
        await cache_manager.invalidate_membership(user_id)
        
        # 验证调用
        mock_membership_cache.invalidate_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_invalidate_all(self, cache_manager, mock_user_cache, mock_membership_cache):
        """测试使所有缓存失效"""
        user_id = "123"
        
        # 执行测试
        await cache_manager.invalidate_all(user_id)
        
        # 验证调用
        mock_user_cache.invalidate_user.assert_called_once_with(user_id)
        mock_membership_cache.invalidate_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, cache_manager, mock_user_cache, mock_membership_cache):
        """测试获取缓存统计信息"""
        # 准备测试数据
        user_id = "123"
        profile_data = {"user_id": user_id}
        membership_data = {"user_id": user_id}
        
        # 模拟缓存操作
        mock_user_cache.get_user_profile.return_value = profile_data
        mock_membership_cache.get_user_membership.return_value = membership_data
        
        # 执行多次缓存操作
        await cache_manager.get_user_profile(user_id)
        await cache_manager.get_user_profile(user_id)
        await cache_manager.get_membership_permissions(user_id)
        
        # 获取统计信息
        stats = cache_manager.get_statistics()
        
        # 验证统计信息
        assert stats["total_requests"] == 3
        assert stats["total_hits"] == 3
        assert stats["total_misses"] == 0
        assert stats["hit_rate"] == 100.0
        assert stats["user_profile_requests"] == 2
        assert stats["user_profile_hits"] == 2
        assert stats["user_profile_hit_rate"] == 100.0
        assert stats["membership_requests"] == 1
        assert stats["membership_hits"] == 1
        assert stats["membership_hit_rate"] == 100.0
        assert "avg_response_time_ms" in stats
    
    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self, cache_manager, mock_user_cache):
        """测试命中率计算"""
        # 准备测试数据
        profile_data = {"user_id": "123"}
        
        # 模拟3次命中，2次未命中
        mock_user_cache.get_user_profile.side_effect = [
            profile_data,  # 命中
            profile_data,  # 命中
            None,          # 未命中
            profile_data,  # 命中
            None           # 未命中
        ]
        
        # 执行5次查询
        for i in range(5):
            await cache_manager.get_user_profile(f"user_{i}")
        
        # 获取统计信息
        stats = cache_manager.get_statistics()
        
        # 验证命中率
        assert stats["user_profile_requests"] == 5
        assert stats["user_profile_hits"] == 3
        assert stats["user_profile_misses"] == 2
        assert stats["user_profile_hit_rate"] == 60.0
    
    @pytest.mark.asyncio
    async def test_shutdown(self, cache_manager, mock_user_cache, mock_membership_cache):
        """测试关闭缓存管理器"""
        # 执行测试
        await cache_manager.shutdown()
        
        # 验证调用
        mock_user_cache.shutdown.assert_called_once()
        mock_membership_cache.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_manager_without_caches(self):
        """测试没有缓存实例的CacheManager"""
        # 创建没有缓存的管理器
        manager = CacheManager(user_cache=None, membership_cache=None)
        
        # 测试获取操作（应该返回None）
        result = await manager.get_user_profile("123")
        assert result is None
        assert manager.stats.user_profile_misses == 1
        
        result = await manager.get_membership_permissions("123")
        assert result is None
        assert manager.stats.membership_misses == 1
        
        # 测试设置操作（应该不抛出异常）
        await manager.set_user_profile("123", {})
        await manager.set_membership_permissions("123", {})
        
        # 测试失效操作（应该不抛出异常）
        await manager.invalidate_user_profile("123")
        await manager.invalidate_membership("123")
        await manager.invalidate_all("123")


class TestCacheStatistics:
    """CacheStatistics单元测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        stats = CacheStatistics()
        
        assert stats.user_profile_requests == 0
        assert stats.user_profile_hits == 0
        assert stats.user_profile_misses == 0
        assert stats.membership_requests == 0
        assert stats.membership_hits == 0
        assert stats.membership_misses == 0
        assert stats.total_requests == 0
        assert stats.total_hits == 0
        assert stats.total_misses == 0
        assert stats.get_hit_rate() == 0.0
    
    def test_update_hit_rate(self):
        """测试更新命中率"""
        stats = CacheStatistics()
        
        # 模拟一些请求
        stats.user_profile_requests = 10
        stats.user_profile_hits = 8
        stats.user_profile_misses = 2
        stats.membership_requests = 5
        stats.membership_hits = 3
        stats.membership_misses = 2
        
        # 更新命中率
        stats.update_hit_rate()
        
        # 验证
        assert stats.total_requests == 15
        assert stats.total_hits == 11
        assert stats.total_misses == 4
    
    def test_get_hit_rate(self):
        """测试获取命中率"""
        stats = CacheStatistics()
        
        # 空请求
        assert stats.get_hit_rate() == 0.0
        
        # 有请求
        stats.user_profile_requests = 10
        stats.user_profile_hits = 7
        stats.membership_requests = 10
        stats.membership_hits = 8
        stats.update_hit_rate()
        
        # 验证总体命中率
        assert stats.get_hit_rate() == 0.75  # (7+8)/(10+10)
    
    def test_get_user_profile_hit_rate(self):
        """测试获取用户档案命中率"""
        stats = CacheStatistics()
        
        # 空请求
        assert stats.get_user_profile_hit_rate() == 0.0
        
        # 有请求
        stats.user_profile_requests = 10
        stats.user_profile_hits = 8
        
        # 验证
        assert stats.get_user_profile_hit_rate() == 0.8
    
    def test_get_membership_hit_rate(self):
        """测试获取会员权限命中率"""
        stats = CacheStatistics()
        
        # 空请求
        assert stats.get_membership_hit_rate() == 0.0
        
        # 有请求
        stats.membership_requests = 5
        stats.membership_hits = 4
        
        # 验证
        assert stats.get_membership_hit_rate() == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
