"""
知识库导入脚本 — 将生成的 JSON chunks 向量化并追加到现有知识向量库

运行方式（容器内）:
  cd /app && DATA_DIR=/app/data/v3 python data/knowledge_generation/import_to_vectordb.py

流程:
  1. 读取 output/*.json
  2. 用 gte-large-zh 编码为 1024 维向量
  3. 追加到现有的 knowledge.npy / knowledge_ids.json / knowledge_payloads.json
"""

import json
import os
import sys
import time
import numpy as np
from typing import List, Dict

# 确保路径
sys.path.insert(0, "/app")

DATA_DIR = os.environ.get("DATA_DIR", "/app/data/v3")
VECTORS_DIR = os.path.join(DATA_DIR, "vectors")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def load_generated_chunks() -> List[Dict]:
    """加载所有生成的 JSON chunks"""
    all_chunks = []
    for filename in sorted(os.listdir(OUTPUT_DIR)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
            all_chunks.extend(chunks)
        print(f"  加载 {filename}: {len(chunks)} chunks")
    return all_chunks


def encode_chunks(chunks: List[Dict]) -> np.ndarray:
    """用 gte-large-zh 编码所有 chunks"""
    from src_v2.tools.embedding import encode

    # 构建搜索文本（title + content 拼接）
    texts = []
    for chunk in chunks:
        text = f"{chunk['title']}\n{chunk['content']}"
        # 截断过长文本（gte-large-zh 最大 512 tokens）
        if len(text) > 1500:
            text = text[:1500]
        texts.append(text)

    print(f"  编码 {len(texts)} 条文本...")
    t0 = time.time()

    # 分批编码（避免 OOM）
    batch_size = 32
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        vectors = encode(batch)
        all_vectors.append(vectors)
        if (i + batch_size) % 100 == 0:
            print(f"    已编码 {min(i+batch_size, len(texts))}/{len(texts)}")

    result = np.vstack(all_vectors)
    elapsed = time.time() - t0
    print(f"  编码完成: {result.shape}, 耗时 {elapsed:.1f}s")
    return result


def append_to_knowledge_db(chunks: List[Dict], vectors: np.ndarray):
    """追加到现有知识向量库"""
    npy_path = os.path.join(VECTORS_DIR, "knowledge.npy")
    ids_path = os.path.join(VECTORS_DIR, "knowledge_ids.json")
    payloads_path = os.path.join(VECTORS_DIR, "knowledge_payloads.json")

    # 加载现有数据
    existing_vectors = np.load(npy_path) if os.path.exists(npy_path) else np.empty((0, 1024), dtype=np.float32)
    existing_ids = json.load(open(ids_path, "r", encoding="utf-8")) if os.path.exists(ids_path) else []
    existing_payloads = json.load(open(payloads_path, "r", encoding="utf-8")) if os.path.exists(payloads_path) else []

    print(f"  现有知识库: {existing_vectors.shape[0]} vectors")

    # 生成新 IDs
    max_existing_id = 0
    for eid in existing_ids:
        try:
            num = int(str(eid).split("_")[-1]) if "_" in str(eid) else int(eid)
            max_existing_id = max(max_existing_id, num)
        except (ValueError, TypeError):
            pass

    new_ids = [f"ai_kb_{max_existing_id + i + 1}" for i in range(len(chunks))]

    # 构建 payloads（与现有格式对齐）
    new_payloads = []
    for chunk in chunks:
        payload = {
            "source": chunk["source"],
            "title": chunk["title"],
            "chunk_text": chunk["content"][:500],  # 截断存储
            "content": chunk["content"],
            "category": chunk["category"],
            "subcategory": chunk.get("subcategory", ""),
            "keywords": chunk.get("keywords", []),
            "language": "zh",
            "source_type": "ai_generated",
            "confidence": chunk.get("confidence", "high"),
            "related_muscles": chunk.get("related_muscles", []),
            "related_injuries": chunk.get("related_injuries", []),
        }
        new_payloads.append(payload)

    # 合并
    merged_vectors = np.vstack([existing_vectors, vectors.astype(np.float32)])
    merged_ids = existing_ids + new_ids
    merged_payloads = existing_payloads + new_payloads

    # 保存
    np.save(npy_path, merged_vectors)
    with open(ids_path, "w", encoding="utf-8") as f:
        json.dump(merged_ids, f, ensure_ascii=False)
    with open(payloads_path, "w", encoding="utf-8") as f:
        json.dump(merged_payloads, f, ensure_ascii=False)

    print(f"  导入完成: {existing_vectors.shape[0]} → {merged_vectors.shape[0]} vectors (+{len(chunks)})")
    print(f"  文件已更新:")
    print(f"    {npy_path}")
    print(f"    {ids_path}")
    print(f"    {payloads_path}")


def main():
    print("=" * 60)
    print("知识库导入 — AI 生成知识 → 向量库")
    print("=" * 60)

    # 1. 加载 chunks
    print("\n[1/3] 加载生成的 chunks...")
    chunks = load_generated_chunks()
    if not chunks:
        print("  没有找到 chunks，退出")
        return
    print(f"  总计: {len(chunks)} chunks")

    # 2. 向量化
    print("\n[2/3] 向量化（gte-large-zh）...")
    vectors = encode_chunks(chunks)

    # 3. 导入
    print("\n[3/3] 追加到知识向量库...")
    append_to_knowledge_db(chunks, vectors)

    print("\n" + "=" * 60)
    print("导入完成！重启 DAML-RAG 服务后生效。")
    print("=" * 60)


if __name__ == "__main__":
    main()
