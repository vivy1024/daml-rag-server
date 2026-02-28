# -*- coding: utf-8 -*-
"""
用户跨对话记忆服务

基于 Qdrant user_memory collection 实现用户偏好的持久化存储和检索。
支持：recall（检索）、remember（存储+去重）、list_memories、clear_all。

向量模型：复用项目现有 GTE-Large-zh（1024维）
存储：Qdrant user_memory collection

版本: v1.0.0
日期: 2026-02-20
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

COLLECTION_NAME = "user_memory"

MEMORY_CATEGORIES = [
    "exercise_preference",
    "diet_preference",
    "general",
]


class UserMemoryService:
    """用户跨对话记忆服务"""

    SIMILARITY_THRESHOLD = 0.9  # 去重阈值

    def __init__(self, qdrant_client=None, embedding_fn=None):
        """
        Args:
            qdrant_client: QdrantClient 实例（None 时从单例获取）
            embedding_fn: 向量化函数 (str) -> List[float]（None 时自动加载 GTE-Large-zh）
        """
        self._qdrant = qdrant_client
        self._embedding_fn = embedding_fn
        self._encoder = None  # 懒加载 SentenceTransformer

    def _get_qdrant(self):
        if self._qdrant is None:
            from ...framework.clients.qdrant_client import get_qdrant_client
            self._qdrant = get_qdrant_client()
        return self._qdrant

    def _embed(self, text: str) -> List[float]:
        """向量化文本（复用 GTE-Large-zh）"""
        if self._embedding_fn:
            return self._embedding_fn(text)

        if self._encoder is None:
            import os
            try:
                from sentence_transformers import SentenceTransformer
                model_name = os.getenv("EMBEDDING_MODEL", "thenlper/gte-large-zh")
                self._encoder = SentenceTransformer(model_name)
                logger.info(f"✅ UserMemoryService 加载向量模型: {model_name}")
            except Exception as e:
                logger.error(f"❌ 向量模型加载失败: {e}")
                raise

        return self._encoder.encode(text).tolist()

    async def recall(self, user_id: int, query: str, top_k: int = 5) -> List[dict]:
        """检索与查询相关的用户记忆"""
        try:
            vector = await asyncio.to_thread(self._embed, query)
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            response = await asyncio.to_thread(
                self._get_qdrant().query_points,
                collection_name=COLLECTION_NAME,
                query=vector,
                query_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=top_k,
            )

            points = response.points if hasattr(response, 'points') else response
            return [
                {
                    "id": str(r.id),
                    "content": r.payload.get("content", ""),
                    "category": r.payload.get("category", "general"),
                    "score": round(r.score, 4),
                    "created_at": r.payload.get("created_at", ""),
                }
                for r in points
            ]
        except Exception as e:
            logger.warning(f"记忆检索失败 (user_id={user_id}): {e}", exc_info=True)
            return []

    async def remember(self, user_id: int, content: str, category: str = "general") -> str:
        """存储新记忆（自动去重：相似度 > 0.9 时更新而非新增）"""
        if category not in MEMORY_CATEGORIES:
            category = "general"

        try:
            vector = await asyncio.to_thread(self._embed, content)
            from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct

            # 检查是否有高度相似的已有记忆
            response = await asyncio.to_thread(
                self._get_qdrant().query_points,
                collection_name=COLLECTION_NAME,
                query=vector,
                query_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=1,
            )

            existing = response.points if hasattr(response, 'points') else response
            now = datetime.now(timezone.utc).isoformat()

            if existing and existing[0].score >= self.SIMILARITY_THRESHOLD:
                # 更新已有记忆
                point_id = str(existing[0].id)
                await asyncio.to_thread(
                    self._get_qdrant().set_payload,
                    collection_name=COLLECTION_NAME,
                    payload={"content": content, "updated_at": now},
                    points=[point_id],
                )
                logger.info(f"记忆更新 (user_id={user_id}, id={point_id}, score={existing[0].score:.3f})")
                return point_id
            else:
                # 新增记忆
                point_id = str(uuid.uuid4())
                payload = {
                    "user_id": user_id,
                    "content": content,
                    "category": category,
                    "created_at": now,
                    "updated_at": now,
                }
                await asyncio.to_thread(
                    self._get_qdrant().upsert,
                    collection_name=COLLECTION_NAME,
                    points=[PointStruct(id=point_id, vector=vector, payload=payload)],
                )
                logger.info(f"记忆新增 (user_id={user_id}, id={point_id}, category={category})")
                return point_id

        except Exception as e:
            logger.error(f"记忆存储失败 (user_id={user_id}): {e}")
            raise

    async def list_memories(self, user_id: int) -> List[dict]:
        """列出用户所有记忆"""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            results, _ = await asyncio.to_thread(
                self._get_qdrant().scroll,
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=100,
            )

            return [
                {
                    "id": str(r.id),
                    "content": r.payload.get("content", ""),
                    "category": r.payload.get("category", "general"),
                    "created_at": r.payload.get("created_at", ""),
                    "updated_at": r.payload.get("updated_at", ""),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"记忆列表获取失败 (user_id={user_id}): {e}")
            return []

    async def clear_all(self, user_id: int) -> int:
        """清空用户所有记忆，返回删除数量"""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # 先统计数量
            memories = await self.list_memories(user_id)
            count = len(memories)

            if count > 0:
                await asyncio.to_thread(
                    self._get_qdrant().delete,
                    collection_name=COLLECTION_NAME,
                    points_selector=Filter(
                        must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                    ),
                )
                logger.info(f"记忆清空 (user_id={user_id}, count={count})")

            return count
        except Exception as e:
            logger.error(f"记忆清空失败 (user_id={user_id}): {e}")
            raise


# 全局单例
_memory_service: Optional[UserMemoryService] = None


def get_user_memory_service() -> UserMemoryService:
    """获取 UserMemoryService 单例"""
    global _memory_service
    if _memory_service is None:
        _memory_service = UserMemoryService()
    return _memory_service
