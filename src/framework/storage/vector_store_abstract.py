# -*- coding: utf-8 -*-
"""
VectorStore Abstract Layer - 向量存储抽象层

设计原则：
- 接口统一：定义通用接口（IVectorStore）
- 多实现：支持Qdrant、FAISS、Pinecone等
- 可扩展：轻松添加新的向量数据库

版本：v1.0.0
日期：2025-10-28
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from enum import Enum


class Distance(Enum):
    """距离度量方式"""
    COSINE = "cosine"        # 余弦相似度
    EUCLIDEAN = "euclidean"  # 欧氏距离
    DOT_PRODUCT = "dot"      # 点积


class IVectorStore(ABC):
    """
    向量存储抽象接口（通用框架）
    
    设计原则：
    - 零实现依赖：不依赖特定向量数据库
    - 接口通用：适配所有主流向量数据库
    - 最小化接口：只定义核心必需方法
    
    实现类：
    - QdrantVectorStore: Qdrant实现
    - FAISSVectorStore: FAISS实现（未来）
    - PineconeVectorStore: Pinecone实现（未来）
    """
    
    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        **kwargs
    ):
        """
        创建集合/索引
        
        Args:
            collection_name: 集合名称
            vector_size: 向量维度
            distance: 距离度量方式
            **kwargs: 实现特定参数
        """
        pass
    
    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """
        检查集合是否存在
        
        Args:
            collection_name: 集合名称
        
        Returns:
            bool: 是否存在
        """
        pass
    
    @abstractmethod
    def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ):
        """
        插入/更新向量点
        
        Args:
            collection_name: 集合名称
            points: 点列表
                [
                    {
                        "id": "uuid-xxx",
                        "vector": [0.1, 0.2, ...],
                        "payload": {"key": "value"}
                    },
                    ...
                ]
        """
        pass
    
    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        向量检索
        
        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            top_k: 返回数量
            score_threshold: 相似度阈值
            filter: 过滤条件
        
        Returns:
            List[Dict]: 检索结果
                [
                    {
                        "id": "uuid-xxx",
                        "score": 0.85,
                        "payload": {...}
                    },
                    ...
                ]
        """
        pass
    
    @abstractmethod
    def update_payload(
        self,
        collection_name: str,
        point_id: str,
        payload: Dict
    ):
        """
        更新点的payload
        
        Args:
            collection_name: 集合名称
            point_id: 点ID
            payload: 新的payload数据
        """
        pass
    
    @abstractmethod
    def delete(
        self,
        collection_name: str,
        point_ids: List[str]
    ):
        """
        删除点
        
        Args:
            collection_name: 集合名称
            point_ids: 点ID列表
        """
        pass
    
    @abstractmethod
    def get_collection_info(self, collection_name: str) -> Dict:
        """
        获取集合信息
        
        Args:
            collection_name: 集合名称
        
        Returns:
            Dict: 集合信息
                {
                    "vectors_count": 1000,
                    "indexed_vectors_count": 1000,
                    "points_count": 1000,
                    "segments_count": 1,
                    "status": "green"
                }
        """
        pass


