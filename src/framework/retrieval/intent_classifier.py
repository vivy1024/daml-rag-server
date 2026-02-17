# -*- coding: utf-8 -*-
"""
查询意图分类器（规则引擎版）

根据查询文本的模式和关键词，将查询分为三类：
- structured: 可直接用 Neo4j Cypher 回答（动作-肌肉、器械、营养成分等）
- semantic: 需要语义理解的开放性问题 → Hybrid Search
- hybrid: 两路都走，融合结果

设计原则：纯规则+正则，零 LLM 调用，零延迟开销。

版本: v1.0.0
作者: 薛小川
日期: 2026-02-17
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """查询意图类型"""
    STRUCTURED = "structured"  # Neo4j Cypher 直查
    SEMANTIC = "semantic"      # Hybrid Search（BM25 + 向量 + RRF）
    HYBRID = "hybrid"          # 两路融合


class StructuredQueryType(Enum):
    """结构化查询子类型（对应 Cypher 模板）"""
    EXERCISE_MUSCLES = "exercise_muscles"       # 动作→肌肉
    MUSCLE_EXERCISES = "muscle_exercises"       # 肌肉→动作
    EXERCISE_EQUIPMENT = "exercise_equipment"   # 动作→器械
    EXERCISE_DETAILS = "exercise_details"       # 动作详情
    MUSCLE_CAPACITY = "muscle_capacity"         # 肌肉训练容量
    EXERCISE_BY_EQUIPMENT = "exercise_by_equipment"  # 器械→动作


@dataclass
class IntentResult:
    """意图分类结果"""
    intent: QueryIntent
    confidence: float  # 0.0 ~ 1.0
    structured_type: Optional[StructuredQueryType] = None
    extracted_entity: Optional[str] = None  # 提取的实体（动作名/肌肉名等）
    reason: str = ""


# ─── 实体词典 ─────────────────────────────────────

# 常见动作名（用于实体提取）
EXERCISE_KEYWORDS = [
    "深蹲", "硬拉", "卧推", "引体向上", "划船", "推举", "弯举",
    "飞鸟", "臂屈伸", "腿举", "腿弯举", "腿屈伸", "小腿提踵",
    "罗马尼亚硬拉", "相扑硬拉", "前蹲", "颈前深蹲", "保加利亚分腿蹲",
    "俯卧撑", "双杠臂屈伸", "面拉", "侧平举", "前平举",
    "杠铃弯举", "哑铃弯举", "锤式弯举", "绳索下压",
    "高位下拉", "坐姿划船", "T杠划船", "杠铃划船",
    "上斜卧推", "下斜卧推", "哑铃卧推", "杠铃卧推",
    "肩推", "哑铃推举", "杠铃推举", "阿诺德推举",
    "山羊挺身", "仰卧起坐", "平板支撑", "卷腹",
    "箭步蹲", "臀桥", "臀推", "早安式体前屈",
]

# 常见肌肉名
MUSCLE_KEYWORDS = [
    "胸肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌",
    "股四头肌", "腘绳肌", "臀大肌", "小腿", "腓肠肌", "比目鱼肌",
    "斜方肌", "竖脊肌", "腹直肌", "腹外斜肌", "腹内斜肌",
    "前臂", "菱形肌", "大圆肌", "小圆肌", "冈下肌",
    "胸大肌", "胸小肌", "三角肌前束", "三角肌中束", "三角肌后束",
    "臀中肌", "臀小肌", "髂腰肌", "内收肌",
    "胸", "背", "肩", "手臂", "腿", "臀", "核心", "腹肌",
]

# 常见器械名
EQUIPMENT_KEYWORDS = [
    "杠铃", "哑铃", "绳索", "龙门架", "史密斯机",
    "弹力带", "壶铃", "TRX", "瑜伽垫", "泡沫轴",
    "腿举机", "坐姿推胸机", "高位下拉机", "蝴蝶机",
    "罗马椅", "卧推架", "深蹲架", "引体向上杆",
    "自重", "徒手",
]


# ─── 结构化查询模式 ─────────────────────────────────

# 模式：动作 → 肌肉（"深蹲练哪些肌肉"、"卧推锻炼什么部位"）
EXERCISE_MUSCLE_PATTERNS = [
    r"(.+?)(?:练|锻炼|训练|刺激|激活|用到)(?:哪些?|什么|哪个|啥)(?:肌肉|肌群|部位|肌)",
    r"(.+?)(?:主要|主动|目标)(?:肌肉|肌群|部位)",
    r"(.+?)(?:能|可以)(?:练到|锻炼到|刺激到)(?:哪些?|什么)?(?:肌肉|肌群|部位)?",
    r"做(.+?)(?:时|的时候)(?:用到|练到|刺激)(?:哪些?|什么)(?:肌肉|肌群)?",
]

# 模式：肌肉 → 动作（"练胸肌的动作"、"怎么练背"）
MUSCLE_EXERCISE_PATTERNS = [
    r"(?:练|锻炼|训练|强化)(.+?)(?:的|用什么|有哪些?)(?:动作|方法|训练|运动|方式)",
    r"(.+?)(?:怎么练|如何练|如何锻炼|怎么锻炼|怎样练)",
    r"(?:哪些?|什么|啥)(?:动作|训练|运动)(?:练|锻炼|针对)(.+)",
    r"(?:针对|锻炼|训练)(.+?)(?:的|最好的|推荐的?)(?:动作|训练|运动)",
]

# 模式：动作 → 器械（"深蹲需要什么器械"）
EXERCISE_EQUIPMENT_PATTERNS = [
    r"(.+?)(?:需要|用|使用)(?:什么|哪些?|啥)(?:器械|器材|设备|工具)",
    r"做(.+?)(?:需要|用)(?:什么|哪些?)(?:器械|器材)?",
]

# 模式：器械 → 动作（"哑铃能做什么动作"）
EQUIPMENT_EXERCISE_PATTERNS = [
    r"(?:用)?(.+?)(?:能做|可以做|能练|可以练)(?:什么|哪些?)(?:动作|训练|运动)?",
    r"(.+?)(?:的|相关)(?:动作|训练|运动|练法)",
]

# 模式：动作详情（"深蹲怎么做"、"硬拉的正确姿势"）
EXERCISE_DETAIL_PATTERNS = [
    r"(.+?)(?:怎么做|怎样做|如何做|正确做法|正确姿势|动作要领|技术要点)",
    r"(.+?)(?:的)(?:正确|标准)(?:姿势|做法|动作|形式)",
]

# 模式：肌肉训练容量（"胸肌的训练量"、"背的MEV"）
MUSCLE_CAPACITY_PATTERNS = [
    r"(.+?)(?:的)?(?:训练量|训练容量|最大可恢复量|最小有效量|最大适应量)",
    r"(.+?)(?:的)?(?:MEV|MAV|MRV|训练频率|恢复时间)",
]


def classify_intent(query: str) -> IntentResult:
    """
    分类查询意图

    Args:
        query: 用户查询文本

    Returns:
        IntentResult: 分类结果
    """
    query_clean = query.strip()

    # 1. 尝试匹配结构化模式
    structured_result = _match_structured_patterns(query_clean)
    if structured_result and structured_result.confidence >= 0.7:
        logger.info(
            f"🎯 意图分类: STRUCTURED ({structured_result.structured_type.value}), "
            f"实体='{structured_result.extracted_entity}', "
            f"置信度={structured_result.confidence:.2f}"
        )
        return structured_result

    # 2. 检查是否包含结构化实体但模式不明确 → hybrid
    has_exercise = any(kw in query_clean for kw in EXERCISE_KEYWORDS)
    has_muscle = any(kw in query_clean for kw in MUSCLE_KEYWORDS)
    has_equipment = any(kw in query_clean for kw in EQUIPMENT_KEYWORDS)

    if (has_exercise or has_muscle or has_equipment) and len(query_clean) > 10:
        # 有实体但查询较长/复杂 → hybrid
        entity = _extract_first_entity(query_clean)
        logger.info(
            f"🎯 意图分类: HYBRID, 实体='{entity}', "
            f"原因='含结构化实体但查询复杂'"
        )
        return IntentResult(
            intent=QueryIntent.HYBRID,
            confidence=0.6,
            extracted_entity=entity,
            reason="含结构化实体但查询复杂，两路融合"
        )

    # 3. 默认 → semantic
    logger.info(f"🎯 意图分类: SEMANTIC, 原因='无结构化模式匹配'")
    return IntentResult(
        intent=QueryIntent.SEMANTIC,
        confidence=0.8,
        reason="语义查询，使用混合检索"
    )


def _match_structured_patterns(query: str) -> Optional[IntentResult]:
    """尝试匹配结构化查询模式"""

    # 动作 → 肌肉
    for pattern in EXERCISE_MUSCLE_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_exercise(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.9,
                    structured_type=StructuredQueryType.EXERCISE_MUSCLES,
                    extracted_entity=entity,
                    reason=f"动作→肌肉查询: {entity}"
                )

    # 肌肉 → 动作
    for pattern in MUSCLE_EXERCISE_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_muscle(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.9,
                    structured_type=StructuredQueryType.MUSCLE_EXERCISES,
                    extracted_entity=entity,
                    reason=f"肌肉→动作查询: {entity}"
                )

    # 动作 → 器械
    for pattern in EXERCISE_EQUIPMENT_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_exercise(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.EXERCISE_EQUIPMENT,
                    extracted_entity=entity,
                    reason=f"动作→器械查询: {entity}"
                )

    # 器械 → 动作
    for pattern in EQUIPMENT_EXERCISE_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_equipment(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.EXERCISE_BY_EQUIPMENT,
                    extracted_entity=entity,
                    reason=f"器械→动作查询: {entity}"
                )

    # 动作详情
    for pattern in EXERCISE_DETAIL_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_exercise(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.8,
                    structured_type=StructuredQueryType.EXERCISE_DETAILS,
                    extracted_entity=entity,
                    reason=f"动作详情查询: {entity}"
                )

    # 肌肉训练容量
    for pattern in MUSCLE_CAPACITY_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_muscle(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.MUSCLE_CAPACITY,
                    extracted_entity=entity,
                    reason=f"肌肉训练容量查询: {entity}"
                )

    return None


def _is_valid_exercise(entity: str) -> bool:
    """检查是否是有效的动作名"""
    if not entity or len(entity) > 15:
        return False
    return any(kw in entity for kw in EXERCISE_KEYWORDS)


def _is_valid_muscle(entity: str) -> bool:
    """检查是否是有效的肌肉名"""
    if not entity or len(entity) > 10:
        return False
    return any(kw in entity for kw in MUSCLE_KEYWORDS)


def _is_valid_equipment(entity: str) -> bool:
    """检查是否是有效的器械名"""
    if not entity or len(entity) > 10:
        return False
    return any(kw in entity for kw in EQUIPMENT_KEYWORDS)


def _extract_first_entity(query: str) -> Optional[str]:
    """从查询中提取第一个匹配的实体"""
    for kw in EXERCISE_KEYWORDS:
        if kw in query:
            return kw
    for kw in MUSCLE_KEYWORDS:
        if kw in query:
            return kw
    for kw in EQUIPMENT_KEYWORDS:
        if kw in query:
            return kw
    return None
