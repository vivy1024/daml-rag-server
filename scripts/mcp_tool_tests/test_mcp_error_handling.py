"""
验证MCP工具管理器的错误处理功能

测试：
1. 捕获MCP调用异常
2. 记录详细错误信息（工具名、参数、堆栈）
3. 提供降级方案
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.clients.mcp_tool_manager import (
    MCPToolManager,
    MCPToolNotFoundError,
    MCPParameterError,
    create_mcp_tool_manager
)


class MockMCPClient:
    """模拟MCP客户端"""
    
    def __init__(self, should_fail=False, error_type="general"):
        self.should_fail = should_fail
        self.error_type = error_type
    
    async def call_tool(self, server_name, tool_name, arguments):
        """模拟工具调用"""
        if self.should_fail:
            if self.error_type == "timeout":
                raise asyncio.TimeoutError("模拟超时错误")
            elif self.error_type == "connection":
                raise ConnectionError("模拟连接错误")
            else:
                raise Exception("模拟一般错误")
        
        return {
            "success": True,
            "data": {"result": "模拟成功结果"},
            "tool_name": tool_name
        }


async def test_tool_not_found():
    """测试1: 工具不存在错误"""
    print("\n" + "="*60)
    print("测试1: 工具不存在错误")
    print("="*60)
    
    tool_manager = create_mcp_tool_manager()
    
    try:
        await tool_manager.call_tool(
            task_name="non_existent_tool",
            parameters={}
        )
        print("❌ 测试失败：应该抛出MCPToolNotFoundError")
        return False
    except MCPToolNotFoundError as e:
        print(f"✅ 成功捕获MCPToolNotFoundError")
        print(f"   错误信息: {str(e)[:100]}...")
        return True


async def test_parameter_validation():
    """测试2: 参数验证错误"""
    print("\n" + "="*60)
    print("测试2: 参数验证错误")
    print("="*60)
    
    tool_manager = create_mcp_tool_manager()
    
    try:
        await tool_manager.call_tool(
            task_name="check_contraindications",
            parameters={}  # 缺少必需参数
        )
        print("❌ 测试失败：应该抛出MCPParameterError")
        return False
    except MCPParameterError as e:
        print(f"✅ 成功捕获MCPParameterError")
        print(f"   错误信息: {str(e)}")
        return True


async def test_timeout_error():
    """测试3: 超时错误处理"""
    print("\n" + "="*60)
    print("测试3: 超时错误处理")
    print("="*60)
    
    tool_manager = create_mcp_tool_manager()
    mock_client = MockMCPClient(should_fail=True, error_type="timeout")
    
    result = await tool_manager.call_tool(
        task_name="check_contraindications",
        parameters={
            "user_profile": {"user_id": "test"},
            "exercises": []
        },
        mcp_client=mock_client
    )
    
    print(f"✅ 成功处理超时错误")
    print(f"   success: {result.success}")
    print(f"   fallback_used: {result.fallback_used}")
    print(f"   error_type: {result.error_type}")
    print(f"   error: {result.error}")
    print(f"   stack_trace存在: {result.stack_trace is not None}")
    
    # 验证
    assert result.success is False
    assert result.fallback_used is True
    assert result.error_type == "MCPTimeoutError"
    assert result.stack_trace is not None
    
    return True


async def test_connection_error():
    """测试4: 连接错误处理"""
    print("\n" + "="*60)
    print("测试4: 连接错误处理")
    print("="*60)
    
    tool_manager = create_mcp_tool_manager()
    mock_client = MockMCPClient(should_fail=True, error_type="connection")
    
    result = await tool_manager.call_tool(
        task_name="check_contraindications",
        parameters={
            "user_profile": {"user_id": "test"},
            "exercises": []
        },
        mcp_client=mock_client
    )
    
    print(f"✅ 成功处理连接错误")
    print(f"   success: {result.success}")
    print(f"   fallback_used: {result.fallback_used}")
    print(f"   error_type: {result.error_type}")
    print(f"   error: {result.error}")
    print(f"   降级消息: {result.data.get('message', 'N/A')}")
    print(f"   建议: {result.data.get('suggestion', 'N/A')[:50]}...")
    
    # 验证
    assert result.success is False
    assert result.fallback_used is True
    assert result.error_type == "MCPConnectionError"
    assert "建议" in result.data.get("suggestion", "")
    
    return True


async def test_general_error():
    """测试5: 一般错误处理"""
    print("\n" + "="*60)
    print("测试5: 一般错误处理")
    print("="*60)
    
    tool_manager = create_mcp_tool_manager()
    mock_client = MockMCPClient(should_fail=True, error_type="general")
    
    result = await tool_manager.call_tool(
        task_name="check_contraindications",
        parameters={
            "user_profile": {"user_id": "test"},
            "exercises": []
        },
        mcp_client=mock_client
    )
    
    print(f"✅ 成功处理一般错误")
    print(f"   success: {result.success}")
    print(f"   fallback_used: {result.fallback_used}")
    print(f"   error_type: {result.error_type}")
    print(f"   降级结果包含fallback标记: {'fallback' in result.data}")
    
    # 验证
    assert result.success is False
    assert result.fallback_used is True
    assert result.data.get("fallback") is True
    
    return True


async def test_error_statistics():
    """测试6: 错误统计"""
    print("\n" + "="*60)
    print("测试6: 错误统计")
    print("="*60)
    
    tool_manager = create_mcp_tool_manager()
    mock_client = MockMCPClient(should_fail=True, error_type="general")
    
    # 执行多次调用
    for i in range(3):
        await tool_manager.call_tool(
            task_name="check_contraindications",
            parameters={
                "user_profile": {"user_id": f"test_{i}"},
                "exercises": []
            },
            mcp_client=mock_client
        )
    
    # 获取统计
    stats = tool_manager.get_error_statistics()
    
    print(f"✅ 错误统计功能正常")
    print(f"   总调用次数: {stats['total_calls']}")
    print(f"   失败次数: {stats['failed_calls']}")
    print(f"   降级次数: {stats['fallback_calls']}")
    print(f"   成功率: {stats['success_rate']}")
    print(f"   错误类型统计: {stats['error_by_type']}")
    print(f"   工具错误统计: {stats['error_by_tool']}")
    
    # 验证
    assert stats["total_calls"] == 3
    assert stats["failed_calls"] == 3
    assert stats["fallback_calls"] == 3
    
    return True


async def test_successful_call():
    """测试7: 成功调用（不使用降级）"""
    print("\n" + "="*60)
    print("测试7: 成功调用")
    print("="*60)
    
    tool_manager = create_mcp_tool_manager()
    mock_client = MockMCPClient(should_fail=False)
    
    result = await tool_manager.call_tool(
        task_name="check_contraindications",
        parameters={
            "user_profile": {"user_id": "test"},
            "exercises": []
        },
        mcp_client=mock_client
    )
    
    print(f"✅ 成功调用")
    print(f"   success: {result.success}")
    print(f"   fallback_used: {result.fallback_used}")
    print(f"   error: {result.error}")
    print(f"   data: {result.data}")
    
    # 验证
    assert result.success is True
    assert result.fallback_used is False
    assert result.error is None
    
    return True


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("MCP工具管理器错误处理功能验证")
    print("="*60)
    
    tests = [
        ("工具不存在错误", test_tool_not_found),
        ("参数验证错误", test_parameter_validation),
        ("超时错误处理", test_timeout_error),
        ("连接错误处理", test_connection_error),
        ("一般错误处理", test_general_error),
        ("错误统计", test_error_statistics),
        ("成功调用", test_successful_call),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
