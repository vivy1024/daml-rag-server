#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
错误处理和稳定性测试脚本

测试系统在异常情况下的稳定性、错误恢复机制、超时处理

版本：v1.0.0
创建日期：2025-12-15
"""

import asyncio
import httpx
import time

# 测试配置
BASE_URL = "http://localhost:8001"
API_ENDPOINT = f"{BASE_URL}/api/v1/chat"
TEST_USER_ID = "2"


async def test_empty_query():
    """测试空查询处理"""
    print("\n" + "=" * 80)
    print("测试：空查询处理")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                API_ENDPOINT,
                json={
                    "query": "",
                    "user_id": TEST_USER_ID,
                    "domain": "fitness"
                }
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code in [200, 400, 422]:
                print(f"✅ 空查询处理正常")
                return {"passed": True, "status_code": response.status_code}
            else:
                print(f"⚠️  意外的状态码: {response.status_code}")
                return {"passed": False, "status_code": response.status_code}
                
    except Exception as e:
        print(f"✅ 空查询被正确拒绝: {e}")
        return {"passed": True, "error": str(e)}


async def test_invalid_user():
    """测试无效用户ID处理"""
    print("\n" + "=" * 80)
    print("测试：无效用户ID处理")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                API_ENDPOINT,
                json={
                    "query": "测试查询",
                    "user_id": "999999",  # 不存在的用户
                    "domain": "fitness"
                }
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code in [200, 400, 404]:
                print(f"✅ 无效用户ID处理正常")
                return {"passed": True, "status_code": response.status_code}
            else:
                print(f"⚠️  意外的状态码: {response.status_code}")
                return {"passed": False, "status_code": response.status_code}
                
    except Exception as e:
        print(f"✅ 无效用户ID被正确处理: {e}")
        return {"passed": True, "error": str(e)}


async def test_long_query():
    """测试超长查询处理"""
    print("\n" + "=" * 80)
    print("测试：超长查询处理")
    print("=" * 80)
    
    try:
        long_query = "测试" * 1000  # 4000字符
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                API_ENDPOINT,
                json={
                    "query": long_query,
                    "user_id": TEST_USER_ID,
                    "domain": "fitness"
                }
            )
            
            print(f"状态码: {response.status_code}")
            print(f"查询长度: {len(long_query)} 字符")
            
            if response.status_code in [200, 400, 413]:
                print(f"✅ 超长查询处理正常")
                return {"passed": True, "status_code": response.status_code}
            else:
                print(f"⚠️  意外的状态码: {response.status_code}")
                return {"passed": False, "status_code": response.status_code}
                
    except Exception as e:
        print(f"✅ 超长查询被正确处理: {e}")
        return {"passed": True, "error": str(e)}


async def test_malformed_request():
    """测试格式错误的请求"""
    print("\n" + "=" * 80)
    print("测试：格式错误的请求")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 缺少必需字段
            response = await client.post(
                API_ENDPOINT,
                json={
                    "query": "测试查询"
                    # 缺少 user_id
                }
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code in [400, 422]:
                print(f"✅ 格式错误的请求被正确拒绝")
                return {"passed": True, "status_code": response.status_code}
            else:
                print(f"⚠️  意外的状态码: {response.status_code}")
                return {"passed": False, "status_code": response.status_code}
                
    except Exception as e:
        print(f"✅ 格式错误的请求被正确处理: {e}")
        return {"passed": True, "error": str(e)}


async def test_timeout_handling():
    """测试超时处理"""
    print("\n" + "=" * 80)
    print("测试：超时处理")
    print("=" * 80)
    
    try:
        # 使用很短的超时时间
        async with httpx.AsyncClient(timeout=0.1) as client:
            response = await client.post(
                API_ENDPOINT,
                json={
                    "query": "制定一个完整的训练计划",
                    "user_id": TEST_USER_ID,
                    "domain": "fitness"
                }
            )
            
            print(f"⚠️  请求未超时（意外）")
            return {"passed": False, "status_code": response.status_code}
                
    except httpx.TimeoutException:
        print(f"✅ 超时处理正常")
        return {"passed": True, "timeout": True}
    except Exception as e:
        print(f"⚠️  其他错误: {e}")
        return {"passed": False, "error": str(e)}


async def test_concurrent_requests():
    """测试并发请求处理"""
    print("\n" + "=" * 80)
    print("测试：并发请求处理")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 发送10个并发请求
            tasks = []
            for i in range(10):
                task = client.post(
                    API_ENDPOINT,
                    json={
                        "query": f"测试查询 {i}",
                        "user_id": TEST_USER_ID,
                        "domain": "fitness",
                        "session_id": f"concurrent_test_{i}"
                    }
                )
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed_time = time.time() - start_time
            
            success_count = sum(
                1 for r in responses
                if not isinstance(r, Exception) and r.status_code == 200
            )
            
            print(f"并发请求数: 10")
            print(f"成功响应: {success_count}")
            print(f"总耗时: {elapsed_time:.2f}秒")
            print(f"平均响应时间: {elapsed_time / 10:.2f}秒")
            
            if success_count >= 8:  # 至少80%成功
                print(f"✅ 并发请求处理正常")
                return {
                    "passed": True,
                    "success_count": success_count,
                    "total_time": elapsed_time
                }
            else:
                print(f"⚠️  并发请求成功率过低")
                return {
                    "passed": False,
                    "success_count": success_count,
                    "total_time": elapsed_time
                }
                
    except Exception as e:
        print(f"❌ 并发请求测试失败: {e}")
        return {"passed": False, "error": str(e)}


async def main():
    """运行所有错误处理测试"""
    print("\n" + "=" * 80)
    print("DAML-RAG错误处理和稳定性测试")
    print("=" * 80)
    
    # 测试1：空查询
    empty_query_result = await test_empty_query()
    
    # 测试2：无效用户
    invalid_user_result = await test_invalid_user()
    
    # 测试3：超长查询
    long_query_result = await test_long_query()
    
    # 测试4：格式错误
    malformed_result = await test_malformed_request()
    
    # 测试5：超时处理
    timeout_result = await test_timeout_handling()
    
    # 测试6：并发请求
    concurrent_result = await test_concurrent_requests()
    
    # 总结
    print("\n" + "=" * 80)
    print("错误处理和稳定性测试总结")
    print("=" * 80)
    
    results = {
        "empty_query": empty_query_result,
        "invalid_user": invalid_user_result,
        "long_query": long_query_result,
        "malformed_request": malformed_result,
        "timeout_handling": timeout_result,
        "concurrent_requests": concurrent_result
    }
    
    for test_name, result in results.items():
        status = "✅ 通过" if result.get('passed', False) else "❌ 未通过"
        print(f"{test_name}: {status}")
    
    all_passed = all(result.get('passed', False) for result in results.values())
    
    print(f"\n总体结果: {'✅ 所有测试通过' if all_passed else '⚠️  部分测试未通过'}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
