# -*- coding: utf-8 -*-
"""
工具注册表 - 框架层通用组件

提供工具元数据的注册、查询、管理功能。
支持动态注册和查询工具元数据。

版本: v1.0.0
日期: 2025-12-14
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 1     # 关键任务
    HIGH = 2         # 高优先级
    NORMAL = 3       # 普通优先级
    LOW = 4          # 低优先级


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    mcp_server: str
    execution_time: float = 1.0  # 预估执行时间(秒)
    cacheable: bool = True
    cache_ttl: int = 300  # 缓存TTL(秒)
    parallel_safe: bool = True
    supports_concurrent: bool = False
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 3
    timeout: float = 30.0  # 超时时间(秒)
    description: str = ""  # 工具描述
    category: str = "general"  # 工具分类


class ToolAlreadyRegisteredError(Exception):
    """工具已注册错误"""
    pass


class ToolNotFoundError(Exception):
    """工具未找到错误"""
    pass


class ToolRegistry:
    """
    工具注册表（框架层）
    
    提供工具元数据的注册、查询、管理功能。
    支持多种查询方式：按名称、按分类、按MCP服务器等。
    """
    
    def __init__(self):
        """初始化工具注册表"""
        self._tools: Dict[str, ToolMetadata] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._mcp_server_index: Dict[str, List[str]] = {}
        logger.info("✅ 工具注册表初始化完成")
    
    def register(self, tool_name: str, metadata: ToolMetadata) -> None:
        """
        注册工具
        
        Args:
            tool_name: 工具名称
            metadata: 工具元数据
            
        Raises:
            ToolAlreadyRegisteredError: 工具已注册
        """
        if tool_name in self._tools:
            raise ToolAlreadyRegisteredError(f"工具已注册: {tool_name}")
        
        self._tools[tool_name] = metadata
        
        # 更新分类索引
        category = metadata.category
        if category not in self._category_index:
            self._category_index[category] = []
        self._category_index[category].append(tool_name)
        
        # 更新MCP服务器索引
        mcp_server = metadata.mcp_server
        if mcp_server not in self._mcp_server_index:
            self._mcp_server_index[mcp_server] = []
        self._mcp_server_index[mcp_server].append(tool_name)
        
        logger.debug(f"✅ 注册工具: {tool_name} (分类: {category}, MCP: {mcp_server})")
    
    def register_batch(self, tools: Dict[str, ToolMetadata]) -> None:
        """
        批量注册工具
        
        Args:
            tools: 工具字典 {tool_name: metadata}
        """
        for tool_name, metadata in tools.items():
            try:
                self.register(tool_name, metadata)
            except ToolAlreadyRegisteredError:
                logger.warning(f"⚠️ 工具已存在，跳过: {tool_name}")
        
        logger.info(f"✅ 批量注册完成，共 {len(tools)} 个工具")
    
    def get_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """
        获取工具元数据
        
        Args:
            tool_name: 工具名称
            
        Returns:
            ToolMetadata: 工具元数据，不存在返回None
        """
        return self._tools.get(tool_name)
    
    def get_metadata_required(self, tool_name: str) -> ToolMetadata:
        """
        获取工具元数据（必须存在）
        
        Args:
            tool_name: 工具名称
            
        Returns:
            ToolMetadata: 工具元数据
            
        Raises:
            ToolNotFoundError: 工具未找到
        """
        metadata = self._tools.get(tool_name)
        if metadata is None:
            raise ToolNotFoundError(f"工具未注册: {tool_name}")
        return metadata
    
    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具
        
        Returns:
            List[str]: 工具名称列表
        """
        return list(self._tools.keys())
    
    def list_tools_by_category(self, category: str) -> List[str]:
        """
        按分类列出工具
        
        Args:
            category: 工具分类
            
        Returns:
            List[str]: 工具名称列表
        """
        return self._category_index.get(category, [])
    
    def list_tools_by_mcp_server(self, mcp_server: str) -> List[str]:
        """
        按MCP服务器列出工具
        
        Args:
            mcp_server: MCP服务器名称
            
        Returns:
            List[str]: 工具名称列表
        """
        return self._mcp_server_index.get(mcp_server, [])
    
    def list_categories(self) -> List[str]:
        """
        列出所有工具分类
        
        Returns:
            List[str]: 分类列表
        """
        return list(self._category_index.keys())
    
    def list_mcp_servers(self) -> List[str]:
        """
        列出所有MCP服务器
        
        Returns:
            List[str]: MCP服务器列表
        """
        return list(self._mcp_server_index.keys())
    
    def unregister(self, tool_name: str) -> bool:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否成功注销
        """
        if tool_name not in self._tools:
            logger.warning(f"⚠️ 工具不存在，无法注销: {tool_name}")
            return False
        
        metadata = self._tools[tool_name]
        
        # 从主字典删除
        del self._tools[tool_name]
        
        # 从分类索引删除
        if metadata.category in self._category_index:
            self._category_index[metadata.category].remove(tool_name)
            if not self._category_index[metadata.category]:
                del self._category_index[metadata.category]
        
        # 从MCP服务器索引删除
        if metadata.mcp_server in self._mcp_server_index:
            self._mcp_server_index[metadata.mcp_server].remove(tool_name)
            if not self._mcp_server_index[metadata.mcp_server]:
                del self._mcp_server_index[metadata.mcp_server]
        
        logger.info(f"✅ 注销工具: {tool_name}")
        return True
    
    def update_metadata(self, tool_name: str, metadata: ToolMetadata) -> bool:
        """
        更新工具元数据
        
        Args:
            tool_name: 工具名称
            metadata: 新的工具元数据
            
        Returns:
            bool: 是否成功更新
        """
        if tool_name not in self._tools:
            logger.warning(f"⚠️ 工具不存在，无法更新: {tool_name}")
            return False
        
        # 先注销旧的
        self.unregister(tool_name)
        
        # 再注册新的
        try:
            self.register(tool_name, metadata)
            logger.info(f"✅ 更新工具元数据: {tool_name}")
            return True
        except ToolAlreadyRegisteredError:
            logger.error(f"❌ 更新失败: {tool_name}")
            return False
    
    def has_tool(self, tool_name: str) -> bool:
        """
        检查工具是否已注册
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否已注册
        """
        return tool_name in self._tools
    
    def get_tool_count(self) -> int:
        """
        获取已注册工具数量
        
        Returns:
            int: 工具数量
        """
        return len(self._tools)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取注册表统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            "total_tools": len(self._tools),
            "categories": {
                category: len(tools)
                for category, tools in self._category_index.items()
            },
            "mcp_servers": {
                server: len(tools)
                for server, tools in self._mcp_server_index.items()
            },
            "priority_distribution": self._get_priority_distribution(),
            "cacheable_tools": sum(1 for m in self._tools.values() if m.cacheable),
            "parallel_safe_tools": sum(1 for m in self._tools.values() if m.parallel_safe)
        }
    
    def _get_priority_distribution(self) -> Dict[str, int]:
        """获取优先级分布"""
        distribution = {
            "CRITICAL": 0,
            "HIGH": 0,
            "NORMAL": 0,
            "LOW": 0
        }
        
        for metadata in self._tools.values():
            distribution[metadata.priority.name] += 1
        
        return distribution
    
    def clear(self) -> None:
        """清空注册表"""
        self._tools.clear()
        self._category_index.clear()
        self._mcp_server_index.clear()
        logger.info("✅ 工具注册表已清空")
    
    def __len__(self) -> int:
        """返回工具数量"""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """支持 in 操作符"""
        return tool_name in self._tools
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"ToolRegistry(tools={len(self._tools)}, categories={len(self._category_index)}, mcp_servers={len(self._mcp_server_index)})"
