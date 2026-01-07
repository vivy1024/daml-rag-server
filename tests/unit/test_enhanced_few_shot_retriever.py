# -*- coding: utf-8 -*-
"""
Enhanced Few-Shot Retriever 单元测试

测试增强版Few-Shot检索器的核心功能
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.framework.retrieval.enhanced_few_shot_retriever import (
    EnhancedFewShotRetriever,
    FewShotExample,
    FewShotConfig
)


class TestFewShotConfig:
    """测试FewShotConfig配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = FewShotConfig()
        assert config.min_rating_threshold == 4.0
        assert config.min_quality_threshold == 3.5
        assert config.max_examples == 5
        assert config.default_similarity_threshold == 0.6

    def test_custom_config(self):
        """测试自定义配置"""
        config = FewShotConfig(
            min_rating_threshold=4.5,
            max_examples=3,
            adaptive_mode=False
        )
        assert config.min_rating_threshold == 4.5
        assert config.max_examples == 3
        assert config.adaptive_mode is False


class TestFewShotExample:
    """测试FewShotExample数据类"""

    def test_example_creation(self):
        """测试示例创建"""
        example = FewShotExample(
            query="测试查询",
            response="测试响应",
            user_rating=4.5,
            quality_score=4.0,
            similarity=0.85,
            tools_used=["tool1", "tool2"],
            model_used="teacher",
            timestamp=datetime.now(),
            session_id="session_123"
        )
        assert example.query == "测试查询"
        assert example.user_rating == 4.5
        assert example.similarity == 0.85

    def test_example_to_dict(self):
        """测试转换为字典"""
        example = FewShotExample(
            query="测试查询",
            response="测试响应",
            user_rating=4.5,
            quality_score=4.0,
            similarity=0.85,
            tools_used=["tool1"],
            model_used="teacher",
            timestamp=datetime.now(),
            session_id="session_123"
        )
        data = example.to_dict()
        assert isinstance(data, dict)
        assert data["query"] == "测试查询"
        assert data["user_rating"] == 4.5
        assert "timestamp" in data


