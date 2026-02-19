# -*- coding: utf-8 -*-
"""
模型路由配置 — 蓝绿测试 + 固定覆盖

两种路由模式共存，优先级：固定覆盖 > 随机池 > 默认降级链

1. TEMPLATE_MODEL_MAP  — 固定覆盖（某模板必须用某模型）
   格式: greeting:siliconflow,safety_assessment:anthropic
2. MULTI_MODEL_POOL    — 蓝绿随机池（每次请求随机选一个后端）
   格式: anthropic,deepseek,siliconflow

路由逻辑:
  get_backend_for_template(template_id)
    → 如果 TEMPLATE_MODEL_MAP 有该模板 → 返回固定后端
    → 如果 MULTI_MODEL_POOL 非空 → 随机选一个
    → 否则返回 None（走默认降级链）

多模型集成 - Task 4 + 蓝绿测试扩展
"""

import os
import random
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# 固定覆盖: TEMPLATE_MODEL_MAP
# ═══════════════════════════════════════════════════════════

def _parse_template_model_map() -> Dict[str, str]:
    """解析 TEMPLATE_MODEL_MAP 环境变量"""
    raw = os.getenv("TEMPLATE_MODEL_MAP", "")
    if not raw.strip():
        return {}

    mapping = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            logger.warning(f"忽略无效的模板路由配置: {pair}")
            continue
        template_id, backend_name = pair.split(":", 1)
        template_id = template_id.strip()
        backend_name = backend_name.strip().lower()
        if template_id and backend_name:
            mapping[template_id] = backend_name

    if mapping:
        logger.info(f"📌 固定路由: {mapping}")
    return mapping


_TEMPLATE_MODEL_MAP: Optional[Dict[str, str]] = None


def get_template_model_map() -> Dict[str, str]:
    """获取模板路由映射（懒加载+缓存）"""
    global _TEMPLATE_MODEL_MAP
    if _TEMPLATE_MODEL_MAP is None:
        _TEMPLATE_MODEL_MAP = _parse_template_model_map()
    return _TEMPLATE_MODEL_MAP


# ═══════════════════════════════════════════════════════════
# 蓝绿随机池: MULTI_MODEL_POOL
# ═══════════════════════════════════════════════════════════

def _parse_multi_model_pool() -> List[str]:
    """解析 MULTI_MODEL_POOL 环境变量"""
    raw = os.getenv("MULTI_MODEL_POOL", "")
    if not raw.strip():
        return []

    pool = [b.strip().lower() for b in raw.split(",") if b.strip()]
    if pool:
        logger.info(f"🎲 蓝绿随机池: {pool}")
    return pool


_MULTI_MODEL_POOL: Optional[List[str]] = None


def get_multi_model_pool() -> List[str]:
    """获取蓝绿随机池（懒加载+缓存）"""
    global _MULTI_MODEL_POOL
    if _MULTI_MODEL_POOL is None:
        _MULTI_MODEL_POOL = _parse_multi_model_pool()
    return _MULTI_MODEL_POOL


# ═══════════════════════════════════════════════════════════
# 统一路由入口
# ═══════════════════════════════════════════════════════════

def get_backend_for_template(template_id: str) -> Optional[str]:
    """
    根据模板ID获取后端名称。

    优先级: 固定覆盖 > 随机池 > None（默认降级链）

    Returns:
        后端名称字符串（如 "deepseek", "siliconflow"），
        或 None 表示走默认降级链。
    """
    # 1. 固定覆盖
    mapping = get_template_model_map()
    fixed = mapping.get(template_id)
    if fixed:
        return fixed

    # 2. 蓝绿随机池
    pool = get_multi_model_pool()
    if pool:
        chosen = random.choice(pool)
        logger.info(f"🎲 蓝绿选择: {template_id} → {chosen} (pool={pool})")
        return chosen

    # 3. 无配置，走默认降级链
    return None
