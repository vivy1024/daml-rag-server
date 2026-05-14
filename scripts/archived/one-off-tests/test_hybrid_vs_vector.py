#!/usr/bin/env python3
"""
A/B对比测试：向量检索 vs BM25 vs 混合检索(RRF)
对比三种检索方法在20个典型健身查询上的表现

用法:
  docker exec fitness_daml_rag python /app/scripts/test_hybrid_vs_vector.py
  docker exec fitness_daml_rag python /app/scripts/test_hybrid_vs_vector.py --top-k 5 --queries 10

版本: v1.0.0
"""

import sys, os, json, time, logging, argparse, asyncio
from typing import List, Dict, Tuple
from collections import defaultdict

sys.path.insert(0, '/app/src')

logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ============= 20个典型健身查询 =============
# 覆盖5大类场景：动作技术、训练计划、营养、康复、理论原则
TEST_QUERIES = [
    # --- 动作技术（精确关键词匹配场景，BM25应占优）---
    {"query": "深蹲的正确姿势和常见错误", "category": "动作技术", "keywords": ["深蹲", "姿势", "错误"]},
    {"query": "硬拉和罗马尼亚硬拉的区别", "category": "动作技术", "keywords": ["硬拉", "罗马尼亚", "区别"]},
    {"query": "卧推时肩膀疼怎么办", "category": "动作技术", "keywords": ["卧推", "肩膀", "疼"]},
    {"query": "引体向上做不了怎么练", "category": "动作技术", "keywords": ["引体向上", "练"]},

    # --- 训练计划（语义理解场景，向量应占优）---
    {"query": "新手一周三练的训练安排", "category": "训练计划", "keywords": ["新手", "一周三练", "安排"]},
    {"query": "如何突破力量平台期", "category": "训练计划", "keywords": ["突破", "平台期", "力量"]},
    {"query": "增肌和减脂能同时进行吗", "category": "训练计划", "keywords": ["增肌", "减脂", "同时"]},
    {"query": "周期化训练是什么意思", "category": "训练计划", "keywords": ["周期化", "训练"]},

    # --- 营养（混合场景）---
    {"query": "训练后多久吃蛋白质最好", "category": "营养", "keywords": ["训练后", "蛋白质", "时间"]},
    {"query": "增肌期每天需要多少蛋白质", "category": "营养", "keywords": ["增肌", "蛋白质", "多少"]},
    {"query": "肌酸的正确服用方法", "category": "营养", "keywords": ["肌酸", "服用", "方法"]},
    {"query": "减脂期碳水化合物怎么吃", "category": "营养", "keywords": ["减脂", "碳水化合物"]},

    # --- 康复安全（精确匹配+语义混合）---
    {"query": "腰椎间盘突出能做深蹲吗", "category": "康复安全", "keywords": ["腰椎间盘突出", "深蹲"]},
    {"query": "膝盖有响声是怎么回事", "category": "康复安全", "keywords": ["膝盖", "响声"]},
    {"query": "运动后肌肉酸痛和受伤的区别", "category": "康复安全", "keywords": ["肌肉酸痛", "受伤", "区别"]},
    {"query": "热身和拉伸的正确顺序", "category": "康复安全", "keywords": ["热身", "拉伸", "顺序"]},

    # --- 理论原则（纯语义场景）---
    {"query": "渐进超负荷原则怎么应用", "category": "理论原则", "keywords": ["渐进超负荷", "原则"]},
    {"query": "RPE和1RM的关系", "category": "理论原则", "keywords": ["RPE", "1RM"]},
    {"query": "FITT原则在力量训练中的应用", "category": "理论原则", "keywords": ["FITT", "力量训练"]},
    {"query": "超量恢复理论", "category": "理论原则", "keywords": ["超量恢复"]},
]


def keyword_hit_rate(results: List[Dict], keywords: List[str], text_field: str = 'text') -> float:
    """计算关键词命中率：top结果中包含多少个期望关键词"""
    if not results or not keywords:
        return 0.0
    combined_text = ' '.join(r.get(text_field, '') for r in results[:5]).lower()
    hits = sum(1 for kw in keywords if kw.lower() in combined_text)
    return hits / len(keywords)


def result_diversity(results: List[Dict], text_field: str = 'text') -> float:
    """计算结果多样性：不同文档来源的比例"""
    if not results:
        return 0.0
    sources = set()
    for r in results[:10]:
        payload = r.get('payload', {})
        source = payload.get('filename', '') or payload.get('source', '') or r.get(text_field, '')[:30]
        sources.add(source)
    return len(sources) / min(len(results), 10)


