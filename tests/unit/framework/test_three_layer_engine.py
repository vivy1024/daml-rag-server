# -*- coding: utf-8 -*-
"""
三层检索引擎单元测试 (REQ-9)

测试 TrueThreeLayerEngine 的 Layer1 向量、Layer2 图、Layer3 规则、
结果融合、超时降级及空查询处理。全部使用 Mock，不依赖真实服务。
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.framework.retrieval.three_layer.models import (
    LayerExecutionResult,
    ThreeLayerResult,
)
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


class TestLayer1Vector:
    """Layer 1 向量检索测试"""

    @pytest.mark.asyncio
    async def test_layer1_success(self, engine):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "data": {
                    "results": [
                        {"id": "e1", "score": 0.9, "payload": {"name_zh": "俯卧撑"}},
                        {"id": "e2", "score": 0.85, "payload": {"name_zh": "哑铃卧推"}},
                    ]
                }
            }
        )

        with patch(
            "src.framework.retrieval.three_layer.layer1_vector.aiohttp.ClientSession"
        ) as MockSession:
            mock_post_cm = MagicMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_cm.__aexit__ = AsyncMock(return_value=False)

            mock_session = MagicMock()
            mock_session.post.return_value = mock_post_cm

            mock_session_cm = MagicMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)
            MockSession.return_value = mock_session_cm

            result = await engine._execute_layer1_vector_search(
                query="练胸",
                domain="fitness",
                top_k=10,
                filters=None,
            )
        assert result.success
        assert len(result.results) == 2
        assert result.layer_name == "Layer1-Vector"

    @pytest.mark.asyncio
    async def test_layer1_failure_api_error(self, engine):
        mock_response = MagicMock()
        mock_response.status = 500

        with patch(
            "src.framework.retrieval.three_layer.layer1_vector.aiohttp.ClientSession"
        ) as MockSession:
            mock_post_cm = MagicMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_cm.__aexit__ = AsyncMock(return_value=False)

            mock_session = MagicMock()
            mock_session.post.return_value = mock_post_cm

            mock_session_cm = MagicMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)
            MockSession.return_value = mock_session_cm

            result = await engine._execute_layer1_vector_search(
                query="练胸",
                domain="fitness",
                top_k=10,
                filters=None,
            )
        assert not result.success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_layer1_timeout(self, engine):
        import asyncio

        with patch(
            "src.framework.retrieval.three_layer.layer1_vector.aiohttp.ClientSession"
        ) as MockSession:
            mock_post_cm = MagicMock()
            mock_post_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_post_cm.__aexit__ = AsyncMock(return_value=False)

            mock_session = MagicMock()
            mock_session.post.return_value = mock_post_cm

            mock_session_cm = MagicMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)
            MockSession.return_value = mock_session_cm

            result = await engine._execute_layer1_vector_search(
                query="练胸",
                domain="fitness",
                top_k=10,
                filters=None,
                max_retries=1,
            )
        assert not result.success
        assert "超时" in (result.error or "")


class TestLayer2Graph:
    """Layer 2 图检索测试"""

    @pytest.mark.asyncio
    async def test_layer2_api_fallback_success(self, engine):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "data": {
                    "results": [
                        {"score": 0.8, "payload": {"name_zh": "深蹲", "exercise_id": "e1"}},
                    ]
                }
            }
        )

        with patch(
            "src.framework.retrieval.three_layer.layer2_graph.aiohttp.ClientSession"
        ) as MockSession:
            mock_post_cm = MagicMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_cm.__aexit__ = AsyncMock(return_value=False)
            mock_session = MagicMock()
            mock_session.post.return_value = mock_post_cm
            mock_session_cm = MagicMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)
            MockSession.return_value = mock_session_cm

            result = await engine._query_neo4j_via_api(
                query="练腿",
                domain="fitness",
                vector_results=[{"id": "e1"}],
                top_k=5,
            )
        assert result.success
        assert len(result.results) > 0
        assert result.metadata.get("source") == "api_fallback"

    @pytest.mark.asyncio
    async def test_layer2_api_fallback_failure(self, engine):
        mock_response = MagicMock()
        mock_response.status = 503

        with patch(
            "src.framework.retrieval.three_layer.layer2_graph.aiohttp.ClientSession"
        ) as MockSession:
            mock_post_cm = MagicMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_cm.__aexit__ = AsyncMock(return_value=False)
            mock_session = MagicMock()
            mock_session.post.return_value = mock_post_cm
            mock_session_cm = MagicMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)
            MockSession.return_value = mock_session_cm

            result = await engine._query_neo4j_via_api(
                query="练腿",
                domain="fitness",
                vector_results=[],
                top_k=5,
            )
        assert not result.success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_layer2_fallback_no_vector_results(self, engine):
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
            mock_post_cm = MagicMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post_cm.__aexit__ = AsyncMock(return_value=False)
            mock_session = MagicMock()
            mock_session.post.return_value = mock_post_cm
            mock_session_cm = MagicMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=False)
            MockSession.return_value = mock_session_cm
            result = await engine._query_neo4j_via_api_fallback(
                query="练背",
                domain="fitness",
                top_k=5,
            )
        assert result.success
        assert len(result.results) > 0


class TestLayer3Rules:
    """Layer 3 规则引擎测试"""

    def test_match_fitness_level_beginner(self, engine):
        exercise = {"difficulty_zh": "beginner", "difficulty_en": "beginner"}
        profile = {"fitness_level": "beginner"}
        assert engine._match_fitness_level(exercise, profile) is True

    def test_match_fitness_level_advanced_rejects_beginner(self, engine):
        exercise = {"difficulty_zh": "beginner", "difficulty_en": "beginner"}
        profile = {"fitness_level": "advanced"}
        assert engine._match_fitness_level(exercise, profile) is False

    def test_match_fitness_level_no_profile(self, engine):
        exercise = {"difficulty_zh": "intermediate"}
        assert engine._match_fitness_level(exercise, None) is True

    @pytest.mark.asyncio
    async def test_validate_safety_no_profile(self, engine):
        exercise = {"exercise_name_zh": "深蹲", "difficulty": "beginner"}
        profile = None
        assert await engine._validate_safety(exercise, profile) is True

    @pytest.mark.asyncio
    async def test_validate_safety_age_over_60(self, engine):
        exercise = {"exercise_name_zh": "大重量深蹲", "difficulty": "advanced", "difficulty_zh": "advanced"}
        profile = {"basic_info": {"age": 65}, "health_status": {}}
        assert await engine._validate_safety(exercise, profile) is False

    def test_check_equipment_availability_no_profile(self, engine):
        exercise = {"equipment": "哑铃"}
        assert engine._check_equipment_availability(exercise, None) is True

    def test_check_equipment_availability_match(self, engine):
        exercise = {"equipment": "哑铃", "exercise_name_zh": "哑铃弯举"}
        profile = {"available_equipment": ["哑铃", "杠铃"]}
        assert engine._check_equipment_availability(exercise, profile) is True

    def test_check_equipment_availability_no_match(self, engine):
        exercise = {"equipment": "杠铃", "exercise_name_zh": "杠铃卧推"}
        profile = {"available_equipment": ["哑铃"]}
        assert engine._check_equipment_availability(exercise, profile) is False

    def test_assess_training_volume_full(self, engine):
        exercise = {"training_volume": {"mev": 10, "mav": 20, "mrv": 15}}
        assert engine._assess_training_volume(exercise, {}) == 1.0

    def test_assess_training_volume_partial(self, engine):
        exercise = {"training_volume": {"mev": 10}}
        assert engine._assess_training_volume(exercise, {}) == 0.9


class TestResultMerger:
    """结果融合与去重排序测试"""

    def test_empty_layer_result(self, engine):
        result = engine._empty_layer_result("Layer1-Vector", error="test error")
        assert result.layer_name == "Layer1-Vector"
        assert not result.success
        assert result.results == []
        assert result.error == "test error"

    def test_build_final_result_layer3_priority(self, engine):
        layer1 = LayerExecutionResult("L1", True, [{"id": "1"}], 10, 0.8, {})
        layer2 = LayerExecutionResult("L2", True, [{"id": "1"}, {"id": "2"}], 20, 0.9, {})
        layer3 = LayerExecutionResult("L2", True, [{"id": "1"}, {"id": "2"}, {"id": "3"}], 5, 0.95, {})

        with patch.object(engine, "get_stats", return_value={}):
            with patch.dict("os.environ", {"ENABLE_RERANKER": "false"}):
                result = engine._build_final_result(
                    query="test",
                    domain="fitness",
                    layer1=layer1,
                    layer2=layer2,
                    layer3=layer3,
                    start_time=datetime.now(),
                )
        assert len(result.final_results) == 3
        assert result.total_confidence > 0
        assert "Layer3" in result.reasoning


class TestFallback:
    """规则匹配降级测试"""

    @pytest.mark.asyncio
    async def test_rule_based_fallback_keyword_match(self, engine):
        result = await engine._execute_rule_based_fallback(
            query="练胸",
            user_profile={"fitness_level": "intermediate"},
            top_k=5,
        )
        assert result.success
        assert len(result.results) > 0
        assert result.layer_name == "Layer2-RuleBased-Fallback"

    @pytest.mark.asyncio
    async def test_rule_based_fallback_default_items(self, engine):
        result = await engine._execute_rule_based_fallback(
            query="无关内容xyz",
            user_profile={"fitness_level": "beginner"},
            top_k=5,
        )
        assert result.success
        assert len(result.results) > 0


class TestEmptyQueryHandling:
    """空查询与空结果处理测试"""

    @pytest.mark.asyncio
    async def test_execute_three_layer_layer1_failure_fallback_chain(self, engine):
        mock_l1 = AsyncMock(return_value=LayerExecutionResult(
            "L1", False, [], 0, 0, {}, error="empty"
        ))
        mock_l2 = AsyncMock(return_value=LayerExecutionResult("L2", False, [], 0, 0, {}))
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
                            query="",
                            domain="fitness",
                            top_k=5,
                        )
        assert result is not None
        assert isinstance(result, ThreeLayerResult)
        assert mock_fb.called
        assert mock_l3.called


class TestEngineStats:
    """引擎统计测试"""

    def test_get_stats(self, engine):
        engine.stats["total_queries"] = 10
        engine.stats["layer1_success"] = 8
        engine.stats["layer2_neo4j_direct"] = 2
        engine.stats["layer2_api_fallback"] = 6
        engine.stats["layer3_success"] = 9
        stats = engine.get_stats()
        assert "success_rate" in stats
        assert "neo4j_available" in stats


class TestKeywordExtraction:
    """关键词提取测试"""

    def test_extract_muscle_keywords(self, engine):
        keywords = engine._extract_muscle_keywords("我想练胸和背部")
        assert len(keywords) > 0

    def test_extract_muscle_keywords_no_match(self, engine):
        keywords = engine._extract_muscle_keywords("今天天气真好")
        assert isinstance(keywords, list)
