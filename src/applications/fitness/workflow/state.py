"""
工作流状态定义模块

参考 LangGraph 的状态管理模式，定义工作流状态数据结构。
每个节点接收状态，返回状态更新（而非直接修改）。

版本: v1.0.0
日期: 2025-12-28
"""

from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class WorkflowStep(Enum):
    """工作流步骤枚举"""
    START = "start"
    PRELOAD_USER_PROFILE = "preload_user_profile"  # 步骤1
    STORE_SESSION = "store_session"  # 步骤2
    CHECK_MEMBERSHIP = "check_membership"  # 步骤3
    CLASSIFY_COMPLEXITY = "classify_complexity"  # 步骤4
    SELECT_MODEL = "select_model"  # 步骤5
    RETRIEVE_FEW_SHOT = "retrieve_few_shot"  # 步骤6
    SELECT_DAG_TEMPLATE = "select_dag_template"  # 步骤6.5
    EXECUTE_DAG = "execute_dag"  # 步骤7
    RETRIEVE_CONTEXT = "retrieve_context"  # 步骤8
    AGGREGATE_DATA = "aggregate_data"  # 步骤9
    LLM_ANALYSIS = "llm_analysis"  # 步骤10
    LOG_INTERACTION = "log_interaction"  # 步骤11
    END = "end"


class ComplexityLevel(Enum):
    """查询复杂度级别"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class WorkflowState(TypedDict, total=False):
    """
    工作流状态（参考 LangGraph AgentState）
    
    使用 TypedDict 定义，支持类型检查和IDE自动补全。
    total=False 表示所有字段都是可选的。
    """
    # ========== 请求信息 ==========
    request_id: str  # 请求唯一标识
    user_id: str  # 用户ID
    query_text: str  # 用户查询文本
    domain: str  # 领域（默认 fitness）
    
    # ========== 步骤1-2: 用户上下文 ==========
    user_profile: Optional[Dict[str, Any]]  # 用户档案
    session_id: Optional[str]  # 会话ID
    
    # ========== 步骤3: 会员权限 ==========
    membership_info: Optional[Dict[str, Any]]  # 会员信息
    is_premium: bool  # 是否高级会员
    
    # ========== 步骤4-5: 复杂度和模型选择 ==========
    complexity_level: Optional[str]  # 复杂度级别
    selected_model: Optional[str]  # 选择的模型
    
    # ========== 步骤6: Few-Shot ==========
    few_shot_examples: Optional[List[Dict[str, Any]]]  # Few-Shot示例
    
    # ========== 步骤6.5-7: DAG ==========
    dag_template_id: Optional[str]  # DAG模板ID
    dag_results: Optional[Dict[str, Any]]  # DAG执行结果
    
    # ========== 步骤8-9: 检索结果 ==========
    retrieval_results: Optional[Dict[str, Any]]  # 检索结果
    aggregated_data: Optional[Dict[str, Any]]  # 汇总数据
    
    # ========== 步骤10-11: 最终响应 ==========
    final_response: Optional[str]  # 最终响应
    interaction_logged: bool  # 是否已记录交互
    
    # ========== 元数据 ==========
    step_timings: Dict[str, float]  # 各步骤耗时
    errors: List[str]  # 错误列表
    warnings: List[str]  # 警告列表
    current_step: int  # 当前步骤编号
    current_step_name: str  # 当前步骤名称
    
    # ========== 流式输出相关 ==========
    is_streaming: bool  # 是否流式输出
    stream_buffer: Optional[str]  # 流式缓冲区


@dataclass
class StateUpdate:
    """
    状态更新（节点返回值）
    
    节点函数返回此对象，包含需要更新的状态字段和可选的路由信息。
    """
    updates: Dict[str, Any] = field(default_factory=dict)
    next_step: Optional[str] = None  # 条件路由：指定下一个节点
    error: Optional[str] = None  # 错误信息
    warning: Optional[str] = None  # 警告信息
    
    def __post_init__(self):
        """初始化后处理"""
        if self.updates is None:
            self.updates = {}
    
    def merge_into(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        将更新合并到状态中
        
        Args:
            state: 当前状态字典
            
        Returns:
            更新后的状态字典（新对象，不修改原状态）
        """
        new_state = state.copy()
        new_state.update(self.updates)
        
        # 处理错误
        if self.error:
            errors = new_state.get("errors", [])
            if isinstance(errors, list):
                errors = errors.copy()
                errors.append(self.error)
                new_state["errors"] = errors
        
        # 处理警告
        if self.warning:
            warnings = new_state.get("warnings", [])
            if isinstance(warnings, list):
                warnings = warnings.copy()
                warnings.append(self.warning)
                new_state["warnings"] = warnings
        
        return new_state


def create_initial_state(
    request_id: str,
    user_id: str,
    query_text: str,
    domain: str = "fitness",
    is_streaming: bool = False,
    **kwargs
) -> WorkflowState:
    """
    创建初始工作流状态
    
    Args:
        request_id: 请求唯一标识
        user_id: 用户ID
        query_text: 用户查询文本
        domain: 领域（默认 fitness）
        is_streaming: 是否流式输出
        **kwargs: 其他初始状态字段
        
    Returns:
        初始化的工作流状态
    """
    state: WorkflowState = {
        # 请求信息
        "request_id": request_id,
        "user_id": user_id,
        "query_text": query_text,
        "domain": domain,
        
        # 初始化为空/默认值
        "user_profile": None,
        "session_id": None,
        "membership_info": None,
        "is_premium": False,
        "complexity_level": None,
        "selected_model": None,
        "few_shot_examples": None,
        "dag_template_id": None,
        "dag_results": None,
        "retrieval_results": None,
        "aggregated_data": None,
        "final_response": None,
        "interaction_logged": False,
        
        # 元数据
        "step_timings": {},
        "errors": [],
        "warnings": [],
        "current_step": 0,
        "current_step_name": WorkflowStep.START.value,
        
        # 流式输出
        "is_streaming": is_streaming,
        "stream_buffer": None,
    }
    
    # 合并额外参数
    state.update(kwargs)
    
    return state


def serialize_state(state: WorkflowState) -> Dict[str, Any]:
    """
    序列化状态（用于调试和恢复）
    
    Args:
        state: 工作流状态
        
    Returns:
        可JSON序列化的字典
    """
    import json
    
    def make_serializable(obj):
        """递归处理不可序列化的对象"""
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(item) for item in obj]
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, '__dict__'):
            return make_serializable(obj.__dict__)
        else:
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    return make_serializable(dict(state))


def deserialize_state(data: Dict[str, Any]) -> WorkflowState:
    """
    反序列化状态（用于恢复）
    
    Args:
        data: 序列化的状态数据
        
    Returns:
        工作流状态
    """
    state: WorkflowState = {}
    
    # 直接复制所有字段
    for key, value in data.items():
        state[key] = value
    
    # 确保列表字段是列表
    if "errors" not in state or state["errors"] is None:
        state["errors"] = []
    if "warnings" not in state or state["warnings"] is None:
        state["warnings"] = []
    if "step_timings" not in state or state["step_timings"] is None:
        state["step_timings"] = {}
    
    return state
