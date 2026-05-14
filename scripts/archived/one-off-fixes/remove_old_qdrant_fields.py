#!/usr/bin/env python3
"""
删除Qdrant中的旧字段
"""

import os
import sys
sys.path.insert(0, '/app')

from qdrant_client import QdrantClient


def main():
    print("="*60)
    print("🗑️ 删除Qdrant旧字段 difficulty")
    print("="*60)
    
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "qdrant"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )
    
    # 获取集合信息
    collection_info = client.get_collection("fitness_exercises_v2")
    total_points = collection_info.points_count
    print(f"\n📊 总向量数: {total_points}")
    
    # 分批处理
    batch_size = 100
    offset = None
    updated_count = 0
    
    while True:
        results, next_offset = client.scroll(
            collection_name="fitness_exercises_v2",
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        if not results:
            break
        
        for point in results:
            if "difficulty" in point.payload:
                # 删除旧字段
                client.delete_payload(
                    collection_name="fitness_exercises_v2",
                    keys=["difficulty"],
                    points=[point.id]
                )
                updated_count += 1
        
        if updated_count > 0 and updated_count % 100 == 0:
            print(f"  ✅ 已处理 {updated_count} 个点")
        
        offset = next_offset
        if offset is None:
            break
    
    print(f"\n🎉 完成！共删除 {updated_count} 个点的旧字段")
    
    # 验证
    print("\n📊 验证结果:")
    results, _ = client.scroll(
        collection_name="fitness_exercises_v2",
        limit=1,
        with_payload=True
    )
    
    if results:
        payload = results[0].payload
        if "difficulty" in payload:
            print("  ⚠️ difficulty 仍存在")
        else:
            print("  ✅ difficulty 已删除")
        
        if "difficulty_zh" in payload:
            print(f"  ✓ difficulty_zh: {payload['difficulty_zh']}")


if __name__ == "__main__":
    main()
