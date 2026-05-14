# -*- coding: utf-8 -*-
"""
A/B 测试脚本：对比三种检索策略
- 纯 BM25
- 新权重 Hybrid（按意图动态调整）
- 旧等权 Hybrid（weights=[1.0, 1.0]）

用于 retrieval-optimization-v2 Task 2 验证
"""
import asyncio
import sys
import os
import json
import time

# 添加项目根目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.framework.retrieval.intent_classifier import classify_intent
from src.framework.retrieval.hybrid_search import HybridSearchEngine, INTENT_WEIGHTS, DEFAULT_WEIGHTS
from src.framework.retrieval.reranker import FitnessReranker

# ─── 20 个测试查询（覆盖 STRUCTURED / HYBRID / SEMANTIC 三类意图）─────────

TEST_QUERIES = [
    # STRUCTURED 类（预期走 Neo4j Cypher）
    {"query": "深蹲练哪些肌肉", "expected_intent": "STRUCTURED", "category": "exercise_muscles"},
    {"query": "练胸肌的动作有哪些", "expected_intent": "STRUCTURED", "category": "muscle_exercises"},
    {"query": "哑铃能做什么动作", "expected_intent": "STRUCTURED", "category": "equipment_exercises"},
    {"query": "卧推需要什么器械", "expected_intent": "STRUCTURED", "category": "exercise_equipment"},
    {"query": "腰椎间盘突出不能做什么动作", "expected_intent": "STRUCTURED", "category": "safety"},
    {"query": "圆肩怎么矫正", "expected_intent": "STRUCTURED", "category": "postural"},
    {"query": "卧推力量标准", "expected_intent": "STRUCTURED", "category": "strength_standard"},

    # HYBRID 类（有实体但查询复杂）
    {"query": "深蹲时膝盖总是内扣怎么办，需要加强哪些肌肉", "expected_intent": "HYBRID", "category": "complex_exercise"},
    {"query": "我想用哑铃在家练背，有什么好的训练计划推荐", "expected_intent": "HYBRID", "category": "complex_plan"},
    {"query": "卧推总是肩膀疼，是不是动作有问题，怎么改善", "expected_intent": "HYBRID", "category": "complex_pain"},
    {"query": "硬拉和罗马尼亚硬拉有什么区别，分别练什么", "expected_intent": "HYBRID", "category": "comparison"},
    {"query": "引体向上做不了怎么办，有什么替代动作可以练背", "expected_intent": "HYBRID", "category": "alternative"},
    {"query": "三角肌后束很弱，除了面拉还有什么好动作", "expected_intent": "HYBRID", "category": "weak_point"},

    # SEMANTIC 类（开放性问题，无明确结构化实体）
    {"query": "增肌期间怎么安排饮食", "expected_intent": "SEMANTIC", "category": "nutrition"},
    {"query": "一周练几次比较好", "expected_intent": "SEMANTIC", "category": "frequency"},
    {"query": "减脂期力量会下降吗", "expected_intent": "SEMANTIC", "category": "cutting"},
    {"query": "健身多久能看到效果", "expected_intent": "SEMANTIC", "category": "progress"},
    {"query": "蛋白粉有必要吃吗", "expected_intent": "SEMANTIC", "category": "supplement"},
    {"query": "训练后肌肉酸痛还能继续练吗", "expected_intent": "SEMANTIC", "category": "recovery"},
    {"query": "有氧和无氧哪个减脂效果好", "expected_intent": "SEMANTIC", "category": "cardio_vs_weight"},
]


