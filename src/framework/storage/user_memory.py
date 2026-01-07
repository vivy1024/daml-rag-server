# -*- coding: utf-8 -*-
"""
UserMemory - 用户级向量库管理器（通用框架）

设计原则：
- 领域无关：不包含任何健身领域知识
- 用户隔离：每个用户独立namespace
- 可扩展：支持任意领域的交互记录

版本：v1.0.0
日期：2025-10-28
"""

import logging
import uuid
import time
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    VectorParams,
    Distance,
    MatchValue,
    Range
)

logger = logging.getLogger(__name__)


class UserMemory:
    """
    用户级向量库管理器（通用框架）
    
    核心功能：
    1. 用户级隔离：每个用户独立collection（namespace: user_interactions_{user_id}）
    2. 交互记录存储：query + response + metadata
    3. 语义检索：基于向量相似度检索历史案例
    4. 奖励更新：支持用户反馈闭环
    
    设计原则：
    - 零领域依赖：不硬编码任何健身、教育、医疗等领域知识
    - 接口通用：metadata支持任意领域特定字段
    - 性能优化：向量检索 <50ms，支持过滤器
    
    Example:
        >>> user_memory = UserMemory(qdrant_client)
        >>> 
        >>> # 存储交互（健身领域）
        >>> interaction_id = user_memory.store_interaction(
        ...     user_id="zhangsan",
        ...     query="如何增肌？",
        ...     response="推荐杠铃卧推...",
        ...     query_vector=embedding_vector,
        ...     metadata={
        ...         "domain": "fitness",
        ...         "model_used": "deepseek",
        ...         "tools_used": ["user-profile", "exercises"],
        ...         "timestamp": int(time.time())
        ...     }
        ... )
        >>> 
        >>> # 检索相似案例（只检索张三的历史）
        >>> similar_cases = user_memory.retrieve_similar(
        ...     user_id="zhangsan",
        ...     query_vector=new_query_vector,
        ...     top_k=5,
        ...     min_similarity=0.6,
        ...     filters={"reward": {"$gte": 4.0}}
        ... )
        >>> 
        >>> # 更新奖励
        >>> user_memory.update_reward(
        ...     user_id="zhangsan",
        ...     interaction_id=interaction_id,
        ...     reward=4.5
        ... )
    """
    
    def __init__(
        self,
        qdrant_client: QdrantClient,
        collection_prefix: str = "user_interactions",
        vector_size: int = 1024,
        distance: Distance = Distance.COSINE
    ):
        """
        初始化用户内存管理器
        
        Args:
            qdrant_client: Qdrant客户端实例
            collection_prefix: 集合名前缀（通用，默认"user_interactions"）
            vector_size: 向量维度（默认1024，BGE-M3标准维度）
            distance: 距离度量方式（默认余弦距离）
        """
        self.client = qdrant_client
        self.collection_prefix = collection_prefix
        self.vector_size = vector_size
        self.distance = distance
        
        logger.info(
            f"✅ UserMemory 初始化完成 "
            f"(prefix={collection_prefix}, vector_size={vector_size})"
        )
    
    def get_collection_name(self, user_id: str) -> str:
        """
        生成用户专属集合名
        
        格式: {collection_prefix}_{user_id}
        例如: user_interactions_zhangsan
        
        Args:
            user_id: 用户ID（必需）
        
        Returns:
            str: 用户专属集合名
        """
        return f"{self.collection_prefix}_{user_id}"
    
    def store_interaction(
        self,
        user_id: str,
        query: str,
        response: str,
        query_vector: List[float],
        metadata: Dict,
        interaction_id: Optional[str] = None
    ) -> str:
        """
        存储用户交互（领域无关）
        
        Args:
            user_id: 用户ID（必需）
            query: 用户查询文本
            response: AI响应文本
            query_vector: 查询向量（768维）
            metadata: 元数据（可包含领域特定信息）
                - model_used: str（使用的模型）
                - tools_used: List[str]（使用的工具列表）
                - quality: float（初始值None，等待用户反馈）
                - cot: str（思维链）
                - timestamp: int（Unix时间戳）
                - domain: str（领域标识，如"fitness", "education"）
            interaction_id: 交互ID（可选，默认生成UUID）
        
        Returns:
            str: 交互唯一标识（interaction_id）
        
        Example:
            >>> interaction_id = user_memory.store_interaction(
            ...     user_id="zhangsan",
            ...     query="如何快速增肌？",
            ...     response="建议采用...",
            ...     query_vector=[0.1, 0.2, ...],  # 768维
            ...     metadata={
            ...         "domain": "fitness",
            ...         "model_used": "ollama",
            ...         "tools_used": ["user-profile", "exercises"],
            ...         "cot": "思维链...",
            ...         "timestamp": 1698765432
            ...     }
            ... )
        """
        collection_name = self.get_collection_name(user_id)
        
        # 确保集合存在
        self._ensure_collection(collection_name)
        
        # 生成交互ID
        if not interaction_id:
            interaction_id = str(uuid.uuid4())
        
        # 验证向量维度
        if len(query_vector) != self.vector_size:
            raise ValueError(
                f"向量维度不匹配: 期望{self.vector_size}, 实际{len(query_vector)}"
            )
        
        # 构建点
        point = PointStruct(
            id=interaction_id,
            vector=query_vector,
            payload={
                "user_id": user_id,
                "query": query,
                "response": response,
                "reward": None,  # 初始无奖励，等待用户反馈
                **metadata  # 展开元数据（领域特定字段）
            }
        )
        
        # 存储到Qdrant
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            logger.debug(
                f"✅ 交互已存储: user={user_id}, id={interaction_id}, "
                f"domain={metadata.get('domain')}"
            )
            return interaction_id
            
        except Exception as e:
            logger.error(f"❌ 存储交互失败: {e}")
            raise
    
    def retrieve_similar(
        self,
        user_id: str,
        query_vector: List[float],
        top_k: int = 5,
        min_similarity: float = 0.5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        检索用户历史相似案例（领域无关）
        
        Args:
            user_id: 用户ID
            query_vector: 查询向量（768维）
            top_k: 返回数量（默认5）
            min_similarity: 最小相似度阈值（默认0.5）
            filters: 额外过滤条件（可选）
                例如: {"reward": {"$gte": 4.0}}  # 只要高质量
                     {"domain": "fitness"}        # 只要健身领域
                     {"model_used": "ollama"}     # 只要学生模型
        
        Returns:
            List[Dict]: 相似案例列表（按相似度降序）
                [
                    {
                        "interaction_id": "uuid-xxx",
                        "query": "用户原始问题",
                        "response": "AI回答",
                        "similarity": 0.85,  # 相似度（0-1）
                        "reward": 4.5,       # 用户评分（1-5）
                        "cot": "思维链...",
                        "tools_used": ["tool_a", "tool_b"],
                        "model_used": "ollama",
                        "timestamp": 1698765432,
                        "metadata": {...}    # 完整metadata
                    },
                    ...
                ]
        
        Example:
            >>> # 检索高质量案例
            >>> cases = user_memory.retrieve_similar(
            ...     user_id="zhangsan",
            ...     query_vector=new_vector,
            ...     top_k=5,
            ...     min_similarity=0.6,
            ...     filters={"reward": {"$gte": 4.0}, "domain": "fitness"}
            ... )
        """
        collection_name = self.get_collection_name(user_id)
        
        # 检查集合是否存在
        if not self._collection_exists(collection_name):
            logger.warning(f"用户{user_id}无历史记录（集合不存在）")
            return []  # 新用户，无历史
        
        # 验证向量维度
        if len(query_vector) != self.vector_size:
            raise ValueError(
                f"向量维度不匹配: 期望{self.vector_size}, 实际{len(query_vector)}"
            )
        
        # 构建过滤器
        query_filter = None
        if filters:
            conditions = []
            
            for key, value in filters.items():
                if isinstance(value, dict):
                    # 范围过滤，如 {"reward": {"$gte": 4.0}}
                    for op, val in value.items():
                        if op == "$gte":
                            conditions.append(
                                FieldCondition(
                                    key=key,
                                    range=Range(gte=val)
                                )
                            )
                        elif op == "$lte":
                            conditions.append(
                                FieldCondition(
                                    key=key,
                                    range=Range(lte=val)
                                )
                            )
                        elif op == "$gt":
                            conditions.append(
                                FieldCondition(
                                    key=key,
                                    range=Range(gt=val)
                                )
                            )
                        elif op == "$lt":
                            conditions.append(
                                FieldCondition(
                                    key=key,
                                    range=Range(lt=val)
                                )
                            )
                else:
                    # 精确匹配，如 {"domain": "fitness"}
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
            
            if conditions:
                query_filter = Filter(must=conditions)
        
        # 向量检索
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=min_similarity,
                query_filter=query_filter
            )
            
            # 格式化返回
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    "interaction_id": hit.id,
                    "query": hit.payload.get("query"),
                    "response": hit.payload.get("response"),
                    "similarity": hit.score,
                    "reward": hit.payload.get("reward"),
                    "cot": hit.payload.get("cot"),
                    "tools_used": hit.payload.get("tools_used"),
                    "model_used": hit.payload.get("model_used"),
                    "timestamp": hit.payload.get("timestamp"),
                    "metadata": hit.payload  # 完整payload
                })
            
            logger.debug(
                f"✅ 检索完成: user={user_id}, 找到{len(formatted_results)}条"
            )
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 检索失败: {e}")
            raise
    
    def update_reward(
        self,
        user_id: str,
        interaction_id: str,
        reward: float
    ) -> bool:
        """
        更新交互奖励信号（领域无关）
        
        用于用户反馈闭环，支持强化学习算法（Thompson Sampling等）
        
        Args:
            user_id: 用户ID
            interaction_id: 交互ID（由store_interaction返回）
            reward: 奖励值（通常1-5分）
        
        Returns:
            bool: 是否成功
        
        Example:
            >>> success = user_memory.update_reward(
            ...     user_id="zhangsan",
            ...     interaction_id="uuid-xxx",
            ...     reward=4.5
            ... )
        """
        collection_name = self.get_collection_name(user_id)
        
        # 验证奖励范围（1-5分）
        if not 1.0 <= reward <= 5.0:
            logger.warning(f"⚠️ 奖励值{reward}超出范围[1-5]")
        
        try:
            self.client.set_payload(
                collection_name=collection_name,
                payload={"reward": reward},
                points=[interaction_id]
            )
            logger.debug(f"✅ 奖励已更新: user={user_id}, reward={reward}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新奖励失败: {e}")
            return False
    
    def get_user_stats(self, user_id: str) -> Dict:
        """
        获取用户统计信息（领域无关）
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 统计信息
                {
                    "total_interactions": 100,        # 总交互数
                    "avg_reward": 4.2,                # 平均奖励
                    "high_quality_count": 80,         # 高质量数量（reward >= 4.0）
                    "domains": {                      # 领域分布
                        "fitness": 90,
                        "education": 10
                    },
                    "models": {                       # 模型使用分布
                        "ollama": 90,
                        "deepseek": 10
                    }
                }
        
        Example:
            >>> stats = user_memory.get_user_stats("zhangsan")
            >>> print(f"总交互: {stats['total_interactions']}")
        """
        collection_name = self.get_collection_name(user_id)
        
        # 检查集合是否存在
        if not self._collection_exists(collection_name):
            return {
                "total_interactions": 0,
                "avg_reward": 0.0,
                "high_quality_count": 0,
                "domains": {},
                "models": {}
            }
        
        try:
            # 获取collection信息
            collection_info = self.client.get_collection(collection_name)
            total_count = collection_info.points_count
            
            # 滚动查询所有点（批量获取metadata）
            # 注意：生产环境应该用聚合查询，这里简化实现
            scroll_result = self.client.scroll(
                collection_name=collection_name,
                limit=total_count,
                with_payload=True,
                with_vectors=False
            )
            
            points = scroll_result[0]
            
            # 统计
            rewards = []
            high_quality_count = 0
            domains = {}
            models = {}
            
            for point in points:
                payload = point.payload
                
                # 奖励统计
                reward = payload.get("reward")
                if reward is not None:
                    rewards.append(reward)
                    if reward >= 4.0:
                        high_quality_count += 1
                
                # 领域分布
                domain = payload.get("domain", "unknown")
                domains[domain] = domains.get(domain, 0) + 1
                
                # 模型分布
                model = payload.get("model_used", "unknown")
                models[model] = models.get(model, 0) + 1
            
            # 平均奖励
            avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
            
            return {
                "total_interactions": total_count,
                "avg_reward": round(avg_reward, 2),
                "high_quality_count": high_quality_count,
                "domains": domains,
                "models": models
            }
            
        except Exception as e:
            logger.error(f"❌ 获取统计失败: {e}")
            return {
                "total_interactions": 0,
                "avg_reward": 0.0,
                "high_quality_count": 0,
                "domains": {},
                "models": {}
            }
    
    def _ensure_collection(self, collection_name: str):
        """
        确保集合存在，不存在则创建
        
        Args:
            collection_name: 集合名
        """
        if self._collection_exists(collection_name):
            return  # 已存在，跳过
        
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=self.distance
                )
            )
            logger.info(f"✅ 创建集合: {collection_name}")
            
        except Exception as e:
            logger.error(f"❌ 创建集合失败: {e}")
            raise
    
    def _collection_exists(self, collection_name: str) -> bool:
        """
        检查集合是否存在
        
        Args:
            collection_name: 集合名
        
        Returns:
            bool: 是否存在
        """
        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error(f"❌ 检查集合失败: {e}")
            return False

