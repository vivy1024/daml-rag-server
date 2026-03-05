# -*- coding: utf-8 -*-
"""步骤10：LLM生成回答"""

import logging
import json
from typing import Dict, Any, Optional

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_llm_analysis(
    state: WorkflowState,
    config_manager=None,
    fallback_manager=None,
    template_manager=None
) -> StateUpdate:
    """
    步骤10：LLM生成最终回答（使用配置管理器）

    Args:
        state: 当前工作流状态
        config_manager: LLM响应配置管理器（可选）
        fallback_manager: LLM降级管理器（可选）
        template_manager: DAG模板管理器（可选）

    Returns:
        StateUpdate: 状态更新，包含 final_response
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    selected_template_id = state.get("dag_template_id", "default")
    user_profile = state.get("user_profile")
    aggregated_data = state.get("aggregated_data", {})
    few_shot_examples = state.get("few_shot_examples", [])
    dag_results = state.get("dag_results", {})
    mcp_tools_called = state.get("_mcp_tools_called", [])
    retrieval_results = state.get("retrieval_results") or {}
    conversation_history = state.get("conversation_history") or []

    try:
        # 1. 初始化配置管理器
        if config_manager is None:
            from .....framework.config.llm_response_config_manager import LLMResponseConfigManager
            config_manager = LLMResponseConfigManager()

        # 2. 获取模板配置
        llm_response_config = config_manager.get_config(selected_template_id)
        logger.info(f"   - 使用模板配置: {selected_template_id}")
        logger.info(f"   - max_tokens={llm_response_config.max_tokens}, temperature={llm_response_config.temperature}")

        # 3. 从DAG模板获取response_hint
        if template_manager is None:
            from ...dag_template_system import DAGTemplateManager
            template_manager = DAGTemplateManager()

        selected_template = template_manager.get_template(selected_template_id)
        response_hint = selected_template.response_hint if selected_template else "请提供专业的分析和建议"

        # 4. 准备用户档案字符串
        user_profile_for_prompt = '未提供'
        if user_profile:
            try:
                serializable_profile = {}
                for key, value in user_profile.items():
                    if key == 'membership' and hasattr(value, '__dict__'):
                        if hasattr(value, 'tier'):
                            serializable_profile['membership_tier'] = str(value.tier)
                    elif isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        serializable_profile[key] = value
                    else:
                        serializable_profile[key] = str(value)
                user_profile_for_prompt = json.dumps(serializable_profile, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"用户档案序列化失败: {e}")
                user_profile_for_prompt = str(user_profile)

        # 5. 准备MCP工具结果
        mcp_tools_result_json = "{}"
        if mcp_tools_called and dag_results:
            try:
                if "professional_program_designer" in dag_results:
                    program_result = dag_results["professional_program_designer"]
                    if program_result and not program_result.get("error"):
                        # 使用WeeklyPlanGenerator转换为单周输出
                        try:
                            from ...services.weekly_plan_generator import WeeklyPlanGenerator

                            weekly_generator = WeeklyPlanGenerator()
                            total_weeks = program_result.get("program_overview", {}).get("training_weeks", 4)

                            weekly_plan = weekly_generator.generate_first_week(
                                full_program=program_result,
                                user_profile=user_profile,
                                total_weeks=total_weeks
                            )

                            weekly_plan_output = weekly_generator.convert_to_output_format(weekly_plan)
                            program_result["weekly_plan_output"] = weekly_plan_output
                            program_result["output_mode"] = "weekly"

                        except Exception as weekly_gen_error:
                            logger.warning(f"分周计划生成失败: {weekly_gen_error}")
                            program_result["output_mode"] = "full"

                        mcp_tools_result_json = json.dumps(program_result, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"提取MCP工具结果失败: {e}")

        # 6. 构建提示词
        system_prompt = config_manager.build_prompt(
            template_id=selected_template_id,
            query=query_text,
            user_profile=user_profile_for_prompt,
            response_hint=response_hint,
            mcp_tools_count=len(mcp_tools_called),
            retrieval_count=len(retrieval_results.get('results', [])),
            mcp_tools_result=mcp_tools_result_json
        )

        # 6.1 追加知识库引用到 system_prompt
        knowledge_refs = retrieval_results.get("knowledge_refs", [])
        if knowledge_refs:
            refs_lines = ["", "---", "【知识库参考文献】"]
            for ref in knowledge_refs:
                title = ref.get("title", "")
                source_book = ref.get("source_book", "")
                chapter = ref.get("chapter", "")
                chapter_part = f" Ch.{chapter}" if chapter else ""
                refs_lines.append(f"[知识引用] {title} — {source_book}{chapter_part}")
            system_prompt = system_prompt + "\n".join(refs_lines)
            logger.info(f"   - 注入知识库引用: {len(knowledge_refs)} 条")

        logger.info(f"   - 提示词长度: {len(system_prompt)}字")

        # 7. 调用LLM
        if fallback_manager is None:
            from ..singletons import get_llm_degradation_manager
            fallback_manager = get_llm_degradation_manager()

        few_shot_dicts = [{"query": ex["query"], "response": ex["response"]} for ex in few_shot_examples]

        from .....framework.clients.llm_fallback_manager import LLMRequest
        llm_request = LLMRequest(
            query=query_text,
            few_shot_examples=few_shot_dicts,
            tool_results=aggregated_data,
            system_prompt=system_prompt,
            max_tokens=llm_response_config.max_tokens,
            temperature=llm_response_config.temperature,
            stream=False,
            conversation_history=conversation_history if conversation_history else None,
        )

        llm_response = await fallback_manager.call_with_fallback(llm_request)
        final_response = llm_response.content

        # 记录降级信息
        if llm_response.fallback_used:
            logger.warning(
                f"⚠️ [{request_id}] 步骤10: 使用了降级策略 "
                f"(backend={llm_response.backend_used.value})"
            )

        logger.info(
            f"✅ [{request_id}] 步骤10完成: LLM生成完成 "
            f"(backend={llm_response.backend_used.value}, "
            f"length={len(final_response)}字)"
        )

        return StateUpdate(updates={
            "final_response": final_response,
            "_llm_backend_used": llm_response.backend_used.value,
            "_llm_fallback_used": llm_response.fallback_used
        })

    except Exception as e:
        logger.error(f"❌ [{request_id}] 步骤10: LLM生成异常: {e}", exc_info=True)

        # 构建降级响应
        results_data = retrieval_results.get('results', []) if retrieval_results else []
        final_response = _build_fallback_response(
            query_text=query_text,
            user_profile=user_profile,
            results_data=results_data,
            error=str(e)
        )

        return StateUpdate(
            updates={"final_response": final_response},
            error=f"LLM生成异常: {str(e)}"
        )


def _build_fallback_response(
    query_text: str,
    user_profile: Optional[Dict[str, Any]],
    results_data: list,
    error: str
) -> str:
    """构建降级响应"""
    user_profile_summary = ""
    if user_profile:
        user_profile_summary = f"""
👤 **用户档案**：
- 年龄：{user_profile.get('age', '未知')}岁
- 训练经验：{user_profile.get('training_experience', '未知')}
- 训练目标：{user_profile.get('fitness_goal', '未知')}
"""

    retrieval_summary = ""
    if results_data:
        retrieval_summary = f"""
🔍 **检索结果**：找到 {len(results_data)} 个相关推荐
"""
        for i, item in enumerate(results_data[:3], 1):
            name = item.get('name_zh', item.get('name', '未知'))
            retrieval_summary += f"{i}. {name}\n"

    return f"""抱歉，AI分析功能暂时不可用（{error[:100]}）。

📝 **您的查询**：{query_text}
{user_profile_summary}
✅ **已完成以下数据分析**：
{retrieval_summary}

💡 **建议**：
- 请稍后重试获取AI分析
- 或联系客服获取人工指导

感谢您的理解！"""
