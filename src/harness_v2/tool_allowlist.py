# -*- coding: utf-8 -*-
"""
ToolAllowlist — 工具调用权限控制

在 Skill 执行过程中，每次工具调用前检查：
- 当前工具是否属于已加载 Skill 的 allowlist（required_tools + optional_tools）
- 未授权工具调用 → 拒绝

对应需求：REQ-3.2
版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AllowlistResult:
    """工具权限检查结果"""
    allowed: bool
    tool_name: str
    skill_id: str
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "tool_name": self.tool_name,
            "skill_id": self.skill_id,
            "reason": self.reason,
        }


class ToolAllowlist:
    """
    工具调用权限控制器

    基于当前加载的 Skill 定义，限制 Agent 只能调用 Skill 声明的工具。
    防止 LLM 越权调用未授权工具。
    """

    def __init__(self):
        self._current_allowlist: Set[str] = set()
        self._current_skill_id: str = ""

    def set_skill_context(
        self,
        skill_id: str,
        required_tools: list,
        optional_tools: list,
    ):
        """
        设置当前 Skill 上下文，更新 allowlist

        Args:
            skill_id: 当前 Skill ID
            required_tools: 必需工具列表
            optional_tools: 可选工具列表
        """
        self._current_skill_id = skill_id
        self._current_allowlist = set(required_tools) | set(optional_tools)

        # 始终允许的基础工具
        self._current_allowlist.add("get_user_profile")

        logger.info(
            f"🔒 ToolAllowlist: Skill [{skill_id}] 设置 allowlist: "
            f"{len(self._current_allowlist)} 个工具"
        )

    def check(self, tool_name: str) -> AllowlistResult:
        """
        检查工具调用是否被允许

        Args:
            tool_name: 要调用的工具名称

        Returns:
            AllowlistResult: 检查结果
        """
        if not self._current_skill_id:
            # 没有 Skill 上下文时，拒绝所有工具调用
            logger.warning(f"🚫 ToolAllowlist: 无 Skill 上下文，拒绝工具 [{tool_name}]")
            return AllowlistResult(
                allowed=False,
                tool_name=tool_name,
                skill_id="",
                reason="无 Skill 上下文，不允许调用任何工具",
            )

        if tool_name in self._current_allowlist:
            logger.debug(
                f"✅ ToolAllowlist: 工具 [{tool_name}] 在 Skill [{self._current_skill_id}] allowlist 中"
            )
            return AllowlistResult(
                allowed=True,
                tool_name=tool_name,
                skill_id=self._current_skill_id,
            )
        else:
            logger.warning(
                f"🚫 ToolAllowlist: 工具 [{tool_name}] 不在 Skill [{self._current_skill_id}] allowlist 中，拒绝"
            )
            return AllowlistResult(
                allowed=False,
                tool_name=tool_name,
                skill_id=self._current_skill_id,
                reason=f"工具 [{tool_name}] 未被 Skill [{self._current_skill_id}] 授权",
            )

    def get_allowed_tools(self) -> Set[str]:
        """获取当前 allowlist"""
        return self._current_allowlist.copy()

    def reset(self):
        """重置 allowlist（Skill 执行完毕后调用）"""
        self._current_allowlist = set()
        self._current_skill_id = ""
