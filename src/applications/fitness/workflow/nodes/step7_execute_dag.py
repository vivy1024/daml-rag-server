# -*- coding: utf-8 -*-
"""步骤7：DAG编排执行（含 Harness v1 钩子）"""

import logging

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


def _get_harness_config():
    """获取 HarnessConfig（容错：配置不可用时返回 None）"""
    try:
        from ...config.runtime import get_runtime_config
        return get_runtime_config().harness
    except Exception:
        return None


async def node_execute_dag(
    state: WorkflowState,
    dag_orchestrator=None,
    mcp_tool_manager=None,
    template_manager=None
) -> StateUpdate:
    """
    步骤7：DAG编排执行

    当 HarnessConfig 启用时，在 DAG 执行前后插入：
    1. pre_template: ExecutionPolicy 安全策略检查
    2. post_dag: OutputVerifier 输出校验
    3. 全程: HarnessTracer 追踪

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

    # ============================================================
    # Harness v1: 初始化（feature flag 控制）
    # ============================================================
    harness_cfg = _get_harness_config()
    harness_active = (
        harness_cfg is not None
        and harness_cfg.is_active_for(selected_template_id, user_id or 0)
    )

    tracer = None
    policy = None
    verifier = None

    if harness_active:
        try:
            from ...harness import ExecutionPolicy, OutputVerifier, HarnessTracer
            if harness_cfg.tracer_enabled:
                tracer = HarnessTracer()
                tracer.start_trace(str(user_id or ""), selected_template_id)
            if harness_cfg.policy_enabled:
                policy = ExecutionPolicy()
            if harness_cfg.verifier_enabled:
                verifier = OutputVerifier()
            logger.info(f"🔧 [{request_id}] Harness v1 激活: template={selected_template_id}")
        except Exception as e:
            logger.warning(f"⚠️ [{request_id}] Harness 初始化失败，回退旧路径: {e}")
            harness_active = False

    try:
        from ...enhanced_dag_orchestrator import EnhancedDAGOrchestrator
        from ...dag_template_system import DAGTemplateManager

        # 初始化模板管理器
        if template_manager is None:
            template_manager = DAGTemplateManager()

        # ============================================================
        # Harness v1: pre_template 策略检查
        # ============================================================
        if harness_active and policy:
            if tracer:
                tracer.start_stage("policy")

            template_def = template_manager.get_template(selected_template_id)
            if template_def:
                decision = policy.check_pre_template(
                    template_id=selected_template_id,
                    complexity_level=template_def.complexity_level,
                    required_tools=template_def.required_tools,
                    user_profile=user_profile or {},
                )

                if tracer:
                    tracer.record_policy([decision.to_dict()])
                    tracer.end_stage("policy")

                if decision.decision == "deny":
                    logger.warning(
                        f"🚫 [{request_id}] 策略拒绝: {decision.reason}"
                    )
                    # 降级：告知 LLM 需要更安全的方案
                    fallback_update = {
                        "dag_results": None,
                        "_harness_policy_deny": True,
                        "_harness_deny_reason": decision.reason,
                    }
                    if tracer:
                        tracer.end_trace(output_rendered=False, error=f"policy_deny: {decision.reason}")
                    return StateUpdate(
                        updates=fallback_update,
                        warning=f"策略拒绝: {decision.reason}"
                    )

        # 初始化DAG编排器
        if dag_orchestrator is None:
            dag_orchestrator = EnhancedDAGOrchestrator(
                template_manager=template_manager,
                mcp_orchestrator=mcp_tool_manager
            )

        # 执行DAG模板
        if tracer:
            tracer.start_stage("dag_execution")

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

        if tracer:
            tracer.end_stage("dag_execution")

        # 提取结果
        dag_results = dag_execution_result.results

        # ============================================================
        # Harness v1: post_dag 输出校验
        # ============================================================
        if harness_active and verifier and dag_results:
            if tracer:
                tracer.start_stage("verifier")

            # 获取硬约束
            hard_constraints = []
            if harness_cfg.memory_v2_enabled:
                try:
                    from ...services.user_memory import get_user_memory_service
                    mem = get_user_memory_service()
                    constraints = await mem.recall_constraints(user_id or 0)
                    hard_constraints = [c["content"] for c in constraints]
                except Exception as e:
                    logger.warning(f"⚠️ [{request_id}] 硬约束检索失败: {e}")

            verification = verifier.verify(
                dag_results=dag_results,
                user_profile=user_profile or {},
                hard_constraints=hard_constraints,
            )

            if tracer:
                tracer.record_verifier(verification.to_dict())
                tracer.end_stage("verifier")

            if not verification.passed:
                logger.warning(
                    f"🚫 [{request_id}] 输出校验未通过: "
                    f"{len(verification.critical_failures)} critical"
                )
                # 将校验结果附加到状态，供 LLM 综合时参考
                dag_results["_harness_verification"] = verification.to_dict()

        if dag_results:
            logger.info(
                f"✅ [{request_id}] 步骤7完成: "
                f"{dag_execution_result.tasks_completed}个任务成功, "
                f"{dag_execution_result.tasks_failed}个任务失败"
            )

            if tracer:
                tracer.end_trace(output_rendered=True)

            return StateUpdate(updates={
                "dag_results": dag_results,
                "_dag_tasks_completed": dag_execution_result.tasks_completed,
                "_dag_tasks_failed": dag_execution_result.tasks_failed
            })
        else:
            logger.warning(f"⚠️ [{request_id}] 步骤7: DAG执行返回空结果")
            if tracer:
                tracer.end_trace(output_rendered=False, error="empty_dag_results")
            return StateUpdate(
                updates={"dag_results": None},
                warning="DAG执行返回空结果"
            )

    except Exception as e:
        logger.error(f"❌ [{request_id}] 步骤7: DAG执行异常: {e}")
        if tracer:
            tracer.end_trace(output_rendered=False, error=str(e))
        return StateUpdate(
            updates={"dag_results": None},
            error=f"DAG执行异常: {str(e)}"
        )

