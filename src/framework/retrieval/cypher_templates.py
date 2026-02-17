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

    # 肌肉 → 推荐动作
    StructuredQueryType.MUSCLE_EXERCISES: """
        MATCH (m:Muscle)<-[r:TARGETS_PRIMARY]-(e:Exercise)
        WHERE m.name_zh CONTAINS $keyword
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

    # 肌肉训练容量（MEV/MAV/MRV）
    StructuredQueryType.MUSCLE_CAPACITY: """
        MATCH (m:Muscle)
        WHERE m.name_zh CONTAINS $keyword
        RETURN m.name_zh AS muscle,
               m.MEV AS mev,
               m.MAV AS mav,
               m.MRV AS mrv,
               m.training_frequency AS frequency,
               m.recovery_time AS recovery_time
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
}

# ─── 实体同义词映射（用户常用名 → Neo4j 实际名称） ─────────

MUSCLE_SYNONYMS = {
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

        try:
            neo4j = self._get_neo4j()
            raw_results = neo4j.execute_query(template, {"keyword": normalized_entity})

            if not raw_results:
                logger.info(f"Neo4j 查询无结果: {query_type.value}, entity='{entity}'→'{normalized_entity}'")
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

        return str(row)
