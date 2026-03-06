# -*- coding: utf-8 -*-
"""
三层检索引擎 - Layer 1 向量语义检索
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp

from .models import LayerExecutionResult

logger = logging.getLogger(__name__)


class Layer1VectorMixin:
    """Layer 1: 向量语义检索 Mixin"""

    async def _execute_layer1_vector_search(
        self,
        query: str,
        domain: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        user_id: Optional[str] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        min_confidence: float = 0.70  # 最低置信度阈值
    ) -> LayerExecutionResult:
        """
        Layer 1: 向量语义检索 (Qdrant via GraphRAG API)

        特性：
        - 重试机制：最多重试3次
        - 指数退避：1s, 2s, 4s
        - 详细日志：记录每次重试
        - 质量评估：标记低质量结果（置信度 < min_confidence）
        - 统一超时：使用TimeoutManager配置 (Requirements 3.6)
        """
        start_time = datetime.now()
        logger.info("→ Layer 1: 向量语义检索 (Qdrant)")

        # 从超时管理器获取配置
        layer1_timeout = self.timeout_manager.get_timeout("layer1_timeout_ms", 5000)
        http_timeout = self.timeout_manager.get_timeout("http_total_timeout_ms", 60000)

        retry_delay = initial_retry_delay
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"  ⟳ 重试 {attempt}/{max_retries-1}，等待{retry_delay:.1f}秒...")
                    await asyncio.sleep(retry_delay)

                _headers = {}
                if self._internal_api_token:
                    _headers["X-Internal-Token"] = self._internal_api_token
                async with aiohttp.ClientSession(headers=_headers) as session:
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
                        timeout=aiohttp.ClientTimeout(total=min(layer1_timeout, http_timeout))
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get("data", {}).get("results", [])

                            # 计算置信度
                            if results:
                                avg_score = sum(r.get("score", 0) for r in results) / len(results)
                                confidence = min(avg_score, 1.0)

                                # 质量评估
                                is_low_quality = confidence < min_confidence

                                if is_low_quality:
                                    logger.warning(f"  ⚠️ Layer1质量偏低（置信度{confidence:.2f} < {min_confidence}）")
                            else:
                                confidence = 0.0
                                is_low_quality = True

                            execution_time = (datetime.now() - start_time).total_seconds() * 1000
                            self.stats["layer1_success"] += 1

                            if attempt > 0:
                                logger.info(f"  ✓ Layer 1重试成功（第{attempt+1}次尝试）: {len(results)}个向量结果, 置信度{confidence:.2f}")
                            else:
                                logger.info(f"  ✓ Layer 1完成: {len(results)}个向量结果, 置信度{confidence:.2f}")

                            return LayerExecutionResult(
                                layer_name="Layer1-Vector",
                                success=True,
                                results=results,
                                execution_time_ms=execution_time,
                                confidence=confidence,
                                metadata={
                                    "source": "qdrant_via_api",
                                    "count": len(results),
                                    "avg_score": confidence,
                                    "retry_count": attempt,
                                    "is_low_quality": is_low_quality
                                }
                            )
                        else:
                            last_error = f"GraphRAG API返回错误: {response.status}"
                            logger.warning(f"  ⚠️ 尝试{attempt+1}/{max_retries}失败: {last_error}")

                            if attempt == max_retries - 1:
                                logger.error(f"  ✗ Layer 1最终失败: {last_error}")
                                return self._empty_layer_result("Layer1-Vector", error=last_error)

                            retry_delay *= 2

            except asyncio.TimeoutError:
                last_error = f"Layer 1超时 (配置: {layer1_timeout}s)"
                logger.warning(f"  ⚠️ 尝试{attempt+1}/{max_retries}超时")
                self.stats["timeout_count"] += 1

                if attempt == max_retries - 1:
                    logger.error(f"  ✗ Layer 1最终失败: {last_error}")
                    return self._empty_layer_result("Layer1-Vector", error=last_error)

                retry_delay *= 2

            except Exception as e:
                last_error = f"Layer 1异常: {e}"
                logger.warning(f"  ⚠️ 尝试{attempt+1}/{max_retries}异常: {e}")

                if attempt == max_retries - 1:
                    logger.error(f"  ✗ Layer 1最终失败: {last_error}")
                    return self._empty_layer_result("Layer1-Vector", error=last_error)

                retry_delay *= 2

        logger.error(f"  ✗ Layer 1失败: 所有重试均失败")
        return self._empty_layer_result("Layer1-Vector", error=last_error or "所有重试均失败")

    async def _fetch_knowledge_context(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.55
    ) -> List[Dict[str, Any]]:
        """
        查询 training_knowledge 集合获取知识上下文

        从教材PDF和B站字幕中检索与查询相关的知识片段，
        作为补充上下文传递给LLM综合阶段。

        v2.5.0 新增
        """
        try:
            # 延迟初始化（单例缓存）
            if not hasattr(self, '_knowledge_qdrant'):
                from qdrant_client import QdrantClient
                from ...config.app_config import get_config
                config = get_config()
                self._knowledge_qdrant = QdrantClient(
                    host=config.database.qdrant.host,
                    port=config.database.qdrant.port,
                    timeout=5
                )

                # 检查集合是否存在
                collections = [c.name for c in self._knowledge_qdrant.get_collections().collections]
                self._knowledge_available = "training_knowledge" in collections
                if self._knowledge_available:
                    info = self._knowledge_qdrant.get_collection("training_knowledge")
                    logger.info(f"  📚 知识库已连接: training_knowledge ({info.points_count} points)")

            if not self._knowledge_available:
                return []

            if not hasattr(self, '_knowledge_encoder'):
                from sentence_transformers import SentenceTransformer
                self._knowledge_encoder = SentenceTransformer("thenlper/gte-large-zh")

            query_vector = self._knowledge_encoder.encode(query).tolist()

            results = self._knowledge_qdrant.query_points(
                collection_name="training_knowledge",
                query=query_vector,
                limit=top_k
            )

            points = results.points if hasattr(results, 'points') else results
            knowledge = []
            for p in points:
                score = p.score if hasattr(p, 'score') else 0.0
                if score < min_similarity:
                    continue
                payload = p.payload if hasattr(p, 'payload') else {}
                knowledge.append({
                    "text": payload.get("chunk_text", ""),
                    "source": payload.get("source", "unknown"),
                    "title": payload.get("title", ""),
                    "score": round(score, 3),
                    "filename": payload.get("filename", payload.get("bvid", "")),
                    "chapter": payload.get("chapter", ""),
                })

            if knowledge:
                logger.info(f"  📚 知识上下文: {len(knowledge)}条 (来源: {set(k['source'] for k in knowledge)})")

            return knowledge

        except Exception as e:
            logger.debug(f"知识上下文查询失败（非致命）: {e}")
            return []
