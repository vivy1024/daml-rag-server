# -*- coding: utf-8 -*-
"""
Qdrant向量存储辅助工具

提供Qdrant集合管理、向量存储和检索功能

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-11-05
"""

import logging
import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    Range,
    MatchValue
)
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class QdrantHelper:
    """Qdrant向量存储辅助类"""
    
    # 集合配置
    COLLECTION_NAME = "chat_conversations"
    VECTOR_DIM = 1024  # BGE-M3维度（统一使用BGE-M3）
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        embedding_model: str = "BAAI/bge-m3"
    ):
        """
        初始化Qdrant客户端和Embedding模型
        
        Args:
            host: Qdrant服务器地址（默认从环境变量读取）
            port: Qdrant端口（默认从环境变量读取）
            embedding_model: Embedding模型名称
        """
        self.host = host or os.getenv('QDRANT_HOST', 'qdrant')
        self.port = port or int(os.getenv('QDRANT_PORT', '6333'))
        
        # 初始化Qdrant客户端（优化配置）
        try:
            from src.framework.clients.qdrant_client import create_qdrant_client
            self.client = create_qdrant_client(
                host=self.host,
                port=self.port,
                timeout=30.0,  # 增加超时时间到30秒
                prefer_grpc=True  # 启用gRPC连接
            )
            logger.info(f"✅ Qdrant客户端已连接: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"❌ Qdrant连接失败: {e}")
            raise
        
        # 初始化Embedding模型
        logger.info(f"加载Embedding模型: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        logger.info(f"✅ Embedding模型已加载: {embedding_model} (维度: {self.VECTOR_DIM})")
    
    def ensure_collection_exists(self) -> bool:
        """
        确保集合存在，不存在则创建
        
        Returns:
            bool: 集合是否存在或创建成功
        """
        try:
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.COLLECTION_NAME in collection_names:
                logger.info(f"✅ Qdrant集合已存在: {self.COLLECTION_NAME}")
                return True
            
            # 创建集合
            logger.info(f"创建Qdrant集合: {self.COLLECTION_NAME} (维度: {self.VECTOR_DIM})")
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_DIM,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"✅ Qdrant集合创建成功: {self.COLLECTION_NAME}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 集合管理失败: {e}")
            return False
    
    def vectorize_conversation(
        self,
        user_query: str,
        llm_response: str
    ) -> List[float]:
        """
        向量化对话内容（问题+回答）
        
        Args:
            user_query: 用户问题
            llm_response: AI回答
            
        Returns:
            向量列表
        """
        # 组合问题和答案
        conversation_text = f"用户问题: {user_query}\nAI回答: {llm_response}"
        
        # 向量化
        embedding = self.embedder.encode(
            conversation_text,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        return embedding.tolist()
    
    def save_conversation(
        self,
        session_id: str,
        user_id: Optional[int],
        user_query: str,
        llm_response: str,
        model_used: str,
        tools_used: List[str],
        user_rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        保存对话到Qdrant
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            user_query: 用户问题
            llm_response: AI回答
            model_used: 使用的模型
            tools_used: 调用的工具列表
            user_rating: 用户评分（1-5）
            metadata: 额外元数据
            
        Returns:
            Qdrant点ID，失败返回None
        """
        try:
            # 确保集合存在
            if not self.ensure_collection_exists():
                return None
            
            # 向量化对话
            vector = self.vectorize_conversation(user_query, llm_response)
            
            # 生成点ID
            point_id = str(uuid.uuid4())
            
            # 构建payload
            payload = {
                "session_id": session_id,
                "user_id": user_id,
                "user_query": user_query,
                "llm_response": llm_response,
                "model_used": model_used,
                "tools_used": tools_used,
                "user_rating": user_rating,
            }
            
            # 合并额外元数据
            if metadata:
                payload.update(metadata)
            
            # 存储到Qdrant
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            
            logger.info(f"✅ 对话已保存到Qdrant: point_id={point_id}, session={session_id}")
            return point_id
            
        except Exception as e:
            logger.error(f"❌ Qdrant存储失败: {e}", exc_info=True)
            return None
    
    def update_conversation_rating(
        self,
        point_id: str,
        user_rating: int,
        user_feedback: Optional[str] = None
    ) -> bool:
        """
        更新对话评分
        
        Args:
            point_id: Qdrant点ID
            user_rating: 用户评分
            user_feedback: 用户反馈文本
            
        Returns:
            是否更新成功
        """
        try:
            # 获取现有点数据
            point = self.client.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=[point_id]
            )
            
            if not point:
                logger.warning(f"⚠️ Qdrant点不存在: {point_id}")
                return False
            
            # 更新payload
            existing_payload = point[0].payload
            existing_payload['user_rating'] = user_rating
            if user_feedback:
                existing_payload['user_feedback'] = user_feedback
            
            # 重新上传（保持原向量）
            self.client.set_payload(
                collection_name=self.COLLECTION_NAME,
                payload=existing_payload,
                points=[point_id]
            )
            
            logger.info(f"✅ Qdrant评分已更新: point_id={point_id}, rating={user_rating}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Qdrant更新失败: {e}")
            return False
    
    def search_similar_conversations(
        self,
        query: str,
        top_k: int = 3,
        min_rating: Optional[int] = 4,
        min_score: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        检索相似对话（用于Few-Shot学习）
        
        Args:
            query: 查询文本
            top_k: 返回数量
            min_rating: 最低评分过滤
            min_score: 最低相似度
            
        Returns:
            相似对话列表
        """
        try:
            # 确保集合存在
            if not self.ensure_collection_exists():
                return []
            
            # 向量化查询
            query_text = f"用户问题: {query}"
            query_vector = self.embedder.encode(
                query_text,
                convert_to_numpy=True,
                show_progress_bar=False
            ).tolist()
            
            # 构建过滤条件
            query_filter = None
            if min_rating:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="user_rating",
                            range=Range(gte=min_rating)
                        )
                    ]
                )
            
            # 搜索
            search_results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=min_score,
                query_filter=query_filter
            )
            
            # 转换结果
            results = []
            for hit in search_results:
                results.append({
                    "similarity": hit.score,
                    "user_query": hit.payload.get("user_query", ""),
                    "llm_response": hit.payload.get("llm_response", ""),
                    "model_used": hit.payload.get("model_used", ""),
                    "user_rating": hit.payload.get("user_rating"),
                    "tools_used": hit.payload.get("tools_used", []),
                    "session_id": hit.payload.get("session_id", ""),
                })
            
            logger.info(f"✅ Qdrant检索完成: 找到 {len(results)} 条相似对话")
            return results
            
        except Exception as e:
            logger.error(f"❌ Qdrant检索失败: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            统计信息字典
        """
        try:
            collection_info = self.client.get_collection(self.COLLECTION_NAME)

            return {
                "collection_name": self.COLLECTION_NAME,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
            }
        except Exception as e:
            logger.error(f"❌ 获取统计失败: {e}")
            return {}

    def delete_point(self, point_id: str) -> bool:
        """
        删除指定的向量点（用于事务回滚）

        Args:
            point_id: 要删除的点ID

        Returns:
            bool: 是否删除成功
        """
        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[point_id]
            )

            logger.info(f"✅ Qdrant点已删除: point_id={point_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Qdrant点删除失败: {e}")
            return False


# 全局单例实例（延迟初始化）
_qdrant_helper_instance: Optional[QdrantHelper] = None


def get_qdrant_helper() -> QdrantHelper:
    """
    获取Qdrant辅助工具单例
    
    Returns:
        QdrantHelper实例
    """
    global _qdrant_helper_instance
    
    if _qdrant_helper_instance is None:
        _qdrant_helper_instance = QdrantHelper()
    
    return _qdrant_helper_instance







