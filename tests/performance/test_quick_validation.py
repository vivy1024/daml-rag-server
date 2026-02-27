# -*- coding: utf-8 -*-
"""
快速验证测试 - 验证性能测试基础设施

这个测试用于快速验证：
1. API可访问性
2. 测试框架正常工作
3. 基本请求能够成功

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import asyncio
import aiohttp

API_BASE_URL = "http://localhost:8001"


@pytest.mark.asyncio
async def test_api_health():
    """测试API健康检查"""
    url = f"{API_BASE_URL}/api/health/"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            assert response.status == 200, f"API健康检查失败: {response.status}"

            data = await response.json()
            # 兼容两种格式: {"code": 200, "data": {"status": ...}} 或 {"status": ...}
            if "code" in data:
                status = data.get("data", {}).get("status", "unknown")
            else:
                status = data.get("status", "unknown")

            assert status in ("healthy", "degraded"), f"API状态异常: {status}"

            print(f"\n✅ API健康检查通过")
            print(f"   状态: {status}")


@pytest.mark.asyncio
async def test_simple_query():
    """测试简单查询"""
    url = f"{API_BASE_URL}/api/v1/chat"
    payload = {
        "query": "你好",
        "user_id": 1,
        "stream": False
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
            assert response.status == 200, f"查询请求失败: {response.status}"

            data = await response.json()
            # API返回格式: {"code": 200, "data": {"response": "..."}} 或直接 {"response": "..."}
            has_response = "response" in data or "answer" in data or (
                "data" in data and isinstance(data["data"], dict) and "response" in data["data"]
            )
            assert has_response, f"响应格式不正确: {list(data.keys())}"
            
            print(f"\n✅ 简单查询测试通过")
            print(f"   响应长度: {len(str(data))} 字符")


@pytest.mark.asyncio
async def test_concurrent_requests():
    """测试并发请求（小规模）"""
    url = f"{API_BASE_URL}/api/v1/chat"
    
    async def make_request(session, i):
        payload = {
            "query": f"测试查询 {i}",
            "user_id": i + 1,
            "stream": False
        }
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
            return response.status == 200
    
    async with aiohttp.ClientSession() as session:
        # 并发5个请求
        tasks = [make_request(session, i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        
        print(f"\n✅ 并发请求测试通过")
        print(f"   成功: {success_count}/5")
        
        assert success_count >= 3, f"并发请求成功率过低: {success_count}/5"


if __name__ == "__main__":
    # 直接运行测试
    print("开始快速验证测试...")
    pytest.main([__file__, "-v", "-s"])
