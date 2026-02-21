# -*- coding: utf-8 -*-
"""
查询预处理器 — 口语噪声清洗

将用户口语化查询清洗为结构化检索查询，提升向量检索和 BM25 的命中率。

设计原则：纯规则+正则，零 LLM 调用，零延迟开销。

版本: v1.0.0
作者: 薛小川
日期: 2026-02-21
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── 口语填充词（filler words）─────────────────────────
# 按长度降序排列，优先匹配长的
FILLER_WORDS = [
    "我想问一下就是",
    "请问一下就是",
    "我想问一下",
    "请问一下",
    "我想知道",
    "想问一下",
    "就是那个",
    "那个就是",
    "到底是不是",
    "到底有没有",
    "到底能不能",
    "到底",
    "就是说",
    "就是嘛",
    "就是",
    "那个",
    "嗯嗯",
    "emmm",
    "emm",
    "嗯",
    "啊",
    "呢",
    "吧",
    "嘛",
    "哈",
    "呀",
    "哦",
    "噢",
    "额",
]

# ─── 口语句式模式 → 清洗规则 ─────────────────────────
ORAL_PATTERNS = [
    # "那个XXX叫啥来着" → "XXX"
    (r"那个(.+?)叫啥来着", r"\1"),
    # "XXX到底有没有用啊" → "XXX有用吗"
    (r"(.+?)到底有没有用[啊呢吧]?", r"\1有用吗"),
    # "XXX到底能不能XXX" → "XXX能XXX吗"
    (r"(.+?)到底能不能(.+?)[啊呢吧]?$", r"\1能\2吗"),
    # "XXX是不是不能XXX" → "XXX能XXX吗"
    (r"(.+?)是不是不能(.+?)[啊呢吧]?$", r"\1能\2吗"),
    # "我老是XXX怎么办" → "XXX怎么办"
    (r"我老是(.+?)怎么办", r"\1怎么办"),
    # "我一个都做不了有没有替代的" → "替代动作"
    (r"(.+?)我一个都做不了有没有替代的", r"\1替代动作"),
    # "XXX有没有替代的" → "XXX替代动作"
    (r"(.+?)有没有替代的", r"\1替代动作"),
]


def clean_oral_noise(query: str) -> str:
    """
    清洗口语噪声，返回更适合检索的查询文本。

    Args:
        query: 原始用户查询

    Returns:
        清洗后的查询文本
    """
    if not query or len(query) < 2:
        return query

    original = query
    cleaned = query.strip()

    # 1. 应用句式模式替换
    for pattern, replacement in ORAL_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned)

    # 2. 移除填充词（从长到短）
    for filler in FILLER_WORDS:
        cleaned = cleaned.replace(filler, "")

    # 3. 清理多余空格和标点
    cleaned = re.sub(r'\s+', '', cleaned)
    cleaned = re.sub(r'^[，。、！？,.!?]+', '', cleaned)
    cleaned = re.sub(r'[，。、！？,.!?]+$', '', cleaned)

    # 4. 如果清洗后太短（< 2字），回退到原始查询
    if len(cleaned) < 2:
        cleaned = original.strip()

    if cleaned != original.strip():
        logger.debug(f"口语清洗: '{original}' → '{cleaned}'")

    return cleaned


def preprocess_query(query: str) -> str:
    """
    查询预处理入口：口语清洗 + 未来可扩展的其他预处理步骤。

    Args:
        query: 原始用户查询

    Returns:
        预处理后的查询文本
    """
    return clean_oral_noise(query)
