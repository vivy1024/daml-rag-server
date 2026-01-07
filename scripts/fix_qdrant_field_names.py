#!/usr/bin/env python3
"""
修复Qdrant字段名
将difficulty重命名为difficulty_zh，添加muscles_primary_zh和muscles_secondary_zh
"""

import os
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct


def main():
    print("="*60)
    print("🔧 修复Qdrant fitness_exercises_v2字段名")
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
        # 获取一批点
        results, next_offset = client.scroll(
            collection_name="fitness_exercises_v2",
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        if not results:
            break
        
        points_to_update = []
        
        for point in results:
            payload = point.payload
            updated = False
            new_payload = dict(payload)
            
            # 1. difficulty -> difficulty_zh
            if "difficulty" in payload and "difficulty_zh" not in payload:
                new_payload["difficulty_zh"] = payload["difficulty"]
                del new_payload["difficulty"]
                updated = True
            
            # 2. 添加muscles_primary_zh（从primary_muscle_zh或all_muscles_zh）
            if "muscles_primary_zh" not in payload:
                primary = payload.get("primary_muscle_zh")
                if primary:
                    new_payload["muscles_primary_zh"] = [primary] if isinstance(primary, str) else primary
                    updated = True
            
            # 3. 添加muscles_secondary_zh（从all_muscles_zh减去primary）
            if "muscles_secondary_zh" not in payload:
                all_muscles = payload.get("all_muscles_zh", [])
                primary = payload.get("primary_muscle_zh", "")
                if all_muscles:
                    secondary = [m for m in all_muscles if m != primary]
                    new_payload["muscles_secondary_zh"] = secondary
                    updated = True
            
            if updated:
                points_to_update.append(PointStruct(
                    id=point.id,
                    payload=new_payload,
                    vector={}  # 不更新向量
                ))
        
        # 批量更新payload
        if points_to_update:
            for p in points_to_update:
                client.set_payload(
                    collection_name="fitness_exercises_v2",
                    payload=p.payload,
                    points=[p.id]
                )
            updated_count += len(points_to_update)
            print(f"  ✅ 已更新 {updated_count}/{total_points} 个点")
        
        offset = next_offset
        if offset is None:
            break
    
    print(f"\n🎉 完成！共更新 {updated_count} 个点")
    
    # 验证
    print("\n📊 验证更新结果:")
    results, _ = client.scroll(
        collection_name="fitness_exercises_v2",
        limit=1,
        with_payload=True
    )
    
    if results:
        payload = results[0].payload
        fields = list(payload.keys())
        print(f"  字段数: {len(fields)}")
        
        check_fields = ["difficulty_zh", "muscles_primary_zh", "muscles_secondary_zh"]
        for f in check_fields:
            if f in fields:
                print(f"  ✓ {f}: {payload.get(f)}")
            else:
                print(f"  ✗ {f}: 缺失")
        
        if "difficulty" in fields:
            print(f"  ⚠️ difficulty (旧字段仍存在)")


if __name__ == "__main__":
    main()
