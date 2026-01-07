"""
测试MCP工具管理器的错误处理功能

验证：
1. 捕获MCP调用异常
2. 记录详细错误信息（工具名、参数、堆栈）
3. 提供降级方案
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.framework.clients.mcp_tool_manager import (
    MCPToolManager,
    MCPToolNotFoundError,
    MCPToolCallError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPParameterError,
    create_mcp_tool_manager
)


class TestMCPErrorHandling:
    """测试MCP错误处理"""

    @pytest.fixture
    def tool_manager(self):
        """创建工具管理器实例（带mock的Python工具注册表）"""
        mock_registry = MagicMock()
        mock_registry.call_tool = AsyncMock(return_value={"success": True, "data": {}})
        manager = MCPToolManager(python_tool_registry=mock_registry)
        return manager

    @pytest.mark.asyncio
    async def test_tool_not_found_error(self, tool_manager):
        """测试工具不存在错误 - 返回失败结果而不是抛出异常"""
        result = await tool_manager.call_tool(
            task_name="non_existent_tool",
            parameters={}
        )
        
        # 由于有重试机制，工具不存在会返回失败结果
        assert result.success is False
        assert "non_existent_tool" in result.error or "未知" in result.error

    @pytest.mark.asyncio
    async def test_parameter_validation_error(self, tool_manager):
        """测试参数验证错误 - 返回失败结果而不是抛出异常"""
        result = await tool_manager.call_tool(
            task_name="contraindications_checker",
            parameters={}  # 缺少必需参数
        )
        
        # 参数验证失败会返回失败结果
        assert result.success is False
        assert "验证" in result.error or "参数" in result.error

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, tool_manager):
        """测试超时错误处理"""
        # 设置mock抛出超时错误
        tool_manager.python_tool_registry.call_tool.side_effect = asyncio.TimeoutError("调用超时")
        
        result = await tool_manager.call_tool(
            task_name="contraindications_checker",
            parameters={
                "user_id": "test_user",
                "exercise_ids": ["ex1", "ex2"]
            }
        )
        
        # 验证返回降级结果
        assert result.success is False
        assert result.fallback_used is True
        assert result.error_type == "MCPTimeoutError"
        assert result.stack_trace is not None

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, tool_manager):
        """测试连接错误处理"""
        # 设置mock抛出连接错误
        tool_manager.python_tool_registry.call_tool.side_effect = ConnectionError("连接失败")
        
        result = await tool_manager.call_tool(
            task_name="contraindications_checker",
            parameters={
                "user_id": "test_user",
                "exercise_ids": ["ex1", "ex2"]
            }
        )
        
        # 验证返回降级结果
        assert result.success is False
        assert result.fallback_used is True
        assert result.error_type == "MCPConnectionError"
        assert result.stack_trace is not None

    @pytest.mark.asyncio
    async def test_general_error_handling(self, tool_manager):
        """测试一般错误处理"""
        # 设置mock抛出一般异常
        tool_manager.python_tool_registry.call_tool.side_effect = ValueError("无效的参数值")
        
        result = await tool_manager.call_tool(
            task_name="contraindications_checker",
            parameters={
                "user_id": "test_user",
                "exercise_ids": ["ex1", "ex2"]
            }
        )
        
        # 验证返回降级结果
        assert result.success is False
        assert result.fallback_used is True
        assert result.error_type == "ValueError"
        assert result.stack_trace is not None
        assert "无效的参数值" in result.error

    @pytest.mark.asyncio
    async def test_error_logging(self, tool_manager, caplog):
        """测试错误日志记录"""
        tool_manager.python_tool_registry.call_tool.side_effect = Exception("测试错误")
        
        import logging
        with caplog.at_level(logging.ERROR):
            result = await tool_manager.call_tool(
                task_name="contraindications_checker",
                parameters={
                    "user_id": "test_user",
                    "exercise_ids": ["ex1", "ex2"]
                }
            )
        
        # 验证日志包含详细信息
        log_text = caplog.text
        assert "MCP工具调用失败" in log_text or "contraindications_checker" in log_text

    @pytest.mark.asyncio
    async def test_fallback_result_structure(self, tool_manager):
        """测试降级结果结构"""
        tool_manager.python_tool_registry.call_tool.side_effect = Exception("测试错误")
        
        result = await tool_manager.call_tool(
            task_name="contraindications_checker",
            parameters={
                "user_id": "test_user",
                "exercise_ids": ["ex1", "ex2"]
            }
        )
        
        # 验证降级结果包含所有必需字段
        assert result.data is not None
        assert "fallback" in result.data
        assert result.data["fallback"] is True

    def test_error_statistics(self, tool_manager):
        """测试错误统计功能"""
        # 初始状态
        stats = tool_manager.get_error_statistics()
        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0

    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, tool_manager):
        """测试错误统计跟踪"""
        tool_manager.python_tool_registry.call_tool.side_effect = Exception("测试错误")
        
        # 执行多次调用
        for _ in range(3):
            await tool_manager.call_tool(
                task_name="contraindications_checker",
                parameters={
                    "user_id": "test_user",
                    "exercise_ids": ["ex1", "ex2"]
                }
            )
        
        # 验证统计 - 由于有重试机制，实际调用次数会更多
        stats = tool_manager.get_error_statistics()
        assert stats["total_calls"] >= 3
        assert stats["failed_calls"] >= 3

    @pytest.mark.asyncio
    async def test_successful_call_no_fallback(self, tool_manager):
        """测试成功调用不使用降级"""
        # 设置mock返回成功结果
        tool_manager.python_tool_registry.call_tool.return_value = {
            "success": True,
            "data": {"result": "success"}
        }
        tool_manager.python_tool_registry.call_tool.side_effect = None
        
        result = await tool_manager.call_tool(
            task_name="contraindications_checker",
            parameters={
                "user_id": "test_user",
                "exercise_ids": ["ex1", "ex2"]
            }
        )
        
        # 验证成功结果
        assert result.success is True
        assert result.fallback_used is False
        assert result.error is None
        assert result.error_type is None

    def test_get_error_suggestion(self, tool_manager):
        """测试错误建议"""
        # 测试不同错误类别的建议
        timeout_suggestion = tool_manager._get_error_suggestion("timeout")
        assert timeout_suggestion is not None
        
        connection_suggestion = tool_manager._get_error_suggestion("connection")
        assert connection_suggestion is not None
        
        general_suggestion = tool_manager._get_error_suggestion("general")
        assert general_suggestion is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
