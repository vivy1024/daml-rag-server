#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Feature Flag功能

验证USE_NEW_CACHE环境变量是否正确控制新旧缓存切换
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, '/app/src')

def test_feature_flag():
    """测试feature flag读取"""
    print("=" * 60)
    print("测试Feature Flag功能")
    print("=" * 60)
    
    # 测试1：默认值（应该是false）
    use_new = os.getenv('USE_NEW_CACHE', 'false').lower() in ('true', '1', 'yes')
    print(f"\n1. 默认配置（USE_NEW_CACHE未设置或=false）")
    print(f"   USE_NEW_CACHE环境变量: {os.getenv('USE_NEW_CACHE', 'false')}")
    print(f"   使用新缓存: {use_new}")
    print(f"   预期: False")
    print(f"   结果: {'✅ 通过' if not use_new else '❌ 失败'}")
    
    # 测试2：设置为true
    os.environ['USE_NEW_CACHE'] = 'true'
    use_new = os.getenv('USE_NEW_CACHE', 'false').lower() in ('true', '1', 'yes')
    print(f"\n2. 设置USE_NEW_CACHE=true")
    print(f"   USE_NEW_CACHE环境变量: {os.getenv('USE_NEW_CACHE')}")
    print(f"   使用新缓存: {use_new}")
    print(f"   预期: True")
    print(f"   结果: {'✅ 通过' if use_new else '❌ 失败'}")
    
    # 测试3：设置为1
    os.environ['USE_NEW_CACHE'] = '1'
    use_new = os.getenv('USE_NEW_CACHE', 'false').lower() in ('true', '1', 'yes')
    print(f"\n3. 设置USE_NEW_CACHE=1")
    print(f"   USE_NEW_CACHE环境变量: {os.getenv('USE_NEW_CACHE')}")
    print(f"   使用新缓存: {use_new}")
    print(f"   预期: True")
    print(f"   结果: {'✅ 通过' if use_new else '❌ 失败'}")
    
    # 测试4：设置为false
    os.environ['USE_NEW_CACHE'] = 'false'
    use_new = os.getenv('USE_NEW_CACHE', 'false').lower() in ('true', '1', 'yes')
    print(f"\n4. 设置USE_NEW_CACHE=false")
    print(f"   USE_NEW_CACHE环境变量: {os.getenv('USE_NEW_CACHE')}")
    print(f"   使用新缓存: {use_new}")
    print(f"   预期: False")
    print(f"   结果: {'✅ 通过' if not use_new else '❌ 失败'}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    test_feature_flag()
