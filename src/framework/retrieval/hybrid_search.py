# -*- coding: utf-8 -*-
"""
混合检索引擎：向量检索 + BM25全文检索 + RRF融合
支持按意图类型动态调整 BM25/向量权重
"""
import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from .bm25_engine import get_bm25_engine
from .reranker import FitnessReranker

logger = logging.getLogger(__name__)

KNOWLEDGE_ARTICLES_COLLECTION = "knowledge_articles"
TRAINING_KNOWLEDGE_COLLECTION = "training_knowledge"

# ─── 意图→检索权重映射 (vector_weight, bm25_weight) ─────────────────────────
# 健身领域关键词匹配（BM25）通常比语义相似度更精准，默认偏向 BM25
INTENT_WEIGHTS: Dict[str, Tuple[float, float]] = {
    "STRUCTURED": (0.2, 0.8),   # 结构化查询：强偏 BM25（关键词精确匹配）
    "HYBRID":     (0.5, 0.5),   # 混合查询：均衡（有实体但语义也重要）
    "SEMANTIC":   (0.3, 0.7),   # 语义查询：偏 BM25（健身领域默认）
}
DEFAULT_WEIGHTS: Tuple[float, float] = (0.3, 0.7)  # 默认偏向 BM25


class HybridSearchEngine:
    """混合检索引擎：向量 + BM25 + RRF融合"""

    def __init__(
        self,
        rrf_k: int = 60
    ):
        """
        初始化混合检索引擎

        Args:
            rrf_k: RRF融合参数
        """
        self.rrf_k = rrf_k
        self.bm25_engine = get_bm25_engine()
        self._encoder = None  # 懒加载 GTE-Large-zh

        logger.info(f"初始化混合检索引擎: RRF_k={rrf_k}")

    async def vector_search(
        self,
        query: str,
        domain: str = "fitness",
        top_k: int = 20,
        filters: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """
        向量检索（直接查 Qdrant training_knowledge collection，与 BM25 同源）

        Args:
            query: 查询文本
            domain: 领域
            top_k: 返回结果数
            filters: 过滤条件
            user_id: 用户ID

        Returns:
            检索结果列表
        """
        try:
            from ...framework.clients.qdrant_client import get_qdrant_client
            qdrant = get_qdrant_client()

            vector = await asyncio.to_thread(self._embed, query)

            response = await asyncio.to_thread(
                qdrant.query_points,
                collection_name=TRAINING_KNOWLEDGE_COLLECTION,
                query=vector,
                limit=top_k,
            )

            points = response.points if hasattr(response, "points") else response
            unified_results = []
            for p in points:
                payload = p.payload or {}
                text = payload.get('chunk_text') or payload.get('text', '')
                unified_results.append({
                    'id': str(p.id),
                    'score': round(p.score, 4),
                    'text': text,
                    'payload': payload
                })

            logger.info(f"向量检索完成: {len(unified_results)} 个结果")
            return unified_results

        except Exception as e:
            logger.error(f"向量检索异常: {e}")
            return []

    def bm25_search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        BM25全文检索

        Args:
            query: 查询文本
            top_k: 返回结果数

        Returns:
            检索结果列表
        """
        return self.bm25_engine.search(query, top_k)

    def _embed(self, text: str) -> List[float]:
        """向量化文本（懒加载 GTE-Large-zh）"""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            from ..config.app_config import get_config
            config = get_config()
            model_name = config.framework.embedding_model
            self._encoder = SentenceTransformer(model_name)
            logger.info(f"HybridSearchEngine 加载向量模型: {model_name}")
        return self._encoder.encode(text).tolist()

    async def search_knowledge_articles(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        检索 knowledge_articles Qdrant collection

        Args:
            query: 查询文本
            top_k: 返回结果数

        Returns:
            知识库文章检索结果，每条携带 source_type="knowledge_article"
            以及 article_id、title、source_book 字段
        """
        try:
            from ...framework.clients.qdrant_client import get_qdrant_client
            qdrant = get_qdrant_client()

            # 检查 collection 是否存在（优雅降级）
            collections = await asyncio.to_thread(qdrant.get_collections)
            collection_names = [c.name for c in collections.collections]
            if KNOWLEDGE_ARTICLES_COLLECTION not in collection_names:
                logger.warning(
                    f"knowledge_articles collection 不存在，跳过知识库检索"
                )
                return []

            vector = await asyncio.to_thread(self._embed, query)

            response = await asyncio.to_thread(
                qdrant.query_points,
                collection_name=KNOWLEDGE_ARTICLES_COLLECTION,
                query=vector,
                limit=top_k,
            )

            points = response.points if hasattr(response, "points") else response
            results = []
            for p in points:
                payload = p.payload or {}
                results.append({
                    "id": str(p.id),
                    "score": round(p.score, 4),
                    "text": payload.get("content", payload.get("text", "")),
                    "payload": payload,
                    "source_type": "knowledge_article",
                    "article_id": payload.get("article_id", str(p.id)),
                    "title": payload.get("title", ""),
                    "source_book": payload.get("source_book", ""),
                    "chapter": payload.get("chapter", ""),
                })

            logger.info(
                f"knowledge_articles 检索完成: {len(results)} 个结果"
            )
            return results

        except Exception as e:
            logger.warning(f"knowledge_articles 检索失败，跳过: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        domain: str = "fitness",
        top_k: int = 10,
        vector_top_k: int = 20,
        bm25_top_k: int = 20,
        filters: Optional[Dict] = None,
        user_id: Optional[str] = None,
        intent_type: Optional[str] = None
    ) -> List[Dict]:
        """
        混合检索：向量 + BM25 + 加权RRF融合

        Args:
            query: 查询文本
            domain: 领域
            top_k: 最终返回结果数
            vector_top_k: 向量检索召回数
            bm25_top_k: BM25检索召回数
            filters: 过滤条件
            user_id: 用户ID
            intent_type: 意图类型（STRUCTURED/HYBRID/SEMANTIC），用于动态调整权重

        Returns:
            融合后的检索结果列表
        """
        # 根据意图类型选择权重
        vec_w, bm25_w = INTENT_WEIGHTS.get(intent_type, DEFAULT_WEIGHTS) if intent_type else DEFAULT_WEIGHTS

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🔍 混合检索: {query}")
        logger.info(f"   权重: vector={vec_w}, bm25={bm25_w} (intent={intent_type or 'default'})")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 1. 向量检索
        logger.info("→ 执行向量检索...")
        vector_results = await self.vector_search(
            query=query,
            domain=domain,
            top_k=vector_top_k,
            filters=filters,
            user_id=user_id
        )

        # 2. BM25检索
        logger.info("→ 执行BM25检索...")
        bm25_results = self.bm25_search(query, top_k=bm25_top_k)

        # 3. 加权RRF融合
        logger.info(f"→ 执行加权RRF融合 (vec={vec_w}, bm25={bm25_w})...")
        fused_results = FitnessReranker.rrf_fusion(
            result_lists=[vector_results, bm25_results],
            k=self.rrf_k,
            id_field='id',
            weights=[vec_w, bm25_w]
        )

        # 4. 返回top_k
        final_results = fused_results[:top_k]

        logger.info(
            f"✅ 混合检索完成: 向量{len(vector_results)} + BM25{len(bm25_results)} "
            f"→ RRF融合{len(fused_results)} → 返回{len(final_results)}"
        )

        return final_results


# 便捷函数
def get_hybrid_search_engine() -> HybridSearchEngine:
    """获取混合检索引擎实例"""
    return HybridSearchEngine()
