"""
TDEE计算器工具测试（薄包装版）

测试 tdee_calculator 从 user_profile.nutrition_profile.auto_calculated 读取预计算数据的逻辑。
PHP Calculator Service 负责核心计算，Python 端只做数据读取和透传。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.applications.fitness.mcp_tools.nutrition.tdee_calculator import (
    TDEECalculator,
    TDEECalculatorInput,
    TDEECalculatorOutput
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
def tdee_calculator(mock_neo4j_client, mock_qdrant_client, mock_three_layer_engine, mock_logger):
    return TDEECalculator(
        neo4j_client=mock_neo4j_client,
        qdrant_client=mock_qdrant_client,
        three_layer_engine=mock_three_layer_engine,
        logger=mock_logger
    )


def _make_input(bmr=1700.0, tdee=2300.0, target_calories=2700.0,
                fitness_goal="muscle_gain", macros=None):
    """构造带 user_profile 的输入数据"""
    if macros is None:
        macros = {
            "protein_grams": 180,
            "carbs_grams": 300,
            "fat_grams": 80,
        }
    return {
        "user_id": "test_user_123",
        "user_profile": {
            "nutrition_profile": {
                "auto_calculated": {
                    "bmr": bmr,
                    "tdee": tdee,
                    "target_calories": target_calories,
                    "fitness_goal": fitness_goal,
                    "macros": macros,
                }
            }
        }
    }


class TestTDEECalculatorBasics:
    """测试TDEE计算器基础功能"""

    def test_get_name(self, tdee_calculator):
        assert tdee_calculator.get_name() == "tdee_calculator"

    def test_get_category(self, tdee_calculator):
        assert tdee_calculator.get_category() == "nutrition"

    def test_get_complexity(self, tdee_calculator):
        assert tdee_calculator.get_complexity() == "low"

    def test_get_estimated_duration(self, tdee_calculator):
        assert tdee_calculator.get_estimated_duration() == 50.0

    def test_requires_user_profile(self, tdee_calculator):
        assert tdee_calculator.requires_user_profile() is True

    def test_get_dependencies(self, tdee_calculator):
        deps = tdee_calculator.get_dependencies()
        assert "user_profile_mcp" in deps

    def test_input_schema(self):
        valid_input = TDEECalculatorInput(user_id="user_123")
        assert valid_input.user_id == "user_123"


class TestTDEEExecution:
    """测试完整执行流程"""

    @pytest.mark.asyncio
    async def test_read_precalculated_data(self, tdee_calculator):
        """有预计算数据时正常返回"""
        result = await tdee_calculator.execute(_make_input())

        assert result["success"] is True
        assert result["tool_name"] == "tdee_calculator"
        assert result["bmr"] == 1700.0
        assert result["tdee"] == 2300.0
        assert result["target_calories"] == 2700.0
        assert result["fitness_goal"] == "muscle_gain"
        assert result["macros"]["protein_grams"] == 180
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_weight_loss_goal(self, tdee_calculator):
        """减脂目标数据透传"""
        result = await tdee_calculator.execute(
            _make_input(tdee=2000.0, target_calories=1600.0, fitness_goal="weight_loss")
        )
        assert result["success"] is True
        assert result["tdee"] == 2000.0
        assert result["target_calories"] == 1600.0
        assert result["fitness_goal"] == "weight_loss"

    @pytest.mark.asyncio
    async def test_no_auto_calculated_returns_failure(self, tdee_calculator):
        """没有预计算数据时返回失败+引导"""
        input_data = {
            "user_id": "test_user",
            "user_profile": {
                "nutrition_profile": {}
            }
        }
        result = await tdee_calculator.execute(input_data)
        assert result["success"] is False
        assert "TDEE" in result["message"]

    @pytest.mark.asyncio
    async def test_empty_auto_calculated_returns_failure(self, tdee_calculator):
        """auto_calculated 为空字典时返回失败"""
        input_data = {
            "user_id": "test_user",
            "user_profile": {
                "nutrition_profile": {
                    "auto_calculated": {}
                }
            }
        }
        result = await tdee_calculator.execute(input_data)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_no_user_profile_returns_failure(self, tdee_calculator):
        """没有 user_profile 时返回失败"""
        input_data = {"user_id": "test_user"}
        result = await tdee_calculator.execute(input_data)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_no_nutrition_profile_returns_failure(self, tdee_calculator):
        """没有 nutrition_profile 时返回失败"""
        input_data = {
            "user_id": "test_user",
            "user_profile": {}
        }
        result = await tdee_calculator.execute(input_data)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_error_handling(self, tdee_calculator):
        """execute 内部异常返回 success=False"""
        input_data = {
            "user_id": "test_user",
            "user_profile": "invalid_type"  # 触发异常
        }
        result = await tdee_calculator.execute(input_data)
        assert result["success"] is False
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_execution_time_tracked(self, tdee_calculator):
        """执行时间被记录"""
        result = await tdee_calculator.execute(_make_input())
        assert result["execution_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_partial_auto_calculated_no_tdee(self, tdee_calculator):
        """auto_calculated 有数据但缺少 tdee 字段时返回失败"""
        input_data = {
            "user_id": "test_user",
            "user_profile": {
                "nutrition_profile": {
                    "auto_calculated": {
                        "bmr": 1700.0,
                        # 缺少 tdee
                    }
                }
            }
        }
        result = await tdee_calculator.execute(input_data)
        assert result["success"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
