#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单模型测试脚本 - 快速测试指定模型

用法: python test_single_model.py [model_name]
model_name: bge-m3, bge-large, gte, m3e
"""

import os
import sys
import json
import time
import numpy as np
from typing import List, Dict, Tuple, Any

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer

# 测试查询
TEST_CASES = [
    {"query": "胸部训练 卧推", "keywords": ["卧推", "胸", "推", "飞鸟", "胸大肌"]},
    {"query": "背部拉力动作", "keywords": ["背", "拉力", "划船", "下拉", "引体"]},
    {"query": "腿部复合动作", "keywords": ["腿", "深蹲", "蹲", "腿举", "股四头肌"]},
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


def build_search_text(exercise: Dict[str, Any]) -> str:
    """构建搜索文本"""
    parts = []
    
    name_zh = exercise.get('name_zh', '')
    if name_zh:
        parts.extend([name_zh] * 3)
    
    name_en = exercise.get('name_en', '')
    if name_en:
        parts.append(name_en)
    
    primary_muscle = exercise.get('primary_muscle_zh', '')
    if primary_muscle:
        parts.extend([primary_muscle] * 2)
    
    muscles_primary = exercise.get('muscles_primary_zh', [])
    if isinstance(muscles_primary, list):
        parts.extend(muscles_primary)
    
    secondary_muscles = exercise.get('muscles_secondary_zh', [])
    if isinstance(secondary_muscles, list) and secondary_muscles:
        parts.extend(secondary_muscles)
    
    all_muscles = exercise.get('all_muscles_zh', [])
    if isinstance(all_muscles, list):
        parts.extend(all_muscles)
    
    force_zh = exercise.get('force_zh', '')
    if force_zh:
        parts.append(force_zh)
    
    mechanic_zh = exercise.get('mechanic_zh', '')
    if mechanic_zh:
        parts.append(mechanic_zh)
    
    equipment = exercise.get('equipment_zh', '')
    if equipment:
        parts.append(equipment)
    
    difficulty = exercise.get('difficulty_zh', '') or exercise.get('difficulty', '')
    if difficulty:
        parts.append(difficulty)
    
    desc = exercise.get('description_zh', '') or ''
    if desc:
        parts.append(desc[:300])
    
    return ' '.join(parts)


def main():
    model_key = sys.argv[1] if len(sys.argv) > 1 else "bge-m3"
    
    if model_key not in MODELS:
        print(f"未知模型: {model_key}")
        print(f"可用模型: {list(MODELS.keys())}")
        return
    
    model_path = MODELS[model_key]
    print(f"\n测试模型: {model_key}")
    print(f"模型路径: {model_path}")
    
    # 加载数据
    print("\n加载数据...")
    with open('/app/data/enhanced_perfect_exercises_dataset.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    exercises = data.get('enhanced_perfect_exercises', [])
    print(f"加载了 {len(exercises)} 个Exercise")
    
    # 构建search_text
    search_texts = [build_search_text(ex) for ex in exercises]
    exercise_names = [ex.get('name_zh', '') for ex in exercises]
    
    # 加载模型
    print(f"\n加载模型...")
    start = time.time()
    model = SentenceTransformer(model_path)
    print(f"模型加载完成，耗时: {time.time()-start:.2f}秒")
    
    # 编码所有文档
    print("\n编码文档...")
    start = time.time()
    doc_embeddings = model.encode(search_texts, normalize_embeddings=True, show_progress_bar=True)
    print(f"编码完成，耗时: {time.time()-start:.2f}秒")
    
    # 测试查询
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    
    total_top1 = 0
    total_top3 = 0
    total_relevant = 0
    
    for tc in TEST_CASES:
        query = tc["query"]
        keywords = tc["keywords"]
        
        # 编码查询
        query_vec = model.encode([query], normalize_embeddings=True)[0]
        
        # 计算相似度
        scores = np.dot(doc_embeddings, query_vec)
        
        # 排序
        indices = np.argsort(scores)[::-1][:5]
        
        top1_score = scores[indices[0]]
        top3_scores = [scores[i] for i in indices[:3]]
        top3_avg = sum(top3_scores) / 3
        
        # 检查相关性
        relevant = 0
        for i in indices[:3]:
            name = exercise_names[i]
            text = search_texts[i]
            if any(kw in (name + " " + text) for kw in keywords):
                relevant += 1
        
        relevance = relevant / 3
        
        total_top1 += top1_score
        total_top3 += top3_avg
        total_relevant += relevance
        
        print(f"\n查询: {query}")
        print(f"  Top1: {top1_score:.4f}, Top3平均: {top3_avg:.4f}, 相关性: {relevant}/3")
        print(f"  Top5结果:")
        for rank, i in enumerate(indices, 1):
            name = exercise_names[i]
            score = scores[i]
            is_rel = any(kw in (name + " " + search_texts[i]) for kw in keywords)
            print(f"    {rank}. {name} ({score:.4f}) {'✅' if is_rel else '❌'}")
    
    # 汇总
    n = len(TEST_CASES)
    avg_top1 = total_top1 / n
    avg_top3 = total_top3 / n
    avg_rel = total_relevant / n
    composite = avg_top1 * 0.4 + avg_top3 * 0.3 + avg_rel * 0.3
    
    print("\n" + "="*60)
    print(f"模型: {model_key}")
    print(f"  平均Top1分数: {avg_top1:.4f}")
    print(f"  平均Top3分数: {avg_top3:.4f}")
    print(f"  相关性准确率: {avg_rel*100:.1f}%")
    print(f"  综合分: {composite:.4f}")
    print("="*60)


if __name__ == "__main__":
    main()
