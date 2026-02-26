"""
智能重量计算器工具测试（薄包装版）

测试 intelligent_weight_calculator 从 user_profile 读取预计算数据的逻辑。
PHP WeightRecommender 负责核心计算，Python 端只做数据组装和安全提示。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.applications.fitness.mcp_tools.training.intelligent_weight_calculator import (
    IntelligentWeightCalculator,
    IntelligentWeightCalculatorInput,
    TrainingGoal,
    UserLevel
)


@pytest.fixture
def mock_neo4j_client():
    return AsyncMock()


@pytest.fixture
def mock_qdrant_client():
    return MagicMock()


@pytest.fixture
def mock_three_layer_engine():
    return MagicMock()


@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def weight_calculator(mock_neo4j_client, mock_qdrant_client, mock_three_layer_engine, mock_logger):
    return IntelligentWeightCalculator(
        neo4j_client=mock_neo4j_client,
        qdrant_client=mock_qdrant_client,
        three_layer_engine=mock_three_layer_engine,
        logger=mock_logger
    )


def _make_input(exercise_id="bench_press", goal="hypertrophy", reps=10, rpe=8.0,
                level="intermediate", estimated_1rm=100.0):
    """构造带 user_profile 的输入数据"""
    return {
        "exercise_id": exercise_id,
        "training_goal": goal,
        "reps_target": reps,
        "rpe_target": rpe,
        "user_level": level,
        "user_profile": {
            "strength_data": {
                "personal_bests": {
                    exercise_id: {"estimated_1rm": estimated_1rm}
                }
            }
        }
    }


class TestIntelligentWeightCalculator:
    """智能重量计算器测试类"""

    def test_tool_metadata(self, weight_calculator):
        """测试工具元数据"""
        assert weight_calculator.get_name() == "intelligent_weight_calculator"
        assert "智能重量计算器" in weight_calculator.get_description()
        assert weight_calculator.get_category() == "training"
        assert weight_calculator.get_complexity() == "low"
        assert weight_calculator.get_estimated_duration() == 50.0

    def test_input_schema_validation(self):
        """测试输入Schema验证"""
        valid_input = IntelligentWeightCalculatorInput(
            user_id="user_123",
            exercise_id="bench_press",
            training_goal=TrainingGoal.HYPERTROPHY,
            reps_target=10,
            rpe_target=8.0,
            user_level=UserLevel.INTERMEDIATE
        )
        assert valid_input.user_id == "user_123"
        assert valid_input.training_goal == TrainingGoal.HYPERTROPHY

        with pytest.raises(ValueError):
            IntelligentWeightCalculatorInput(
                user_id="user_123",
                exercise_id="bench_press",
                training_goal=TrainingGoal.STRENGTH,
                reps_target=5,
                rpe_target=11.0
            )

    @pytest.mark.asyncio
    async def test_basic_weight_calculation(self, weight_calculator):
        """测试有1RM记录时的基础推荐"""
        result = await weight_calculator.execute(_make_input(estimated_1rm=100.0))

        assert result["success"] is True
        assert result["tool_name"] == "intelligent_weight_calculator"
        assert result["recommended_weight"] > 0
        assert result["estimated_1rm"] == 100.0
        assert "safety_considerations" in result
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_strength_goal_higher_weight(self, weight_calculator):
        """力量目标推荐更高重量（85-95% 1RM）"""
        strength = await weight_calculator.execute(
            _make_input(goal="strength", estimated_1rm=100.0)
        )
        hypertrophy = await weight_calculator.execute(
            _make_input(goal="hypertrophy", estimated_1rm=100.0)
        )
        assert strength["recommended_weight"] > hypertrophy["recommended_weight"]

    @pytest.mark.asyncio
    async def test_endurance_goal_lower_weight(self, weight_calculator):
        """耐力目标推荐更低重量（50-65% 1RM）"""
        endurance = await weight_calculator.execute(
            _make_input(goal="endurance", estimated_1rm=100.0)
        )
        hypertrophy = await weight_calculator.execute(
            _make_input(goal="hypertrophy", estimated_1rm=100.0)
        )
        assert endurance["recommended_weight"] < hypertrophy["recommended_weight"]

    @pytest.mark.asyncio
    async def test_weight_range_returned(self, weight_calculator):
        """返回的 weight_range 是 (min, max) 元组"""
        result = await weight_calculator.execute(_make_input(estimated_1rm=100.0))
        w_min, w_max = result["weight_range"]
        assert w_min < w_max
        assert w_min <= result["recommended_weight"] <= w_max

    @pytest.mark.asyncio
    async def test_weight_rounded_to_2_5kg(self, weight_calculator):
        """推荐重量向下取整到 2.5kg"""
        result = await weight_calculator.execute(_make_input(estimated_1rm=100.0))
        assert result["recommended_weight"] % 2.5 == 0

    @pytest.mark.asyncio
    async def test_no_1rm_returns_failure(self, weight_calculator):
        """没有1RM记录时返回失败+引导"""
        input_data = {
            "exercise_id": "bench_press",
            "training_goal": "hypertrophy",
            "reps_target": 10,
            "rpe_target": 8.0,
            "user_profile": {"strength_data": {"personal_bests": {}}}
        }
        result = await weight_calculator.execute(input_data)
        assert result["success"] is False
        assert "1RM" in result["message"]

    @pytest.mark.asyncio
    async def test_no_user_profile_returns_failure(self, weight_calculator):
        """没有 user_profile 时返回失败"""
        input_data = {
            "exercise_id": "bench_press",
            "training_goal": "hypertrophy",
            "reps_target": 10,
            "rpe_target": 8.0,
        }
        result = await weight_calculator.execute(input_data)
        assert result["success"] is False

    def test_safety_tips_beginner(self, weight_calculator):
        """初学者安全提示包含教练指导"""
        tips = weight_calculator._build_safety_tips("beginner", "bench_press")
        assert any("初学者" in t or "教练" in t for t in tips)

    def test_safety_tips_compound_lift(self, weight_calculator):
        """大重量复合动作提示保护员"""
        tips = weight_calculator._build_safety_tips("intermediate", "squat")
        assert any("保护员" in t for t in tips)

    @pytest.mark.asyncio
    async def test_error_handling(self, weight_calculator):
        """execute 内部异常返回 success=False"""
        input_data = {
            "exercise_id": "bench_press",
            "training_goal": "hypertrophy",
            "reps_target": 10,
            "rpe_target": 8.0,
            "user_profile": "invalid_type"  # 触发异常
        }
        result = await weight_calculator.execute(input_data)
        assert result["success"] is False
        assert "execution_time_ms" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
