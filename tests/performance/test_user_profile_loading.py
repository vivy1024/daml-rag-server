# -*- coding: utf-8 -*-
"""
用户档案加载性能测试

测试目标：
1. 缓存命中时的响应时间 < 50ms
2. 缓存未命中时的响应时间 < 500ms
3. 并发加载的性能

版本: v1.0.0
日期: 2025-12-21
作者: 薛小川
"""

import pytest
import pytest_asyncio
import asyncio
import time
import statistics
from typing import List, Dict, Any

# 导入被测试的组件
from src.framework.storage.intelligent_user_profile_cache import (
    IntelligentUserCache,
    CacheConfig
)
from src.applications.fitness.clients.backend_client import BackendClient


class MockBackendClient:
    """模拟后端客户端（用于测试）"""
    
    def __init__(self, response_delay_ms: float = 100):
        """
        初始化模拟客户端
        
        Args:
            response_delay_ms: 模拟的响应延迟（毫秒）
        """
        self.response_delay_ms = response_delay_ms
        self.call_count = 0
        
    async def get_user_profile(self, user_id: int, timeout: float = 5.0) -> Dict[str, Any]:
        """模拟获取用户档案（支持超时）"""
        self.call_count += 1
        
        # 检查是否会超时
        if self.response_delay_ms / 1000 > timeout:
            # 模拟超时，等待timeout秒后抛出异常
            await asyncio.sleep(timeout)
            raise asyncio.TimeoutError(f"Request timeout after {timeout}s")
        
        # 模拟网络延迟
        await asyncio.sleep(self.response_delay_ms / 1000)
        
        # 返回模拟数据
        return {
            'user_id': str(user_id),
            'basic_info': {
                'age': 25,
                'gender': 'male',
                'height': 175,
                'weight': 70
            },
            'nutrition_profile': {
                'daily_calories': 2200,
                'protein_g': 110,
                'carbs_g': 275,
                'fat_g': 70
            },
            'fitness_config': {
                'training_experience': 'intermediate',
                'training_frequency': 4,
                'session_duration': 75
            },
            'fitness_goals': {
                'primary_goal': 'muscle_gain',
                'target_weight': 75
            },
            'strength_levels': {
                'bench_press': 80,
                'squat': 100,
                'deadlift': 120
            },
            'health_profile': {
                'injuries': [],
                'medical_conditions': []
            },
            'created_at': '2025-01-01T00:00:00Z',
            'updated_at': '2025-12-21T00:00:00Z'
        }


@pytest_asyncio.fixture
async def cache_with_mock_backend():
    """创建带模拟后端的缓存实例"""
    mock_backend = MockBackendClient(response_delay_ms=100)
    
    config = CacheConfig(
        max_memory_entries=100,
        max_memory_size_mb=50,
        redis_ttl_seconds=1800,
        preload_enabled=False,  # 测试时禁用预加载
        auto_refresh_enabled=False  # 测试时禁用自动刷新
    )
    
    cache = IntelligentUserCache(
        backend_client=mock_backend,
        redis_client=None,  # 测试时不使用Redis
        config=config
    )
    
    yield cache, mock_backend
    
    # 清理
    await cache.shutdown()


