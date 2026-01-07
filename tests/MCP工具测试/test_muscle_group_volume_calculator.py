"""
肌群训练量计算器单元测试

测试muscle_group_volume_calculator工具的核心功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.applications.fitness.mcp_tools.training.muscle_group_volume_calculator import (
    MuscleGroupVolumeCalculator,
    MuscleGroupVolumeCalculatorInput,
    VolumeRecommendation,
    RecoveryGuidance,
    OvertrainingRisk
)


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j客户端"""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant客户端"""
    client = MagicMock()
    return client


@pytest.fixture
def mock_three_layer_engine():
    """Mock 三层检索引擎"""
    engine = AsyncMock()
    return engine


@pytest.fixture
def mock_logger():
    """Mock 日志记录器"""
    import logging
    return logging.getLogger("test")


@pytest.fixture
def calculator(mock_neo4j_client, mock_qdrant_client, mock_three_layer_engine, mock_logger):
    """创建MuscleGroupVolumeCalculator实例"""
    return MuscleGroupVolumeCalculator(
        neo4j_client=mock_neo4j_client,
        qdrant_client=mock_qdrant_client,
        three_layer_engine=mock_three_layer_engine,
        logger=mock_logger
    )


class TestMuscleGroupVolumeCalculator:
    """测试MuscleGroupVolumeCalculator类"""
    
    def test_get_name(self, calculator):
        """测试工具名称"""
        assert calculator.get_name() == "muscle_group_volume_calculator"
    
    def test_get_category(self, calculator):
        """测试工具分类"""
        assert calculator.get_category() == "training"
    
    def test_get_complexity(self, calculator):
        """测试工具复杂度"""
        assert calculator.get_complexity() == "medium"
    
    def test_requires_user_profile(self, calculator):
        """测试是否需要用户档案"""
        assert calculator.requires_user_profile() is True
    
    @pytest.mark.asyncio
    async def test_execute_basic(self, calculator, mock_neo4j_client):
        """测试基本执行流程"""
        # 准备测试数据
        input_data = {
            "user_id": "test_user_123",
            "muscle_group": "胸大肌",
            "training_goal": "hypertrophy",
            "training_frequency_per_week": 3
        }
        
        # Mock Neo4j查询结果
        mock_result = MagicMock()
        mock_result.records = [
            {
                "name_zh": "胸大肌",
                "name_en": "Pectoralis Major",
                "training_frequency": "2-3次/周",
                "recovery_time": "48小时",
                "mev": 10,
                "mav": 16,
                "mrv": 22,
                "movement_patterns": ["推", "夹胸"],
                "function": ["肩关节水平内收", "肩关节内旋"]
            }
        ]
        mock_neo4j_client.query.return_value = mock_result
        
        # 执行工具
        result = await calculator.execute(input_data)
        
        # 验证结果
        assert result["success"] is True
        assert result["tool_name"] == "muscle_group_volume_calculator"
        assert result["user_id"] == "test_user_123"
        assert result["muscle_group"] == "胸大肌"
        assert result["mev"] == 10
        assert result["mav"] == 16
        assert result["mrv"] == 22
        assert "volume_recommendation" in result
        assert "recovery_guidance" in result
        assert result["confidence_score"] == 95.0
    
    @pytest.mark.asyncio
    async def test_execute_with_overtraining_check(self, calculator, mock_neo4j_client):
        """测试包含过度训练检查的执行"""
        input_data = {
            "user_id": "test_user_123",
            "muscle_group": "胸大肌",
            "training_goal": "hypertrophy",
            "training_frequency_per_week": 3,
            "current_weekly_sets": 25  # 超过MRV
        }
        
        # Mock Neo4j查询结果
        mock_result = MagicMock()
        mock_result.records = [
            {
                "name_zh": "胸大肌",
                "name_en": "Pectoralis Major",
                "training_frequency": "2-3次/周",
                "recovery_time": "48小时",
                "mev": 10,
                "mav": 16,
                "mrv": 22,
                "movement_patterns": ["推", "夹胸"],
                "function": ["肩关节水平内收"]
            }
        ]
        mock_neo4j_client.query.return_value = mock_result
        
        # 执行工具
        result = await calculator.execute(input_data)
        
        # 验证过度训练风险评估
        assert result["overtraining_risk"] is not None
        assert result["overtraining_risk"]["risk_level"] in ["HIGH", "CRITICAL"]
        assert len(result["overtraining_risk"]["warnings"]) > 0
    
    @pytest.mark.asyncio
    async def test_muscle_not_found(self, calculator, mock_neo4j_client):
        """测试肌群未找到的情况"""
        input_data = {
            "user_id": "test_user_123",
            "muscle_group": "不存在的肌群",
            "training_goal": "hypertrophy",
            "training_frequency_per_week": 3
        }
        
        # Mock Neo4j查询结果（空）
        mock_result = MagicMock()
        mock_result.records = []
        mock_neo4j_client.query.return_value = mock_result
        
        # 执行工具应该抛出异常
        with pytest.raises(ValueError, match="未找到肌群数据"):
            await calculator.execute(input_data)
    
    def test_parse_recovery_time(self, calculator):
        """测试恢复时间解析"""
        assert calculator._parse_recovery_time("48小时") == 48
        assert calculator._parse_recovery_time("72小时") == 72
        assert calculator._parse_recovery_time("24小时") == 24
        assert calculator._parse_recovery_time("无效格式") == 48  # 默认值
    
    def test_calculate_volume_recommendation_beginner(self, calculator):
        """测试新手训练量推荐"""
        muscle_data = {
            "mev": 10,
            "mav": 16,
            "mrv": 22
        }
        input_data = {
            "training_goal": "hypertrophy",
            "training_frequency_per_week": 3
        }
        user_profile = {
            "fitness_profile": {
                "training_level": "beginner",
                "recovery_capacity": "moderate"
            }
        }
        
        recommendation = calculator._calculate_volume_recommendation(
            muscle_data, input_data, user_profile
        )
        
        # 新手应该接近MEV
        assert recommendation.recommended_weekly_sets >= 10
        assert recommendation.recommended_weekly_sets <= 13
        assert recommendation.reps_per_set_range == (8, 12)  # 肌肥大
        assert recommendation.rest_period_seconds == 90
    
    def test_calculate_volume_recommendation_advanced(self, calculator):
        """测试高级训练者训练量推荐"""
        muscle_data = {
            "mev": 10,
            "mav": 16,
            "mrv": 22
        }
        input_data = {
            "training_goal": "strength",
            "training_frequency_per_week": 4
        }
        user_profile = {
            "fitness_profile": {
                "training_level": "advanced",
                "recovery_capacity": "high"
            }
        }
        
        recommendation = calculator._calculate_volume_recommendation(
            muscle_data, input_data, user_profile
        )
        
        # 高级训练者应该接近MAV，且恢复能力高会增加训练量
        assert recommendation.recommended_weekly_sets >= 16
        assert recommendation.reps_per_set_range == (3, 6)  # 力量训练
        assert recommendation.rest_period_seconds == 180
    
    def test_assess_overtraining_risk_low(self, calculator):
        """测试低过度训练风险"""
        muscle_data = {
            "mev": 10,
            "mav": 16,
            "mrv": 22
        }
        current_weekly_sets = 14  # 低于MAV
        volume_recommendation = VolumeRecommendation(
            recommended_weekly_sets=13,
            sets_per_session=4,
            reps_per_set_range=(8, 12),
            rest_period_seconds=90,
            reasoning="测试"
        )
        
        risk = calculator._assess_overtraining_risk(
            muscle_data, current_weekly_sets, volume_recommendation
        )
        
        assert risk.risk_level == "LOW"
        assert risk.risk_score == 0.0
    
    def test_assess_overtraining_risk_high(self, calculator):
        """测试高过度训练风险"""
        muscle_data = {
            "mev": 10,
            "mav": 16,
            "mrv": 22
        }
        current_weekly_sets = 25  # 超过MRV
        volume_recommendation = VolumeRecommendation(
            recommended_weekly_sets=16,
            sets_per_session=5,
            reps_per_set_range=(8, 12),
            rest_period_seconds=90,
            reasoning="测试"
        )
        
        risk = calculator._assess_overtraining_risk(
            muscle_data, current_weekly_sets, volume_recommendation
        )
        
        assert risk.risk_level in ["HIGH", "CRITICAL"]
        assert risk.risk_score > 5.0
        assert len(risk.warnings) > 0
        assert "超出" in risk.current_vs_mrv
    
    def test_calculate_recovery_guidance(self, calculator):
        """测试恢复指导计算"""
        muscle_data = {
            "recovery_time": "48小时",
            "movement_patterns": ["推", "夹胸"]
        }
        input_data = {
            "training_goal": "hypertrophy",
            "training_frequency_per_week": 3
        }
        user_profile = {
            "fitness_profile": {
                "recovery_capacity": "moderate"
            }
        }
        
        guidance = calculator._calculate_recovery_guidance(
            muscle_data, input_data, user_profile
        )
        
        assert guidance.recovery_time_hours > 0
        assert len(guidance.recovery_strategies) > 0
        assert len(guidance.warning_signs) > 0
        assert "训练频率" in guidance.training_frequency_recommendation
    
    def test_generate_additional_recommendations(self, calculator):
        """测试额外建议生成"""
        muscle_data = {
            "movement_patterns": ["推", "夹胸", "上斜推"],
            "function": ["肩关节水平内收"]
        }
        input_data = {
            "training_goal": "hypertrophy",
            "training_frequency_per_week": 3
        }
        user_profile = {
            "fitness_profile": {
                "training_level": "intermediate"
            }
        }
        volume_recommendation = VolumeRecommendation(
            recommended_weekly_sets=13,
            sets_per_session=4,
            reps_per_set_range=(8, 12),
            rest_period_seconds=90,
            reasoning="测试"
        )
        
        recommendations = calculator._generate_additional_recommendations(
            muscle_data, input_data, user_profile, volume_recommendation, None
        )
        
        assert len(recommendations) > 0
        assert any("肌肥大" in rec for rec in recommendations)
        assert any("动作模式" in rec for rec in recommendations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

