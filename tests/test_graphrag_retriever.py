# -*- coding: utf-8 -*-
"""
GraphRAG检索层单元测试

验证FitnessGraphRAGRetriever的核心行为：
- 配置加载
- 降级机制（fallback）
- 结果格式化
- 接口兼容性

版本: v1.0.0
日期: 2026-02-16
Requirements: Phase 1 Task 4
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.framework.retrieval.graphrag_retriever import (
    FitnessGraphRAGRetriever,
    _load_config,
)


# =============================================================================
# 配置加载测试
# =============================================================================

class TestConfigLoading:
    """验证检索配置加载"""

    def test_load_config_returns_dict(self):
        """配置加载应返回字典"""
        config = _load_config()
        assert isinstance(config, dict)

    def test_config_has_default_mode(self):
        """配置应包含default_mode"""
        config = _load_config()
        assert "default_mode" in config
        assert config["default_mode"] in ("hybrid", "vector", "cypher")

    def test_config_has_top_k(self):
        """配置应包含top_k"""
        config = _load_config()
        assert "top_k" in config
        assert isinstance(config["top_k"], int)
        assert config["top_k"] > 0

    def test_config_has_hybrid_weights(self):
        """配置应包含hybrid_weights"""
        config = _load_config()
        assert "hybrid_weights" in config
        weights = config["hybrid_weights"]
        assert "bm25" in weights
        assert "vector" in weights
        # 权重之和应为1.0
        assert abs(weights["bm25"] + weights["vector"] - 1.0) < 0.01


# =============================================================================
# 初始化测试
# =============================================================================

class TestRetrieverInitialization:
    """验证检索器初始化行为"""

    def test_init_without_dependencies(self):
        """无依赖时应正常初始化（延迟加载）"""
        retriever = FitnessGraphRAGRetriever()
        assert retriever._initialized is False
        assert retriever._qdrant_retriever is None
        assert retriever._hybrid_retriever is None

    def test_init_with_fallback_engine(self):
        """带降级引擎时应正常初始化"""
        mock_engine = MagicMock()
        retriever = FitnessGraphRAGRetriever(fallback_engine=mock_engine)
        assert retriever.fallback_engine is mock_engine

    def test_config_loaded_on_init(self):
        """初始化时应加载配置"""
        retriever = FitnessGraphRAGRetriever()
        assert isinstance(retriever.config, dict)
        assert "default_mode" in retriever.config


# =============================================================================
# 降级机制测试
# =============================================================================

class TestFallbackMechanism:
    """验证降级到旧引擎的行为"""

    @pytest.mark.asyncio
    async def test_fallback_when_no_retrievers_available(self):
        """无可用检索器时应降级到旧引擎"""
        mock_fallback = AsyncMock()
        mock_fallback.search.return_value = {
            "results": [{"content": "fallback result"}],
            "count": 1,
            "domain": "fitness",
            "query_type": "three_layer",
        }

        retriever = FitnessGraphRAGRetriever(fallback_engine=mock_fallback)
        result = await retriever.search("深蹲怎么做")

        mock_fallback.search.assert_called_once_with(
            query="深蹲怎么做", domain="fitness", top_k=15
        )
        assert result["count"] == 1
        assert result["results"][0]["content"] == "fallback result"

    @pytest.mark.asyncio
    async def test_empty_result_when_no_engine_available(self):
        """无任何引擎时应返回空结果"""
        retriever = FitnessGraphRAGRetriever()
        result = await retriever.search("深蹲怎么做")

        assert result["results"] == []
        assert result["count"] == 0
        assert result["query_type"] == "none"

    @pytest.mark.asyncio
    async def test_fallback_on_graphrag_exception(self):
        """GraphRAG异常时应降级"""
        mock_fallback = AsyncMock()
        mock_fallback.search.return_value = {
            "results": [],
            "count": 0,
            "domain": "fitness",
            "query_type": "three_layer",
        }

        retriever = FitnessGraphRAGRetriever(fallback_engine=mock_fallback)
        # 模拟已初始化但检索器抛异常
        retriever._initialized = True
        retriever._hybrid_retriever = MagicMock()
        retriever._hybrid_retriever.search.side_effect = RuntimeError("连接失败")

        result = await retriever.search("深蹲怎么做", mode="hybrid")

        # 应该降级到fallback
        mock_fallback.search.assert_called_once()


# =============================================================================
# 结果格式化测试
# =============================================================================

class TestResultFormatting:
    """验证结果格式化"""

    def test_format_result_with_items_attribute(self):
        """有items属性的结果应正确格式化"""
        retriever = FitnessGraphRAGRetriever()

        mock_item = MagicMock()
        mock_item.content = "深蹲是一种复合动作"
        mock_item.metadata = {"exercise_id": 1}
        mock_item.score = 0.95

        mock_result = MagicMock()
        mock_result.items = [mock_item]

        formatted = retriever._format_result(
            mock_result, "深蹲", "fitness", "graphrag_hybrid"
        )

        assert formatted["count"] == 1
        assert formatted["query_type"] == "graphrag_hybrid"
        assert formatted["domain"] == "fitness"
        assert formatted["retriever"] == "neo4j-graphrag-python"
        assert formatted["results"][0]["content"] == "深蹲是一种复合动作"
        assert formatted["results"][0]["score"] == 0.95

    def test_format_result_with_list(self):
        """列表结果应正确格式化"""
        retriever = FitnessGraphRAGRetriever()

        raw_result = [
            {"content": "结果1", "score": 0.9},
            {"content": "结果2", "score": 0.8},
        ]

        formatted = retriever._format_result(
            raw_result, "卧推", "fitness", "graphrag_vector"
        )

        assert formatted["count"] == 2
        assert formatted["results"][0]["content"] == "结果1"

    def test_format_empty_result(self):
        """空结果应返回空列表"""
        retriever = FitnessGraphRAGRetriever()

        mock_result = MagicMock()
        mock_result.items = []

        formatted = retriever._format_result(
            mock_result, "查询", "fitness", "graphrag_hybrid"
        )

        assert formatted["count"] == 0
        assert formatted["results"] == []


# =============================================================================
# 接口兼容性测试
# =============================================================================

class TestInterfaceCompatibility:
    """验证与旧引擎的接口兼容性"""

    @pytest.mark.asyncio
    async def test_search_accepts_query_domain_top_k(self):
        """search()应接受query, domain, top_k参数"""
        mock_fallback = AsyncMock()
        mock_fallback.search.return_value = {
            "results": [], "count": 0, "domain": "fitness", "query_type": "test"
        }

        retriever = FitnessGraphRAGRetriever(fallback_engine=mock_fallback)
        result = await retriever.search(
            query="硬拉", domain="fitness", top_k=10
        )

        assert isinstance(result, dict)
        assert "results" in result
        assert "count" in result
        assert "domain" in result

    @pytest.mark.asyncio
    async def test_search_default_parameters(self):
        """search()默认参数应从配置读取"""
        retriever = FitnessGraphRAGRetriever()
        # 无引擎时直接返回空结果，但参数应正确处理
        result = await retriever.search("测试查询")

        assert result["domain"] == "fitness"  # 默认domain

    @pytest.mark.asyncio
    async def test_search_mode_parameter(self):
        """search()应支持mode参数"""
        mock_fallback = AsyncMock()
        mock_fallback.search.return_value = {
            "results": [], "count": 0, "domain": "fitness", "query_type": "test"
        }

        retriever = FitnessGraphRAGRetriever(fallback_engine=mock_fallback)
        # vector模式
        await retriever.search("测试", mode="vector")
        # hybrid模式
        await retriever.search("测试", mode="hybrid")
        # 都应该正常执行不报错
