# -*- coding: utf-8 -*-
"""步骤9：工具结果汇总"""

import logging

from ..state import WorkflowState, StateUpdate
from .constants import MCP_TASK_TYPES, WORKFLOW_STEPS

logger = logging.getLogger(__name__)


async def node_aggregate_data(
    state: WorkflowState
) -> StateUpdate:
    """
    步骤9：工具结果汇总（结构化JSON）

    Args:
        state: 当前工作流状态

    Returns:
        StateUpdate: 状态更新，包含 aggregated_data
    """
    request_id = state.get("request_id", "unknown")
    dag_results = state.get("dag_results", {})
    user_profile = state.get("user_profile")
    membership_info = state.get("membership_info")
    retrieval_results = state.get("retrieval_results")

    # 汇总所有数据
    all_data = {}
    mcp_tools_called = []

    # 1. 从DAG执行结果中提取MCP工具调用结果
    if dag_results:
        for task_name, task_result in dag_results.items():
            # 只记录真正的MCP工具
            if task_name in MCP_TASK_TYPES:
                if task_result and isinstance(task_result, dict):
                    all_data[task_name] = task_result

                    # 严格的成功判断
                    has_error = "error" in task_result and task_result["error"] is not None
                    is_success = task_result.get("success", False) is True
                    is_fallback = task_result.get("fallback", False) or task_result.get("fallback_used", False)

                    if is_success and not has_error and not is_fallback:
                        mcp_tools_called.append(task_name)
                        logger.debug(f"   ✅ MCP工具: {task_name} (成功)")
                    else:
                        error_msg = task_result.get('error', 'Unknown')
                        logger.warning(f"   ⚠️ MCP工具: {task_name} (失败: {error_msg})")

            # 工作流程步骤数据也保存
            elif task_name in WORKFLOW_STEPS:
                if task_result and isinstance(task_result, dict):
                    all_data[task_name] = task_result

    # 2. 添加用户档案
    if user_profile:
        all_data["user_profile"] = user_profile

    # 3. 添加会员信息
    if membership_info:
        all_data["user_membership"] = membership_info

    # 4. 添加检索结果
    if retrieval_results and retrieval_results.get("results"):
        all_data["retrieval_results"] = {
            "results": retrieval_results.get("results", []),
            "count": retrieval_results.get("count", 0),
            "query_type": retrieval_results.get("query_type", "unknown")
        }

    workflow_data_count = len([
        k for k in all_data.keys()
        if k in WORKFLOW_STEPS or k in ['user_profile', 'user_membership', 'retrieval_results']
    ])

    logger.info(f"✅ [{request_id}] 步骤9完成:")
    logger.info(f"   - MCP工具调用: {len(mcp_tools_called)}个 ({', '.join(mcp_tools_called) if mcp_tools_called else '无'})")
    logger.info(f"   - 工作流程数据: {workflow_data_count}项")
    logger.info(f"   - 总数据项: {len(all_data)}个")

    return StateUpdate(updates={
        "aggregated_data": all_data,
        "_mcp_tools_called": mcp_tools_called
    })
