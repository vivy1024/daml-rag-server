# -*- coding: utf-8 -*-
"""调试Qdrant向量检索问题

直接在容器内测试Qdrant查询，绕过HTTP层
"""

import sys
import os
sys.path.insert(0, '/app')

from qdrant_client import QdrantClient

def main():
    print("=" * 60)
    print("🔍 调试Qdrant向量检索")
    print("=" * 60)
    
    # 连接Qdrant
    client = QdrantClient(host="qdrant", port=6333)
    
    # 1. 检查集合信息
    print("\n📊 集合信息:")
    collections = client.get_collections().collections
    for c in collections:
        print(f"  - {c.name}")
    
    # 2. 检查fitness_exercises_v2集合
    collection_name = "fitness_exercises_v2"
    try:
        info = client.get_collection(collection_name)
        print(f"\n📊 {collection_name} 集合详情:")
        print(f"  - 向量数量: {info.points_count}")
        print(f"  - 向量维度: {info.config.params.vectors.size}")
        print(f"  - 距离度量: {info.config.params.vectors.distance}")
    except Exception as e:
        print(f"❌ 获取集合信息失败: {e}")
        return
    
    # 3. 获取几个样本点，查看payload结构
    print(f"\n📊 样本数据 (前3个):")
    try:
        # 使用scroll获取样本
        results, _ = client.scroll(
            collection_name=collection_name,
            limit=3,
            with_payload=True,
            with_vectors=False
        )
        
        for i, point in enumerate(results):
            print(f"\n  样本 {i+1}:")
            print(f"    ID: {point.id}")
            print(f"    Payload字段: {list(point.payload.keys())}")
            # 显示部分payload内容
            for key in ['exercise_id', 'name_zh', 'name_en', 'equipment_zh', 'difficulty', 'primary_muscle_zh']:
                if key in point.payload:
                    value = point.payload[key]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"    {key}: {value}")
    except Exception as e:
        print(f"❌ 获取样本失败: {e}")
    
    # 4. 测试向量检索（使用BGE模型）
    print("\n📊 测试向量检索:")
    try:
        from src.framework.models.model_cache_manager import ModelCacheManager
        cache = ModelCacheManager.get_instance()
        encoder = cache.get_bge_model("BAAI/bge-m3")
        
        if encoder:
            print("  ✅ BGE模型加载成功")
            
            # 编码测试查询
            test_query = "胸部训练动作"
            query_vector = encoder.encode(test_query, convert_to_numpy=True)
            print(f"  查询文本: {test_query}")
            print(f"  向量维度: {len(query_vector)}")
            
            # 执行向量检索
            results = client.query_points(
                collection_name=collection_name,
                query=query_vector.tolist(),
                limit=5
            )
            
            print(f"\n  检索结果 ({len(results.points)}个):")
            for r in results.points:
                name = r.payload.get('name_zh', 'N/A')
                score = r.score
                print(f"    - {name} (相似度: {score:.4f})")
        else:
            print("  ❌ BGE模型加载失败")
    except Exception as e:
        print(f"❌ 向量检索测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. 测试带过滤条件的检索
    print("\n📊 测试带过滤条件的检索:")
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        # 测试不同的过滤条件
        test_filters = [
            {"label": "Exercise"},  # 可能不存在的字段
            {"difficulty": "beginner"},
            None  # 无过滤
        ]
        
        for filter_dict in test_filters:
            if filter_dict:
                conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v))
                    for k, v in filter_dict.items()
                ]
                qdrant_filter = Filter(must=conditions)
                filter_desc = str(filter_dict)
            else:
                qdrant_filter = None
                filter_desc = "无过滤"
            
            results = client.query_points(
                collection_name=collection_name,
                query=query_vector.tolist(),
                limit=5,
                query_filter=qdrant_filter
            )
            
            print(f"  过滤条件: {filter_desc} → 结果数: {len(results.points)}")
            
    except Exception as e:
        print(f"❌ 过滤测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ 调试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
