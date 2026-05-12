"""
从 Qdrant 导出向量数据为 .npy 文件

用法：
  docker exec fitness_daml_rag python -m scripts.export_vectors

输出：
  data/vectors/exercises.npy          — 1790 × 1536 向量矩阵
  data/vectors/exercises_ids.json     — ID 映射 {index: exercise_id}
  data/vectors/knowledge.npy          — 4062 × 1536
  data/vectors/knowledge_ids.json
  data/vectors/foods.npy              — 1851 × 1536
  data/vectors/foods_ids.json
"""

import json
import os
import sys
import time

import numpy as np

# Qdrant 连接配置（容器内）
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
OUTPUT_DIR = os.getenv("EXPORT_OUTPUT_DIR", "/app/data/vectors")

# 要导出的 collection
COLLECTIONS = [
    {"name": "fitness_exercises_v2", "output_prefix": "exercises"},
    {"name": "training_knowledge", "output_prefix": "knowledge"},
    {"name": "food_nutrition_vector", "output_prefix": "foods"},
]


def export_collection(client, collection_name: str, output_prefix: str):
    """导出单个 collection 的所有向量和 payload"""
    print(f"\n{'='*60}")
    print(f"导出 collection: {collection_name}")
    print(f"{'='*60}")

    # 获取 collection 信息
    info = client.get_collection(collection_name)
    total_points = info.points_count
    vector_size = info.config.params.vectors.size
    print(f"  总点数: {total_points}, 向量维度: {vector_size}")

    # 滚动获取所有点
    all_vectors = []
    all_ids = []
    all_payloads = []
    offset = None
    batch_size = 100
    fetched = 0

    while True:
        results = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_vectors=True,
            with_payload=True,
        )

        points, next_offset = results

        if not points:
            break

        for point in points:
            all_vectors.append(point.vector)
            all_ids.append(str(point.id))
            # 保存 payload（元数据）
            all_payloads.append(point.payload if point.payload else {})

        fetched += len(points)
        if fetched % 500 == 0:
            print(f"  已获取: {fetched}/{total_points}")

        if next_offset is None:
            break
        offset = next_offset

    print(f"  获取完成: {fetched} 个点")

    # 转换为 numpy 数组
    vectors_array = np.array(all_vectors, dtype=np.float32)
    print(f"  向量矩阵形状: {vectors_array.shape}")
    print(f"  内存占用: {vectors_array.nbytes / 1024 / 1024:.1f} MB")

    # 保存向量
    vectors_path = os.path.join(OUTPUT_DIR, f"{output_prefix}.npy")
    np.save(vectors_path, vectors_array)
    print(f"  向量已保存: {vectors_path}")

    # 保存 ID 映射
    ids_path = os.path.join(OUTPUT_DIR, f"{output_prefix}_ids.json")
    with open(ids_path, "w", encoding="utf-8") as f:
        json.dump(all_ids, f, ensure_ascii=False)
    print(f"  ID 映射已保存: {ids_path} ({len(all_ids)} 条)")

    # 保存 payload（元数据）
    payloads_path = os.path.join(OUTPUT_DIR, f"{output_prefix}_payloads.json")
    with open(payloads_path, "w", encoding="utf-8") as f:
        json.dump(all_payloads, f, ensure_ascii=False, indent=None)
    print(f"  Payload 已保存: {payloads_path}")

    return {
        "collection": collection_name,
        "count": fetched,
        "dimension": vector_size,
        "vectors_file": vectors_path,
        "ids_file": ids_path,
    }


def main():
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        print("错误: 需要 qdrant-client 包")
        print("  pip install qdrant-client")
        sys.exit(1)

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 连接 Qdrant
    print(f"连接 Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # 验证连接
    collections = client.get_collections().collections
    print(f"可用 collections: {[c.name for c in collections]}")

    # 导出每个 collection
    start_time = time.time()
    results = []

    for col in COLLECTIONS:
        # 检查 collection 是否存在
        col_names = [c.name for c in collections]
        if col["name"] not in col_names:
            print(f"\n⚠️ Collection '{col['name']}' 不存在，跳过")
            continue

        result = export_collection(client, col["name"], col["output_prefix"])
        results.append(result)

    # 汇总
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"导出完成！耗时: {elapsed:.1f}s")
    print(f"{'='*60}")
    for r in results:
        print(f"  {r['collection']}: {r['count']} vectors × {r['dimension']} dim")

    # 保存导出元数据
    meta_path = os.path.join(OUTPUT_DIR, "_export_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "qdrant_host": QDRANT_HOST,
            "collections": results,
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
