# -*- coding: utf-8 -*-
"""
调试greeting API响应格式
"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8001"
API_ENDPOINT = f"{BASE_URL}/api/v1/chat"
TEST_USER_ID = "2"

async def test_greeting_api():
    """测试greeting API并打印完整响应"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("发送请求...")
        response = await client.post(
            API_ENDPOINT,
            json={
                "query": "你好",
                "user_id": TEST_USER_ID,
                "session_id": "debug_greeting",
                "domain": "fitness"
            }
        )
        
        print(f"\n状态码: {response.status_code}")
        print(f"\n完整响应:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_greeting_api())
