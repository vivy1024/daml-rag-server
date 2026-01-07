"""
训练目标推荐服务单元测试

测试TrainingGoalRecommender的核心功能
Requirements: 3.1, 3.2, 3.3, 3.4
"""

import pytest
from src.applications.fitness.services.training_goal_recommender import (
    TrainingGoalRecommender,
    get_training_goal_recommender,
    UserType
)


@pytest.fixture
def recommender():
    """创建TrainingGoalRecommender实例"""
    return TrainingGoalRecommender()


class TestTrainingGoalRecommender:
    """测试TrainingGoalRecommender类"""
    
    def test_get_training_goal_recommender_singleton(self):
        """测试单例模式"""
        recommender1 = get_training_goal_recommender()
        recommender2 = get_training_goal_recommender()
        assert recommender1 is recommender2
    
    def test_get_posture_correction_recommendations_sedentary(self, recommender):
        """测试久坐人群体态矫正推荐 - Requirements 3.2, 3.4"""
        user_profile = {
            "user_type": "worker",
            "occupation": "程序员"
        }
        
        result = recommender.get_posture_correction_recommendations(user_profile)
        
        assert result["priority"] == "high"
        assert "久坐人群" in result["message"]
        assert len(result["exercises"]) > 0
        assert "common_issues" in result
        assert "training_tips" in result
    
    def test_get_posture_correction_recommendations_non_sedentary(self, recommender):
        """测试非久坐人群体态矫正推荐"""
        user_profile = {
            "user_type": "athlete",
            "occupation": "运动员"
        }
        
        result = recommender.get_posture_correction_recommendations(user_profile)
        
        assert result["priority"] == "medium"
        assert len(result["exercises"]) > 0
    
    def test_get_student_nutrition_plan_hypertrophy(self, recommender):
        """测试大学生增肌营养方案 - Requirements 3.4"""
        user_profile = {
            "user_type": "student",
            "campus_name": "清华大学"
        }
        
        result = recommender.get_student_nutrition_plan("hypertrophy", user_profile)
        
        assert result["is_student_optimized"] is True
        assert "大学生" in result["message"]
        assert "清华大学" in result["message"]
        assert "budget_friendly_foods" in result
        assert "meal_timing" in result
        assert "budget_tips" in result
    
    def test_get_student_nutrition_plan_fat_loss(self, recommender):
        """测试大学生减脂营养方案 - Requirements 3.4"""
        user_profile = {
            "user_type": "student"
        }
        
        result = recommender.get_student_nutrition_plan("fat_loss", user_profile)
        
        assert result["is_student_optimized"] is True
        assert "daily_calorie_deficit" in result
    
    def test_get_student_nutrition_plan_non_student(self, recommender):
        """测试非学生用户营养方案"""
        user_profile = {
            "user_type": "worker"
        }
        
        result = recommender.get_student_nutrition_plan("hypertrophy", user_profile)
        
        assert result["is_student_optimized"] is False
    
    def test_get_fat_loss_training_params(self, recommender):
        """测试减脂训练参数 - Requirements 3.1"""
        result = recommender.get_fat_loss_training_params()
        
        assert result["description"] == "减脂塑形训练参数"
        assert result["rep_range"] == "12-20"
        assert result["rest_period"] == "30-45秒"
        assert result["training_density"] == "高"
        assert "recommended_methods" in result
        assert "cardio_recommendations" in result
    
    def test_get_functional_training_params(self, recommender):
        """测试功能性训练参数 - Requirements 3.3"""
        result = recommender.get_functional_training_params()
        
        assert result["description"] == "功能性训练参数"
        assert result["rep_range"] == "8-15"
        assert "focus_areas" in result
        assert "recommended_exercises" in result
        assert "sport_specific_tips" in result
    
    def test_get_goal_specific_recommendations_fat_loss(self, recommender):
        """测试减脂目标综合推荐 - Requirements 3.1"""
        user_profile = {
            "user_type": "worker"
        }
        
        result = recommender.get_goal_specific_recommendations("fat_loss", user_profile)
        
        assert result["training_goal"] == "fat_loss"
        assert "training_params" in result
        assert len(result["additional_recommendations"]) > 0
    
    def test_get_goal_specific_recommendations_posture_correction(self, recommender):
        """测试体态矫正目标综合推荐 - Requirements 3.2"""
        user_profile = {
            "user_type": "worker",
            "occupation": "办公室文员"
        }
        
        result = recommender.get_goal_specific_recommendations("posture_correction", user_profile)
        
        assert result["training_goal"] == "posture_correction"
        assert "posture_exercises" in result
        assert len(result["additional_recommendations"]) > 0
    
    def test_get_goal_specific_recommendations_functional(self, recommender):
        """测试功能性训练目标综合推荐 - Requirements 3.3"""
        user_profile = {
            "user_type": "athlete"
        }
        
        result = recommender.get_goal_specific_recommendations("functional", user_profile)
        
        assert result["training_goal"] == "functional"
        assert "training_params" in result
        assert len(result["additional_recommendations"]) > 0
    
    def test_get_goal_specific_recommendations_student_with_nutrition(self, recommender):
        """测试大学生用户包含营养方案 - Requirements 3.4"""
        user_profile = {
            "user_type": "student",
            "campus_name": "北京大学"
        }
        
        result = recommender.get_goal_specific_recommendations("hypertrophy", user_profile)
        
        assert result["nutrition_plan"] is not None
        assert result["nutrition_plan"]["is_student_optimized"] is True


class TestUserType:
    """测试UserType枚举"""
    
    def test_user_type_values(self):
        """测试用户类型枚举值"""
        assert UserType.STUDENT.value == "student"
        assert UserType.WORKER.value == "worker"
        assert UserType.ATHLETE.value == "athlete"
        assert UserType.SENIOR.value == "senior"
        assert UserType.OTHER.value == "other"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
