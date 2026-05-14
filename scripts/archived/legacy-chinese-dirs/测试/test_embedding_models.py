#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量模型对比测试脚本

测试不同向量模型在健身领域的语义理解能力
对比模型：
1. BGE-M3 (当前使用，568M参数，1024维)
2. BGE-Large-zh-v1.5 (326M参数，1024维)
3. GTE-Large-zh (阿里达摩院，326M参数，1024维)
4. M3E-Large (Moka开源，326M参数，1024维)

版本: v1.0.0
日期: 2026-01-06
"""

import time
import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer

# 测试查询和期望的相关动作
TEST_CASES = [
    {
        "query": "胸部训练 卧推",
        "expected_keywords": ["卧推", "胸", "推举", "飞鸟"],
        "category": "胸部"
    },
    {
        "query": "背部训练 引体向上",
        "expected_keywords": ["引体", "背", "划船", "下拉"],
        "category": "背部"
    },
    {
        "query": "腿部训练 深蹲",
        "expected_keywords": ["深蹲", "腿", "蹲", "腿举"],
        "category": "腿部"
    },
    {
        "query": "肩部训练 推举",
        "expected_keywords": ["肩", "推举", "三角肌", "侧平举"],
        "category": "肩部"
    },
    {
        "query": "核心训练 平板支撑",
        "expected_keywords": ["核心", "腹", "平板", "卷腹"],
        "category": "核心"
    },
    {
        "query": "手臂训练 弯举",
        "expected_keywords": ["弯举", "二头", "臂", "三头"],
        "category": "手臂"
    }
]

# 健身动作样本（用于计算相似度）
EXERCISE_SAMPLES = [
    # 胸部
    "杠铃卧推 胸大肌 复合动作 推力",
    "哑铃飞鸟 胸大肌 孤立动作 推力",
    "上斜卧推 上胸 复合动作 推力",
    "俯卧撑 胸大肌 自重训练 推力",
    # 背部
    "引体向上 背阔肌 复合动作 拉力",
    "杠铃划船 背阔肌 复合动作 拉力",
    "高位下拉 背阔肌 复合动作 拉力",
    "坐姿划船 背阔肌 复合动作 拉力",
    # 腿部
    "杠铃深蹲 股四头肌 复合动作 推力",
    "腿举 股四头肌 复合动作 推力",
    "罗马尼亚硬拉 腘绳肌 复合动作 拉力",
    "弓步蹲 股四头肌 复合动作 推力",
    # 肩部
    "杠铃推举 三角肌 复合动作 推力",
    "哑铃侧平举 三角肌中束 孤立动作 推力",
    "哑铃前平举 三角肌前束 孤立动作 推力",
    "面拉 三角肌后束 孤立动作 拉力",
    # 核心
    "平板支撑 核心肌群 静态保持",
    "卷腹 腹直肌 孤立动作",
    "俄罗斯转体 腹斜肌 旋转动作",
    "悬垂举腿 腹直肌 复合动作",
    # 手臂
    "杠铃弯举 肱二头肌 孤立动作 拉力",
    "三头肌下压 肱三头肌 孤立动作 推力",
    "锤式弯举 肱二头肌 孤立动作 拉力",
    "窄距卧推 肱三头肌 复合动作 推力"
]

# 候选模型列表
CANDIDATE_MODELS = [
    {
        "name": "BGE-M3",
        "model_id": "BAAI/bge-m3",
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


def load_model(model_id: str) -> SentenceTransformer:
    """加载向量模型"""
    print(f"  加载模型: {model_id}...")
    start_time = time.time()
    model = SentenceTransformer(model_id)
    load_time = time.time() - start_time
    print(f"  加载完成，耗时: {load_time:.2f}秒")
    return model


def compute_similarity(model: SentenceTransformer, query: str, documents: List[str]) -> List[Tuple[str, float]]:
    """计算查询与文档的相似度"""
    # 编码查询和文档
    query_embedding = model.encode([query], normalize_embeddings=True)[0]
    doc_embeddings = model.encode(documents, normalize_embeddings=True)
    
    # 计算余弦相似度
    similarities = np.dot(doc_embeddings, query_embedding)
    
    # 排序返回
    results = list(zip(documents, similarities))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def evaluate_model(model: SentenceTransformer, model_name: str) -> Dict:
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
        similarities = compute_similarity(model, query, EXERCISE_SAMPLES)
        
        # 获取Top3结果
        top3 = similarities[:3]
        top1_score = top3[0][1]
        top3_avg_score = sum(score for _, score in top3) / 3
        
        # 检查相关性
        relevant_count = 0
        for doc, score in top3:
            if any(kw in doc for kw in expected_keywords):
                relevant_count += 1
        
        relevance_rate = relevant_count / 3
        
        # 记录结果
        case_result = {
            "query": query,
            "category": category,
            "top1_score": float(top1_score),
            "top3_avg_score": float(top3_avg_score),
            "relevance_rate": relevance_rate,
            "top3_results": [(doc, float(score)) for doc, score in top3]
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
        print(f"  Top3结果:")
        for i, (doc, score) in enumerate(top3, 1):
            is_relevant = any(kw in doc for kw in expected_keywords)
            print(f"    {i}. {doc[:30]}... ({score:.4f}) {'✅' if is_relevant else '❌'}")
    
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
    print("向量模型对比测试 - 健身领域")
    print("="*60)
    print(f"测试用例数: {len(TEST_CASES)}")
    print(f"动作样本数: {len(EXERCISE_SAMPLES)}")
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
            results = evaluate_model(model, model_name)
            results["model_info"] = model_info
            all_results.append(results)
            
            # 释放内存
            del model
            
        except Exception as e:
            print(f"❌ 模型 {model_name} 测试失败: {e}")
            all_results.append({
                "model_name": model_name,
                "model_info": model_info,
                "error": str(e)
            })
    
    # 打印对比结果
    print("\n" + "="*60)
    print("模型对比结果汇总")
    print("="*60)
    print(f"{'模型名称':<20} {'Top1分数':<12} {'Top3分数':<12} {'相关性':<12} {'状态':<10}")
    print("-"*60)
    
    for result in all_results:
        model_name = result["model_name"]
        if "error" in result:
            print(f"{model_name:<20} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'❌ 失败':<10}")
        else:
            top1 = result["avg_top1_score"]
            top3 = result["avg_top3_score"]
            relevance = result["relevance_accuracy"]
            status = "✅ 推荐" if top1 > 0.75 and relevance > 0.8 else "⚠️ 一般"
            print(f"{model_name:<20} {top1:<12.4f} {top3:<12.4f} {relevance*100:<11.1f}% {status:<10}")
    
    # 找出最佳模型
    valid_results = [r for r in all_results if "error" not in r]
    if valid_results:
        best_by_score = max(valid_results, key=lambda x: x["avg_top1_score"])
        best_by_relevance = max(valid_results, key=lambda x: x["relevance_accuracy"])
        
        print(f"\n最佳Top1分数: {best_by_score['model_name']} ({best_by_score['avg_top1_score']:.4f})")
        print(f"最佳相关性: {best_by_relevance['model_name']} ({best_by_relevance['relevance_accuracy']*100:.1f}%)")
        
        # 综合评分
        print("\n综合推荐:")
        for result in valid_results:
            score = result["avg_top1_score"] * 0.4 + result["avg_top3_score"] * 0.3 + result["relevance_accuracy"] * 0.3
            print(f"  {result['model_name']}: 综合分 {score:.4f}")
    
    print("\n测试完成！")
    return all_results


if __name__ == "__main__":
    main()
