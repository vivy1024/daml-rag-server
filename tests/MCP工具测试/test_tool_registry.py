# -*- coding: utf-8 -*-
"""
工具注册表单元测试

测试框架层ToolRegistry的功能。

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-14
"""

import pytest
from src.framework.orchestration import (
    ToolRegistry,
    ToolMetadata,
    TaskPriority,
    ToolAlreadyRegisteredError,
    ToolNotFoundError
)


class TestToolRegistry:
    """测试工具注册表"""
    
    def test_registry_initialization(self):
        """测试注册表初始化"""
        registry = ToolRegistry()
        assert len(registry) == 0
        assert registry.get_tool_count() == 0
    
    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()
        
        metadata = ToolMetadata(
            name="test_tool",
            mcp_server="test-server",
            execution_time=1.0,
            category="test"
        )
        
        registry.register("test_tool", metadata)
        
        assert len(registry) == 1
        assert registry.has_tool("test_tool")
        assert registry.get_metadata("test_tool") == metadata
    
    def test_register_duplicate_tool(self):
        """测试注册重复工具"""
        registry = ToolRegistry()
        
        metadata = ToolMetadata(
            name="test_tool",
            mcp_server="test-server"
        )
        
        registry.register("test_tool", metadata)
        
        # 尝试注册重复工具应该抛出异常
        with pytest.raises(ToolAlreadyRegisteredError):
            registry.register("test_tool", metadata)
    
    def test_get_metadata_required(self):
        """测试获取必需的元数据"""
        registry = ToolRegistry()
        
        # 获取不存在的工具应该抛出异常
        with pytest.raises(ToolNotFoundError):
            registry.get_metadata_required("nonexistent_tool")
        
        # 注册工具后应该能获取
        metadata = ToolMetadata(name="test_tool", mcp_server="test-server")
        registry.register("test_tool", metadata)
        
        result = registry.get_metadata_required("test_tool")
        assert result == metadata
    
    def test_list_tools(self):
        """测试列出所有工具"""
        registry = ToolRegistry()
        
        # 注册多个工具
        for i in range(3):
            metadata = ToolMetadata(
                name=f"tool_{i}",
                mcp_server="test-server"
            )
            registry.register(f"tool_{i}", metadata)
        
        tools = registry.list_tools()
        assert len(tools) == 3
        assert "tool_0" in tools
        assert "tool_1" in tools
        assert "tool_2" in tools
    
    def test_list_tools_by_category(self):
        """测试按分类列出工具"""
        registry = ToolRegistry()
        
        # 注册不同分类的工具
        registry.register("tool_a", ToolMetadata(
            name="tool_a",
            mcp_server="server",
            category="training"
        ))
        registry.register("tool_b", ToolMetadata(
            name="tool_b",
            mcp_server="server",
            category="training"
        ))
        registry.register("tool_c", ToolMetadata(
            name="tool_c",
            mcp_server="server",
            category="nutrition"
        ))
        
        training_tools = registry.list_tools_by_category("training")
        assert len(training_tools) == 2
        assert "tool_a" in training_tools
        assert "tool_b" in training_tools
        
        nutrition_tools = registry.list_tools_by_category("nutrition")
        assert len(nutrition_tools) == 1
        assert "tool_c" in nutrition_tools
    
    def test_list_tools_by_mcp_server(self):
        """测试按MCP服务器列出工具"""
        registry = ToolRegistry()
        
        # 注册不同MCP服务器的工具
        registry.register("tool_a", ToolMetadata(
            name="tool_a",
            mcp_server="server-1"
        ))
        registry.register("tool_b", ToolMetadata(
            name="tool_b",
            mcp_server="server-1"
        ))
        registry.register("tool_c", ToolMetadata(
            name="tool_c",
            mcp_server="server-2"
        ))
        
        server1_tools = registry.list_tools_by_mcp_server("server-1")
        assert len(server1_tools) == 2
        
        server2_tools = registry.list_tools_by_mcp_server("server-2")
        assert len(server2_tools) == 1
    
    def test_unregister_tool(self):
        """测试注销工具"""
        registry = ToolRegistry()
        
        metadata = ToolMetadata(name="test_tool", mcp_server="test-server")
        registry.register("test_tool", metadata)
        
        assert registry.has_tool("test_tool")
        
        # 注销工具
        result = registry.unregister("test_tool")
        assert result is True
        assert not registry.has_tool("test_tool")
        
        # 注销不存在的工具
        result = registry.unregister("nonexistent_tool")
        assert result is False
    
    def test_update_metadata(self):
        """测试更新工具元数据"""
        registry = ToolRegistry()
        
        old_metadata = ToolMetadata(
            name="test_tool",
            mcp_server="test-server",
            execution_time=1.0
        )
        registry.register("test_tool", old_metadata)
        
        new_metadata = ToolMetadata(
            name="test_tool",
            mcp_server="test-server",
            execution_time=2.0
        )
        
        result = registry.update_metadata("test_tool", new_metadata)
        assert result is True
        
        updated = registry.get_metadata("test_tool")
        assert updated.execution_time == 2.0
    
    def test_batch_register(self):
        """测试批量注册"""
        registry = ToolRegistry()
        
        tools = {
            "tool_1": ToolMetadata(name="tool_1", mcp_server="server"),
            "tool_2": ToolMetadata(name="tool_2", mcp_server="server"),
            "tool_3": ToolMetadata(name="tool_3", mcp_server="server")
        }
        
        registry.register_batch(tools)
        
        assert len(registry) == 3
        assert registry.has_tool("tool_1")
        assert registry.has_tool("tool_2")
        assert registry.has_tool("tool_3")
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        registry = ToolRegistry()
        
        # 注册不同类型的工具
        registry.register("tool_1", ToolMetadata(
            name="tool_1",
            mcp_server="server-1",
            category="training",
            priority=TaskPriority.HIGH,
            cacheable=True,
            parallel_safe=True
        ))
        registry.register("tool_2", ToolMetadata(
            name="tool_2",
            mcp_server="server-2",
            category="nutrition",
            priority=TaskPriority.NORMAL,
            cacheable=False,
            parallel_safe=False
        ))
        
        stats = registry.get_statistics()
        
        assert stats["total_tools"] == 2
        assert "training" in stats["categories"]
        assert "nutrition" in stats["categories"]
        assert stats["cacheable_tools"] == 1
        assert stats["parallel_safe_tools"] == 1
    
    def test_clear_registry(self):
        """测试清空注册表"""
        registry = ToolRegistry()
        
        # 注册一些工具
        for i in range(3):
            registry.register(f"tool_{i}", ToolMetadata(
                name=f"tool_{i}",
                mcp_server="server"
            ))
        
        assert len(registry) == 3
        
        # 清空注册表
        registry.clear()
        
        assert len(registry) == 0
        assert registry.get_tool_count() == 0
    
    def test_contains_operator(self):
        """测试 in 操作符"""
        registry = ToolRegistry()
        
        metadata = ToolMetadata(name="test_tool", mcp_server="test-server")
        registry.register("test_tool", metadata)
        
        assert "test_tool" in registry
        assert "nonexistent_tool" not in registry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
