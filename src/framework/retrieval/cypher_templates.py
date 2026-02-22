# -*- coding: utf-8 -*-
"""
Neo4j Cypher 查询模板 + 直查执行器

根据意图分类器的结果，选择对应的 Cypher 模板执行 Neo4j 查询。
查询结果格式化为与 HybridSearch 相同的 {id, score, text, payload} 格式，
确保下游 node_aggregate_data / node_llm_analysis 无需修改。

版本: v1.0.0
作者: 薛小川
日期: 2026-02-17
"""

import os
import logging
from typing import List, Dict, Any, Optional

from .intent_classifier import StructuredQueryType

logger = logging.getLogger(__name__)


# ─── Cypher 模板定义 ─────────────────────────────────

CYPHER_TEMPLATES: Dict[StructuredQueryType, str] = {

    # 动作 → 目标肌肉
    StructuredQueryType.EXERCISE_MUSCLES: """
        MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m:Muscle)
        WHERE e.name_zh CONTAINS $keyword
        RETURN e.name_zh AS exercise,
               m.name_zh AS muscle,
               type(r) AS relation,
               e.difficulty AS difficulty,
               e.force AS force
        ORDER BY CASE type(r) WHEN 'TARGETS_PRIMARY' THEN 0 ELSE 1 END
        LIMIT 20
    """,

    # 肌肉 → 推荐动作（支持 group 精确匹配 + CONTAINS 回退）
    StructuredQueryType.MUSCLE_EXERCISES: """
        MATCH (m:Muscle)<-[r:TARGETS_PRIMARY]-(e:Exercise)
        WHERE (CASE WHEN $group IS NOT NULL THEN m.group = $group ELSE true END)
          AND (CASE WHEN $group IS NULL THEN m.name_zh CONTAINS $keyword ELSE true END)
        RETURN e.name_zh AS exercise,
               m.name_zh AS muscle,
               e.difficulty AS difficulty,
               e.equipment_zh AS equipment,
               e.force AS force,
               e.mechanic AS mechanic
        ORDER BY e.difficulty
        LIMIT 20
    """,

    # 动作 → 所需器械
    StructuredQueryType.EXERCISE_EQUIPMENT: """
        MATCH (e:Exercise)-[:REQUIRES]->(eq:Equipment)
        WHERE e.name_zh CONTAINS $keyword
        RETURN e.name_zh AS exercise,
               eq.name_zh AS equipment,
               e.difficulty AS difficulty,
               e.equipment_zh AS equipment_detail
        LIMIT 20
    """,

    # 动作详情
    StructuredQueryType.EXERCISE_DETAILS: """
        MATCH (e:Exercise)
        WHERE e.name_zh CONTAINS $keyword
        OPTIONAL MATCH (e)-[:TARGETS_PRIMARY]->(pm:Muscle)
        OPTIONAL MATCH (e)-[:TARGETS_SECONDARY]->(sm:Muscle)
        OPTIONAL MATCH (e)-[:REQUIRES]->(eq:Equipment)
        RETURN e.name_zh AS exercise,
               e.difficulty AS difficulty,
               e.force AS force,
               e.mechanic AS mechanic,
               e.equipment_zh AS equipment,
               collect(DISTINCT pm.name_zh) AS primary_muscles,
               collect(DISTINCT sm.name_zh) AS secondary_muscles,
               collect(DISTINCT eq.name_zh) AS equipment_list
        LIMIT 10
    """,

    # 肌肉训练容量（MEV/MAV/MRV）— 支持 group 精确匹配
    StructuredQueryType.MUSCLE_CAPACITY: """
        MATCH (m:Muscle)
        WHERE (CASE WHEN $group IS NOT NULL THEN m.group = $group ELSE true END)
          AND (CASE WHEN $group IS NULL THEN m.name_zh CONTAINS $keyword ELSE true END)
        RETURN m.name_zh AS muscle,
               m.mev AS mev,
               m.mav AS mav,
               m.mrv AS mrv,
               m.optimal_frequency AS frequency,
               m.recovery_time AS recovery_time,
               m.group AS muscle_group,
               m.level AS level
        LIMIT 10
    """,

    # 器械 → 可做动作
    StructuredQueryType.EXERCISE_BY_EQUIPMENT: """
        MATCH (e:Exercise)-[:REQUIRES]->(eq:Equipment)
        WHERE eq.name_zh CONTAINS $keyword
        OPTIONAL MATCH (e)-[:TARGETS_PRIMARY]->(m:Muscle)
        RETURN e.name_zh AS exercise,
               eq.name_zh AS equipment,
               e.difficulty AS difficulty,
               collect(DISTINCT m.name_zh) AS primary_muscles
        ORDER BY e.difficulty
        LIMIT 20
    """,

    # 安全禁忌查询（损伤/疾病 → 禁忌动作）
    StructuredQueryType.SAFETY_CONTRAINDICATIONS: """
        MATCH (e:Exercise)-[r:CONTRAINDICATED_FOR]->(i:InjuryType)
        WHERE i.name CONTAINS $keyword OR i.name_zh CONTAINS $keyword
           OR i.category CONTAINS $keyword
        RETURN e.name_zh AS exercise, i.name AS injury_type,
               i.name_zh AS injury_name_zh, i.category AS category,
               r.severity AS severity, r.reason AS reason,
               e.difficulty_zh AS difficulty, e.safety_level AS safety_level
        ORDER BY r.severity DESC, e.difficulty_zh
        LIMIT 20
    """,

    # 体态矫正动作查询（体态问题 → 矫正/加重动作）
    StructuredQueryType.POSTURAL_EXERCISES: """
        MATCH (e:Exercise)-[r:CORRECTS]->(p:PosturalIssue)
        WHERE p.name_zh CONTAINS $keyword OR p.name CONTAINS $keyword
        RETURN e.name_zh AS exercise, p.name_zh AS postural_issue,
               'corrects' AS relation_type, p.category AS category,
               e.difficulty AS difficulty
        LIMIT 15
        UNION ALL
        MATCH (e:Exercise)-[r:AGGRAVATES]->(p:PosturalIssue)
        WHERE p.name_zh CONTAINS $keyword OR p.name CONTAINS $keyword
        RETURN e.name_zh AS exercise, p.name_zh AS postural_issue,
               'aggravates' AS relation_type, p.category AS category,
               e.difficulty AS difficulty
        LIMIT 15
    """,

    # 力量标准查询（动作 → 各水平力量标准）
    StructuredQueryType.STRENGTH_STANDARDS: """
        MATCH (s:StrengthStandard)
        WHERE s.exercise_name CONTAINS $keyword
           OR s.exercise_name_zh CONTAINS $keyword
        RETURN s.exercise_name_zh AS exercise,
               s.gender AS gender,
               s.bodyweight_kg AS body_weight,
               s.level AS level,
               s.weight_kg AS weight_kg,
               s.weight_percentage AS weight_percentage
        ORDER BY s.gender, s.bodyweight_kg, s.level
        LIMIT 20
    """,

    # 健身水平查询（级别 → 适合的动作）
    StructuredQueryType.EXERCISE_BY_LEVEL: """
        MATCH (e:Exercise)-[r:SUITABLE_FOR_LEVEL]->(l:TrainingLevel)
        WHERE l.name CONTAINS $keyword OR l.name_zh CONTAINS $keyword
           OR l.name_en CONTAINS $keyword
        RETURN e.name_en AS exercise, e.name_zh AS exercise_zh,
               l.name AS fitness_level, l.name_zh AS level_zh, l.name_en AS level_en,
               e.difficulty_en AS difficulty, e.equipment_en AS equipment,
               e.muscles_primary_en AS primary_muscles
        ORDER BY e.name_en
        LIMIT 25
    """,

    # 力类型查询（力类型 → 动作）
    StructuredQueryType.EXERCISE_BY_FORCE: """
        MATCH (e:Exercise)-[r:USES_FORCE]->(f:ForceType)
        WHERE f.name CONTAINS $keyword OR f.name_zh CONTAINS $keyword
        RETURN e.name_zh AS exercise, f.name AS force_type,
               f.name_zh AS force_type_zh,
               e.difficulty AS difficulty, e.equipment AS equipment
        ORDER BY e.name_zh
        LIMIT 25
    """,

    # 运动学机制查询（机制类型 → 动作）
    StructuredQueryType.EXERCISE_BY_MECHANIC: """
        MATCH (e:Exercise)-[r:HAS_MECHANIC]->(m:MechanicType)
        WHERE m.name CONTAINS $keyword OR m.name_zh CONTAINS $keyword
        RETURN e.name_zh AS exercise, m.name AS mechanic_type,
               m.name_zh AS mechanic_type_zh,
               e.difficulty AS difficulty, e.equipment AS equipment
        ORDER BY e.name_zh
        LIMIT 25
    """,

    # ─── v1.1.0 新增 Cypher 模板 ───

    # 训练频率查询（肌肉 → 推荐频率 + 恢复时间）
    StructuredQueryType.TRAINING_FREQUENCY: """
        MATCH (m:Muscle)
        WHERE (CASE WHEN $group IS NOT NULL THEN m.group = $group ELSE true END)
          AND (CASE WHEN $group IS NULL THEN m.name_zh CONTAINS $keyword ELSE true END)
        RETURN m.name_zh AS muscle,
               m.optimal_frequency AS frequency,
               m.recovery_time AS recovery_time,
               m.mev AS mev,
               m.mav AS mav,
               m.group AS muscle_group
        LIMIT 10
    """,

    # 动作替代查询（找共享目标肌肉最多的替代动作）
    StructuredQueryType.EXERCISE_SUBSTITUTION: """
        MATCH (e1:Exercise)-[:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m:Muscle)
        WHERE e1.name_zh CONTAINS $keyword
        WITH e1, collect(DISTINCT m) AS e1_muscles,
             CASE WHEN e1.name_zh = $keyword THEN 0
                  WHEN e1.name_zh STARTS WITH $keyword THEN 1
                  ELSE 2 END AS match_rank,
             size(e1.name_zh) AS name_len
        ORDER BY match_rank, name_len
        LIMIT 1
        UNWIND e1_muscles AS m
        MATCH (e2:Exercise)-[:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
        WHERE e1 <> e2 AND NOT e2.name_zh CONTAINS $keyword
        WITH e1, e2, collect(DISTINCT m.name_zh) AS shared_muscles,
             count(DISTINCT m) AS shared_count
        WHERE shared_count >= 2
        RETURN e1.name_zh AS original_exercise,
               e2.name_zh AS substitute_exercise,
               shared_muscles,
               shared_count,
               e2.equipment_zh AS equipment,
               e2.difficulty AS difficulty
        ORDER BY shared_count DESC
        LIMIT 15
    """,

    # 食物宏量营养素查询（食物 → 蛋白质/碳水/脂肪/能量）
    StructuredQueryType.NUTRITION_MACRO: """
        MATCH (f:Food)-[r:CONTAINS_NUTRIENT]->(n:Nutrient)
        WHERE f.name CONTAINS $keyword
          AND n.name IN ['蛋白质', '碳水化合物', '脂肪', '能量']
        RETURN f.name AS food,
               n.name AS nutrient,
               r.amount AS amount,
               r.unit AS unit
        ORDER BY f.name, n.name
        LIMIT 40
    """,
}

