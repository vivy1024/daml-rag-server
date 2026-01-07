"""
工作流模块

参考 LangGraph StateGraph 模式重构的工作流管理模块。
提供状态管理、节点函数、条件路由和执行器。

版本: v1.0.0
日期: 2025-12-28

模块结构:
- state.py: 状态定义（WorkflowState TypedDict, StateUpdate dataclass）
- nodes.py: 节点函数（每个步骤一个纯函数）
- edges.py: 边定义（条件路由逻辑）
- graph.py: 图构建（StateGraph 组装）
- executor.py: 执行器（同步执行）
- stream_executor.py: 流式执行器
- singletons.py: 单例管理

向后兼容:
- execute_eleven_step_workflow: 同步执行11步工作流
- execute_eleven_step_workflow_stream: 流式执行11步工作流
- get_user_cache, get_membership_cache 等单例获取函数
"""

# 状态定义
from .state import (
    WorkflowState,
    StateUpdate,
    WorkflowStep,
    ComplexityLevel,
    create_initial_state,
    serialize_state,
    deserialize_state,
)

# 节点函数
from .nodes import (
    node_preload_user_profile,
    node_store_session,
    node_check_membership,
    node_classify_complexity,
    node_select_model,
    node_retrieve_few_shot,
    node_select_dag_template,
    node_execute_dag,
    node_retrieve_context,
    node_aggregate_data,
    node_llm_analysis,
    node_log_interaction,
    MCP_TASK_TYPES,
    WORKFLOW_STEPS,
)

# 边定义（条件路由）
from .edges import (
    route_after_complexity,
    route_after_dag,
    route_on_error,
    should_continue,
    route_retrieval_strategy,
    route_model_selection,
    should_skip_step,
    get_next_step,
)

# 图构建
from .graph import (
    WorkflowGraph,
    NodeConfig,
    EdgeConfig,
    get_default_graph,
    create_custom_graph,
)

# 执行器
from .executor import (
    WorkflowExecutor,
    execute_workflow,
)

# 流式执行器
from .stream_executor import (
    StreamWorkflowExecutor,
    execute_workflow_stream,
)

# 单例管理
from .singletons import (
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


# ============ 向后兼容别名 ============

async def execute_eleven_step_workflow(
    query_text: str,
    user_id: str,
    domain: str = "fitness",
    user_profile=None,
    session_id=None
):
    """
    执行完整的11步工作流程（向后兼容）
    
    这是对新 WorkflowExecutor 的包装，保持与原有接口兼容。
    
    Args:
        query_text: 用户查询文本
        user_id: 用户ID
        domain: 领域（默认fitness）
        user_profile: 用户档案（可选）
        session_id: 会话ID（可选）
        
    Returns:
        Dict[str, Any]: 工作流程执行结果
    """
    return await execute_workflow(
        query_text=query_text,
        user_id=user_id,
        domain=domain,
        user_profile=user_profile,
        session_id=session_id
    )


async def execute_eleven_step_workflow_stream(
    query_text: str,
    user_id: str,
    domain: str = "fitness",
    user_profile=None,
    session_id=None,
    topic_id=None  # 话题ID，用于多轮对话
):
    """
    执行11步工作流程（流式版本，向后兼容）
    
    这是对新 StreamWorkflowExecutor 的包装，保持与原有接口兼容。
    
    Args:
        query_text: 用户查询文本
        user_id: 用户ID
        domain: 领域（默认fitness）
        user_profile: 用户档案（可选）
        session_id: 会话ID（可选）
        topic_id: 话题ID（可选，用于多轮对话）
        
    Yields:
        Dict[str, Any]: SSE事件
    """
    async for event in execute_workflow_stream(
        query_text=query_text,
        user_id=user_id,
        domain=domain,
        user_profile=user_profile,
        session_id=session_id,
        topic_id=topic_id
    ):
        yield event


__all__ = [
    # ========== 状态相关 ==========
    "WorkflowState",
    "StateUpdate",
    "WorkflowStep",
    "ComplexityLevel",
    "create_initial_state",
    "serialize_state",
    "deserialize_state",
    
    # ========== 节点函数 ==========
    "node_preload_user_profile",
    "node_store_session",
    "node_check_membership",
    "node_classify_complexity",
    "node_select_model",
    "node_retrieve_few_shot",
    "node_select_dag_template",
    "node_execute_dag",
    "node_retrieve_context",
    "node_aggregate_data",
    "node_llm_analysis",
    "node_log_interaction",
    "MCP_TASK_TYPES",
    "WORKFLOW_STEPS",
    
    # ========== 边定义 ==========
    "route_after_complexity",
    "route_after_dag",
    "route_on_error",
    "should_continue",
    "route_retrieval_strategy",
    "route_model_selection",
    "should_skip_step",
    "get_next_step",
    
    # ========== 图构建 ==========
    "WorkflowGraph",
    "NodeConfig",
    "EdgeConfig",
    "get_default_graph",
    "create_custom_graph",
    
    # ========== 执行器 ==========
    "WorkflowExecutor",
    "execute_workflow",
    "StreamWorkflowExecutor",
    "execute_workflow_stream",
    
    # ========== 单例管理 ==========
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
    
    # ========== 向后兼容 ==========
    "execute_eleven_step_workflow",
    "execute_eleven_step_workflow_stream",
]