def test_intent_classification():
    """测试意图分类准确率"""
    print("\n" + "=" * 70)
    print("📊 Part 1: 意图分类准确率测试")
    print("=" * 70)

    correct = 0
    results = []

    for i, tc in enumerate(TEST_QUERIES, 1):
        result = classify_intent(tc["query"])
        actual = result.intent.name  # STRUCTURED / HYBRID / SEMANTIC
        expected = tc["expected_intent"]
        match = actual == expected

        if match:
            correct += 1
            icon = "✅"
        else:
            icon = "❌"

        results.append({
            "query": tc["query"],
            "expected": expected,
            "actual": actual,
            "match": match,
            "confidence": result.confidence,
            "structured_type": result.structured_type.value if result.structured_type else None,
            "entity": result.extracted_entity,
        })

        print(f"  {icon} [{i:2d}] {tc['query'][:30]:30s} | 预期={expected:10s} | 实际={actual:10s} | conf={result.confidence:.2f}")

    accuracy = correct / len(TEST_QUERIES) * 100
    print(f"\n  📈 准确率: {correct}/{len(TEST_QUERIES)} = {accuracy:.1f}%")
    print(f"  {'✅ 达标 (>85%)' if accuracy > 85 else '⚠️ 未达标 (<85%)'}")

    return results, accuracy


