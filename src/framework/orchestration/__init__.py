# -*- coding: utf-8 -*-
"""
框架层编排模块

提供通用的DAG编排、Agent执行和工具管理功能。

版本: v1.2.0
日期: 2026-01-12
变更: 工具注册表已迁移到tools模块，此处重新导出以保持向后兼容
"""

# 工具注册表已迁移到tools模块，为了向后兼容，从tools模块重新导出
from ..tools.registry import (
    ToolRegistry,
    ToolConfig,
    ToolMetadata,  # ToolConfig的别名，保持向后兼容
    TaskPriority,
    ToolNotFoundError,
    ValidationError as ToolAlreadyRegisteredError  # 保持向后兼容
)

from .generic_dag_orchestrator import (
    GenericDAGOrchestrator,
    DAGTask,
    DAGTemplate,
    DAGExecutionResult,
    ExecutionLevel,
    TaskStatus
)

# CacheManager和CacheStatistics已迁移到mcp模块
# 为了向后兼容，从mcp模块重新导出
from ..mcp.cache_manager import (
    CacheManager,
    CacheStatistics
)

from .agent_executor import (
    AgentExecutor,
    AgentDecision,
    AgentAction,
    AgentExecutionResult,
    ExecutionStrategy,
    ToolCallRecord,
    SafetyCheckResult,
    LLMClientInterface,
    ToolInterface,
    create_agent_executor
)

__all__ = [
    # 工具注册表（从tools模块重新导出）
    "ToolRegistry",
    "ToolConfig",
    "ToolMetadata",  # ToolConfig的别名
    "TaskPriority",
    "ToolAlreadyRegisteredError",
    "ToolNotFoundError",
    # DAG编排器
    "GenericDAGOrchestrator",
    "DAGTask",
    "DAGTemplate",
    "DAGExecutionResult",
    "ExecutionLevel",
    "TaskStatus",
    # Agent执行器
    "AgentExecutor",
    "AgentDecision",
    "AgentAction",
    "AgentExecutionResult",
    "ExecutionStrategy",
    "ToolCallRecord",
    "SafetyCheckResult",
    "LLMClientInterface",
    "ToolInterface",
    "create_agent_executor",
    # 缓存管理器
    "CacheManager",
    "CacheStatistics"
]