def print_results_comparison(query_info: Dict, vector_results: List, bm25_results: List, hybrid_results: List, top_k: int):
    """打印单个查询的对比结果"""
    q = query_info['query']
    kw = query_info['keywords']

    v_hit = keyword_hit_rate(vector_results, kw)
    b_hit = keyword_hit_rate(bm25_results, kw)
    h_hit = keyword_hit_rate(hybrid_results, kw)

    v_div = result_diversity(vector_results)
    b_div = result_diversity(bm25_results)
    h_div = result_diversity(hybrid_results)

    # 判断赢家
    hits = {'vector': v_hit, 'bm25': b_hit, 'hybrid': h_hit}
    winner = max(hits, key=hits.get)
    if list(hits.values()).count(max(hits.values())) > 1:
        winner = 'tie'

    print(f"\n{'─'*70}")
    print(f"  📝 {q}")
    print(f"  🏷️  {query_info['category']} | 关键词: {', '.join(kw)}")
    print(f"{'─'*70}")
    print(f"  {'方法':<12} {'结果数':>6} {'关键词命中':>10} {'多样性':>8} {'Top1分数':>10}")
    print(f"  {'─'*56}")

    for name, results, hit, div in [
        ('Vector', vector_results, v_hit, v_div),
        ('BM25', bm25_results, b_hit, b_div),
        ('Hybrid+RRF', hybrid_results, h_hit, h_div),
    ]:
        top1_score = results[0].get('score', results[0].get('rrf_score', 0)) if results else 0
        marker = ' 🏆' if name.lower().startswith(winner[:3]) and winner != 'tie' else ''
        print(f"  {name:<12} {len(results):>6} {hit:>10.0%} {div:>8.0%} {top1_score:>10.4f}{marker}")

    return {
        'query': q,
        'category': query_info['category'],
        'vector_hit': v_hit, 'bm25_hit': b_hit, 'hybrid_hit': h_hit,
        'vector_div': v_div, 'bm25_div': b_div, 'hybrid_div': h_div,
        'vector_count': len(vector_results),
        'bm25_count': len(bm25_results),
        'hybrid_count': len(hybrid_results),
        'winner': winner,
    }


