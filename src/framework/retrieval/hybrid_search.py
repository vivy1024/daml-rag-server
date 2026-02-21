# -*- coding: utf-8 -*-
"""
混合检索引擎：向量检索 + BM25全文检索 + RRF融合
"""
import asyncio
import logging
import os
from typing import List, Dict, Optional
import aiohttp
from .bm25_engine import get_bm25_engine
from .reranker import FitnessReranker

logger = logging.getLogger(__name__)

KNOWLEDGE_ARTICLES_COLLECTION = "knowledge_articles"


class HybridSearchEngine:
    """混合检索引擎：向量 + BM25 + RRF融合"""

    def __init__(
        self,
        graphrag_api_base: str = "http://localhost:8001/api/v1/graphrag",
        rrf_k: int = 60
    ):
        """
        初始化混合检索引擎

        Args:
            graphrag_api_base: GraphRAG API地址
            rrf_k: RRF融合参数
        """
        self.graphrag_api_base = graphrag_api_base
        self.rrf_k = rrf_k
        self.bm25_engine = get_bm25_engine()
        self._encoder = None  # 懒加载 GTE-Large-zh，用于 knowledge_articles 检索

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
        向量检索（通过GraphRAG API）

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
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.graphrag_api_base}/query",
                    json={
                        "query_text": query,
                        "domain": domain,
                        "query_type": "semantic_search",
                        "top_k": top_k,
                        "filters": filters or {},
                        "return_reason": False,
                        "user_id": user_id or "anonymous"
                    },
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("data", {}).get("results", [])

                        # 转换为统一格式
                        unified_results = []
                        for r in results:
                            unified_results.append({
                                'id': r.get('id', ''),
                                'score': r.get('score', 0.0),
                                'text': r.get('text', ''),
                                'payload': r.get('metadata', {})
                            })

                        logger.info(f"向量检索完成: {len(unified_results)} 个结果")
                        return unified_results
                    else:
                        logger.error(f"向量检索失败: HTTP {response.status}")
                        return []

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
            model_name = os.getenv("EMBEDDING_MODEL", "thenlper/gte-large-zh")
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
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """
        混合检索：向量 + BM25 + RRF融合

        Args:
            query: 查询文本
            domain: 领域
            top_k: 最终返回结果数
            vector_top_k: 向量检索召回数
            bm25_top_k: BM25检索召回数
            filters: 过滤条件
            user_id: 用户ID

        Returns:
            融合后的检索结果列表
        """
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🔍 混合检索: {query}")
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

        # 3. RRF融合
        logger.info("→ 执行RRF融合...")
        fused_results = FitnessReranker.rrf_fusion(
            result_lists=[vector_results, bm25_results],
            k=self.rrf_k,
            id_field='id'
        )

        # 4. 返回top_k
        final_results = fused_results[:top_k]

        logger.info(
            f"✅ 混合检索完成: 向量{len(vector_results)} + BM25{len(bm25_results)} "
            f"→ RRF融合{len(fused_results)} → 返回{len(final_results)}"
        )

        return final_results

    async def compare_search_methods(
        self,
        query: str,
        domain: str = "fitness",
        top_k: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        对比三种检索方法

        Args:
            query: 查询文本
            domain: 领域
            top_k: 返回结果数

        Returns:
            包含三种方法结果的字典
        """
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"📊 对比检索方法: {query}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 向量检索
        vector_results = await self.vector_search(query, domain, top_k=top_k)

        # BM25检索
        bm25_results = self.bm25_search(query, top_k=top_k)

        # 混合检索
        hybrid_results = await self.hybrid_search(
            query, domain, top_k=top_k,
            vector_top_k=20, bm25_top_k=20
        )

        return {
            'vector': vector_results,
            'bm25': bm25_results,
            'hybrid': hybrid_results
        }


# 便捷函数
def get_hybrid_search_engine() -> HybridSearchEngine:
    """获取混合检索引擎实例"""
    return HybridSearchEngine()
