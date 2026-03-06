# -*- coding: utf-8 -*-
"""
企业级三层检索引擎 - DAML-RAG框架核心组件

基于GraphRAG v3简洁架构,增强Neo4j直接连接能力,实现真正的三层检索。

三层架构:
- Layer 1: 向量语义检索 (Qdrant via GraphRAG API)
- Layer 2: 图谱关系推理 (Neo4j Direct Connection with Fallback)
- Layer 3: 专业规则约束 (Business Rules Engine)

设计原则:
1. 连接池管理 - 企业级Neo4j连接管理
2. 优雅降级 - Neo4j失败时自动降级到API
3. 清晰分层 - 每层职责明确,互不耦合
4. 完善监控 - 详细日志和性能指标
5. 统一超时 - 全局超时配置管理 (Requirements 3.6)

版本: v2.1.0
日期: 2026-01-11
作者: 薛小川

注意: 实际实现在 three_layer 子模块中，本文件为兼容性别名。
"""

from .three_layer import (
    TrueThreeLayerEngine,
    ThreeLayerResult,
    LayerExecutionResult,
    Neo4jConnectionManager,
)

__all__ = [
    "TrueThreeLayerEngine",
    "ThreeLayerResult",
    "LayerExecutionResult",
    "Neo4jConnectionManager",
]
