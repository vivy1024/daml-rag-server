#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Chat路由配置

检查 /api/v1/chat 端点是否正确挂载
"""

import requests
import json

def verify_routes():
    """验证路由配置"""
    print("=" * 60)
    print("验证Chat路由配置")
    print("=" * 60)
    
    # 1. 获取所有路由
    try:
        response = requests.get('http://localhost:8001/debug/routes')
        if response.status_code == 200:
            routes = response.json()['routes']
            
            # 过滤chat相关路由
            chat_routes = [r for r in routes if 'chat' in r['path'].lower()]
            
            print(f"\n✅ 找到 {len(chat_routes)} 个Chat相关路由:\n")
            for route in chat_routes:
                methods = ', '.join(route['methods'])
                print(f"  {methods:10} {route['path']}")
            
            # 检查关键路由
            required_routes = ['/api/chat', '/api/v1/chat', '/api/v1/chat/stream']
            found_routes = [r['path'] for r in chat_routes]
            
            print("\n" + "=" * 60)
            print("关键路由检查:")
            print("=" * 60)
            
            for req_route in required_routes:
                if req_route in found_routes:
                    print(f"  ✅ {req_route} - 已挂载")
                else:
                    print(f"  ❌ {req_route} - 未找到")
            
        else:
            print(f"❌ 无法获取路由列表: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 获取路由失败: {e}")
    
    # 2. 测试 /api/v1/chat 端点
    print("\n" + "=" * 60)
    print("测试 /api/v1/chat 端点:")
    print("=" * 60)
    
    try:
        test_data = {
            "user_id": "test_user",
            "query": "测试查询"
        }
        
        response = requests.post(
            'http://localhost:8001/api/v1/chat',
            json=test_data,
            timeout=60
        )
        
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应码: {result.get('code')}")
            print(f"消息: {result.get('msg')}")
            
            data = result.get('data', {})
            print(f"\n响应数据:")
            print(f"  - interaction_id: {data.get('interaction_id')}")
            print(f"  - model_used: {data.get('model_used')}")
            print(f"  - execution_time: {data.get('execution_time'):.2f}s")
            print(f"  - tools_used: {len(data.get('tools_used', []))} 个工具")
            
            print(f"\n✅ /api/v1/chat 端点工作正常")
        else:
            print(f"❌ 端点返回错误: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

if __name__ == "__main__":
    verify_routes()
