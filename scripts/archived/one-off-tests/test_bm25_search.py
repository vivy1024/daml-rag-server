#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BM25全文检索测试脚本
对比向量检索、BM25检索、混合RRF检索的效果
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.framework.retrieval.hybrid_search import get_hybrid_search_engine


def print_results(method_name: str, results: list, max_display: int = 5):
    """打印检索结果"""
    print(f"\n{'='*80}")
    print(f"【{method_name}】检索结果（共{len(results)}个）")
    print(f"{'='*80}")

    for i, result in enumerate(results[:max_display], 1):
        score = result.get('score', 0.0)
        rrf_score = result.get('rrf_score', 0.0)
        text = result.get('text', '')[:100]  # 只显示前100字符

        print(f"\n{i}. [分数: {score:.4f}", end='')
        if rrf_score > 0:
            print(f" | RRF: {rrf_score:.4f}", end='')
        print(f"]")
        print(f"   {text}...")


async def test_single_query(engine, query: str):
    """测试单个查询"""
    print(f"\n\n{'#'*80}")
    print(f"# 查询: {query}")
    print(f"{'#'*80}")

    # 对比三种检索方法
    results = await engine.compare_search_methods(query, top_k=10)

    # 打印结果
    print_results("向量检索", results['vector'])
    print_results("BM25检索", results['bm25'])
    print_results("混合RRF检索", results['hybrid'])


async def main():
    """主函数"""
    print("="*80)
    print("BM25全文检索测试")
    print("="*80)

    # 初始化混合检索引擎
    engine = get_hybrid_search_engine()

    # 测试查询列表
    test_queries = [
        "NSCA CSCS认证",  # 精确术语匹配
        "深蹲 膝关节 疼痛",  # 多关键词匹配
        "蛋白质 每公斤体重 1.6克",  # 数字+术语匹配
        "周期化训练 线性周期",  # 专业术语
        "肩袖损伤 康复训练",  # 康复领域
    ]

    # 逐个测试
    for query in test_queries:
        await test_single_query(engine, query)

    print(f"\n\n{'='*80}")
    print("测试完成！")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
