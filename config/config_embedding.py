#!/usr/bin/env python3
"""
Embedding模型配置
支持多种模型：BGE、OpenAI、本地模型
"""

import os
from pathlib import Path

# ==================== Embedding模型配置 ====================

# 选择embedding模型类型
# 选项: "bge", "openai", "sentence_transformers", "none"
# 
# 🎉 当前配置：生产模式
# - 使用 GTE-Large-zh（阿里达摩院，中文优化）
# - GPU加速已启用（CUDA 12.1）
# - 语义搜索准确率：~94.4%（相关性最高）
# - 综合分最高（0.7580）
#
# ⚙️ 技术细节：
#   - 使用 sentence-transformers 直接加载
#   - 1024维输出，与系统架构兼容
#   - 自动选择 CUDA/CPU
EMBEDDING_TYPE = "sentence_transformers"  # 生产模式：GTE-Large-zh

# GTE-Large-zh模型配置
# 理论依据：docs/02-核心架构/02-数据层/03-Qdrant向量库结构.md
GTE_MODEL = "thenlper/gte-large-zh"  # 1024维，阿里达摩院，中文优化

# 自动检测设备
try:
    import torch
    BGE_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except:
    BGE_DEVICE = "cpu"

GTE_USE_SAFETENSORS = True  # GTE-Large-zh 配置
GTE_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："  # 检索指令

# OpenAI配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "text-embedding-ada-002"  # 1536维

# Sentence Transformers配置（已更新为GTE-Large-zh）
ST_MODEL = "thenlper/gte-large-zh"  # 1024维，阿里达摩院，中文优化

# 向量维度（根据模型自动设置）
VECTOR_DIMS = {
    "bge": 768,
    "openai": 1536,
    "sentence_transformers": 1024,  # GTE-Large-zh 是 1024维
    "none": 768  # 随机向量
}

# ==================== 知识图谱配置 ====================

# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
NEO4J_DATABASE = "neo4j"

# Qdrant配置
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "fitness_kg"

# 批处理配置
BATCH_SIZE = 1000  # 节点批处理大小
RELATION_BATCH_SIZE = 500  # 关系批处理大小

# ==================== 日志配置 ====================

LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def get_embedding_config():
    """获取当前embedding配置"""
    return {
        "type": EMBEDDING_TYPE,
        "model": get_model_name(),
        "vector_dim": VECTOR_DIMS[EMBEDDING_TYPE],
        "device": BGE_DEVICE if EMBEDDING_TYPE == "bge" else "auto"  # GTE自动检测
    }


def get_model_name():
    """获取模型名称"""
    if EMBEDDING_TYPE == "bge":
        return BGE_MODEL
    elif EMBEDDING_TYPE == "openai":
        return OPENAI_MODEL
    elif EMBEDDING_TYPE == "sentence_transformers":
        return ST_MODEL
    else:
        return None


def print_config():
    """打印当前配置"""
    config = get_embedding_config()
    print("\n" + "=" * 80)
    print("📋 当前配置")
    print("=" * 80)
    print(f"Embedding类型: {config['type']}")
    print(f"模型: {config['model']}")
    print(f"向量维度: {config['vector_dim']}")
    if config['device']:
        print(f"设备: {config['device']}")
    print("=" * 80)
    print()


if __name__ == "__main__":
    print_config()

