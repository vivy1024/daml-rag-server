"""
Tool Registry - Generic Tool Registration System

This module provides a domain-agnostic tool registry for managing
MCP tools and their configurations. It supports:
- Configuration-driven tool registration (no hardcoded tools)
- YAML/JSON configuration file loading
- Runtime tool registration and lookup
- Tool metadata management with indexing
- Task priority and parallel execution support (merged from orchestration/tool_registry.py)

Requirements: 1.1, 1.2, 1.3, 1.4, 1.6
Merged from: orchestration/tool_registry.py (v1.0.0)
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """
    任务优先级枚举（从orchestration/tool_registry.py合并）
    
    用于定义工具执行的优先级顺序。
    """
    CRITICAL = 1     # 关键任务，最高优先级
    HIGH = 2         # 高优先级
    NORMAL = 3       # 普通优先级（默认）
    LOW = 4          # 低优先级


# Define exception classes locally to avoid circular imports
class ToolRegistryError(Exception):
    """Base exception for tool registry errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, 
                 suggestion: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.suggestion = suggestion


class ToolNotFoundError(ToolRegistryError):
    """Exception raised when a tool is not found in the registry."""
    def __init__(self, message: str, tool_name: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None,
                 suggestion: Optional[str] = None):
        ctx = context or {}
        if tool_name:
            ctx["tool_name"] = tool_name
        super().__init__(message, context=ctx, suggestion=suggestion)
        self.tool_name = tool_name


class ConfigurationError(ToolRegistryError):
    """Exception raised for configuration errors."""
    pass


class ValidationError(ToolRegistryError):
    """Exception raised for validation errors."""
    def __init__(self, message: str, field: Optional[str] = None,
                 expected: Optional[Any] = None, received: Optional[Any] = None,
                 context: Optional[Dict[str, Any]] = None,
                 suggestion: Optional[str] = None):
        ctx = context or {}
        if field:
            ctx["field"] = field
        if expected is not None:
            ctx["expected"] = str(expected)
        if received is not None:
            ctx["received"] = str(received)
        super().__init__(message, context=ctx, suggestion=suggestion)
        self.field = field
        self.expected = expected
        self.received = received


# Try to import framework exceptions if available
try:
    from ..exceptions import (
        ToolNotFoundError as FrameworkToolNotFoundError,
        ConfigurationError as FrameworkConfigurationError,
        ValidationError as FrameworkValidationError,
    )
    ToolNotFoundError = FrameworkToolNotFoundError
    ConfigurationError = FrameworkConfigurationError
    ValidationError = FrameworkValidationError
except ImportError:
    pass


class ToolCategory(Enum):
    """Tool category enumeration (generic, domain-agnostic)."""
    DATA_RETRIEVAL = "data_retrieval"
    DATA_PROCESSING = "data_processing"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    VALIDATION = "validation"
    INTEGRATION = "integration"
    UTILITY = "utility"
    CUSTOM = "custom"