@pytest.mark.asyncio
async def test_cache_hit_performance(cache_with_mock_backend):
    """
    测试缓存命中时的响应时间
    
    需求: 1.1, 1.2
    目标: < 50ms
    """
    cache, mock_backend = cache_with_mock_backend
    user_id = "1"
    
    # 第一次加载（缓存未命中）
    await cache.get_user_profile(user_id)
    
    # 重置调用计数
    mock_backend.call_count = 0
    
    # 测试缓存命中性能（10次）
    response_times = []
    
    for _ in range(10):
        start_time = time.time()
        profile = await cache.get_user_profile(user_id)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        response_times.append(response_time_ms)
        
        # 验证返回了正确的数据
        assert profile is not None
        assert profile['user_id'] == user_id
    
    # 验证没有调用后端（全部命中缓存）
    assert mock_backend.call_count == 0
    
    # 计算统计数据
    avg_response_time = statistics.mean(response_times)
    max_response_time = max(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
    
    print(f"\n缓存命中性能测试结果:")
    print(f"  平均响应时间: {avg_response_time:.2f}ms")
    print(f"  最大响应时间: {max_response_time:.2f}ms")
    print(f"  P95响应时间: {p95_response_time:.2f}ms")
    print(f"  后端调用次数: {mock_backend.call_count}")
    
    # 断言：平均响应时间应该 < 50ms
    assert avg_response_time < 50, f"缓存命中平均响应时间 {avg_response_time:.2f}ms 超过50ms"
    
    # 断言：P95响应时间应该 < 50ms
    assert p95_response_time < 50, f"缓存命中P95响应时间 {p95_response_time:.2f}ms 超过50ms"


@pytest.mark.asyncio
async def test_cache_miss_performance(cache_with_mock_backend):
    """
    测试缓存未命中时的响应时间
    
    需求: 1.1, 1.2
    目标: < 500ms
    """
    cache, mock_backend = cache_with_mock_backend
    
    # 测试缓存未命中性能（10个不同用户）
    response_times = []
    
    for i in range(10):
        user_id = str(i + 1)
        
        start_time = time.time()
        profile = await cache.get_user_profile(user_id)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        response_times.append(response_time_ms)
        
        # 验证返回了正确的数据
        assert profile is not None
        assert profile['user_id'] == user_id
    
    # 验证调用了后端（每个用户一次）
    assert mock_backend.call_count == 10
    
    # 计算统计数据
    avg_response_time = statistics.mean(response_times)
    max_response_time = max(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
    
    print(f"\n缓存未命中性能测试结果:")
    print(f"  平均响应时间: {avg_response_time:.2f}ms")
    print(f"  最大响应时间: {max_response_time:.2f}ms")
    print(f"  P95响应时间: {p95_response_time:.2f}ms")
    print(f"  后端调用次数: {mock_backend.call_count}")
    
    # 断言：平均响应时间应该 < 500ms
    assert avg_response_time < 500, f"缓存未命中平均响应时间 {avg_response_time:.2f}ms 超过500ms"
    
    # 断言：P95响应时间应该 < 500ms
    assert p95_response_time < 500, f"缓存未命中P95响应时间 {p95_response_time:.2f}ms 超过500ms"


@pytest.mark.asyncio
async def test_concurrent_loading_performance(cache_with_mock_backend):
    """
    测试并发加载的性能
    
    需求: 1.1, 1.2
    目标: 支持100个并发请求，平均响应时间 < 500ms
    """
    cache, mock_backend = cache_with_mock_backend
    
    # 并发加载100个用户档案
    num_concurrent = 100
    user_ids = [str(i + 1) for i in range(num_concurrent)]
    
    start_time = time.time()
    
    # 并发执行
    tasks = [cache.get_user_profile(user_id) for user_id in user_ids]
    profiles = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000
    avg_response_time = total_time_ms / num_concurrent
    
    # 验证所有档案都加载成功
    assert len(profiles) == num_concurrent
    assert all(p is not None for p in profiles)
    
    # 验证调用了后端
    assert mock_backend.call_count == num_concurrent
    
    print(f"\n并发加载性能测试结果:")
    print(f"  并发数量: {num_concurrent}")
    print(f"  总耗时: {total_time_ms:.2f}ms")
    print(f"  平均响应时间: {avg_response_time:.2f}ms")
    print(f"  吞吐量: {num_concurrent / (total_time_ms / 1000):.2f} req/s")
    print(f"  后端调用次数: {mock_backend.call_count}")
    
    # 断言：平均响应时间应该 < 500ms
    assert avg_response_time < 500, f"并发加载平均响应时间 {avg_response_time:.2f}ms 超过500ms"


@pytest.mark.asyncio
async def test_cache_hit_rate():
    """
    测试缓存命中率
    
    目标: 缓存命中率 > 80%
    """
    mock_backend = MockBackendClient(response_delay_ms=100)
    
    config = CacheConfig(
        max_memory_entries=100,
        preload_enabled=False,
        auto_refresh_enabled=False
    )
    
    cache = IntelligentUserCache(
        backend_client=mock_backend,
        redis_client=None,
        config=config
    )
    
    try:
        # 模拟真实访问模式：20个用户，每个用户访问5次
        num_users = 20
        accesses_per_user = 5
        
        for _ in range(accesses_per_user):
            for user_id in range(1, num_users + 1):
                await cache.get_user_profile(str(user_id))
        
        # 获取统计信息
        stats = cache.get_statistics()
        
        total_requests = stats['total_requests']
        cache_hits = stats['memory_hits'] + stats['redis_hits']
        cache_hit_rate = stats['cache_hit_rate']
        
        print(f"\n缓存命中率测试结果:")
        print(f"  总请求数: {total_requests}")
        print(f"  缓存命中数: {cache_hits}")
        print(f"  缓存命中率: {cache_hit_rate * 100:.2f}%")
        print(f"  后端调用次数: {mock_backend.call_count}")
        
        # 断言：缓存命中率应该 >= 80%
        assert cache_hit_rate >= 0.8, f"缓存命中率 {cache_hit_rate * 100:.2f}% 低于80%"
        
        # 验证后端调用次数（应该只调用了num_users次，因为后续都命中缓存）
        assert mock_backend.call_count == num_users
        
    finally:
        await cache.shutdown()


@pytest.mark.asyncio
async def test_timeout_and_fallback():
    """
    测试超时控制和降级机制
    
    需求: 1.3, 1.4
    """
    # 创建一个响应很慢的模拟后端（10秒）
    slow_backend = MockBackendClient(response_delay_ms=10000)
    
    config = CacheConfig(
        max_memory_entries=100,
        preload_enabled=False,
        auto_refresh_enabled=False
    )
    
    cache = IntelligentUserCache(
        backend_client=slow_backend,
        redis_client=None,
        config=config
    )
    
    try:
        user_id = "1"
        
        # 测试超时（应该在5秒内返回降级档案）
        start_time = time.time()
        profile = await cache.get_user_profile(user_id)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        print(f"\n超时和降级测试结果:")
        print(f"  响应时间: {response_time_ms:.2f}ms")
        print(f"  是否降级: {profile.get('_fallback', False)}")
        
        # 断言：应该返回了档案（即使是降级档案）
        assert profile is not None
        
        # 断言：响应时间应该 < 6000ms（5秒超时 + 1秒容错）
        assert response_time_ms < 6000, f"响应时间 {response_time_ms:.2f}ms 超过6000ms"
        
    finally:
        await cache.shutdown()


@pytest.mark.asyncio
async def test_memory_cache_eviction():
    """
    测试内存缓存的LRU淘汰机制
    """
    mock_backend = MockBackendClient(response_delay_ms=10)
    
    # 设置很小的缓存容量
    config = CacheConfig(
        max_memory_entries=5,  # 只能缓存5个用户
        preload_enabled=False,
        auto_refresh_enabled=False
    )
    
    cache = IntelligentUserCache(
        backend_client=mock_backend,
        redis_client=None,
        config=config
    )
    
    try:
        # 加载10个用户（超过缓存容量）
        for i in range(10):
            await cache.get_user_profile(str(i + 1))
        
        # 获取统计信息
        stats = cache.get_statistics()
        
        print(f"\nLRU淘汰测试结果:")
        print(f"  内存缓存条目数: {stats['memory_cache_entries']}")
        print(f"  缓存淘汰次数: {stats['cache_evictions']}")
        
        # 断言：内存缓存条目数应该 <= 5
        assert stats['memory_cache_entries'] <= 5
        
        # 断言：应该发生了淘汰
        assert stats['cache_evictions'] > 0
        
    finally:
        await cache.shutdown()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
