# -*- coding: utf-8 -*-
"""
框架层编排模块

提供通用的DAG编排、Agent执行和工具管理功能。

版本: v1.1.0
日期: 2026-01-11
"""

from .tool_registry import (
    ToolRegistry,
    ToolMetadata,
    TaskPriority,
    ToolAlreadyRegisteredError,
    ToolNotFoundError
)

from .generic_dag_orchestrator import (
    GenericDAGOrchestrator,
    DAGTask,
    DAGTemplate,
    DAGExecutionResult,
    ExecutionLevel,
    TaskStatus
)

from .cache_manager import (
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
    # 工具注册表
    "ToolRegistry",
    "ToolMetadata",
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
