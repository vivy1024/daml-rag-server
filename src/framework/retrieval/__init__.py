# -*- coding: utf-8 -*-
"""
DAML-RAG检索模块（v3.1增强版）

核心组件：
- Neo4j图数据库管理
- Qdrant向量搜索
- 完整知识图谱系统
- 三层检索引擎
- Layer3规则引擎（增强版）
- 动态上下文构建器

版本: v3.1.0
日期: 2026-01-06
"""

# v3.0: 核心组件
from .graph.neo4j_manager import Neo4jManager
from .graph.vector_search_engine import VectorSearchEngine
from .graph.kg_full import KnowledgeGraphFull

# v3.1: 三层检索引擎
from .true_three_layer_engine import TrueThreeLayerEngine, ThreeLayerResult, LayerExecutionResult

# v3.1: Layer3规则引擎（增强版）
from .layer3_rule_engine import (
    Layer3RuleEngine,
    RuleExecutionResult,
    Layer3ExecutionLog,
    ForceType,
    KineticChainType,
    BodyType,
    TrainingGoal,
)

# v3.1: 动态上下文构建器
from .dynamic_context_builder import (
    DynamicContextBuilder,
    ContextResult,
    EntityInfo,
    RelationshipInfo,
    QueryType,
    RelationshipType,
)

__all__ = [
    # 核心组件
    "Neo4jManager",
    "VectorSearchEngine",
    "KnowledgeGraphFull",
    # 三层检索引擎
    "TrueThreeLayerEngine",
    "ThreeLayerResult",
    "LayerExecutionResult",
    # Layer3规则引擎
    "Layer3RuleEngine",
    "RuleExecutionResult",
    "Layer3ExecutionLog",
    "ForceType",
    "KineticChainType",
    "BodyType",
    "TrainingGoal",
    # 动态上下文构建器
    "DynamicContextBuilder",
    "ContextResult",
    "EntityInfo",
    "RelationshipInfo",
    "QueryType",
    "RelationshipType",
]
