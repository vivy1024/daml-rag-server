#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API端点验证脚本

验证任务13的要求：
1. 确认 /api/v1/chat 端点可访问
2. 检查 src/api/main.py 路由配置
3. 确保chat路由正确挂载
"""

import sys
import requests
import json
from pathlib import Path

def check_file_exists(file_path: str) -> bool:
    """检查文件是否存在"""
    path = Path(file_path)
    if path.exists():
        print(f"  ✅ 文件存在: {file_path}")
        return True
    else:
        print(f"  ❌ 文件不存在: {file_path}")
        return False

def check_route_registration(file_path: str) -> bool:
    """检查路由注册"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查关键导入
        checks = {
            "导入chat路由": "from .routes import api_router" in content or "from .routes.chat import router" in content,
            "注册api_router": "app.include_router(api_router" in content,
            "路由前缀/api": 'prefix="/api"' in content
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                print(f"  ✅ {check_name}")
            else:
                print(f"  ❌ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ❌ 检查失败: {e}")
        return False

def test_endpoint(url: str, method: str = "POST", data: dict = None) -> bool:
    """测试API端点"""
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=60)
        else:
            response = requests.get(url, timeout=10)
        
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if 'code' in result:
                print(f"  响应码: {result.get('code')}")
                print(f"  消息: {result.get('msg')}")
                
                if result.get('code') == 200:
                    print(f"  ✅ 端点工作正常")
                    return True
                else:
                    print(f"  ❌ 业务错误: {result.get('msg')}")
                    return False
            else:
                print(f"  ✅ 端点返回数据")
                return True
        else:
            print(f"  ❌ HTTP错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        return False

def main():
    """主验证流程"""
    print("=" * 70)
    print("API端点验证 - 任务13")
    print("=" * 70)
    
    results = {}
    
    # 1. 检查main.py文件
    print("\n【检查1】验证 src/api/main.py 文件存在")
    print("-" * 70)
    results['main_py_exists'] = check_file_exists('src/api/main.py')
    
    # 2. 检查路由配置
    print("\n【检查2】验证路由配置")
    print("-" * 70)
    results['route_config'] = check_route_registration('src/api/main.py')
    
    # 3. 检查chat.py文件
    print("\n【检查3】验证 src/api/routes/chat.py 文件存在")
    print("-" * 70)
    results['chat_py_exists'] = check_file_exists('src/api/routes/chat.py')
    
    # 4. 检查__init__.py文件
    print("\n【检查4】验证 src/api/routes/__init__.py 文件存在")
    print("-" * 70)
    results['init_py_exists'] = check_file_exists('src/api/routes/__init__.py')
    
    # 5. 测试 /api/v1/chat 端点
    print("\n【检查5】测试 /api/v1/chat 端点")
    print("-" * 70)
    test_data = {
        "user_id": "test_user",
        "query": "验证端点测试"
    }
    results['chat_endpoint'] = test_endpoint(
        'http://localhost:8001/api/v1/chat',
        method='POST',
        data=test_data
    )
    
    # 6. 测试 /api/chat 端点（兼容性）
    print("\n【检查6】测试 /api/chat 端点（兼容性）")
    print("-" * 70)
    results['chat_compat_endpoint'] = test_endpoint(
        'http://localhost:8001/api/chat',
        method='POST',
        data=test_data
    )
    
    # 7. 测试根路径
    print("\n【检查7】测试根路径 /")
    print("-" * 70)
    results['root_endpoint'] = test_endpoint(
        'http://localhost:8001/',
        method='GET'
    )
    
    # 8. 测试健康检查
    print("\n【检查8】测试健康检查 /api/health")
    print("-" * 70)
    results['health_endpoint'] = test_endpoint(
        'http://localhost:8001/api/health',
        method='GET'
    )
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("验证结果汇总")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for check_name, passed_check in results.items():
        status = "✅ 通过" if passed_check else "❌ 失败"
        print(f"  {status} - {check_name}")
    
    print("\n" + "-" * 70)
    print(f"总计: {passed}/{total} 项检查通过")
    print("=" * 70)
    
    # 核心要求检查
    print("\n【任务13核心要求】")
    print("-" * 70)
    
    core_requirements = {
        "1. /api/v1/chat 端点可访问": results.get('chat_endpoint', False),
        "2. src/api/main.py 路由配置正确": results.get('route_config', False),
        "3. chat路由正确挂载": results.get('chat_py_exists', False) and results.get('init_py_exists', False)
    }
    
    all_core_passed = all(core_requirements.values())
    
    for req, passed_req in core_requirements.items():
        status = "✅" if passed_req else "❌"
        print(f"  {status} {req}")
    
    print("\n" + "=" * 70)
    if all_core_passed:
        print("✅ 任务13验证通过！所有核心要求已满足。")
        print("=" * 70)
        return 0
    else:
        print("❌ 任务13验证失败！部分核心要求未满足。")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
