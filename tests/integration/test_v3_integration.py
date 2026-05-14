"""
DAML-RAG v3 浪潮引擎 — 集成测试

在容器内运行，测试完整的搜索管线。
运行方式: docker exec fitness_daml_rag python -m pytest /app/tests/integration/test_v3_integration.py -v
"""

import os
import sys
import time
import asyncio
import pytest

os.environ["DATA_DIR"] = "/app/data/v3"
os.environ.setdefault("EMBEDDING_API_KEY", "test")

sys.path.insert(0, "/app")


@pytest.fixture(scope="module")
def engine_stack():
    """初始化完整引擎栈（模块级别，只加载一次）"""
    # 重置 config 单例以确保使用正确的 DATA_DIR
    import src_v2.config as cfg_mod
    cfg_mod._config = None

    from src_v2.config import get_config
    from src_v2.data.loader import DataStore
    from src_v2.engine.wave_engine import WaveEngine
    from src_v2.rules.safety_engine import SafetyEngine
    from src_v2.tools.embedding import warmup

    cfg = get_config()
    data = DataStore(config=cfg.data)
    asyncio.get_event_loop().run_until_complete(data.load())
    engine = WaveEngine(data_store=data, config=cfg.engine)
    safety = SafetyEngine(graph_store=data.graph, metadata_store=data.metadata)
    warmup()

    return {
        "config": cfg,
        "data": data,
        "engine": engine,
        "safety": safety,
    }


class TestDataLoading:
    """数据加载完整性测试"""

    def test_exercise_count(self, engine_stack):
        data = engine_stack["data"]
        assert data.exercise_index.count == 1790

    def test_knowledge_count(self, engine_stack):
        data = engine_stack["data"]
        assert data.knowledge_index.count == 4062

    def test_food_count(self, engine_stack):
        data = engine_stack["data"]
        assert data.food_index.count == 1851

    def test_graph_loaded(self, engine_stack):
        data = engine_stack["data"]
        assert data.graph.node_count >= 4000

    def test_vector_dimension(self, engine_stack):
        data = engine_stack["data"]
        vec = data.exercise_index.get_vector(0)
        assert vec.shape == (1024,)


class TestSearchExercises:
    """动作搜索端到端测试"""

    def test_chest_exercises(self, engine_stack):
        from src_v2.tools.search_exercises import search_exercises

        result = asyncio.get_event_loop().run_until_complete(
            search_exercises(
                query_text="练胸的动作",
                user_profile={"fitness_level": "intermediate"},
                top_k=10,
                wave_engine=engine_stack["engine"],
                safety_engine=engine_stack["safety"],
            )
        )

        assert result["total"] >= 5
        # 前 5 个结果应该包含胸肌训练动作
        names = [ex.get("name_zh", "") for ex in result["exercises"][:5]]
        chest_keywords = ["卧推", "飞鸟", "俯卧撑", "夹胸", "胸"]
        has_chest = any(
            any(kw in name for kw in chest_keywords)
            for name in names
        )
        assert has_chest, f"前5结果中没有胸部训练动作: {names}"

    def test_back_exercises(self, engine_stack):
        from src_v2.tools.search_exercises import search_exercises

        result = asyncio.get_event_loop().run_until_complete(
            search_exercises(
                query_text="背部训练",
                user_profile={"fitness_level": "beginner"},
                top_k=5,
                wave_engine=engine_stack["engine"],
                safety_engine=engine_stack["safety"],
            )
        )

        assert result["total"] >= 3
        names = [ex.get("name_zh", "") for ex in result["exercises"][:5]]
        back_keywords = ["划船", "引体", "下拉", "背", "超人"]
        has_back = any(
            any(kw in name for kw in back_keywords)
            for name in names
        )
        assert has_back, f"前5结果中没有背部训练动作: {names}"

    def test_latency_under_500ms(self, engine_stack):
        """端到端延迟应 < 500ms（含 embedding）"""
        from src_v2.tools.search_exercises import search_exercises

        t0 = time.time()
        asyncio.get_event_loop().run_until_complete(
            search_exercises(
                query_text="深蹲",
                user_profile={"fitness_level": "intermediate"},
                top_k=5,
                wave_engine=engine_stack["engine"],
                safety_engine=engine_stack["safety"],
            )
        )
        elapsed = (time.time() - t0) * 1000
        assert elapsed < 500, f"延迟 {elapsed:.0f}ms 超过 500ms 阈值"

    def test_result_has_required_fields(self, engine_stack):
        from src_v2.tools.search_exercises import search_exercises

        result = asyncio.get_event_loop().run_until_complete(
            search_exercises(
                query_text="哑铃训练",
                user_profile={"fitness_level": "intermediate"},
                top_k=3,
                wave_engine=engine_stack["engine"],
                safety_engine=engine_stack["safety"],
            )
        )

        for ex in result["exercises"]:
            assert "id" in ex
            assert "score" in ex
            assert "name_zh" in ex
            assert ex["score"] > 0


