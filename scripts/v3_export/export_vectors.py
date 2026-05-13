"""
Phase 0 Task 0.1: 从 Qdrant 导出向量数据为 .npy + .json 文件

导出 3 个核心 collection:
  - fitness_exercises_v2: 1790 vectors × 1024 dim
  - training_knowledge: 4062 vectors × 1024 dim
  - food_nutrition_vector: 1851 vectors × 1024 dim

输出到 data/v3/ 目录
"""

import json
import sys
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import ScrollRequest

# 配置
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "v3"

COLLECTIONS = [
    "fitness_exercises_v2",
    "training_knowledge",
    "food_nutrition_vector",
]


def export_collection(client: QdrantClient, collection_name: str, output_dir: Path):
    """导出单个 collection 的向量和元数据"""
    print(f"\n{'='*60}")
    print(f"导出 {collection_name}...")

    info = client.get_collection(collection_name)
    total = info.points_count
    print(f"  总点数: {total}")

    if total == 0:
        print(f"  跳过（空集合）")
        return

    # 获取向量维度
    vec_config = info.config.params.vectors
    dim = vec_config.size if hasattr(vec_config, "size") else None
    if dim is None:
        print(f"  错误：无法获取向量维度")
        return
    print(f"  向量维度: {dim}")

    # 滚动读取所有点
    all_vectors = []
    all_ids = []
    all_payloads = []

    offset = None
    batch_size = 256
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
            all_ids.append(str(point.id))
            all_vectors.append(point.vector)
            # payload 转为可序列化的 dict
            payload = dict(point.payload) if point.payload else {}
            all_payloads.append(payload)

        fetched += len(points)
        print(f"  已读取: {fetched}/{total}", end="\r")

        if next_offset is None:
            break
        offset = next_offset

    print(f"  已读取: {fetched}/{total} ✓")

    # 保存向量为 .npy
    vectors_array = np.array(all_vectors, dtype=np.float32)
    vectors_path = output_dir / f"{collection_name}.npy"
    np.save(vectors_path, vectors_array)
    print(f"  向量保存: {vectors_path} ({vectors_array.shape})")

    # 保存 ID 映射
    ids_path = output_dir / f"{collection_name}_ids.json"
    with open(ids_path, "w", encoding="utf-8") as f:
        json.dump(all_ids, f)
    print(f"  ID 映射: {ids_path} ({len(all_ids)} 条)")

    # 保存 payload 元数据
    payloads_path = output_dir / f"{collection_name}_payloads.json"
    with open(payloads_path, "w", encoding="utf-8") as f:
        json.dump(all_payloads, f, ensure_ascii=False, indent=None)
    print(f"  Payload: {payloads_path}")

    # 验证
    assert vectors_array.shape == (total, dim), f"形状不匹配: {vectors_array.shape} != ({total}, {dim})"
    assert len(all_ids) == total, f"ID 数量不匹配: {len(all_ids)} != {total}"
    print(f"  验证通过 ✓")


def main():
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Qdrant 导出工具")
    print(f"连接: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"输出目录: {output_dir}")

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # 验证连接
    collections = client.get_collections().collections
    available = [c.name for c in collections]
    print(f"可用集合: {available}")

    for coll_name in COLLECTIONS:
        if coll_name not in available:
            print(f"\n⚠️  集合 {coll_name} 不存在，跳过")
            continue
        export_collection(client, coll_name, output_dir)

    print(f"\n{'='*60}")
    print(f"导出完成！文件列表:")
    for f in sorted(output_dir.glob("*")):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
