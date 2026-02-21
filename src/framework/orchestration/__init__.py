# -*- coding: utf-8 -*-
"""
框架层编排模块

提供通用的DAG编排和工具管理功能。
v3.0: Agent执行器已移至experimental/，仅保留DAG编排。

版本: v3.0.0
日期: 2026-02-22
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

# 策略选择器（仅DAG策略）
from .strategy_selector import (
    ExecutionStrategy,
    StrategyDecision,
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
    # 策略选择器
    "ExecutionStrategy",
    "StrategyDecision",
    # 缓存管理器
    "CacheManager",
    "CacheStatistics"
]