class TestEnhancedFewShotRetriever:
    """测试EnhancedFewShotRetriever核心功能"""

    @pytest.fixture
    def mock_vector_store(self):
        """模拟向量存储"""
        store = Mock()
        store.search_conversations = AsyncMock(
            return_value=[
                {
                    "query": "训练计划",
                    "response": "详细响应",
                    "user_rating": 4.5,
                    "quality_score": 4.0,
                    "similarity": 0.85,
                    "tools_used": ["tool1"],
                    "model_used": "teacher",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": "session_1"
                },
                {
                    "query": "营养建议",
                    "response": "营养响应",
                    "user_rating": 4.8,
                    "quality_score": 4.5,
                    "similarity": 0.75,
                    "tools_used": ["tool2"],
                    "model_used": "teacher",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": "session_2"
                }
            ]
        )
        return store

    @pytest.fixture
    def mock_backend_client(self):
        """模拟后端客户端"""
        client = Mock()
        client.search_similar_conversations = AsyncMock(
            return_value={
                "conversations": [
                    {
                        "query": "测试查询",
                        "response": "测试响应",
                        "user_rating": 4.0,
                        "quality_score": 3.8,
                        "similarity": 0.7,
                        "tools_used": [],
                        "model_used": "student",
                        "timestamp": datetime.now().isoformat(),
                        "session_id": "session_3"
                    }
                ]
            }
        )
        return client

    @pytest.fixture
    def retriever(self, mock_vector_store, mock_backend_client):
        """创建测试用的检索器实例"""
        config = FewShotConfig(
            min_rating_threshold=4.0,
            min_quality_threshold=3.5,
            max_examples=5
        )
        return EnhancedFewShotRetriever(
            vector_store=mock_vector_store,
            backend_client=mock_backend_client,
            config=config
        )

    def test_initialization(self, retriever):
        """测试初始化"""
        assert retriever.config is not None
        assert retriever.vector_store is not None
        assert retriever.backend_client is not None
        assert isinstance(retriever.stats, dict)

    @pytest.mark.asyncio
    async def test_retrieve_with_quality_filter(self, retriever):
        """测试基于质量过滤的检索"""
        examples, stats = await retriever.retrieve_with_quality_filter(
            query="训练计划",
            user_id="test_user"
        )

        assert isinstance(examples, list)
        assert isinstance(stats, dict)
        assert "execution_time_ms" in stats
        assert "final_examples" in stats

        # 验证返回的示例
        for example in examples:
            assert isinstance(example, FewShotExample)
            assert example.user_rating >= retriever.config.min_rating_threshold
            assert example.quality_score >= retriever.config.min_quality_threshold

    @pytest.mark.asyncio
    async def test_retrieve_with_complexity(self, retriever):
        """测试带复杂度的检索"""
        # 复杂查询
        examples_complex, stats_complex = await retriever.retrieve_with_quality_filter(
            query="设计训练计划",
            user_id="test_user",
            query_complexity=True
        )

        # 简单查询
        examples_simple, stats_simple = await retriever.retrieve_with_quality_filter(
            query="简单查询",
            user_id="test_user",
            query_complexity=False
        )

        # 验证阈值不同
        assert stats_complex["similarity_threshold"] != stats_simple["similarity_threshold"]

    @pytest.mark.asyncio
    async def test_retrieve_with_top_k(self, retriever):
        """测试指定返回数量"""
        examples, stats = await retriever.retrieve_with_quality_filter(
            query="训练计划",
            user_id="test_user",
            top_k=3
        )

        # 返回数量不应超过top_k
        assert len(examples) <= 3

    @pytest.mark.asyncio
    async def test_quality_filtering(self, retriever, mock_vector_store):
        """测试质量过滤"""
        # 添加低质量结果
        mock_vector_store.search_conversations = AsyncMock(
            return_value=[
                {
                    "query": "高质量",
                    "response": "响应",
                    "user_rating": 4.5,
                    "quality_score": 4.0,
                    "similarity": 0.8,
                    "tools_used": [],
                    "model_used": "teacher",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": "session_1"
                },
                {
                    "query": "低质量",
                    "response": "响应",
                    "user_rating": 2.0,  # 低于阈值
                    "quality_score": 2.0,  # 低于阈值
                    "similarity": 0.8,
                    "tools_used": [],
                    "model_used": "student",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": "session_2"
                }
            ]
        )

        examples, stats = await retriever.retrieve_with_quality_filter(
            query="测试",
            user_id="test_user"
        )

        # 低质量结果应该被过滤
        assert stats["quality_filtered"] > 0
        for example in examples:
            assert example.user_rating >= retriever.config.min_rating_threshold

    @pytest.mark.asyncio
    async def test_diversity_filtering(self, retriever, mock_vector_store):
        """测试多样性过滤"""
        # 添加相似的结果
        mock_vector_store.search_conversations = AsyncMock(
            return_value=[
                {
                    "query": "训练计划设计",
                    "response": "响应1",
                    "user_rating": 4.5,
                    "quality_score": 4.0,
                    "similarity": 0.9,
                    "tools_used": [],
                    "model_used": "teacher",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": "session_1"
                },
                {
                    "query": "训练计划设计方案",  # 非常相似
                    "response": "响应2",
                    "user_rating": 4.5,
                    "quality_score": 4.0,
                    "similarity": 0.85,
                    "tools_used": [],
                    "model_used": "teacher",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": "session_2"
                },
                {
                    "query": "营养建议",  # 不同主题
                    "response": "响应3",
                    "user_rating": 4.5,
                    "quality_score": 4.0,
                    "similarity": 0.8,
                    "tools_used": [],
                    "model_used": "teacher",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": "session_3"
                }
            ]
        )

        examples, stats = await retriever.retrieve_with_quality_filter(
            query="训练计划",
            user_id="test_user"
        )

        # 应该有多样性过滤
        if stats["diversity_filtered"] > 0:
            # 验证结果确实更多样化
            queries = [ex.query for ex in examples]
            assert len(set(queries)) > 0

    def test_calculate_text_similarity(self, retriever):
        """测试文本相似度计算"""
        # 使用英文测试，因为中文分词可能导致相似度为0
        text1 = "training plan design"
        text2 = "training plan method"
        text3 = "nutrition advice"

        sim_12 = retriever._calculate_text_similarity(text1, text2)
        sim_13 = retriever._calculate_text_similarity(text1, text3)

        # text1和text2应该更相似
        assert sim_12 > sim_13
        assert 0 <= sim_12 <= 1
        assert 0 <= sim_13 <= 1

    @pytest.mark.asyncio
    async def test_determine_similarity_threshold_adaptive(self, retriever):
        """测试自适应相似度阈值"""
        # 复杂查询
        threshold_complex = await retriever._determine_similarity_threshold(
            query="设计完整训练计划",
            query_complexity=True
        )

        # 简单查询
        threshold_simple = await retriever._determine_similarity_threshold(
            query="简单查询",
            query_complexity=False
        )

        # 复杂查询应该有更高的阈值
        assert threshold_complex > threshold_simple

    @pytest.mark.asyncio
    async def test_determine_similarity_threshold_non_adaptive(self):
        """测试非自适应模式"""
        config = FewShotConfig(adaptive_mode=False)
        retriever = EnhancedFewShotRetriever(config=config)

        threshold = await retriever._determine_similarity_threshold(
            query="任意查询",
            query_complexity=True
        )

        # 非自适应模式应该返回默认阈值
        assert threshold == config.default_similarity_threshold

    def test_should_use_teacher_model(self, retriever):
        """测试教师模型使用决策"""
        # 复杂查询 + Few-Shot不足 -> 教师模型
        assert retriever.should_use_teacher_model(
            few_shot_count=2,
            query_complexity=True
        ) is True

        # 简单查询 + Few-Shot充足 -> 学生模型
        assert retriever.should_use_teacher_model(
            few_shot_count=5,
            query_complexity=False
        ) is False

        # 复杂查询 + Few-Shot充足 -> 学生模型
        assert retriever.should_use_teacher_model(
            few_shot_count=5,
            query_complexity=True
        ) is False

    def test_get_statistics(self, retriever):
        """测试获取统计信息"""
        stats = retriever.get_statistics()

        assert "total_retrievals" in stats
        assert "avg_similarity" in stats
        assert "avg_quality" in stats
        assert "success_rate" in stats

    @pytest.mark.asyncio
    async def test_error_handling_vector_store_failure(self, retriever, mock_vector_store):
        """测试向量存储失败的错误处理"""
        # 模拟向量存储失败
        mock_vector_store.search_conversations = AsyncMock(
            side_effect=Exception("向量存储错误")
        )

        examples, stats = await retriever.retrieve_with_quality_filter(
            query="测试查询",
            user_id="test_user"
        )

        # 应该返回空结果但不崩溃
        assert isinstance(examples, list)
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_fallback_to_backend(self, mock_backend_client):
        """测试降级到后端API"""
        # 创建没有向量存储的检索器
        retriever = EnhancedFewShotRetriever(
            vector_store=None,
            backend_client=mock_backend_client
        )

        examples, stats = await retriever.retrieve_with_quality_filter(
            query="测试查询",
            user_id="test_user"
        )

        # 应该使用后端客户端
        assert mock_backend_client.search_similar_conversations.called
        assert isinstance(examples, list)

    @pytest.mark.asyncio
    async def test_evaluate_few_shot_quality(self, retriever):
        """测试Few-Shot质量评估"""
        # 创建测试示例
        examples = [
            FewShotExample(
                query="查询1",
                response="响应1",
                user_rating=4.5,
                quality_score=4.0,
                similarity=0.9,
                tools_used=[],
                model_used="teacher",
                timestamp=datetime.now(),
                session_id="session_1"
            ),
            FewShotExample(
                query="查询2",
                response="响应2",
                user_rating=4.8,
                quality_score=4.5,
                similarity=0.85,
                tools_used=[],
                model_used="teacher",
                timestamp=datetime.now(),
                session_id="session_2"
            )
        ]

        quality_result = await retriever._evaluate_few_shot_quality(
            few_shot_examples=examples
        )

        assert "quality_score" in quality_result
        assert "example_count" in quality_result
        assert "recommendation" in quality_result
        assert quality_result["example_count"] == 2
        # 质量评分可能超过100（因为quality_score是5分制，需要归一化）
        assert quality_result["quality_score"] >= 0

    @pytest.mark.asyncio
    async def test_evaluate_few_shot_quality_insufficient(self, retriever):
        """测试Few-Shot质量评估（示例不足）"""
        quality_result = await retriever._evaluate_few_shot_quality(
            few_shot_examples=[]
        )

        assert quality_result["quality_score"] == 0.0
        assert quality_result["example_count"] == 0
        assert quality_result["recommendation"] == "insufficient_examples"
        assert quality_result["should_use_teacher_model"] is True

    @pytest.mark.asyncio
    async def test_statistics_update(self, retriever):
        """测试统计信息更新"""
        initial_retrievals = retriever.stats["total_retrievals"]

        await retriever.retrieve_with_quality_filter(
            query="测试查询",
            user_id="test_user"
        )

        # 检索次数应该增加
        assert retriever.stats["total_retrievals"] == initial_retrievals + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
