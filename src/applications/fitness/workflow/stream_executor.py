# -*- coding: utf-8 -*-
"""
流式工作流执行器模块

执行工作流图，支持流式输出。
步骤1-9保持同步执行，步骤10改为流式LLM调用。
集成 StreamingMetrics 进行流式监控。
集成 ContextEngineering 进行多轮对话上下文管理。

版本: v1.1.0
日期: 2025-12-31

主要类:
- StreamWorkflowExecutor: 流式工作流执行器

更新记录:
- v1.1.0: 集成上下文工程模块（Requirements 8.1-8.5）
"""

import logging
import time
import uuid
import asyncio
import httpx
from typing import Dict, Any, Optional, AsyncGenerator

from .state import (
    WorkflowState,
    StateUpdate,
    create_initial_state,
)
from .graph import WorkflowGraph, get_default_graph
from .executor import WorkflowExecutor

# 导入上下文工程模块
from ..context import (
    ContextEngineering,
    ContextConfig,
    ContextResult,
)

logger = logging.getLogger(__name__)


class StreamWorkflowExecutor(WorkflowExecutor):
    """
    流式工作流执行器
    
    继承自 WorkflowExecutor，添加流式输出支持。
    步骤1-9同步执行，步骤10流式输出。
    
    集成上下文工程模块（Requirements 8.1-8.5）：
    - 对话历史管理（滑动窗口）
    - Token智能压缩
    - 用户档案自动注入
    - 话题切换逻辑
    """
    
    def __init__(
        self,
        graph: Optional[WorkflowGraph] = None,
        enable_monitoring: bool = True,
        enable_performance: bool = True,
        enable_streaming_metrics: bool = True,
        enable_context_engineering: bool = True,
        context_config: Optional[ContextConfig] = None,
    ):
        """
        初始化流式执行器
        
        Args:
            graph: 工作流图
            enable_monitoring: 是否启用工作流监控
            enable_performance: 是否启用性能监控
            enable_streaming_metrics: 是否启用流式监控
            enable_context_engineering: 是否启用上下文工程
            context_config: 上下文工程配置
        """
        super().__init__(
            graph=graph,
            enable_monitoring=enable_monitoring,
            enable_performance=enable_performance
        )
        self.enable_streaming_metrics = enable_streaming_metrics
        self._streaming_monitor = None
        
        # 上下文工程（Requirements 8.1-8.5）
        self.enable_context_engineering = enable_context_engineering
        self._context_engine: Optional[ContextEngineering] = None
        self._context_config = context_config
    
    @property
    def streaming_monitor(self):
        """获取流式监控器"""
        if self._streaming_monitor is None and self.enable_streaming_metrics:
            from ....framework.monitoring.streaming_metrics import streaming_monitor
            self._streaming_monitor = streaming_monitor
        return self._streaming_monitor
    
    @property
    def context_engine(self) -> Optional[ContextEngineering]:
        """
        获取上下文工程实例（懒加载）
        
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
        """
        if self._context_engine is None and self.enable_context_engineering:
            try:
                backend_client = self._get_backend_client()
                llm_client = self._get_llm_client()
                
                self._context_engine = ContextEngineering(
                    config=self._context_config,
                    backend_client=backend_client,
                    llm_client=llm_client,
                )
                logger.info("上下文工程模块初始化成功")
            except (ImportError, AttributeError, TypeError, ConnectionError) as e:
                logger.warning(f"上下文工程模块初始化失败: {e}")
                self._context_engine = None
        return self._context_engine
    
    def _get_llm_client(self):
        """获取LLM客户端（懒加载）"""
        try:
            from ....framework.clients.llm_client import get_llm_client
            return get_llm_client()
        except (ImportError, AttributeError) as e:
            logger.warning(f"获取LLM客户端失败: {e}")
            return None
    
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
        
        # ========== 策略分流：Agent模式使用 LangGraph 执行器 ==========
        if strategy == "agent":
            logger.info(f"🤖 [{request_id}] 使用Agent模式执行（LangGraph + Skills）")
            from ..agent import create_agent_executor_from_singletons

            try:
                agent_executor = create_agent_executor_from_singletons()

                # 构建对话历史（上下文工程）
                conversation_history = []
                if self.context_engine:
                    try:
                        context_result = await self.context_engine.build_context(
                            user_id=str(user_id),
                            message=query_text,
                            topic_id=topic_id,
                            user_profile=user_profile,
                        )
                        conversation_history = [
                            {"role": h.get("role", "user"), "content": h.get("content", "")}
                            for h in (context_result.conversation_history or [])
                        ]
                    except (RuntimeError, ValueError, ConnectionError, TimeoutError) as e:
                        logger.warning(f"[{request_id}] Agent上下文构建失败: {e}")

                yield {"type": "step", "step": 1, "message": "Agent模式初始化..."}
                yield {"type": "step", "step": 2, "message": "AI正在分析您的需求..."}

                agent_result = await agent_executor.execute(
                    user_id=user_id,
                    query=query_text,
                    user_profile=user_profile,
                    conversation_history=conversation_history,
                    membership_level=kwargs.get("membership_level", "free"),
                )

                # 发送结构化数据
                yield {
                    "type": "structured_data",
                    "data": {
                        "mode": "agent",
                        "skills_loaded": agent_result.get("skills_loaded", []),
                        "tool_calls": [
                            r.get("tool") for r in agent_result.get("tool_results", [])
                        ],
                    },
                }

                # 流式发送最终响应（分块模拟打字效果）
                final_response = agent_result.get("final_response") or "抱歉，暂时无法生成回答。"
                yield {"type": "step", "step": 10, "message": "生成专业建议..."}

                chunk_size = 20
                tokens_generated = 0
                for i in range(0, len(final_response), chunk_size):
                    chunk = final_response[i : i + chunk_size]
                    tokens_generated += len(chunk)
                    yield {"type": "chunk", "content": chunk, "tokens": tokens_generated}

                processing_time = agent_result.get("total_time_s", 0.0)
                yield {
                    "type": "done",
                    "data": {
                        "request_id": request_id,
                        "processing_time": processing_time,
                        "mode": "agent",
                        "skills_loaded": agent_result.get("skills_loaded", []),
                        "tool_calls_count": agent_result.get("tool_calls_count", 0),
                        "tokens_generated": tokens_generated,
                    },
                }

                logger.info(
                    f"✅ [{request_id}] Agent模式完成: "
                    f"skills={agent_result.get('skills_loaded', [])}, "
                    f"tools={agent_result.get('tool_calls_count', 0)}, "
                    f"time={processing_time:.2f}s"
                )

            except Exception as e:  # 需要宽泛捕获：Agent模式顶层错误边界，确保所有异常都返回错误响应
                logger.error(f"❌ [{request_id}] Agent模式执行失败: {e}", exc_info=True)
                yield {"type": "error", "error": str(e), "request_id": request_id}

            # Agent模式执行完毕，增加用量计数（Requirements 7.4）
            await self._increment_usage_after_execute(
                user_id=user_id,
                strategy=strategy,
                request_id=request_id
            )
            return
        
        # ========== DAG模式：继续原有的11步工作流程 ==========
        logger.info(f"📊 [{request_id}] 使用DAG模式执行")
        
        # ========== 上下文工程：构建对话上下文 ==========
        context_result: Optional[ContextResult] = None
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
                request_id=request_id
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
        
        result = await node_select_dag_template(state)
        if isinstance(result, StateUpdate):
            state = result.merge_into(state)
        
        return state
    
    async def _execute_steps_7_8(self, state: WorkflowState) -> WorkflowState:
        """执行步骤7-8"""
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
    
    async def _execute_step_9(self, state: WorkflowState) -> WorkflowState:
        """执行步骤9"""
        from .nodes import node_aggregate_data
        
        result = await node_aggregate_data(state)
        if isinstance(result, StateUpdate):
            state = result.merge_into(state)
        
        return state
    
    async def _execute_step_10_stream(
        self,
        state: WorkflowState
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行步骤10
        
        集成上下文工程：将对话历史传递给LLM
        
        Args:
            state: 当前状态
            
        Yields:
            LLM生成的内容块
        """
        request_id = state.get("request_id", "unknown")
        query_text = state.get("query_text", "")
        selected_template_id = state.get("dag_template_id", "default")
        user_profile = state.get("user_profile")
        aggregated_data = state.get("aggregated_data", {})
        few_shot_examples = state.get("few_shot_examples", [])

        # 获取对话历史（上下文工程）
        conversation_history = state.get("conversation_history", [])

        # 获取附件（multimodal）
        attachments = state.get("attachments") or []
        has_images = attachments and any(
            a.get("mime_type", "").startswith("image/") or a.get("type") == "image"
            for a in attachments
        )
        
        try:
            # 初始化配置管理器
            from ....framework.config.llm_response_config_manager import LLMResponseConfigManager
            config_manager = LLMResponseConfigManager()
            
            # 获取模板配置
            llm_response_config = config_manager.get_config(selected_template_id)
            
            # 从DAG模板获取response_hint
            from ..dag_template_system import DAGTemplateManager
            template_manager = DAGTemplateManager()
            selected_template = template_manager.get_template(selected_template_id)
            response_hint = selected_template.response_hint if selected_template else "请提供专业的分析和建议"
            
            # 准备用户档案字符串
            import json
            user_profile_for_prompt = '未提供'
            if user_profile:
                try:
                    serializable_profile = {
                        k: v for k, v in user_profile.items()
                        if isinstance(v, (str, int, float, bool, list, dict, type(None)))
                    }
                    user_profile_for_prompt = json.dumps(serializable_profile, ensure_ascii=False)
                except (TypeError, ValueError):
                    user_profile_for_prompt = str(user_profile)
            
            # 准备MCP工具结果字符串
            mcp_tools_result_str = '无MCP工具结果'
            if aggregated_data:
                try:
                    # 只提取MCP工具的结果，排除工作流元数据
                    mcp_results = {}
                    for key, value in aggregated_data.items():
                        if not key.startswith('_') and key not in ['workflow_metadata', 'retrieval_results']:
                            # 处理特殊对象类型（如MembershipPermissions）
                            mcp_results[key] = self._make_json_serializable(value)
                    if mcp_results:
                        mcp_tools_result_str = json.dumps(mcp_results, ensure_ascii=False, indent=2)
                except (TypeError, ValueError) as e:
                    logger.warning(f"序列化MCP工具结果失败: {e}")
                    mcp_tools_result_str = str(aggregated_data)
            
            # 构建提示词（三层组装：Persona + Task + Rendering）
            retrieval_results = state.get("retrieval_results") or {}
            persona_id = state.get("persona_id")  # 从请求传入
            system_prompt = config_manager.build_prompt(
                template_id=selected_template_id,
                persona_id=persona_id,
                query=query_text,
                user_profile=user_profile_for_prompt,
                response_hint=response_hint,
                mcp_tools_count=len(state.get("_mcp_tools_called", [])),
                retrieval_count=len(retrieval_results.get('results', [])),
                mcp_tools_result=mcp_tools_result_str
            )

            # 注入跨对话记忆到 system_prompt
            user_memory_text = state.get("user_memory_text", "")
            if user_memory_text:
                system_prompt = f"{system_prompt}\n\n{user_memory_text}"

            # ========== Layer4: WebSearch 兜底 ==========
            retrieval_results = state.get("retrieval_results") or {}
            try:
                from ...fitness.services.web_search import (
                    should_web_search, web_search_fallback, format_web_results_for_prompt
                )
                if should_web_search(query_text, retrieval_results):
                    web_results = await web_search_fallback(query_text)
                    if web_results:
                        web_text = format_web_results_for_prompt(web_results)
                        system_prompt = f"{system_prompt}\n{web_text}"
                        state["web_search_triggered"] = True
                        state["web_search_results"] = web_results
                        logger.info(f"🔍 [{request_id}] WebSearch注入: {len(web_results)}条结果")
            except (ImportError, ConnectionError, TimeoutError, httpx.HTTPError) as ws_err:
                logger.debug(f"[{request_id}] WebSearch跳过: {ws_err}")

            # ========== TokenBudgetManager: 统一预算控制 ==========
            try:
                from ...fitness.context.token_budget_manager import TokenBudgetManager, estimate_tokens
                import json as _json

                budget_mgr = TokenBudgetManager()
                # 将各组件文本传入预算管理器
                budget_components = {
                    "system_prompt": system_prompt,  # persona + task + rendering + memory + websearch
                    "conversation_history": _json.dumps(
                        conversation_history, ensure_ascii=False
                    ) if conversation_history else "",
                    "few_shot_examples": _json.dumps(
                        [{"query": ex["query"], "response": ex["response"]} for ex in few_shot_examples],
                        ensure_ascii=False,
                    ) if few_shot_examples else "",
                    "current_message": query_text,
                }
                # 重新映射：system_prompt 包含多个子组件，按 task_instruction 限额管理
                budget_components_mapped = {
                    "task_instruction": system_prompt,
                    "conversation_history": budget_components["conversation_history"],
                    "few_shot_examples": budget_components["few_shot_examples"],
                    "current_message": query_text,
                }
                budget_result = budget_mgr.allocate(budget_components_mapped)

                if budget_result.over_budget:
                    logger.warning(
                        f"⚠️ [{request_id}] Token预算仍超限: "
                        f"{budget_result.total_tokens}/{budget_result.budget}"
                    )

                # 应用压缩结果
                system_prompt = budget_result.get_text("task_instruction")

                # 压缩对话历史：按比例截断条数
                conv_alloc = budget_result.allocations.get("conversation_history")
                if conv_alloc and conv_alloc.compressed and conversation_history:
                    ratio = conv_alloc.allocated_tokens / max(conv_alloc.original_tokens, 1)
                    keep_count = max(2, int(len(conversation_history) * ratio))
                    conversation_history = conversation_history[-keep_count:]
                    logger.info(
                        f"📦 [{request_id}] 对话历史压缩: "
                        f"{conv_alloc.original_tokens}→{conv_alloc.allocated_tokens} tokens, "
                        f"保留最近 {keep_count} 条"
                    )

                # 压缩 few_shot：按比例截断条数
                fs_alloc = budget_result.allocations.get("few_shot_examples")
                if fs_alloc and fs_alloc.compressed and few_shot_examples:
                    ratio = fs_alloc.allocated_tokens / max(fs_alloc.original_tokens, 1)
                    keep_count = max(1, int(len(few_shot_examples) * ratio))
                    few_shot_examples = few_shot_examples[-keep_count:]

            except (ImportError, ValueError, KeyError) as budget_err:
                logger.debug(f"[{request_id}] TokenBudgetManager跳过: {budget_err}")

            # 初始化LLM降级管理器（根据模板路由选择后端）
            from ....framework.clients.llm_fallback_manager import LLMFallbackManager, LLMRequest
            from ...fitness.config.model_routing import get_backend_for_template, PoolEntry

            routed = get_backend_for_template(selected_template_id)
            model_override = None  # 蓝绿池模型覆盖
            pool_meta = None  # 蓝绿池元数据（用于DAML-Eval）

            if isinstance(routed, PoolEntry):
                # YAML蓝绿池返回完整条目
                pool_meta = {
                    "model_id": routed.model,
                    "cost_tier": routed.cost_tier,
                    "backend": routed.backend,
                }
                model_override = routed.model
                fallback_manager = LLMFallbackManager(
                    primary_backend=routed.backend,
                    fallback_backends=["anthropic", "deepseek", "template"],
                    max_retries=3,
                    timeout=30,
                    enable_health_check=True
                )
                logger.info(
                    f"🔀 [{request_id}] 步骤10: 蓝绿池 {selected_template_id} → "
                    f"{routed.backend}/{routed.model} (tier={routed.cost_tier})"
                )
            elif routed:
                # 固定覆盖或环境变量池（返回字符串）
                fallback_manager = LLMFallbackManager(
                    primary_backend=routed,
                    fallback_backends=["anthropic", "deepseek", "template"],
                    max_retries=3,
                    timeout=30,
                    enable_health_check=True
                )
                logger.info(
                    f"🔀 [{request_id}] 步骤10: 模板路由 {selected_template_id} → {routed}"
                )
            else:
                # 未配置路由，走默认降级链
                fallback_manager = LLMFallbackManager(
                    primary_backend="anthropic",
                    fallback_backends=["deepseek", "template"],
                    max_retries=3,
                    timeout=30,
                    enable_health_check=True
                )
            
            # 准备LLM请求
            few_shot_dicts = [{"query": ex["query"], "response": ex["response"]} for ex in few_shot_examples]
            
            # 构建LLM请求（包含对话历史 + 蓝绿池模型覆盖）
            llm_request = LLMRequest(
                query=query_text,
                few_shot_examples=few_shot_dicts,
                tool_results=aggregated_data,
                system_prompt=system_prompt,
                max_tokens=llm_response_config.max_tokens,
                temperature=llm_response_config.temperature,
                stream=True,  # 启用流式
                conversation_history=conversation_history,  # 传递对话历史
                model_override=model_override,  # 蓝绿池指定模型
            )
            
            # 记录对话历史信息
            if conversation_history:
                logger.info(
                    f"📚 [{request_id}] 步骤10: 携带{len(conversation_history)}条对话历史"
                )

            # ========== Vision 分支：有图片时构建 multimodal messages ==========
            if has_images:
                try:
                    from ...fitness.services.vision_message_builder import VisionMessageBuilder
                    from ...fitness.config.model_routing import _load_yaml_pool, PoolEntry as VisionPoolEntry

                    vision_builder = VisionMessageBuilder()
                    vision_messages = vision_builder.build_messages(
                        query=query_text,
                        attachments=attachments,
                        system_prompt=system_prompt,
                        conversation_history=conversation_history,
                    )
                    # 用 multimodal messages 覆盖 LLMRequest
                    llm_request.messages = vision_messages
                    llm_request.conversation_history = None  # 已包含在 messages 中

                    # 从 Vision 蓝绿池选模型（独立于文本池）
                    import yaml
                    from pathlib import Path
                    vision_pool_path = Path(__file__).resolve().parents[4] / "config" / "vision_model_pool.yaml"
                    if vision_pool_path.exists():
                        import random
                        with open(vision_pool_path, "r", encoding="utf-8") as f:
                            vp_data = yaml.safe_load(f)
                        if vp_data and vp_data.get("enabled") and vp_data.get("pool"):
                            vp_entries = vp_data["pool"]
                            weights = [e.get("weight", 10) for e in vp_entries]
                            chosen_v = random.choices(vp_entries, weights=weights, k=1)[0]
                            llm_request.model_override = chosen_v["model"]
                            # 重建 fallback_manager 使用 vision 后端
                            fallback_manager = LLMFallbackManager(
                                primary_backend=chosen_v["backend"],
                                fallback_backends=["anthropic", "deepseek", "template"],
                                max_retries=3,
                                timeout=60,  # Vision 调用给更长超时
                                enable_health_check=True,
                            )
                            pool_meta = {
                                "model_id": chosen_v["model"],
                                "cost_tier": chosen_v.get("cost_tier", "free"),
                                "backend": chosen_v["backend"],
                                "vision": True,
                            }
                            logger.info(
                                f"🖼️ [{request_id}] Vision模式: "
                                f"{chosen_v['backend']}/{chosen_v['model']} "
                                f"(images={len(attachments)})"
                            )
                except (ImportError, KeyError, ValueError, ConnectionError) as ve:
                    logger.warning(f"[{request_id}] Vision分支初始化失败，回退文本模式: {ve}")

            # 流式调用LLM
            async for chunk, response in fallback_manager.call_with_fallback_stream(llm_request):
                if chunk:  # 只处理非空的chunk
                    yield {"content": chunk}
                if response:
                    # 捕获 backend_used + 蓝绿池元数据供 DAML-Eval 使用
                    meta = {"_backend_used": response.backend_used.value}
                    if pool_meta:
                        meta["_pool_meta"] = pool_meta
                    yield meta

            logger.info(f"✅ [{request_id}] 步骤10完成: 流式LLM生成完成")
            
        except Exception as e:  # 需要宽泛捕获：步骤10顶层错误边界，确保LLM生成失败时返回降级响应
            logger.error(f"❌ [{request_id}] 步骤10: 流式LLM生成异常: {e}")

            # 生成降级响应
            fallback_response = f"抱歉，AI分析功能暂时不可用。\n\n您的查询：{query_text}\n\n请稍后重试。"
            yield {"content": fallback_response}
    
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
    
    async def _execute_step_12_three_track_rating(self, state: WorkflowState) -> WorkflowState:
        """
        执行步骤12：三轨评分
        
        在LLM翻译完成后执行：
        1. 自动计算个性化感知评分
        2. 检查Few-Shot准入资格
        3. 高评分对话自动导入Few-Shot库
        
        Requirements: 3.7, 3.8
        """
        request_id = state.get("request_id", "unknown")
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        user_query = state.get("query_text", "")
        final_response = state.get("final_response", "")
        user_profile = state.get("user_profile")
        tools_used = state.get("_mcp_tools_called", [])
        
        try:
            logger.info(f"🎯 [{request_id}] 步骤12: 开始三轨评分")
            
            # 导入三轨评分服务
            from ..services.three_track_rating import ThreeTrackRatingService
            
            # 获取后端客户端和Qdrant客户端
            backend_client = self._get_backend_client()
            qdrant_client = self._get_qdrant_client()
            
            # 创建三轨评分服务
            rating_service = ThreeTrackRatingService(
                backend_client=backend_client,
                qdrant_client=qdrant_client
            )
            
            # 构建元数据
            metadata = {
                'dag_template_id': state.get("dag_template_id"),
                'complexity_level': state.get("complexity_level"),
                'few_shot_count': len(state.get("few_shot_examples", [])),
                'context_used': state.get("context_used", False),
                'conversation_turn': state.get("conversation_turn", 1),
                'backend_used': state.get("backend_used"),
            }
            
            # 处理三轨评分
            rating_result = await rating_service.process_rating(
                session_id=session_id or request_id,
                user_id=str(user_id) if user_id else "anonymous",
                user_query=user_query,
                llm_response=final_response,
                user_profile=user_profile,
                tools_used=tools_used,
                metadata=metadata
            )
            
            # 将评分结果存入状态
            state["three_track_rating"] = rating_result.to_dict()
            state["personalization_grade"] = rating_result.personalization_grade.value
            state["fewshot_eligible"] = rating_result.fewshot_eligible
            
            # 如果有后端客户端，提交评分到后端
            if backend_client and session_id:
                try:
                    await backend_client.submit_three_track_rating(
                        session_id=session_id,
                        personalization_scores=rating_result.personalization.to_dict(),
                        personalization_grade=rating_result.personalization_grade.value,
                        fewshot_eligible=rating_result.fewshot_eligible,
                        eligibility_reason=rating_result.eligibility_reason,
                        overall_score=rating_result.overall_score
                    )
                except (httpx.HTTPError, ConnectionError, TimeoutError) as e:
                    logger.warning(f"[{request_id}] 提交三轨评分到后端失败: {e}")
            
            logger.info(
                f"✅ [{request_id}] 步骤12完成: "
                f"grade={rating_result.personalization_grade.value}, "
                f"eligible={rating_result.fewshot_eligible}"
            )
            
        except (ImportError, ValueError, RuntimeError, ConnectionError, TimeoutError) as e:
            logger.error(f"❌ [{request_id}] 步骤12: 三轨评分异常: {e}")
            # 不影响主流程，记录错误但继续
            state["three_track_rating"] = {
                'error': str(e),
                'fewshot_eligible': False
            }
        
        return state
    
    def _get_qdrant_client(self):
        """获取Qdrant客户端（懒加载）"""
        try:
            from ....framework.clients.qdrant_client import get_qdrant_client
            return get_qdrant_client()
        except (ImportError, ConnectionError) as e:
            logger.warning(f"获取Qdrant客户端失败: {e}")
            return None
    
    # ============ 权限检查方法（Requirements 7.1, 7.4） ============
    
    async def _check_permission_before_execute(
        self,
        user_id: str,
        strategy: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        执行前检查权限
        
        Requirements: 7.1, 7.2, 7.3
        
        Args:
            user_id: 用户ID
            strategy: 执行策略（dag或agent）
            request_id: 请求ID
            
        Returns:
            Dict[str, Any]: 权限检查结果
        """
        try:
            # 获取权限检查器
            from ....framework.auth.permission_checker import get_permission_checker
            permission_checker = get_permission_checker()
            
            # 如果权限检查器没有后端客户端，尝试设置
            if permission_checker.backend_client is None:
                backend_client = self._get_backend_client()
                if backend_client:
                    permission_checker.backend_client = backend_client
            
            # 检查权限
            result = await permission_checker.check_permission(
                user_id=int(user_id) if user_id.isdigit() else 0,
                mode=strategy
            )
            
            if result.allowed:
                logger.info(
                    f"✅ [{request_id}] 权限检查通过: "
                    f"user_id={user_id}, tier={result.tier}, "
                    f"remaining={result.remaining}"
                )
                return {
                    "allowed": True,
                    "tier": result.tier,
                    "remaining": result.remaining,
                    "message": result.message
                }
            else:
                logger.warning(
                    f"⚠️ [{request_id}] 权限检查失败: "
                    f"user_id={user_id}, message={result.message}"
                )
                return {
                    "allowed": False,
                    "tier": result.tier,
                    "remaining": result.remaining,
                    "message": result.message,
                    "upgrade_hint": result.upgrade_hint
                }
                
        except (ImportError, httpx.HTTPError, ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"❌ [{request_id}] 权限检查异常: {e}")
            # 权限检查异常时，允许执行（避免阻塞用户）
            return {
                "allowed": True,
                "tier": "unknown",
                "remaining": -1,
                "message": f"权限检查异常，暂时允许执行: {e}"
            }
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """
        将对象转换为JSON可序列化格式
        
        处理特殊对象类型（如MembershipPermissions、dataclass等）
        
        Args:
            obj: 要转换的对象
            
        Returns:
            JSON可序列化的对象
        """
        # 基本类型直接返回
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        
        # 列表递归处理
        if isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        
        # 字典递归处理
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        
        # 有to_dict方法的对象（如MembershipPermissions、UserProfile等）
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return obj.to_dict()
        
        # 有__dict__属性的对象
        if hasattr(obj, '__dict__'):
            return {k: self._make_json_serializable(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
        
        # 其他情况转为字符串
        return str(obj)
    
    async def _increment_usage_after_execute(
        self,
        user_id: str,
        strategy: str,
        request_id: str
    ) -> bool:
        """
        执行后增加用量计数
        
        Requirements: 7.4
        
        Args:
            user_id: 用户ID
            strategy: 执行策略（dag或agent）
            request_id: 请求ID
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取权限检查器
            from ....framework.auth.permission_checker import get_permission_checker
            permission_checker = get_permission_checker()
            
            # 如果权限检查器没有后端客户端，尝试设置
            if permission_checker.backend_client is None:
                backend_client = self._get_backend_client()
                if backend_client:
                    permission_checker.backend_client = backend_client
            
            # 增加用量
            success = await permission_checker.increment_usage(
                user_id=int(user_id) if user_id.isdigit() else 0,
                mode=strategy
            )
            
            if success:
                logger.info(
                    f"✅ [{request_id}] 用量增加成功: "
                    f"user_id={user_id}, mode={strategy}"
                )
            else:
                logger.warning(
                    f"⚠️ [{request_id}] 用量增加失败: "
                    f"user_id={user_id}, mode={strategy}"
                )
            
            return success
            
        except (ImportError, httpx.HTTPError, ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"❌ [{request_id}] 用量增加异常: {e}")
            return False
    
    async def _report_credit_consumption(
        self,
        user_id: str,
        tokens_generated: int,
        mode: str,
        template_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        request_id: str = "unknown"
    ) -> bool:
        """
        上报积分消耗到后端
        
        Requirements: 10.1
        
        在DAG工作流完成后调用，将Token消耗上报到后端进行积分扣除。
        使用try-except确保不阻塞主响应流程。
        
        Args:
            user_id: 用户ID
            tokens_generated: 生成的Token数量（作为总Token消耗的估算）
            mode: 执行模式（dag或agent）
            template_name: DAG模板名称
            conversation_id: 会话ID
            request_id: 请求ID（用于日志）
            
        Returns:
            bool: 是否成功
        """
        try:
            # 导入积分上报服务
            from ..services.credit_reporter import report_credit_consumption
            
            # 估算Token消耗（输出Token通常是主要消耗）
            # 实际项目中可以从LLM响应中获取精确的Token统计
            # 这里使用生成的Token数作为输出Token的估算
            # 输入Token估算为输出Token的0.3倍（经验值）
            output_tokens = tokens_generated
            input_tokens = int(tokens_generated * 0.3)
            total_tokens = input_tokens + output_tokens
            
            # 上报积分消耗
            result = await report_credit_consumption(
                user_id=int(user_id) if user_id.isdigit() else 0,
                tokens=total_tokens,
                mode=mode,
                template_name=template_name,
                conversation_id=conversation_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            if result.get("success"):
                credits = result.get("credits", 0)
                logger.info(
                    f"💰 [{request_id}] 积分上报成功: "
                    f"user_id={user_id}, credits={credits}, "
                    f"tokens={total_tokens}, mode={mode}, "
                    f"template={template_name}"
                )
                return True
            else:
                error = result.get("error", "未知错误")
                logger.warning(
                    f"⚠️ [{request_id}] 积分上报失败: "
                    f"user_id={user_id}, error={error}"
                )
                return False
                
        except (ImportError, httpx.HTTPError, ConnectionError, TimeoutError, ValueError) as e:
            # 积分上报失败不应阻塞主流程
            logger.error(
                f"❌ [{request_id}] 积分上报异常: {e}",
                exc_info=True
            )
            return False


# ============ 便捷函数 ============

async def execute_workflow_stream(
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
    流式执行工作流的便捷函数
    
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
        SSE事件
    """
    executor = StreamWorkflowExecutor()
    async for event in executor.execute_stream(
        query_text=query_text,
        user_id=user_id,
        domain=domain,
        user_profile=user_profile,
        session_id=session_id,
        topic_id=topic_id,
        strategy=strategy,
        **kwargs
    ):
        yield event


# ============ 导出 ============

__all__ = [
    "StreamWorkflowExecutor",
    "execute_workflow_stream",
]
