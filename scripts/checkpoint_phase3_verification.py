#!/usr/bin/env python3
"""
Phase 3 迁移成功验证脚本

验证项目：
1. 所有功能正常
2. 无运行时错误
3. 监控指标正常（缓存命中率>90%，响应时间<10ms）
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework.storage.unified_cache import UnifiedCache, CacheConfig
from framework.storage.user_profile_cache import UserProfileCache
from framework.storage.membership_cache import MembershipCache
from framework.storage.warmup import WarmupManager, WarmupConfig
import redis.asyncio as redis


class Phase3Verifier:
    """Phase 3 迁移验证器"""
    
    def __init__(self):
        self.redis_client = None
        self.unified_cache = None
        self.user_cache = None
        self.membership_cache = None
        self.warmup_manager = None
        self.results = {
            "功能测试": [],
            "错误检查": [],
            "性能指标": [],
            "总体状态": "未知"
        }
    
    async def setup(self):
        """初始化测试环境"""
        print("🔧 初始化测试环境...")
        
        # 连接Redis（使用Docker网络中的主机名）
        import os
        redis_host = os.getenv('REDIS_HOST', 'fitness_redis')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=0,
            decode_responses=True
        )
        
        # 创建统一缓存
        config = CacheConfig(
            default_ttl=300,
            enable_statistics=True
        )
        self.unified_cache = UnifiedCache(self.redis_client, config)
        
        # 创建专用缓存
        self.user_cache = UserProfileCache(self.unified_cache)
        self.membership_cache = MembershipCache(self.unified_cache)
        
        # 创建预加载管理器
        warmup_config = WarmupConfig(
            enabled=True,
            batch_size=10,
            max_concurrent=3,
            timeout=10
        )
        self.warmup_manager = WarmupManager(warmup_config)
        
        print("✅ 测试环境初始化完成\n")
    
    async def test_unified_cache(self):
        """测试统一缓存功能"""
        print("📦 测试统一缓存...")
        
        try:
            # 测试基本操作
            test_key = "test:unified:key"
            test_value = {"data": "test_value", "timestamp": time.time()}
            
            # Set
            await self.unified_cache.set(test_key, test_value, ttl=60)
            
            # Get
            result = await self.unified_cache.get(test_key)
            assert result == test_value, "缓存值不匹配"
            
            # Delete
            await self.unified_cache.delete(test_key)
            result = await self.unified_cache.get(test_key)
            assert result is None, "删除后仍能获取到值"
            
            self.results["功能测试"].append({
                "测试项": "统一缓存基本操作",
                "状态": "✅ 通过"
            })
            print("  ✅ 统一缓存基本操作正常")
            
        except Exception as e:
            self.results["功能测试"].append({
                "测试项": "统一缓存基本操作",
                "状态": f"❌ 失败: {str(e)}"
            })
            print(f"  ❌ 统一缓存测试失败: {e}")
    
    async def test_user_profile_cache(self):
        """测试用户档案缓存"""
        print("👤 测试用户档案缓存...")
        
        try:
            test_user_id = 99999
            
            # 测试缓存未命中（应该返回None，因为没有数据库）
            profile = await self.user_cache.get_profile(test_user_id)
            
            # 手动设置一个测试档案
            test_profile = {
                "user_id": test_user_id,
                "nickname": "测试用户",
                "age": 25,
                "gender": "male"
            }
            cache_key = f"user_profile:{test_user_id}"
            await self.unified_cache.set(cache_key, test_profile, ttl=300)
            
            # 测试缓存命中
            profile = await self.user_cache.get_profile(test_user_id)
            assert profile == test_profile, "用户档案不匹配"
            
            # 测试缓存失效
            await self.user_cache.invalidate_profile(test_user_id)
            profile = await self.user_cache.get_profile(test_user_id)
            assert profile is None, "失效后仍能获取到档案"
            
            self.results["功能测试"].append({
                "测试项": "用户档案缓存",
                "状态": "✅ 通过"
            })
            print("  ✅ 用户档案缓存正常")
            
        except Exception as e:
            self.results["功能测试"].append({
                "测试项": "用户档案缓存",
                "状态": f"❌ 失败: {str(e)}"
            })
            print(f"  ❌ 用户档案缓存测试失败: {e}")
    
    async def test_membership_cache(self):
        """测试会员缓存"""
        print("💎 测试会员缓存...")
        
        try:
            test_user_id = 99999
            
            # 手动设置一个测试会员信息
            test_membership = {
                "user_id": test_user_id,
                "level": "premium",
                "expires_at": "2026-12-31"
            }
            cache_key = f"membership:{test_user_id}"
            await self.unified_cache.set(cache_key, test_membership, ttl=600)
            
            # 测试缓存命中
            membership = await self.membership_cache.get_membership(test_user_id)
            assert membership == test_membership, "会员信息不匹配"
            
            # 测试缓存失效
            await self.membership_cache.invalidate_membership(test_user_id)
            membership = await self.membership_cache.get_membership(test_user_id)
            assert membership is None, "失效后仍能获取到会员信息"
            
            self.results["功能测试"].append({
                "测试项": "会员缓存",
                "状态": "✅ 通过"
            })
            print("  ✅ 会员缓存正常")
            
        except Exception as e:
            self.results["功能测试"].append({
                "测试项": "会员缓存",
                "状态": f"❌ 失败: {str(e)}"
            })
            print(f"  ❌ 会员缓存测试失败: {e}")
    
    async def test_performance_metrics(self):
        """测试性能指标"""
        print("⚡ 测试性能指标...")
        
        try:
            # 预热缓存
            test_keys = [f"perf:test:{i}" for i in range(100)]
            for key in test_keys:
                await self.unified_cache.set(key, {"value": key}, ttl=60)
            
            # 测试响应时间
            start_time = time.time()
            for key in test_keys:
                await self.unified_cache.get(key)
            end_time = time.time()
            
            total_time = (end_time - start_time) * 1000  # 转换为毫秒
            avg_time = total_time / len(test_keys)
            
            # 获取统计信息
            stats = self.unified_cache.get_statistics()
            hit_rate = stats.hit_rate if stats.total_requests > 0 else 0
            
            # 验证指标
            response_time_ok = avg_time < 10  # 小于10ms
            hit_rate_ok = hit_rate > 0.90  # 大于90%
            
            self.results["性能指标"].append({
                "指标": "平均响应时间",
                "值": f"{avg_time:.2f}ms",
                "目标": "<10ms",
                "状态": "✅ 达标" if response_time_ok else "❌ 未达标"
            })
            
            self.results["性能指标"].append({
                "指标": "缓存命中率",
                "值": f"{hit_rate*100:.1f}%",
                "目标": ">90%",
                "状态": "✅ 达标" if hit_rate_ok else "❌ 未达标"
            })
            
            print(f"  📊 平均响应时间: {avg_time:.2f}ms {'✅' if response_time_ok else '❌'}")
            print(f"  📊 缓存命中率: {hit_rate*100:.1f}% {'✅' if hit_rate_ok else '❌'}")
            
            # 清理测试数据
            for key in test_keys:
                await self.unified_cache.delete(key)
            
        except Exception as e:
            self.results["性能指标"].append({
                "指标": "性能测试",
                "状态": f"❌ 失败: {str(e)}"
            })
            print(f"  ❌ 性能测试失败: {e}")
    
    async def check_runtime_errors(self):
        """检查运行时错误"""
        print("🔍 检查运行时错误...")
        
        try:
            # 测试异常情况处理
            
            # 1. 测试无效键
            result = await self.unified_cache.get("nonexistent:key")
            assert result is None, "不存在的键应返回None"
            
            # 2. 测试空值
            await self.unified_cache.set("test:empty", None, ttl=60)
            result = await self.unified_cache.get("test:empty")
            
            # 3. 测试大对象
            large_obj = {"data": "x" * 10000}
            await self.unified_cache.set("test:large", large_obj, ttl=60)
            result = await self.unified_cache.get("test:large")
            assert result == large_obj, "大对象缓存失败"
            
            self.results["错误检查"].append({
                "检查项": "运行时错误处理",
                "状态": "✅ 正常"
            })
            print("  ✅ 无运行时错误")
            
        except Exception as e:
            self.results["错误检查"].append({
                "检查项": "运行时错误处理",
                "状态": f"❌ 发现错误: {str(e)}"
            })
            print(f"  ❌ 发现运行时错误: {e}")
    
    async def cleanup(self):
        """清理测试环境"""
        print("\n🧹 清理测试环境...")
        
        if self.redis_client:
            await self.redis_client.close()
        
        print("✅ 清理完成")
    
    def print_summary(self):
        """打印验证摘要"""
        print("\n" + "="*60)
        print("📋 Phase 3 迁移验证报告")
        print("="*60)
        
        # 功能测试
        print("\n【功能测试】")
        for test in self.results["功能测试"]:
            print(f"  {test['测试项']}: {test['状态']}")
        
        # 错误检查
        print("\n【错误检查】")
        for check in self.results["错误检查"]:
            print(f"  {check['检查项']}: {check['状态']}")
        
        # 性能指标
        print("\n【性能指标】")
        for metric in self.results["性能指标"]:
            if "值" in metric:
                print(f"  {metric['指标']}: {metric['值']} (目标: {metric['目标']}) {metric['状态']}")
            else:
                print(f"  {metric['指标']}: {metric['状态']}")
        
        # 总体评估
        all_passed = all(
            "✅" in str(item.get("状态", "")) 
            for category in ["功能测试", "错误检查", "性能指标"]
            for item in self.results[category]
        )
        
        self.results["总体状态"] = "✅ 通过" if all_passed else "❌ 失败"
        
        print("\n" + "="*60)
        print(f"【总体状态】: {self.results['总体状态']}")
        print("="*60)
        
        if not all_passed:
            print("\n⚠️  发现问题，建议执行回滚计划")
            print("回滚步骤：")
            print("  1. 设置 USE_NEW_CACHE=False")
            print("  2. 重启 DAML-RAG 服务")
            print("  3. 验证旧缓存正常工作")
        else:
            print("\n🎉 所有验证通过，迁移成功！")
        
        return all_passed


async def main():
    """主函数"""
    verifier = Phase3Verifier()
    
    try:
        await verifier.setup()
        
        # 执行所有验证
        await verifier.test_unified_cache()
        await verifier.test_user_profile_cache()
        await verifier.test_membership_cache()
        await verifier.test_performance_metrics()
        await verifier.check_runtime_errors()
        
        # 打印摘要
        success = verifier.print_summary()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await verifier.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