# ─── 肌肉分组映射（用户常用名 → Neo4j group 字段值） ─────────
# Neo4j Muscle 节点的 group 字段: chest/back/shoulder/arm/leg/core/hip/neck
# 优先用 group 精确匹配，避免 CONTAINS 的模糊问题

MUSCLE_GROUP_MAP: Dict[str, str] = {
    # 胸部
    "胸": "chest", "胸肌": "chest", "胸大肌": "chest", "胸小肌": "chest",
    "上胸": "chest", "下胸": "chest", "中胸": "chest",
    # 背部
    "背": "back", "背肌": "back", "背阔肌": "back", "斜方肌": "back",
    "下背": "back", "上背": "back", "中背": "back",
    # 肩部
    "肩": "shoulder", "肩膀": "shoulder", "三角肌": "shoulder",
    "前束": "shoulder", "中束": "shoulder", "后束": "shoulder",
    # 手臂
    "手臂": "arm", "二头肌": "arm", "三头肌": "arm",
    "肱二头肌": "arm", "肱三头肌": "arm", "前臂": "arm",
    # 腿部
    "腿": "leg", "大腿": "leg", "小腿": "leg",
    "股四头肌": "leg", "腘绳肌": "leg", "股二头肌": "leg",
    # 核心
    "腹": "core", "腹肌": "core", "腹直肌": "core", "核心": "core",
    "腹斜肌": "core",
    # 臀部
    "臀": "hip", "臀部": "hip", "臀大肌": "hip", "臀中肌": "hip",
    # 颈部
    "颈": "neck", "颈部": "neck",
}

