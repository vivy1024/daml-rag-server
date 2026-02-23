"""
MCPToolRegistry工具注册表

管理所有MCP工具的注册、查询和调用
"""

from typing import Dict, List, Optional, Any
from .base_tool import BaseMCPTool, ToolMetadata
from src.framework.exceptions import ToolExecutionError, ValidationError
import logging

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """
    MCP工具注册表
    
    功能：
    1. 工具注册和验证
    2. 工具查询和过滤
    3. 工具调用和监控
    4. 性能统计
    """
    
    def __init__(self):
        self.tools: Dict[str, BaseMCPTool] = {}
        self.metadata: Dict[str, ToolMetadata] = {}
        self.performance_stats: Dict[str, Dict[str, Any]] = {}
        self.logger = logger
    
    def register_tool(self, tool: BaseMCPTool) -> None:
        """
        注册工具
        
        Args:
            tool: BaseMCPTool实例
        
        Raises:
            ValueError: 如果工具已注册或不符合接口规范
        """
        # 验证工具接口（必须先检查类型）
        if not isinstance(tool, BaseMCPTool):
            raise ValueError(f"工具必须继承BaseMCPTool")
        
        tool_name = tool.get_name()
        
        # 检查重复注册
        if tool_name in self.tools:
            raise ValueError(f"工具 {tool_name} 已注册")
        
        # 注册工具
        self.tools[tool_name] = tool
        self.metadata[tool_name] = tool.get_metadata()
        self.performance_stats[tool_name] = {
            "total_calls": 0,
            "success_count": 0,
            "error_count": 0,
            "total_duration_ms": 0.0,
            "avg_duration_ms": 0.0,
            "last_call_timestamp": None,
            "last_error": None
        }
        
        self.logger.info(
            f"✅ 注册MCP工具: {tool_name} "
            f"(分类: {tool.get_category()}, "
            f"复杂度: {tool.get_complexity()})"
        )
    
    def get_tool(self, tool_name: str) -> Optional[BaseMCPTool]:
        """
        获取工具实例
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具实例，如果不存在返回None
        """
        return self.tools.get(tool_name)
    
    def get_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """
        获取工具元数据
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具元数据，如果不存在返回None
        """
        return self.metadata.get(tool_name)
    
    def list_tools(
        self,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        requires_user_profile: Optional[bool] = None
    ) -> List[ToolMetadata]:
        """
        列出工具
        
        Args:
            category: 按分类过滤（可选）
            complexity: 按复杂度过滤（可选）
            requires_user_profile: 按是否需要用户档案过滤（可选）
        
        Returns:
            工具元数据列表
        """
        tools = list(self.metadata.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        if complexity:
            tools = [t for t in tools if t.complexity == complexity]
        
        if requires_user_profile is not None:
            tools = [t for t in tools if t.requires_user_profile == requires_user_profile]
        
        return tools
    
    def list_tool_names(
        self,
        category: Optional[str] = None,
        complexity: Optional[str] = None
    ) -> List[str]:
        """
        列出工具名称
        
        Args:
            category: 按分类过滤（可选）
            complexity: 按复杂度过滤（可选）
        
        Returns:
            工具名称列表
        """
        tools = self.list_tools(category=category, complexity=complexity)
        return [t.name for t in tools]
    
    async def call_tool(
        self,
        tool_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            input_data: 输入数据
        
        Returns:
            工具执行结果
        
        Raises:
            ValueError: 如果工具不存在
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"工具不存在: {tool_name}")
        
        # 更新统计
        self.performance_stats[tool_name]["total_calls"] += 1
        
        # 执行工具
        result = await tool.execute_with_monitoring(input_data)
        
        # 更新性能统计
        from datetime import datetime
        self.performance_stats[tool_name]["last_call_timestamp"] = datetime.now().isoformat()
        
        if result.get("success"):
            self.performance_stats[tool_name]["success_count"] += 1
        else:
            self.performance_stats[tool_name]["error_count"] += 1
            self.performance_stats[tool_name]["last_error"] = result.get("error", {})
        
        duration = result.get("metadata", {}).get("execution_time_ms", 0)
        stats = self.performance_stats[tool_name]
        stats["total_duration_ms"] += duration
        stats["avg_duration_ms"] = (
            stats["total_duration_ms"] / stats["total_calls"]
        )
        
        return result
    
    def get_performance_stats(
        self,
        tool_name: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        获取性能统计
        
        Args:
            tool_name: 工具名称（可选），如果不指定则返回所有工具的统计
        
        Returns:
            性能统计字典
        """
        if tool_name:
            return {tool_name: self.performance_stats.get(tool_name, {})}
        return self.performance_stats
    
    def get_tool_count(self) -> int:
        """获取已注册工具数量"""
        return len(self.tools)
    
    def get_categories(self) -> List[str]:
        """获取所有工具分类"""
        return list(set(m.category for m in self.metadata.values()))
    
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """按分类分组工具"""
        result = {}
        for metadata in self.metadata.values():
            category = metadata.category
            if category not in result:
                result[category] = []
            result[category].append(metadata.name)
        return result
    
    def reset_stats(self, tool_name: Optional[str] = None) -> None:
        """
        重置性能统计
        
        Args:
            tool_name: 工具名称（可选），如果不指定则重置所有工具的统计
        """
        if tool_name:
            if tool_name in self.performance_stats:
                self.performance_stats[tool_name] = {
                    "total_calls": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "total_duration_ms": 0.0,
                    "avg_duration_ms": 0.0,
                    "last_call_timestamp": None,
                    "last_error": None
                }
        else:
            for tool_name in self.performance_stats:
                self.performance_stats[tool_name] = {
                    "total_calls": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "total_duration_ms": 0.0,
                    "avg_duration_ms": 0.0,
                    "last_call_timestamp": None,
                    "last_error": None
                }
