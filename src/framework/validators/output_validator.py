# -*- coding: utf-8 -*-
"""
LLM Output Validator - LLM输出验证器

在LLM分析引擎（段3）输出后进行安全验证:
1. 禁忌症交叉检查：推荐动作 vs 用户禁忌列表
2. 训练量范围检查：不超过用户能力的120%

验证失败时:
- 标记低置信度（confidence降至0.3）
- 附加安全警告到safety_reminders
- 不阻断响应（用户仍可看到建议，但有明确警告）

版本: v1.0.0
日期: 2026-02-19
作者: 薛小川
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)
    contraindication_violations: List[str] = field(default_factory=list)
    overload_violations: List[str] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return len(self.contraindication_violations) > 0 or len(self.overload_violations) > 0


class LLMOutputValidator:
    """
    LLM输出验证器

    使用方式:
        validator = LLMOutputValidator()
        result = validator.validate(llm_output_text, contraindications, user_capacity)
        if result.has_violations:
            # 降低置信度，附加安全警告
    """

    # 训练量上限倍率（用户能力的120%）
    OVERLOAD_THRESHOLD = 1.2

    def validate(
        self,
        output_text: str,
        contraindications: Optional[List[Dict[str, Any]]] = None,
        user_capacity: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        验证LLM输出

        Args:
            output_text: LLM生成的文本
            contraindications: 用户禁忌动作列表 [{"name": "深蹲", "reason": "膝盖损伤"}, ...]
            user_capacity: 用户训练能力 {"max_weight_kg": 80, "max_reps": 15, "max_sets": 5, ...}

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # 1. 禁忌症交叉检查
        if contraindications:
            self._check_contraindications(output_text, contraindications, result)

        # 2. 训练量范围检查
        if user_capacity:
            self._check_training_load(output_text, user_capacity, result)

        result.is_valid = not result.has_violations
        return result

    def apply_to_analysis(
        self,
        analysis_result: Any,
        validation: "ValidationResult",
    ) -> Any:
        """
        将验证结果应用到AnalysisResult

        Args:
            analysis_result: LLMAnalysisEngine的AnalysisResult
            validation: 验证结果

        Returns:
            修改后的AnalysisResult
        """
        if not validation.has_violations:
            return analysis_result

        # 降低置信度
        analysis_result.confidence = min(analysis_result.confidence, 0.3)

        # 附加安全警告
        for violation in validation.contraindication_violations:
            warning = f"⚠️ 安全警告：{violation}"
            if warning not in analysis_result.safety_reminders:
                analysis_result.safety_reminders.append(warning)

        for violation in validation.overload_violations:
            warning = f"⚠️ 训练量警告：{violation}"
            if warning not in analysis_result.safety_reminders:
                analysis_result.safety_reminders.append(warning)

        # 在元数据中记录验证失败
        analysis_result.analysis_metadata["validation_failed"] = True
        analysis_result.analysis_metadata["violation_count"] = (
            len(validation.contraindication_violations) + len(validation.overload_violations)
        )

        logger.warning(
            f"LLM输出验证失败: "
            f"{len(validation.contraindication_violations)}个禁忌违规, "
            f"{len(validation.overload_violations)}个训练量超标"
        )

        return analysis_result

    def _check_contraindications(
        self,
        output_text: str,
        contraindications: List[Dict[str, Any]],
        result: ValidationResult,
    ):
        """禁忌症交叉检查：扫描输出文本中是否推荐了禁忌动作"""
        text_lower = output_text.lower()

        for item in contraindications:
            name = ""
            if isinstance(item, dict):
                name = item.get("name", item.get("exercise_name", ""))
            elif isinstance(item, str):
                name = item

            if not name:
                continue

            name_lower = name.lower()

            # 检查动作名是否出现在输出中（排除"禁忌"/"避免"/"不要"上下文）
            if name_lower in text_lower:
                # 检查是否在安全警告上下文中（这种情况是正确的）
                if self._is_in_warning_context(text_lower, name_lower):
                    continue

                reason = ""
                if isinstance(item, dict):
                    reason = item.get("reason", item.get("contraindication_reason", ""))

                violation_msg = f"输出中推荐了禁忌动作「{name}」"
                if reason:
                    violation_msg += f"（用户禁忌原因: {reason}）"

                result.contraindication_violations.append(violation_msg)
                logger.warning(f"禁忌症违规: {violation_msg}")

    def _is_in_warning_context(self, text: str, name: str) -> bool:
        """检查动作名是否出现在警告/禁止上下文中（这种情况是安全的）"""
        # 在name前后50字符范围内搜索警告关键词
        warning_keywords = [
            "禁忌", "避免", "不要", "不推荐", "不建议", "禁止",
            "注意", "危险", "风险", "不适合", "不宜", "慎做",
            "❌", "⚠️",
        ]

        idx = text.find(name)
        while idx != -1:
            # 取前后50字符的上下文
            start = max(0, idx - 50)
            end = min(len(text), idx + len(name) + 50)
            context = text[start:end]

            has_warning = any(kw in context for kw in warning_keywords)
            if not has_warning:
                # 找到一个不在警告上下文中的出现 → 可能是推荐
                return False

            # 继续搜索下一个出现
            idx = text.find(name, idx + 1)

        # 所有出现都在警告上下文中
        return True

    def _check_training_load(
        self,
        output_text: str,
        user_capacity: Dict[str, Any],
        result: ValidationResult,
    ):
        """训练量范围检查：提取数字型训练参数，确保不超过用户能力的120%"""
        # 检查重量
        max_weight = user_capacity.get("max_weight_kg")
        if max_weight and isinstance(max_weight, (int, float)):
            self._check_numeric_param(
                output_text, max_weight, "重量",
                [r"(\d+(?:\.\d+)?)\s*(?:kg|公斤|千克)"],
                result,
            )

        # 检查次数
        max_reps = user_capacity.get("max_reps")
        if max_reps and isinstance(max_reps, (int, float)):
            self._check_numeric_param(
                output_text, max_reps, "次数",
                [r"(\d+)\s*(?:次|reps|rep)"],
                result,
            )

        # 检查组数
        max_sets = user_capacity.get("max_sets")
        if max_sets and isinstance(max_sets, (int, float)):
            self._check_numeric_param(
                output_text, max_sets, "组数",
                [r"(\d+)\s*(?:组|sets|set)"],
                result,
            )

    def _check_numeric_param(
        self,
        text: str,
        user_max: float,
        param_name: str,
        patterns: List[str],
        result: ValidationResult,
    ):
        """检查文本中的数值参数是否超过用户能力的120%"""
        threshold = user_max * self.OVERLOAD_THRESHOLD

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match)
                    if value > threshold:
                        violation = (
                            f"{param_name}建议值{value}超过用户能力上限"
                            f"（用户最大{user_max}, 安全阈值{threshold:.0f}）"
                        )
                        result.overload_violations.append(violation)
                except (ValueError, TypeError):
                    pass
