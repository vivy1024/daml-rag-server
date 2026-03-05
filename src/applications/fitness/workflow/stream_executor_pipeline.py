# -*- coding: utf-8 -*-
"""
PipelineMixin: 管线步骤执行逻辑

从 StreamWorkflowExecutor 提取的管线编排方法：
- execute_stream(): 主流式执行入口
- _execute_steps_1_2 ~ _execute_step_9: 同步管线步骤
- _execute_step_11: 交互记录

版本: v1.0.0
日期: 2026-03-05
"""

import logging
import time
import uuid
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator

from .state import (
    WorkflowState,
    StateUpdate,
    create_initial_state,
)

logger = logging.getLogger(__name__)


class PipelineMixin:
    """
    管线步骤执行 Mixin

    提供工作流管线编排能力：
    - execute_stream(): 流式执行入口（步骤1-12协调）
    - _execute_steps_1_2 ~ _execute_step_9: 同步步骤
    - _execute_step_11: 交互记录
    """

    async def execute_stream(
        self,
        query_text: str,
        user_id: str,
        domain: str = "fitness",
        user_profile: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        strategy: str = "dag",
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行工作流

        步骤1-9保持同步执行，步骤10改为流式LLM调用。
        集成上下文工程模块进行多轮对话管理。
        集成权限检查模块进行用量控制（Requirements 7.1, 7.4）。

        Args:
            query_text: 用户查询文本
            user_id: 用户ID
            domain: 领域
            user_profile: 用户档案
            session_id: 会话ID
            topic_id: 话题ID（用于多轮对话）
            strategy: 执行策略（dag或agent，默认dag）
            **kwargs: 其他参数

        Yields:
            SSE事件字典:
            - type: "step" | "chunk" | "structured_data" | "done" | "error"
            - data: 事件数据
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]

        logger.info(f"🚀 [{request_id}] 开始执行工作流程（流式）")
        logger.info(f"📝 查询: {query_text[:50]}...")
        logger.info(f"👤 用户: {user_id}")
        logger.info(f"🎯 策略: {strategy}")

        # ========== 权限检查（Requirements 7.1, 7.2） ==========
        permission_result = await self._check_permission_before_execute(
            user_id=user_id,
            strategy=strategy,
            request_id=request_id
        )

        if not permission_result.get("allowed", True):
            # 权限检查失败，返回错误事件
            yield {
                "type": "error",
                "error": permission_result.get("message", "权限检查失败"),
                "error_code": "PERMISSION_DENIED",
                "upgrade_hint": permission_result.get("upgrade_hint"),
                "request_id": request_id
            }
            return

        # ========== DAG模式：11步工作流程 ==========
        logger.info(f"📊 [{request_id}] 使用DAG模式执行")

        # ========== 上下文工程：构建对话上下文 ==========
        context_result = None
        conversation_history = []

        if self.context_engine:
            try:
                context_result = await self.context_engine.build_context(
                    user_id=str(user_id),
                    message=query_text,
                    topic_id=topic_id,
                    user_profile=user_profile,
                )
                conversation_history = context_result.conversation_history

                logger.info(
                    f"📚 [{request_id}] 上下文构建完成: "
                    f"history={len(conversation_history)}条, "
                    f"tokens={context_result.total_tokens}, "
                    f"compressed={context_result.was_compressed}"
                )
            except (RuntimeError, ValueError, ConnectionError, TimeoutError) as e:
                logger.warning(f"[{request_id}] 上下文构建失败: {e}")

        # 初始化状态
        state = create_initial_state(
            request_id=request_id,
            user_id=user_id,
            query_text=query_text,
            domain=domain,
            is_streaming=True,
            user_profile=user_profile,
            session_id=session_id,
            **kwargs
        )

        # 将上下文信息添加到状态
        state["strategy"] = strategy
        if context_result:
            state["conversation_history"] = conversation_history
            state["topic_id"] = context_result.topic_id
            state["conversation_turn"] = context_result.conversation_turn
            state["context_was_compressed"] = context_result.was_compressed
            state["context_total_tokens"] = context_result.total_tokens
            # 跨对话记忆注入
            if hasattr(context_result, "user_memory_text") and context_result.user_memory_text:
                state["user_memory_text"] = context_result.user_memory_text

        # 流式监控变量
        ttfb_ms = None
        first_chunk_time = None
        tokens_generated = 0
        content_length = 0

        # 增加活跃连接数
        if self.streaming_monitor:
            self.streaming_monitor.increment_active_connections()

        # 开始监控会话
        perf_context = None
        if self.performance_monitor:
            perf_context = self.performance_monitor.start_workflow(
                request_id=request_id,
                user_id=str(user_id)
            )

        try:
            # ========== 步骤1-9：同步执行 ==========

            # 步骤1-2：并行执行
            yield {
                "type": "step",
                "step": 1,
                "message": "正在加载用户档案和初始化会话..."
            }

            state = await self._execute_steps_1_2(state)

            # 步骤3-4：并行执行
            yield {
                "type": "step",
                "step": 3,
                "message": "检查会员权限和分析查询复杂度..."
            }

            state = await self._execute_steps_3_4(state)

            # 步骤5：智能模型选择
            yield {
                "type": "step",
                "step": 5,
                "message": "选择AI模型..."
            }

            state = await self._execute_step_5(state)

            # 步骤6：Few-Shot检索
            yield {
                "type": "step",
                "step": 6,
                "message": "检索最佳实践..."
            }

            state = await self._execute_step_6(state)

            # 步骤6.5：LLM选择DAG模板
            yield {
                "type": "step",
                "step": 7,
                "message": "选择执行方案..."
            }

            state = await self._execute_step_6_5(state)

            # 步骤7-8：DAG编排执行
            yield {
                "type": "step",
                "step": 8,
                "message": "执行数据分析..."
            }

            state = await self._execute_steps_7_8(state)

            # 步骤9：工具结果汇总
            yield {
                "type": "step",
                "step": 9,
                "message": "汇总分析结果..."
            }

            state = await self._execute_step_9(state)

            # 发送结构化数据（元数据）
            if state.get("aggregated_data"):
                yield {
                    "type": "structured_data",
                    "data": {
                        "mcp_tools_called": state.get("_mcp_tools_called", []),
                        "dag_template_id": state.get("dag_template_id"),
                        "complexity_level": state.get("complexity_level")
                    }
                }

            # 程序化发送训练计划数据（不依赖LLM嵌入）
            # 支持多种训练计划工具：professional_program_designer 和 periodized_program_designer
            dag_results = state.get("dag_results") or {}
            program_result = None
            program_tool_name = None

            # 优先检查 professional_program_designer
            if dag_results and "professional_program_designer" in dag_results:
                result = dag_results["professional_program_designer"]
                if result and result.get("success") and not result.get("error"):
                    program_result = result
                    program_tool_name = "professional_program_designer"

            # 如果没有，检查 periodized_program_designer
            if not program_result and dag_results and "periodized_program_designer" in dag_results:
                result = dag_results["periodized_program_designer"]
                if result and result.get("success") and not result.get("error"):
                    program_result = result
                    program_tool_name = "periodized_program_designer"

            # 发送训练计划数据
            if program_result:
                yield {
                    "type": "structured_data",
                    "data_type": "training_plan",
                    "data": program_result
                }
                weekly_count = len(program_result.get('weekly_programs', []))
                if weekly_count == 0 and program_result.get('weekly_program'):
                    weekly_count = 1
                logger.info(
                    f"📊 程序化发送训练计划数据: "
                    f"tool={program_tool_name}, "
                    f"weekly_programs={weekly_count}周"
                )

            # ========== 步骤10：流式LLM生成 ==========

            yield {
                "type": "step",
                "step": 10,
                "message": "AI正在分析..."
            }

            # 记录TTFB开始时间
            ttfb_start = time.time()

            # 流式生成
            async for chunk in self._execute_step_10_stream(state):
                # 捕获 backend_used 元数据（不发送给前端）
                if "_backend_used" in chunk:
                    state["backend_used"] = chunk["_backend_used"]
                    continue

                # 记录首字节时间
                if first_chunk_time is None:
                    first_chunk_time = time.time()
                    ttfb_ms = (first_chunk_time - ttfb_start) * 1000

                    if self.streaming_monitor:
                        self.streaming_monitor.record_ttfb(ttfb_ms)

                # 更新统计
                tokens_generated += 1
                content_length += len(chunk.get("content", ""))

                # 累积响应
                current_response = state.get("final_response") or ""
                state["final_response"] = current_response + chunk.get("content", "")

                yield {
                    "type": "chunk",
                    "content": chunk.get("content", ""),
                    "tokens": tokens_generated
                }

            # ========== 步骤11：记录交互 ==========

            yield {
                "type": "step",
                "step": 11,
                "message": "保存会话记录..."
            }

            state = await self._execute_step_11(state)

            # ========== 步骤12：三轨评分（新增） ==========

            yield {
                "type": "step",
                "step": 12,
                "message": "计算个性化评分..."
            }

            state = await self._execute_step_12_three_track_rating(state)

            # 发送三轨评分结果
            if state.get("three_track_rating"):
                yield {
                    "type": "rating",
                    "data": state.get("three_track_rating")
                }

            # ========== 上下文工程：记录对话历史 ==========
            # Requirements: 8.3 - 对话历史管理
            if self.context_engine and state.get("final_response"):
                try:
                    await self.context_engine.add_turn(
                        user_id=str(user_id),
                        user_message=query_text,
                        assistant_response=state.get("final_response", ""),
                        topic_id=state.get("topic_id"),
                        session_id=state.get("session_id"),
                        tools_used=state.get("_mcp_tools_called", []),
                        metadata={
                            "request_id": request_id,
                            "dag_template_id": state.get("dag_template_id"),
                            "three_track_rating": state.get("three_track_rating"),
                        }
                    )
                    logger.info(f"📝 [{request_id}] 对话历史已记录")
                except (RuntimeError, ValueError, ConnectionError, TimeoutError) as e:
                    logger.warning(f"[{request_id}] 记录对话历史失败: {e}")

            # ========== 偏好提取（异步，不阻塞主流程） ==========
            if state.get("final_response") and user_id:
                try:
                    import asyncio
                    from ..services.preference_extractor import (
                        should_extract_preferences,
                        extract_preferences_from_conversation,
                    )
                    from ..services.user_memory import get_user_memory_service

                    user_query_text = state.get("query_text", "")
                    final_resp = state.get("final_response", "")

                    if should_extract_preferences(user_query_text):
                        async def _extract_and_store():
                            try:
                                prefs = await extract_preferences_from_conversation(
                                    user_query=user_query_text,
                                    ai_response=final_resp,
                                )
                                if prefs:
                                    mem_service = get_user_memory_service()
                                    uid = int(user_id) if str(user_id).isdigit() else 0
                                    for p in prefs:
                                        await mem_service.remember(
                                            user_id=uid,
                                            content=p["content"],
                                            category=p["category"],
                                        )
                                    logger.info(
                                        f"🧠 [{request_id}] 偏好提取: "
                                        f"存储{len(prefs)}条记忆 (user={user_id})"
                                    )
                            except (RuntimeError, ValueError, ConnectionError, TimeoutError) as pe:
                                logger.warning(f"[{request_id}] 偏好提取失败: {pe}")

                        asyncio.create_task(_extract_and_store())
                        logger.debug(f"[{request_id}] 偏好提取任务已启动（异步）")
                except (ImportError, AttributeError) as e:
                    logger.warning(f"[{request_id}] 偏好提取初始化失败: {e}")

            # 计算总耗时
            processing_time = time.time() - start_time

            # 记录流式会话完成
            if self.streaming_monitor:
                self.streaming_monitor.record_stream_complete(
                    duration_ms=processing_time * 1000,
                    tokens=tokens_generated,
                    content_length=content_length
                )
                self.streaming_monitor.decrement_active_connections()

            # 完成监控
            if self.performance_monitor and perf_context:
                self.performance_monitor.finish_workflow(
                    context=perf_context,
                    success=True,
                    total_duration_ms=processing_time * 1000
                )

            # ========== 增加用量计数（Requirements 7.4） ==========
            await self._increment_usage_after_execute(
                user_id=user_id,
                strategy=strategy,
                request_id=request_id
            )

            # ========== 积分上报（Requirements 10.1） ==========
            await self._report_credit_consumption(
                user_id=user_id,
                tokens_generated=tokens_generated,
                mode=strategy,
                template_name=state.get("dag_template_id"),
                conversation_id=session_id,
                request_id=request_id,
                # 性能监控字段（unified-observability-dashboard）
                ttfb_ms=int(ttfb_ms) if ttfb_ms is not None else 0,
                duration_ms=int(processing_time * 1000),
                backend_used=state.get("backend_used", "unknown"),
                fallback_count=state.get("fallback_count", 0),
                error_type="",
            )

            # 发送完成事件
            yield {
                "type": "done",
                "data": {
                    "request_id": request_id,
                    "processing_time": processing_time,
                    "ttfb_ms": ttfb_ms,
                    "tokens_generated": tokens_generated,
                    "content_length": content_length,
                    "interaction_logged": state.get("interaction_logged", False),
                    "three_track_rating": state.get("three_track_rating"),
                    "personalization_grade": state.get("personalization_grade"),
                    "fewshot_eligible": state.get("fewshot_eligible", False),
                    "topic_id": state.get("topic_id"),
                    "conversation_turn": state.get("conversation_turn", 1),
                    "context_was_compressed": state.get("context_was_compressed", False),
                    "web_search_used": state.get("web_search_triggered", False),
                }
            }

            logger.info(
                f"🎉 [{request_id}] 流式工作流执行成功! "
                f"耗时: {processing_time:.2f}秒, "
                f"TTFB: {f'{ttfb_ms:.0f}ms' if ttfb_ms is not None else 'N/A'}, "
                f"tokens: {tokens_generated}, "
                f"grade: {state.get('personalization_grade', 'N/A')}"
            )

        except Exception as e:  # 需要宽泛捕获：主工作流顶层错误边界，确保所有异常都返回错误响应
            processing_time = time.time() - start_time
            logger.error(f"❌ [{request_id}] 流式工作流执行失败: {e}", exc_info=True)

            # 记录失败
            if self.streaming_monitor:
                self.streaming_monitor.record_stream_error(str(e))
                self.streaming_monitor.decrement_active_connections()

            if self.performance_monitor and perf_context:
                self.performance_monitor.finish_workflow(
                    context=perf_context,
                    success=False,
                    total_duration_ms=processing_time * 1000
                )

            yield {
                "type": "error",
                "error": str(e),
                "request_id": request_id
            }

    async def _execute_steps_1_2(self, state: WorkflowState) -> WorkflowState:
        """执行步骤1-2（并行）"""
        from .nodes import node_preload_user_profile, node_store_session

        backend_client = self._get_backend_client()
        cache_manager = self._get_cache_manager()
        user_cache = self._get_user_cache()

        # 并行执行
        results = await asyncio.gather(
            node_preload_user_profile(
                state,
                backend_client=backend_client,
                cache_manager=cache_manager,
                user_cache=user_cache
            ),
            node_store_session(state, conversation_memory=self.conversation_memory),
            return_exceptions=True
        )

        # 合并结果
        for result in results:
            if isinstance(result, StateUpdate):
                state = result.merge_into(state)
            elif isinstance(result, Exception):
                state["errors"] = state.get("errors", []) + [str(result)]

        return state

    async def _execute_steps_3_4(self, state: WorkflowState) -> WorkflowState:
        """执行步骤3-4（并行）"""
        from .nodes import node_check_membership, node_classify_complexity

        backend_client = self._get_backend_client()
        cache_manager = self._get_cache_manager()
        membership_cache = self._get_membership_cache()

        # 并行执行
        results = await asyncio.gather(
            node_check_membership(
                state,
                backend_client=backend_client,
                cache_manager=cache_manager,
                membership_cache=membership_cache
            ),
            node_classify_complexity(
                state,
                cache_manager=cache_manager
            ),
            return_exceptions=True
        )

        # 合并结果
        for result in results:
            if isinstance(result, StateUpdate):
                state = result.merge_into(state)
            elif isinstance(result, Exception):
                state["errors"] = state.get("errors", []) + [str(result)]

        return state

    async def _execute_step_5(self, state: WorkflowState) -> WorkflowState:
        """执行步骤5"""
        from .nodes import node_select_model

        result = await node_select_model(state)
        if isinstance(result, StateUpdate):
            state = result.merge_into(state)

        return state

    async def _execute_step_6(self, state: WorkflowState) -> WorkflowState:
        """执行步骤6"""
        from .nodes import node_retrieve_few_shot

        backend_client = self._get_backend_client()
        cache_manager = self._get_cache_manager()

        result = await node_retrieve_few_shot(
            state,
            backend_client=backend_client,
            cache_manager=cache_manager
        )
        if isinstance(result, StateUpdate):
            state = result.merge_into(state)

        return state

    async def _execute_step_6_5(self, state: WorkflowState) -> WorkflowState:
        """执行步骤6.5"""
        from .nodes import node_select_dag_template
        cache_manager = self._get_cache_manager()
        result = await node_select_dag_template(state, cache_manager=cache_manager)
        if isinstance(result, StateUpdate):
            state = result.merge_into(state)

        return state

    async def _execute_steps_7_8(self, state: WorkflowState) -> WorkflowState:
        """执行步骤7-8（支持 DAG 固定编排 / Agent 动态决策）"""
        strategy = state.get("strategy", "dag")

        if strategy == "agent":
            return await self._execute_steps_7_8_agent(state)

        return await self._execute_steps_7_8_dag(state)

    async def _execute_steps_7_8_dag(self, state: WorkflowState) -> WorkflowState:
        """步骤7-8: DAG 固定编排模式"""
        from .nodes import node_execute_dag, node_retrieve_context
        from .singletons import get_mcp_orchestrator, get_hybrid_search_engine, get_cypher_executor

        # 获取MCP编排器
        mcp_orchestrator = get_mcp_orchestrator()

        # 执行DAG
        result = await node_execute_dag(state, mcp_tool_manager=mcp_orchestrator)
        if isinstance(result, StateUpdate):
            state = result.merge_into(state)

        # 如果DAG失败，执行意图路由检索（Phase 4C）
        if not state.get("dag_results"):
            result = await node_retrieve_context(
                state,
                hybrid_search_engine=get_hybrid_search_engine(),
                cypher_executor=get_cypher_executor(),
            )
            if isinstance(result, StateUpdate):
                state = result.merge_into(state)

        return state

    async def _execute_steps_7_8_agent(self, state: WorkflowState) -> WorkflowState:
        """步骤7-8: Agent 动态决策模式（LangGraph tool-calling loop）"""
        from .nodes import node_retrieve_context
        from .singletons import get_hybrid_search_engine, get_cypher_executor

        request_id = state.get("request_id", "?")
        logger.info(f"🤖 [{request_id}] 步骤7-8: Agent模式执行")

        try:
            from ..agent.executor import create_agent_executor_from_singletons
            agent_executor = create_agent_executor_from_singletons()

            # 从管线 state 提取 Agent 所需参数
            agent_result = await agent_executor.execute(
                user_id=state.get("user_id", ""),
                query=state.get("query_text", ""),
                user_profile=state.get("user_profile"),
                conversation_history=state.get("conversation_history"),
                membership_level=state.get("membership_info", {}).get("tier", "free") if isinstance(state.get("membership_info"), dict) else "free",
            )

            # 将 Agent tool_results 转换为 dag_results 格式
            # Agent 返回 [{tool_name, result, ...}]，DAG 期望 {tool_name: result}
            dag_results = {}
            for tr in agent_result.get("tool_results", []):
                tool_name = tr.get("tool_name") or tr.get("name", "unknown")
                dag_results[tool_name] = tr.get("result", tr)

            state["dag_results"] = dag_results
            state["_agent_response"] = agent_result.get("final_response")
            state["_agent_tool_calls_count"] = agent_result.get("tool_calls_count", 0)
            state["_agent_skills_loaded"] = agent_result.get("skills_loaded", [])

            logger.info(
                f"🤖 [{request_id}] Agent完成: "
                f"tools={agent_result.get('tool_calls_count', 0)}, "
                f"skills={agent_result.get('skills_loaded', [])}"
            )

        except Exception as e:
            logger.error(f"🤖 [{request_id}] Agent执行失败，降级到检索: {e}")
            # Agent 失败时降级到检索
            result = await node_retrieve_context(
                state,
                hybrid_search_engine=get_hybrid_search_engine(),
                cypher_executor=get_cypher_executor(),
            )
            if isinstance(result, StateUpdate):
                state = result.merge_into(state)

        return state

    async def _execute_step_9(self, state: WorkflowState) -> WorkflowState:
        """执行步骤9"""
        from .nodes import node_aggregate_data

        result = await node_aggregate_data(state)
        if isinstance(result, StateUpdate):
            state = result.merge_into(state)

        return state

    async def _execute_step_11(self, state: WorkflowState) -> WorkflowState:
        """执行步骤11"""
        from .nodes import node_log_interaction

        backend_client = self._get_backend_client()

        result = await node_log_interaction(
            state,
            backend_client=backend_client
        )
        if isinstance(result, StateUpdate):
            state = result.merge_into(state)

        return state
