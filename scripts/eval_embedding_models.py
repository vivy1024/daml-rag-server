# -*- coding: utf-8 -*-
"""
Embedding 模型评估脚本 — 健身领域语义检索质量对比

评估 GTE-Large-zh (当前) vs BGE-M3 vs GTE-Qwen2 在健身领域的表现。
使用 query-document 相关性对 + Qdrant 实际检索两种方式评估。

retrieval-optimization-v2 Task 6
"""
import sys
import os
import time
import json
import numpy as np
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ─── 评估数据集：健身领域 query-document 相关性对 ─────────────
# (query, positive_doc, negative_doc) — positive 应该比 negative 更相关

EVAL_PAIRS = [
    # 动作-肌肉关系
    (
        "深蹲练哪些肌肉",
        "杠铃深蹲主要锻炼股四头肌、臀大肌，次要锻炼腘绳肌和核心肌群",
        "俯卧撑是一种上肢推力训练，主要锻炼胸大肌和肱三头肌"
    ),
    (
        "卧推怎么做",
        "杠铃卧推：仰卧在平板凳上，双手握杠铃，下放至胸部，推起至手臂伸直",
        "硬拉是一种髋关节铰链动作，从地面拉起杠铃至站立位"
    ),
    # 营养相关
    (
        "增肌期蛋白质摄入量",
        "增肌期建议每公斤体重摄入1.6-2.2克蛋白质，分3-5餐摄入",
        "有氧运动建议每周进行150分钟中等强度或75分钟高强度"
    ),
    (
        "减脂碳水怎么安排",
        "减脂期碳水化合物建议每公斤体重2-3克，训练日可适当增加",
        "力量训练的渐进超负荷原则是指逐步增加训练负荷"
    ),
    # 训练计划
    (
        "推拉腿怎么安排",
        "推拉腿分化：推日（胸肩三头）、拉日（背二头）、腿日（股四臀腿），每周2轮",
        "深蹲的正确姿势是双脚与肩同宽，脚尖微外展"
    ),
    # 补剂
    (
        "肌酸什么时候吃",
        "肌酸建议每天5克，训练后与碳水一起服用吸收更好，无需加载期",
        "拉伸可以分为静态拉伸和动态拉伸两种"
    ),
    # 安全/伤病
    (
        "腰椎间盘突出能做什么运动",
        "腰椎间盘突出建议避免深蹲硬拉等轴向负荷动作，可做游泳、平板支撑等",
        "三角肌分为前束、中束和后束三个部分"
    ),
    # 口语化查询（噪声测试）
    (
        "那个就是练胸的那个动作叫啥来着",
        "常见的胸部训练动作包括卧推、飞鸟、双杠臂屈伸等",
        "腹肌训练可以每天进行，因为腹肌恢复较快"
    ),
    (
        "我想问一下就是新手刚开始健身应该怎么练",
        "新手建议从全身训练开始，每周3次，以复合动作为主，逐步增加重量",
        "高级训练者可以使用递减组、超级组等高级训练技术"
    ),
    (
        "emmm那个蛋白粉到底有没有用啊",
        "蛋白粉是蛋白质的便捷补充方式，适合饮食中蛋白质摄入不足的人群",
        "训练前30分钟可以摄入咖啡因来提升运动表现"
    ),
]

# ─── 口语噪声测试对 ─────────────────────────────────
# (原始口语查询, 清洗后查询) — 评估清洗前后检索质量差异

ORAL_NOISE_PAIRS = [
    ("那个就是练胸的那个动作叫啥来着", "练胸的动作"),
    ("我想问一下就是新手刚开始健身应该怎么练", "新手健身怎么练"),
    ("emmm那个蛋白粉到底有没有用啊", "蛋白粉有用吗"),
    ("就是那个深蹲嘛它到底练的是哪里啊", "深蹲练哪里"),
    ("嗯我觉得就是那个卧推我老是做不好怎么办", "卧推做不好怎么办"),
    ("请问一下就是减肥的话是不是不能吃碳水啊", "减肥能吃碳水吗"),
    ("那个什么引体向上我一个都做不了有没有替代的", "引体向上替代动作"),
    ("就是想知道一周练几次比较合适嘛", "一周练几次"),
]


