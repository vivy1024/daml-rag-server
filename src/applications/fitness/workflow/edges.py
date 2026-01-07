# -*- coding: utf-8 -*-
"""
工作流边定义模块（条件路由）

定义条件边：根据状态决定下一个节点。
参考 LangGraph 的 conditional_edges 设计。

版本: v1.0.0
日期: 2025-12-28

路由函数:
- route_after_complexity: 复杂度分类后的路由
- route_after_dag: DAG执行后的路由
- route_on_error: 错误处理路由
- should_continue: 是否继续执行
"""

import logging
from typing import Literal, Optional

from .state import WorkflowState, WorkflowStep

logger = logging.getLogger(__name__)


# ============ 路由类型定义 ============

# 复杂度路由目标
ComplexityRouteTarget = Literal["select_model", "simple_response"]

# DAG路由目标
DAGRouteTarget = Literal["llm_analysis", "fallback_search", "aggregate_data"]

# 错误路由目标
ErrorRouteTarget = Literal["continue", "fallback", "end"]

# 继续/结束路由
ContinueRouteTarget = Literal["continue", "end"]


# ============ 复杂度分类后的路由 ============

def route_after_complexity(state: WorkflowState) -> ComplexityRouteTarget:
    """
    复杂度分类后的路由
    
    根据查询复杂度决定下一步：
    - 简单查询：可以使用简单响应模式
    - 复杂查询：需要完整的模型选择流程
    
    Args:
        state: 当前工作流状态
        
    Returns:
        下一个节点名称
    """
    complexity_level = state.get("complexity_level", "simple")
    similarity = state.get("_complexity_similarity", 0.0)
    
    # 如果是非常简单的查询（相似度很低），可以使用简单响应
    if complexity_level == "simple" and similarity < 0.3:
        logger.debug(f"路由决策: 简单查询 (complexity={complexity_level}, similarity={similarity:.2f}) -> simple_response")
        return "simple_response"
    
    # 其他情况走完整流程
    logger.debug(f"路由决策: 标准流程 (complexity={complexity_level}, similarity={similarity:.2f}) -> select_model")
    return "select_model"


# ============ DAG执行后的路由 ============

def route_after_dag(state: WorkflowState) -> DAGRouteTarget:
    """
    DAG执行后的路由
    
    根据DAG执行结果决定下一步：
    - 成功：进入数据汇总
    - 失败：回退到三层检索
    
    Args:
        state: 当前工作流状态
        
    Returns:
        下一个节点名称
    """
    dag_results = state.get("dag_results")
    dag_tasks_completed = state.get("_dag_tasks_completed", 0)
    dag_tasks_failed = state.get("_dag_tasks_failed", 0)
    
    # 检查DAG执行是否成功
    if dag_results and dag_tasks_completed > 0:
        # 有成功的任务，进入数据汇总
        logger.debug(f"路由决策: DAG成功 (completed={dag_tasks_completed}, failed={dag_tasks_failed}) -> aggregate_data")
        return "aggregate_data"
    
    # DAG执行失败或无结果，回退到三层检索
    logger.debug(f"路由决策: DAG失败 (completed={dag_tasks_completed}, failed={dag_tasks_failed}) -> fallback_search")
    return "fallback_search"


# ============ 错误处理路由 ============

def route_on_error(state: WorkflowState) -> ErrorRouteTarget:
    """
    错误处理路由
    
    根据错误数量和类型决定下一步：
    - 少量错误：继续执行
    - 多个错误：使用降级策略
    - 严重错误：结束工作流
    
    Args:
        state: 当前工作流状态
        
    Returns:
        下一个节点名称
    """
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    current_step = state.get("current_step", 0)
    
    error_count = len(errors)
    warning_count = len(warnings)
    
    # 严重错误：超过3个错误，结束工作流
    if error_count > 3:
        logger.warning(f"路由决策: 严重错误 (errors={error_count}) -> end")
        return "end"
    
    # 多个错误：使用降级策略
    if error_count > 1:
        logger.warning(f"路由决策: 多个错误 (errors={error_count}) -> fallback")
        return "fallback"
    
    # 少量错误或警告：继续执行
    logger.debug(f"路由决策: 继续执行 (errors={error_count}, warnings={warning_count})")
    return "continue"


# ============ 是否继续执行 ============

def should_continue(state: WorkflowState) -> ContinueRouteTarget:
    """
    是否继续执行
    
    检查是否应该继续执行工作流：
    - 错误过多：结束
    - 已完成所有步骤：结束
    - 其他情况：继续
    
    Args:
        state: 当前工作流状态
        
    Returns:
        "continue" 或 "end"
    """
    errors = state.get("errors", [])
    current_step = state.get("current_step", 0)
    final_response = state.get("final_response")
    interaction_logged = state.get("interaction_logged", False)
    
    # 错误过多，结束
    if len(errors) > 3:
        logger.warning(f"工作流结束: 错误过多 (errors={len(errors)})")
        return "end"
    
    # 已完成所有步骤（步骤11完成）
    if current_step >= 11 and interaction_logged:
        logger.info(f"工作流结束: 所有步骤完成")
        return "end"
    
    # 已有最终响应但未记录交互
    if final_response and current_step >= 10:
        logger.debug(f"继续执行: 等待记录交互")
        return "continue"
    
    # 继续执行
    return "continue"


# ============ 检索策略路由 ============

