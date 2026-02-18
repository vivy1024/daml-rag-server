#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Layer2图谱查询修复

验证：
1. 向量结果ID提取成功
2. Layer2返回图谱结果>0
3. 三层检索完整执行
"""

import asyncio
import logging
import sys
import os

# 这是手工验证脚本（依赖 Neo4j/Qdrant/真实数据），不纳入默认 pytest 套件
if "pytest" in sys.modules:
    import pytest

    pytest.skip("手工验证脚本（Layer2 图谱查询修复），默认跳过", allow_module_level=True)

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from framework.retrieval.graphrag import GraphRAGQueryTool
from framework.retrieval.graph.kg_full import KnowledgeGraphFull

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_layer2_graph_query():
    """测试Layer2图谱查询"""
    logger.info("=" * 80)
    logger.info("测试Layer2图谱查询修复")
    logger.info("=" * 80)
    
    try:
        # 1. 初始化GraphRAG
        logger.info("\n→ 步骤1: 初始化GraphRAG组件")
        kg_full = KnowledgeGraphFull(
            qdrant_collection="fitness_exercises_v2",  # 使用正确的集合
            embedding_model="BAAI/bge-m3"  # 使用正确的embedding模型
        )
        graphrag_tool = GraphRAGQueryTool(kg_full)
        
        # 2. 执行三层检索
        logger.info("\n→ 步骤2: 执行三层检索查询")
        query_input = {
            "query_type": "three_layer",
            "domain": "fitness_exercises",
            "query_text": "胸部训练动作",
            "top_k": 5,
            "min_similarity": 0.5,
            "return_reason": True
        }
        
        result = await graphrag_tool.query(query_input)
        
        # 3. 验证结果
        logger.info("\n→ 步骤3: 验证结果")
        logger.info(f"查询类型: {result.get('query_type')}")
        logger.info(f"结果数量: {result.get('count')}")
        
        # 检查三层检索信息
        three_layer_info = result.get('three_layer_result')
        if three_layer_info:
            logger.info("\n三层检索详情:")
            logger.info(f"  Layer 1: {three_layer_info['layer1']['count']}个结果 (来源: {three_layer_info['layer1']['source']})")
            logger.info(f"  Layer 2: {three_layer_info['layer2']['count']}个结果 (来源: {three_layer_info['layer2']['source']})")
            logger.info(f"  Layer 3: {three_layer_info['layer3']['count']}个结果 (来源: {three_layer_info['layer3']['source']})")
            logger.info(f"  Pipeline: {three_layer_info['pipeline']}")
            
            # 验证Layer2是否成功
            layer2_count = three_layer_info['layer2']['count']
            layer2_source = three_layer_info['layer2']['source']
            
            if layer2_count > 0 and layer2_source == "Neo4j":
                logger.info("\n✅ Layer2图谱查询成功!")
                logger.info(f"   返回{layer2_count}个图谱结果")
                return True
            else:
                logger.warning(f"\n⚠️ Layer2图谱查询失败或降级")
                logger.warning(f"   结果数: {layer2_count}, 来源: {layer2_source}")
                return False
        else:
            logger.error("\n❌ 未找到三层检索信息")
            return False
            
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_layer2_graph_query())
    sys.exit(0 if success else 1)
