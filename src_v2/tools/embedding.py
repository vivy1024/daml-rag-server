"""
Embedding 服务 — 文本向量化

复用容器内 sentence_transformers + gte-large-zh 模型。
单例模式，首次调用时加载模型。
"""

import logging
import time
from typing import List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# 全局单例
_encoder = None
_model_name = "thenlper/gte-large-zh"
_vector_dim = 1024


def get_encoder():
    """获取或初始化 Embedding 编码器（单例）"""
    global _encoder
    if _encoder is not None:
        return _encoder

    t0 = time.time()
    try:
        from sentence_transformers import SentenceTransformer
        _encoder = SentenceTransformer(_model_name)
        logger.info(
            f"Embedding 模型加载完成: {_model_name}, "
            f"耗时 {(time.time()-t0)*1000:.0f}ms"
        )
    except Exception as e:
        logger.error(f"Embedding 模型加载失败: {e}")
        _encoder = None

    return _encoder


def encode(text: Union[str, List[str]]) -> np.ndarray:
    """将文本编码为向量

    Args:
        text: 单个文本或文本列表

    Returns:
        np.ndarray: 形状 (D,) 或 (N, D)，D=1024
    """
    encoder = get_encoder()

    if encoder is None:
        # fallback: 随机向量（仅测试用）
        logger.warning("Embedding 模型未加载，返回随机向量")
        if isinstance(text, str):
            return np.random.randn(_vector_dim).astype(np.float32)
        return np.random.randn(len(text), _vector_dim).astype(np.float32)

    vectors = encoder.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vectors.astype(np.float32)


def encode_query(query: str) -> np.ndarray:
    """编码查询文本（单条），返回 (D,) 向量"""
    vec = encode(query)
    if vec.ndim == 2:
        vec = vec[0]
    return vec
