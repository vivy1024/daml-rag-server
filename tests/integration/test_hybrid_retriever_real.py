# -*- coding: utf-8 -*-
"""
HybridRetriever真实连接测试

验证Neo4j fulltext index创建后，HybridRetriever的真实工作情况：
- BM25全文搜索 + 向量语义混合检索
- 真实查询场景测试
- Hybrid vs Vector模式对比

版本: v1.0.0
日期: 2026-02-16
Requirements: Phase 1 Task 4 - Fulltext Index已创建
"""

import asyncio
import logging
import os
from typing import Dict, Any

import pytest
import pytest_asyncio

logger = logging.getLogger(__name__)


# =============================================================================
# Embedder Wrapper
# =============================================================================

class SentenceTransformerEmbedder:
    """Wrapper for SentenceTransformer to match neo4j-graphrag interface"""

    def __init__(self, model_name: str = "thenlper/gte-large-zh"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed_query(self, text: str):
        """Embed a single query text"""
        return self.model.encode(text).tolist()


# =============================================================================
# 真实连接测试（需要Neo4j + Qdrant + fulltext index）
# =============================================================================

@pytest.mark.integration
@pytest.mark.skip(reason="需要Neo4j 5.18.1+和正确的Qdrant collection配置")
@pytest.mark.asyncio
class TestHybridRetrieverReal:
    """HybridRetriever真实连接测试"""

    @pytest_asyncio.fixture(scope="class")
    async def real_retriever(self):
        """创建真实的GraphRAG检索器"""
        from neo4j import GraphDatabase  # 使用同步Driver
        from qdrant_client import QdrantClient
        from src.framework.retrieval.graphrag_retriever import FitnessGraphRAGRetriever

        # 从环境变量读取连接信息
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

        # 创建连接（使用同步Driver）
        neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

        qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)

        # 创建embedder（使用wrapper）
        embedder = SentenceTransformerEmbedder("thenlper/gte-large-zh")

        # 创建检索器
        retriever = FitnessGraphRAGRetriever(
            neo4j_driver=neo4j_driver,
            qdrant_client=qdrant_client,
            embedder=embedder
        )

        yield retriever

        # 清理
        neo4j_driver.close()

    async def test_hybrid_mode_chest_training(self, real_retriever):
        """测试hybrid模式：胸肌训练查询"""
        query = "胸肌训练动作推荐"

        result = await real_retriever.search(
            query=query,
            mode="hybrid",
            top_k=10
        )

        logger.info(f"查询: {query}")
        logger.info(f"结果数量: {result['count']}")
        logger.info(f"检索模式: {result.get('query_type')}")

        # 验证结果
        assert result["count"] > 0, "应该返回至少1个结果"
        assert result["query_type"] == "graphrag_hybrid"
        assert "results" in result

        # 验证结果包含相关内容
        results_text = " ".join([r.get("content", "") for r in result["results"]])
        assert any(keyword in results_text for keyword in ["胸", "卧推", "飞鸟", "夹胸"]), \
            "结果应包含胸肌训练相关内容"

    async def test_hybrid_mode_back_training(self, real_retriever):
        """测试hybrid模式：背部训练查询"""
        query = "背部肌肉锻炼方法"

        result = await real_retriever.search(
            query=query,
            mode="hybrid",
            top_k=10
        )

        logger.info(f"查询: {query}")
        logger.info(f"结果数量: {result['count']}")

        assert result["count"] > 0
        assert result["query_type"] == "graphrag_hybrid"

        # 验证结果相关性
        results_text = " ".join([r.get("content", "") for r in result["results"]])
        assert any(keyword in results_text for keyword in ["背", "引体", "划船", "硬拉"]), \
            "结果应包含背部训练相关内容"

    async def test_hybrid_mode_squat_form(self, real_retriever):
        """测试hybrid模式：深蹲姿势查询"""
        query = "深蹲的正确姿势"

        result = await real_retriever.search(
            query=query,
            mode="hybrid",
            top_k=10
        )

        logger.info(f"查询: {query}")
        logger.info(f"结果数量: {result['count']}")

        assert result["count"] > 0
        assert result["query_type"] == "graphrag_hybrid"

        # 验证结果相关性
        results_text = " ".join([r.get("content", "") for r in result["results"]])
        assert "深蹲" in results_text or "squat" in results_text.lower(), \
            "结果应包含深蹲相关内容"

    async def test_hybrid_vs_vector_comparison(self, real_retriever):
        """对比hybrid模式和vector模式的结果"""
        query = "胸肌训练"

        # Hybrid模式
        hybrid_result = await real_retriever.search(
            query=query,
            mode="hybrid",
            top_k=10
        )

        # Vector模式
        vector_result = await real_retriever.search(
            query=query,
            mode="vector",
            top_k=10
        )

        logger.info(f"Hybrid结果数: {hybrid_result['count']}")
        logger.info(f"Vector结果数: {vector_result['count']}")

        # 验证两种模式都返回结果
        assert hybrid_result["count"] > 0
        assert vector_result["count"] > 0

        # 验证结果类型不同
        assert hybrid_result["query_type"] == "graphrag_hybrid"
        assert vector_result["query_type"] == "graphrag_vector"

        # Hybrid模式应该利用BM25全文搜索，可能返回更相关的结果
        logger.info("✅ Hybrid和Vector模式都正常工作")

    async def test_fulltext_index_working(self, real_retriever):
        """验证fulltext index正常工作"""
        # 使用中文查询（应该触发BM25全文搜索）
        query = "卧推"

        result = await real_retriever.search(
            query=query,
            mode="hybrid",
            top_k=5
        )

        logger.info(f"Fulltext查询: {query}")
        logger.info(f"结果数量: {result['count']}")

        assert result["count"] > 0, "Fulltext index应该返回结果"

        # 验证结果包含查询关键词
        results_text = " ".join([r.get("content", "") for r in result["results"]])
        assert "卧推" in results_text or "bench press" in results_text.lower(), \
            "Fulltext搜索应该返回包含关键词的结果"

        logger.info("✅ Fulltext index正常工作")


