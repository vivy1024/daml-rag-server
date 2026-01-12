# -*- coding: utf-8 -*-
"""
缓存集成测试

测试 CacheManager（framework/mcp/cache_manager.py）在工作流执行器中的集成情况。

版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

# 导入被测试的模块
from src.applications.fitness.workflow_executor import (
    get_cache_manager,
    initialize_performance_components
)
from src.framework.mcp.cache_manager import CacheManager


class TestCacheIntegration:
    """缓存集成测试类"""
    
    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self):
        """测试缓存管理器初始化"""
        # 初始化性能组件
        initialize_performance_components()
        
        # 获取缓存管理器
        cache_manager = get_cache_manager()
        
        # 验证缓存管理器已初始化
        assert cache_manager is not None
        assert isinstance(cache_manager, CacheManager)
        
        print("✅ 缓存管理器初始化测试通过")
    
    @pytest.mark.asyncio
    async def test_cache_manager_singleton(self):
        """测试缓存管理器单例模式"""
        # 初始化性能组件
        initialize_performance_components()
        
        # 多次获取缓存管理器
        cache_manager1 = get_cache_manager()
        cache_manager2 = get_cache_manager()
        
        # 验证是同一个实例
        assert cache_manager1 is cache_manager2
        
        print("✅ 缓存管理器单例模式测试通过")
    
    @pytest.mark.asyncio
    async def test_cache_get_put(self):
        """测试缓存的基本get/put操作"""
        # 初始化性能组件
        initialize_performance_components()
        cache_manager = get_cache_manager()
        
        # 测试数据
        test_key = "test_key_123"
        test_value = {"data": "test_value", "timestamp": time.time()}
        
        # 存储到缓存
        await cache_manager.put(test_key, test_value, ttl=60)
        
        # 从缓存获取
        cached_value = await cache_manager.get(test_key)
        
        # 验证数据一致
        assert cached_value is not None
        assert cached_value["data"] == test_value["data"]
        
        print("✅ 缓存get/put操作测试通过")
    
    @pytest.mark.asyncio
    async def test_cache_with_fetch_func(self):
        """测试缓存的fetch_func功能"""
        # 初始化性能组件
        initialize_performance_components()
        cache_manager = get_cache_manager()
        
        # 测试数据
        test_key = "test_fetch_key"
        fetch_called = False
        
        async def fetch_func():
            nonlocal fetch_called
            fetch_called = True
            return {"data": "fetched_value"}
        
        # 第一次获取（应该调用fetch_func）
        value1 = await cache_manager.get(test_key, fetch_func=fetch_func, ttl=60)
        assert fetch_called is True
        assert value1["data"] == "fetched_value"
        
        # 重置标志
        fetch_called = False
        
        # 第二次获取（应该从缓存获取，不调用fetch_func）
        value2 = await cache_manager.get(test_key, fetch_func=fetch_func, ttl=60)
        assert fetch_called is False  # 不应该调用fetch_func
        assert value2["data"] == "fetched_value"
        
        print("✅ 缓存fetch_func功能测试通过")
    
    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """测试缓存统计功能"""
        # 初始化性能组件
        initialize_performance_components()
        cache_manager = get_cache_manager()
        
        # 执行一些缓存操作
        await cache_manager.put("key1", "value1", ttl=60)
        await cache_manager.get("key1")
        await cache_manager.get("key2")  # 未命中
        
        # 获取统计信息
        stats = await cache_manager.get_stats()
        
        # 验证统计信息
        assert "hit_rate" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert (stats["hits"] + stats["misses"]) >= 2
        
        print("✅ 缓存统计功能测试通过")
        print(f"   - 命中数: {stats['hits']}")
        print(f"   - 未命中数: {stats['misses']}")
        print(f"   - 命中率: {stats['hit_rate']}")
    
    @pytest.mark.asyncio
    async def test_user_profile_cache_key_format(self):
        """测试用户档案缓存键格式"""
        # 初始化性能组件
        initialize_performance_components()
        cache_manager = get_cache_manager()
        
        # 模拟用户档案数据
        user_id = 123
        user_profile = {
            "user_id": user_id,
            "name": "测试用户",
            "fitness_goal": "增肌"
        }
        
        # 使用正确的缓存键格式
        cache_key = f"user_profile:{user_id}"
        
        # 存储到缓存
        await cache_manager.put(cache_key, user_profile, ttl=300)
        
        # 从缓存获取
        cached_profile = await cache_manager.get(cache_key)
        
        # 验证数据
        assert cached_profile is not None
        assert cached_profile["user_id"] == user_id
        assert cached_profile["fitness_goal"] == "增肌"
        
        print("✅ 用户档案缓存键格式测试通过")
    
    @pytest.mark.asyncio
    async def test_membership_cache_key_format(self):
        """测试会员权限缓存键格式"""
        # 初始化性能组件
        initialize_performance_components()
        cache_manager = get_cache_manager()
        
        # 模拟会员权限数据
        user_id = 123
        membership = {
            "user_id": user_id,
            "tier": "premium",
            "expires_at": "2025-12-31"
        }
        
        # 使用正确的缓存键格式
        cache_key = f"user_membership:{user_id}"
        
        # 存储到缓存
        await cache_manager.put(cache_key, membership, ttl=600)
        
        # 从缓存获取
        cached_membership = await cache_manager.get(cache_key)
        
        # 验证数据
        assert cached_membership is not None
        assert cached_membership["tier"] == "premium"
        
        print("✅ 会员权限缓存键格式测试通过")
    
    @pytest.mark.asyncio
    async def test_bge_complexity_cache_key_format(self):
        """测试BGE复杂度缓存键格式"""
        # 初始化性能组件
        initialize_performance_components()
        cache_manager = get_cache_manager()
        
        # 模拟BGE分类结果
        import hashlib
        query_text = "我想增肌，应该怎么训练？"
        query_hash = hashlib.md5(query_text.encode('utf-8')).hexdigest()
        cache_key = f"bge_complexity:{query_hash}"
        
        # 模拟分类结果
        from dataclasses import dataclass
        
        @dataclass
        class MockClassificationResult:
            is_complex: bool
            similarity: float
            reason: str
            duration_ms: float
            cache_hit: bool
            fallback_used: bool
        
        result = MockClassificationResult(
            is_complex=True,
            similarity=0.85,
            reason="复杂查询",
            duration_ms=50.0,
            cache_hit=False,
            fallback_used=False
        )
        
        # 存储到缓存
        await cache_manager.put(cache_key, result, ttl=3600)
        
        # 从缓存获取
        cached_result = await cache_manager.get(cache_key)
        
        # 验证数据
        assert cached_result is not None
        assert cached_result.is_complex is True
        assert cached_result.similarity == 0.85
        
        print("✅ BGE复杂度缓存键格式测试通过")
    
    @pytest.mark.asyncio
    async def test_few_shot_cache_key_format(self):
        """测试Few-Shot缓存键格式"""
        # 初始化性能组件
        initialize_performance_components()
        cache_manager = get_cache_manager()
        
        # 模拟Few-Shot示例数据
        import hashlib
        query_text = "我想增肌"
        fitness_goal = "增肌"
        domain = "fitness"
        cache_key_data = f"{query_text}:{fitness_goal}:{domain}"
        cache_hash = hashlib.md5(cache_key_data.encode('utf-8')).hexdigest()
        cache_key = f"few_shot:{cache_hash}"
        
        few_shot_examples = [
            {
                "query": "如何增肌？",
                "response": "建议进行力量训练...",
                "match_score": 0.9,
                "pattern_id": "pattern_001"
            }
        ]
        
        # 存储到缓存
        await cache_manager.put(cache_key, few_shot_examples, ttl=1800)
        
        # 从缓存获取
        cached_examples = await cache_manager.get(cache_key)
        
        # 验证数据
        assert cached_examples is not None
        assert len(cached_examples) == 1
        assert cached_examples[0]["match_score"] == 0.9
        
        print("✅ Few-Shot缓存键格式测试通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
