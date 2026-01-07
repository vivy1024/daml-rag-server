# -*- coding: utf-8 -*-
"""
DAG模块 - 有向无环图编排系统

提供DAG任务编排、执行和结果汇总功能。

模块结构：
- models.py: 数据模型定义（TaskStatus, DAGTask, TaskResult, DAGExecutionResult）
- orchestrator.py: 核心编排逻辑（EnhancedDAGOrchestrator）
- task_executor.py: 任务执行器
- result_aggregator.py: 结果汇总器
- parameter_mapper.py: 参数映射器

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-28
"""

from .models import (
    TaskStatus,
    TaskPriority,
    ToolMetadata,
    DAGTask,
    ExecutionLevel,
    DAGExecutionResult,
    TaskResult,
)
from .orchestrator import EnhancedDAGOrchestrator
from .task_executor import TaskExecutor, TaskParamBuilder
from .result_aggregator import ResultAggregator
from .parameter_mapper import ParameterMapper

__all__ = [
    # 枚举类型
    "TaskStatus",
    "TaskPriority",
    # 数据类
    "ToolMetadata",
    "DAGTask",
    "ExecutionLevel",
    "DAGExecutionResult",
    "TaskResult",
    # 核心类
    "EnhancedDAGOrchestrator",
    "TaskExecutor",
    "TaskParamBuilder",
    "ResultAggregator",
    "ParameterMapper",
]
