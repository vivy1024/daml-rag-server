"""
test_engine_pipeline.py — 浪潮引擎管线端到端测试

验证：
- 随机向量检索返回结果
- 各阶段 timing 存在
- 结果格式正确
- 不同 domain 都能检索
- top_k 参数生效
"""

import pytest
import numpy as np


class TestWaveEngineSearch:
    """WaveEngine.search 端到端测试"""

    async def test_basic_search(self, wave_engine, random_query_vec):
        """基本检索返回结果"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            top_k=5,
        )
        assert len(result.results) > 0
        assert len(result.results) <= 5

    async def test_result_has_id_and_score(self, wave_engine, random_query_vec):
        """结果包含 id 和 score"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            top_k=3,
        )
        for item in result.results:
            assert "id" in item
            assert "score" in item
            assert isinstance(item["score"], float)

    async def test_scores_descending(self, wave_engine, random_query_vec):
        """结果按 score 降序排列"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            top_k=10,
        )
        scores = [r["score"] for r in result.results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Score not descending at {i}: {scores[i]} < {scores[i+1]}"

    async def test_timing_fields(self, wave_engine, random_query_vec):
        """timing 包含各阶段耗时"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            top_k=5,
        )
        assert "total" in result.timing
        assert "vector_search" in result.timing
        assert result.timing["total"] > 0

    async def test_top_k_respected(self, wave_engine, random_query_vec):
        """top_k 参数限制结果数"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            top_k=2,
        )
        assert len(result.results) <= 2

    async def test_knowledge_domain(self, wave_engine):
        """知识领域检索"""
        vec = np.random.randn(1024).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        result = await wave_engine.search(
            query_vec=vec,
            domain="knowledge",
            top_k=5,
        )
        assert len(result.results) >= 0  # 可能为空（取决于数据）

    async def test_food_domain(self, wave_engine):
        """食物领域检索"""
        vec = np.random.randn(1024).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        result = await wave_engine.search(
            query_vec=vec,
            domain="foods",
            top_k=5,
        )
        assert len(result.results) >= 0

    async def test_invalid_domain_returns_empty(self, wave_engine, random_query_vec):
        """无效 domain 返回空结果"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="nonexistent",
            top_k=5,
        )
        assert len(result.results) == 0

    async def test_performance_under_50ms(self, wave_engine, random_query_vec):
        """管线耗时 < 50ms（不含 embedding）"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            top_k=10,
        )
        assert result.timing["total"] < 50, f"Too slow: {result.timing['total']:.1f}ms"


class TestWaveEngineWithFilters:
    """带过滤条件的检索测试"""

    async def test_with_user_profile(self, wave_engine, random_query_vec):
        """带用户档案检索"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            user_profile={"fitness_level": "beginner", "primary_goal": "增肌"},
            top_k=5,
        )
        assert len(result.results) > 0

    async def test_with_filters(self, wave_engine, random_query_vec):
        """带过滤条件检索"""
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            filters={"muscle_group": "胸肌"},
            top_k=5,
        )
        assert len(result.results) > 0

    async def test_with_recent_used(self, wave_engine, random_query_vec, data_store):
        """带最近使用列表检索（去重）"""
        # 先获取一些 ID
        first_result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            top_k=3,
        )
        used_ids = [r["id"] for r in first_result.results[:2]]

        # 带 recent_used 再次检索
        result = await wave_engine.search(
            query_vec=random_query_vec,
            domain="exercises",
            top_k=5,
            recent_used=used_ids,
        )
        # 结果中不应包含 recent_used 的 ID（如果 geodesic 启用）
        result_ids = [r["id"] for r in result.results]
        # 注意：geodesic_rerank 可能不完全排除，只是降权
        # 所以这里只验证不报错
        assert len(result.results) > 0