@dataclass
class ToolConfig:
    """
    Tool configuration data class.
    
    This class holds all metadata and configuration for a registered tool.
    It is domain-agnostic and can be used for any type of MCP tool.
    
    扩展字段（从orchestration/tool_registry.py合并）：
    - priority: 任务优先级（支持TaskPriority枚举或整数）
    - parallel_safe: 是否并行安全
    - execution_time: 预估执行时间（秒）
    - supports_concurrent: 是否支持并发执行
    - dependencies: 工具依赖列表
    - resource_requirements: 资源需求配置
    """
    name: str
    description: str = ""
    # 新字段名：server_name；旧字段名：mcp_server（兼容）
    server_name: str = ""
    mcp_server: Optional[str] = None
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    param_schema: Dict[str, str] = field(default_factory=dict)
    category: Union[ToolCategory, str] = ToolCategory.CUSTOM
    # 扩展字段：支持TaskPriority枚举或整数（向后兼容）
    priority: Union[TaskPriority, int] = TaskPriority.NORMAL
    # 新增字段（从orchestration/tool_registry.py合并）
    parallel_safe: bool = True  # 是否并行安全
    execution_time: float = 1.0  # 预估执行时间(秒)
    supports_concurrent: bool = False  # 是否支持并发执行
    dependencies: List[str] = field(default_factory=list)  # 工具依赖
    resource_requirements: Dict[str, Any] = field(default_factory=dict)  # 资源需求
    # 原有字段
    timeout: float = 30.0
    cacheable: bool = True
    cache_ttl: int = 300
    retry_count: int = 3
    executor: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize the configuration after initialization."""
        # 兼容旧字段名：mcp_server -> server_name
        if not self.server_name and self.mcp_server:
            self.server_name = self.mcp_server

        if not self.server_name:
            raise ValidationError(
                "Missing required field: server_name",
                field="server_name",
                suggestion="Provide 'server_name' (or legacy 'mcp_server') in the tool configuration",
            )

        if isinstance(self.category, str):
            # 允许领域自定义分类（例如 "training" / "nutrition"），仅在匹配到枚举时才转换
            try:
                self.category = ToolCategory(self.category)
            except ValueError:
                pass
        
        # 处理priority：支持整数或TaskPriority枚举
        if isinstance(self.priority, int) and not isinstance(self.priority, TaskPriority):
            # 将整数映射到TaskPriority（1-4映射到枚举，其他保持整数）
            priority_map = {1: TaskPriority.CRITICAL, 2: TaskPriority.HIGH, 
                          3: TaskPriority.NORMAL, 4: TaskPriority.LOW}
            self.priority = priority_map.get(self.priority, TaskPriority.NORMAL)
        
        if self.required_params is None:
            self.required_params = []
        if self.optional_params is None:
            self.optional_params = []
        if self.param_schema is None:
            self.param_schema = {}
        if self.metadata is None:
            self.metadata = {}
        if self.dependencies is None:
            self.dependencies = []
        if self.resource_requirements is None:
            self.resource_requirements = {}
    
    def get_priority_value(self) -> int:
        """获取优先级数值（用于排序）"""
        if isinstance(self.priority, TaskPriority):
            return self.priority.value
        return int(self.priority) if isinstance(self.priority, int) else 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        priority_value = self.priority.value if isinstance(self.priority, TaskPriority) else self.priority
        return {
            "name": self.name,
            "description": self.description,
            "server_name": self.server_name,
            "required_params": self.required_params,
            "optional_params": self.optional_params,
            "param_schema": self.param_schema,
            "category": self.category.value if isinstance(self.category, ToolCategory) else self.category,
            "priority": priority_value,
            "parallel_safe": self.parallel_safe,
            "execution_time": self.execution_time,
            "supports_concurrent": self.supports_concurrent,
            "dependencies": self.dependencies,
            "resource_requirements": self.resource_requirements,
            "timeout": self.timeout,
            "cacheable": self.cacheable,
            "cache_ttl": self.cache_ttl,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolConfig":
        """Create a ToolConfig from a dictionary."""
        if "name" not in data:
            raise ValidationError(
                "Missing required field: name",
                field="name",
                suggestion="Add 'name' to the tool configuration",
            )

        # 兼容旧字段名：mcp_server
        if "server_name" not in data and "mcp_server" in data:
            data = dict(data)
            data["server_name"] = data.get("mcp_server")

        if "server_name" not in data or not data.get("server_name"):
            raise ValidationError(
                "Missing required field: server_name",
                field="server_name",
                suggestion="Add 'server_name' (or legacy 'mcp_server') to the tool configuration",
            )
        
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            server_name=data["server_name"],
            required_params=data.get("required_params", []),
            optional_params=data.get("optional_params", []),
            param_schema=data.get("param_schema", {}),
            category=data.get("category", "custom"),
            priority=data.get("priority", TaskPriority.NORMAL),
            parallel_safe=data.get("parallel_safe", True),
            execution_time=data.get("execution_time", 1.0),
            supports_concurrent=data.get("supports_concurrent", False),
            dependencies=data.get("dependencies", []),
            resource_requirements=data.get("resource_requirements", {}),
            timeout=data.get("timeout", 30.0),
            cacheable=data.get("cacheable", True),
            cache_ttl=data.get("cache_ttl", 300),
            retry_count=data.get("retry_count", 3),
            metadata=data.get("metadata", {}),
        )


class ToolRegistry:
    """
    Generic Tool Registry for managing MCP tools.
    
    This registry provides a domain-agnostic way to register, lookup,
    and manage MCP tools.
    """
    
    def __init__(self):
        """Initialize an empty tool registry."""
        self._tools: Dict[str, ToolConfig] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._server_index: Dict[str, List[str]] = {}
        logger.debug("Tool registry initialized")
    
    def register_tool(self, name: str, config: ToolConfig) -> None:
        """Register a single tool with the registry."""
        if name in self._tools:
            raise ValidationError(
                f"Tool already registered: {name}",
                field="name",
                expected="unique tool name",
                received=name,
                suggestion=f"Use a different name or call unregister_tool('{name}') first"
            )
        
        self._tools[name] = config
        
        # Update category index
        category_key = config.category.value if isinstance(config.category, ToolCategory) else str(config.category)
        if category_key not in self._category_index:
            self._category_index[category_key] = []
        self._category_index[category_key].append(name)
        
        # Update server index
        server_name = config.server_name
        if server_name not in self._server_index:
            self._server_index[server_name] = []
        self._server_index[server_name].append(name)
        
        logger.debug(f"Registered tool: {name} (server: {server_name}, category: {category_key})")
    
    def get_tool(self, name: str) -> ToolConfig:
        """Retrieve a tool configuration by name."""
        if name not in self._tools:
            available = self.list_tools()
            raise ToolNotFoundError(
                f"Tool '{name}' not found in registry",
                tool_name=name,
                context={"available_tools": available[:10] if len(available) > 10 else available},
                suggestion=f"Register the tool first using registry.register_tool('{name}', config)"
            )
        return self._tools[name]
    
    def get_tool_optional(self, name: str) -> Optional[ToolConfig]:
        """Retrieve a tool configuration by name, returning None if not found."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def list_tools_by_category(self, category: Union[ToolCategory, str]) -> List[str]:
        """List tools by category."""
        category_key = category.value if isinstance(category, ToolCategory) else str(category)
        return self._category_index.get(category_key, []).copy()
    
    def list_tools_by_server(self, server_name: str) -> List[str]:
        """List tools by MCP server."""
        return self._server_index.get(server_name, []).copy()
    
    def list_categories(self) -> List[str]:
        """List all tool categories with registered tools."""
        return list(self._category_index.keys())
    
    def list_servers(self) -> List[str]:
        """List all MCP servers with registered tools."""
        return list(self._server_index.keys())
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def unregister_tool(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name not in self._tools:
            logger.warning(f"Tool not found for unregistration: {name}")
            return False
        
        config = self._tools[name]
        del self._tools[name]
        
        # Remove from category index
        category_key = config.category.value if isinstance(config.category, ToolCategory) else str(config.category)
        if category_key in self._category_index:
            self._category_index[category_key].remove(name)
            if not self._category_index[category_key]:
                del self._category_index[category_key]
        
        # Remove from server index
        if config.server_name in self._server_index:
            self._server_index[config.server_name].remove(name)
            if not self._server_index[config.server_name]:
                del self._server_index[config.server_name]
        
        logger.debug(f"Unregistered tool: {name}")
        return True

    # 向后兼容：旧接口名称
    def unregister(self, name: str) -> bool:
        return self.unregister_tool(name)
    
    def register_from_config(self, config_path: Union[str, Path]) -> int:
        """Register tools from a YAML or JSON configuration file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {config_path}",
                context={"path": str(config_path)},
                suggestion="Check that the file path is correct"
            )
        
        try:
            content = config_path.read_text(encoding="utf-8")
            
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                try:
                    import yaml
                    data = yaml.safe_load(content)
                except ImportError:
                    raise ConfigurationError(
                        "PyYAML is required to load YAML configuration files",
                        context={"path": str(config_path)},
                        suggestion="Install PyYAML: pip install pyyaml"
                    )
            elif config_path.suffix.lower() == ".json":
                data = json.loads(content)
            else:
                raise ConfigurationError(
                    f"Unsupported configuration file format: {config_path.suffix}",
                    context={"path": str(config_path), "suffix": config_path.suffix},
                    suggestion="Use .yaml, .yml, or .json file extension"
                )
            
            if isinstance(data, dict):
                tools_data = data.get("tools", [])
            elif isinstance(data, list):
                tools_data = data
            else:
                raise ConfigurationError(
                    "Invalid configuration format",
                    context={"path": str(config_path), "type": type(data).__name__},
                    suggestion="Configuration should be a dict with 'tools' key or a list of tools"
                )
            
            registered_count = 0
            for tool_data in tools_data:
                try:
                    config = ToolConfig.from_dict(tool_data)
                    self.register_tool(config.name, config)
                    registered_count += 1
                except ValidationError as e:
                    logger.warning(f"Skipping invalid tool configuration: {e}")
                except Exception as e:
                    logger.warning(f"Failed to register tool: {e}")
            
            logger.info(f"Registered {registered_count} tools from {config_path}")
            return registered_count
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Failed to parse JSON configuration: {e}",
                context={"path": str(config_path)},
                suggestion="Check the JSON syntax in the configuration file"
            )
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                context={"path": str(config_path)}
            )
    
    def register_batch(self, tools: Dict[str, ToolConfig]) -> int:
        """Register multiple tools at once."""
        registered_count = 0
        for name, config in tools.items():
            try:
                self.register_tool(name, config)
                registered_count += 1
            except ValidationError as e:
                logger.warning(f"Skipping tool {name}: {e}")
        
        logger.info(f"Batch registered {registered_count}/{len(tools)} tools")
        return registered_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self._tools),
            "categories": {cat: len(tools) for cat, tools in self._category_index.items()},
            "servers": {srv: len(tools) for srv, tools in self._server_index.items()},
            "priority_distribution": self.get_priority_distribution(),
            "cacheable_tools": sum(1 for t in self._tools.values() if t.cacheable),
            "parallel_safe_tools": sum(1 for t in self._tools.values() if t.parallel_safe),
        }
    
    def get_priority_distribution(self) -> Dict[str, int]:
        """
        获取优先级分布统计（从orchestration/tool_registry.py合并）
        
        Returns:
            Dict[str, int]: 各优先级的工具数量
        """
        distribution = {
            "CRITICAL": 0,
            "HIGH": 0,
            "NORMAL": 0,
            "LOW": 0
        }
        
        for config in self._tools.values():
            if isinstance(config.priority, TaskPriority):
                distribution[config.priority.name] += 1
            else:
                # 整数优先级映射
                priority_map = {1: "CRITICAL", 2: "HIGH", 3: "NORMAL", 4: "LOW"}
                priority_name = priority_map.get(config.priority, "NORMAL")
                distribution[priority_name] += 1
        
        return distribution
    
    def get_tools_by_priority(self, priority: Union[TaskPriority, int]) -> List[str]:
        """
        按优先级获取工具列表（从orchestration/tool_registry.py合并）
        
        Args:
            priority: 优先级（TaskPriority枚举或整数）
            
        Returns:
            List[str]: 工具名称列表
        """
        target_priority = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
        return [
            name for name, config in self._tools.items()
            if (isinstance(config.priority, TaskPriority) and config.priority == target_priority)
            or (isinstance(config.priority, int) and config.priority == target_priority.value)
        ]
    
    def get_parallel_safe_tools(self) -> List[str]:
        """
        获取所有并行安全的工具（从orchestration/tool_registry.py合并）
        
        Returns:
            List[str]: 并行安全的工具名称列表
        """
        return [name for name, config in self._tools.items() if config.parallel_safe]
    
    def get_concurrent_tools(self) -> List[str]:
        """
        获取支持并发执行的工具（从orchestration/tool_registry.py合并）
        
        Returns:
            List[str]: 支持并发的工具名称列表
        """
        return [name for name, config in self._tools.items() if config.supports_concurrent]
    
    def get_tool_execution_time(self, name: str) -> float:
        """
        获取工具的预估执行时间（从orchestration/tool_registry.py合并）
        
        Args:
            name: 工具名称
            
        Returns:
            float: 预估执行时间（秒）
        """
        config = self._tools.get(name)
        return config.execution_time if config else 1.0
    
    def get_tool_dependencies(self, name: str) -> List[str]:
        """
        获取工具的依赖列表（从orchestration/tool_registry.py合并）
        
        Args:
            name: 工具名称
            
        Returns:
            List[str]: 依赖的工具名称列表
        """
        config = self._tools.get(name)
        return config.dependencies if config else []
    
    # 兼容性别名方法（保持与orchestration/tool_registry.py的API兼容）
    def register(self, tool_name: str, metadata: ToolConfig) -> None:
        """
        注册工具（兼容orchestration/tool_registry.py的API）
        
        Args:
            tool_name: 工具名称
            metadata: 工具配置（ToolConfig）
        """
        self.register_tool(tool_name, metadata)
    
    def get_metadata(self, tool_name: str) -> Optional[ToolConfig]:
        """
        获取工具元数据（兼容orchestration/tool_registry.py的API）
        
        Args:
            tool_name: 工具名称
            
        Returns:
            ToolConfig: 工具配置，不存在返回None
        """
        return self.get_tool_optional(tool_name)
    
    def get_metadata_required(self, tool_name: str) -> ToolConfig:
        """
        获取工具元数据（必须存在，兼容orchestration/tool_registry.py的API）
        
        Args:
            tool_name: 工具名称
            
        Returns:
            ToolConfig: 工具配置
            
        Raises:
            ToolNotFoundError: 工具未找到
        """
        return self.get_tool(tool_name)
    
    def list_tools_by_mcp_server(self, mcp_server: str) -> List[str]:
        """
        按MCP服务器列出工具（兼容orchestration/tool_registry.py的API）
        
        Args:
            mcp_server: MCP服务器名称
            
        Returns:
            List[str]: 工具名称列表
        """
        return self.list_tools_by_server(mcp_server)
    
    def list_mcp_servers(self) -> List[str]:
        """
        列出所有MCP服务器（兼容orchestration/tool_registry.py的API）
        
        Returns:
            List[str]: MCP服务器列表
        """
        return self.list_servers()
    
    def get_tool_count(self) -> int:
        """
        获取已注册工具数量（兼容orchestration/tool_registry.py的API）
        
        Returns:
            int: 工具数量
        """
        return len(self._tools)
    
    def update_metadata(self, tool_name: str, metadata: ToolConfig) -> bool:
        """
        更新工具元数据（兼容orchestration/tool_registry.py的API）
        
        Args:
            tool_name: 工具名称
            metadata: 新的工具配置
            
        Returns:
            bool: 是否成功更新
        """
        if tool_name not in self._tools:
            logger.warning(f"Tool not found for update: {tool_name}")
            return False
        
        # 先注销旧的
        self.unregister_tool(tool_name)
        
        # 再注册新的
        try:
            self.register_tool(tool_name, metadata)
            logger.info(f"Updated tool metadata: {tool_name}")
            return True
        except ValidationError:
            logger.error(f"Failed to update tool: {tool_name}")
            return False
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._category_index.clear()
        self._server_index.clear()
        logger.debug("Tool registry cleared")
    
    def export_config(self) -> Dict[str, Any]:
        """Export all tool configurations as a dictionary."""
        return {
            "tools": [config.to_dict() for config in self._tools.values()]
        }
    
    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        """Support 'in' operator for checking tool existence."""
        return name in self._tools
    
    def __iter__(self):
        """Iterate over tool names."""
        return iter(self._tools)
    
    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"ToolRegistry(tools={len(self._tools)}, "
            f"categories={len(self._category_index)}, "
            f"servers={len(self._server_index)})"
        )


def create_tool_registry() -> ToolRegistry:
    """Create a new tool registry instance."""
    return ToolRegistry()


# 向后兼容别名（从orchestration/tool_registry.py迁移）
# ToolMetadata 是 ToolConfig 的别名，保持与旧代码的兼容性
ToolMetadata = ToolConfig

# 异常类别名（保持兼容性）
ToolAlreadyRegisteredError = ValidationError
