"""
test_search_quality.py — 检索质量回归测试

验证语义相关性：给定查询，结果中应包含相关动作。
使用真实 Embedding（如果模型可用），否则跳过。

这些测试是"金标准"回归测试，确保引擎升级不会降低质量。
"""

import json
import pytest

# 标记：需要 Embedding 模型
needs_embedding = pytest.mark.skipif(
    True,  # 默认跳过，手动运行时改为 False
    reason="Requires embedding model loaded (slow, ~8s first call)"
)


class TestSearchRelevance:
    """检索相关性测试（需要 Embedding 模型）"""

    @needs_embedding
    async def test_chest_query_returns_chest_exercises(self):
        """查询'练胸'应返回胸肌动作"""
        from src_v2.server import call_tool
        result = await call_tool("search_exercises", {"query_text": "练胸的动作", "top_k": 5})
        data = json.loads(result[0].text)
        exercises = data["exercises"]

        # 至少 3/5 的结果应该是胸肌相关
        chest_count = sum(
            1 for ex in exercises
            if "胸" in str(ex.get("muscles_primary_zh", []))
        )
        assert chest_count >= 3, f"Only {chest_count}/5 chest exercises for '练胸'"

    @needs_embedding
    async def test_squat_query_returns_leg_exercises(self):
        """查询'深蹲'应返回腿部动作"""
        from src_v2.server import call_tool
        result = await call_tool("search_exercises", {"query_text": "深蹲", "top_k": 5})
        data = json.loads(result[0].text)
        exercises = data["exercises"]

        # 至少有一个结果名称包含"深蹲"
        squat_found = any("深蹲" in ex.get("name_zh", "") for ex in exercises)
        assert squat_found, f"No squat exercise found for '深蹲'"

    @needs_embedding
    async def test_back_query_returns_back_exercises(self):
        """查询'练背'应返回背部动作"""
        from src_v2.server import call_tool
        result = await call_tool("search_exercises", {"query_text": "练背的动作", "top_k": 5})
        data = json.loads(result[0].text)
        exercises = data["exercises"]

        back_count = sum(
            1 for ex in exercises
            if "背" in str(ex.get("muscles_primary_zh", []))
        )
        assert back_count >= 2, f"Only {back_count}/5 back exercises for '练背'"


class TestSearchPerformance:
    """检索性能测试（不需要 Embedding）"""

    async def test_engine_latency_under_50ms(self, wave_engine, random_query_vec):
        """引擎管线延迟 < 50ms（排除首次冷启动）"""
        import time
        # warmup run
        await wave_engine.search(query_vec=random_query_vec, domain="exercises", top_k=10)

        times = []
        for _ in range(10):
            t0 = time.time()
            await wave_engine.search(query_vec=random_query_vec, domain="exercises", top_k=10)
            times.append((time.time() - t0) * 1000)

        avg = sum(times) / len(times)
        p95 = sorted(times)[int(len(times) * 0.95)]
        assert avg < 50, f"Average latency {avg:.1f}ms > 50ms"
        assert p95 < 200, f"P95 latency {p95:.1f}ms > 200ms"

    async def test_concurrent_searches(self, wave_engine):
        """并发检索不报错"""
        import asyncio
        import numpy as np

        async def single_search():
            vec = np.random.randn(1024).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            return await wave_engine.search(query_vec=vec, domain="exercises", top_k=5)

        results = await asyncio.gather(*[single_search() for _ in range(10)])
        assert all(len(r.results) > 0 for r in results)
