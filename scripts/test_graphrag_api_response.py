#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试GraphRAG API响应格式
"""

import asyncio
import aiohttp
import json


async def test_api_response():
    """测试API响应"""
    
    print("=" * 80)
    print("🔍 测试GraphRAG API响应格式")
    print("=" * 80)
    
    url = "http://localhost:8001/api/graphrag/query"
    payload = {
        "query_text": "胸部训练动作",
        "domain": "fitness_exercises",
        "query_type": "semantic_search",
        "top_k": 3,
        "filters": {},
        "return_reason": False,
        "user_id": "test_user"
    }
    
    print(f"\n→ 请求URL: {url}")
    print(f"→ 请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                print(f"\n→ 响应状态码: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"\n→ 响应数据结构:")
                    print(f"  - 顶层键: {list(data.keys())}")
                    
                    if "data" in data:
                        print(f"  - data键: {list(data['data'].keys())}")
                        
                        if "results" in data["data"]:
                            results = data["data"]["results"]
                            print(f"  - results类型: {type(results)}")
                            print(f"  - results长度: {len(results)}")
                            
                            if results:
                                print(f"\n→ 第一个结果:")
                                first_result = results[0]
                                print(f"  - 类型: {type(first_result)}")
                                print(f"  - 内容: {json.dumps(first_result, ensure_ascii=False, indent=4, default=str)}")
                        else:
                            print(f"  - ⚠️ data中没有results键")
                    else:
                        print(f"  - ⚠️ 响应中没有data键")
                        print(f"\n完整响应: {json.dumps(data, ensure_ascii=False, indent=2, default=str)}")
                else:
                    text = await response.text()
                    print(f"\n❌ API返回错误: {text}")
    
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("✅ 测试完成")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(test_api_response())