class QdrantVectorStore(IVectorStore):
    """
    Qdrant向量存储实现
    
    特点：
    - 高性能：支持HNSW索引
    - 功能完整：支持过滤、聚合、推荐
    - 易部署：Docker一键部署
    """
    
    def __init__(self, client):
        """
        初始化Qdrant向量存储
        
        Args:
            client: QdrantClient实例
        """
        from qdrant_client import QdrantClient
        self.client: QdrantClient = client
    
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        **kwargs
    ):
        """创建Qdrant集合"""
        from qdrant_client.models import VectorParams, Distance as QdrantDistance
        
        # 映射距离度量
        distance_map = {
            Distance.COSINE: QdrantDistance.COSINE,
            Distance.EUCLIDEAN: QdrantDistance.EUCLID,
            Distance.DOT_PRODUCT: QdrantDistance.DOT
        }
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance_map[distance]
            )
        )
    
    def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception:
            return False
    
    def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ):
        """插入/更新点"""
        from qdrant_client.models import PointStruct
        
        qdrant_points = [
            PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p.get("payload", {})
            )
            for p in points
        ]
        
        self.client.upsert(
            collection_name=collection_name,
            points=qdrant_points
        )
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        """向量检索"""
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=filter
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results
        ]
    
    def update_payload(
        self,
        collection_name: str,
        point_id: str,
        payload: Dict
    ):
        """更新payload"""
        self.client.set_payload(
            collection_name=collection_name,
            payload=payload,
            points=[point_id]
        )
    
    def delete(
        self,
        collection_name: str,
        point_ids: List[str]
    ):
        """删除点"""
        self.client.delete(
            collection_name=collection_name,
            points_selector=point_ids
        )
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """获取集合信息"""
        info = self.client.get_collection(collection_name)
        
        return {
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "status": info.status.value
        }


class FAISSVectorStore(IVectorStore):
    """
    FAISS向量存储实现（预留接口）
    
    特点：
    - 高性能：Meta开源，优化的向量检索
    - 离线优先：无需服务器
    - 轻量级：适合中小规模数据
    
    状态：接口预留，未来实现
    """
    
    def __init__(self, index_path: str):
        """
        初始化FAISS向量存储
        
        Args:
            index_path: 索引文件路径
        """
        self.index_path = index_path
        self.indices = {}  # collection_name -> faiss.Index
        self.metadata = {}  # collection_name -> List[payload]
    
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        **kwargs
    ):
        """创建FAISS索引"""
        raise NotImplementedError("FAISS实现预留，未来支持")
    
    def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        return collection_name in self.indices
    
    def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ):
        """插入/更新点"""
        raise NotImplementedError("FAISS实现预留，未来支持")
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        """向量检索"""
        raise NotImplementedError("FAISS实现预留，未来支持")
    
    def update_payload(
        self,
        collection_name: str,
        point_id: str,
        payload: Dict
    ):
        """更新payload"""
        raise NotImplementedError("FAISS实现预留，未来支持")
    
    def delete(
        self,
        collection_name: str,
        point_ids: List[str]
    ):
        """删除点"""
        raise NotImplementedError("FAISS实现预留，未来支持")
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """获取集合信息"""
        raise NotImplementedError("FAISS实现预留，未来支持")


class PineconeVectorStore(IVectorStore):
    """
    Pinecone向量存储实现（预留接口）
    
    特点：
    - 云服务：无需部署
    - 高可用：托管服务
    - 按需付费：适合生产环境
    
    状态：接口预留，未来实现
    """
    
    def __init__(self, api_key: str, environment: str):
        """
        初始化Pinecone向量存储
        
        Args:
            api_key: Pinecone API密钥
            environment: 环境（如us-west1-gcp）
        """
        self.api_key = api_key
        self.environment = environment
    
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        **kwargs
    ):
        """创建Pinecone索引"""
        raise NotImplementedError("Pinecone实现预留，未来支持")
    
    def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        raise NotImplementedError("Pinecone实现预留，未来支持")
    
    def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ):
        """插入/更新点"""
        raise NotImplementedError("Pinecone实现预留，未来支持")
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        """向量检索"""
        raise NotImplementedError("Pinecone实现预留，未来支持")
    
    def update_payload(
        self,
        collection_name: str,
        point_id: str,
        payload: Dict
    ):
        """更新payload"""
        raise NotImplementedError("Pinecone实现预留，未来支持")
    
    def delete(
        self,
        collection_name: str,
        point_ids: List[str]
    ):
        """删除点"""
        raise NotImplementedError("Pinecone实现预留，未来支持")
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """获取集合信息"""
        raise NotImplementedError("Pinecone实现预留，未来支持")

