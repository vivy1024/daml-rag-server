# -*- coding: utf-8 -*-
"""
BM25全文检索引擎
使用rank_bm25库实现BM25Okapi算法，支持中文分词
"""
import logging
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
import jieba
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class BM25Engine:
    """BM25全文检索引擎（单例模式）"""

    _instance = None

    def __init__(
        self,
        qdrant_host: str = "qdrant",
        qdrant_port: int = 6333,
        collection_name: str = "training_knowledge"
    ):
        """
        初始化BM25引擎

        Args:
            qdrant_host: Qdrant服务地址
            qdrant_port: Qdrant端口
            collection_name: Qdrant集合名称
        """
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name

        self.index = None  # BM25Okapi实例
        self.documents = []  # 原始文档列表
        self.tokenized_corpus = []  # 分词后的语料

        # 中文停用词列表
        self.stopwords = set([
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
            '看', '好', '自己', '这', '那', '里', '为', '与', '及', '等', '之', '于'
        ])

        logger.info(f"初始化BM25引擎: {qdrant_host}:{qdrant_port}/{collection_name}")
        self._build_index()

    @classmethod
    def get_instance(
        cls,
        qdrant_host: str = "qdrant",
        qdrant_port: int = 6333,
        collection_name: str = "training_knowledge"
    ) -> "BM25Engine":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(qdrant_host, qdrant_port, collection_name)
        return cls._instance

    def _tokenize(self, text: str) -> List[str]:
        """
        中文分词（jieba）

        Args:
            text: 待分词文本

        Returns:
            分词列表（去除停用词）
        """
        if not text:
            return []

        # jieba分词
        tokens = jieba.cut(text.lower())

        # 去除停用词和空白
        tokens = [
            token.strip()
            for token in tokens
            if token.strip() and token not in self.stopwords
        ]

        return tokens

    def _build_index(self):
        """从Qdrant加载所有文档构建BM25索引"""
        try:
            logger.info("开始构建BM25索引...")

            # 连接Qdrant
            client = QdrantClient(self.qdrant_host, port=self.qdrant_port)

            # 使用scroll API分批获取所有文档
            offset = None
            all_points = []
            batch_count = 0

            while True:
                result = client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,  # 不需要向量，节省内存
                )
                points, offset = result
                all_points.extend(points)
                batch_count += 1

                if offset is None:
                    break

                if batch_count % 10 == 0:
                    logger.info(f"  已加载 {len(all_points)} 个文档...")

            logger.info(f"从Qdrant加载完成: {len(all_points)} 个文档")

            # 提取文档文本并分词
            for point in all_points:
                # 构建文档对象（优先使用chunk_text，其次text）
                text = point.payload.get('chunk_text') or point.payload.get('text', '')
                doc = {
                    'id': str(point.id),
                    'text': text,
                    'payload': point.payload
                }
                self.documents.append(doc)

                # 分词
                tokens = self._tokenize(doc['text'])
                self.tokenized_corpus.append(tokens)

            # 构建BM25索引
            logger.info("构建BM25索引...")
            self.index = BM25Okapi(self.tokenized_corpus)

            logger.info(f"✅ BM25索引构建完成: {len(self.documents)} 个文档")

        except Exception as e:
            logger.error(f"BM25索引构建失败: {e}")
            raise

    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        BM25全文检索

        Args:
            query: 查询文本
            top_k: 返回结果数

        Returns:
            检索结果列表，每个结果包含 {id, score, text, payload}
        """
        if not self.index or not self.documents:
            logger.warning("BM25索引未初始化")
            return []

        try:
            # 分词查询
            query_tokens = self._tokenize(query)

            if not query_tokens:
                logger.warning(f"查询分词为空: {query}")
                return []

            # BM25打分
            scores = self.index.get_scores(query_tokens)

            # 获取top_k结果
            top_indices = scores.argsort()[-top_k:][::-1]

            results = []
            for idx in top_indices:
                score = float(scores[idx])
                if score > 0:  # 只返回有分数的结果
                    doc = self.documents[idx]
                    results.append({
                        'id': doc['id'],
                        'score': score,
                        'text': doc['text'],
                        'payload': doc['payload']
                    })

            logger.info(
                f"BM25检索完成: query='{query}' ({len(query_tokens)}个词), "
                f"返回{len(results)}个结果"
            )

            return results

        except Exception as e:
            logger.error(f"BM25检索失败: {e}")
            return []


# 便捷函数
def get_bm25_engine() -> BM25Engine:
    """获取BM25引擎单例实例"""
    return BM25Engine.get_instance()


def bm25_search(query: str, top_k: int = 20) -> List[Dict]:
    """
    便捷函数：BM25全文检索

    Args:
        query: 查询文本
        top_k: 返回结果数

    Returns:
        检索结果列表
    """
    engine = get_bm25_engine()
    return engine.search(query, top_k)
