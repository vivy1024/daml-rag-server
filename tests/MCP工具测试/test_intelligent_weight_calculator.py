"""
智能重量计算器工具测试

测试intelligent_weight_calculator工具的核心功能
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
    """模拟Neo4j客户端"""
    client = AsyncMock()
    client.run_query = AsyncMock(return_value=[
        {
            "mechanic": "compound",
            "force": "push",
            "difficulty_level": "intermediate"
        }
    ])
    return client


@pytest.fixture
def mock_qdrant_client():
    """模拟Qdrant客户端"""
    return MagicMock()


@pytest.fixture
def mock_three_layer_engine():
    """模拟三层检索引擎"""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """模拟日志记录器"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def weight_calculator(
    mock_neo4j_client,
    mock_qdrant_client,
    mock_three_layer_engine,
    mock_logger
):
    """创建智能重量计算器实例"""
    return IntelligentWeightCalculator(
        neo4j_client=mock_neo4j_client,
        qdrant_client=mock_qdrant_client,
        three_layer_engine=mock_three_layer_engine,
        logger=mock_logger
    )


class TestIntelligentWeightCalculator:
    """智能重量计算器测试类"""

    def test_tool_metadata(self, weight_calculator):
        """测试工具元数据"""
        assert weight_calculator.get_name() == "intelligent_weight_calculator"
        assert "智能重量计算器" in weight_calculator.get_description()
        assert weight_calculator.get_category() == "training"
        assert weight_calculator.get_complexity() == "medium"
        assert weight_calculator.get_estimated_duration() == 300.0

    def test_input_schema_validation(self):
        """测试输入Schema验证"""
        # 有效输入
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
        assert valid_input.reps_target == 10
        assert valid_input.rpe_target == 8.0

        # 无效RPE（超出范围）
        with pytest.raises(ValueError):
            IntelligentWeightCalculatorInput(
                user_id="user_123",
                exercise_id="bench_press",
                training_goal=TrainingGoal.STRENGTH,
                reps_target=5,
                rpe_target=11.0  # 超出范围
            )

    @pytest.mark.asyncio
    async def test_basic_weight_calculation(self, weight_calculator):
        """测试基础重量计算"""
        input_data = {
            "user_id": "user_123",
            "exercise_id": "bench_press",
            "training_goal": "hypertrophy",
            "reps_target": 10,
            "rpe_target": 8.0,
            "user_level": "intermediate"
        }

        result = await weight_calculator.execute(input_data)

        assert result["success"] is True
        assert result["tool_name"] == "intelligent_weight_calculator"
        assert "calculation" in result
        assert "adjustments" in result
        assert "safety_considerations" in result
        assert "progression_guidelines" in result

        # 验证计算结果
        calculation = result["calculation"]
        assert calculation["recommended_weight"] > 0
        assert len(calculation["weight_range"]) == 2
        assert calculation["weight_range"][0] < calculation["weight_range"][1]
        assert calculation["reps_1rm_estimate"] > 0
        assert 0 < calculation["percentage_of_1rm"] <= 100
        assert calculation["rpe_correlation"] == 8.0

    @pytest.mark.asyncio
    async def test_strength_training_calculation(self, weight_calculator):
        """测试力量训练重量计算"""
        input_data = {
            "user_id": "user_123",
            "exercise_id": "squat",
            "training_goal": "strength",
            "reps_target": 3,
            "rpe_target": 9.0,
            "user_level": "advanced"
        }

        result = await weight_calculator.execute(input_data)

        assert result["success"] is True
        calculation = result["calculation"]
        adjustments = result["adjustments"]

        # 力量训练应该使用85-95%的力量标准（中位数90%）
        assert adjustments["goal_adjustment"] == 0.90
        assert adjustments["level_adjustment"] == 1.3  # 高级训练者
        assert calculation["recommended_weight"] > 0

    @pytest.mark.asyncio
    async def test_endurance_training_calculation(self, weight_calculator):
        """测试耐力训练重量计算"""
        input_data = {
            "user_id": "user_123",
            "exercise_id": "overhead_press",
            "training_goal": "endurance",
            "reps_target": 15,
            "rpe_target": 7.0,
            "user_level": "beginner"
        }

        result = await weight_calculator.execute(input_data)

        assert result["success"] is True
        calculation = result["calculation"]
        adjustments = result["adjustments"]

        # 耐力训练应该使用40-60%的力量标准（中位数50%）
        assert adjustments["goal_adjustment"] == 0.50
        assert adjustments["level_adjustment"] == 0.7  # 初学者
        assert calculation["recommended_weight"] > 0

    @pytest.mark.asyncio
    async def test_rpe_percentage_mapping(self, weight_calculator):
        """测试RPE百分比映射"""
        # 测试不同RPE值
        test_cases = [
            (10.0, 1.0),
            (9.0, 0.95),
            (8.0, 0.90),
            (7.0, 0.85),
            (6.0, 0.80)
        ]

        for rpe, expected_percentage in test_cases:
            result = weight_calculator._get_rpe_percentage(rpe)
            assert result == expected_percentage

    def test_adjustments_calculation(self, weight_calculator):
        """测试调整因子计算"""
        # 测试中级训练者增肌训练
        adjustments = weight_calculator._calculate_adjustments(
            user_level="intermediate",
            training_goal="hypertrophy",
            rpe_target=8.0
        )

        assert adjustments["level_adjustment"] == 1.0
        # 增肌训练应该使用60-80%的力量标准（中位数70%）
        assert adjustments["goal_adjustment"] == 0.70
        assert adjustments["fatigue_adjustment"] == 0.8  # RPE 8
        assert adjustments["total_adjustment"] == 1.0 * 0.70 * 0.8

    def test_safety_considerations_generation(self, weight_calculator):
        """测试安全考虑生成"""
        # 初学者
        considerations = weight_calculator._generate_safety_considerations(
            exercise_id="bench_press",
            user_level="beginner"
        )
        assert len(considerations) > 0
        assert any("初学者" in c for c in considerations)

        # 深蹲动作
        considerations = weight_calculator._generate_safety_considerations(
            exercise_id="squat",
            user_level="intermediate"
        )
        assert any("保护员" in c for c in considerations)

    def test_progression_guidelines_generation(self, weight_calculator):
        """测试进阶指导生成"""
        # 力量训练
        guidelines = weight_calculator._generate_progression_guidelines(
            training_goal="strength",
            reps_target=5
        )
        assert len(guidelines) > 0
        assert any("力量训练" in g for g in guidelines)

        # 增肌训练
        guidelines = weight_calculator._generate_progression_guidelines(
            training_goal="hypertrophy",
            reps_target=10
        )
        assert any("增肌训练" in g for g in guidelines)

    @pytest.mark.asyncio
    async def test_different_user_levels(self, weight_calculator):
        """测试不同用户水平的计算差异"""
        base_input = {
            "user_id": "user_123",
            "exercise_id": "bench_press",
            "training_goal": "hypertrophy",
            "reps_target": 10,
            "rpe_target": 8.0
        }

        # 初学者
        beginner_input = {**base_input, "user_level": "beginner"}
        beginner_result = await weight_calculator.execute(beginner_input)

        # 高级训练者
        advanced_input = {**base_input, "user_level": "advanced"}
        advanced_result = await weight_calculator.execute(advanced_input)

        # 高级训练者的推荐重量应该更高
        beginner_weight = beginner_result["calculation"]["recommended_weight"]
        advanced_weight = advanced_result["calculation"]["recommended_weight"]
        assert advanced_weight > beginner_weight

    @pytest.mark.asyncio
    async def test_weight_range_calculation(self, weight_calculator):
        """测试重量范围计算"""
        input_data = {
            "user_id": "user_123",
            "exercise_id": "deadlift",
            "training_goal": "strength",
            "reps_target": 5,
            "rpe_target": 9.0,
            "user_level": "intermediate"
        }

        result = await weight_calculator.execute(input_data)
        calculation = result["calculation"]

        # 重量范围应该是推荐重量的±5%
        recommended = calculation["recommended_weight"]
        weight_min, weight_max = calculation["weight_range"]

        assert weight_min < recommended < weight_max
        assert abs(weight_min - recommended * 0.95) < 1.0
        assert abs(weight_max - recommended * 1.05) < 1.0

    def test_training_goal_weight_percentages(self, weight_calculator):
        """测试不同训练目标的重量百分比"""
        # 力量训练：85-95%（中位数90%）
        strength_adjustments = weight_calculator._calculate_adjustments(
            user_level="intermediate",
            training_goal="strength",
            rpe_target=8.0
        )
        assert strength_adjustments["goal_adjustment"] == 0.90

        # 增肌训练：60-80%（中位数70%）
        hypertrophy_adjustments = weight_calculator._calculate_adjustments(
            user_level="intermediate",
            training_goal="hypertrophy",
            rpe_target=8.0
        )
        assert hypertrophy_adjustments["goal_adjustment"] == 0.70

        # 耐力训练：40-60%（中位数50%）
        endurance_adjustments = weight_calculator._calculate_adjustments(
            user_level="intermediate",
            training_goal="endurance",
            rpe_target=8.0
        )
        assert endurance_adjustments["goal_adjustment"] == 0.50

        # 一般健身：65-75%（中位数70%）
        general_adjustments = weight_calculator._calculate_adjustments(
            user_level="intermediate",
            training_goal="general_fitness",
            rpe_target=8.0
        )
        assert general_adjustments["goal_adjustment"] == 0.70

    @pytest.mark.asyncio
    async def test_error_handling(self, weight_calculator, mock_neo4j_client):
        """测试错误处理 - Neo4j查询失败时使用默认值"""
        # 模拟Neo4j查询失败
        mock_neo4j_client.run_query = AsyncMock(side_effect=Exception("数据库错误"))

        input_data = {
            "user_id": "user_123",
            "exercise_id": "bench_press",
            "training_goal": "hypertrophy",
            "reps_target": 10,
            "rpe_target": 8.0
        }

        result = await weight_calculator.execute(input_data)

        # 即使Neo4j查询失败，工具仍应成功执行（使用默认1RM估算）
        assert result["success"] is True
        assert result["calculation"]["recommended_weight"] > 0
        # 验证使用了默认的1RM估算值
        assert result["calculation"]["reps_1rm_estimate"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
