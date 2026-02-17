# -*- coding: utf-8 -*-
"""
MCP参数验证中间件 - Parameter Validation Middleware

Phase 3 Task 2: 在MCP工具调用前进行Pydantic验证，
自动修复LLM生成的参数问题（类型错误、别名、缺失字段）。

核心设计：
- validate_and_fix(): 验证+修复，不拒绝（graceful degradation）
- 有Pydantic模型的工具：严格验证 + 自动转换
- 无模型的工具：透传原始参数（向后兼容）

版本: v1.0.0
日期: 2026-02-17
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic import ValidationError

from .mcp_tool_params import get_param_model, TOOL_PARAM_MODELS

logger = logging.getLogger(__name__)


class ParamValidationResult:
    """参数验证结果"""

    __slots__ = ("params", "is_valid", "was_modified", "errors", "warnings")

    def __init__(
        self,
        params: Dict[str, Any],
        is_valid: bool = True,
        was_modified: bool = False,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.params = params
        self.is_valid = is_valid
        self.was_modified = was_modified
        self.errors = errors or []
        self.warnings = warnings or []


class MCPParamValidator:
    """
    MCP参数验证中间件

    在工具调用前验证和修复参数，确保类型安全。
    采用"修复优先"策略：尽量自动修复而非拒绝。
    """

    def __init__(self):
        self.logger = logger
        self.stats = {
            "total_validations": 0,
            "passed": 0,
            "fixed": 0,
            "fallback": 0,
        }

    def validate_and_fix(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> ParamValidationResult:
        """
        验证并修复工具参数

        流程：
        1. 查找工具对应的Pydantic模型
        2. 如果有模型：用Pydantic验证，field_validator自动做别名映射和类型转换
        3. 如果验证失败：尝试逐字段修复，移除无效字段后重试
        4. 如果无模型：直接透传（向后兼容）

        Args:
            tool_name: MCP工具名称
            params: 原始参数字典

        Returns:
            ParamValidationResult 包含验证后的参数和诊断信息
        """
        self.stats["total_validations"] += 1

        model_cls = get_param_model(tool_name)
        if model_cls is None:
            # 无Pydantic模型，透传
            self.stats["passed"] += 1
            return ParamValidationResult(params=params)

        # 第一次尝试：直接验证
        try:
            validated = model_cls.model_validate(params)
            validated_dict = validated.model_dump(exclude_none=True)

            was_modified = validated_dict != params
            if was_modified:
                self.stats["fixed"] += 1
                self.logger.info(
                    f"参数已自动修正: {tool_name} | "
                    f"原始={_safe_summary(params)} → 修正={_safe_summary(validated_dict)}"
                )
            else:
                self.stats["passed"] += 1

            return ParamValidationResult(
                params=validated_dict,
                is_valid=True,
                was_modified=was_modified,
            )

        except ValidationError as e:
            # 第一次验证失败，尝试逐字段修复
            self.logger.warning(
                f"参数验证失败，尝试修复: {tool_name} | errors={e.error_count()}"
            )
            return self._attempt_fix(tool_name, params, model_cls, e)

    def _attempt_fix(
        self,
        tool_name: str,
        params: Dict[str, Any],
        model_cls: type,
        original_error: ValidationError,
    ) -> ParamValidationResult:
        """
        尝试修复验证失败的参数

        策略：收集所有出错字段，移除无法修复的字段后重试验证。
        """
        warnings = []
        error_fields = set()

        for err in original_error.errors():
            loc = err.get("loc", ())
            field_name = str(loc[0]) if loc else "unknown"
            error_fields.add(field_name)
            warnings.append(f"{field_name}: {err.get('msg', 'validation error')}")

        # 移除出错字段后重试
        cleaned_params = {
            k: v for k, v in params.items() if k not in error_fields
        }

        try:
            validated = model_cls.model_validate(cleaned_params)
            validated_dict = validated.model_dump(exclude_none=True)

            self.stats["fixed"] += 1
            self.logger.info(
                f"参数修复成功: {tool_name} | 移除字段={error_fields} | "
                f"结果={_safe_summary(validated_dict)}"
            )

            return ParamValidationResult(
                params=validated_dict,
                is_valid=True,
                was_modified=True,
                warnings=warnings,
            )

        except ValidationError as e2:
            # 修复也失败了，回退到原始参数
            self.stats["fallback"] += 1
            all_errors = [
                f"{err.get('loc', ('?',))[0]}: {err.get('msg', '')}"
                for err in e2.errors()
            ]
            self.logger.error(
                f"参数修复失败，回退原始参数: {tool_name} | errors={all_errors}"
            )

            return ParamValidationResult(
                params=params,
                is_valid=False,
                was_modified=False,
                errors=all_errors,
                warnings=warnings,
            )

    def get_stats(self) -> Dict[str, int]:
        """获取验证统计"""
        return self.stats.copy()

    def get_missing_required_hints(
        self, tool_name: str, params: Dict[str, Any]
    ) -> List[str]:
        """
        检查缺失的必填字段，返回提示列表

        用于在验证前给LLM提供缺失字段的提示。
        """
        model_cls = get_param_model(tool_name)
        if model_cls is None:
            return []

        hints = []
        for field_name, field_info in model_cls.model_fields.items():
            if field_info.is_required() and field_name not in params:
                desc = field_info.description or field_name
                hints.append(f"缺少必填参数 '{field_name}': {desc}")

        return hints


def _safe_summary(params: Dict[str, Any], max_len: int = 120) -> str:
    """安全地生成参数摘要（避免日志过长）"""
    text = str(params)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text
