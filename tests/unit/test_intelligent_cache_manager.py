# -*- coding: utf-8 -*-
"""
智能缓存管理器单元测试

测试IntelligentCacheManager的核心功能。

版本: v1.0.0
日期: 2025-12-21
作者: 薛小川
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.framework.storage.intelligent_cache_manager import (
    IntelligentCacheManager,
    CacheConfig,
    CacheLevel
)


class TestIntelligentCacheManager:
    """测试智能缓存管理器"""
    
    @pytest.fixture
    def cache_config(self):
        """创建测试配置"""
        return CacheConfig(
            l1_enabled=True,
            l1_max_size=10,
            l1_max_memory_mb=1,
            l2_enabled=True,
            default_ttl=60,
            warmup_enabled=True,
            warmup_batch_size=5
        )
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis客户端"""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()
        redis.delete = AsyncMock()
        redis.scan = AsyncMock(return_value=(0, []))
        return redis
    
    @pytest_asyncio.fixture
    async def cache_manager(self, cache_config, mock_redis):
        """创建缓存管理器实例"""
        manager = IntelligentCacheManager(
            config=cache_config,
            redis_client=mock_redis
        )
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_l1_cache_hit(self, cache_manager):
        """测试L1缓存命中"""
        # 存储数据
        await cache_manager.put("test_key", "test_value", ttl=60)
        
        # 获取数据
        value = await cache_manager.get("test_key")
        
        assert value == "test_value"
        assert cache_manager.stats.l1_hits == 1
        assert cache_manager.stats.misses == 0
    
    @pytest.mark.asyncio
    async def test_l1_cache_miss(self, cache_manager):
        """测试L1缓存未命中"""
        # 获取不存在的数据
        value = await cache_manager.get("nonexistent_key")
        
        assert value is None
        assert cache_manager.stats.l1_hits == 0
        assert cache_manager.stats.misses == 1
    
    @pytest.mark.asyncio
    async def test_l1_cache_with_fetch_func(self, cache_manager):
        """测试带fetch_func的缓存获取"""
        # 定义fetch函数
        async def fetch_data():
            return "fetched_value"
        
        # 第一次获取（缓存未命中，执行fetch）
        value1 = await cache_manager.get("test_key", fetch_func=fetch_data)
        assert value1 == "fetched_value"
        # fetch_func成功获取数据，不计为miss
        assert cache_manager.stats.total_gets == 1
        
        # 第二次获取（缓存命中）
        value2 = await cache_manager.get("test_key")
        assert value2 == "fetched_value"
        assert cache_manager.stats.l1_hits == 1
    
    @pytest.mark.asyncio
    async def test_l1_lru_eviction(self, cache_manager):
        """测试L1 LRU淘汰策略"""
        # 填满缓存（配置的max_size=10）
        for i in range(10):
            await cache_manager.put(f"key_{i}", f"value_{i}")
        
        assert len(cache_manager.l1_cache) == 10
        
        # 添加第11个条目，应该淘汰最旧的
        await cache_manager.put("key_10", "value_10")
        
        assert len(cache_manager.l1_cache) == 10
        assert "key_0" not in cache_manager.l1_cache  # 最旧的被淘汰
        assert "key_10" in cache_manager.l1_cache
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache_manager):
        """测试TTL过期"""
        # 存储数据，TTL=1秒
        await cache_manager.put("test_key", "test_value", ttl=1)
        
        # 立即获取，应该命中
        value1 = await cache_manager.get("test_key")
        assert value1 == "test_value"
        
        # 等待过期
        await asyncio.sleep(1.1)
        
        # 再次获取，应该未命中
        value2 = await cache_manager.get("test_key")
        assert value2 is None
    
    @pytest.mark.asyncio
    async def test_invalidate_exact(self, cache_manager):
        """测试精确失效"""
        # 存储数据
        await cache_manager.put("test_key", "test_value")
        
        # 验证存在
        value1 = await cache_manager.get("test_key")
        assert value1 == "test_value"
        
        # 失效
        await cache_manager.invalidate("test_key")
        
        # 验证已失效
        value2 = await cache_manager.get("test_key")
        assert value2 is None
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_manager):
        """测试模式失效"""
        # 存储多个数据
        await cache_manager.put("user:1:profile", "profile1")
        await cache_manager.put("user:2:profile", "profile2")
        await cache_manager.put("user:1:settings", "settings1")
        
        # 模式失效
        await cache_manager.invalidate("user:1:*", pattern=True)
        
        # 验证user:1的数据已失效
        assert await cache_manager.get("user:1:profile") is None
        assert await cache_manager.get("user:1:settings") is None
        
        # 验证user:2的数据仍然存在
        assert await cache_manager.get("user:2:profile") == "profile2"
    
    @pytest.mark.asyncio
    async def test_warm_up(self, cache_manager):
        """测试缓存预热"""
        # 定义fetch函数
        async def fetch_data(key):
            return f"value_for_{key}"
        
        # 预热多个键
        keys = ["key_1", "key_2", "key_3"]
        await cache_manager.warm_up(keys, fetch_data)
        
        # 验证所有键都已缓存
        for key in keys:
            value = await cache_manager.get(key)
            assert value == f"value_for_{key}"
        
        # 验证统计
        assert cache_manager.stats.total_warmups == 3
    
    @pytest.mark.asyncio
    async def test_statistics(self, cache_manager):
        """测试统计功能"""
        # 执行一些操作
        await cache_manager.put("key1", "value1")
        await cache_manager.get("key1")  # 命中
        await cache_manager.get("key2")  # 未命中
        await cache_manager.invalidate("key1")
        
        # 获取统计
        stats = cache_manager.get_statistics()
        
        assert stats["l1_hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_gets"] == 2
        assert stats["total_puts"] == 1
        assert stats["total_invalidations"] == 1
        assert stats["l1_size"] == 0  # key1已失效
        assert stats["l1_hit_rate"] == 50.0  # 1/2 = 50%
    
    @pytest.mark.asyncio
    async def test_l2_redis_fallback(self, cache_manager, mock_redis):
        """测试L2 Redis回填L1"""
        import pickle
        
        # 模拟Redis中有数据
        mock_redis.get = AsyncMock(return_value=pickle.dumps("redis_value"))
        
        # 获取数据（L1未命中，L2命中）
        value = await cache_manager.get("test_key")
        
        assert value == "redis_value"
        assert cache_manager.stats.l2_hits == 1
        
        # 验证已回填到L1
        value2 = await cache_manager.get("test_key")
        assert value2 == "redis_value"
        assert cache_manager.stats.l1_hits == 1
    
    @pytest.mark.asyncio
    async def test_multiple_cache_levels(self, cache_manager):
        """测试多层缓存"""
        # 定义fetch函数
        async def fetch_data():
            return "database_value"
        
        # 指定只使用L1和L3
        value = await cache_manager.get(
            "test_key",
            fetch_func=fetch_data,
            cache_levels=[CacheLevel.L1_MEMORY, CacheLevel.L3_DATABASE]
        )
        
        assert value == "database_value"
        
        # 验证已存储到L1
        value2 = await cache_manager.get("test_key")
        assert value2 == "database_value"
        assert cache_manager.stats.l1_hits == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
