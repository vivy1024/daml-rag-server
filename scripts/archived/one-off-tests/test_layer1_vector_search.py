#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Layer 1向量检索
诊断为什么返回0个结果
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.framework.retrieval.graph.kg_full import KnowledgeGraphFull
from src.framework.retrieval.graphrag import GraphRAGQueryTool
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_vector_search():
    """测试向量检索"""
    
    logger.info("=" * 80)
    logger.info("🔍 测试Layer 1向量检索")
    logger.info("=" * 80)
    
    # 1. 初始化KnowledgeGraphFull
    logger.info("\n→ 步骤1: 初始化KnowledgeGraphFull")
    kg_full = KnowledgeGraphFull(
        qdrant_collection="fitness_exercises_v2",
        embedding_model="BAAI/bge-m3"
    )
    
    # 2. 创建GraphRAGQueryTool
    logger.info("\n→ 步骤2: 创建GraphRAGQueryTool")
    graphrag_tool = GraphRAGQueryTool(kg_full)
    
    # 3. 测试不同的查询场景
    test_cases = [
        {
            "name": "场景1: 无过滤条件",
            "query_text": "胸部训练动作",
            "filters": {},
            "top_k": 5
        },
        {
            "name": "场景2: 带difficulty过滤（中文）",
            "query_text": "胸部训练动作",
            "filters": {"difficulty": "新手"},
            "top_k": 5
        },
        {
            "name": "场景3: 带difficulty过滤（英文）",
            "query_text": "胸部训练动作",
            "filters": {"difficulty": "beginner"},
            "top_k": 5
        },
        {
            "name": "场景4: 带label过滤（错误）",
            "query_text": "胸部训练动作",
            "filters": {"label": "Exercise"},
            "top_k": 5
        },
        {
            "name": "场景5: 直接调用_semantic_search",
            "query_text": "胸部训练动作",
            "filters": {},
            "top_k": 5,
            "direct": True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"测试 {i}/{len(test_cases)}: {test_case['name']}")
        logger.info(f"{'=' * 80}")
        logger.info(f"查询文本: {test_case['query_text']}")
        logger.info(f"过滤条件: {test_case['filters']}")
        logger.info(f"top_k: {test_case['top_k']}")
        
        try:
            if test_case.get('direct'):
                # 直接调用_semantic_search
                results = await graphrag_tool._semantic_search(
                    query_text=test_case['query_text'],
                    domain="fitness_exercises",
                    top_k=test_case['top_k'],
                    min_similarity=0.5,
                    filters=test_case['filters']
                )
                logger.info(f"✅ 结果数量: {len(results)}")
                if results:
                    for j, r in enumerate(results[:3], 1):
                        if hasattr(r, 'payload'):
                            logger.info(f"  {j}. {r.payload.get('name_zh', 'N/A')} (score: {r.score:.4f})")
                        else:
                            logger.info(f"  {j}. {r}")
            else:
                # 通过GraphRAG API
                result = await graphrag_tool.query({
                    "query_type": "semantic_search",
                    "domain": "fitness_exercises",
                    "query_text": test_case['query_text'],
                    "filters": test_case['filters'],
                    "top_k": test_case['top_k'],
                    "min_similarity": 0.5,
                    "return_reason": False
                })
                
                logger.info(f"✅ 结果数量: {result.get('count', 0)}")
                if result.get('results'):
                    for j, r in enumerate(result['results'][:3], 1):
                        if hasattr(r, 'payload'):
                            logger.info(f"  {j}. {r.payload.get('name_zh', 'N/A')} (score: {r.score:.4f})")
                        elif isinstance(r, dict):
                            logger.info(f"  {j}. {r.get('name_zh', 'N/A')}")
                        else:
                            logger.info(f"  {j}. {r}")
        
        except Exception as e:
            logger.error(f"❌ 测试失败: {e}", exc_info=True)
    
    logger.info(f"\n{'=' * 80}")
    logger.info("✅ 测试完成")
    logger.info(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(test_vector_search())
