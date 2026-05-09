# -*- coding: utf-8 -*-
"""
safety_check 节点 — Skill 执行前安全策略检查

职责：
- 使用 PreSkillPolicy 检查
- requires_approval → 调用 interrupt() 进入 HITL
- force_safety → 修改 current_skill 为 safety_assessment
- require_profile → 设置 direct_reply 提示补充档案

版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any

from src.harness_v2.pre_skill_policy import PreSkillPolicy, PolicyResult
from ..state import AgentState

logger = logging.getLogger(__name__)

# 模块级单例
_policy: PreSkillPolicy | None = None


def configure_safety_check(policy: PreSkillPolicy) -> None:
    """配置 safety_check 节点依赖

    Args:
        policy: PreSkillPolicy 实例
    """
    global _policy
    _policy = policy


async def safety_check(state: AgentState) -> Dict[str, Any]:
    """安全策略检查节点

    在 Skill 执行前进行安全检查，根据结果决定：
    - 放行 → 不修改 state
    - 强制安全评估 → 修改 current_skill
    - 需要审批 → interrupt 暂停等待人工确认
    - 需要档案 → 设置 direct_reply 提示用户

    Args:
        state: 当前 Agent 状态

    Returns:
        状态更新字典
    """
    current_skill = state.get("current_skill")

    # 如果没有选中 Skill（direct_reply 路径），跳过检查
    if not current_skill:
        return {}

    policy = _policy or PreSkillPolicy()
    user_profile = state.get("user_profile")

    result: PolicyResult = policy.check(
        skill_id=current_skill,
        user_profile=user_profile,
    )

    # 放行
    if result.allowed:
        logger.info(f"safety_check: Skill [{current_skill}] 通过安全检查")
        return {"approval_status": "approved"}

    # 需要强制安全评估 + HITL 审批
    if result.action == "force_safety":
        logger.warning(
            f"safety_check: 强制安全评估，原 Skill [{current_skill}] "
            f"→ [{result.forced_skill}]"
        )
        if result.requires_approval:
            # 中断等待人工确认（延迟导入避免无 langgraph 环境报错）
            from langgraph.types import interrupt as lg_interrupt
            lg_interrupt({
                "type": "approval_required",
                "original_skill": current_skill,
                "forced_skill": result.forced_skill,
                "reason": result.reason,
            })
            # interrupt 后恢复执行时到达这里
            return {
                "current_skill": result.forced_skill,
                "approval_status": "approved",
            }
        return {
            "current_skill": result.forced_skill,
            "approval_status": "approved",
        }

    # 需要用户档案
    if result.action == "require_profile":
        logger.info(f"safety_check: Skill [{current_skill}] 需要用户档案")
        return {
            "direct_reply": result.reason,
            "current_skill": None,
        }

    # deny 或其他情况
    logger.warning(f"safety_check: Skill [{current_skill}] 被拒绝: {result.reason}")
    return {
        "direct_reply": f"安全检查未通过：{result.reason}",
        "current_skill": None,
        "approval_status": "denied",
    }
