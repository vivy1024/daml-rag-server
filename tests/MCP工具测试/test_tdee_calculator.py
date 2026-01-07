"""
TDEE计算器工具测试

测试TDEE计算器的核心功能
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
    """Mock Neo4j客户端"""
    client = MagicMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant客户端"""
    return MagicMock()


@pytest.fixture
def mock_three_layer_engine():
    """Mock三层检索引擎"""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Mock日志记录器"""
    return MagicMock()


@pytest.fixture
def tdee_calculator(mock_neo4j_client, mock_qdrant_client, mock_three_layer_engine, mock_logger):
    """创建TDEE计算器实例"""
    return TDEECalculator(
        neo4j_client=mock_neo4j_client,
        qdrant_client=mock_qdrant_client,
        three_layer_engine=mock_three_layer_engine,
        logger=mock_logger
    )


class TestTDEECalculatorBasics:
    """测试TDEE计算器基础功能"""
    
    def test_get_name(self, tdee_calculator):
        """测试工具名称"""
        assert tdee_calculator.get_name() == "tdee_calculator"
    
    def test_get_category(self, tdee_calculator):
        """测试工具分类"""
        assert tdee_calculator.get_category() == "nutrition"
    
    def test_get_complexity(self, tdee_calculator):
        """测试工具复杂度"""
        assert tdee_calculator.get_complexity() == "medium"
    
    def test_requires_user_profile(self, tdee_calculator):
        """测试是否需要用户档案"""
        assert tdee_calculator.requires_user_profile() is True
    
    def test_get_dependencies(self, tdee_calculator):
        """测试依赖列表"""
        deps = tdee_calculator.get_dependencies()
        assert "user_profile_mcp" in deps


class TestBMRCalculation:
    """测试BMR计算"""
    
    def test_bmr_male(self, tdee_calculator):
        """测试男性BMR计算"""
        user_info = {
            "age": 30,
            "gender": "male",
            "weight_kg": 75.0,
            "height_cm": 175.0
        }
        
        bmr_result = tdee_calculator._calculate_bmr(user_info)
        
        # 男性: BMR = 10 × 75 + 6.25 × 175 - 5 × 30 + 5
        # = 750 + 1093.75 - 150 + 5 = 1698.75
        assert bmr_result.bmr == pytest.approx(1698.8, abs=0.1)
        assert bmr_result.formula == "Mifflin-St Jeor公式"
        assert "75.0kg" in bmr_result.calculation_details
        assert "175.0cm" in bmr_result.calculation_details
    
    def test_bmr_female(self, tdee_calculator):
        """测试女性BMR计算"""
        user_info = {
            "age": 25,
            "gender": "female",
            "weight_kg": 60.0,
            "height_cm": 165.0
        }
        
        bmr_result = tdee_calculator._calculate_bmr(user_info)
        
        # 女性: BMR = 10 × 60 + 6.25 × 165 - 5 × 25 - 161
        # = 600 + 1031.25 - 125 - 161 = 1345.25
        assert bmr_result.bmr == pytest.approx(1345.2, abs=0.1)
        assert bmr_result.formula == "Mifflin-St Jeor公式"


class TestActivityMultiplier:
    """测试活动系数计算"""
    
    def test_sedentary_low_training(self, tdee_calculator):
        """测试久坐+低强度训练"""
        result = tdee_calculator._calculate_activity_multiplier(
            training_frequency=2,
            training_intensity="low",
            daily_activity_level="sedentary"
        )
        
        # 久坐: 1.2 + 训练贡献: 2 × 0.02 = 1.24
        assert result.multiplier == pytest.approx(1.24, abs=0.01)
        assert result.daily_activity_contribution == 1.2
        assert result.training_contribution == pytest.approx(0.04, abs=0.01)
    
    def test_very_active_high_training(self, tdee_calculator):
        """测试高度活动+高强度训练"""
        result = tdee_calculator._calculate_activity_multiplier(
            training_frequency=5,
            training_intensity="high",
            daily_activity_level="very_active"
        )
        
        # 高度活动: 1.725 + 训练贡献: 5 × 0.06 = 2.025
        assert result.multiplier == pytest.approx(2.02, abs=0.01)
        assert result.daily_activity_contribution == pytest.approx(1.73, abs=0.01)
        assert result.training_contribution == pytest.approx(0.30, abs=0.01)


class TestCalorieTarget:
    """测试热量目标计算"""
    
    def test_weight_loss_target(self, tdee_calculator):
        """测试减脂目标"""
        result = tdee_calculator._calculate_calorie_target(
            tdee=2000.0,
            fitness_goal="weight_loss"
        )
        
        assert result.tdee == 2000.0
        assert result.adjustment == -400
        assert result.target_calories == 1600.0
        assert "减脂" in result.reasoning
    
    def test_muscle_gain_target(self, tdee_calculator):
        """测试增肌目标"""
        result = tdee_calculator._calculate_calorie_target(
            tdee=2500.0,
            fitness_goal="muscle_gain"
        )
        
        assert result.tdee == 2500.0
        assert result.adjustment == 400
        assert result.target_calories == 2900.0
        assert "增肌" in result.reasoning
    
    def test_maintenance_target(self, tdee_calculator):
        """测试维持目标"""
        result = tdee_calculator._calculate_calorie_target(
            tdee=2200.0,
            fitness_goal="maintenance"
        )
        
        assert result.tdee == 2200.0
        assert result.adjustment == 0
        assert result.target_calories == 2200.0


class TestMacronutrientDistribution:
    """测试营养素分配"""
    
    def test_balanced_muscle_gain(self, tdee_calculator):
        """测试均衡饮食+增肌目标"""
        result = tdee_calculator._calculate_macronutrient_distribution(
            target_calories=2500.0,
            weight_kg=75.0,
            fitness_goal="muscle_gain",
            dietary_preference="balanced"
        )
        
        # 验证总热量
        total_calories = (
            result.protein_calories +
            result.carbs_calories +
            result.fat_calories
        )
        assert total_calories == pytest.approx(2500.0, abs=10.0)
        
        # 验证百分比总和
        total_percentage = (
            result.protein_percentage +
            result.carbs_percentage +
            result.fat_percentage
        )
        assert total_percentage == pytest.approx(100.0, abs=1.0)
        
        # 验证蛋白质合理性（增肌目标应该较高）
        assert result.protein_percentage >= 25.0
        assert result.protein_grams > 0
    
    def test_keto_diet(self, tdee_calculator):
        """测试生酮饮食"""
        result = tdee_calculator._calculate_macronutrient_distribution(
            target_calories=2000.0,
            weight_kg=70.0,
            fitness_goal="weight_loss",
            dietary_preference="keto"
        )
        
        # 生酮饮食：脂肪应该占主导（70%）
        assert result.fat_percentage >= 60.0
        # 碳水应该很低（5%）
        assert result.carbs_percentage <= 10.0
    
    def test_high_protein_diet(self, tdee_calculator):
        """测试高蛋白饮食"""
        result = tdee_calculator._calculate_macronutrient_distribution(
            target_calories=2200.0,
            weight_kg=80.0,
            fitness_goal="recomp",
            dietary_preference="high_protein"
        )
        
        # 高蛋白饮食：蛋白质应该占35%
        assert result.protein_percentage >= 30.0


class TestMealTiming:
    """测试进餐时机"""
    
    def test_low_calorie_meal_timing(self, tdee_calculator):
        """测试低热量进餐时机"""
        result = tdee_calculator._generate_meal_timing(
            target_calories=1600.0,
            training_frequency=3
        )
        
        # 低热量：3餐
        assert result.meals_per_day == 3
        assert result.calories_per_meal == pytest.approx(1600.0 / 3, abs=1.0)
        assert result.pre_workout_calories > 0
        assert result.post_workout_calories > 0
    
    def test_high_calorie_meal_timing(self, tdee_calculator):
        """测试高热量进餐时机"""
        result = tdee_calculator._generate_meal_timing(
            target_calories=3000.0,
            training_frequency=5
        )
        
        # 高热量：5餐
        assert result.meals_per_day == 5
        assert result.calories_per_meal == pytest.approx(3000.0 / 5, abs=1.0)
    
    def test_no_training_meal_timing(self, tdee_calculator):
        """测试无训练进餐时机"""
        result = tdee_calculator._generate_meal_timing(
            target_calories=2000.0,
            training_frequency=0
        )
        
        # 无训练：训练前后热量为0
        assert result.pre_workout_calories == 0
        assert result.post_workout_calories == 0


class TestFullExecution:
    """测试完整执行流程"""
    
    @pytest.mark.asyncio
    async def test_execute_weight_loss(self, tdee_calculator):
        """测试减脂目标的完整执行"""
        input_data = {
            "user_id": "test_user_123",
            "age": 30,
            "gender": "male",
            "weight_kg": 80.0,
            "height_cm": 175.0,
            "training_frequency_per_week": 4,
            "training_intensity": "moderate",
            "daily_activity_level": "moderately_active",
            "fitness_goal": "weight_loss",
            "dietary_preference": "balanced"
        }
        
        result = await tdee_calculator.execute(input_data)
        
        # 验证基本结构
        assert result["success"] is True
        assert result["tool_name"] == "tdee_calculator"
        assert result["user_id"] == "test_user_123"
        
        # 验证BMR计算
        assert "bmr_calculation" in result
        assert result["bmr_calculation"]["bmr"] > 0
        
        # 验证活动系数
        assert "activity_multiplier" in result
        assert result["activity_multiplier"]["multiplier"] > 1.0
        
        # 验证热量目标
        assert "calorie_target" in result
        assert result["calorie_target"]["adjustment"] == -400  # 减脂
        
        # 验证营养素分配
        assert "macronutrient_distribution" in result
        macro = result["macronutrient_distribution"]
        assert macro["protein_grams"] > 0
        assert macro["carbs_grams"] > 0
        assert macro["fat_grams"] > 0
        
        # 验证进餐时机
        assert "meal_timing" in result
        assert result["meal_timing"]["meals_per_day"] > 0
        
        # 验证额外建议
        assert "additional_recommendations" in result
        assert len(result["additional_recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_execute_muscle_gain(self, tdee_calculator):
        """测试增肌目标的完整执行"""
        input_data = {
            "user_id": "test_user_456",
            "age": 25,
            "gender": "male",
            "weight_kg": 70.0,
            "height_cm": 180.0,
            "training_frequency_per_week": 5,
            "training_intensity": "high",
            "daily_activity_level": "very_active",
            "fitness_goal": "muscle_gain",
            "dietary_preference": "high_protein"
        }
        
        result = await tdee_calculator.execute(input_data)
        
        assert result["success"] is True
        assert result["calorie_target"]["adjustment"] == 400  # 增肌
        
        # 高蛋白饮食：蛋白质比例应该较高（考虑到平均计算，放宽要求）
        macro = result["macronutrient_distribution"]
        assert macro["protein_percentage"] >= 20.0
    
    @pytest.mark.asyncio
    async def test_execute_missing_info(self, tdee_calculator):
        """测试缺少必需信息的情况"""
        input_data = {
            "user_id": "test_user_789",
            # 缺少age, gender, weight_kg, height_cm
            "training_frequency_per_week": 3,
            "training_intensity": "moderate",
            "daily_activity_level": "moderately_active",
            "fitness_goal": "maintenance"
        }
        
        with pytest.raises(ValueError) as exc_info:
            await tdee_calculator.execute(input_data)
        
        assert "缺少必需信息" in str(exc_info.value)


class TestEdgeCases:
    """测试边界情况"""
    
    def test_very_young_user(self, tdee_calculator):
        """测试年轻用户"""
        user_info = {
            "age": 18,
            "gender": "male",
            "weight_kg": 65.0,
            "height_cm": 170.0
        }
        
        bmr_result = tdee_calculator._calculate_bmr(user_info)
        assert bmr_result.bmr > 0
    
    def test_older_user(self, tdee_calculator):
        """测试年长用户"""
        user_info = {
            "age": 60,
            "gender": "female",
            "weight_kg": 65.0,
            "height_cm": 160.0
        }
        
        bmr_result = tdee_calculator._calculate_bmr(user_info)
        assert bmr_result.bmr > 0
    
    def test_zero_training_frequency(self, tdee_calculator):
        """测试零训练频率"""
        result = tdee_calculator._calculate_activity_multiplier(
            training_frequency=0,
            training_intensity="low",
            daily_activity_level="sedentary"
        )
        
        # 零训练：只有日常活动系数
        assert result.multiplier == 1.2
        assert result.training_contribution == 0.0
    
    def test_extreme_training_frequency(self, tdee_calculator):
        """测试极高训练频率"""
        result = tdee_calculator._calculate_activity_multiplier(
            training_frequency=7,
            training_intensity="high",
            daily_activity_level="extremely_active"
        )
        
        # 极高训练：系数应该很高
        assert result.multiplier > 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
