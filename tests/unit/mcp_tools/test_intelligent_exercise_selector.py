"""
测试intelligent_exercise_selector工具

验证工具的基本功能和评分逻辑
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.applications.fitness.mcp_tools.exercise.intelligent_exercise_selector import (
    IntelligentExerciseSelector,
    IntelligentExerciseSelectorInput,
    TrainingGoal,
    DifficultyLevel
)


@pytest.fixture
def mock_neo4j_client():
    """模拟Neo4j客户端"""
    return Mock()


@pytest.fixture
def mock_qdrant_client():
    """模拟Qdrant客户端"""
    return Mock()


@pytest.fixture
def mock_three_layer_engine():
    """模拟三层检索引擎"""
    engine = Mock()
    engine.execute_three_layer_query = AsyncMock()
    return engine


@pytest.fixture
def selector(mock_neo4j_client, mock_qdrant_client, mock_three_layer_engine):
    """创建IntelligentExerciseSelector实例"""
    return IntelligentExerciseSelector(
        neo4j_client=mock_neo4j_client,
        qdrant_client=mock_qdrant_client,
        three_layer_engine=mock_three_layer_engine
    )


class TestIntelligentExerciseSelector:
    """测试IntelligentExerciseSelector类"""
    
    def test_get_name(self, selector):
        """测试工具名称"""
        assert selector.get_name() == "intelligent_exercise_selector"
    
    def test_get_category(self, selector):
        """测试工具分类"""
        assert selector.get_category() == "exercise"
    
    def test_get_complexity(self, selector):
        """测试工具复杂度"""
        assert selector.get_complexity() == "complex"
    
    def test_requires_user_profile(self, selector):
        """测试是否需要用户档案"""
        assert selector.requires_user_profile() is True
    
    def test_build_query_text_basic(self, selector):
        """测试基础查询文本构建"""
        input_data = {
            "user_id": "test_user",
            "muscle_group": "胸",
            "training_goal": "strength",
            "difficulty_level": "intermediate",
            "available_equipment": ["杠铃", "哑铃"]
        }
        user_profile = {}
        
        query_text = selector._build_query_text(input_data, user_profile)

        assert "胸" in query_text
        assert "中级" in query_text  # intermediate -> 中级
        assert "力量" in query_text  # strength -> 力量
        assert "杠铃" in query_text or "哑铃" in query_text
    
    def test_build_query_text_with_injury(self, selector):
        """测试包含损伤史的查询文本构建"""
        input_data = {
            "user_id": "test_user",
            "muscle_group": "肩",
            "training_goal": "hypertrophy",
            "difficulty_level": "beginner",
            "available_equipment": ["哑铃"],
            "injury_history": ["肩部损伤"]
        }
        user_profile = {}
        
        query_text = selector._build_query_text(input_data, user_profile)
        
        assert "肩" in query_text
        assert "肩部损伤" in query_text
        assert "避免" in query_text
    
    def test_calculate_suitability_score_strength_goal(self, selector):
        """测试力量训练目标的适配度评分"""
        exercise = {
            "exercise_id": "ex1",
            "name_zh": "杠铃卧推",
            "force_zh": "推",
            "equipment_zh": ["杠铃"]
        }
        input_data = {
            "training_goal": "strength",
            "available_equipment": ["杠铃", "哑铃"],
            "disliked_exercises": []
        }
        user_profile = {}

        score = selector._calculate_suitability_score(exercise, input_data, user_profile)

        # 基础分50 + 力量目标(force_zh含"推")20 + 器械匹配20 = 90
        assert score >= 80
        assert score <= 100
    
    def test_calculate_suitability_score_equipment_mismatch(self, selector):
        """测试器械不匹配的适配度评分"""
        exercise = {
            "exercise_id": "ex1",
            "name_zh": "史密斯卧推",
            "equipment_zh": ["史密斯机"]
        }
        input_data = {
            "training_goal": "hypertrophy",
            "available_equipment": ["杠铃", "哑铃"],
            "disliked_exercises": []
        }
        user_profile = {}
        
        score = selector._calculate_suitability_score(exercise, input_data, user_profile)
        
        # 基础分50 + 增肌目标15 = 65（没有器械匹配加分）
        assert score >= 50
        assert score < 80
    
    def test_calculate_safety_score_low_risk(self, selector):
        """测试低风险动作的安全评分"""
        exercise = {
            "exercise_id": "ex1",
            "safety_level": "LOW_RISK",
            "contraindications_zh": []
        }
        input_data = {
            "difficulty_level": "intermediate",
            "injury_history": []
        }
        user_profile = {}
        
        score = selector._calculate_safety_score(exercise, input_data, user_profile)
        
        # 基础分100，低风险不扣分
        assert score == 100.0
    
    def test_calculate_safety_score_high_risk(self, selector):
        """测试高风险动作的安全评分"""
        exercise = {
            "exercise_id": "ex1",
            "safety_level": "HIGH_RISK",
            "contraindications_zh": []
        }
        input_data = {
            "difficulty_level": "advanced",
            "injury_history": []
        }
        user_profile = {}
        
        score = selector._calculate_safety_score(exercise, input_data, user_profile)
        
        # 基础分100 - 高风险40 = 60
        assert score == 60.0
    
    def test_calculate_safety_score_with_injury_contraindication(self, selector):
        """测试有禁忌症匹配的安全评分"""
        exercise = {
            "exercise_id": "ex1",
            "safety_level": "MEDIUM_RISK",
            "contraindications_zh": ["肩部损伤", "腰部损伤"]
        }
        input_data = {
            "difficulty_level": "intermediate",
            "injury_history": ["肩部损伤"]
        }
        user_profile = {}
        
        score = selector._calculate_safety_score(exercise, input_data, user_profile)
        
        # 基础分100 - 中风险20 - 禁忌症匹配10 = 70
        assert score == 70.0
    
    def test_calculate_safety_score_beginner_advanced_exercise(self, selector):
        """测试新手遇到高级动作的安全评分"""
        exercise = {
            "exercise_id": "ex1",
            "safety_level": "MEDIUM_RISK",
            "difficulty_zh": "高级",
            "contraindications_zh": []
        }
        input_data = {
            "difficulty_level": "beginner",
            "injury_history": []
        }
        user_profile = {}

        score = selector._calculate_safety_score(exercise, input_data, user_profile)

        # 基础分100 - 中风险20 - 新手高级动作20 = 60
        assert score == 60.0
    
    @pytest.mark.asyncio
    async def test_execute_success(self, selector, mock_three_layer_engine):
        """测试成功执行工具"""
        # 模拟三层检索返回结果
        mock_three_layer_engine.execute_three_layer_query.return_value = Mock(
            final_results=[
                {
                    "exercise_id": "ex1",
                    "name_zh": "杠铃卧推",
                    "name_en": "Barbell Bench Press",
                    "category": "力量训练",
                    "difficulty": "中级",
                    "safety_level": "MEDIUM_RISK",
                    "primary_muscles": ["胸大肌"],
                    "secondary_muscles": ["三角肌前束", "肱三头肌"],
                    "muscle_groups": ["胸大肌", "三角肌前束", "肱三头肌"],
                    "equipment_zh": ["杠铃"],
                    "movement_pattern_zh": "推",
                    "force_type_zh": "推",
                    "mechanics_zh": "复合",
                    "safety_warning_signs": [],
                    "contraindications_zh": [],
                    "injury_risk_factors": [],
                    "common_mistakes_zh": [],
                    "progression_options": []
                }
            ]
        )
        
        input_data = {
            "user_id": "test_user",
            "muscle_group": "胸",
            "training_goal": "strength",
            "difficulty_level": "intermediate",
            "available_equipment": ["杠铃", "哑铃"]
        }
        
        result = await selector.execute(input_data)
        
        assert result["success"] is True
        assert result["tool_name"] == "intelligent_exercise_selector"
        assert len(result["recommendations"]) > 0
        assert result["recommendations"][0]["name_zh"] == "杠铃卧推"
        assert "suitability_score" in result["recommendations"][0]
        assert "safety_score" in result["recommendations"][0]
    
    def test_generate_reasoning(self, selector):
        """测试推荐理由生成"""
        input_data = {
            "muscle_group": "胸",
            "training_goal": "strength",
            "difficulty_level": "intermediate",
            "injury_history": ["肩部损伤"]
        }
        user_profile = {}
        
        reasoning = selector._generate_reasoning(input_data, user_profile)
        
        assert "胸" in reasoning
        assert "strength" in reasoning
        assert "intermediate" in reasoning
        assert "损伤史" in reasoning
    
    def test_generate_safety_alerts_high_risk(self, selector):
        """测试高风险动作的安全提醒"""
        from src.applications.fitness.mcp_tools.exercise.intelligent_exercise_selector import (
            ExerciseRecommendation
        )
        
        recommendations = [
            ExerciseRecommendation(
                exercise_id="ex1",
                name_zh="杠铃深蹲",
                name_en="Barbell Squat",
                category="力量训练",
                difficulty="高级",
                safety_level="HIGH_RISK",
                primary_muscles=["股四头肌"],
                secondary_muscles=[],
                muscle_groups=["股四头肌"],
                equipment_zh=["杠铃"],
                safety_warning_signs=[],
                contraindications_zh=[],
                injury_risk_factors=[],
                common_mistakes_zh=[],
                progression_options=[],
                suitability_score=85.0,
                safety_score=60.0,
                reasoning="测试"
            )
        ]
        user_profile = {}
        
        alerts = selector._generate_safety_alerts(recommendations, user_profile)
        
        assert len(alerts) > 0
        assert any("高风险" in alert for alert in alerts)
    
    def test_generate_safety_alerts_beginner(self, selector):
        """测试新手的安全提醒"""
        recommendations = []
        user_profile = {"training_level": "beginner"}
        
        alerts = selector._generate_safety_alerts(recommendations, user_profile)
        
        assert len(alerts) > 0
        assert any("新手" in alert for alert in alerts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
