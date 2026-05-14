#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速模型对比测试 - 使用Qdrant已有向量

只编码查询，直接在Qdrant中搜索，避免重新编码1790个文档
"""

import os
import sys
import time

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,qdrant'

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

# 测试查询
TEST_CASES = [
    {"query": "胸部训练 卧推", "keywords": ["卧推", "胸", "推", "飞鸟", "胸大肌"]},
    {"query": "背部拉力动作", "keywords": ["背", "拉力", "划船", "下拉", "引体", "背阔肌"]},
    {"query": "腿部复合动作", "keywords": ["腿", "深蹲", "蹲", "腿举", "股四头肌", "臀"]},
    {"query": "肱二头肌弯举", "keywords": ["弯举", "二头", "肱二头肌"]},
    {"query": "核心稳定性训练", "keywords": ["核心", "腹", "平板", "稳定"]},
    {"query": "肩部推举动作", "keywords": ["肩", "推举", "三角肌"]}
]

# 模型映射
MODELS = {
    "bge-m3": "/root/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181",
    "bge-large": "BAAI/bge-large-zh-v1.5",
    "gte": "thenlper/gte-large-zh",
    "m3e": "moka-ai/m3e-large"
}


def test_model(model_key: str, qdrant: QdrantClient):
    """测试单个模型"""
    model_path = MODELS[model_key]
    print(f"\n{'='*60}")
    print(f"测试模型: {model_key}")
    print(f"{'='*60}")
    
    # 加载模型
    print(f"加载模型...")
    start = time.time()
    model = SentenceTransformer(model_path)
    print(f"加载完成，耗时: {time.time()-start:.2f}秒")
    
    total_top1 = 0
    total_top3 = 0
    total_relevant = 0
    
    for tc in TEST_CASES:
        query = tc["query"]
        keywords = tc["keywords"]
        
        # 编码查询
        query_vec = model.encode(query, normalize_embeddings=True).tolist()
        
        # 在Qdrant中搜索
        results = qdrant.query_points(
            collection_name="fitness_exercises_v2",
            query=query_vec,
            limit=5
        )
        
        # 计算指标
        top1_score = results.points[0].score if results.points else 0
        top3_scores = [p.score for p in results.points[:3]]
        top3_avg = sum(top3_scores) / 3 if top3_scores else 0
        
        # 检查相关性
        relevant = 0
        for p in results.points[:3]:
            name = p.payload.get('name_zh', '')
            muscle = p.payload.get('primary_muscle_zh', '')
            force = p.payload.get('force_zh', '')
            combined = f"{name} {muscle} {force}"
            if any(kw in combined for kw in keywords):
                relevant += 1
        
        relevance = relevant / 3
        
        total_top1 += top1_score
        total_top3 += top3_avg
        total_relevant += relevance
        
        print(f"\n查询: {query}")
        print(f"  Top1: {top1_score:.4f}, Top3平均: {top3_avg:.4f}, 相关性: {relevant}/3")
        for i, p in enumerate(results.points[:5], 1):
            name = p.payload.get('name_zh', '')
            muscle = p.payload.get('primary_muscle_zh', '')
            is_rel = any(kw in f"{name} {muscle}" for kw in keywords)
            print(f"    {i}. {name} | {muscle} ({p.score:.4f}) {'✅' if is_rel else '❌'}")
    
    # 汇总
    n = len(TEST_CASES)
    avg_top1 = total_top1 / n
    avg_top3 = total_top3 / n
    avg_rel = total_relevant / n
    composite = avg_top1 * 0.4 + avg_top3 * 0.3 + avg_rel * 0.3
    
    # 释放模型
    del model
    
    return {
        "model": model_key,
        "top1": avg_top1,
        "top3": avg_top3,
        "relevance": avg_rel,
        "composite": composite
    }


def main():
    # 连接Qdrant
    qdrant = QdrantClient(host="qdrant", port=6333)
    print("已连接Qdrant")
    
    # 检查集合
    info = qdrant.get_collection("fitness_exercises_v2")
    print(f"集合向量数: {info.points_count}")
    
    # 测试指定模型或全部
    if len(sys.argv) > 1:
        models_to_test = [sys.argv[1]]
    else:
        models_to_test = list(MODELS.keys())
    
    results = []
    for model_key in models_to_test:
        if model_key not in MODELS:
            print(f"未知模型: {model_key}")
            continue
        try:
            result = test_model(model_key, qdrant)
            results.append(result)
        except Exception as e:
            print(f"❌ {model_key} 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 打印汇总
    if len(results) > 1:
        print("\n" + "="*70)
        print("模型对比汇总")
        print("="*70)
        print(f"{'模型':<15} {'Top1':<10} {'Top3':<10} {'相关性':<12} {'综合分':<10}")
        print("-"*70)
        
        for r in sorted(results, key=lambda x: x["composite"], reverse=True):
            print(f"{r['model']:<15} {r['top1']:<10.4f} {r['top3']:<10.4f} {r['relevance']*100:<11.1f}% {r['composite']:<10.4f}")
        
        best = max(results, key=lambda x: x["composite"])
        print(f"\n🏆 推荐模型: {best['model']} (综合分: {best['composite']:.4f})")
    
    print("\n测试完成！")


if __name__ == "__main__":
    main()
