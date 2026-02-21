"""
Reranker 重排序模块
使用 GTE-Large-zh 模型进行语义相似度重排序
"""
import logging
from typing import List, Dict, Optional
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class FitnessReranker:
    """健身领域重排序器（单例模式）"""
    
    _instance = None
    
    def __init__(self, model_name: str = "thenlper/gte-large-zh"):
        """
        初始化重排序器
        
        Args:
            model_name: 使用的模型名称，默认使用GTE-Large-zh
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"初始化 Reranker，模型: {model_name}, 设备: {self.device}")
        
        try:
            # 加载 SentenceTransformer 模型用于计算语义相似度
            self.model = SentenceTransformer(model_name, device=self.device)
            logger.info(f"Reranker 模型加载成功")
        except Exception as e:
            logger.error(f"Reranker 模型加载失败: {e}")
            raise
    
    @classmethod
    def get_instance(cls, model_name: str = "thenlper/gte-large-zh") -> "FitnessReranker":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance
    
    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5,
        score_threshold: float = 0.0,
        timeout: float = 5.0
    ) -> List[Dict]:
        """
        对检索结果进行重排序
        
        Args:
            query: 用户查询
            documents: 待重排序的文档列表，每个文档需包含 'content' 或 'text' 字段
            top_k: 返回前 k 个结果
            score_threshold: 分数阈值，低于此分数的结果将被过滤
            timeout: 超时时间（秒）
            
        Returns:
            重排序后的文档列表，添加 'rerank_score' 字段
        """
        if not documents:
            return []
        
        try:
            # 提取文档文本
            doc_texts = []
            for doc in documents:
                text = doc.get('content') or doc.get('text') or doc.get('name', '')
                doc_texts.append(text)
            
            # 计算 query 和所有文档的 embedding
            query_embedding = self.model.encode(query, convert_to_tensor=True, device=self.device)
            doc_embeddings = self.model.encode(
                doc_texts,
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=False
            )
            
            # 计算余弦相似度
            similarities = torch.nn.functional.cosine_similarity(
                query_embedding.unsqueeze(0),
                doc_embeddings,
                dim=1
            )
            
            # 转换为 numpy 数组
            scores = similarities.cpu().numpy()
            
            # 为每个文档添加重排序分数
            reranked_docs = []
            for doc, score in zip(documents, scores):
                doc_copy = doc.copy()
                doc_copy['rerank_score'] = float(score)
                reranked_docs.append(doc_copy)
            
            # 按分数降序排序
            reranked_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            # 过滤低分结果
            if score_threshold > 0:
                reranked_docs = [
                    doc for doc in reranked_docs
                    if doc['rerank_score'] >= score_threshold
                ]
            
            # 返回 top_k 结果
            result = reranked_docs[:top_k]
            
            logger.info(
                f"Rerank 完成: {len(documents)} -> {len(result)} 文档, "
                f"分数范围: [{result[-1]['rerank_score']:.3f}, {result[0]['rerank_score']:.3f}]"
                if result else "无结果"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Rerank 失败: {e}，返回原始结果")
            return documents[:top_k]
    
    @staticmethod
    def rrf_fusion(
        result_lists: List[List[Dict]],
        k: int = 60,
        id_field: str = 'id',
        weights: Optional[List[float]] = None
    ) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) 多路结果融合

        Args:
            result_lists: 多个检索结果列表
            k: RRF 参数，默认 60
            id_field: 用于识别文档的字段名
            weights: 每路结果的权重列表，None 则等权（1.0）

        Returns:
            融合后的结果列表，按 RRF 分数降序排列
        """
        if not result_lists:
            return []

        # 默认等权
        if weights is None:
            weights = [1.0] * len(result_lists)

        # 计算每个文档的加权 RRF 分数
        rrf_scores = defaultdict(float)
        doc_map = {}  # 存储文档对象

        for list_idx, result_list in enumerate(result_lists):
            w = weights[list_idx] if list_idx < len(weights) else 1.0
            for rank, doc in enumerate(result_list, start=1):
                doc_id = doc.get(id_field, id(doc))  # 使用 id 字段或对象 id
                rrf_scores[doc_id] += w * (1.0 / (k + rank))

                # 保存文档对象（如果已存在则保留第一个）
                if doc_id not in doc_map:
                    doc_map[doc_id] = doc.copy()
        
        # 为每个文档添加 RRF 分数
        fused_docs = []
        for doc_id, score in rrf_scores.items():
            doc = doc_map[doc_id]
            doc['rrf_score'] = score
            fused_docs.append(doc)
        
        # 按 RRF 分数降序排序
        fused_docs.sort(key=lambda x: x['rrf_score'], reverse=True)
        
        logger.info(
            f"RRF 融合完成: {len(result_lists)} 路结果 (weights={[round(w, 2) for w in weights]}) -> {len(fused_docs)} 文档"
        )
        
        return fused_docs


# 便捷函数
def get_reranker() -> FitnessReranker:
    """获取 Reranker 单例实例"""
    return FitnessReranker.get_instance()


def rerank_results(
    query: str,
    documents: List[Dict],
    top_k: int = 5,
    score_threshold: float = 0.0
) -> List[Dict]:
    """
    便捷函数：对检索结果进行重排序
    
    Args:
        query: 用户查询
        documents: 待重排序的文档列表
        top_k: 返回前 k 个结果
        score_threshold: 分数阈值
        
    Returns:
        重排序后的文档列表
    """
    reranker = get_reranker()
    return reranker.rerank(query, documents, top_k, score_threshold)