# ─── 实体同义词映射（用于 CONTAINS 回退匹配） ─────────
# 当 group 匹配不适用时（如动作查询），用 CONTAINS 模糊匹配

MUSCLE_SYNONYMS: Dict[str, str] = {
    "胸肌": "胸",       # Neo4j: 上胸, 中胸与下胸, 胸部
    "胸大肌": "胸",
    "胸小肌": "胸",
    "背": "背阔肌",
    "肩": "三角肌",
    "腹肌": "腹",       # Neo4j: 上腹肌, 下腹部
    "腹直肌": "腹",
    "臀": "臀",         # Neo4j: 臀部
    "臀大肌": "臀",
    "臀中肌": "臀",
    "腘绳肌": "股二头肌",  # Neo4j: 股二头肌（外侧）
    "竖脊肌": "下背部",
    "核心": "腹",
    "手臂": "肱",       # 匹配肱二头肌、肱三头肌
    "前臂": "前臂肌群",
}

# 伤病/体态同义词映射（用户口语 → Neo4j InjuryType.name_zh）
INJURY_SYNONYMS: Dict[str, str] = {
    "腰突": "腰椎间盘突出",
    "椎间盘突出": "腰椎间盘突出",
    "腰间盘突出": "腰椎间盘突出",
    "腰椎突出": "腰椎间盘突出",
    "腰痛": "下背部疼痛",
    "下背痛": "下背部疼痛",
    "腰疼": "下背部疼痛",
    "膝盖疼": "膝盖受伤",
    "膝盖痛": "膝盖受伤",
    "膝关节损伤": "膝盖受伤",
    "前叉": "前交叉韧带损伤",
    "ACL": "前交叉韧带损伤",
    "acl": "前交叉韧带损伤",
    "十字韧带": "前交叉韧带损伤",
    "髌骨软化": "髌骨软化症",
    "跑步膝": "髌骨软化症",
    "ITBS": "髂胫束综合征",
    "itbs": "髂胫束综合征",
    "髂胫束": "髂胫束综合征",
    "肩袖": "肩袖损伤",
    "肩袖撕裂": "肩袖损伤",
    "肩峰撞击": "肩峰撞击",
    "肩膀疼": "肩部受伤",
    "肩痛": "肩部受伤",
    "腕管": "腕管综合征",
    "鼠标手": "腕管综合征",
    "手腕疼": "腕部受伤",
    "手腕痛": "腕部受伤",
    "脚踝扭伤": "踝关节扭伤",
    "崴脚": "踝关节扭伤",
    "跟腱": "跟腱炎",
    "足底筋膜": "足底筋膜炎",
    "脚底疼": "足底筋膜炎",
    "颈椎": "颈椎病",
    "脖子疼": "颈部受伤",
    "脖子痛": "颈部受伤",
    "网球肘": "网球肘",
    "高尔夫球肘": "高尔夫球肘",
    "髋关节疼": "髋部受伤",
    "髋关节痛": "髋部受伤",
    "FAI": "髋关节撞击",
    "fai": "髋关节撞击",
    "圆肩": "圆肩",
    "驼背": "胸椎后凸过度(驼背)",
    "骨盆前倾": "骨盆前倾",
    "骨盆后倾": "骨盆后倾",
    "头前伸": "头前伸",
    "X型腿": "膝外翻(X型腿)",
    "O型腿": "膝内翻(O型腿)",
    "脊柱侧弯": "脊柱侧弯",
    "扁平足": "扁平足",
    "高弓足": "高弓足",
}


