#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量模型对比测试脚本 v2.0

基于Qdrant中增强后的search_text数据测试不同向量模型
对比模型：
1. BGE-M3 (当前使用，568M参数，1024维)
2. BGE-Large-zh-v1.5 (326M参数，1024维)
3. GTE-Large-zh (阿里达摩院，326M参数，1024维)
4. M3E-Large (Moka开源，326M参数，1024维)

版本: v2.0.0
日期: 2026-01-06
"""

import os
import json
import time
import numpy as np
from typing import List, Dict, Tuple, Any

# 设置离线模式，避免HuggingFace限流
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer

# 测试查询和期望的相关动作
TEST_CASES = [
    {
        "query": "胸部训练 卧推",
        "expected_keywords": ["卧推", "胸", "推举", "飞鸟", "胸大肌"],
        "category": "胸部"
    },
    {
        "query": "背部拉力动作",
        "expected_keywords": ["背", "拉力", "划船", "下拉", "引体", "背阔肌"],
        "category": "背部"
    },
    {
        "query": "腿部复合动作",
        "expected_keywords": ["腿", "深蹲", "蹲", "腿举", "股四头肌", "臀"],
        "category": "腿部"
    },
    {
        "query": "肱二头肌弯举",
        "expected_keywords": ["弯举", "二头", "肱二头肌", "臂"],
        "category": "手臂"
    },
    {
        "query": "核心稳定性训练",
        "expected_keywords": ["核心", "腹", "平板", "稳定", "支撑"],
        "category": "核心"
    },
    {
        "query": "肩部推举动作",
        "expected_keywords": ["肩", "推举", "三角肌", "侧平举", "前平举"],
        "category": "肩部"
    }
]

# 候选模型列表
CANDIDATE_MODELS = [
    {
        "name": "BGE-M3",
        "model_id": "/root/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181",
        "params": "568M",
        "dim": 1024,
        "description": "当前使用的模型，多语言支持"
    },
    {
        "name": "BGE-Large-zh-v1.5",
        "model_id": "BAAI/bge-large-zh-v1.5",
        "params": "326M",
        "dim": 1024,
        "description": "中文优化版本"
    },
    {
        "name": "GTE-Large-zh",
        "model_id": "thenlper/gte-large-zh",
        "params": "326M",
        "dim": 1024,
        "description": "阿里达摩院，中文语义强"
    },
    {
        "name": "M3E-Large",
        "model_id": "moka-ai/m3e-large",
        "params": "326M",
        "dim": 1024,
        "description": "Moka开源，中文优化"
    }
]


def load_exercise_data() -> List[Dict[str, Any]]:
    """从JSON文件加载exercise数据"""
    data_file = "/app/data/enhanced_perfect_exercises_dataset.json"
    print(f"加载数据文件: {data_file}")
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    exercises = data.get('enhanced_perfect_exercises', [])
    print(f"加载了 {len(exercises)} 个Exercise")
    return exercises


def build_search_text(exercise: Dict[str, Any]) -> str:
    """构建搜索文本（与import脚本一致）"""
    parts = []
    
    # 1. 名称（中英文）- 权重最高，重复3次
    name_zh = exercise.get('name_zh', '')
    name_en = exercise.get('name_en', '')
    if name_zh:
        parts.extend([name_zh] * 3)
    if name_en:
        parts.append(name_en)
    
    # 2. 主要肌群 - 权重高，重复2次
    primary_muscle = exercise.get('primary_muscle_zh', '')
    if primary_muscle:
        parts.extend([primary_muscle] * 2)
    
    # 3. 所有主要肌群
    muscles_primary = exercise.get('muscles_primary_zh', [])
    if isinstance(muscles_primary, list):
        parts.extend(muscles_primary)
    
    # 4. 次要肌群
    secondary_muscles = exercise.get('muscles_secondary_zh', [])
    if isinstance(secondary_muscles, list) and secondary_muscles:
        parts.extend(secondary_muscles)
    
    # 5. 所有相关肌群
    all_muscles = exercise.get('all_muscles_zh', [])
    if isinstance(all_muscles, list):
        parts.extend(all_muscles)
    
    # 6. 力类型
    force_zh = exercise.get('force_zh', '')
    if force_zh:
        parts.append(force_zh)
    
    # 7. 动作类型
    mechanic_zh = exercise.get('mechanic_zh', '')
    if mechanic_zh:
        parts.append(mechanic_zh)
    
    # 8. 动力链
    kinetic_chain = exercise.get('kinetic_chain_type', '')
    if kinetic_chain:
        kinetic_chain_map = {
            'open_chain': '开链动作',
            'closed_chain': '闭链动作',
            'mixed': '混合动作'
        }
        parts.append(kinetic_chain_map.get(kinetic_chain, kinetic_chain))
    
    # 9. 握法
    grips = exercise.get('grips_zh', [])
    if isinstance(grips, list):
        parts.extend(grips)
    elif grips:
        parts.append(grips)
    
    # 10. 器械
    equipment = exercise.get('equipment_zh', '')
    if equipment:
        parts.append(equipment)
    
    # 11. 难度
    difficulty = exercise.get('difficulty_zh', '') or exercise.get('difficulty', '')
    if difficulty:
        parts.append(difficulty)
    
    # 12. 训练参数
    rep_range = exercise.get('rep_range', '')
    if rep_range:
        parts.append(f"次数范围{rep_range}次")
    
    set_range = exercise.get('set_range', '')
    if set_range:
        parts.append(f"组数{set_range}组")
    
    # 13. 描述
    desc = exercise.get('description_zh', '') or ''
    if desc:
        parts.append(desc[:500])
    
    # 14. 正确步骤
    steps = exercise.get('correct_steps_zh', []) or []
    if isinstance(steps, list) and steps:
        steps_text = ' '.join(str(s) for s in steps)[:300]
        parts.append(steps_text)
    
    # 15. 安全等级
    safety_level = exercise.get('safety_level', '')
    if safety_level:
        safety_map = {
            'LOW_RISK': '低风险',
            'MODERATE_RISK': '中等风险',
            'HIGH_RISK': '高风险'
        }
        parts.append(safety_map.get(safety_level, safety_level))
    
    return ' '.join(parts)


def load_model(model_id: str) -> SentenceTransformer:
    """加载向量模型"""
    print(f"  加载模型: {model_id}...")
    start_time = time.time()
    model = SentenceTransformer(model_id)
    load_time = time.time() - start_time
    print(f"  加载完成，耗时: {load_time:.2f}秒")
    return model


def compute_similarity(model: SentenceTransformer, query: str, 
                       documents: List[str], exercise_names: List[str]) -> List[Tuple[str, str, float]]:
    """计算查询与文档的相似度"""
    # 编码查询和文档
    query_embedding = model.encode([query], normalize_embeddings=True)[0]
    doc_embeddings = model.encode(documents, normalize_embeddings=True)
    
    # 计算余弦相似度
    similarities = np.dot(doc_embeddings, query_embedding)
    
    # 排序返回 (name, search_text, score)
    results = list(zip(exercise_names, documents, similarities))
    results.sort(key=lambda x: x[2], reverse=True)
    return results


def evaluate_model(model: SentenceTransformer, model_name: str, 
                   exercises: List[Dict], search_texts: List[str], 
                   exercise_names: List[str]) -> Dict:
    """评估模型在健身领域的表现"""
    print(f"\n{'='*60}")
    print(f"评估模型: {model_name}")
    print(f"{'='*60}")
    
    results = {
        "model_name": model_name,
        "test_cases": [],
        "avg_top1_score": 0,
        "avg_top3_score": 0,
        "relevance_accuracy": 0
    }
    
    total_top1_score = 0
    total_top3_score = 0
    total_relevant = 0
    
    for test_case in TEST_CASES:
        query = test_case["query"]
        expected_keywords = test_case["expected_keywords"]
        category = test_case["category"]
        
        # 计算相似度
        similarities = compute_similarity(model, query, search_texts, exercise_names)
        
        # 获取Top5结果
        top5 = similarities[:5]
        top1_score = top5[0][2]
        top3 = top5[:3]
        top3_avg_score = sum(score for _, _, score in top3) / 3
        
        # 检查相关性（基于名称和search_text）
        relevant_count = 0
        for name, text, score in top3:
            combined = name + " " + text
            if any(kw in combined for kw in expected_keywords):
                relevant_count += 1
        
        relevance_rate = relevant_count / 3
        
        # 记录结果
        case_result = {
            "query": query,
            "category": category,
            "top1_score": float(top1_score),
            "top3_avg_score": float(top3_avg_score),
            "relevance_rate": relevance_rate,
            "top5_results": [(name, float(score)) for name, _, score in top5]
        }
        results["test_cases"].append(case_result)
        
        total_top1_score += top1_score
        total_top3_score += top3_avg_score
        total_relevant += relevance_rate
        
        # 打印结果
        print(f"\n查询: {query}")
        print(f"  Top1分数: {top1_score:.4f}")
        print(f"  Top3平均: {top3_avg_score:.4f}")
        print(f"  相关性: {relevant_count}/3 ({relevance_rate*100:.0f}%)")
        print(f"  Top5结果:")
        for i, (name, text, score) in enumerate(top5, 1):
            is_relevant = any(kw in (name + " " + text) for kw in expected_keywords)
            print(f"    {i}. {name} ({score:.4f}) {'✅' if is_relevant else '❌'}")
    
    # 计算平均值
    num_cases = len(TEST_CASES)
    results["avg_top1_score"] = total_top1_score / num_cases
    results["avg_top3_score"] = total_top3_score / num_cases
    results["relevance_accuracy"] = total_relevant / num_cases
    
    print(f"\n{'='*60}")
    print(f"模型总结: {model_name}")
    print(f"  平均Top1分数: {results['avg_top1_score']:.4f}")
    print(f"  平均Top3分数: {results['avg_top3_score']:.4f}")
    print(f"  相关性准确率: {results['relevance_accuracy']*100:.1f}%")
    print(f"{'='*60}")
    
    return results


def main():
    """主函数"""
    print("\n" + "="*60)
    print("向量模型对比测试 v2.0 - 基于增强search_text")
    print("="*60)
    
    # 加载exercise数据
    exercises = load_exercise_data()
    
    # 构建search_text列表
    print("构建search_text...")
    search_texts = []
    exercise_names = []
    for ex in exercises:
        search_texts.append(build_search_text(ex))
        exercise_names.append(ex.get('name_zh', ''))
    
    print(f"测试用例数: {len(TEST_CASES)}")
    print(f"动作样本数: {len(search_texts)}")
    print(f"候选模型数: {len(CANDIDATE_MODELS)}")
    
    all_results = []
    
    for model_info in CANDIDATE_MODELS:
        model_name = model_info["name"]
        model_id = model_info["model_id"]
        
        print(f"\n{'#'*60}")
        print(f"# 测试模型: {model_name}")
        print(f"# 模型ID: {model_id}")
        print(f"# 参数量: {model_info['params']}")
        print(f"# 维度: {model_info['dim']}")
        print(f"# 描述: {model_info['description']}")
        print(f"{'#'*60}")
        
        try:
            # 加载模型
            model = load_model(model_id)
            
            # 评估模型
            results = evaluate_model(model, model_name, exercises, search_texts, exercise_names)
            results["model_info"] = model_info
            all_results.append(results)
            
            # 释放内存
            del model
            
        except Exception as e:
            print(f"❌ 模型 {model_name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            all_results.append({
                "model_name": model_name,
                "model_info": model_info,
                "error": str(e)
            })
    
    # 打印对比结果
    print("\n" + "="*60)
    print("模型对比结果汇总")
    print("="*60)
    print(f"{'模型名称':<20} {'Top1分数':<12} {'Top3分数':<12} {'相关性':<12} {'综合分':<12}")
    print("-"*68)
    
    for result in all_results:
        model_name = result["model_name"]
        if "error" in result:
            print(f"{model_name:<20} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'❌ 失败':<12}")
        else:
            top1 = result["avg_top1_score"]
            top3 = result["avg_top3_score"]
            relevance = result["relevance_accuracy"]
            # 综合分 = Top1*0.4 + Top3*0.3 + 相关性*0.3
            composite = top1 * 0.4 + top3 * 0.3 + relevance * 0.3
            print(f"{model_name:<20} {top1:<12.4f} {top3:<12.4f} {relevance*100:<11.1f}% {composite:<12.4f}")
    
    # 找出最佳模型
    valid_results = [r for r in all_results if "error" not in r]
    if valid_results:
        # 计算综合分
        for r in valid_results:
            r["composite_score"] = r["avg_top1_score"] * 0.4 + r["avg_top3_score"] * 0.3 + r["relevance_accuracy"] * 0.3
        
        best_composite = max(valid_results, key=lambda x: x["composite_score"])
        best_by_score = max(valid_results, key=lambda x: x["avg_top1_score"])
        best_by_relevance = max(valid_results, key=lambda x: x["relevance_accuracy"])
        
        print(f"\n🏆 最佳综合分: {best_composite['model_name']} ({best_composite['composite_score']:.4f})")
        print(f"📊 最佳Top1分数: {best_by_score['model_name']} ({best_by_score['avg_top1_score']:.4f})")
        print(f"🎯 最佳相关性: {best_by_relevance['model_name']} ({best_by_relevance['relevance_accuracy']*100:.1f}%)")
        
        print("\n📋 综合排名:")
        sorted_results = sorted(valid_results, key=lambda x: x["composite_score"], reverse=True)
        for i, result in enumerate(sorted_results, 1):
            status = "⭐ 推荐" if i == 1 else ("✅ 良好" if result["composite_score"] > 0.7 else "⚠️ 一般")
            print(f"  {i}. {result['model_name']}: 综合分 {result['composite_score']:.4f} {status}")
    
    print("\n测试完成！")
    return all_results


if __name__ == "__main__":
    main()
