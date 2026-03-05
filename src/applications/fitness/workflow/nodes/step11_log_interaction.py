# -*- coding: utf-8 -*-
"""步骤11：记录交互"""

import logging
from typing import Dict, Any

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_log_interaction(
    state: WorkflowState,
    backend_client=None
) -> StateUpdate:
    """
    步骤11：记录交互（用于未来学习）

    Args:
        state: 当前工作流状态
        backend_client: 后端客户端（可选）

    Returns:
        StateUpdate: 状态更新，包含 interaction_logged
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    query_text = state.get("query_text", "")
    final_response = state.get("final_response", "")
    selected_model = state.get("selected_model", "unknown")
    mcp_tools_called = state.get("_mcp_tools_called", [])
    dag_template_id = state.get("dag_template_id")
    complexity_level = state.get("complexity_level")
    few_shot_examples = state.get("few_shot_examples", [])
    retrieval_results = state.get("retrieval_results", {})

    if not backend_client:
        logger.warning(f"⚠️ [{request_id}] 步骤11: 无后端客户端，跳过交互记录")
        return StateUpdate(updates={"interaction_logged": False})

    try:
        # 转换user_id
        user_id_int = None
        if isinstance(user_id, int):
            user_id_int = user_id
        elif isinstance(user_id, str) and user_id.isdigit():
            user_id_int = int(user_id)

        if not user_id_int:
            logger.info(f"✅ [{request_id}] 步骤11完成: 匿名用户，跳过交互记录")
            return StateUpdate(updates={"interaction_logged": False})

        # 计算检索层数
        retrieval_layers_count = 0
        if retrieval_results:
            layer_results = retrieval_results.get("layer_results", {})
            if layer_results:
                retrieval_layers_count = len(layer_results)
            elif retrieval_results.get("results"):
                retrieval_layers_count = 1

        # 保存会话
        result_data = await backend_client.save_chat_session(
            session_id=session_id,
            user_id=user_id_int,
            user_query=query_text,
            llm_response=final_response,
            model_used=selected_model,
            tools_used=mcp_tools_called,
            metadata={
                "graphrag_service": True,
                "quality_score": None,
                "retrieval_layers": retrieval_layers_count,
                "workflow_steps": 11,
                "is_complex": complexity_level == "complex",
                "few_shot_count": len(few_shot_examples),
                "dag_template_id": dag_template_id,
                "mcp_tools_count": len(mcp_tools_called),
                "request_id": request_id,
                "awaiting_user_feedback": True
            },
            qdrant_point_id=None
        )

        logger.info(f"✅ [{request_id}] 步骤11完成: 交互记录完成 (db_id={result_data.get('id')})")
        logger.info(f"   - MCP工具: {', '.join(mcp_tools_called) if mcp_tools_called else '无'}")
        logger.info(f"   - 工具数量: {len(mcp_tools_called)}")

        return StateUpdate(updates={
            "interaction_logged": True,
            "_interaction_db_id": result_data.get('id')
        })

    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤11: 交互记录失败: {e}")
        return StateUpdate(
            updates={"interaction_logged": False},
            warning=f"交互记录失败: {str(e)}"
        )
