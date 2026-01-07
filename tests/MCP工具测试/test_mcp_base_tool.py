"""
测试BaseMCPTool基类

验证：
1. 基类接口定义
2. 性能监控功能
3. 错误处理机制
"""

import pytest
import asyncio
from pydantic import BaseModel, Field
from typing import Dict, Any
from src.applications.fitness.mcp_tools.base_tool import BaseMCPTool, ToolMetadata
from src.applications.fitness.mcp_tools.exceptions import ToolValidationError


# 测试用的简单工具实现
class SimpleToolInput(BaseModel):
    """简单工具输入"""
    query: str = Field(..., description="查询文本")
    limit: int = Field(10, description="结果数量限制")


class SimpleToolOutput(BaseModel):
    """简单工具输出"""
    success: bool
    tool_name: str
    data: Dict[str, Any]


class SimpleMCPTool(BaseMCPTool):
    """简单的测试工具"""
    
    def get_name(self) -> str:
        return "simple_test_tool"
    
    def get_description(self) -> str:
        return "简单的测试工具"
    
    def get_category(self) -> str:
        return "utility"
    
    def get_input_schema(self) -> type[BaseModel]:
        return SimpleToolInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return SimpleToolOutput
    
    def get_complexity(self) -> str:
        return "simple"
    
    def get_estimated_duration(self) -> float:
        return 100.0
    
    def requires_user_profile(self) -> bool:
        return False
    
    def get_dependencies(self) -> list:
        return ["neo4j"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行简单逻辑"""
        return {
            "success": True,
            "tool_name": self.get_name(),
            "data": {
                "query": input_data["query"],
                "limit": input_data["limit"],
                "results": ["result1", "result2"]
            }
        }


class ErrorMCPTool(BaseMCPTool):
    """会抛出错误的测试工具"""
    
    def get_name(self) -> str:
        return "error_test_tool"
    
    def get_description(self) -> str:
        return "会抛出错误的测试工具"
    
    def get_category(self) -> str:
        return "utility"
    
    def get_input_schema(self) -> type[BaseModel]:
        return SimpleToolInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return SimpleToolOutput
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """抛出错误"""
        raise ValueError("测试错误")


@pytest.fixture
def mock_clients():
    """模拟客户端"""
    return {
        "neo4j_client": None,
        "qdrant_client": None,
        "three_layer_engine": None
    }


@pytest.fixture
def simple_tool(mock_clients):
    """创建简单工具实例"""
    return SimpleMCPTool(**mock_clients)


@pytest.fixture
def error_tool(mock_clients):
    """创建错误工具实例"""
    return ErrorMCPTool(**mock_clients)


class TestBaseMCPTool:
    """测试BaseMCPTool基类"""
    
    def test_get_metadata(self, simple_tool):
        """测试获取工具元数据"""
        metadata = simple_tool.get_metadata()
        
        assert isinstance(metadata, ToolMetadata)
        assert metadata.name == "simple_test_tool"
        assert metadata.description == "简单的测试工具"
        assert metadata.category == "utility"
        assert metadata.complexity == "simple"
        assert metadata.estimated_duration_ms == 100.0
        assert metadata.requires_user_profile is False
        assert "neo4j" in metadata.dependencies
    
    @pytest.mark.asyncio
    async def test_execute_with_monitoring_success(self, simple_tool):
        """测试成功执行并监控"""
        input_data = {
            "query": "测试查询",
            "limit": 5
        }
        
        result = await simple_tool.execute_with_monitoring(input_data)
        
        # 验证结果结构
        assert result["success"] is True
        assert result["tool_name"] == "simple_test_tool"
        assert "data" in result
        assert "metadata" in result
        
        # 验证数据
        assert result["data"]["query"] == "测试查询"
        assert result["data"]["limit"] == 5
        assert len(result["data"]["results"]) == 2
        
        # 验证元数据
        assert "execution_time_ms" in result["metadata"]
        assert "timestamp" in result["metadata"]
        assert result["metadata"]["tool_name"] == "simple_test_tool"
        assert result["metadata"]["execution_time_ms"] >= 0
    
    @pytest.mark.asyncio
    async def test_execute_with_monitoring_validation_error(self, simple_tool):
        """测试输入验证错误"""
        # 缺少必需参数
        input_data = {
            "limit": 5
            # 缺少 query 参数
        }
        
        result = await simple_tool.execute_with_monitoring(input_data)
        
        # 验证错误结果
        assert result["success"] is False
        assert result["tool_name"] == "simple_test_tool"
        assert "error" in result
        assert "metadata" in result
        
        # 验证错误信息
        assert result["error"]["code"] == "TOOL_EXECUTION_ERROR"
        assert "query" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_execute_with_monitoring_execution_error(self, error_tool):
        """测试执行错误"""
        input_data = {
            "query": "测试查询",
            "limit": 5
        }
        
        result = await error_tool.execute_with_monitoring(input_data)
        
        # 验证错误结果
        assert result["success"] is False
        assert result["tool_name"] == "error_test_tool"
        assert "error" in result
        
        # 验证错误信息
        assert result["error"]["code"] == "TOOL_EXECUTION_ERROR"
        assert "测试错误" in result["error"]["message"]
        assert result["error"]["type"] == "ValueError"
    
    @pytest.mark.asyncio
    async def test_execute_with_monitoring_performance(self, simple_tool):
        """测试性能监控"""
        input_data = {
            "query": "测试查询",
            "limit": 5
        }
        
        result = await simple_tool.execute_with_monitoring(input_data)
        
        # 验证性能指标
        assert "execution_time_ms" in result["metadata"]
        execution_time = result["metadata"]["execution_time_ms"]
        
        # 执行时间应该是合理的（小于1秒）
        assert 0 <= execution_time < 1000
    
    def test_default_methods(self, simple_tool):
        """测试默认方法"""
        # 测试默认复杂度
        assert simple_tool.get_complexity() == "simple"
        
        # 测试默认预估时间
        assert simple_tool.get_estimated_duration() == 100.0
        
        # 测试默认用户档案需求
        assert simple_tool.requires_user_profile() is False
        
        # 测试默认依赖
        assert "neo4j" in simple_tool.get_dependencies()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
