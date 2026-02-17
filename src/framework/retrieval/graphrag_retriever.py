# -*- coding: utf-8 -*-
"""
GraphRAG 统一检索器 - 基于 neo4j-graphrag-python 官方包

替代 DAML-RAG 自研的 Layer1(Qdrant向量搜索) + Layer2(Neo4j图搜索)，
使用 neo4j-graphrag-python 的 QdrantNeo4jRetriever 一步完成
向量搜索→Neo4j节点关联。

核心优势：
1. QdrantNeo4jRetriever: 向量搜索结果自动关联 Neo4j 节点属性
2. HybridRetriever: BM25全文 + 向量语义混合检索
3. VectorCypherRetriever: 向量搜索 + Cypher图遍历一步完成

兼容性：
- 实现与 true_three_layer_engine 相同的 search() 接口
- 支持降级到旧引擎（fallback）
- Layer3 安全约束保持不变

版本: v1.0.0
日期: 2026-02-16
作者: Carol-AI架构师 (Team Lead 接手完成)
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional

import yaml

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "retrieval_config.yaml"
)


def _load_config() -> Dict[str, Any]:
    """加载检索配置"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("retrieval", {})
    except Exception as e:
        logger.warning(f"加载检索配置失败，使用默认值: {e}")
        return {
            "default_mode": "hybrid",
            "hybrid_weights": {"bm25": 0.3, "vector": 0.7},
            "top_k": 15,
        }


class FitnessGraphRAGRetriever:
    """
    统一 GraphRAG 检索接口

    替代 DAML-RAG 的 Layer1(Qdrant) + Layer2(Neo4j)，
    使用 neo4j-graphrag-python 官方包实现。

    接口兼容 true_three_layer_engine.search(query, domain, top_k)
    """

    def __init__(
        self,
        neo4j_driver=None,
        qdrant_client=None,
        embedder=None,
        fallback_engine=None,
    ):
        """
        初始化 GraphRAG 检索器

        Args:
            neo4j_driver: Neo4j 异步驱动
            qdrant_client: Qdrant 客户端
            embedder: 嵌入模型（GTE-Large-zh）
            fallback_engine: 降级引擎（旧的 true_three_layer_engine）
        """
        self.neo4j_driver = neo4j_driver
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.fallback_engine = fallback_engine
        self.config = _load_config()
        self._initialized = False

        # 延迟初始化 retrievers（等待依赖注入完成）
        self._qdrant_retriever = None
        self._hybrid_retriever = None

    def _ensure_initialized(self):
        """延迟初始化 neo4j-graphrag retrievers"""
        if self._initialized:
            return

        try:
            from neo4j_graphrag.retrievers import (
                QdrantNeo4jRetriever,
                HybridRetriever,
            )

            qdrant_cfg = self.config.get("qdrant", {})
            neo4j_cfg = self.config.get("neo4j", {})

            # QdrantNeo4jRetriever: 向量搜索→Neo4j节点关联
            if self.neo4j_driver and self.qdrant_client and self.embedder:
                self._qdrant_retriever = QdrantNeo4jRetriever(
                    driver=self.neo4j_driver,
                    client=self.qdrant_client,
                    collection_name=qdrant_cfg.get(
                        "collection_name", "fitness-exercises"
                    ),
                    id_property_external=qdrant_cfg.get(
                        "id_property_external", "neo4j_id"
                    ),
                    id_property_neo4j="id",
                    embedder=self.embedder,
                )
                logger.info("✅ QdrantNeo4jRetriever 初始化成功")

            # HybridRetriever: BM25 + 向量混合检索
            if self.neo4j_driver and self.embedder:
                self._hybrid_retriever = HybridRetriever(
                    driver=self.neo4j_driver,
                    vector_index_name=neo4j_cfg.get(
                        "vector_index_name", "exercise-embeddings"
                    ),
                    fulltext_index_name=neo4j_cfg.get(
                        "fulltext_index_name", "exercise-fulltext"
                    ),
                    embedder=self.embedder,
                )
                logger.info("✅ HybridRetriever 初始化成功")

            self._initialized = True

        except ImportError:
            logger.warning(
                "⚠️ neo4j-graphrag 未安装，将使用降级引擎。"
                "请运行: pip install neo4j-graphrag[qdrant]"
            )
        except Exception as e:
            logger.error(f"❌ GraphRAG Retriever 初始化失败: {e}")

    async def search(
        self,
        query: str,
        domain: str = "fitness",
        top_k: int = None,
        mode: str = None,
        user_level: str = None,  # 新增：用户健身水平
    ) -> Dict[str, Any]:
        """
        执行检索（兼容 true_three_layer_engine.search 接口）

        Args:
            query: 用户查询文本
            domain: 领域（默认 fitness）
            top_k: 返回结果数（默认从配置读取）
            mode: 检索模式 hybrid/vector/cypher（默认从配置读取）
            user_level: 用户健身水平（beginner/intermediate/advanced等）

        Returns:
            Dict: {
                "results": [...],
                "query_type": "graphrag_hybrid",
                "domain": "fitness",
                "count": int,
                "retriever": "neo4j-graphrag-python"
            }
        """
        top_k = top_k or self.config.get("top_k", 15)
        mode = mode or self.config.get("default_mode", "hybrid")

        self._ensure_initialized()

        # 尝试使用新的 GraphRAG 检索
        try:
            if mode == "hybrid" and self._hybrid_retriever:
                result = await asyncio.to_thread(
                    self._hybrid_retriever.search,
                    query_text=query, top_k=top_k
                )
                return self._format_result(result, query, domain, "graphrag_hybrid", user_level)

            elif self._qdrant_retriever:
                result = await asyncio.to_thread(
                    self._qdrant_retriever.search,
                    query_text=query, top_k=top_k
                )
                return self._format_result(result, query, domain, "graphrag_vector", user_level)

        except Exception as e:
            logger.warning(f"⚠️ GraphRAG 检索失败，尝试降级: {e}")

        # 降级到旧引擎
        if self.fallback_engine:
            logger.info("🔄 降级到旧三层检索引擎")
            return await self.fallback_engine.search(
                query=query, domain=domain, top_k=top_k
            )

        # 无可用引擎
        logger.error("❌ 无可用检索引擎")
        return {"results": [], "count": 0, "domain": domain, "query_type": "none"}

    def _format_result(
        self, raw_result, query: str, domain: str, query_type: str, user_level: str = None
    ) -> Dict[str, Any]:
        """将 neo4j-graphrag 结果格式化为兼容格式"""
        items = []

        if hasattr(raw_result, "items"):
            for item in raw_result.items:
                items.append(
                    {
                        "content": getattr(item, "content", str(item)),
                        "metadata": getattr(item, "metadata", {}),
                        "score": getattr(item, "score", 0.0),
                    }
                )
        elif isinstance(raw_result, list):
            for item in raw_result:
                if isinstance(item, dict):
                    items.append(item)
                else:
                    items.append({"content": str(item), "score": 0.0})

        result = {
            "results": items,
            "query_type": query_type,
            "domain": domain,
            "count": len(items),
            "retriever": "neo4j-graphrag-python",
        }

        # 如果提供了user_level，添加到结果metadata中
        if user_level:
            result["user_level_filter"] = user_level

        return result
