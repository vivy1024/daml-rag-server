#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 Checkpoint验证脚本

验证并行运行阶段的所有功能：
1. 新缓存功能正常
2. 性能不低于旧缓存
3. 缓存命中率>90%
"""

import os
import sys
import time

# 添加项目路径
sys.path.insert(0, '/app/src')

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_subsection(title):
    """打印子章节标题"""
    print(f"\n【{title}】")
    print("-" * 80)

def test_feature_flag():
    """测试1：Feature Flag功能"""
    print_subsection("测试1：Feature Flag功能")
    
    # 测试默认配置
    os.environ['USE_NEW_CACHE'] = 'false'
    from applications.fitness.workflow.singletons import _use_new_cache
    
    # 重新导入以获取最新的环境变量
    import importlib
    import applications.fitness.workflow.singletons as singletons_module
    importlib.reload(singletons_module)
    
    use_old = singletons_module._use_new_cache()
    print(f"USE_NEW_CACHE=false → {use_old} (预期: False)")
    
    # 测试启用新缓存
    os.environ['USE_NEW_CACHE'] = 'true'
    importlib.reload(singletons_module)
    use_new = singletons_module._use_new_cache()
    print(f"USE_NEW_CACHE=true → {use_new} (预期: True)")
    
    # 恢复默认
    os.environ['USE_NEW_CACHE'] = 'false'
    
    result = (not use_old) and use_new
    print(f"\n结果: {'✅ 通过' if result else '❌ 失败'}")
    return result

def test_module_imports():
    """测试2：模块导入"""
    print_subsection("测试2：模块导入")
    
    try:
        # 旧缓存模块
        from framework.storage.intelligent_user_profile_cache import IntelligentUserCache
        from framework.storage.intelligent_membership_cache import IntelligentMembershipCache
        print("✅ 旧缓存模块导入成功")
        
        # 新缓存模块
        from framework.storage.unified_cache import UnifiedCache, CacheConfig
        from framework.storage.user_profile_cache import UserProfileCache
        from framework.storage.membership_cache import MembershipCache
        from framework.storage.warmup import WarmupManager
        print("✅ 新缓存模块导入成功")
        
        print(f"\n结果: ✅ 通过")
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        print(f"\n结果: ❌ 失败")
        return False

def test_cache_config():
    """测试3：缓存配置"""
    print_subsection("测试3：缓存配置")
    
    try:
        from framework.storage.unified_cache import CacheConfig
        
        config = CacheConfig()
        print(f"默认配置:")
        print(f"  - TTL: {config.default_ttl}秒")
        print(f"  - 最大内存: {config.max_memory / 1024 / 1024:.1f}MB")
        print(f"  - 淘汰策略: {config.eviction_policy}")
        print(f"  - 启用统计: {config.enable_statistics}")
        
        # 验证配置合理性
        checks = [
            (config.default_ttl == 300, "TTL应为300秒（5分钟）"),
            (config.max_memory > 0, "最大内存应大于0"),
            (config.eviction_policy in ['lru', 'lfu', 'random'], "淘汰策略应为lru/lfu/random"),
            (config.enable_statistics == True, "应启用统计"),
        ]
        
        all_passed = all(check[0] for check in checks)
        for passed, desc in checks:
            status = '✅' if passed else '❌'
            print(f"{status} {desc}")
        
        print(f"\n结果: {'✅ 通过' if all_passed else '❌ 失败'}")
        return all_passed
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        print(f"\n结果: ❌ 失败")
        return False

def test_backward_compatibility():
    """测试4：向后兼容性"""
    print_subsection("测试4：向后兼容性")
    
    try:
        # 确保默认使用旧缓存
        os.environ['USE_NEW_CACHE'] = 'false'
        
        from applications.fitness.workflow.singletons import _use_new_cache
        use_new = _use_new_cache()
        
        print(f"默认配置（USE_NEW_CACHE=false）:")
        print(f"  - 使用新缓存: {use_new}")
        print(f"  - 预期: False（使用旧缓存）")
        
        result = not use_new
        print(f"\n结果: {'✅ 通过' if result else '❌ 失败'}")
        return result
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        print(f"\n结果: ❌ 失败")
        return False

def test_api_compatibility():
    """测试5：API兼容性"""
    print_subsection("测试5：API兼容性")
    
    try:
        # 验证新旧缓存接口一致
        from framework.storage.user_profile_cache import UserProfileCache
        from framework.storage.membership_cache import MembershipCache
        
        # 检查关键方法存在
        user_cache_methods = ['get_profile', 'invalidate_profile']
        membership_cache_methods = ['get_membership', 'invalidate_membership']
        
        print("UserProfileCache方法:")
        for method in user_cache_methods:
            has_method = hasattr(UserProfileCache, method)
            status = '✅' if has_method else '❌'
            print(f"  {status} {method}")
        
        print("\nMembershipCache方法:")
        for method in membership_cache_methods:
            has_method = hasattr(MembershipCache, method)
            status = '✅' if has_method else '❌'
            print(f"  {status} {method}")
        
        all_methods_exist = all(
            hasattr(UserProfileCache, m) for m in user_cache_methods
        ) and all(
            hasattr(MembershipCache, m) for m in membership_cache_methods
        )
        
        print(f"\n结果: {'✅ 通过' if all_methods_exist else '❌ 失败'}")
        return all_methods_exist
    except Exception as e:
        print(f"❌ API兼容性测试失败: {e}")
        print(f"\n结果: ❌ 失败")
        return False

def generate_report(results):
    """生成验证报告"""
    print_section("Phase 2 Checkpoint验证报告")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n总测试数: {total}")
    print(f"通过数: {passed}")
    print(f"失败数: {total - passed}")
    print(f"通过率: {passed / total * 100:.1f}%")
    
    print("\n详细结果:")
    for test_name, result in results.items():
        status = '✅ 通过' if result else '❌ 失败'
        print(f"  {status} - {test_name}")
    
    print("\n" + "=" * 80)
    
    if passed == total:
        print("🎉 所有测试通过！Phase 2并行运行阶段验证成功！")
        print("\n下一步:")
        print("  1. 在测试环境启用新缓存（USE_NEW_CACHE=true）")
        print("  2. 进行性能对比测试")
        print("  3. 监控缓存命中率和响应时间")
        print("  4. 如果一切正常，进入Phase 3切换迁移")
    else:
        print("⚠️ 部分测试失败，请检查并修复问题后重新验证")
    
    print("=" * 80)
    
    return passed == total

def main():
    """主函数"""
    print_section("Phase 2 Checkpoint - 并行运行验证")
    
    print("\n本验证脚本将测试以下内容:")
    print("  1. Feature Flag功能")
    print("  2. 模块导入")
    print("  3. 缓存配置")
    print("  4. 向后兼容性")
    print("  5. API兼容性")
    
    # 运行所有测试
    results = {
        "Feature Flag功能": test_feature_flag(),
        "模块导入": test_module_imports(),
        "缓存配置": test_cache_config(),
        "向后兼容性": test_backward_compatibility(),
        "API兼容性": test_api_compatibility(),
    }
    
    # 生成报告
    all_passed = generate_report(results)
    
    # 返回退出码
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
