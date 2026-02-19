# -*- coding: utf-8 -*-
"""
偏好自动提取模块

在步骤11（日志记录）之后异步执行：
1. 关键词预筛（避免每次都调 LLM）
2. LLM 分析提取偏好
3. 写入 user_memory collection

版本: v1.0.0
日期: 2026-02-20
"""

import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 关键词预筛列表
PREFERENCE_KEYWORDS = [
    "喜欢", "不喜欢", "偏好", "习惯", "不要", "讨厌",
    "过敏", "受伤", "素食", "只能", "不能", "目标",
    "不吃", "爱吃", "怕", "膝盖", "腰", "颈椎",
    "早上", "晚上", "周末", "没时间", "器械", "徒手",
]

PREFERENCE_EXTRACTION_PROMPT = """分析以下对话，提取用户表达的偏好、习惯或重要信息。

对话内容:
{conversation}

只提取以下类型的信息（如果有的话）：
- exercise_preference: 训练偏好（喜欢/不喜欢的运动、器械偏好、时间偏好）
- diet_preference: 饮食偏好（素食、过敏、不吃的食物）
- general: 其他（目标变化、反馈、健康备注）

如果对话中没有值得记忆的偏好信息，返回空数组 []。
不要记忆具体的健康数值（如血压、血糖数字）。
不要记忆单次的训练计划或饮食方案。
只记忆长期有效的偏好和习惯。

返回纯 JSON 数组（不要 markdown 代码块）:
[{"category": "...", "content": "..."}]"""


def should_extract_preferences(conversation_text: str) -> bool:
    """关键词预筛，包含偏好相关词才触发 LLM 提取"""
    return any(kw in conversation_text for kw in PREFERENCE_KEYWORDS)


async def extract_preferences_from_conversation(
    user_query: str,
    ai_response: str,
    llm_call_fn=None,
) -> List[Dict[str, str]]:
    """
    从对话中提取用户偏好。

    Args:
        user_query: 用户查询
        ai_response: AI 回复
        llm_call_fn: LLM 调用函数 (prompt: str) -> str

    Returns:
        偏好列表 [{"category": "...", "content": "..."}]
    """
    conversation = f"用户: {user_query}\nAI: {ai_response[:500]}"

    # 阶段1: 关键词预筛
    if not should_extract_preferences(conversation):
        return []

    # 阶段2: LLM 提取
    if llm_call_fn is None:
        return _keyword_fallback_extract(user_query)

    try:
        prompt = PREFERENCE_EXTRACTION_PROMPT.replace("{conversation}", conversation)
        result_text = await llm_call_fn(prompt)

        # 清理 markdown 代码块
        result_text = result_text.strip()
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        preferences = json.loads(result_text)
        if not isinstance(preferences, list):
            return []

        # 验证格式
        valid = []
        for p in preferences:
            if isinstance(p, dict) and "category" in p and "content" in p:
                if p["category"] in ("exercise_preference", "diet_preference", "general"):
                    valid.append(p)
        return valid

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"偏好提取LLM解析失败: {e}")
        return _keyword_fallback_extract(user_query)


def _keyword_fallback_extract(query: str) -> List[Dict[str, str]]:
    """关键词兜底提取（不依赖 LLM）"""
    results = []

    # 训练偏好
    exercise_kws = ["不喜欢跑步", "喜欢力量", "偏好哑铃", "只能早上", "只能晚上",
                     "膝盖不好", "腰不好", "受伤", "徒手训练", "器械训练"]
    for kw in exercise_kws:
        if kw in query:
            results.append({"category": "exercise_preference", "content": f"用户提到: {kw}"})

    # 饮食偏好
    diet_kws = ["素食", "不吃", "过敏", "不喝牛奶", "乳糖不耐"]
    for kw in diet_kws:
        if kw in query:
            results.append({"category": "diet_preference", "content": f"用户提到: {kw}"})

    return results[:3]  # 最多3条
