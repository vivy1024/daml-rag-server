#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chunk元数据增强脚本
增强Qdrant中所有向量的payload，添加关键词、内容类型等元数据
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import models
import jieba
import jieba.analyse
from collections import Counter
import re
from typing import List, Dict, Any

# 内容类型分类规则
CONTENT_TYPE_RULES = {
    "exercise": ["动作", "训练", "组数", "次数", "重量", "exercise", "rep", "set", "workout", "movement"],
    "nutrition": ["蛋白质", "碳水", "脂肪", "热量", "营养", "protein", "calorie", "carb", "diet", "meal"],
    "anatomy": ["肌肉", "关节", "骨骼", "解剖", "muscle", "joint", "bone", "anatomy", "tissue"],
    "rehabilitation": ["康复", "损伤", "疼痛", "禁忌", "rehab", "injury", "pain", "recovery", "contraindication"],
    "training_theory": ["周期化", "渐进超负荷", "训练原则", "periodization", "progressive", "overload", "principle"],
}

def extract_keywords(text: str, top_k: int = 5) -> List[str]:
    """提取关键词（使用jieba TF-IDF）"""
    if not text or len(text) < 10:
        return []
    keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=False)
    return keywords

def classify_content_type(text: str) -> str:
    """根据关键词规则分类内容类型"""
    text_lower = text.lower()
    scores = {}
    for content_type, keywords in CONTENT_TYPE_RULES.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[content_type] = score
    if not scores:
        return "general"
    return max(scores.items(), key=lambda x: x[1])[0]

def detect_language(text: str) -> str:
    """检测语言（简单规则：中文字符占比）"""
    if not text:
        return "unknown"
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())
    if total_chars == 0:
        return "unknown"
    chinese_ratio = chinese_chars / total_chars
    if chinese_ratio > 0.3:
        return "zh"
    elif chinese_ratio < 0.1:
        return "en"
    else:
        return "mixed"

def extract_doc_title(payload: Dict[str, Any]) -> str:
    """提取文档标题"""
    if "title" in payload and payload["title"]:
        return payload["title"]
    if "source" in payload:
        source = payload["source"]
        if isinstance(source, str):
            filename = Path(source).stem
            return filename
    return "未知文档"

def enrich_metadata(client: QdrantClient, collection_name: str = "training_knowledge"):
    """增强所有chunk的元数据"""
    print(f"开始增强集合 {collection_name} 的元数据...")
    collection_info = client.get_collection(collection_name)
    total_points = collection_info.points_count
    print(f"总向量数: {total_points}")
    
    batch_size = 100
    offset = None
    processed = 0
    stats = {"content_types": Counter(), "languages": Counter(), "keywords_count": 0}
    
    while True:
        records, next_offset = client.scroll(
            collection_name=collection_name, limit=batch_size, offset=offset,
            with_payload=True, with_vectors=False)
        if not records:
            break
        for record in records:
            point_id = record.id
            payload = record.payload or {}
            text = payload.get("chunk_text", "") or payload.get("text", "")
            if not text:
                processed += 1
                continue
            enriched = {}
            enriched["doc_title"] = extract_doc_title(payload)
            keywords = extract_keywords(text, top_k=5)
            enriched["keywords"] = keywords
            if keywords:
                stats["keywords_count"] += 1
            content_type = classify_content_type(text)
            enriched["content_type"] = content_type
            stats["content_types"][content_type] += 1
            language = detect_language(text)
            enriched["language"] = language
            stats["languages"][language] += 1
            if "char_count" not in payload:
                enriched["char_count"] = len(text)
            client.set_payload(collection_name=collection_name, payload=enriched, points=[point_id])
            processed += 1
            if processed % 100 == 0:
                print(f"已处理: {processed}/{total_points} ({processed/total_points*100:.1f}%)")
        offset = next_offset
        if offset is None:
            break
    
    print(f"\n元数据增强完成！共处理 {processed} 个向量")
    print(f"\n统计数据:")
    print(f"  关键词覆盖率: {stats['keywords_count']}/{processed} ({stats['keywords_count']/processed*100:.1f}%)")
    print(f"\n  内容类型分布:")
    for content_type, count in stats["content_types"].most_common():
        print(f"    {content_type}: {count} ({count/processed*100:.1f}%)")
    print(f"\n  语言分布:")
    for lang, count in stats["languages"].most_common():
        print(f"    {lang}: {count} ({count/processed*100:.1f}%)")
    return stats

def create_payload_indexes(client: QdrantClient, collection_name: str = "training_knowledge"):
    """为新增字段创建payload索引"""
    print(f"\n创建payload索引...")
    try:
        client.create_payload_index(collection_name=collection_name, field_name="content_type",
            field_schema=models.PayloadSchemaType.KEYWORD)
        print("content_type索引创建成功")
    except Exception as e:
        print(f"content_type索引创建失败（可能已存在）: {e}")
    try:
        client.create_payload_index(collection_name=collection_name, field_name="keywords",
            field_schema=models.PayloadSchemaType.KEYWORD)
        print("keywords索引创建成功")
    except Exception as e:
        print(f"keywords索引创建失败（可能已存在）: {e}")
    try:
        client.create_payload_index(collection_name=collection_name, field_name="language",
            field_schema=models.PayloadSchemaType.KEYWORD)
        print("language索引创建成功")
    except Exception as e:
        print(f"language索引创建失败（可能已存在）: {e}")

def verify_enrichment(client: QdrantClient, collection_name: str = "training_knowledge"):
    """验证元数据增强结果"""
    print(f"\n验证元数据增强结果...")
    results = client.query_points(collection_name=collection_name, query=[0.0]*1024, limit=3, with_payload=True)
    print(f"\n样本检查:")
    for i, point in enumerate(results.points, 1):
        payload = point.payload or {}
        print(f"\n样本 {i}:")
        print(f"  doc_title: {payload.get('doc_title', 'N/A')}")
        print(f"  content_type: {payload.get('content_type', 'N/A')}")
        print(f"  language: {payload.get('language', 'N/A')}")
        print(f"  keywords: {payload.get('keywords', [])}")
        print(f"  char_count: {payload.get('char_count', 'N/A')}")
    print(f"\n测试过滤查询（content_type=exercise）:")
    try:
        results = client.query_points(collection_name=collection_name, query=[0.0]*1024,
            query_filter=models.Filter(must=[models.FieldCondition(key="content_type",
            match=models.MatchValue(value="exercise"))]), limit=3, with_payload=True)
        print(f"  找到 {len(results.points)} 个结果")
        for point in results.points:
            print(f"    - {point.payload.get('doc_title', 'N/A')}")
    except Exception as e:
        print(f"  过滤查询失败: {e}")

def main():
    client = QdrantClient("qdrant", port=6333)
    stats = enrich_metadata(client)
    create_payload_indexes(client)
    verify_enrichment(client)
    print(f"\n所有任务完成！")

if __name__ == "__main__":
    main()
