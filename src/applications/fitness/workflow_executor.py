# -*- coding: utf-8 -*-
"""
11步工作流程执行器 - 兼容层

⚠️ 此文件是向后兼容层，原始实现已迁移到 workflow/ 模块。
新代码请直接使用 workflow 模块。

原始文件已归档到: archive/workflow_executor.py.bak

迁移说明:
- workflow/state.py: 状态定义（WorkflowState TypedDict）
- workflow/nodes.py: 节点函数（每个步骤一个纯函数）
- workflow/edges.py: 边定义（条件路由逻辑）
- workflow/graph.py: 图构建（StateGraph 组装）
- workflow/executor.py: 同步执行器
- workflow/stream_executor.py: 流式执行器
- workflow/singletons.py: 单例管理

版本: v3.0.0 (兼容层)
日期: 2025-12-28
"""

import logging

logger = logging.getLogger(__name__)

# 从新模块导入所有接口（向后兼容）
from .workflow import (
    # 主要执行函数
    execute_eleven_step_workflow,
    execute_eleven_step_workflow_stream,
    execute_workflow,
    execute_workflow_stream,
    
    # 执行器类
    WorkflowExecutor,
    StreamWorkflowExecutor,
    
    # 状态相关
    WorkflowState,
    StateUpdate,
    WorkflowStep,
    ComplexityLevel,
    create_initial_state,
    serialize_state,
    deserialize_state,
    
    # 单例管理
    get_user_cache,
    get_membership_cache,
    get_workflow_monitor,
    get_dag_visualizer,
    get_cache_manager,
    get_connection_pool_manager,
    get_llm_degradation_manager,
    get_concurrency_limiter,
    get_performance_monitor,
    initialize_performance_components,
    reset_all_singletons,
)

# 导入后端异常类（保持向后兼容）
from .clients.backend_client import (
    BackendAPIError,
    BackendValidationError,
    BackendNotFoundError,
    BackendServerError
)

# 辅助函数（保持向后兼容）
def parse_validation_error(error):
    """解析验证错误（向后兼容）"""
    from .workflow.nodes import parse_validation_error as _parse
    return _parse(error)

def format_validation_error_log(request_id, user_id, error_details):
    """格式化验证错误日志（向后兼容）"""
    from .workflow.nodes import format_validation_error_log as _format
    return _format(request_id, user_id, error_details)

__all__ = [
    # 主要执行函数
    "execute_eleven_step_workflow",
    "execute_eleven_step_workflow_stream",
    "execute_workflow",
    "execute_workflow_stream",
    
    # 执行器类
    "WorkflowExecutor",
    "StreamWorkflowExecutor",
    
    # 状态相关
    "WorkflowState",
    "StateUpdate",
    "WorkflowStep",
    "ComplexityLevel",
    "create_initial_state",
    "serialize_state",
    "deserialize_state",
    
    # 单例管理
    "get_user_cache",
    "get_membership_cache",
    "get_workflow_monitor",
    "get_dag_visualizer",
    "get_cache_manager",
    "get_connection_pool_manager",
    "get_llm_degradation_manager",
    "get_concurrency_limiter",
    "get_performance_monitor",
    "initialize_performance_components",
    "reset_all_singletons",
    
    # 后端异常类
    "BackendAPIError",
    "BackendValidationError",
    "BackendNotFoundError",
    "BackendServerError",
    
    # 辅助函数
    "parse_validation_error",
    "format_validation_error_log",
]
