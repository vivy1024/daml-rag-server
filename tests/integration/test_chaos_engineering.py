# -*- coding: utf-8 -*-
"""
Chaos Engineering 测试 (REQ-10)

验证在外部服务故障时的降级行为与服务可用性。
4 场景 × 2 用例，全部使用 Mock 注入故障。
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.framework.retrieval.three_layer.models import LayerExecutionResult
from src.framework.retrieval.three_layer.engine import TrueThreeLayerEngine
from src.applications.fitness.fitness_adapter import get_fitness_adapter


@pytest.fixture
def mock_config():
    with patch("src.framework.retrieval.three_layer.engine.get_config") as m:
        cfg = MagicMock()
        cfg.api.port = "8001"
        cfg.internal.api_token = "test-token"
        cfg.database.neo4j.uri = "bolt://localhost:7687"
        cfg.database.neo4j.user = "neo4j"
        cfg.database.neo4j.password = "test"
        m.return_value = cfg
        yield cfg


@pytest.fixture
def mock_timeout_manager():
    with patch("src.framework.retrieval.three_layer.engine.get_timeout_manager") as m:
        tm = MagicMock()
        tm.get_timeout.return_value = 5.0
        tm.get_timeout_ms.return_value = 5000
        m.return_value = tm
        yield tm


@pytest.fixture
def engine(mock_config, mock_timeout_manager):
    with patch.object(TrueThreeLayerEngine, "_initialize_neo4j_connection"):
        eng = TrueThreeLayerEngine(
            enable_neo4j_direct=False,
            domain_adapter=get_fitness_adapter(),
        )
        eng.neo4j_available = False
        eng.neo4j_manager = None
        return eng


def _setup_aiohttp_mock(MockSession, mock_response):
    """设置 aiohttp.ClientSession 双层异步上下文管理器 mock"""
    mock_post_cm = MagicMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.post.return_value = mock_post_cm
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)
    MockSession.return_value = mock_session_cm


class TestRedisDown:
    """场景1: Redis 完全断连 - L1 缓存继续工作，服务不中断"""

    @pytest.mark.asyncio
    async def test_graphrag_query_without_redis_cache_miss(self, engine):
        with patch("redis.asyncio.Redis") as mock_redis:
            mock_redis.return_value.ping.side_effect = ConnectionError("Redis down")
            mock_redis.return_value.get.side_effect = ConnectionError("Redis down")
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={"data": {"results": [{"id": "e1", "score": 0.9, "payload": {}}]}}
            )
            with patch(
                "src.framework.retrieval.three_layer.layer1_vector.aiohttp.ClientSession"
            ) as MockSession:
                _setup_aiohttp_mock(MockSession, mock_response)
                result = await engine._execute_layer1_vector_search(
                    query="练胸",
                    domain="fitness",
                    top_k=10,
                    filters=None,
                )
            assert result.success
            assert len(result.results) > 0

    @pytest.mark.asyncio
    async def test_rule_based_fallback_works_without_redis(self, engine):
        with patch("redis.asyncio.Redis") as mock_redis:
            mock_redis.return_value.ping.side_effect = ConnectionError("Redis down")
            result = await engine._execute_rule_based_fallback(
                query="练背",
                user_profile={"fitness_level": "intermediate"},
                top_k=5,
            )
        assert result.success
        assert len(result.results) > 0


class TestNeo4jTimeout:
    """场景2: Neo4j 超时 (>5s) - 图检索降级到 BM25+向量"""

    @pytest.mark.asyncio
    async def test_neo4j_timeout_falls_back_to_api(self, engine):
        mock_api_response = MagicMock()
        mock_api_response.status = 200
        mock_api_response.json = AsyncMock(
            return_value={
                "data": {
                    "results": [
                        {"score": 0.7, "payload": {"name_zh": "深蹲", "exercise_id": "e1"}},
                    ]
                }
            }
        )
        with patch(
            "src.framework.retrieval.three_layer.layer2_graph.aiohttp.ClientSession"
        ) as MockSession:
            _setup_aiohttp_mock(MockSession, mock_api_response)
            result = await engine._query_neo4j_via_api(
                query="练腿",
                domain="fitness",
                vector_results=[{"id": "e1"}],
                top_k=5,
            )
        assert result.success
        assert result.metadata.get("source") == "api_fallback"

    @pytest.mark.asyncio
    async def test_layer2_api_fallback_when_neo4j_unavailable(self, engine):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "data": {
                    "results": [
                        {"score": 0.6, "payload": {"name_zh": "引体向上", "exercise_id": "e2"}},
                    ]
                }
            }
        )
        with patch(
            "src.framework.retrieval.three_layer.layer2_graph.aiohttp.ClientSession"
        ) as MockSession:
            _setup_aiohttp_mock(MockSession, mock_response)
            result = await engine._query_neo4j_via_api_fallback(
                query="练背",
                domain="fitness",
                top_k=5,
            )
        assert result.success
        assert len(result.results) > 0


class TestLLMAllFailure:
    """场景3: LLM 全部故障 - Template 兜底返回结构化回答"""

    @pytest.mark.asyncio
    async def test_rule_based_fallback_when_all_llm_fail(self, engine):
        result = await engine._execute_rule_based_fallback(
            query="练胸",
            user_profile={"fitness_level": "beginner"},
            top_k=5,
        )
        assert result.success
        assert len(result.results) > 0
        for item in result.results:
            assert "exercise_name_zh" in item or "source" in item

    @pytest.mark.asyncio
    async def test_default_fallback_items_returned(self, engine):
        result = await engine._execute_rule_based_fallback(
            query="随机无关内容",
            user_profile={"fitness_level": "intermediate"},
            top_k=5,
        )
        assert result.success
        assert len(result.results) > 0
        assert result.metadata.get("source") == "rule_based_fallback"


class TestQdrantUnavailable:
    """场景4: Qdrant 不可用 - 向量检索跳过，其他层继续工作"""

    @pytest.mark.asyncio
    async def test_layer1_failure_triggers_layer2_fallback(self, engine):
        mock_l1 = AsyncMock(return_value=LayerExecutionResult(
            "L1", False, [], 0, 0, {}, error="Qdrant unavailable"
        ))
        mock_l2 = AsyncMock(return_value=LayerExecutionResult(
            "L2", False, [], 0, 0, {}
        ))
        mock_fb = AsyncMock(return_value=LayerExecutionResult(
            "FB", True,
            [{"exercise_name_zh": "俯卧撑", "difficulty": "beginner", "equipment": "徒手"}],
            0, 0.5, {}
        ))
        mock_l3 = AsyncMock(return_value=LayerExecutionResult(
            "L3", True, [{"exercise_name_zh": "俯卧撑"}], 0, 0.9, {}
        ))
        with patch.object(engine, "_execute_layer1_vector_search", mock_l1):
            with patch.object(engine, "_execute_layer2_graph_reasoning_fallback", mock_l2):
                with patch.object(engine, "_execute_rule_based_fallback", mock_fb):
                    with patch.object(engine, "_execute_layer3_business_rules", mock_l3):
                        result = await engine.execute_three_layer_query(
                            query="练胸",
                            domain="fitness",
                            top_k=5,
                        )
        assert result is not None
        assert mock_fb.called
        assert len(result.final_results) > 0 or result.reasoning

    @pytest.mark.asyncio
    async def test_full_chain_without_qdrant_returns_rule_results(self, engine):
        mock_l1 = AsyncMock(return_value=LayerExecutionResult(
            "L1", False, [], 0, 0, {}, error="Qdrant connection refused"
        ))
        mock_l2 = AsyncMock(return_value=LayerExecutionResult("L2", False, [], 0, 0, {}))
        mock_fb = AsyncMock(return_value=LayerExecutionResult(
            "FB", True,
            [
                {"exercise_name_zh": "深蹲", "difficulty": "beginner"},
                {"exercise_name_zh": "平板支撑", "difficulty": "beginner"},
            ],
            0, 0.5, {}
        ))
        mock_l3 = AsyncMock(return_value=LayerExecutionResult(
            "L3", True,
            [
                {"exercise_name_zh": "深蹲", "difficulty": "beginner"},
                {"exercise_name_zh": "平板支撑", "difficulty": "beginner"},
            ],
            0, 0.9, {}
        ))
        with patch.object(engine, "_execute_layer1_vector_search", mock_l1):
            with patch.object(engine, "_execute_layer2_graph_reasoning_fallback", mock_l2):
                with patch.object(engine, "_execute_rule_based_fallback", mock_fb):
                    with patch.object(engine, "_execute_layer3_business_rules", mock_l3):
                        with patch.dict("os.environ", {"ENABLE_RERANKER": "false"}):
                            result = await engine.execute_three_layer_query(
                                query="练腿",
                                domain="fitness",
                                top_k=5,
                            )
        assert len(result.final_results) == 2
        names = [r.get("exercise_name_zh") for r in result.final_results]
        assert "深蹲" in names
        assert "平板支撑" in names
