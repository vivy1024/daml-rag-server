"""
测试MCP工具管理器的错误处理功能

验证：
1. 工具不存在时返回失败结果
2. 参数验证失败时返回失败结果
3. 错误统计功能正常
4. 错误建议功能正常

更新日期: 2025-12-29
更新说明: 适配当前MCP工具管理器的实现行为
- 当前实现返回MCPToolCallResult对象而不是抛出异常
- 当前实现使用重试机制
- Python内置工具需要python_tool_registry初始化
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.framework.clients.mcp_tool_manager import (
    MCPToolManager,
    MCPToolCallResult,
    create_mcp_tool_manager
)


class TestMCPErrorHandling:
    """测试MCP错误处理"""

    @pytest.fixture
    def tool_manager(self):
        """创建工具管理器实例（不带Python工具注册表）"""
        return create_mcp_tool_manager()

    @pytest.mark.asyncio
    async def test_tool_not_found_returns_failure(self, tool_manager):
        """测试工具不存在时返回失败结果"""
        result = await tool_manager.call_tool(
            task_name="non_existent_tool",
            parameters={}
        )
        
        # 验证返回失败结果
        assert result.success is False
        assert result.error is not None
        assert "non_existent_tool" in result.error
        assert result.error_type == "MCPToolNotFoundError"

    @pytest.mark.asyncio
    async def test_parameter_validation_returns_failure(self, tool_manager):
        """测试参数验证失败时返回失败结果"""
        result = await tool_manager.call_tool(
            task_name="contraindications_checker",
            parameters={}  # 缺少必需参数
        )
        
        # 验证返回失败结果
        assert result.success is False
        assert result.error is not None
        # 可能是参数验证失败或Python工具注册表未初始化
        assert "参数验证失败" in result.error or "Python工具注册表未初始化" in result.error

    @pytest.mark.asyncio
    async def test_python_tool_registry_not_initialized(self, tool_manager):
        """测试Python工具注册表未初始化时返回失败结果"""
        result = await tool_manager.call_tool(
            task_name="contraindications_checker",
            parameters={
                "user_id": "test",
                "exercise_ids": []
            }
        )
        
        # 验证返回失败结果（因为Python工具注册表未初始化）
        assert result.success is False
        assert result.error is not None
        assert "Python工具注册表未初始化" in result.error

    def test_error_statistics_initial_state(self, tool_manager):
        """测试错误统计初始状态"""
        stats = tool_manager.get_error_statistics()
        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0

    @pytest.mark.asyncio
    async def test_error_statistics_after_failures(self, tool_manager):
        """测试失败后的错误统计"""
        # 执行一次失败的调用
        await tool_manager.call_tool(
            task_name="non_existent_tool",
            parameters={}
        )
        
        # 验证统计（注意：重试机制会导致多次调用）
        stats = tool_manager.get_error_statistics()
        assert stats["total_calls"] > 0
        assert stats["failed_calls"] > 0

    def test_get_error_suggestion_timeout(self, tool_manager):
        """测试超时错误建议"""
        suggestion = tool_manager._get_error_suggestion("timeout")
        assert suggestion is not None
        assert len(suggestion) > 0

    def test_get_error_suggestion_connection(self, tool_manager):
        """测试连接错误建议"""
        suggestion = tool_manager._get_error_suggestion("connection")
        assert suggestion is not None
        assert len(suggestion) > 0

    def test_get_error_suggestion_general(self, tool_manager):
        """测试一般错误建议"""
        suggestion = tool_manager._get_error_suggestion("general")
        assert suggestion is not None
        assert len(suggestion) > 0

    def test_tool_mapping_loaded(self, tool_manager):
        """测试工具映射已加载"""
        assert tool_manager.tool_mapping is not None
        assert len(tool_manager.tool_mapping) > 0
        # 验证一些已知的工具存在
        assert "contraindications_checker" in tool_manager.tool_mapping
        assert "intelligent_exercise_selector" in tool_manager.tool_mapping
        assert "tdee_calculator" in tool_manager.tool_mapping

    @pytest.mark.asyncio
    async def test_result_structure(self, tool_manager):
        """测试结果结构"""
        result = await tool_manager.call_tool(
            task_name="non_existent_tool",
            parameters={}
        )
        
        # 验证结果是MCPToolCallResult类型
        assert isinstance(result, MCPToolCallResult)
        # 验证必需字段存在
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        assert hasattr(result, 'error')
        assert hasattr(result, 'tool_name')
        assert hasattr(result, 'execution_time_ms')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'fallback_used')
        assert hasattr(result, 'error_type')
        assert hasattr(result, 'stack_trace')

    @pytest.mark.asyncio
    async def test_stack_trace_on_error(self, tool_manager):
        """测试错误时包含堆栈跟踪"""
        result = await tool_manager.call_tool(
            task_name="non_existent_tool",
            parameters={}
        )
        
        # 验证堆栈跟踪存在
        assert result.stack_trace is not None
        assert len(result.stack_trace) > 0


class TestMCPToolManagerWithMock:
    """使用Mock测试MCP工具管理器"""

    @pytest.fixture
    def mock_python_registry(self):
        """创建Mock的Python工具注册表"""
        registry = AsyncMock()
        return registry

    @pytest.fixture
    def tool_manager_with_registry(self, mock_python_registry):
        """创建带有Mock注册表的工具管理器"""
        manager = create_mcp_tool_manager()
        manager.python_tool_registry = mock_python_registry
        return manager

    @pytest.mark.asyncio
    async def test_successful_call_with_mock_registry(self, tool_manager_with_registry, mock_python_registry):
        """测试使用Mock注册表的成功调用"""
        # 设置Mock返回值
        mock_python_registry.call_tool.return_value = {
            "success": True,
            "data": {"result": "test_result"},
            "tool_name": "contraindications_checker"
        }
        
        result = await tool_manager_with_registry.call_tool(
            task_name="contraindications_checker",
            parameters={
                "user_id": "test",
                "exercise_ids": []
            }
        )
        
        # 验证成功结果
        assert result.success is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_failed_call_with_mock_registry(self, tool_manager_with_registry, mock_python_registry):
        """测试使用Mock注册表的失败调用"""
        # 设置Mock抛出异常
        mock_python_registry.call_tool.side_effect = Exception("测试错误")
        
        result = await tool_manager_with_registry.call_tool(
            task_name="contraindications_checker",
            parameters={
                "user_id": "test",
                "exercise_ids": []
            }
        )
        
        # 验证失败结果
        assert result.success is False
        assert result.error is not None
        assert "测试错误" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