# =============================================================================
# 性能基准测试
# =============================================================================

@pytest.mark.integration
@pytest.mark.skip(reason="需要Neo4j 5.18.1+和正确的Qdrant collection配置")
@pytest.mark.asyncio
class TestHybridPerformanceReal:
    """Hybrid模式性能基准测试"""

    @pytest_asyncio.fixture(scope="class")
    async def real_retriever(self):
        """创建真实的GraphRAG检索器"""
        from neo4j import GraphDatabase  # 使用同步Driver
        from qdrant_client import QdrantClient
        from src.framework.retrieval.graphrag_retriever import FitnessGraphRAGRetriever
        from sentence_transformers import SentenceTransformer

        neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

        neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

        qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        embedder = SentenceTransformer("thenlper/gte-large-zh")

        retriever = FitnessGraphRAGRetriever(
            neo4j_driver=neo4j_driver,
            qdrant_client=qdrant_client,
            embedder=embedder
        )

        yield retriever

        neo4j_driver.close()

    async def test_hybrid_response_time(self, real_retriever):
        """测试hybrid模式的响应时间"""
        import time

        query = "胸肌训练动作"

        start = time.time()
        result = await real_retriever.search(
            query=query,
            mode="hybrid",
            top_k=10
        )
        elapsed = time.time() - start

        logger.info(f"Hybrid模式响应时间: {elapsed*1000:.2f}ms")

        # 验证响应时间在合理范围内（<2秒）
        assert elapsed < 2.0, f"响应时间过长: {elapsed:.2f}s"
        assert result["count"] > 0

    async def test_vector_response_time(self, real_retriever):
        """测试vector模式的响应时间"""
        import time

        query = "胸肌训练动作"

        start = time.time()
        result = await real_retriever.search(
            query=query,
            mode="vector",
            top_k=10
        )
        elapsed = time.time() - start

        logger.info(f"Vector模式响应时间: {elapsed*1000:.2f}ms")

        assert elapsed < 2.0
        assert result["count"] > 0

    async def test_performance_comparison(self, real_retriever):
        """对比不同模式的性能"""
        import time

        queries = [
            "胸肌训练",
            "背部锻炼",
            "腿部动作",
            "肩部训练",
            "核心力量"
        ]

        hybrid_times = []
        vector_times = []

        for query in queries:
            # Hybrid模式
            start = time.time()
            await real_retriever.search(query=query, mode="hybrid", top_k=10)
            hybrid_times.append(time.time() - start)

            # Vector模式
            start = time.time()
            await real_retriever.search(query=query, mode="vector", top_k=10)
            vector_times.append(time.time() - start)

        avg_hybrid = sum(hybrid_times) / len(hybrid_times)
        avg_vector = sum(vector_times) / len(vector_times)

        logger.info(f"Hybrid平均响应时间: {avg_hybrid*1000:.2f}ms")
        logger.info(f"Vector平均响应时间: {avg_vector*1000:.2f}ms")

        # 验证性能在合理范围内
        assert avg_hybrid < 2.0
        assert avg_vector < 2.0


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