class CypherQueryExecutor:
    """Neo4j Cypher 直查执行器"""

    def __init__(self, neo4j_manager=None):
        """
        Args:
            neo4j_manager: Neo4jManager 实例（可选，延迟初始化）
        """
        self._neo4j = neo4j_manager

    def _get_neo4j(self):
        """延迟获取 Neo4j 连接"""
        if self._neo4j is None:
            from .graph.neo4j_manager import Neo4jManager
            uri = os.getenv("NEO4J_URI", "bolt://fitness_neo4j:7687")
            # 修复：环境变量可能配置了不可达的hostname，尝试回退
            if "://" in uri:
                import socket
                host = uri.split("://")[1].split(":")[0]
                try:
                    socket.gethostbyname(host)
                except socket.gaierror:
                    uri = "bolt://fitness_neo4j:7687"
                    logger.info(f"Neo4j URI DNS解析失败，回退到: {uri}")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "")
            self._neo4j = Neo4jManager(uri=uri, user=user, password=password)
            logger.info(f"✅ CypherQueryExecutor: Neo4j 连接成功 ({uri})")
        return self._neo4j

    def execute(
        self,
        query_type: StructuredQueryType,
        entity: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        执行结构化 Cypher 查询

        Args:
            query_type: 查询类型
            entity: 提取的实体关键词
            limit: 返回结果数

        Returns:
            统一格式的结果列表 [{id, score, text, payload}]
        """
        template = CYPHER_TEMPLATES.get(query_type)
        if not template:
            logger.warning(f"未找到 Cypher 模板: {query_type}")
            return []

        # 同义词规范化：将用户常用名映射到 Neo4j 实际名称
        normalized_entity = MUSCLE_SYNONYMS.get(entity, entity)
        # 伤病/体态同义词（安全禁忌和体态查询时优先使用）
        if query_type in (StructuredQueryType.SAFETY_CONTRAINDICATIONS, StructuredQueryType.POSTURAL_EXERCISES):
            normalized_entity = INJURY_SYNONYMS.get(entity, entity)

        # 肌肉分组匹配：优先用 group 字段精确匹配
        muscle_group = MUSCLE_GROUP_MAP.get(entity)

        try:
            neo4j = self._get_neo4j()
            params = {"keyword": normalized_entity, "group": muscle_group}
            raw_results = neo4j.execute_query(template, params)

            if not raw_results:
                logger.info(f"Neo4j 查询无结果: {query_type.value}, entity='{entity}'→'{normalized_entity}', group={muscle_group}")
                return []

            # 格式化为统一格式
            formatted = self._format_results(query_type, raw_results, entity)

            logger.info(
                f"✅ Neo4j 直查完成: {query_type.value}, "
                f"entity='{entity}', 结果={len(formatted)}条"
            )
            return formatted[:limit]

        except Exception as e:
            logger.error(f"❌ Neo4j 查询失败: {query_type.value}, entity='{entity}', error={e}")
            return []

    def _format_results(
        self,
        query_type: StructuredQueryType,
        raw_results: List[Dict],
        entity: str
    ) -> List[Dict[str, Any]]:
        """将 Neo4j 原始结果格式化为统一格式"""

        formatted = []
        for i, row in enumerate(raw_results):
            text = self._build_text(query_type, row)
            result = {
                "id": f"neo4j_{query_type.value}_{i}",
                "score": 1.0 - (i * 0.02),  # 按排序递减
                "text": text,
                "payload": {
                    "source": "neo4j_structured",
                    "query_type": query_type.value,
                    "entity": entity,
                    **{k: v for k, v in row.items() if v is not None},
                }
            }
            formatted.append(result)

        return formatted

    def _build_text(self, query_type: StructuredQueryType, row: Dict) -> str:
        """根据查询类型构建可读文本"""

        if query_type == StructuredQueryType.EXERCISE_MUSCLES:
            rel = "主要目标" if row.get("relation") == "TARGETS_PRIMARY" else "次要目标"
            return (
                f"动作「{row.get('exercise', '')}」的{rel}肌肉是"
                f"「{row.get('muscle', '')}」"
                f"（难度: {row.get('difficulty', '未知')}, "
                f"力的方向: {row.get('force', '未知')}）"
            )

        elif query_type == StructuredQueryType.MUSCLE_EXERCISES:
            return (
                f"锻炼「{row.get('muscle', '')}」的推荐动作: "
                f"「{row.get('exercise', '')}」"
                f"（难度: {row.get('difficulty', '未知')}, "
                f"器械: {row.get('equipment', '未知')}, "
                f"类型: {row.get('mechanic', '未知')}）"
            )

        elif query_type == StructuredQueryType.EXERCISE_EQUIPMENT:
            return (
                f"动作「{row.get('exercise', '')}」需要的器械: "
                f"「{row.get('equipment', '')}」"
                f"（难度: {row.get('difficulty', '未知')}）"
            )

        elif query_type == StructuredQueryType.EXERCISE_DETAILS:
            primary = ", ".join(row.get("primary_muscles", []))
            secondary = ", ".join(row.get("secondary_muscles", []))
            equip = ", ".join(row.get("equipment_list", []))
            return (
                f"动作「{row.get('exercise', '')}」详情: "
                f"难度={row.get('difficulty', '未知')}, "
                f"力的方向={row.get('force', '未知')}, "
                f"类型={row.get('mechanic', '未知')}, "
                f"器械={row.get('equipment', '未知')}。"
                f"主要肌肉: {primary or '无'}。"
                f"次要肌肉: {secondary or '无'}。"
                f"所需器械: {equip or '无'}。"
            )

        elif query_type == StructuredQueryType.MUSCLE_CAPACITY:
            return (
                f"肌肉「{row.get('muscle', '')}」训练容量: "
                f"MEV(最小有效量)={row.get('mev', '未知')}, "
                f"MAV(最大适应量)={row.get('mav', '未知')}, "
                f"MRV(最大可恢复量)={row.get('mrv', '未知')}, "
                f"推荐频率={row.get('frequency', '未知')}, "
                f"恢复时间={row.get('recovery_time', '未知')}"
            )

        elif query_type == StructuredQueryType.EXERCISE_BY_EQUIPMENT:
            muscles = ", ".join(row.get("primary_muscles", []))
            return (
                f"使用「{row.get('equipment', '')}」可做的动作: "
                f"「{row.get('exercise', '')}」"
                f"（难度: {row.get('difficulty', '未知')}, "
                f"目标肌肉: {muscles or '未知'}）"
            )

        elif query_type == StructuredQueryType.SAFETY_CONTRAINDICATIONS:
            severity = row.get('severity', '未知')
            severity_label = {'high': '高风险', 'moderate': '中风险'}.get(severity, severity)
            return (
                f"⚠️ 动作「{row.get('exercise', '')}」"
                f"对「{row.get('injury_name_zh', '') or row.get('injury_type', '')}」"
                f"（{row.get('category', '未知')}）存在禁忌。"
                f"风险等级: {severity_label}, "
                f"原因: {row.get('reason', '未知')}"
            )

        elif query_type == StructuredQueryType.POSTURAL_EXERCISES:
            rel = row.get("relation_type", "")
            if rel == "corrects":
                return (
                    f"✅ 动作「{row.get('exercise', '')}」"
                    f"可以矫正「{row.get('postural_issue', '')}」"
                    f"（分类: {row.get('category', '未知')}, "
                    f"难度: {row.get('difficulty', '未知')}）"
                )
            else:
                return (
                    f"⚠️ 动作「{row.get('exercise', '')}」"
                    f"可能加重「{row.get('postural_issue', '')}」"
                    f"（分类: {row.get('category', '未知')}, "
                    f"难度: {row.get('difficulty', '未知')}）"
                )

        elif query_type == StructuredQueryType.STRENGTH_STANDARDS:
            gender_zh = "男性" if row.get("gender") == "male" else "女性"
            return (
                f"「{row.get('exercise', '')}」力量标准 — "
                f"{gender_zh}, 体重{row.get('body_weight', '?')}kg: "
                f"{row.get('level', '未知')}水平 = "
                f"{row.get('weight_kg', '?')}kg "
                f"({row.get('weight_percentage', '?')}%体重)"
            )

        elif query_type == StructuredQueryType.EXERCISE_BY_LEVEL:
            muscles = row.get('primary_muscles', '?')
            return (
                f"- {row.get('exercise', '?')} "
                f"(级别: {row.get('level_zh', row.get('fitness_level', '?'))}, "
                f"主要肌群: {muscles}, "
                f"难度: {row.get('difficulty', '?')})"
            )

        elif query_type == StructuredQueryType.EXERCISE_BY_FORCE:
            return (
                f"- {row.get('exercise', '?')} "
                f"(力类型: {row.get('force_type_zh', row.get('force_type', '?'))}, "
                f"难度: {row.get('difficulty', '?')})"
            )

        elif query_type == StructuredQueryType.EXERCISE_BY_MECHANIC:
            return (
                f"- {row.get('exercise', '?')} "
                f"(机制: {row.get('mechanic_type_zh', row.get('mechanic_type', '?'))}, "
                f"难度: {row.get('difficulty', '?')})"
            )

        elif query_type == StructuredQueryType.TRAINING_FREQUENCY:
            return (
                f"肌肉「{row.get('muscle', '')}」训练频率: "
                f"推荐{row.get('frequency', '未知')}, "
                f"恢复时间{row.get('recovery_time', '未知')}, "
                f"MEV={row.get('mev', '未知')}, "
                f"MAV={row.get('mav', '未知')}"
            )

        elif query_type == StructuredQueryType.EXERCISE_SUBSTITUTION:
            shared = ", ".join(row.get("shared_muscles", []))
            return (
                f"「{row.get('original_exercise', '')}」的替代动作: "
                f"「{row.get('substitute_exercise', '')}」"
                f"（共享肌肉: {shared}, "
                f"器械: {row.get('equipment', '未知')}, "
                f"难度: {row.get('difficulty', '未知')}）"
            )

        elif query_type == StructuredQueryType.NUTRITION_MACRO:
            unit = row.get('unit', 'g') or 'g'
            return (
                f"食物「{row.get('food', '')}」"
                f"每100g含{row.get('nutrient', '')} "
                f"{row.get('amount', '?')}{unit}"
            )

        return str(row)
