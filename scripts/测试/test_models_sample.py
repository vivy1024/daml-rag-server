#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型对比测试 - 使用采样数据

从1790个exercise中采样200个进行测试，减少编码时间
"""

import os
import sys
import json
import time
import random
import numpy as np

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer

# 测试查询
TEST_CASES = [
    {"query": "胸部训练 卧推", "keywords": ["卧推", "胸", "推", "飞鸟", "胸大肌"]},
    {"query": "背部拉力动作", "keywords": ["背", "拉力", "划船", "下拉", "引体", "背阔肌"]},
    {"query": "腿部复合动作", "keywords": ["腿", "深蹲", "蹲", "腿举", "股四头肌", "臀"]},
    {"query": "肱二头肌弯举", "keywords": ["弯举", "二头", "肱二头肌"]},
    {"query": "核心稳定性训练", "keywords": ["核心", "腹", "平板", "稳定"]},
    {"query": "肩部推举动作", "keywords": ["肩", "推举", "三角肌"]}
]

MODELS = {
    "bge-m3": "/root/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181",
    "bge-large": "BAAI/bge-large-zh-v1.5",
    "gte": "thenlper/gte-large-zh",
    "m3e": "moka-ai/m3e-large"
}


def build_search_text(ex):
    """构建搜索文本（简化版）"""
    parts = []
    
    name = ex.get('name_zh', '')
    if name:
        parts.extend([name] * 3)
    
    muscle = ex.get('primary_muscle_zh', '')
    if muscle:
        parts.extend([muscle] * 2)
    
    secondary = ex.get('muscles_secondary_zh', [])
    if isinstance(secondary, list):
        parts.extend([str(s) for s in secondary if s])
    elif secondary:
        parts.append(str(secondary))
    
    force = ex.get('force_zh', '')
    if force and isinstance(force, str):
        parts.append(force)
    
    mechanic = ex.get('mechanic_zh', '')
    if mechanic and isinstance(mechanic, str):
        parts.append(mechanic)
    
    equipment = ex.get('equipment_zh', '')
    if equipment:
        if isinstance(equipment, list):
            parts.extend([str(e) for e in equipment if e])
        else:
            parts.append(str(equipment))
    
    desc = ex.get('description_zh', '') or ''
    if desc and isinstance(desc, str):
        parts.append(desc[:200])
    
    return ' '.join(parts)


def test_model(model_key, exercises, search_texts, names):
    """测试单个模型"""
    model_path = MODELS[model_key]
    print(f"\n{'='*60}")
    print(f"测试模型: {model_key}")
    print(f"{'='*60}")
    
    # 加载模型（使用GPU）
    print("加载模型...")
    start = time.time()
    device = "cuda" if __import__('torch').cuda.is_available() else "cpu"
    model = SentenceTransformer(model_path, device=device)
    load_time = time.time() - start
    print(f"加载完成: {load_time:.2f}秒 (设备: {device})")
    
    # 编码文档
    print(f"编码 {len(search_texts)} 个文档...")
    start = time.time()
    doc_vecs = model.encode(search_texts, normalize_embeddings=True, show_progress_bar=True)
    encode_time = time.time() - start
    print(f"编码完成: {encode_time:.2f}秒")
    
    total_top1 = 0
    total_top3 = 0
    total_relevant = 0
    
    for tc in TEST_CASES:
        query = tc["query"]
        keywords = tc["keywords"]
        
        # 编码查询
        q_vec = model.encode([query], normalize_embeddings=True)[0]
        
        # 计算相似度
        scores = np.dot(doc_vecs, q_vec)
        indices = np.argsort(scores)[::-1][:5]
        
        top1 = scores[indices[0]]
        top3_avg = np.mean([scores[i] for i in indices[:3]])
        
        # 相关性
        relevant = 0
        for i in indices[:3]:
            if any(kw in (names[i] + " " + search_texts[i]) for kw in keywords):
                relevant += 1
        
        total_top1 += top1
        total_top3 += top3_avg
        total_relevant += relevant / 3
        
        print(f"\n查询: {query}")
        print(f"  Top1: {top1:.4f}, Top3: {top3_avg:.4f}, 相关: {relevant}/3")
        for rank, i in enumerate(indices[:3], 1):
            is_rel = any(kw in (names[i] + " " + search_texts[i]) for kw in keywords)
            print(f"    {rank}. {names[i]} ({scores[i]:.4f}) {'✅' if is_rel else '❌'}")
    
    n = len(TEST_CASES)
    result = {
        "model": model_key,
        "top1": total_top1 / n,
        "top3": total_top3 / n,
        "relevance": total_relevant / n,
        "load_time": load_time,
        "encode_time": encode_time
    }
    result["composite"] = result["top1"] * 0.4 + result["top3"] * 0.3 + result["relevance"] * 0.3
    
    del model
    return result


def main():
    # 加载数据
    print("加载数据...")
    with open('/app/data/enhanced_perfect_exercises_dataset.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    all_exercises = data.get('enhanced_perfect_exercises', [])
    print(f"总共 {len(all_exercises)} 个Exercise")
    
    # 采样200个（保证覆盖各类动作）
    sample_size = 200
    random.seed(42)  # 固定种子保证可重复
    exercises = random.sample(all_exercises, min(sample_size, len(all_exercises)))
    print(f"采样 {len(exercises)} 个用于测试")
    
    # 构建search_text
    search_texts = [build_search_text(ex) for ex in exercises]
    names = [ex.get('name_zh', '') for ex in exercises]
    
    # 测试模型
    models_to_test = sys.argv[1:] if len(sys.argv) > 1 else list(MODELS.keys())
    
    results = []
    for model_key in models_to_test:
        if model_key not in MODELS:
            print(f"未知模型: {model_key}")
            continue
        try:
            result = test_model(model_key, exercises, search_texts, names)
            results.append(result)
        except Exception as e:
            print(f"❌ {model_key} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 汇总
    if results:
        print("\n" + "="*80)
        print("模型对比汇总（基于200个采样）")
        print("="*80)
        print(f"{'模型':<12} {'Top1':<10} {'Top3':<10} {'相关性':<10} {'综合分':<10} {'编码时间':<10}")
        print("-"*80)
        
        for r in sorted(results, key=lambda x: x["composite"], reverse=True):
            print(f"{r['model']:<12} {r['top1']:<10.4f} {r['top3']:<10.4f} {r['relevance']*100:<9.1f}% {r['composite']:<10.4f} {r['encode_time']:<9.1f}s")
        
        best = max(results, key=lambda x: x["composite"])
        print(f"\n🏆 推荐: {best['model']} (综合分: {best['composite']:.4f})")


if __name__ == "__main__":
    main()
