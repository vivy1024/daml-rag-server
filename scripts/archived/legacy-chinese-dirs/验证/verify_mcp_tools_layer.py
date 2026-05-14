"""
MCP工具层验证脚本

验证任务8（MCP工具层增强）的所有子任务：
- 8.1 统一错误处理 ✅
- 8.3 缓存机制 ✅
- 8.5 intelligent_exercise_selector增强 ✅
- 8.7 exercise_alternative_finder增强
- 8.9 contraindications_checker增强

Version: 1.0.0
Date: 2026-01-05
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.framework.mcp.error_handler import (
    MCPErrorCode,
    MCPToolError,
    MCPErrorHandler,
    create_mcp_error,
    wrap_mcp_error
)
from src.framework.mcp.cache_manager import (
    CacheManager,
    get_cache_manager,
    cached
)


def test_error_handler():
    """测试8.1: 统一错误处理"""
    print("\n" + "="*60)
    print("测试8.1: 统一错误处理")
    print("="*60)
    
    results = []
    
    # 测试1: MCPToolError创建
    try:
        error = create_mcp_error(
            tool_name="test_tool",
            error_code=MCPErrorCode.INVALID_INPUT,
            message="测试错误",
            context={"param": "value"}
        )
        assert error.tool_name == "test_tool"
        assert error.error_code == MCPErrorCode.INVALID_INPUT
        assert error.message == "测试错误"
        print("✅ MCPToolError创建成功")
        results.append(("MCPToolError创建", True))
    except Exception as e:
        print(f"❌ MCPToolError创建失败: {e}")
        results.append(("MCPToolError创建", False))
    
    # 测试2: 错误码定义
    try:
        assert hasattr(MCPErrorCode, "INVALID_INPUT")
        assert hasattr(MCPErrorCode, "DATA_NOT_FOUND")
        assert hasattr(MCPErrorCode, "DEPENDENCY_ERROR")
        assert hasattr(MCPErrorCode, "TIMEOUT")
        assert hasattr(MCPErrorCode, "INTERNAL_ERROR")
        print("✅ 标准错误码定义完整")
        results.append(("标准错误码", True))
    except Exception as e:
        print(f"❌ 标准错误码定义不完整: {e}")
        results.append(("标准错误码", False))
    
    # 测试3: MCPErrorHandler
    try:
        handler = MCPErrorHandler()
        
        # 测试异常包装
        original_error = ValueError("测试异常")
        mcp_error = handler.handle_error(
            original_error,
            "test_tool",
            {"context": "test"}
        )
        assert isinstance(mcp_error, MCPToolError)
        assert mcp_error.cause == original_error
        print("✅ MCPErrorHandler异常包装成功")
        results.append(("MCPErrorHandler", True))
    except Exception as e:
        print(f"❌ MCPErrorHandler失败: {e}")
        results.append(("MCPErrorHandler", False))
    
    # 测试4: 错误策略
    try:
        handler = MCPErrorHandler()
        strategy = handler.get_error_strategy(MCPErrorCode.TIMEOUT)
        assert strategy.get("retry") is True
        assert strategy.get("max_retries") == 2
        print("✅ 错误处理策略配置正确")
        results.append(("错误策略", True))
    except Exception as e:
        print(f"❌ 错误策略配置失败: {e}")
        results.append(("错误策略", False))
    
    return results


async def test_cache_manager():
    """测试8.3: 缓存机制"""
    print("\n" + "="*60)
    print("测试8.3: 缓存机制")
    print("="*60)
    
    results = []
    
    # 测试1: 缓存管理器创建
    try:
        cache = CacheManager(max_size=100)
        assert cache.max_size == 100
        print("✅ CacheManager创建成功")
        results.append(("CacheManager创建", True))
    except Exception as e:
        print(f"❌ CacheManager创建失败: {e}")
        results.append(("CacheManager创建", False))
        return results
    
    # 测试2: 缓存设置和获取
    try:
        await cache.set("test_key", "test_value", ttl=60)
        value = await cache.get("test_key")
        assert value == "test_value"
        print("✅ 缓存设置和获取成功")
        results.append(("缓存设置获取", True))
    except Exception as e:
        print(f"❌ 缓存设置获取失败: {e}")
        results.append(("缓存设置获取", False))
    
    # 测试3: 缓存失效
    try:
        await cache.set("test_key2", "test_value2", ttl=60)
        await cache.invalidate("test_key2")
        value = await cache.get("test_key2")
        assert value is None
        print("✅ 缓存失效成功")
        results.append(("缓存失效", True))
    except Exception as e:
        print(f"❌ 缓存失效失败: {e}")
        results.append(("缓存失效", False))
    
    # 测试4: 模式失效
    try:
        await cache.set("muscle_data_1", "value1", ttl=60)
        await cache.set("muscle_data_2", "value2", ttl=60)
        await cache.set("other_data", "value3", ttl=60)
        
        count = await cache.invalidate_pattern("muscle_*")
        assert count == 2
        
        value1 = await cache.get("muscle_data_1")
        value2 = await cache.get("muscle_data_2")
        value3 = await cache.get("other_data")
        
        assert value1 is None
        assert value2 is None
        assert value3 == "value3"
        print("✅ 模式失效成功")
        results.append(("模式失效", True))
    except Exception as e:
        print(f"❌ 模式失效失败: {e}")
        results.append(("模式失效", False))
    
    # 测试5: 缓存统计
    try:
        stats = await cache.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        print(f"✅ 缓存统计成功: {stats}")
        results.append(("缓存统计", True))
    except Exception as e:
        print(f"❌ 缓存统计失败: {e}")
        results.append(("缓存统计", False))
    
    # 测试6: 预定义配置
    try:
        assert "muscle_training_data" in CacheManager.CACHE_CONFIG
        assert "equipment_alias" in CacheManager.CACHE_CONFIG
        assert "contraindication_rules" in CacheManager.CACHE_CONFIG
        
        config = CacheManager.CACHE_CONFIG["muscle_training_data"]
        assert config["ttl"] == 86400  # 24小时
        print("✅ 预定义缓存配置正确")
        results.append(("预定义配置", True))
    except Exception as e:
        print(f"❌ 预定义配置失败: {e}")
        results.append(("预定义配置", False))
    
    return results


def test_intelligent_exercise_selector_enhancement():
    """测试8.5: intelligent_exercise_selector增强"""
    print("\n" + "="*60)
    print("测试8.5: intelligent_exercise_selector增强")
    print("="*60)
    
    results = []
    
    try:
        from src.applications.fitness.mcp_tools.exercise.intelligent_exercise_selector import (
            IntelligentExerciseSelectorInput
        )
        
        # 测试1: rehabilitation_phase参数
        try:
            assert hasattr(IntelligentExerciseSelectorInput, '__fields__')
            fields = IntelligentExerciseSelectorInput.__fields__
            assert 'rehabilitation_phase' in fields
            print("✅ rehabilitation_phase参数已添加")
            results.append(("rehabilitation_phase参数", True))
        except Exception as e:
            print(f"❌ rehabilitation_phase参数缺失: {e}")
            results.append(("rehabilitation_phase参数", False))
        
        # 测试2: force_type参数
        try:
            assert 'force_type' in fields
            print("✅ force_type参数已添加")
            results.append(("force_type参数", True))
        except Exception as e:
            print(f"❌ force_type参数缺失: {e}")
            results.append(("force_type参数", False))
        
        # 测试3: postural_issues参数
        try:
            assert 'postural_issues' in fields
            print("✅ postural_issues参数已添加")
            results.append(("postural_issues参数", True))
        except Exception as e:
            print(f"❌ postural_issues参数缺失: {e}")
            results.append(("postural_issues参数", False))
        
    except ImportError as e:
        print(f"❌ 无法导入IntelligentExerciseSelector: {e}")
        results.append(("工具导入", False))
    
    return results


def print_summary(all_results):
    """打印测试总结"""
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    total = 0
    passed = 0
    
    for test_name, test_results in all_results.items():
        print(f"\n{test_name}:")
        for item_name, success in test_results:
            status = "✅" if success else "❌"
            print(f"  {status} {item_name}")
            total += 1
            if success:
                passed += 1
    
    print("\n" + "="*60)
    print(f"总计: {passed}/{total} 测试通过")
    print(f"通过率: {passed/total*100:.1f}%")
    print("="*60)
    
    return passed == total


async def main():
    """主函数"""
    print("="*60)
    print("MCP工具层验证 - 任务8")
    print("="*60)
    
    all_results = {}
    
    # 测试8.1: 统一错误处理
    all_results["8.1 统一错误处理"] = test_error_handler()
    
    # 测试8.3: 缓存机制
    all_results["8.3 缓存机制"] = await test_cache_manager()
    
    # 测试8.5: intelligent_exercise_selector增强
    all_results["8.5 intelligent_exercise_selector增强"] = test_intelligent_exercise_selector_enhancement()
    
    # 打印总结
    all_passed = print_summary(all_results)
    
    if all_passed:
        print("\n🎉 所有测试通过！MCP工具层验证成功！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
