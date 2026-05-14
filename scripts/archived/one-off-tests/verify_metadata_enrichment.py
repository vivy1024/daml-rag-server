#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证元数据增强结果
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import models
from collections import Counter

def verify_metadata():
    client = QdrantClient("qdrant", port=6333)
    collection_name = "training_knowledge"
    
    print("=== 元数据增强验证报告 ===\n")
    
    # 获取集合信息
    collection_info = client.get_collection(collection_name)
    total_points = collection_info.points_count
    print(f"总向量数: {total_points}\n")
    
    # 统计各字段覆盖率
    stats = {
        "doc_title": 0,
        "keywords": 0,
        "content_type": 0,
        "language": 0,
        "char_count": 0,
    }
    content_types = Counter()
    languages = Counter()
    keyword_counts = []
    
    # 滚动获取所有向量
    offset = None
    checked = 0
    
    while True:
        records, next_offset = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        
        if not records:
            break
        
        for record in records:
            payload = record.payload or {}
            
            if "doc_title" in payload:
                stats["doc_title"] += 1
            if "keywords" in payload and payload["keywords"]:
                stats["keywords"] += 1
                keyword_counts.append(len(payload["keywords"]))
            if "content_type" in payload:
                stats["content_type"] += 1
                content_types[payload["content_type"]] += 1
            if "language" in payload:
                stats["language"] += 1
                languages[payload["language"]] += 1
            if "char_count" in payload:
                stats["char_count"] += 1
            
            checked += 1
        
        offset = next_offset
        if offset is None:
            break
    
    # 输出统计结果
    print("字段覆盖率:")
    for field, count in stats.items():
        coverage = count / total_points * 100 if total_points > 0 else 0
        print(f"  {field}: {count}/{total_points} ({coverage:.1f}%)")
    
    print(f"\n内容类型分布:")
    for content_type, count in content_types.most_common():
        percentage = count / total_points * 100 if total_points > 0 else 0
        print(f"  {content_type}: {count} ({percentage:.1f}%)")
    
    print(f"\n语言分布:")
    for lang, count in languages.most_common():
        percentage = count / total_points * 100 if total_points > 0 else 0
        print(f"  {lang}: {count} ({percentage:.1f}%)")
    
    if keyword_counts:
        avg_keywords = sum(keyword_counts) / len(keyword_counts)
        print(f"\n关键词统计:")
        print(f"  平均关键词数: {avg_keywords:.2f}")
        print(f"  最少关键词数: {min(keyword_counts)}")
        print(f"  最多关键词数: {max(keyword_counts)}")
    
    # 测试各种过滤查询
    print(f"\n过滤查询测试:")
    
    test_filters = [
        ("exercise", "exercise"),
        ("nutrition", "nutrition"),
        ("anatomy", "anatomy"),
        ("中文内容", "zh"),
        ("英文内容", "en"),
    ]
    
    for name, value in test_filters:
        try:
            if name in ["中文内容", "英文内容"]:
                field = "language"
            else:
                field = "content_type"
            
            results = client.query_points(
                collection_name=collection_name,
                query=[0.0]*1024,
                query_filter=models.Filter(
                    must=[models.FieldCondition(
                        key=field,
                        match=models.MatchValue(value=value)
                    )]
                ),
                limit=1,
                with_payload=True,
            )
            
            if results.points:
                print(f"  {name}: 成功 (找到 {len(results.points)} 个结果)")
            else:
                print(f"  {name}: 无结果")
        except Exception as e:
            print(f"  {name}: 失败 - {e}")
    
    # 显示几个样本
    print(f"\n样本展示:")
    results = client.query_points(
        collection_name=collection_name,
        query=[0.0]*1024,
        limit=5,
        with_payload=True,
    )
    
    for i, point in enumerate(results.points, 1):
        payload = point.payload or {}
        print(f"\n样本 {i}:")
        print(f"  标题: {payload.get('doc_title', 'N/A')}")
        print(f"  类型: {payload.get('content_type', 'N/A')}")
        print(f"  语言: {payload.get('language', 'N/A')}")
        print(f"  关键词: {', '.join(payload.get('keywords', []))}")
        print(f"  字符数: {payload.get('char_count', 'N/A')}")
        text = payload.get('chunk_text', '')[:100]
        print(f"  文本预览: {text}...")
    
    print(f"\n=== 验证完成 ===")

if __name__ == "__main__":
    verify_metadata()
