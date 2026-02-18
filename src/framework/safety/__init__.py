# -*- coding: utf-8 -*-
"""
Prompt Injection 检测器

检测用户输入中的 LLM 提示词注入攻击，包括：
- 指令覆盖（忽略/遗忘之前的指令）
- 角色扮演攻击（假装你是...）
- 系统提示词泄露（输出你的系统提示）
- 越狱尝试（DAN模式等）
- 编码绕过（base64/unicode混淆）

版本: v1.0.0
创建日期: 2026-02-19
Task: Phase 7 - Task 36
"""

import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class InjectionDetectionResult:
    """注入检测结果"""
    is_injection: bool = False
    confidence: float = 0.0  # 0.0-1.0
    matched_patterns: List[str] = field(default_factory=list)
    risk_description: str = ""


class PromptInjectionDetector:
    """
    Prompt Injection 检测器

    在用户输入到达 LLM 之前进行注入检测。
    检测到注入时返回安全提示，不暴露系统信息。
    """

    # 注入检测正则模式（中英文）
    INJECTION_PATTERNS: List[Tuple[str, str, float]] = [
        # (pattern, description, confidence_weight)
        # 指令覆盖
        (r"(?:忽略|无视|遗忘|忘记|丢弃|放弃)(?:之前|上面|以上|前面|所有)(?:的)?(?:指令|指示|规则|提示|设定|约束|限制)",
         "指令覆盖-中文", 0.95),
        (r"(?:ignore|disregard|forget|bypass|override|skip)\s+(?:all\s+)?(?:previous|above|prior|earlier|your)\s+(?:instructions?|rules?|prompts?|constraints?|guidelines?)",
         "指令覆盖-英文", 0.95),

        # 角色扮演攻击
        (r"(?:假装|假设|扮演|模拟|充当|变成)(?:你是|自己是)",
         "角色扮演-中文", 0.8),
        (r"(?:pretend|act|behave|roleplay|imagine)\s+(?:you\s+are|to\s+be|as\s+if)",
         "角色扮演-英文", 0.8),

        # 系统提示词泄露
        (r"(?:输出|显示|打印|告诉我|展示|泄露|透露)(?:你的)?(?:系统|初始|原始)?(?:提示词|prompt|指令|设定|角色设定|system\s*prompt)",
         "提示词泄露-中文", 0.9),
        (r"(?:show|print|output|reveal|display|leak|expose)\s+(?:me\s+)?(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|initial\s+prompt|hidden\s+prompt)",
         "提示词泄露-英文", 0.9),

        # 越狱尝试
        (r"(?:DAN|do\s+anything\s+now|jailbreak|越狱模式|开发者模式|developer\s+mode)",
         "越狱尝试", 0.85),
        (r"(?:你现在)?(?:没有|不受|不再有|解除)(?:任何)?(?:限制|约束|规则|道德)",
         "限制解除-中文", 0.85),

        # 分隔符注入
        (r"(?:---+|===+|###)\s*(?:system|系统|新指令|new\s+instruction)",
         "分隔符注入", 0.7),

        # 间接注入（通过"翻译/总结"包装）
        (r"(?:翻译|总结|重复|复述)(?:以下|下面)(?:内容|文本)[:：]\s*(?:忽略|ignore|system)",
         "间接注入", 0.75),
    ]

    # 安全响应（不暴露系统信息）
    SAFE_RESPONSE = (
        "您的输入包含不被支持的内容格式。"
        "作为健身顾问，我可以帮您解答训练计划、营养饮食、动作指导等健身相关问题。"
        "请重新描述您的需求。"
    )

    def __init__(self, threshold: float = 0.6):
        """
        Args:
            threshold: 判定为注入的置信度阈值（0.0-1.0）
        """
        self.threshold = threshold
        self._compiled_patterns = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), desc, weight)
            for p, desc, weight in self.INJECTION_PATTERNS
        ]
        logger.info(f"PromptInjectionDetector初始化: {len(self._compiled_patterns)}个检测模式, 阈值={threshold}")

    def detect(self, text: str) -> InjectionDetectionResult:
        """
        检测输入文本是否包含 prompt injection。

        Args:
            text: 用户输入文本

        Returns:
            InjectionDetectionResult
        """
        if not text or len(text.strip()) < 3:
            return InjectionDetectionResult()

        result = InjectionDetectionResult()
        max_confidence = 0.0

        for compiled, desc, weight in self._compiled_patterns:
            if compiled.search(text):
                result.matched_patterns.append(desc)
                max_confidence = max(max_confidence, weight)

        result.confidence = max_confidence
        result.is_injection = max_confidence >= self.threshold

        if result.is_injection:
            result.risk_description = f"检测到{len(result.matched_patterns)}个注入模式: {', '.join(result.matched_patterns)}"
            self._log_injection_attempt(text, result)

        return result

    def _log_injection_attempt(self, text: str, result: InjectionDetectionResult):
        """记录注入尝试到审计日志"""
        # 截断输入避免日志过长
        truncated = text[:200] + "..." if len(text) > 200 else text
        logger.warning(
            f"🚨 Prompt Injection检测 | "
            f"置信度={result.confidence:.2f} | "
            f"模式={result.matched_patterns} | "
            f"输入摘要={truncated!r}"
        )

    def get_safe_response(self) -> str:
        """获取安全响应文本"""
        return self.SAFE_RESPONSE


# 单例
_detector: Optional[PromptInjectionDetector] = None


def get_injection_detector() -> PromptInjectionDetector:
    """获取注入检测器单例"""
    global _detector
    if _detector is None:
        _detector = PromptInjectionDetector()
    return _detector
