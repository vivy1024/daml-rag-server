# -*- coding: utf-8 -*-
"""
健身应用层 - 基于DAML-RAG框架的健身领域应用

这个模块展示了如何使用DAML-RAG框架构建领域特定应用，核心特点是：
1. MCP工具驱动的原子化微服务架构
2. DAG编排的智能工作流程
3. 与Neo4j知识图谱的深度集成
4. 完整的11步无幻觉工作流程

模块结构（v3.0.0 重构版）：
├── workflow/          # 工作流模块（参考 LangGraph StateGraph）
│   ├── state.py      # 状态定义
│   ├── nodes.py      # 节点函数
│   ├── edges.py      # 边定义（条件路由）
│   ├── graph.py      # 图构建
│   ├── executor.py   # 同步执行器
│   ├── stream_executor.py  # 流式执行器
│   └── singletons.py # 单例管理
├── dag/              # DAG编排模块
│   ├── models.py     # 数据模型
│   ├── orchestrator.py    # 核心编排逻辑
│   ├── task_executor.py   # 任务执行器
│   ├── result_aggregator.py  # 结果汇总器
│   └── parameter_mapper.py   # 参数映射器
├── config/           # 配置管理模块
│   ├── prompts.py    # 提示词配置
│   ├── field_mapping.py  # 字段映射配置
│   └── runtime.py    # 运行时配置
├── services/         # 服务模块
├── mcp_tools/        # MCP工具
├── clients/          # 客户端
└── archive/          # 归档（原始大文件备份）

版本: v3.0.0
日期: 2025-12-28
"""

# ============ 工作流模块 ============
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
    
    # 图构建
    WorkflowGraph,
    NodeConfig,
    EdgeConfig,
    get_default_graph,
    create_custom_graph,
    
    # 单例管理
    get_user_cache,
    get_membership_cache,
    # get_workflow_monitor,  # 已删除
    get_cache_manager,
    get_connection_pool_manager,
    get_llm_degradation_manager,
    get_concurrency_limiter,
    # get_performance_monitor,  # 已删除
    initialize_performance_components,
    reset_all_singletons,
)

# ============ DAG编排模块 ============
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

# ============ 配置管理模块 ============
from .config import (
    # 字段映射
    FieldMappingManager,
    get_field_mapping_manager,
    map_exercise_fields,
    map_muscle_fields,
    batch_map_exercise_fields,
    batch_map_muscle_fields,
    EXERCISE_FIELD_MAPPING,
    MUSCLE_FIELD_MAPPING,
    
    # 提示词配置
    PromptConfigManager,
    PromptTemplate,
    get_prompt_config_manager,
    get_prompt,
    get_prompt_config,
    
    # 运行时配置
    RuntimeConfig,
    RuntimeConfigManager,
    get_runtime_config,
    get_runtime_config_manager,
    reload_runtime_config,
)

# ============ 占位符（保持向后兼容） ============
# 这些组件已被移除或重构，保留占位符以避免导入错误
FitnessApp = None
FitnessService = None
FitnessUserProfile = None
EnhancedChatService = None
FitnessOrchestrator = None  # 现在使用 EnhancedDAGOrchestrator

__all__ = [
    # ========== 工作流模块 ==========
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
    
    # 图构建
    "WorkflowGraph",
    "NodeConfig",
    "EdgeConfig",
    "get_default_graph",
    "create_custom_graph",
    
    # 单例管理
    "get_user_cache",
    "get_membership_cache",
    # "get_workflow_monitor",  # 已删除
    "get_cache_manager",
    "get_connection_pool_manager",
    "get_llm_degradation_manager",
    "get_concurrency_limiter",
    # "get_performance_monitor",  # 已删除
    "initialize_performance_components",
    "reset_all_singletons",
    
    # ========== DAG编排模块 ==========
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
    
    # ========== 配置管理模块 ==========
    # 字段映射
    "FieldMappingManager",
    "get_field_mapping_manager",
    "map_exercise_fields",
    "map_muscle_fields",
    "batch_map_exercise_fields",
    "batch_map_muscle_fields",
    "EXERCISE_FIELD_MAPPING",
    "MUSCLE_FIELD_MAPPING",
    
    # 提示词配置
    "PromptConfigManager",
    "PromptTemplate",
    "get_prompt_config_manager",
    "get_prompt",
    "get_prompt_config",
    
    # 运行时配置
    "RuntimeConfig",
    "RuntimeConfigManager",
    "get_runtime_config",
    "get_runtime_config_manager",
    "reload_runtime_config",
    
    # ========== 占位符（向后兼容） ==========
    "FitnessApp",
    "FitnessService",
    "FitnessUserProfile",
    "EnhancedChatService",
    "FitnessOrchestrator",
]
