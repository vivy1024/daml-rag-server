"""
测试MCPToolRegistry工具注册表

验证：
1. 工具注册和验证
2. 工具查询和过滤
3. 工具调用和监控
4. 性能统计
"""

import pytest
import asyncio
from pydantic import BaseModel, Field
from typing import Dict, Any
from src.applications.fitness.mcp_tools.registry import MCPToolRegistry
from src.applications.fitness.mcp_tools.base_tool import BaseMCPTool


# 测试用的工具实现
class TestToolInput(BaseModel):
    query: str = Field(..., description="查询文本")


class TestToolOutput(BaseModel):
    success: bool
    tool_name: str
    data: Dict[str, Any]


class ExerciseTool(BaseMCPTool):
    """动作工具"""
    
    def get_name(self) -> str:
        return "exercise_tool"
    
    def get_description(self) -> str:
        return "动作工具"
    
    def get_category(self) -> str:
        return "exercise"
    
    def get_input_schema(self) -> type[BaseModel]:
        return TestToolInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return TestToolOutput
    
    def get_complexity(self) -> str:
        return "simple"
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "tool_name": self.get_name(),
            "data": {"result": "exercise_result"}
        }


class TrainingTool(BaseMCPTool):
    """训练工具"""
    
    def get_name(self) -> str:
        return "training_tool"
    
    def get_description(self) -> str:
        return "训练工具"
    
    def get_category(self) -> str:
        return "training"
    
    def get_input_schema(self) -> type[BaseModel]:
        return TestToolInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return TestToolOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "tool_name": self.get_name(),
            "data": {"result": "training_result"}
        }


@pytest.fixture
def mock_clients():
    """模拟客户端"""
    return {
        "neo4j_client": None,
        "qdrant_client": None,
        "three_layer_engine": None
    }


@pytest.fixture
def registry():
    """创建注册表实例"""
    return MCPToolRegistry()


@pytest.fixture
def exercise_tool(mock_clients):
    """创建动作工具"""
    return ExerciseTool(**mock_clients)


@pytest.fixture
def training_tool(mock_clients):
    """创建训练工具"""
    return TrainingTool(**mock_clients)


