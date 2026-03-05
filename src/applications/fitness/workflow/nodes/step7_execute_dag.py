# -*- coding: utf-8 -*-
"""步骤7：DAG编排执行"""

import logging

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_execute_dag(
    state: WorkflowState,
    dag_orchestrator=None,
    mcp_tool_manager=None,
    template_manager=None
) -> StateUpdate:
    """
    步骤7：DAG编排执行

    Args:
        state: 当前工作流状态
        dag_orchestrator: DAG编排器（可选）
        mcp_tool_manager: MCP工具管理器（可选）
        template_manager: DAG模板管理器（可选）

    Returns:
        StateUpdate: 状态更新，包含 dag_results
    """
    request_id = state.get("request_id", "unknown")
    selected_template_id = state.get("dag_template_id")
    user_profile = state.get("user_profile")
    session_id = state.get("session_id")
    query_text = state.get("query_text", "")
    user_id = state.get("user_id")

    if not selected_template_id:
        logger.warning(f"⚠️ [{request_id}] 步骤7: 无DAG模板ID，跳过执行")
        return StateUpdate(
            updates={"dag_results": None},
            warning="无DAG模板ID"
        )

    try:
        from ...enhanced_dag_orchestrator import EnhancedDAGOrchestrator
        from ...dag_template_system import DAGTemplateManager

        # 初始化模板管理器
        if template_manager is None:
            template_manager = DAGTemplateManager()

        # 初始化DAG编排器
        if dag_orchestrator is None:
            dag_orchestrator = EnhancedDAGOrchestrator(
                template_manager=template_manager,
                mcp_orchestrator=mcp_tool_manager
            )

        # 执行DAG模板
        dag_execution_result = await dag_orchestrator.execute_template(
            template_id=selected_template_id,
            user_profile=user_profile or {},
            session_context={
                "session_id": session_id,
                "query": query_text,
                "_context": {
                    "user_id": user_id,
                    "query": query_text,
                    "session_id": session_id,
                    "user_profile": user_profile
                }
            },
            cached_results=None
        )

        # 提取结果
        dag_results = dag_execution_result.results

        if dag_results:
            logger.info(
                f"✅ [{request_id}] 步骤7完成: "
                f"{dag_execution_result.tasks_completed}个任务成功, "
                f"{dag_execution_result.tasks_failed}个任务失败"
            )

            return StateUpdate(updates={
                "dag_results": dag_results,
                "_dag_tasks_completed": dag_execution_result.tasks_completed,
                "_dag_tasks_failed": dag_execution_result.tasks_failed
            })
        else:
            logger.warning(f"⚠️ [{request_id}] 步骤7: DAG执行返回空结果")
            return StateUpdate(
                updates={"dag_results": None},
                warning="DAG执行返回空结果"
            )

    except Exception as e:
        logger.error(f"❌ [{request_id}] 步骤7: DAG执行异常: {e}")
        return StateUpdate(
            updates={"dag_results": None},
            error=f"DAG执行异常: {str(e)}"
        )
