"""
休息模式中国本地化测试

测试新增的休息模式枚举和推荐逻辑：
- 练五休二（周末休息）- Requirements 2.1
- 练四休一 - Requirements 2.2
- 练三休一 - Requirements 2.3
- 大学生推荐隔日训练 - Requirements 2.4
- 根据分化类型智能推荐 - Requirements 2.5

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.applications.fitness.mcp_tools.training.training_split_designer import (
    TrainingSplitDesigner,
    RestPattern,
    SplitType,
    UserType
)


@pytest.fixture
def tool():
    """创建训练分化设计器实例"""
    return TrainingSplitDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        logger=None
    )


class TestRestPatternEnum:
    """测试休息模式枚举 - Requirements 2.1, 2.2, 2.3"""
    
    def test_train_5_rest_2_enum_exists(self):
        """测试练五休二枚举存在 - Requirements 2.1"""
        assert hasattr(RestPattern, 'TRAIN_5_REST_2')
        assert RestPattern.TRAIN_5_REST_2.value == "train_5_rest_2"
    
    def test_train_4_rest_1_enum_exists(self):
        """测试练四休一枚举存在 - Requirements 2.2"""
        assert hasattr(RestPattern, 'TRAIN_4_REST_1')
        assert RestPattern.TRAIN_4_REST_1.value == "train_4_rest_1"
    
    def test_train_3_rest_1_enum_exists(self):
        """测试练三休一枚举存在 - Requirements 2.3"""
        assert hasattr(RestPattern, 'TRAIN_3_REST_1')
        assert RestPattern.TRAIN_3_REST_1.value == "train_3_rest_1"
    
    def test_train_6_rest_1_enum_exists(self):
        """测试练六休一枚举存在"""
        assert hasattr(RestPattern, 'TRAIN_6_REST_1')
        assert RestPattern.TRAIN_6_REST_1.value == "train_6_rest_1"
    
    def test_train_2_rest_1_enum_exists(self):
        """测试练二休一枚举存在"""
        assert hasattr(RestPattern, 'TRAIN_2_REST_1')
        assert RestPattern.TRAIN_2_REST_1.value == "train_2_rest_1"
    
    def test_train_1_rest_1_enum_exists(self):
        """测试练一休一枚举存在"""
        assert hasattr(RestPattern, 'TRAIN_1_REST_1')
        assert RestPattern.TRAIN_1_REST_1.value == "train_1_rest_1"
    
    def test_mon_wed_fri_enum_exists(self):
        """测试周一三五枚举存在 - Requirements 2.4"""
        assert hasattr(RestPattern, 'MON_WED_FRI')
        assert RestPattern.MON_WED_FRI.value == "mon_wed_fri"
    
    def test_tue_thu_sat_enum_exists(self):
        """测试周二四六枚举存在 - Requirements 2.4"""
        assert hasattr(RestPattern, 'TUE_THU_SAT')
        assert RestPattern.TUE_THU_SAT.value == "tue_thu_sat"


class TestRestPatternCycleCalculation:
    """测试休息模式周期计算"""
    
    def test_train_5_rest_2_cycle(self, tool):
        """测试练五休二周期计算 - Requirements 2.1"""
        input_data = {
            "training_days_per_week": 5,
            "preferred_rest_pattern": "train_5_rest_2"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 7, "练五休二应为7天周期"
        assert cycle_info["training_pattern"] == "练五休二（周末休息）"
        assert cycle_info["rest_pattern"] == "train_5_rest_2"
    
    def test_train_4_rest_1_cycle(self, tool):
        """测试练四休一周期计算 - Requirements 2.2"""
        input_data = {
            "training_days_per_week": 4,
            "preferred_rest_pattern": "train_4_rest_1"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 5, "练四休一应为5天周期"
        assert cycle_info["training_pattern"] == "练四休一"
        assert cycle_info["rest_pattern"] == "train_4_rest_1"
    
    def test_train_3_rest_1_cycle(self, tool):
        """测试练三休一周期计算 - Requirements 2.3"""
        input_data = {
            "training_days_per_week": 3,
            "preferred_rest_pattern": "train_3_rest_1"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 4, "练三休一应为4天周期"
        assert cycle_info["training_pattern"] == "练三休一"
        assert cycle_info["rest_pattern"] == "train_3_rest_1"
    
    def test_train_6_rest_1_cycle(self, tool):
        """测试练六休一周期计算"""
        input_data = {
            "training_days_per_week": 6,
            "preferred_rest_pattern": "train_6_rest_1"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 7, "练六休一应为7天周期"
        assert cycle_info["training_pattern"] == "练六休一"
        assert cycle_info["rest_pattern"] == "train_6_rest_1"
    
    def test_train_2_rest_1_cycle(self, tool):
        """测试练二休一周期计算"""
        input_data = {
            "training_days_per_week": 4,
            "preferred_rest_pattern": "train_2_rest_1"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 3, "练二休一应为3天周期"
        assert cycle_info["training_pattern"] == "练二休一"
        assert cycle_info["rest_pattern"] == "train_2_rest_1"
    
    def test_train_1_rest_1_cycle(self, tool):
        """测试练一休一周期计算"""
        input_data = {
            "training_days_per_week": 3,
            "preferred_rest_pattern": "train_1_rest_1"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 2, "练一休一应为2天周期"
        assert cycle_info["training_pattern"] == "练一休一（隔日训练）"
        assert cycle_info["rest_pattern"] == "train_1_rest_1"
    
    def test_mon_wed_fri_cycle(self, tool):
        """测试周一三五周期计算 - Requirements 2.4"""
        input_data = {
            "training_days_per_week": 3,
            "preferred_rest_pattern": "mon_wed_fri"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 7, "周一三五应为7天周期"
        assert cycle_info["training_pattern"] == "周一三五"
        assert cycle_info["rest_pattern"] == "mon_wed_fri"


class TestStudentRestPatternRecommendation:
    """测试大学生休息模式推荐 - Requirements 2.4"""
    
    def test_student_3_days_recommends_alternate_day(self, tool):
        """测试大学生每周3天推荐隔日训练"""
        input_data = {
            "training_days_per_week": 3,
            "training_level": "beginner",
            "primary_goal": "hypertrophy",
            "user_type": "student"
        }
        
        # 测试周期计算中的大学生推荐
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["training_pattern"] == "隔日训练（周一三五）"
        assert cycle_info["rest_pattern"] == "mon_wed_fri"
        assert cycle_info.get("recommended_for_student") is True
    
    def test_student_rest_pattern_recommendation(self, tool):
        """测试大学生休息模式推荐方法"""
        input_data = {
            "training_days_per_week": 3,
            "user_type": "student"
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "mon_wed_fri"
        assert "周一三五" in recommendation["pattern_name"]
        assert "大学生" in recommendation["reason"]


class TestWorkerRestPatternRecommendation:
    """测试上班族休息模式推荐"""
    
    def test_worker_5_days_recommends_train_5_rest_2(self, tool):
        """测试上班族每周5天推荐练五休二"""
        input_data = {
            "training_days_per_week": 5,
            "user_type": "worker"
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_5_rest_2"
        assert "周末休息" in recommendation["pattern_name"]


class TestSplitTypeRestPatternRecommendation:
    """测试根据分化类型智能推荐休息模式 - Requirements 2.5"""
    
    def test_push_pull_legs_3_days_recommends_train_3_rest_1(self, tool):
        """测试推拉腿3天推荐练三休一"""
        input_data = {
            "training_days_per_week": 3,
            "preferred_split_type": "push_pull_legs"
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_3_rest_1"
        assert "练三休一" in recommendation["pattern_name"]
    
    def test_push_pull_legs_6_days_recommends_train_6_rest_1(self, tool):
        """测试推拉腿6天推荐练六休一"""
        input_data = {
            "training_days_per_week": 6,
            "preferred_split_type": "push_pull_legs"
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_6_rest_1"
        assert "练六休一" in recommendation["pattern_name"]
    
    def test_antagonist_4_days_recommends_train_4_rest_1(self, tool):
        """测试拮抗肌分化4天推荐练四休一"""
        input_data = {
            "training_days_per_week": 4,
            "preferred_split_type": "antagonist"
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_4_rest_1"
        assert "练四休一" in recommendation["pattern_name"]
    
    def test_upper_lower_4_days_recommends_train_2_rest_1(self, tool):
        """测试上下肢分化4天推荐练二休一"""
        input_data = {
            "training_days_per_week": 4,
            "preferred_split_type": "upper_lower"
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_2_rest_1"
        assert "练二休一" in recommendation["pattern_name"]
    
    def test_full_body_3_days_recommends_train_1_rest_1(self, tool):
        """测试全身训练3天推荐练一休一"""
        input_data = {
            "training_days_per_week": 3,
            "preferred_split_type": "full_body"
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_1_rest_1"
        assert "练一休一" in recommendation["pattern_name"]
    
    def test_bro_split_5_days_recommends_train_5_rest_2(self, tool):
        """测试部位分化5天推荐练五休二"""
        input_data = {
            "training_days_per_week": 5,
            "preferred_split_type": "bro_split"
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_5_rest_2"
        assert "周末休息" in recommendation["pattern_name"]


class TestDefaultRestPatternRecommendation:
    """测试默认休息模式推荐"""
    
    def test_default_2_days_recommends_train_2_rest_1(self, tool):
        """测试默认2天推荐练二休一"""
        input_data = {
            "training_days_per_week": 2
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_2_rest_1"
    
    def test_default_3_days_recommends_train_3_rest_1(self, tool):
        """测试默认3天推荐练三休一"""
        input_data = {
            "training_days_per_week": 3
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_3_rest_1"
    
    def test_default_4_days_recommends_train_4_rest_1(self, tool):
        """测试默认4天推荐练四休一"""
        input_data = {
            "training_days_per_week": 4
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_4_rest_1"
    
    def test_default_5_days_recommends_train_5_rest_2(self, tool):
        """测试默认5天推荐练五休二"""
        input_data = {
            "training_days_per_week": 5
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_5_rest_2"
    
    def test_default_6_days_recommends_train_6_rest_1(self, tool):
        """测试默认6天推荐练六休一"""
        input_data = {
            "training_days_per_week": 6
        }
        
        recommendation = tool.recommend_rest_pattern(input_data)
        
        assert recommendation["recommended_pattern"] == "train_6_rest_1"


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_train_5_rest_2_full_execution(self, tool):
        """测试练五休二完整执行"""
        input_data = {
            "user_id": "test_worker_001",
            "training_level": "intermediate",
            "primary_goal": "hypertrophy",
            "training_days_per_week": 5,
            "session_duration_minutes": 60,
            "available_equipment": ["杠铃", "哑铃", "拉力器"],
            "preferred_rest_pattern": "train_5_rest_2",
            "include_cardio": True,
            "rest_day_preference": "spread_out",
            "user_type": "worker"
        }
        
        result = await tool.execute(input_data)
        
        assert result["success"] is True
        assert result["cycle_info"]["rest_pattern"] == "train_5_rest_2"
        assert result["cycle_info"]["training_pattern"] == "练五休二（周末休息）"
    
    @pytest.mark.asyncio
    async def test_student_alternate_day_full_execution(self, tool):
        """测试大学生隔日训练完整执行"""
        input_data = {
            "user_id": "test_student_001",
            "training_level": "beginner",
            "primary_goal": "hypertrophy",
            "training_days_per_week": 3,
            "session_duration_minutes": 45,
            "available_equipment": ["哑铃"],
            "user_type": "student",
            "include_cardio": True,
            "rest_day_preference": "spread_out"
        }
        
        result = await tool.execute(input_data)
        
        assert result["success"] is True
        # 大学生3天训练应推荐隔日训练
        assert result["cycle_info"]["rest_pattern"] == "mon_wed_fri"
        assert "隔日训练" in result["cycle_info"]["training_pattern"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
