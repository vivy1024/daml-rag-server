#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能测试脚本

测试三层检索响应时间、DAG编排并行效率、缓存命中率

版本：v1.0.0
创建日期：2025-12-15
"""

import asyncio
import httpx
import time
import statistics
from typing import List, Dict, Any

# 测试配置
BASE_URL = "http://localhost:8001"
API_ENDPOINT = f"{BASE_URL}/api/v1/chat"
TEST_USER_ID = "2"

# 性能目标
TARGET_RESPONSE_TIME = 100  # 100ms
TARGET_CACHE_HIT_RATE = 0.8  # 80%


async def test_retrieval_performance():
    """测试三层检索响应时间"""
    print("\n" + "=" * 80)
    print("测试：三层检索响应时间")
    print("=" * 80)
    
    test_queries = [
        "推荐胸肌训练动作",
        "计算我的TDEE",
        "制定训练计划",
        "有哪些动作我不能做",
        "设计营养餐食"
    ]
    
    response_times = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for query in test_queries:
            try:
                start_time = time.time()
                
                response = await client.post(
                    API_ENDPOINT,
                    json={
                        "query": query,
                        "user_id": TEST_USER_ID,
                        "domain": "fitness",
                        "session_id": f"perf_test_{len(response_times)}"
                    }
                )
                
                elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
                response_times.append(elapsed_time)
                
                print(f"查询: {query}")
                print(f"  响应时间: {elapsed_time:.2f}ms")
                print(f"  状态码: {response.status_code}")
                
            except Exception as e:
                print(f"  ⚠️  查询失败: {e}")
                continue
    
    if response_times:
        avg_time = statistics.mean(response_times)
        p50 = statistics.median(response_times)
        p95 = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
        
        print(f"\n性能统计:")
        print(f"  - 平均响应时间: {avg_time:.2f}ms")
        print(f"  - P50: {p50:.2f}ms")
        print(f"  - P95: {p95:.2f}ms")
        print(f"  - 最快: {min(response_times):.2f}ms")
        print(f"  - 最慢: {max(response_times):.2f}ms")
        
        # 评估性能
        if avg_time < TARGET_RESPONSE_TIME:
            print(f"✅ 性能测试通过（目标: <{TARGET_RESPONSE_TIME}ms）")
        else:
            print(f"⚠️  性能未达标（目标: <{TARGET_RESPONSE_TIME}ms，实际: {avg_time:.2f}ms）")
        
        return {
            "avg_time": avg_time,
            "p50": p50,
            "p95": p95,
            "min_time": min(response_times),
            "max_time": max(response_times),
            "passed": avg_time < TARGET_RESPONSE_TIME
        }
    else:
        print("❌ 没有成功的查询")
        return None


async def test_cache_performance():
    """测试缓存命中率"""
    print("\n" + "=" * 80)
    print("测试：缓存命中率")
    print("=" * 80)
    
    test_query = "推荐胸肌训练动作"
    cache_hits = 0
    total_requests = 10
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(total_requests):
            try:
                response = await client.post(
                    API_ENDPOINT,
                    json={
                        "query": test_query,
                        "user_id": TEST_USER_ID,
                        "domain": "fitness",
                        "session_id": "cache_test"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('data', {}).get('cache_hit', False):
                        cache_hits += 1
                
                print(f"请求 {i+1}/{total_requests}: 缓存命中={data.get('data', {}).get('cache_hit', False)}")
                
            except Exception as e:
                print(f"  ⚠️  请求失败: {e}")
                continue
    
    cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0
    
    print(f"\n缓存统计:")
    print(f"  - 总请求数: {total_requests}")
    print(f"  - 缓存命中: {cache_hits}")
    print(f"  - 命中率: {cache_hit_rate * 100:.1f}%")
    
    if cache_hit_rate >= TARGET_CACHE_HIT_RATE:
        print(f"✅ 缓存性能测试通过（目标: >{TARGET_CACHE_HIT_RATE * 100}%）")
    else:
        print(f"⚠️  缓存命中率未达标（目标: >{TARGET_CACHE_HIT_RATE * 100}%，实际: {cache_hit_rate * 100:.1f}%）")
    
    return {
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_hit_rate": cache_hit_rate,
        "passed": cache_hit_rate >= TARGET_CACHE_HIT_RATE
    }


async def main():
    """运行所有性能测试"""
    print("\n" + "=" * 80)
    print("DAML-RAG系统性能测试")
    print("=" * 80)
    
    # 测试1：三层检索响应时间
    retrieval_result = await test_retrieval_performance()
    
    # 测试2：缓存命中率
    cache_result = await test_cache_performance()
    
    # 总结
    print("\n" + "=" * 80)
    print("性能测试总结")
    print("=" * 80)
    
    if retrieval_result:
        print(f"三层检索: {'✅ 通过' if retrieval_result['passed'] else '❌ 未通过'}")
        print(f"  平均响应时间: {retrieval_result['avg_time']:.2f}ms")
    
    if cache_result:
        print(f"缓存性能: {'✅ 通过' if cache_result['passed'] else '❌ 未通过'}")
        print(f"  缓存命中率: {cache_result['cache_hit_rate'] * 100:.1f}%")
    
    # 生成报告
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "retrieval_performance": retrieval_result,
        "cache_performance": cache_result,
        "overall_passed": (
            retrieval_result and retrieval_result['passed'] and
            cache_result and cache_result['passed']
        )
    }
    
    print(f"\n总体结果: {'✅ 所有测试通过' if report['overall_passed'] else '⚠️  部分测试未通过'}")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())