class TestSearchKnowledge:
    """知识搜索测试"""

    def test_training_knowledge(self, engine_stack):
        from src_v2.tools.knowledge_and_food import search_knowledge

        result = asyncio.get_event_loop().run_until_complete(
            search_knowledge(
                query_text="渐进超负荷原则",
                top_k=5,
                wave_engine=engine_stack["engine"],
            )
        )

        assert result["total"] >= 3
        # 应该返回训练相关的知识
        titles = [r["title"] for r in result["results"]]
        assert any("训练" in t or "力量" in t for t in titles), f"结果不相关: {titles}"

    def test_knowledge_has_title(self, engine_stack):
        from src_v2.tools.knowledge_and_food import search_knowledge

        result = asyncio.get_event_loop().run_until_complete(
            search_knowledge(
                query_text="肌肉恢复",
                top_k=3,
                wave_engine=engine_stack["engine"],
            )
        )

        for item in result["results"]:
            assert item["title"], "知识结果缺少 title"
            assert item["score"] > 0


class TestSearchFoods:
    """食物搜索测试"""

    def test_food_search(self, engine_stack):
        from src_v2.tools.knowledge_and_food import search_foods

        result = asyncio.get_event_loop().run_until_complete(
            search_foods(
                query_text="高蛋白食物",
                top_k=5,
                wave_engine=engine_stack["engine"],
            )
        )

        assert result["total"] >= 3
        for food in result["foods"]:
            assert food["name"], "食物缺少名称"
            assert food["protein"] >= 0

    def test_food_latency(self, engine_stack):
        from src_v2.tools.knowledge_and_food import search_foods

        t0 = time.time()
        asyncio.get_event_loop().run_until_complete(
            search_foods(
                query_text="鸡胸肉",
                top_k=5,
                wave_engine=engine_stack["engine"],
            )
        )
        elapsed = (time.time() - t0) * 1000
        assert elapsed < 500, f"食物搜索延迟 {elapsed:.0f}ms 超过 500ms"


class TestCalculators:
    """计算工具集成测试"""

    def test_tdee_realistic(self):
        from src_v2.tools.calculators import calculate_tdee
        # 典型中国男性
        result = calculate_tdee("male", 25, 70, 175, "moderate", "maintain")
        assert 2200 < result["tdee"] < 2800
        assert result["macros"]["protein_g"] > 100

    def test_1rm_bench(self):
        from src_v2.tools.calculators import calculate_1rm
        # 卧推 80kg × 8 次
        result = calculate_1rm(80, 8)
        assert 95 < result["estimated_1rm"] < 105

    def test_training_split_valid(self):
        from src_v2.tools.calculators import design_training_split
        for days in [3, 4, 5, 6]:
            result = design_training_split(days)
            assert result["days_per_week"] == days
            assert len(result["schedule"]) >= days


class TestPerformance:
    """性能基准测试"""

    @pytest.mark.skipif(
        os.environ.get("RUN_COLD_START") != "1",
        reason="冷启动测试需要独立进程，设置 RUN_COLD_START=1 运行"
    )
    def test_cold_start_under_8s(self):
        """冷启动应 < 8 秒（需独立运行，避免内存竞争）"""
        from src_v2.config import get_config
        from src_v2.data.loader import DataStore

        cfg = get_config()
        data = DataStore(config=cfg.data)

        t0 = time.time()
        asyncio.get_event_loop().run_until_complete(data.load())
        elapsed = time.time() - t0

        assert elapsed < 8.0, f"冷启动 {elapsed:.2f}s 超过 8s 阈值"

    def test_batch_search_throughput(self, engine_stack):
        """批量搜索吞吐量（纯引擎，不含 embedding）"""
        from src_v2.tools.embedding import encode_query
        import numpy as np

        queries = ["深蹲", "卧推", "硬拉", "引体向上", "肩推"]
        # 预先编码，不计入引擎延迟
        vecs = [encode_query(q) for q in queries]

        t0 = time.time()
        for vec in vecs:
            asyncio.get_event_loop().run_until_complete(
                engine_stack["engine"].search(query_vec=vec, domain="exercises", top_k=10)
            )
        elapsed = (time.time() - t0) * 1000

        avg_ms = elapsed / len(queries)
        # 纯引擎搜索（含融合+重排）应 < 50ms
        # 如果含 PCA/SVD 等预计算步骤，放宽到 100ms
        assert avg_ms < 100, f"平均引擎延迟 {avg_ms:.1f}ms 超过 100ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
