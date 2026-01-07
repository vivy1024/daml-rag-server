"""
Qdrant向量导入器

功能：
1. 向量化Markdown文件（训练决策树、用户档案分析逻辑）
2. 向量化JSON文本数据
3. 存储向量到Qdrant
4. 支持幂等性检查

作者：薛小川
日期：2025-12-19
版本：v1.0.0
"""

import logging
import hashlib
import time
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

# 注意：这些导入在测试时会被动态注入
# 在正常使用时，通过相对导入
SupplementResult = None
ModelCacheManager = None

try:
    from .models import SupplementResult as _SupplementResult
    SupplementResult = _SupplementResult
except (ImportError, ValueError):
    pass

try:
    from src.framework.models.model_cache_manager import ModelCacheManager as _ModelCacheManager
    ModelCacheManager = _ModelCacheManager
except (ImportError, ValueError):
    pass

logger = logging.getLogger(__name__)


class QdrantImporter:
    """Qdrant向量导入器"""
    
    def __init__(
        self,
        qdrant_client: QdrantClient,
        collection_name: str = "training_knowledge",
        embedding_model: str = "BAAI/bge-m3",
        vector_size: int = 1024
    ):
        """
        初始化Qdrant导入器
        
        Args:
            qdrant_client: Qdrant客户端实例
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
            vector_size: 向量维度
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.vector_size = vector_size
        
        # 获取BGE-M3模型（使用缓存）
        model_cache = ModelCacheManager.get_instance()
        self.encoder = model_cache.get_bge_model(embedding_model)
        
        if self.encoder is None:
            raise RuntimeError(f"无法加载嵌入模型: {embedding_model}")
        
        logger.info(f"✅ Qdrant导入器初始化完成")
        logger.info(f"  - 集合: {collection_name}")
        logger.info(f"  - 模型: {embedding_model}")
        logger.info(f"  - 向量维度: {vector_size}")
    
    def vectorize_markdown(
        self,
        file_path: str,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        向量化Markdown文件
        
        Args:
            file_path: Markdown文件路径
            chunk_size: 分块大小（字符数）
            overlap: 重叠大小（字符数）
        
        Returns:
            List[Dict]: 向量数据列表
        """
        logger.info(f"🔄 开始向量化Markdown文件: {file_path}")
        
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分块处理
            chunks = self._chunk_text(content, chunk_size, overlap)
            logger.info(f"  - 文本分块数: {len(chunks)}")
            
            # 向量化每个块
            vectors = []
            source_file = Path(file_path).name
            
            for i, chunk in enumerate(chunks):
                # 生成向量
                embedding = self._encode_text(chunk)
                
                # 生成唯一ID
                vector_id = self._generate_vector_id(source_file, i, chunk)
                
                # 构建向量数据
                vector_data = {
                    "id": vector_id,
                    "vector": embedding,
                    "payload": {
                        "type": self._get_document_type(source_file),
                        "source_file": source_file,
                        "chunk_index": i,
                        "text": chunk,
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                vectors.append(vector_data)
            
            logger.info(f"✅ Markdown文件向量化完成: {len(vectors)}个向量")
            return vectors
            
        except Exception as e:
            logger.error(f"❌ Markdown文件向量化失败: {e}")
            raise
    
    def vectorize_json_texts(self, file_path: str) -> List[Dict[str, Any]]:
        """
        向量化JSON文本数据
        
        Args:
            file_path: JSON文件路径
        
        Returns:
            List[Dict]: 向量数据列表
        """
        logger.info(f"🔄 开始向量化JSON文件: {file_path}")
        
        try:
            import json
            
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理不同的JSON结构
            if isinstance(data, list):
                texts = data
            elif isinstance(data, dict) and "texts" in data:
                texts = data["texts"]
            elif isinstance(data, dict) and "chunks" in data:
                # 支持training_knowledge_texts.json格式
                texts = data["chunks"]
            else:
                raise ValueError(f"不支持的JSON结构: {type(data)}")
            
            logger.info(f"  - 文本数量: {len(texts)}")
            
            # 向量化每个文本
            vectors = []
            source_file = Path(file_path).name
            
            for i, text_item in enumerate(texts):
                # 提取文本内容
                if isinstance(text_item, str):
                    text = text_item
                elif isinstance(text_item, dict) and "text" in text_item:
                    text = text_item["text"]
                else:
                    logger.warning(f"跳过无效的文本项: {text_item}")
                    continue
                
                # 生成向量
                embedding = self._encode_text(text)
                
                # 生成唯一ID
                vector_id = self._generate_vector_id(source_file, i, text)
                
                # 构建向量数据
                vector_data = {
                    "id": vector_id,
                    "vector": embedding,
                    "payload": {
                        "type": "training_knowledge_text",
                        "source_file": source_file,
                        "chunk_index": i,
                        "text": text,
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                vectors.append(vector_data)
            
            logger.info(f"✅ JSON文件向量化完成: {len(vectors)}个向量")
            return vectors
            
        except Exception as e:
            logger.error(f"❌ JSON文件向量化失败: {e}")
            raise
    
    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> SupplementResult:
        """
        插入或更新向量到Qdrant（支持幂等性）
        
        Args:
            vectors: 向量数据列表
            batch_size: 批处理大小
        
        Returns:
            SupplementResult: 导入结果
        """
        logger.info(f"🔄 开始导入向量到Qdrant: {len(vectors)}个")
        
        start_time = time.time()
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        try:
            # 确保集合存在
            self._ensure_collection_exists()
            
            # 批量处理
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                
                # 检查哪些向量已存在
                existing_ids = self._check_vectors_exist([v["id"] for v in batch])
                
                # 构建Qdrant点
                points = []
                for vector_data in batch:
                    vector_id = vector_data["id"]
                    
                    # 检查是否已存在
                    if vector_id in existing_ids:
                        skipped_count += 1
                        logger.debug(f"跳过已存在的向量: {vector_id}")
                        continue
                    
                    # 构建点
                    point = PointStruct(
                        id=vector_id,
                        vector=vector_data["vector"],
                        payload=vector_data["payload"]
                    )
                    points.append(point)
                
                # 批量插入
                if points:
                    try:
                        self.client.upsert(
                            collection_name=self.collection_name,
                            points=points
                        )
                        created_count += len(points)
                        logger.info(f"  - 已导入: {i + len(batch)}/{len(vectors)}")
                    except Exception as e:
                        error_msg = f"批次 {i}-{i+len(batch)} 导入失败: {e}"
                        logger.error(error_msg)
                        errors.append({"batch": f"{i}-{i+len(batch)}", "error": str(e)})
            
            execution_time = time.time() - start_time
            
            logger.info(f"✅ 向量导入完成")
            logger.info(f"  - 新增: {created_count}")
            logger.info(f"  - 跳过: {skipped_count}")
            logger.info(f"  - 错误: {len(errors)}")
            logger.info(f"  - 耗时: {execution_time:.2f}秒")
            
            return SupplementResult(
                total_nodes=len(vectors),
                created_nodes=created_count,
                updated_nodes=updated_count,
                errors=errors,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"❌ 向量导入失败: {e}")
            raise
    
    def check_vector_exists(self, vector_id: str) -> bool:
        """
        检查向量是否已存在
        
        Args:
            vector_id: 向量ID
        
        Returns:
            bool: 是否存在
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[vector_id]
            )
            return len(result) > 0
        except Exception:
            return False
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """
        将文本分块
        
        Args:
            text: 原始文本
            chunk_size: 块大小
            overlap: 重叠大小
        
        Returns:
            List[str]: 文本块列表
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # 如果不是最后一块，尝试在句子边界处分割
            if end < len(text):
                # 查找最后一个句号、问号或感叹号
                last_period = max(
                    chunk.rfind('。'),
                    chunk.rfind('？'),
                    chunk.rfind('！'),
                    chunk.rfind('.'),
                    chunk.rfind('?'),
                    chunk.rfind('!')
                )
                
                if last_period > chunk_size * 0.5:  # 至少保留一半内容
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return [c for c in chunks if c]  # 过滤空块
    
    def _encode_text(self, text: str) -> List[float]:
        """
        使用BGE-M3编码文本
        
        Args:
            text: 文本内容
        
        Returns:
            List[float]: 向量
        """
        try:
            embedding = self.encoder.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            raise
    
    def _generate_vector_id(
        self,
        source_file: str,
        chunk_index: int,
        text: str
    ) -> str:
        """
        生成向量唯一ID（UUID格式）
        
        Args:
            source_file: 源文件名
            chunk_index: 块索引
            text: 文本内容
        
        Returns:
            str: UUID格式的唯一ID
        """
        # 使用文件名、索引和文本哈希生成确定性UUID
        # 这样相同的输入总是生成相同的UUID（支持幂等性）
        content = f"{source_file}_{chunk_index}_{text}"
        hash_bytes = hashlib.md5(content.encode('utf-8')).digest()
        # 使用UUID3或UUID5生成确定性UUID
        return str(uuid.UUID(bytes=hash_bytes))
    
    def _get_document_type(self, filename: str) -> str:
        """
        根据文件名确定文档类型
        
        Args:
            filename: 文件名
        
        Returns:
            str: 文档类型
        """
        if "decision_tree" in filename.lower():
            return "training_decision_tree"
        elif "profile_analysis" in filename.lower():
            return "user_profile_analysis"
        else:
            return "training_knowledge"
    
    def _ensure_collection_exists(self):
        """确保Qdrant集合存在"""
        try:
            # 检查集合是否存在
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"创建Qdrant集合: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ 集合创建成功: {self.collection_name}")
            else:
                logger.info(f"✅ 集合已存在: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"❌ 集合检查/创建失败: {e}")
            raise
    
    def _check_vectors_exist(self, vector_ids: List[str]) -> set:
        """
        批量检查向量是否存在
        
        Args:
            vector_ids: 向量ID列表
        
        Returns:
            set: 已存在的向量ID集合
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=vector_ids
            )
            return {point.id for point in result}
        except Exception:
            return set()
