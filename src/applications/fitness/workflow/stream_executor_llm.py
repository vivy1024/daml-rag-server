# -*- coding: utf-8 -*-
"""
LLMStreamMixin: 流式 LLM 生成逻辑

从 StreamWorkflowExecutor 提取的步骤10流式LLM调用方法。

版本: v1.0.0
日期: 2026-03-05
"""

import logging
import httpx
from typing import Dict, Any, AsyncGenerator

from .state import WorkflowState

logger = logging.getLogger(__name__)


class LLMStreamMixin:
    """
    流式 LLM 生成 Mixin

    提供步骤10的流式LLM调用能力：
    - _execute_step_10_stream(): 流式LLM生成
    """

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

            # 准备MCP工具结果字符串（LLM摘要版，完整数据已通过structured_data发送给前端）
            mcp_tools_result_str = '无MCP工具结果'
            if aggregated_data:
                try:
                    from .tool_result_summarizer import summarize_for_llm

                    # 只提取MCP工具的结果，排除工作流元数据
                    mcp_results = {}
                    for key, value in aggregated_data.items():
                        if not key.startswith('_') and key not in ['workflow_metadata', 'retrieval_results']:
                            # 处理特殊对象类型（如MembershipPermissions）
                            serializable = self._make_json_serializable(value)
                            # 压缩为LLM摘要（大型工具结果如训练计划只保留核心参数）
                            mcp_results[key] = summarize_for_llm(key, serializable)
                    if mcp_results:
                        mcp_tools_result_str = json.dumps(mcp_results, ensure_ascii=False, indent=2)
                        logger.info(
                            f"📦 [{request_id}] MCP工具结果LLM摘要: "
                            f"{len(mcp_tools_result_str):,} chars "
                            f"(原始aggregated_data keys: {list(aggregated_data.keys())})"
                        )
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

            # ========== 蓝绿池模型选择（提前到预算控制之前） ==========
            from .singletons import get_llm_degradation_manager
            from ....framework.clients.llm_fallback_manager import LLMRequest
            from ...fitness.config.model_routing import get_backend_for_template, PoolEntry

            routed = get_backend_for_template(selected_template_id)
            model_override = None  # 蓝绿池模型覆盖
            pool_meta = None  # 蓝绿池元数据（用于DAML-Eval）
            routed_primary = None  # 路由覆盖的主后端
            routed_fallbacks = None  # 路由覆盖的降级链
            selected_context_window = None  # 选中模型的上下文窗口

            if isinstance(routed, PoolEntry):
                # YAML蓝绿池返回完整条目
                pool_meta = {
                    "model_id": routed.model,
                    "cost_tier": routed.cost_tier,
                    "backend": routed.backend,
                }
                model_override = routed.model
                routed_primary = routed.backend
                routed_fallbacks = ["anthropic", "deepseek", "template"]
                selected_context_window = routed.context_window
                logger.info(
                    f"🔀 [{request_id}] 步骤10: 蓝绿池 {selected_template_id} → "
                    f"{routed.backend}/{routed.model} (tier={routed.cost_tier}, "
                    f"ctx={routed.context_window})"
                )
            elif routed:
                # 固定覆盖或环境变量池（返回字符串）
                routed_primary = routed
                routed_fallbacks = ["anthropic", "deepseek", "template"]
                logger.info(
                    f"🔀 [{request_id}] 步骤10: 模板路由 {selected_template_id} → {routed}"
                )

            # ========== TokenBudgetManager: 统一预算控制 ==========
            try:
                from ...fitness.context.token_budget_manager import TokenBudgetManager, estimate_tokens
                import json as _json

                # 根据选中模型的 context_window 动态设定预算
                if selected_context_window:
                    dynamic_budget = int(selected_context_window * 0.6)
                    budget_mgr = TokenBudgetManager(total_budget=dynamic_budget)
                    logger.info(
                        f"📊 [{request_id}] 动态Token预算: "
                        f"context_window={selected_context_window} → budget={dynamic_budget}"
                    )
                else:
                    budget_mgr = TokenBudgetManager()  # 使用默认预算
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

            fallback_manager = get_llm_degradation_manager()

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
                            # Vision 路由覆盖（复用单例，通过参数覆盖后端）
                            routed_primary = chosen_v["backend"]
                            routed_fallbacks = ["anthropic", "deepseek", "template"]
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

            # 流式调用LLM（传入路由覆盖参数）
            async for chunk, response in fallback_manager.call_with_fallback_stream(
                llm_request,
                primary_backend=routed_primary,
                fallback_backends=routed_fallbacks,
            ):
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