async def test_search_comparison():
    """对比三种检索方法"""
    print("\n" + "=" * 70)
    print("📊 Part 2: 检索方法 A/B 对比")
    print("=" * 70)

    engine = HybridSearchEngine()

    # 检查 BM25 引擎是否可用
    try:
        bm25_test = engine.bm25_search("深蹲", top_k=3)
        bm25_available = len(bm25_test) > 0
        print(f"  BM25 引擎: {'✅ 可用 (' + str(len(bm25_test)) + ' 结果)' if bm25_available else '❌ 不可用'}")
    except Exception as e:
        bm25_available = False
        print(f"  BM25 引擎: ❌ 不可用 ({e})")

    if not bm25_available:
        print("  ⚠️ BM25 引擎不可用，跳过检索对比（仅输出意图分类结果）")
        return None

    comparison_results = []

    for i, tc in enumerate(TEST_QUERIES, 1):
        query = tc["query"]
        intent_result = classify_intent(query)
        intent_type = intent_result.intent.name

        print(f"\n  ─── [{i:2d}] {query} (intent={intent_type}) ───")

        # 1. 纯 BM25
        t0 = time.time()
        bm25_results = engine.bm25_search(query, top_k=5)
        bm25_time = (time.time() - t0) * 1000

        # 2. 新权重 Hybrid（按意图动态调整）
        t0 = time.time()
        try:
            new_hybrid = await engine.hybrid_search(
                query=query, domain="fitness", top_k=5,
                vector_top_k=20, bm25_top_k=20,
                intent_type=intent_type
            )
            new_hybrid_time = (time.time() - t0) * 1000
        except Exception as e:
            new_hybrid = []
            new_hybrid_time = 0
            print(f"    ⚠️ 新权重Hybrid失败: {e}")

        # 3. 旧等权 Hybrid（weights 不传，走 DEFAULT_WEIGHTS）
        t0 = time.time()
        try:
            old_hybrid = await engine.hybrid_search(
                query=query, domain="fitness", top_k=5,
                vector_top_k=20, bm25_top_k=20,
                intent_type=None  # 不传意图，使用默认权重
            )
            old_hybrid_time = (time.time() - t0) * 1000
        except Exception as e:
            old_hybrid = []
            old_hybrid_time = 0
            print(f"    ⚠️ 旧等权Hybrid失败: {e}")

        # 提取 top-5 文本摘要
        def summarize(results, n=5):
            summaries = []
            for r in results[:n]:
                text = r.get("text", "")[:60]
                score = r.get("rrf_score", r.get("score", 0))
                summaries.append(f"{score:.4f} | {text}")
            return summaries

        bm25_summary = summarize(bm25_results)
        new_summary = summarize(new_hybrid)
        old_summary = summarize(old_hybrid)

        # 关键词命中率（查询中的实体词是否出现在 top-5 结果文本中）
        def keyword_hit_rate(results, query_text):
            if not results:
                return 0.0
            # 提取查询中的关键词
            from src.framework.retrieval.intent_classifier import (
                EXERCISE_KEYWORDS, MUSCLE_KEYWORDS, EQUIPMENT_KEYWORDS
            )
            keywords = []
            for kw in EXERCISE_KEYWORDS + MUSCLE_KEYWORDS + EQUIPMENT_KEYWORDS:
                if kw in query_text:
                    keywords.append(kw)
            if not keywords:
                return -1  # 无关键词可检测

            hits = 0
            for r in results[:5]:
                text = r.get("text", "")
                if any(kw in text for kw in keywords):
                    hits += 1
            return hits / min(len(results), 5)

        bm25_hit = keyword_hit_rate(bm25_results, query)
        new_hit = keyword_hit_rate(new_hybrid, query)
        old_hit = keyword_hit_rate(old_hybrid, query)

        print(f"    BM25      ({bm25_time:6.1f}ms): {len(bm25_results)} 结果, 关键词命中={bm25_hit:.0%}")
        print(f"    新Hybrid  ({new_hybrid_time:6.1f}ms): {len(new_hybrid)} 结果, 关键词命中={new_hit:.0%}")
        print(f"    旧Hybrid  ({old_hybrid_time:6.1f}ms): {len(old_hybrid)} 结果, 关键词命中={old_hit:.0%}")

        if bm25_summary:
            print(f"    BM25 Top1: {bm25_summary[0]}")
        if new_summary:
            print(f"    新H  Top1: {new_summary[0]}")
        if old_summary:
            print(f"    旧H  Top1: {old_summary[0]}")

        comparison_results.append({
            "query": query,
            "intent": intent_type,
            "bm25_count": len(bm25_results),
            "new_hybrid_count": len(new_hybrid),
            "old_hybrid_count": len(old_hybrid),
            "bm25_hit_rate": bm25_hit,
            "new_hybrid_hit_rate": new_hit,
            "old_hybrid_hit_rate": old_hit,
            "bm25_time_ms": bm25_time,
            "new_hybrid_time_ms": new_hybrid_time,
            "old_hybrid_time_ms": old_hybrid_time,
        })

    # 汇总统计
    print("\n" + "=" * 70)
    print("📊 汇总统计")
    print("=" * 70)

    valid_results = [r for r in comparison_results if r["bm25_hit_rate"] >= 0]

    if valid_results:
        avg_bm25_hit = sum(r["bm25_hit_rate"] for r in valid_results) / len(valid_results)
        avg_new_hit = sum(r["new_hybrid_hit_rate"] for r in valid_results) / len(valid_results)
        avg_old_hit = sum(r["old_hybrid_hit_rate"] for r in valid_results) / len(valid_results)

        print(f"  平均关键词命中率（{len(valid_results)} 个有关键词的查询）:")
        print(f"    纯 BM25:     {avg_bm25_hit:.1%}")
        print(f"    新权重Hybrid: {avg_new_hit:.1%}")
        print(f"    旧等权Hybrid: {avg_old_hit:.1%}")

    avg_bm25_time = sum(r["bm25_time_ms"] for r in comparison_results) / len(comparison_results)
    avg_new_time = sum(r["new_hybrid_time_ms"] for r in comparison_results) / len(comparison_results)
    avg_old_time = sum(r["old_hybrid_time_ms"] for r in comparison_results) / len(comparison_results)

    print(f"\n  平均响应时间:")
    print(f"    纯 BM25:     {avg_bm25_time:.1f}ms")
    print(f"    新权重Hybrid: {avg_new_time:.1f}ms")
    print(f"    旧等权Hybrid: {avg_old_time:.1f}ms")

    return comparison_results


async def main():
    print("🔬 检索优化 V2 — A/B 测试")
    print(f"   测试查询数: {len(TEST_QUERIES)}")
    print(f"   权重配置: {json.dumps({k: f'vec={v[0]}, bm25={v[1]}' for k, v in INTENT_WEIGHTS.items()}, ensure_ascii=False)}")
    print(f"   默认权重: vec={DEFAULT_WEIGHTS[0]}, bm25={DEFAULT_WEIGHTS[1]}")

    # Part 1: 意图分类
    intent_results, accuracy = test_intent_classification()

    # Part 2: 检索对比
    search_results = await test_search_comparison()

    print("\n" + "=" * 70)
    print("✅ A/B 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
