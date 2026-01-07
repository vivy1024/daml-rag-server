# -*- coding: utf-8 -*-
"""
测试缓存系统的get_stats()方法

测试目标：
1. 验证get_stats()方法返回正确的统计数据
2. 验证统计数据的准确性
3. 验证命中率计算正确

版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import asyncio
from src.framework.storage.intelligent_cache_manager import (
    IntelligentCacheManager,
    CacheConfig
)


@pytest.mark.asyncio
async def test_get_stats_basic():
    """测试get_stats()基本功能"""
    # 创建缓存管理器
    config = CacheConfig(
        l1_enabled=True,
        l2_enabled=False,  # 禁用Redis以简化测试
        stats_enabled=True
    )
    cache = IntelligentCacheManager(config=config)
    
    # 执行一些缓存操作
    await cache.put("key1", "value1", ttl=60)
    await cache.put("key2", "value2", ttl=60)
    
    # 获取数据（命中）
    value1 = await cache.get("key1")
    assert value1 == "value1"
    
    # 获取不存在的数据（未命中）
    value3 = await cache.get("key3")
    assert value3 is None
    
    # 获取统计数据
    stats = cache.get_stats()
    
    # 验证统计数据结构
    assert "hit_rate" in stats
    assert "l1_hit_rate" in stats
    assert "l2_hit_rate" in stats
    assert "total_requests" in stats
    assert "l1_size" in stats
    assert "l1_memory_mb" in stats
    assert "l1_hits" in stats
    assert "l2_hits" in stats
    assert "l3_hits" in stats
    assert "misses" in stats
    
    # 验证统计数据值
    assert stats["total_requests"] == 2  # 2次get操作
    assert stats["l1_hits"] == 1  # key1命中
    assert stats["misses"] == 1  # key3未命中
    assert stats["l1_size"] == 2  # 2个缓存条目
    
    # 验证命中率计算
    expected_hit_rate = (1 / 2) * 100  # 50%
    assert stats["hit_rate"] == round(expected_hit_rate, 2)
    assert stats["l1_hit_rate"] == round(expected_hit_rate, 2)
    
    await cache.shutdown()


@pytest.mark.asyncio
async def test_get_stats_multiple_operations():
    """测试多次操作后的统计数据"""
    config = CacheConfig(
        l1_enabled=True,
        l2_enabled=False,
        stats_enabled=True
    )
    cache = IntelligentCacheManager(config=config)
    
    # 存储多个键
    for i in range(5):
        await cache.put(f"key{i}", f"value{i}", ttl=60)
    
    # 多次获取（命中）
    for i in range(5):
        value = await cache.get(f"key{i}")
        assert value == f"value{i}"
    
    # 多次获取不存在的键（未命中）
    for i in range(5, 10):
        value = await cache.get(f"key{i}")
        assert value is None
    
    # 获取统计数据
    stats = cache.get_stats()
    
    # 验证统计数据
    assert stats["total_requests"] == 10  # 10次get操作
    assert stats["l1_hits"] == 5  # 5次命中
    assert stats["misses"] == 5  # 5次未命中
    assert stats["l1_size"] == 5  # 5个缓存条目
    
    # 验证命中率
    expected_hit_rate = (5 / 10) * 100  # 50%
    assert stats["hit_rate"] == round(expected_hit_rate, 2)
    
    await cache.shutdown()


@pytest.mark.asyncio
async def test_get_stats_memory_tracking():
    """测试内存使用统计"""
    config = CacheConfig(
        l1_enabled=True,
        l2_enabled=False,
        stats_enabled=True
    )
    cache = IntelligentCacheManager(config=config)
    
    # 存储一些数据
    test_data = {"name": "test", "data": "x" * 1000}  # 约1KB数据
    await cache.put("test_key", test_data, ttl=60)
    
    # 获取统计数据
    stats = cache.get_stats()
    
    # 验证内存统计
    assert stats["l1_size"] == 1
    assert stats["l1_memory_mb"] >= 0  # 内存使用应该是非负数
    assert isinstance(stats["l1_memory_mb"], float)
    
    await cache.shutdown()


@pytest.mark.asyncio
async def test_get_stats_vs_get_statistics():
    """测试get_stats()和get_statistics()的兼容性"""
    config = CacheConfig(
        l1_enabled=True,
        l2_enabled=False,
        stats_enabled=True
    )
    cache = IntelligentCacheManager(config=config)
    
    # 执行一些操作
    await cache.put("key1", "value1", ttl=60)
    await cache.get("key1")
    
    # 获取两种统计数据
    stats = cache.get_stats()
    statistics = cache.get_statistics()
    
    # 验证两者包含相同的核心数据
    assert stats["hit_rate"] == statistics["overall_hit_rate"]
    assert stats["l1_hit_rate"] == statistics["l1_hit_rate"]
    assert stats["l2_hit_rate"] == statistics["l2_hit_rate"]
    assert stats["total_requests"] == statistics["total_gets"]
    assert stats["l1_size"] == statistics["l1_size"]
    assert stats["l1_memory_mb"] == statistics["l1_memory_mb"]
    
    # 验证get_statistics()包含更多详细信息
    assert "total_puts" in statistics
    assert "total_invalidations" in statistics
    assert "avg_get_time_ms" in statistics
    
    await cache.shutdown()


@pytest.mark.asyncio
async def test_get_stats_zero_requests():
    """测试没有请求时的统计数据"""
    config = CacheConfig(
        l1_enabled=True,
        l2_enabled=False,
        stats_enabled=True
    )
    cache = IntelligentCacheManager(config=config)
    
    # 不执行任何操作，直接获取统计
    stats = cache.get_stats()
    
    # 验证初始状态
    assert stats["total_requests"] == 0
    assert stats["l1_hits"] == 0
    assert stats["l2_hits"] == 0
    assert stats["l3_hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate"] == 0.0
    assert stats["l1_hit_rate"] == 0.0
    assert stats["l2_hit_rate"] == 0.0
    assert stats["l1_size"] == 0
    assert stats["l1_memory_mb"] == 0.0
    
    await cache.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