async def run_comparison(top_k: int = 5, max_queries: int = 20):
    """运行A/B对比测试"""
    from framework.retrieval.bm25_engine import BM25Engine
    from framework.retrieval.hybrid_search import HybridSearchEngine

    print("=" * 70)
    print("  🔬 A/B对比测试：Vector vs BM25 vs Hybrid(RRF)")
    print(f"  📊 查询数: {min(max_queries, len(TEST_QUERIES))} | Top-K: {top_k}")
    print("=" * 70)

    # 初始化引擎
    print("\n⏳ 初始化检索引擎...")
    t0 = time.time()
    bm25 = BM25Engine(qdrant_host='qdrant', qdrant_port=6333)
    hybrid = HybridSearchEngine()
    print(f"✅ 引擎初始化完成 ({time.time()-t0:.1f}s), BM25索引: {len(bm25.documents)} 文档")

    # 向量检索需要通过 Qdrant 直接查询
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer

    print("⏳ 加载Embedding模型...")
    encoder = SentenceTransformer("thenlper/gte-large-zh")
    qdrant = QdrantClient(host='qdrant', port=6333)
    print("✅ Embedding模型加载完成")

    queries = TEST_QUERIES[:max_queries]
    all_stats = []
    category_stats = defaultdict(lambda: {'vector': 0, 'bm25': 0, 'hybrid': 0, 'count': 0})

    for i, q_info in enumerate(queries, 1):
        print(f"\n\n{'='*70}")
        print(f"  [{i}/{len(queries)}] 测试中...")

        query = q_info['query']

        # 1. 纯向量检索（新版qdrant-client用query_points）
        query_vec = encoder.encode(query).tolist()
        vector_resp = qdrant.query_points(
            collection_name='training_knowledge',
            query=query_vec,
            limit=top_k,
            with_payload=True,
        )
        vector_results = [{
            'id': str(r.id),
            'score': r.score,
            'text': r.payload.get('chunk_text', r.payload.get('text', '')),
            'payload': r.payload,
        } for r in vector_resp.points]

        # 2. 纯BM25检索
        bm25_results = bm25.search(query, top_k=top_k)

        # 3. 混合检索（BM25 + Vector + RRF）
        # 为了公平对比，这里手动做RRF而不走GraphRAG API
        from framework.retrieval.reranker import FitnessReranker

        vector_for_rrf = [{
            'id': str(r.id),
            'score': r.score,
            'text': r.payload.get('chunk_text', r.payload.get('text', '')),
            'payload': r.payload,
        } for r in qdrant.query_points(
            collection_name='training_knowledge',
            query=query_vec,
            limit=20,
            with_payload=True,
        ).points]
        bm25_for_rrf = bm25.search(query, top_k=20)

        hybrid_results = FitnessReranker.rrf_fusion(
            result_lists=[vector_for_rrf, bm25_for_rrf],
            k=60, id_field='id'
        )[:top_k]

        # 对比
        stats = print_results_comparison(q_info, vector_results, bm25_results, hybrid_results, top_k)
        all_stats.append(stats)

        cat = q_info['category']
        category_stats[cat]['count'] += 1
        category_stats[cat]['vector'] += stats['vector_hit']
        category_stats[cat]['bm25'] += stats['bm25_hit']
        category_stats[cat]['hybrid'] += stats['hybrid_hit']

    # ============= 汇总报告 =============
    print(f"\n\n{'='*70}")
    print(f"  📊 汇总报告")
    print(f"{'='*70}")

    # 总体胜率
    wins = defaultdict(int)
    for s in all_stats:
        wins[s['winner']] += 1

    print(f"\n  🏆 总体胜率 ({len(all_stats)} 个查询):")
    for method in ['vector', 'bm25', 'hybrid', 'tie']:
        count = wins.get(method, 0)
        bar = '█' * int(count / len(all_stats) * 30)
        print(f"    {method:<12} {count:>3} 胜 ({count/len(all_stats):>5.0%}) {bar}")

    # 分类别统计
    print(f"\n  📂 分类别关键词命中率:")
    print(f"  {'类别':<12} {'Vector':>10} {'BM25':>10} {'Hybrid':>10} {'最优':>8}")
    print(f"  {'─'*52}")
    for cat, data in sorted(category_stats.items()):
        n = data['count']
        v = data['vector'] / n if n else 0
        b = data['bm25'] / n if n else 0
        h = data['hybrid'] / n if n else 0
        best = max([('Vector', v), ('BM25', b), ('Hybrid', h)], key=lambda x: x[1])
        print(f"  {cat:<12} {v:>10.0%} {b:>10.0%} {h:>10.0%} {best[0]:>8}")

    # 总平均
    avg_v = sum(s['vector_hit'] for s in all_stats) / len(all_stats)
    avg_b = sum(s['bm25_hit'] for s in all_stats) / len(all_stats)
    avg_h = sum(s['hybrid_hit'] for s in all_stats) / len(all_stats)
    print(f"  {'─'*52}")
    print(f"  {'总平均':<12} {avg_v:>10.0%} {avg_b:>10.0%} {avg_h:>10.0%}")

    # 结论
    print(f"\n  💡 结论:")
    if avg_h >= avg_v and avg_h >= avg_b:
        print(f"    ✅ 混合检索(RRF)表现最优，关键词命中率 {avg_h:.0%}")
        if avg_h > avg_v:
            print(f"    📈 比纯向量提升 {(avg_h-avg_v)/avg_v*100:.1f}%" if avg_v > 0 else "")
    elif avg_b > avg_v:
        print(f"    ⚠️ BM25在当前数据上优于向量检索，建议检查embedding质量")
    else:
        print(f"    ℹ️ 向量检索在当前数据上表现最好")

    # 保存JSON结果
    output = {
        'test_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'config': {'top_k': top_k, 'rrf_k': 60, 'bm25_docs': len(bm25.documents)},
        'summary': {
            'wins': dict(wins),
            'avg_keyword_hit': {'vector': avg_v, 'bm25': avg_b, 'hybrid': avg_h},
        },
        'details': all_stats,
    }
    output_path = '/app/scripts/data/hybrid_ab_test_results.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 详细结果已保存: {output_path}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='A/B对比测试：Vector vs BM25 vs Hybrid')
    parser.add_argument('--top-k', type=int, default=5, help='每种方法返回的结果数')
    parser.add_argument('--queries', type=int, default=20, help='测试查询数量')
    args = parser.parse_args()

    asyncio.run(run_comparison(top_k=args.top_k, max_queries=args.queries))


if __name__ == '__main__':
    main()