def route_retrieval_strategy(state: WorkflowState) -> Literal["dag_execution", "three_layer", "simple_search"]:
    """
    检索策略路由
    
    根据查询复杂度和用户权限决定检索策略：
    - 复杂查询 + 高级会员：DAG编排执行
    - 中等复杂度：三层检索
    - 简单查询：简单搜索
    
    Args:
        state: 当前工作流状态
        
    Returns:
        检索策略名称
    """
    complexity_level = state.get("complexity_level", "simple")
    is_premium = state.get("is_premium", False)
    dag_template_id = state.get("dag_template_id")
    
    # 复杂查询且有DAG模板
    if complexity_level == "complex" and dag_template_id:
        logger.debug(f"检索策略: DAG编排执行 (complexity={complexity_level}, template={dag_template_id})")
        return "dag_execution"
    
    # 中等复杂度或高级会员
    if complexity_level == "moderate" or is_premium:
        logger.debug(f"检索策略: 三层检索 (complexity={complexity_level}, premium={is_premium})")
        return "three_layer"
    
    # 简单查询
    logger.debug(f"检索策略: 简单搜索 (complexity={complexity_level})")
    return "simple_search"


# ============ 模型选择路由 ============

def route_model_selection(state: WorkflowState) -> Literal["teacher", "student"]:
    """
    模型选择路由
    
    根据查询复杂度和会员等级选择模型：
    - 复杂查询或高级会员：教师模型
    - 其他情况：学生模型
    
    Args:
        state: 当前工作流状态
        
    Returns:
        模型类型
    """
    complexity_level = state.get("complexity_level", "simple")
    similarity = state.get("_complexity_similarity", 0.0)
    is_premium = state.get("is_premium", False)
    
    # 复杂查询或高相似度
    if complexity_level == "complex" or similarity >= 0.7:
        return "teacher"
    
    # 高级会员
    if is_premium:
        return "teacher"
    
    # 默认学生模型
    return "student"


# ============ 步骤跳过检查 ============

def should_skip_step(state: WorkflowState, step: WorkflowStep) -> bool:
    """
    检查是否应该跳过某个步骤
    
    Args:
        state: 当前工作流状态
        step: 要检查的步骤
        
    Returns:
        是否应该跳过
    """
    # 如果已有用户档案，跳过步骤1
    if step == WorkflowStep.PRELOAD_USER_PROFILE:
        if state.get("user_profile"):
            return True
    
    # 如果已有会话ID，跳过步骤2
    if step == WorkflowStep.STORE_SESSION:
        if state.get("session_id"):
            return True
    
    # 如果是匿名用户，跳过会员检查
    if step == WorkflowStep.CHECK_MEMBERSHIP:
        if not state.get("user_id"):
            return True
    
    # 如果没有DAG模板，跳过DAG执行
    if step == WorkflowStep.EXECUTE_DAG:
        if not state.get("dag_template_id"):
            return True
    
    return False


# ============ 获取下一步骤 ============

def get_next_step(current_step: WorkflowStep, state: WorkflowState) -> Optional[WorkflowStep]:
    """
    获取下一个步骤
    
    根据当前步骤和状态决定下一个步骤。
    
    Args:
        current_step: 当前步骤
        state: 当前工作流状态
        
    Returns:
        下一个步骤，如果工作流结束则返回 None
    """
    # 步骤顺序映射
    step_order = {
        WorkflowStep.START: WorkflowStep.PRELOAD_USER_PROFILE,
        WorkflowStep.PRELOAD_USER_PROFILE: WorkflowStep.STORE_SESSION,
        WorkflowStep.STORE_SESSION: WorkflowStep.CHECK_MEMBERSHIP,
        WorkflowStep.CHECK_MEMBERSHIP: WorkflowStep.CLASSIFY_COMPLEXITY,
        WorkflowStep.CLASSIFY_COMPLEXITY: WorkflowStep.SELECT_MODEL,
        WorkflowStep.SELECT_MODEL: WorkflowStep.RETRIEVE_FEW_SHOT,
        WorkflowStep.RETRIEVE_FEW_SHOT: WorkflowStep.SELECT_DAG_TEMPLATE,
        WorkflowStep.SELECT_DAG_TEMPLATE: WorkflowStep.EXECUTE_DAG,
        WorkflowStep.EXECUTE_DAG: WorkflowStep.RETRIEVE_CONTEXT,
        WorkflowStep.RETRIEVE_CONTEXT: WorkflowStep.AGGREGATE_DATA,
        WorkflowStep.AGGREGATE_DATA: WorkflowStep.LLM_ANALYSIS,
        WorkflowStep.LLM_ANALYSIS: WorkflowStep.LOG_INTERACTION,
        WorkflowStep.LOG_INTERACTION: WorkflowStep.END,
        WorkflowStep.END: None,
    }
    
    next_step = step_order.get(current_step)
    
    # 检查是否应该跳过下一步
    while next_step and should_skip_step(state, next_step):
        logger.debug(f"跳过步骤: {next_step.value}")
        next_step = step_order.get(next_step)
    
    return next_step


# ============ 导出 ============

__all__ = [
    # 路由函数
    "route_after_complexity",
    "route_after_dag",
    "route_on_error",
    "should_continue",
    "route_retrieval_strategy",
    "route_model_selection",
    # 辅助函数
    "should_skip_step",
    "get_next_step",
]
