# -*- coding: utf-8 -*-
"""
增强版DAG编排器 - 兼容层

⚠️ 此文件是向后兼容层，原始实现已迁移到 dag/ 模块。
新代码请直接使用 dag 模块。

原始文件已归档到: archive/enhanced_dag_orchestrator.py.bak

迁移说明:
- dag/models.py: 数据模型定义（TaskStatus, DAGTask, TaskResult, DAGExecutionResult）
- dag/orchestrator.py: 核心编排逻辑（EnhancedDAGOrchestrator）
- dag/task_executor.py: 任务执行器
- dag/result_aggregator.py: 结果汇总器
- dag/parameter_mapper.py: 参数映射器

版本: v4.0.0 (兼容层)
日期: 2025-12-28
"""

import logging

logger = logging.getLogger(__name__)

# 从新模块导入所有接口（向后兼容）
from .dag import (
    # 枚举类型
    TaskStatus,
    TaskPriority,
    
    # 数据类
    ToolMetadata,
    DAGTask,
    ExecutionLevel,
    DAGExecutionResult,
    TaskResult,
    
    # 核心类
    EnhancedDAGOrchestrator,
    TaskExecutor,
    TaskParamBuilder,
    ResultAggregator,
    ParameterMapper,
)

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
