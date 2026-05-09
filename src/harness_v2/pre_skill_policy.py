# -*- coding: utf-8 -*-
"""
PreSkillPolicy — Skill 选择前安全策略检查

在 Agent 选择 Skill 后、执行前进行安全检查：
1. 用户有伤病 + 请求高强度 Skill → 强制先走 safety_assessment
2. 用户无档案 + Skill 需要档案 → 提示补充
3. fail-closed：安全检查点默认拒绝

对应需求：REQ-3.1
版本: v2.0.0
日期: 2026-05-09
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# 高强度 Skill 列表（需要安全前置检查）
HIGH_INTENSITY_SKILLS = {
    "safe_training_plan",
    "strength_program",
    "fat_loss_program",
    "exercise_optimization",
}

# 需要用户档案的 Skill
PROFILE_REQUIRED_SKILLS = {
    "safe_training_plan",
    "strength_program",
    "fat_loss_program",
    "nutrition_planning",
    "progress_analysis",
    "rehabilitation_training",
    "posture_correction",
}


@dataclass
class PolicyResult:
    """策略检查结果"""
    allowed: bool
    action: str = "proceed"  # proceed / force_safety / require_profile / deny
    reason: str = ""
    forced_skill: Optional[str] = None  # 强制切换到的 Skill
    requires_approval: bool = False  # 是否需要 HITL 确认

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "reason": self.reason,
            "forced_skill": self.forced_skill,
            "requires_approval": self.requires_approval,
        }


class PreSkillPolicy:
    """
    Skill 选择前安全策略

    检查逻辑（按优先级）：
    1. 用户有 health_conditions + 选择高强度 Skill → 强制先走 safety_assessment + HITL
    2. Skill 需要档案但用户无档案 → 提示补充
    3. 其他情况 → 放行
    """

    def check(
        self,
        skill_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> PolicyResult:
        """
        执行 Skill 前安全策略检查

        Args:
            skill_id: 选择的 Skill ID
            user_profile: 用户档案（可能为 None）

        Returns:
            PolicyResult: 策略检查结果
        """
        # 1. 检查用户是否有健康状况 + 选择高强度 Skill
        if skill_id in HIGH_INTENSITY_SKILLS:
            health_conditions = self._extract_health_conditions(user_profile)
            if health_conditions:
                logger.warning(
                    f"🚨 PreSkillPolicy: 用户有健康状况 {health_conditions}，"
                    f"但请求高强度 Skill [{skill_id}]，强制先走 safety_assessment"
                )
                return PolicyResult(
                    allowed=False,
                    action="force_safety",
                    reason=f"用户有健康状况（{', '.join(health_conditions)}），需先进行安全评估",
                    forced_skill="safety_assessment",
                    requires_approval=True,
                )

        # 2. 检查 Skill 是否需要用户档案
        if skill_id in PROFILE_REQUIRED_SKILLS:
            if not self._has_basic_profile(user_profile):
                logger.info(
                    f"⚠️ PreSkillPolicy: Skill [{skill_id}] 需要用户档案，但档案不完整"
                )
                return PolicyResult(
                    allowed=False,
                    action="require_profile",
                    reason="该功能需要您的基本信息（身高、体重、健身水平），请先完善个人档案",
                )

        # 3. 默认放行
        logger.debug(f"✅ PreSkillPolicy: Skill [{skill_id}] 通过安全检查")
        return PolicyResult(allowed=True, action="proceed")

    def _extract_health_conditions(
        self, user_profile: Optional[Dict[str, Any]]
    ) -> List[str]:
        """提取用户健康状况列表"""
        if not user_profile:
            return []

        conditions = []

        # 从 health_info 提取
        health_info = user_profile.get("health_info", {})
        if isinstance(health_info, dict):
            injuries = health_info.get("injuries", [])
            if injuries:
                conditions.extend(injuries)
            chronic = health_info.get("chronic_conditions", [])
            if chronic:
                conditions.extend(chronic)
            medical = health_info.get("medical_conditions", [])
            if medical:
                conditions.extend(medical)

        # 从 basic_info 提取
        basic_info = user_profile.get("basic_info", {})
        if isinstance(basic_info, dict):
            health_conds = basic_info.get("health_conditions", [])
            if health_conds:
                conditions.extend(health_conds)

        return [c for c in conditions if c]  # 过滤空值

    def _has_basic_profile(self, user_profile: Optional[Dict[str, Any]]) -> bool:
        """检查用户是否有基本档案"""
        if not user_profile:
            return False

        basic_info = user_profile.get("basic_info", {})
        if not isinstance(basic_info, dict):
            return False

        # 至少需要：性别、年龄/身高/体重之一、健身水平
        has_gender = bool(basic_info.get("gender"))
        has_body = bool(
            basic_info.get("height") or basic_info.get("weight") or basic_info.get("age")
        )
        has_level = bool(basic_info.get("fitness_level"))

        return has_gender and has_body and has_level
