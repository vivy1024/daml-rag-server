# -*- coding: utf-8 -*-
"""
output_generate 节点 — 输出生成

职责：
- 如果有 direct_reply → 直接使用
- 否则：调用 OutputVerifierV2 校验
- 校验通过 → 构建综合 prompt，调用 LLM 生成最终回答
- 校验失败（critical）→ 生成降级回答
- 设置 state.final_output

版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any, Optional

from src.harness_v2.output_verifier import OutputVerifierV2, VerificationResult
from src.framework.models.llm_pool import LLMPoolManager
from ..state import AgentState

logger = logging.getLogger(__name__)

# 模块级依赖
_output_verifier: OutputVerifierV2 | None = None
_llm_pool: LLMPoolManager | None = None


def configure_output_generate(
    verifier: OutputVerifierV2,
    llm_pool: LLMPoolManager,
) -> None:
    """配置 output_generate 节点依赖

    Args:
        verifier: OutputVerifierV2 实例
        llm_pool: LLMPoolManager 实例
    """
    global _output_verifier, _llm_pool
    _output_verifier = verifier
    _llm_pool = llm_pool


SYNTHESIS_SYSTEM_PROMPT = """你是玉珍健身 AI 教练。
根据以下工具执行结果，为用户生成专业、友好、结构化的回答。
要求：
1. 使用中文回答
2. 结合用户档案个性化
3. 安全提示放在最前面
4. 数据引用要准确
"""

DEGRADED_RESPONSE_TEMPLATE = (
    "⚠️ 安全校验发现问题，为确保您的安全，以下建议仅供参考：\n\n"
    "建议您在开始训练前咨询专业教练或医生，确认动作适合您的身体状况。\n"
    "如需更详细的方案，请补充您的健康信息后重新咨询。"
)


async def output_generate(state: AgentState) -> Dict[str, Any]:
    """输出生成节点

    根据 Skill 执行结果生成最终输出：
    - 有 direct_reply → 直接使用
    - 有 tool_results → 校验后调用 LLM 综合
    - 校验失败（critical）→ 降级回答

    Args:
        state: 当前 Agent 状态

    Returns:
        状态更新字典（包含 final_output）
    """
    # 直接回复路径
    direct_reply = state.get("direct_reply")
    if direct_reply:
        logger.info("output_generate: 使用 direct_reply")
        return {"final_output": direct_reply}

    # 错误路径
    error = state.get("error")
    if error:
        logger.warning(f"output_generate: 存在错误，生成降级回答: {error}")
        return {"final_output": DEGRADED_RESPONSE_TEMPLATE}

    tool_results = state.get("tool_results") or {}
    current_skill = state.get("current_skill", "")
    user_profile = state.get("user_profile") or {}

    # OutputVerifier 校验
    verifier = _output_verifier or OutputVerifierV2()
    verification: VerificationResult = verifier.verify(
        skill_id=current_skill,
        tool_results=tool_results,
        user_profile=user_profile,
    )

    if verification.has_critical:
        logger.warning(
            f"output_generate: 校验发现 critical 问题，降级回答. "
            f"failures={[f.detail for f in verification.critical_failures]}"
        )
        return {"final_output": DEGRADED_RESPONSE_TEMPLATE}

    # 构建综合 prompt 调用 LLM
    final_output = await _generate_with_llm(
        tool_results=tool_results,
        user_profile=user_profile,
        skill_id=current_skill,
        messages=state.get("messages", []),
    )

    return {"final_output": final_output}


async def _generate_with_llm(
    tool_results: Dict[str, Any],
    user_profile: Dict[str, Any],
    skill_id: str,
    messages: list,
) -> str:
    """调用 LLM 生成综合回答

    Args:
        tool_results: 工具执行结果
        user_profile: 用户档案
        skill_id: 当前 Skill ID
        messages: 对话消息

    Returns:
        LLM 生成的回答文本
    """
    import json

    if not _llm_pool:
        logger.warning("output_generate: LLMPoolManager 未配置，使用模板回答")
        return _build_template_response(tool_results, skill_id)

    # 构建综合消息
    tool_summary = json.dumps(tool_results, ensure_ascii=False, indent=2)
    profile_summary = json.dumps(user_profile, ensure_ascii=False)

    synthesis_messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"用户档案：{profile_summary}\n\n"
                f"Skill: {skill_id}\n\n"
                f"工具执行结果：\n{tool_summary}\n\n"
                f"请根据以上信息生成回答。"
            ),
        },
    ]

    try:
        model = _llm_pool.get_active_model()
        if not model:
            logger.warning("output_generate: 无可用模型，使用模板回答")
            return _build_template_response(tool_results, skill_id)

        # 使用 httpx 调用 OpenAI 兼容接口
        import httpx

        async with httpx.AsyncClient(timeout=model.timeout_ms / 1000) as client:
            resp = await client.post(
                f"{model.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {model.api_key}"},
                json={
                    "model": model.name,
                    "messages": synthesis_messages,
                    "max_tokens": model.max_tokens,
                    "temperature": model.temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"output_generate: LLM 调用失败: {e}")
        return _build_template_response(tool_results, skill_id)


def _build_template_response(
    tool_results: Dict[str, Any],
    skill_id: str,
) -> str:
    """模板兜底回答（所有 LLM 不可用时）

    Args:
        tool_results: 工具执行结果
        skill_id: Skill ID

    Returns:
        模板回答文本
    """
    successful_tools = [
        name for name, result in tool_results.items()
        if isinstance(result, dict) and result.get("success")
    ]

    if successful_tools:
        return (
            f"已为您完成 {skill_id} 相关分析（使用了 "
            f"{', '.join(successful_tools)} 工具）。\n\n"
            f"由于系统繁忙，暂时无法生成详细解读，请稍后重试。"
        )

    return "抱歉，当前系统繁忙，请稍后再试。"
