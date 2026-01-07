"""
测试MCP工具异常类型

验证：
1. 异常类型定义
2. 异常信息格式
3. 异常上下文传递
"""

import pytest
from src.applications.fitness.mcp_tools.exceptions import (
    ToolError,
    ToolValidationError,
    ToolTimeoutError,
    ToolConnectionError,
    ToolExecutionError
)


class TestToolExceptions:
    """测试工具异常类型"""
    
    def test_tool_error_basic(self):
        """测试基础异常"""
        error = ToolError(
            message="测试错误",
            tool_name="test_tool",
            context={"key": "value"}
        )
        
        assert str(error) == "测试错误"
        assert error.message == "测试错误"
        assert error.tool_name == "test_tool"
        assert error.context == {"key": "value"}
    
    def test_tool_error_to_dict(self):
        """测试异常转字典"""
        error = ToolError(
            message="测试错误",
            tool_name="test_tool",
            context={"key": "value"}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_type"] == "ToolError"
        assert error_dict["message"] == "测试错误"
        assert error_dict["tool_name"] == "test_tool"
        assert error_dict["context"] == {"key": "value"}
    
    def test_tool_validation_error(self):
        """测试验证错误"""
        error = ToolValidationError(
            message="参数验证失败",
            tool_name="test_tool",
            context={"field": "query", "reason": "required"}
        )
        
        assert isinstance(error, ToolError)
        assert error.message == "参数验证失败"
        assert error.context["field"] == "query"
    
    def test_tool_timeout_error(self):
        """测试超时错误"""
        error = ToolTimeoutError(
            message="执行超时",
            tool_name="test_tool",
            timeout_ms=5000.0,
            context={"operation": "database_query"}
        )
        
        assert isinstance(error, ToolError)
        assert error.timeout_ms == 5000.0
        
        error_dict = error.to_dict()
        assert error_dict["timeout_ms"] == 5000.0
    
    def test_tool_connection_error(self):
        """测试连接错误"""
        error = ToolConnectionError(
            message="无法连接到Neo4j",
            tool_name="test_tool",
            service="neo4j",
            context={"host": "localhost", "port": 7687}
        )
        
        assert isinstance(error, ToolError)
        assert error.service == "neo4j"
        
        error_dict = error.to_dict()
        assert error_dict["service"] == "neo4j"
    
    def test_tool_execution_error(self):
        """测试执行错误"""
        error = ToolExecutionError(
            message="Layer1检索失败",
            tool_name="test_tool",
            stage="layer1",
            context={"query": "测试查询"}
        )
        
        assert isinstance(error, ToolError)
        assert error.stage == "layer1"
        
        error_dict = error.to_dict()
        assert error_dict["stage"] == "layer1"
    
    def test_exception_inheritance(self):
        """测试异常继承关系"""
        # 所有异常都应该继承自ToolError
        assert issubclass(ToolValidationError, ToolError)
        assert issubclass(ToolTimeoutError, ToolError)
        assert issubclass(ToolConnectionError, ToolError)
        assert issubclass(ToolExecutionError, ToolError)
        
        # 所有异常都应该继承自Exception
        assert issubclass(ToolError, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