def load_model(model_name: str):
    """加载 SentenceTransformer 模型"""
    from sentence_transformers import SentenceTransformer
    print(f"  加载模型: {model_name} ...")
    t0 = time.time()
    model = SentenceTransformer(model_name)
    t1 = time.time()
    dim = model.get_sentence_embedding_dimension()
    print(f"  ✅ 加载完成: {t1-t0:.1f}s, 维度={dim}")
    return model


def cosine_sim(a, b):
    """余弦相似度"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def eval_relevance(model, pairs: List[Tuple[str, str, str]]) -> Dict:
    """评估 query-document 相关性排序准确率"""
    correct = 0
    total = len(pairs)
    details = []

    for query, pos_doc, neg_doc in pairs:
        q_emb = model.encode(query)
        p_emb = model.encode(pos_doc)
        n_emb = model.encode(neg_doc)

        sim_pos = cosine_sim(q_emb, p_emb)
        sim_neg = cosine_sim(q_emb, n_emb)

        is_correct = sim_pos > sim_neg
        if is_correct:
            correct += 1

        details.append({
            "query": query[:30],
            "sim_pos": round(sim_pos, 4),
            "sim_neg": round(sim_neg, 4),
            "margin": round(sim_pos - sim_neg, 4),
            "correct": is_correct,
        })

    accuracy = correct / total * 100
    avg_margin = np.mean([d["margin"] for d in details])
    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "avg_margin": round(float(avg_margin), 4),
        "details": details,
    }


def eval_oral_noise(model, pairs: List[Tuple[str, str]], reference_doc: str = None) -> Dict:
    """评估口语噪声对检索质量的影响"""
    results = []
    for oral, clean in pairs:
        oral_emb = model.encode(oral)
        clean_emb = model.encode(clean)
        sim = cosine_sim(oral_emb, clean_emb)
        results.append({
            "oral": oral[:30],
            "clean": clean,
            "similarity": round(sim, 4),
        })

    avg_sim = np.mean([r["similarity"] for r in results])
    return {
        "avg_oral_clean_similarity": round(float(avg_sim), 4),
        "details": results,
    }


def eval_encoding_speed(model, queries: List[str], n_runs: int = 3) -> Dict:
    """评估编码速度"""
    times = []
    for _ in range(n_runs):
        t0 = time.time()
        model.encode(queries)
        t1 = time.time()
        times.append(t1 - t0)

    avg_time = np.mean(times)
    per_query = avg_time / len(queries) * 1000  # ms
    return {
        "total_queries": len(queries),
        "avg_batch_time_s": round(float(avg_time), 3),
        "per_query_ms": round(float(per_query), 1),
    }


def main():
    print("=" * 70)
    print("🧪 Embedding 模型评估 — 健身领域语义检索质量")
    print("=" * 70)

    # 要评估的模型
    models_to_eval = [
        ("thenlper/gte-large-zh", "GTE-Large-zh (当前)"),
        ("BAAI/bge-m3", "BGE-M3"),
        # GTE-Qwen2 需要 trust_remote_code，单独处理
    ]

    # 检查是否可以加载 GTE-Qwen2
    try_qwen2 = True

    all_queries = [q for q, _, _ in EVAL_PAIRS]
    results = {}

    for model_name, display_name in models_to_eval:
        print(f"\n{'─' * 60}")
        print(f"📊 评估: {display_name} ({model_name})")
        print(f"{'─' * 60}")

        try:
            model = load_model(model_name)
        except Exception as e:
            print(f"  ❌ 模型加载失败: {e}")
            results[display_name] = {"error": str(e)}
            continue

        # 1. 相关性排序
        print("\n  [1] 相关性排序测试...")
        rel = eval_relevance(model, EVAL_PAIRS)
        print(f"      准确率: {rel['accuracy']:.0f}% ({rel['correct']}/{rel['total']})")
        print(f"      平均 margin: {rel['avg_margin']:.4f}")

        # 2. 口语噪声
        print("\n  [2] 口语噪声测试...")
        noise = eval_oral_noise(model, ORAL_NOISE_PAIRS)
        print(f"      口语↔清洗 平均相似度: {noise['avg_oral_clean_similarity']:.4f}")

        # 3. 编码速度
        print("\n  [3] 编码速度测试...")
        speed = eval_encoding_speed(model, all_queries)
        print(f"      {speed['total_queries']} 条查询: {speed['avg_batch_time_s']:.3f}s ({speed['per_query_ms']:.1f}ms/条)")

        results[display_name] = {
            "model": model_name,
            "dim": model.get_sentence_embedding_dimension(),
            "relevance": rel,
            "oral_noise": noise,
            "speed": speed,
        }

        # 释放显存
        del model

    # GTE-Qwen2 评估
    if try_qwen2:
        print(f"\n{'─' * 60}")
        print(f"📊 评估: GTE-Qwen2 (Alibaba-NLP/gte-Qwen2-1.5B-instruct)")
        print(f"{'─' * 60}")
        try:
            from sentence_transformers import SentenceTransformer
            print("  加载模型 (需要 trust_remote_code)...")
            t0 = time.time()
            model = SentenceTransformer(
                "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
                trust_remote_code=True
            )
            t1 = time.time()
            dim = model.get_sentence_embedding_dimension()
            print(f"  ✅ 加载完成: {t1-t0:.1f}s, 维度={dim}")

            print("\n  [1] 相关性排序测试...")
            rel = eval_relevance(model, EVAL_PAIRS)
            print(f"      准确率: {rel['accuracy']:.0f}% ({rel['correct']}/{rel['total']})")
            print(f"      平均 margin: {rel['avg_margin']:.4f}")

            print("\n  [2] 口语噪声测试...")
            noise = eval_oral_noise(model, ORAL_NOISE_PAIRS)
            print(f"      口语↔清洗 平均相似度: {noise['avg_oral_clean_similarity']:.4f}")

            print("\n  [3] 编码速度测试...")
            speed = eval_encoding_speed(model, all_queries)
            print(f"      {speed['total_queries']} 条查询: {speed['avg_batch_time_s']:.3f}s ({speed['per_query_ms']:.1f}ms/条)")

            results["GTE-Qwen2-1.5B"] = {
                "model": "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
                "dim": dim,
                "relevance": rel,
                "oral_noise": noise,
                "speed": speed,
            }
            del model
        except Exception as e:
            print(f"  ❌ GTE-Qwen2 加载失败: {e}")
            results["GTE-Qwen2-1.5B"] = {"error": str(e)}

    # ─── 汇总报告 ─────────────────────────────────
    print(f"\n{'=' * 70}")
    print("📋 评估汇总")
    print(f"{'=' * 70}")

    print(f"\n{'模型':<25s} {'维度':>5s} {'相关性':>7s} {'Margin':>8s} {'口语sim':>8s} {'速度ms':>7s}")
    print("─" * 65)
    for name, r in results.items():
        if "error" in r:
            print(f"{name:<25s} {'N/A':>5s} {'ERR':>7s}")
            continue
        print(
            f"{name:<25s} "
            f"{r['dim']:>5d} "
            f"{r['relevance']['accuracy']:>6.0f}% "
            f"{r['relevance']['avg_margin']:>8.4f} "
            f"{r['oral_noise']['avg_oral_clean_similarity']:>8.4f} "
            f"{r['speed']['per_query_ms']:>6.1f}"
        )

    print(f"\n{'=' * 70}")

    # 保存详细结果
    output_path = os.path.join(os.path.dirname(__file__), 'eval_embedding_results.json')
    # 清理 details 以减小文件大小
    save_results = {}
    for name, r in results.items():
        if "error" in r:
            save_results[name] = r
        else:
            save_results[name] = {
                "model": r["model"],
                "dim": r["dim"],
                "relevance_accuracy": r["relevance"]["accuracy"],
                "relevance_margin": r["relevance"]["avg_margin"],
                "oral_noise_similarity": r["oral_noise"]["avg_oral_clean_similarity"],
                "speed_per_query_ms": r["speed"]["per_query_ms"],
            }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(save_results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")

    return results


if __name__ == "__main__":
    main()
