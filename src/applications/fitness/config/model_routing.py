# -*- coding: utf-8 -*-
"""
模板级模型路由配置

根据DAG模板ID选择不同的LLM后端，实现按场景分层用模型。
未配置的模板走默认降级链（Anthropic → DeepSeek → Template）。

环境变量: TEMPLATE_MODEL_MAP=greeting:siliconflow,quick_consultation:siliconflow

多模型集成 - Task 4
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


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
        logger.info(f"模板路由配置已加载: {mapping}")
    return mapping


# 模块级缓存，启动时解析一次
_TEMPLATE_MODEL_MAP: Optional[Dict[str, str]] = None


def get_template_model_map() -> Dict[str, str]:
    """获取模板路由映射（懒加载+缓存）"""
    global _TEMPLATE_MODEL_MAP
    if _TEMPLATE_MODEL_MAP is None:
        _TEMPLATE_MODEL_MAP = _parse_template_model_map()
    return _TEMPLATE_MODEL_MAP


def get_backend_for_template(template_id: str) -> Optional[str]:
    """
    根据模板ID获取指定的后端名称。

    Returns:
        后端名称字符串（如 "qwen", "siliconflow"），
        或 None 表示走默认降级链。
    """
    mapping = get_template_model_map()
    return mapping.get(template_id)
