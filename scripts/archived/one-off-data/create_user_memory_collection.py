# -*- coding: utf-8 -*-
"""
创建 Qdrant user_memory collection

用于存储用户跨对话记忆向量，支持按 user_id 过滤检索。
向量维度：1024（GTE-Large-zh）
距离度量：Cosine

使用方式：
    docker exec fitness_daml_rag python scripts/create_user_memory_collection.py

版本：v1.0.0
日期：2026-02-20
"""

import sys
import os

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
)

from src.framework.clients.qdrant_client import create_qdrant_client

COLLECTION_NAME = "user_memory"
VECTOR_DIM = 1024  # GTE-Large-zh


def main():
    client = create_qdrant_client()

    # 如果 collection 已存在则跳过
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"✅ Collection '{COLLECTION_NAME}' 已存在，跳过创建")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_DIM,
            distance=Distance.COSINE,
        ),
    )

    # 为 user_id 创建 payload 索引，加速过滤
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="user_id",
        field_schema=PayloadSchemaType.INTEGER,
    )

    print(f"✅ Collection '{COLLECTION_NAME}' 创建成功 (dim={VECTOR_DIM}, cosine)")


if __name__ == "__main__":
    main()
