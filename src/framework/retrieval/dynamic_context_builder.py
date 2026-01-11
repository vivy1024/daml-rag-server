# -*- coding: utf-8 -*-
"""
动态上下文构建器 - 类似GraphRAG的LocalContextBuilder

基于设计文档Requirements 13.1-13.5实现的动态上下文构建器。

功能:
1. 实体-关系上下文构建
2. 多跳推理支持（1-hop, 2-hop）
3. 相关性评分计算
4. 查询类型支持（local, hybrid）

版本: v1.0.0
日期: 2026-01-06
作者: 薛小川
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


# ============ 枚举定义 ============

class QueryType(Enum):
    """查询类型"""
    LOCAL = "local"       # 实体聚焦查询
    HYBRID = "hybrid"     # 实体 + 语义混合查询
    GLOBAL = "global"     # 全局查询


class RelationshipType(Enum):
    """关系类型"""
    # 肌肉关系
    TARGETS_PRIMARY = "TARGETS_PRIMARY"
    TARGETS_SECONDARY = "TARGETS_SECONDARY"
    SYNERGIST = "SYNERGIST"
    
    # 器械关系
    REQUIRES = "REQUIRES"
    
    # 动作关系
    VARIATION_OF = "VARIATION_OF"
    SIMILAR_TO = "SIMILAR_TO"
    PROGRESSION_OF = "PROGRESSION_OF"
    
    # 分类关系
    USES_FORCE = "USES_FORCE"
    HAS_MECHANIC = "HAS_MECHANIC"
    HAS_KINETIC_CHAIN = "HAS_KINETIC_CHAIN"
    USES_GRIP = "USES_GRIP"
    SUITABLE_FOR_LEVEL = "SUITABLE_FOR_LEVEL"
    
    # 安全关系
    INVOLVES_JOINT = "INVOLVES_JOINT"
    CONTRAINDICATED_FOR = "CONTRAINDICATED_FOR"
    
    # 体态关系
    CORRECTS = "CORRECTS"
    AGGRAVATES = "AGGRAVATES"
    RELATED_TO = "RELATED_TO"


# ============ 数据类定义 ============

@dataclass
class EntityInfo:
    """实体信息"""
    id: str
    name: str
    name_zh: Optional[str] = None
    node_type: str = "Unknown"
    properties: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0


@dataclass
class RelationshipInfo:
    """关系信息"""
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    hop_distance: int = 1


@dataclass
class ContextResult:
    """上下文构建结果"""
    entities: List[EntityInfo]
    relationships: List[RelationshipInfo]
    secondary_connections: List[RelationshipInfo]
    query: str
    query_type: QueryType
    execution_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============ 动态上下文构建器 ============

class DynamicContextBuilder:
    """
    动态上下文构建器 - 类似GraphRAG的LocalContextBuilder
    
    实现Requirements:
    - 13.1: 实体-关系上下文构建
    - 13.2: 多跳推理支持
    - 13.3: 相关性评分计算
    - 13.4: 二跳邻居扩展
    - 13.5: 查询类型支持（local, hybrid）
    
    框架层领域无关 - Requirements 6.1, 6.2:
    - 关键词配置通过domain_adapter获取
    """
    
    # 关系权重配置（用于相关性评分）
    RELATIONSHIP_WEIGHTS = {
        # 高权重关系（直接相关）
        RelationshipType.TARGETS_PRIMARY.value: 1.0,
        RelationshipType.VARIATION_OF.value: 0.95,
        RelationshipType.PROGRESSION_OF.value: 0.9,
        
        # 中等权重关系
        RelationshipType.TARGETS_SECONDARY.value: 0.8,
        RelationshipType.SYNERGIST.value: 0.75,
        RelationshipType.SIMILAR_TO.value: 0.7,
        RelationshipType.REQUIRES.value: 0.7,
        
        # 分类关系
        RelationshipType.USES_FORCE.value: 0.6,
        RelationshipType.HAS_MECHANIC.value: 0.6,
        RelationshipType.HAS_KINETIC_CHAIN.value: 0.6,
        RelationshipType.SUITABLE_FOR_LEVEL.value: 0.5,
        
        # 安全关系
        RelationshipType.INVOLVES_JOINT.value: 0.5,
        RelationshipType.CONTRAINDICATED_FOR.value: 0.4,
        
        # 体态关系
        RelationshipType.CORRECTS.value: 0.8,
        RelationshipType.AGGRAVATES.value: 0.7,
        RelationshipType.RELATED_TO.value: 0.5,
        
        # 默认权重
        "default": 0.5
    }
    
    def __init__(
        self,
        neo4j_manager=None,
        vector_search_engine=None,
        domain_adapter=None,
        max_hops: int = 2,
        max_entities_per_hop: int = 20
    ):
        """
        初始化动态上下文构建器
        
        Args:
            neo4j_manager: Neo4j管理器
            vector_search_engine: 向量搜索引擎
            domain_adapter: 领域适配器（用于获取领域特定配置）
            max_hops: 最大跳数（默认2跳）
            max_entities_per_hop: 每跳最大实体数
        """
        self.neo4j_manager = neo4j_manager
        self.vector_search_engine = vector_search_engine
        self.domain_adapter = domain_adapter
        self.max_hops = max_hops
        self.max_entities_per_hop = max_entities_per_hop
        
        # 从domain_adapter加载关键词配置
        self._load_domain_keywords()
        
        logger.info(
            f"DynamicContextBuilder initialized: max_hops={max_hops}, "
            f"max_entities_per_hop={max_entities_per_hop}"
        )
    
    def _load_domain_keywords(self):
        """从domain_adapter加载领域特定关键词"""
        if self.domain_adapter and hasattr(self.domain_adapter, 'get_keyword_mapping'):
            keyword_mapping = self.domain_adapter.get_keyword_mapping()
            # 展开关键词映射为列表
            self._domain_keywords = []
            for key, synonyms in keyword_mapping.items():
                self._domain_keywords.append(key)
                self._domain_keywords.extend(synonyms)
            logger.info(f"从domain_adapter加载 {len(self._domain_keywords)} 个领域关键词")
        else:
            self._domain_keywords = []
            logger.debug("未配置domain_adapter，使用空关键词列表")
    
    async def build_context(
        self,
        query: str,
        seed_entities: List[Dict[str, Any]],
        query_type: QueryType = QueryType.HYBRID,
        max_hops: Optional[int] = None,
        include_secondary: bool = True
    ) -> ContextResult:
        """
        构建实体-关系上下文
        
        Args:
            query: 用户查询
            seed_entities: 种子实体列表（来自Layer1/Layer2）
            query_type: 查询类型
            max_hops: 最大跳数（覆盖默认值）
            include_secondary: 是否包含二跳连接
            
        Returns:
            ContextResult: 上下文构建结果
        """
        start_time = datetime.now()
        max_hops = max_hops or self.max_hops
        
        logger.info(f"构建上下文: query='{query[:50]}...', seeds={len(seed_entities)}")
        
        entities: List[EntityInfo] = []
        relationships: List[RelationshipInfo] = []
        secondary_connections: List[RelationshipInfo] = []
        
        # 处理种子实体
        seed_entity_ids: Set[str] = set()
        for seed in seed_entities:
            entity_info = self._extract_entity_info(seed)
            if entity_info:
                entities.append(entity_info)
                seed_entity_ids.add(entity_info.id)
        
        # 获取一跳关系
        if self.neo4j_manager and seed_entity_ids:
            one_hop_rels = await self._get_relationships(
                entity_ids=list(seed_entity_ids),
                hop=1
            )
            relationships.extend(one_hop_rels)
            
            # 获取二跳关系（如果需要）
            if include_secondary and max_hops >= 2:
                # 收集一跳邻居的ID
                one_hop_neighbor_ids = set()
                for rel in one_hop_rels:
                    if rel.target_id not in seed_entity_ids:
                        one_hop_neighbor_ids.add(rel.target_id)
                    if rel.source_id not in seed_entity_ids:
                        one_hop_neighbor_ids.add(rel.source_id)
                
                # 限制邻居数量
                one_hop_neighbor_ids = set(list(one_hop_neighbor_ids)[:self.max_entities_per_hop])
                
                if one_hop_neighbor_ids:
                    two_hop_rels = await self._get_relationships(
                        entity_ids=list(one_hop_neighbor_ids),
                        hop=2
                    )
                    secondary_connections.extend(two_hop_rels)
        
        # 计算相关性评分
        entities = await self._rate_relevancy(entities, query)
        
        # 按相关性排序
        entities.sort(key=lambda x: x.relevance_score, reverse=True)
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = ContextResult(
            entities=entities,
            relationships=relationships,
            secondary_connections=secondary_connections,
            query=query,
            query_type=query_type,
            execution_time_ms=execution_time,
            metadata={
                "seed_count": len(seed_entities),
                "entity_count": len(entities),
                "relationship_count": len(relationships),
                "secondary_count": len(secondary_connections),
                "max_hops": max_hops
            }
        )
        
        logger.info(
            f"上下文构建完成: {len(entities)}实体, {len(relationships)}关系, "
            f"{len(secondary_connections)}二跳连接, {execution_time:.1f}ms"
        )
        
        return result
    
    async def multi_hop_reasoning(
        self,
        query: str,
        start_entity: Dict[str, Any],
        target_relationship: str,
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """
        多跳推理 - 支持关系链查询
        
        Requirements: 13.2
        
        示例: "推荐和深蹲相似的动作" → VARIATION_OF → similar exercises
        
        Args:
            query: 用户查询
            start_entity: 起始实体
            target_relationship: 目标关系类型
            max_hops: 最大跳数
            
        Returns:
            List[Dict]: 推理结果列表
        """
        if not self.neo4j_manager:
            logger.warning("Neo4j管理器未配置，无法执行多跳推理")
            return []
        
        start_id = start_entity.get("id") or start_entity.get("exercise_id")
        if not start_id:
            return []
        
        logger.info(f"多跳推理: start={start_id}, rel={target_relationship}, hops={max_hops}")
        
        results = []
        
        try:
            # 构建多跳Cypher查询
            cypher_query = f"""
            MATCH path = (start:Exercise {{id: $start_id}})-[r:{target_relationship}*1..{max_hops}]-(end:Exercise)
            WHERE start <> end
            RETURN DISTINCT
                end.id AS id,
                end.name AS name,
                end.name_zh AS name_zh,
                end.difficulty AS difficulty,
                end.equipment_zh AS equipment,
                length(path) AS hop_distance,
                type(r[0]) AS relationship_type
            ORDER BY hop_distance ASC
            LIMIT 20
            """
            
            # 执行查询
            with self.neo4j_manager.get_session() as session:
                result = session.run(cypher_query, start_id=str(start_id))
                
                for record in result:
                    results.append({
                        "id": record.get("id"),
                        "name": record.get("name"),
                        "name_zh": record.get("name_zh"),
                        "difficulty": record.get("difficulty_zh") or record.get("difficulty_en"),
                        "equipment": record.get("equipment_zh"),
                        "hop_distance": record.get("hop_distance"),
                        "relationship_type": record.get("relationship_type"),
                        "source": "multi_hop_reasoning"
                    })
            
            logger.info(f"多跳推理完成: {len(results)}个结果")
            
        except Exception as e:
            logger.error(f"多跳推理失败: {e}")
        
        return results

    
    async def rate_relevancy(
        self,
        candidates: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """
        计算相关性评分
        
        Requirements: 13.3
        
        评分因素:
        1. 语义相似度（向量距离）
        2. 实体匹配度（关键词匹配）
        3. 关系权重（关系类型重要性）
        
        Args:
            candidates: 候选列表
            query: 用户查询
            
        Returns:
            List[Dict]: 带相关性评分的候选列表
        """
        if not candidates:
            return []
        
        # 提取查询关键词
        query_keywords = self._extract_keywords(query)
        
        for candidate in candidates:
            # 1. 语义相似度（如果有向量分数）
            semantic_score = candidate.get("score", 0.5)
            
            # 2. 实体匹配度
            entity_score = self._compute_entity_match(query_keywords, candidate)
            
            # 3. 关系权重（如果有关系信息）
            relationship_score = self._compute_relationship_score(candidate)
            
            # 综合评分（加权平均）
            relevancy_score = (
                0.5 * semantic_score +
                0.3 * entity_score +
                0.2 * relationship_score
            )
            
            candidate["relevancy_score"] = round(relevancy_score, 4)
        
        # 按相关性排序
        candidates.sort(key=lambda x: x.get("relevancy_score", 0), reverse=True)
        
        return candidates
    
    async def expand_context(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        direction: str = "both"
    ) -> Dict[str, Any]:
        """
        扩展实体上下文 - 获取实体的邻居和关系
        
        Args:
            entity_id: 实体ID
            relationship_types: 关系类型过滤（None表示所有）
            direction: 方向（in, out, both）
            
        Returns:
            Dict: 扩展的上下文信息
        """
        if not self.neo4j_manager:
            return {"entity_id": entity_id, "neighbors": [], "relationships": []}
        
        neighbors = []
        relationships = []
        
        try:
            # 构建方向条件
            if direction == "out":
                pattern = "(e)-[r]->(n)"
            elif direction == "in":
                pattern = "(e)<-[r]-(n)"
            else:
                pattern = "(e)-[r]-(n)"
            
            # 构建关系类型过滤
            rel_filter = ""
            if relationship_types:
                rel_types = "|".join(relationship_types)
                rel_filter = f":{rel_types}"
            
            cypher_query = f"""
            MATCH {pattern.replace('[r]', f'[r{rel_filter}]')}
            WHERE e.id = $entity_id
            RETURN
                n.id AS neighbor_id,
                n.name AS neighbor_name,
                n.name_zh AS neighbor_name_zh,
                labels(n)[0] AS neighbor_type,
                type(r) AS relationship_type,
                properties(r) AS relationship_props
            LIMIT 50
            """
            
            with self.neo4j_manager.get_session() as session:
                result = session.run(cypher_query, entity_id=str(entity_id))
                
                for record in result:
                    neighbors.append({
                        "id": record.get("neighbor_id"),
                        "name": record.get("neighbor_name"),
                        "name_zh": record.get("neighbor_name_zh"),
                        "type": record.get("neighbor_type")
                    })
                    
                    relationships.append({
                        "type": record.get("relationship_type"),
                        "target_id": record.get("neighbor_id"),
                        "properties": record.get("relationship_props", {})
                    })
        
        except Exception as e:
            logger.error(f"扩展上下文失败: {e}")
        
        return {
            "entity_id": entity_id,
            "neighbors": neighbors,
            "relationships": relationships,
            "neighbor_count": len(neighbors)
        }
    
    # ============ 私有方法 ============
    
    def _extract_entity_info(self, entity: Dict[str, Any]) -> Optional[EntityInfo]:
        """从字典提取实体信息"""
        entity_id = entity.get("id") or entity.get("exercise_id") or entity.get("name")
        if not entity_id:
            return None
        
        return EntityInfo(
            id=str(entity_id),
            name=entity.get("name") or entity.get("exercise_name_en", ""),
            name_zh=entity.get("name_zh") or entity.get("exercise_name_zh", ""),
            node_type=entity.get("node_type", "Exercise"),
            properties={
                k: v for k, v in entity.items()
                if k not in ["id", "name", "name_zh", "node_type"]
            },
            relevance_score=entity.get("score", 0.5)
        )
    
    async def _get_relationships(
        self,
        entity_ids: List[str],
        hop: int = 1
    ) -> List[RelationshipInfo]:
        """获取实体的关系"""
        if not self.neo4j_manager or not entity_ids:
            return []
        
        relationships = []
        
        try:
            cypher_query = """
            MATCH (e)-[r]-(n)
            WHERE e.id IN $entity_ids
            RETURN
                e.id AS source_id,
                n.id AS target_id,
                type(r) AS relationship_type,
                properties(r) AS properties
            LIMIT 100
            """
            
            with self.neo4j_manager.get_session() as session:
                result = session.run(cypher_query, entity_ids=entity_ids)
                
                for record in result:
                    relationships.append(RelationshipInfo(
                        source_id=str(record.get("source_id", "")),
                        target_id=str(record.get("target_id", "")),
                        relationship_type=record.get("relationship_type", ""),
                        properties=record.get("properties", {}),
                        hop_distance=hop
                    ))
        
        except Exception as e:
            logger.error(f"获取关系失败: {e}")
        
        return relationships
    
    async def _rate_relevancy(
        self,
        entities: List[EntityInfo],
        query: str
    ) -> List[EntityInfo]:
        """计算实体相关性评分"""
        query_keywords = self._extract_keywords(query)
        
        for entity in entities:
            # 名称匹配
            name_score = 0.0
            entity_name = (entity.name or "").lower()
            entity_name_zh = entity.name_zh or ""
            
            for keyword in query_keywords:
                if keyword.lower() in entity_name or keyword in entity_name_zh:
                    name_score += 0.3
            
            # 属性匹配
            prop_score = 0.0
            for key, value in entity.properties.items():
                if isinstance(value, str):
                    for keyword in query_keywords:
                        if keyword.lower() in value.lower():
                            prop_score += 0.1
            
            # 综合评分
            entity.relevance_score = min(1.0, entity.relevance_score + name_score + prop_score)
        
        return entities
    
    def _extract_keywords(self, query: str) -> List[str]:
        """从查询中提取关键词
        
        框架层领域无关 - Requirements 6.1, 6.2:
        - 使用domain_adapter提供的关键词列表
        """
        keywords = []
        query_lower = query.lower()
        
        # 使用实例变量（从domain_adapter加载）
        for kw in self._domain_keywords:
            if kw.lower() in query_lower or kw in query:
                keywords.append(kw)
        
        return keywords
    
    def _compute_entity_match(
        self,
        query_keywords: List[str],
        candidate: Dict[str, Any]
    ) -> float:
        """计算实体匹配度"""
        if not query_keywords:
            return 0.5
        
        match_count = 0
        
        # 检查名称匹配
        name = (candidate.get("name") or candidate.get("exercise_name_en") or "").lower()
        name_zh = candidate.get("name_zh") or candidate.get("exercise_name_zh") or ""
        
        for keyword in query_keywords:
            if keyword.lower() in name or keyword in name_zh:
                match_count += 1
        
        # 检查目标肌肉匹配
        target_muscle = candidate.get("target_muscle") or ""
        for keyword in query_keywords:
            if keyword in target_muscle:
                match_count += 0.5
        
        # 归一化
        return min(1.0, match_count / max(len(query_keywords), 1))
    
    def _compute_relationship_score(self, candidate: Dict[str, Any]) -> float:
        """计算关系权重分数"""
        relationship_type = candidate.get("relationship_type", "")
        
        if not relationship_type:
            return 0.5
        
        return self.RELATIONSHIP_WEIGHTS.get(
            relationship_type,
            self.RELATIONSHIP_WEIGHTS["default"]
        )
