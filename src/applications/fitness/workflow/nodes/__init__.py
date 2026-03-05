# -*- coding: utf-8 -*-
"""
工作流节点函数模块 — 按步骤拆分

每个节点是一个纯函数：接收状态，返回状态更新。
参考 LangGraph 的节点设计，确保函数不直接修改输入状态。

拆分自原 nodes.py (v1.1.0, 2025-12-29)
"""

from .step1_preload_user_profile import node_preload_user_profile
from .step2_store_session import node_store_session
from .step3_check_membership import node_check_membership
from .step4_classify_complexity import node_classify_complexity
from .step5_select_model import node_select_model
from .step6_retrieve_few_shot import node_retrieve_few_shot
from .step6_5_select_dag_template import node_select_dag_template
from .step7_execute_dag import node_execute_dag
from .step8_retrieve_context import node_retrieve_context
from .step9_aggregate_data import node_aggregate_data
from .step10_llm_analysis import node_llm_analysis
from .step11_log_interaction import node_log_interaction
from .constants import MCP_TASK_TYPES, WORKFLOW_STEPS

__all__ = [
    # 节点函数
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
    # 常量
    "MCP_TASK_TYPES",
    "WORKFLOW_STEPS",
]
