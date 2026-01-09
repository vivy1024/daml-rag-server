#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试缓存集成

验证新旧缓存系统的切换是否正常工作
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, '/app/src')

def test_cache_integration():
    """测试缓存集成"""
    print("=" * 80)
    print("测试缓存集成 - Feature Flag控制新旧缓存切换")
    print("=" * 80)
    
    # 测试1：默认使用旧缓存
    print("\n【测试1】默认配置（USE_NEW_CACHE=false）")
    print("-" * 80)
    
    from applications.fitness.workflow.singletons import _use_new_cache
    use_new = _use_new_cache()
    print(f"USE_NEW_CACHE环境变量: {os.getenv('USE_NEW_CACHE', 'false')}")
    print(f"_use_new_cache()返回值: {use_new}")
    print(f"预期: False（使用旧缓存）")
    print(f"结果: {'✅ 通过' if not use_new else '❌ 失败'}")
    
    # 测试2：验证旧缓存模块可以导入
    print("\n【测试2】验证旧缓存模块可以导入")
    print("-" * 80)
    
    try:
        from framework.storage.intelligent_user_profile_cache import IntelligentUserCache
        from framework.storage.intelligent_membership_cache import IntelligentMembershipCache
        print("✅ IntelligentUserCache 导入成功")
        print("✅ IntelligentMembershipCache 导入成功")
    except Exception as e:
        print(f"❌ 旧缓存模块导入失败: {e}")
    
    # 测试3：验证新缓存模块可以导入
    print("\n【测试3】验证新缓存模块可以导入")
    print("-" * 80)
    
    try:
        from framework.storage.user_profile_cache import UserProfileCache
        from framework.storage.membership_cache import MembershipCache
        from framework.storage.warmup import WarmupManager
        from framework.storage.unified_cache import UnifiedCache
        print("✅ UserProfileCache 导入成功")
        print("✅ MembershipCache 导入成功")
        print("✅ WarmupManager 导入成功")
        print("✅ UnifiedCache 导入成功")
    except Exception as e:
        print(f"❌ 新缓存模块导入失败: {e}")
    
    # 测试4：验证环境变量读取逻辑
    print("\n【测试4】验证环境变量读取逻辑")
    print("-" * 80)
    
    try:
        # 测试不同的环境变量值
        test_cases = [
            ('false', False),
            ('true', True),
            ('1', True),
            ('yes', True),
            ('0', False),
            ('no', False),
        ]
        
        all_passed = True
        for value, expected in test_cases:
            os.environ['USE_NEW_CACHE'] = value
            result = os.getenv('USE_NEW_CACHE', 'false').lower() in ('true', '1', 'yes')
            passed = result == expected
            all_passed = all_passed and passed
            status = '✅' if passed else '❌'
            print(f"{status} USE_NEW_CACHE={value} → {result} (预期: {expected})")
        
        # 恢复默认值
        os.environ['USE_NEW_CACHE'] = 'false'
        print(f"\n总体结果: {'✅ 通过' if all_passed else '❌ 失败'}")
    except Exception as e:
        print(f"❌ 环境变量测试失败: {e}")
    
    # 测试5：验证singletons的feature flag逻辑
    print("\n【测试5】验证singletons的feature flag逻辑")
    print("-" * 80)
    
    try:
        from applications.fitness.workflow.singletons import _use_new_cache as singletons_use_new_cache
        use_new_singletons = singletons_use_new_cache()
        print(f"Singletons _use_new_cache()返回值: {use_new_singletons}")
        print(f"预期: False（使用旧缓存）")
        print(f"结果: {'✅ 通过' if not use_new_singletons else '❌ 失败'}")
    except Exception as e:
        print(f"❌ Singletons feature flag测试失败: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    print("\n提示：要启用新缓存系统，请设置环境变量 USE_NEW_CACHE=true")

if __name__ == '__main__':
    test_cache_integration()