class TestMCPToolRegistry:
    """测试工具注册表"""
    
    def test_register_tool_success(self, registry, exercise_tool):
        """测试成功注册工具"""
        registry.register_tool(exercise_tool)
        
        # 验证工具已注册
        assert registry.get_tool_count() == 1
        assert registry.get_tool("exercise_tool") is not None
        assert registry.get_metadata("exercise_tool") is not None
    
    def test_register_tool_duplicate(self, registry, exercise_tool):
        """测试重复注册工具"""
        registry.register_tool(exercise_tool)
        
        # 尝试重复注册
        with pytest.raises(ValueError, match="已注册"):
            registry.register_tool(exercise_tool)
    
    def test_register_tool_invalid_type(self, registry):
        """测试注册无效类型"""
        # 尝试注册非BaseMCPTool对象
        with pytest.raises(ValueError, match="必须继承BaseMCPTool"):
            registry.register_tool("not_a_tool")
    
    def test_get_tool(self, registry, exercise_tool):
        """测试获取工具"""
        registry.register_tool(exercise_tool)
        
        # 获取存在的工具
        tool = registry.get_tool("exercise_tool")
        assert tool is not None
        assert tool.get_name() == "exercise_tool"
        
        # 获取不存在的工具
        tool = registry.get_tool("nonexistent_tool")
        assert tool is None
    
    def test_get_metadata(self, registry, exercise_tool):
        """测试获取元数据"""
        registry.register_tool(exercise_tool)
        
        metadata = registry.get_metadata("exercise_tool")
        assert metadata is not None
        assert metadata.name == "exercise_tool"
        assert metadata.category == "exercise"
        assert metadata.complexity == "simple"
    
    def test_list_tools_all(self, registry, exercise_tool, training_tool):
        """测试列出所有工具"""
        registry.register_tool(exercise_tool)
        registry.register_tool(training_tool)
        
        tools = registry.list_tools()
        assert len(tools) == 2
    
    def test_list_tools_by_category(self, registry, exercise_tool, training_tool):
        """测试按分类过滤工具"""
        registry.register_tool(exercise_tool)
        registry.register_tool(training_tool)
        
        # 过滤exercise分类
        exercise_tools = registry.list_tools(category="exercise")
        assert len(exercise_tools) == 1
        assert exercise_tools[0].name == "exercise_tool"
        
        # 过滤training分类
        training_tools = registry.list_tools(category="training")
        assert len(training_tools) == 1
        assert training_tools[0].name == "training_tool"
    
    def test_list_tools_by_complexity(self, registry, exercise_tool, training_tool):
        """测试按复杂度过滤工具"""
        registry.register_tool(exercise_tool)
        registry.register_tool(training_tool)
        
        # 过滤simple复杂度
        simple_tools = registry.list_tools(complexity="simple")
        assert len(simple_tools) == 1
        assert simple_tools[0].name == "exercise_tool"
        
        # 过滤complex复杂度
        complex_tools = registry.list_tools(complexity="complex")
        assert len(complex_tools) == 1
        assert complex_tools[0].name == "training_tool"
    
    def test_list_tool_names(self, registry, exercise_tool, training_tool):
        """测试列出工具名称"""
        registry.register_tool(exercise_tool)
        registry.register_tool(training_tool)
        
        names = registry.list_tool_names()
        assert len(names) == 2
        assert "exercise_tool" in names
        assert "training_tool" in names
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, registry, exercise_tool):
        """测试成功调用工具"""
        registry.register_tool(exercise_tool)
        
        input_data = {"query": "测试查询"}
        result = await registry.call_tool("exercise_tool", input_data)
        
        # 验证结果
        assert result["success"] is True
        assert result["tool_name"] == "exercise_tool"
        assert result["data"]["result"] == "exercise_result"
    
    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, registry):
        """测试调用不存在的工具"""
        with pytest.raises(ValueError, match="工具不存在"):
            await registry.call_tool("nonexistent_tool", {})
    
    @pytest.mark.asyncio
    async def test_performance_stats(self, registry, exercise_tool):
        """测试性能统计"""
        registry.register_tool(exercise_tool)
        
        # 初始统计
        stats = registry.get_performance_stats("exercise_tool")
        assert stats["exercise_tool"]["total_calls"] == 0
        assert stats["exercise_tool"]["success_count"] == 0
        
        # 调用工具
        await registry.call_tool("exercise_tool", {"query": "测试"})
        
        # 验证统计更新
        stats = registry.get_performance_stats("exercise_tool")
        assert stats["exercise_tool"]["total_calls"] == 1
        assert stats["exercise_tool"]["success_count"] == 1
        assert stats["exercise_tool"]["avg_duration_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_performance_stats_multiple_calls(self, registry, exercise_tool):
        """测试多次调用的性能统计"""
        registry.register_tool(exercise_tool)
        
        # 调用3次
        for i in range(3):
            await registry.call_tool("exercise_tool", {"query": f"测试{i}"})
        
        # 验证统计
        stats = registry.get_performance_stats("exercise_tool")
        assert stats["exercise_tool"]["total_calls"] == 3
        assert stats["exercise_tool"]["success_count"] == 3
        assert stats["exercise_tool"]["error_count"] == 0
    
    def test_get_categories(self, registry, exercise_tool, training_tool):
        """测试获取所有分类"""
        registry.register_tool(exercise_tool)
        registry.register_tool(training_tool)
        
        categories = registry.get_categories()
        assert len(categories) == 2
        assert "exercise" in categories
        assert "training" in categories
    
    def test_get_tools_by_category(self, registry, exercise_tool, training_tool):
        """测试按分类分组工具"""
        registry.register_tool(exercise_tool)
        registry.register_tool(training_tool)
        
        grouped = registry.get_tools_by_category()
        assert len(grouped) == 2
        assert "exercise_tool" in grouped["exercise"]
        assert "training_tool" in grouped["training"]
    
    def test_reset_stats(self, registry, exercise_tool):
        """测试重置统计"""
        registry.register_tool(exercise_tool)
        
        # 修改统计
        registry.performance_stats["exercise_tool"]["total_calls"] = 10
        registry.performance_stats["exercise_tool"]["success_count"] = 8
        
        # 重置统计
        registry.reset_stats("exercise_tool")
        
        # 验证已重置
        stats = registry.get_performance_stats("exercise_tool")
        assert stats["exercise_tool"]["total_calls"] == 0
        assert stats["exercise_tool"]["success_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
