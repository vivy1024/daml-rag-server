# -*- coding: utf-8 -*-
"""
模型路由配置 — 蓝绿测试 + 固定覆盖

三种路由模式共存，优先级：固定覆盖 > YAML加权池 > 环境变量池 > 默认降级链

1. TEMPLATE_MODEL_MAP  — 固定覆盖（某模板必须用某模型）
   格式: greeting:siliconflow,safety_assessment:anthropic
2. multi_model_pool.yaml — YAML加权随机池（9模型4层级）
3. MULTI_MODEL_POOL    — 环境变量等权池（向后兼容）

路由逻辑:
  get_backend_for_template(template_id)
    → 如果 TEMPLATE_MODEL_MAP 有该模板 → 返回固定后端
    → 如果 YAML池启用 → 加权随机选一个 → 返回 PoolEntry
    → 如果 MULTI_MODEL_POOL 非空 → 等权随机选一个
    → 否则返回 None（走默认降级链）

版本: v2.0.0
日期: 2026-02-20
"""

import os
import random
import logging
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# PoolEntry 数据类
# ═══════════════════════════════════════════════════════════

@dataclass
class PoolEntry:
    """蓝绿池模型条目"""
    backend: str        # 后端名称（如 siliconflow, deepseek）
    model: str          # 模型ID（如 Qwen/Qwen3-8B）
    weight: int         # 权重（加权随机用）
    api_base: str       # API基础URL
    cost_tier: str      # 成本层级: free/free_quota/low/baseline
    note: str = ""      # 备注


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
# YAML 加权池: multi_model_pool.yaml
# ═══════════════════════════════════════════════════════════

_YAML_POOL: Optional[List[PoolEntry]] = None
_YAML_POOL_ENABLED: Optional[bool] = None


def _load_yaml_pool() -> tuple:
    """加载 YAML 蓝绿池配置，返回 (enabled, entries)"""
    config_path = Path(__file__).resolve().parents[4] / "config" / "multi_model_pool.yaml"

    if not config_path.exists():
        logger.debug(f"YAML池配置不存在: {config_path}")
        return False, []

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or not data.get("enabled", False):
            logger.info("YAML池已禁用（enabled=false）")
            return False, []

        entries = []
        for item in data.get("pool", []):
            entry = PoolEntry(
                backend=item["backend"],
                model=item["model"],
                weight=item.get("weight", 10),
                api_base=item.get("api_base", ""),
                cost_tier=item.get("cost_tier", "free"),
                note=item.get("note", ""),
            )
            entries.append(entry)

        if entries:
            total_weight = sum(e.weight for e in entries)
            logger.info(
                f"🎲 YAML蓝绿池加载: {len(entries)}个模型, "
                f"总权重={total_weight}, "
                f"层级分布: {_summarize_tiers(entries)}"
            )
        return True, entries

    except Exception as e:
        logger.error(f"YAML池配置加载失败: {e}")
        return False, []


def _summarize_tiers(entries: List[PoolEntry]) -> str:
    """汇总各层级权重"""
    tiers: Dict[str, int] = {}
    for e in entries:
        tiers[e.cost_tier] = tiers.get(e.cost_tier, 0) + e.weight
    return ", ".join(f"{k}={v}%" for k, v in sorted(tiers.items()))


def _get_yaml_pool() -> tuple:
    """获取 YAML 池（懒加载+缓存）"""
    global _YAML_POOL, _YAML_POOL_ENABLED
    if _YAML_POOL_ENABLED is None:
        _YAML_POOL_ENABLED, _YAML_POOL = _load_yaml_pool()
    return _YAML_POOL_ENABLED, _YAML_POOL or []


def select_from_yaml_pool() -> Optional[PoolEntry]:
    """从 YAML 池中加权随机选择一个模型"""
    enabled, pool = _get_yaml_pool()
    if not enabled or not pool:
        return None

    weights = [e.weight for e in pool]
    chosen = random.choices(pool, weights=weights, k=1)[0]
    logger.info(
        f"🎲 YAML池选择: {chosen.backend}/{chosen.model} "
        f"(tier={chosen.cost_tier}, weight={chosen.weight})"
    )
    return chosen


# ═══════════════════════════════════════════════════════════
# 环境变量等权池: MULTI_MODEL_POOL（向后兼容）
# ═══════════════════════════════════════════════════════════

def _parse_multi_model_pool() -> List[str]:
    """解析 MULTI_MODEL_POOL 环境变量"""
    raw = os.getenv("MULTI_MODEL_POOL", "")
    if not raw.strip():
        return []

    pool = [b.strip().lower() for b in raw.split(",") if b.strip()]
    if pool:
        logger.info(f"🎲 蓝绿随机池(env): {pool}")
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

def get_backend_for_template(template_id: str) -> Optional[Union[str, PoolEntry]]:
    """
    根据模板ID获取后端路由。

    优先级: 固定覆盖 > YAML加权池 > 环境变量池 > None（默认降级链）

    Returns:
        - str: 后端名称（固定覆盖或环境变量池）
        - PoolEntry: YAML池选中的完整条目（含 model/api_base/cost_tier）
        - None: 走默认降级链
    """
    # 1. 固定覆盖
    mapping = get_template_model_map()
    fixed = mapping.get(template_id)
    if fixed:
        return fixed

    # 2. YAML 加权池
    pool_entry = select_from_yaml_pool()
    if pool_entry:
        return pool_entry

    # 3. 环境变量等权池
    pool = get_multi_model_pool()
    if pool:
        chosen = random.choice(pool)
        logger.info(f"🎲 蓝绿选择(env): {template_id} → {chosen} (pool={pool})")
        return chosen

    # 4. 无配置，走默认降级链
    return None
