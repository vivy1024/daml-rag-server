#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chunk质量对比测试脚本

用5个典型查询对比语义分割前后的检索质量。

对比指标：
- 召回的chunk数量
- 平均相似度分数
- Top-K chunk的文本预览（辅助人工判断语义连贯性）

用法:
  docker exec fitness_daml_rag python /app/scripts/compare_chunk_quality.py
  docker exec fitness_daml_rag python /app/scripts/compare_chunk_quality.py --top-k 5

版本: v1.0.0
日期: 2026-02-16
作者: 薛小川
"""

import os
import sys
import json
import logging
import argparse
import time
from typing import List, Dict

if sys.platform == "win32":
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "training_knowledge"
EMBEDDING_MODEL = "thenlper/gte-large-zh"
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# 5个典型测试查询
TEST_QUERIES = [
    {
        "id": 1,
        "query": "深蹲的正确姿势和常见错误",
        "domain": "训练动作",
        "expected_keywords": ["深蹲", "姿势", "膝盖", "髋关节"],
    },
    {
        "id": 2,
        "query": "肌肉恢复时间和训练频率",
        "domain": "训练计划",
        "expected_keywords": ["恢复", "频率", "肌肉", "休息"],
    },
    {
        "id": 3,
        "query": "蛋白质摄入量计算",
        "domain": "营养",
        "expected_keywords": ["蛋白质", "摄入", "克", "体重"],
    },
    {
        "id": 4,
        "query": "运动损伤预防",
        "domain": "安全",
        "expected_keywords": ["损伤", "预防", "热身", "拉伸"],
    },
    {
        "id": 5,
        "query": "力量训练周期化",
        "domain": "训练计划",
        "expected_keywords": ["周期", "力量", "训练", "阶段"],
    },
]


def search_qdrant(client, encoder, query: str, top_k: int = 10) -> List[Dict]:
    """在Qdrant中搜索"""
    query_vector = encoder.encode(query, normalize_embeddings=False).tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )

    hits = []
    for r in results.points:
        payload = r.payload or {}
        hits.append({
            "score": round(r.score, 4),
            "text": payload.get("chunk_text", "")[:300],
            "source": payload.get("source", ""),
            "title": payload.get("title", ""),
            "char_count": payload.get("char_count", 0),
            "splitter": payload.get("splitter", "legacy"),
            "avg_similarity": payload.get("avg_similarity", None),
            "sentence_count": payload.get("sentence_count", None),
        })

    return hits


def keyword_hit_rate(text: str, keywords: List[str]) -> float:
    """计算关键词命中率"""
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in text)
    return hits / len(keywords)


def run_comparison(args):
    logger.info("加载模型和连接Qdrant...")

    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient

    encoder = SentenceTransformer(EMBEDDING_MODEL)
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30)

    # 集合信息
    try:
        info = client.get_collection(COLLECTION_NAME)
        logger.info(f"集合: {COLLECTION_NAME} ({info.points_count} points)")
    except Exception as e:
        logger.error(f"集合不存在: {e}")
        return 1

    top_k = args.top_k
    results_summary = []

    logger.info(f"\n{'='*70}")
    logger.info(f"Chunk质量对比测试 (Top-{top_k})")
    logger.info(f"{'='*70}")

    for tq in TEST_QUERIES:
        query = tq["query"]
        logger.info(f"\n{'─'*70}")
        logger.info(f"查询 {tq['id']}: {query}")
        logger.info(f"领域: {tq['domain']} | 期望关键词: {tq['expected_keywords']}")
        logger.info(f"{'─'*70}")

        start = time.time()
        hits = search_qdrant(client, encoder, query, top_k=top_k)
        elapsed = time.time() - start

        if not hits:
            logger.warning("  无结果")
            results_summary.append({
                "query_id": tq["id"],
                "query": query,
                "hit_count": 0,
                "avg_score": 0,
                "keyword_hit_rate": 0,
                "latency_ms": elapsed * 1000,
            })
            continue

        # 统计
        scores = [h["score"] for h in hits]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)

        # 关键词命中率（在所有返回chunk的合并文本中）
        all_text = " ".join(h["text"] for h in hits)
        kw_rate = keyword_hit_rate(all_text, tq["expected_keywords"])

        # chunk大小统计
        sizes = [h["char_count"] for h in hits if h["char_count"] > 0]
        avg_size = sum(sizes) / len(sizes) if sizes else 0

        # 分割器类型统计
        splitter_types = {}
        for h in hits:
            st = h["splitter"]
            splitter_types[st] = splitter_types.get(st, 0) + 1

        logger.info(f"  命中: {len(hits)} | 平均分: {avg_score:.4f} | 最高: {max_score:.4f} | 最低: {min_score:.4f}")
        logger.info(f"  关键词命中率: {kw_rate:.0%} | 平均chunk大小: {avg_size:.0f}字符")
        logger.info(f"  分割器: {splitter_types}")
        logger.info(f"  延迟: {elapsed*1000:.1f}ms")

        # 显示Top-3详情
        for j, h in enumerate(hits[:3]):
            sim_info = f" | 组内相似度: {h['avg_similarity']:.3f}" if h["avg_similarity"] is not None else ""
            logger.info(f"\n  Top-{j+1} (score={h['score']:.4f} | {h['char_count']}字符{sim_info}):")
            logger.info(f"    来源: {h['source']} | {h['title']}")
            preview = h["text"][:150].replace("\n", " ")
            logger.info(f"    内容: {preview}...")

        results_summary.append({
            "query_id": tq["id"],
            "query": query,
            "domain": tq["domain"],
            "hit_count": len(hits),
            "avg_score": round(avg_score, 4),
            "max_score": round(max_score, 4),
            "min_score": round(min_score, 4),
            "keyword_hit_rate": round(kw_rate, 2),
            "avg_chunk_size": round(avg_size),
            "splitter_types": splitter_types,
            "latency_ms": round(elapsed * 1000, 1),
        })

    # ─── 汇总 ───
    logger.info(f"\n{'='*70}")
    logger.info("汇总")
    logger.info(f"{'='*70}")

    if results_summary:
        overall_avg_score = sum(r["avg_score"] for r in results_summary) / len(results_summary)
        overall_kw_rate = sum(r["keyword_hit_rate"] for r in results_summary) / len(results_summary)
        overall_latency = sum(r["latency_ms"] for r in results_summary) / len(results_summary)

        logger.info(f"  查询数: {len(results_summary)}")
        logger.info(f"  平均相似度: {overall_avg_score:.4f}")
        logger.info(f"  平均关键词命中率: {overall_kw_rate:.0%}")
        logger.info(f"  平均延迟: {overall_latency:.1f}ms")

        # 逐查询表格
        logger.info(f"\n  {'查询':<25} {'命中':>4} {'平均分':>8} {'关键词':>6} {'延迟':>8}")
        logger.info(f"  {'─'*55}")
        for r in results_summary:
            logger.info(
                f"  {r['query']:<25} {r['hit_count']:>4} "
                f"{r['avg_score']:>8.4f} {r['keyword_hit_rate']:>5.0%} "
                f"{r['latency_ms']:>7.1f}ms"
            )

    logger.info(f"\n{'='*70}")

    # 输出JSON结果
    if args.output:
        output_path = args.output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "collection": COLLECTION_NAME,
                "points_count": info.points_count,
                "top_k": top_k,
                "results": results_summary,
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"结果已保存: {output_path}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Chunk质量对比测试")
    parser.add_argument("--top-k", type=int, default=10, help="每个查询返回的Top-K (默认: 10)")
    parser.add_argument("--output", type=str, help="输出JSON结果文件路径")
    args = parser.parse_args()

    return run_comparison(args)


if __name__ == "__main__":
    sys.exit(main())
