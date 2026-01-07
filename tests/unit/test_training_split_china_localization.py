"""
训练分化中国本地化测试

测试新增的分化类型和大学生推荐逻辑：
- 胸背分化 (chest_back)
- 拮抗肌分化 (antagonist)
- 阿诺德分化 (arnold_split)
- 大学生用户推荐逻辑

Requirements: 1.1, 1.2, 1.3, 1.4
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.applications.fitness.mcp_tools.training.training_split_designer import (
    TrainingSplitDesigner,
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


class TestSplitTypeEnum:
    """测试分化类型枚举"""
    
    def test_chest_back_enum_exists(self):
        """测试胸背分化枚举存在 - Requirements 1.1"""
        assert hasattr(SplitType, 'CHEST_BACK')
        assert SplitType.CHEST_BACK.value == "chest_back"
    
    def test_antagonist_enum_exists(self):
        """测试拮抗肌分化枚举存在 - Requirements 1.2"""
        assert hasattr(SplitType, 'ANTAGONIST')
        assert SplitType.ANTAGONIST.value == "antagonist"
    
    def test_arnold_split_enum_exists(self):
        """测试阿诺德分化枚举存在 - Requirements 1.3"""
        assert hasattr(SplitType, 'ARNOLD_SPLIT')
        assert SplitType.ARNOLD_SPLIT.value == "arnold_split"


class TestUserTypeEnum:
    """测试用户类型枚举"""
    
    def test_student_enum_exists(self):
        """测试大学生用户类型枚举存在"""
        assert hasattr(UserType, 'STUDENT')
        assert UserType.STUDENT.value == "student"
    
    def test_worker_enum_exists(self):
        """测试上班族用户类型枚举存在"""
        assert hasattr(UserType, 'WORKER')
        assert UserType.WORKER.value == "worker"


class TestGenerateSplitOptions:
    """测试分化选项生成"""
    
    def test_chest_back_option_for_3_days(self, tool):
        """测试3天训练时包含胸背分化选项 - Requirements 1.1"""
        input_data = {
            "training_days_per_week": 3,
            "training_level": "intermediate",
            "primary_goal": "hypertrophy"
        }
        
        options = tool._generate_split_options(input_data)
        
        # 检查是否包含胸背分化选项
        chest_back_option = next(
            (opt for opt in options if opt["type"] == "chest_back"),
            None
        )
        
        assert chest_back_option is not None, "3天训练应该包含胸背分化选项"
        assert chest_back_option["name"] == "胸背分化"
        assert len(chest_back_option["sessions"]) == 3
        assert "胸背日" in chest_back_option["sessions"][0]
    
    def test_antagonist_option_for_4_days(self, tool):
        """测试4天训练时包含拮抗肌分化选项 - Requirements 1.2"""
        input_data = {
            "training_days_per_week": 4,
            "training_level": "intermediate",
            "primary_goal": "hypertrophy"
        }
        
        options = tool._generate_split_options(input_data)
        
        # 检查是否包含拮抗肌分化选项
        antagonist_option = next(
            (opt for opt in options if opt["type"] == "antagonist"),
            None
        )
        
        assert antagonist_option is not None, "4天训练应该包含拮抗肌分化选项"
        assert antagonist_option["name"] == "拮抗肌分化"
        assert antagonist_option["split_sessions"] == 4
    
    def test_arnold_split_option_for_6_days(self, tool):
        """测试6天训练时包含阿诺德分化选项 - Requirements 1.3"""
        input_data = {
            "training_days_per_week": 6,
            "training_level": "advanced",
            "primary_goal": "hypertrophy"
        }
        
        options = tool._generate_split_options(input_data)
        
        # 检查是否包含阿诺德分化选项
        arnold_option = next(
            (opt for opt in options if opt["type"] == "arnold_split"),
            None
        )
        
        assert arnold_option is not None, "6天训练应该包含阿诺德分化选项"
        assert arnold_option["name"] == "阿诺德分化"
        assert arnold_option["split_sessions"] == 6


class TestStudentRecommendation:
    """测试大学生用户推荐逻辑 - Requirements 1.4"""
    
    def test_student_3_days_recommends_full_body(self, tool):
        """测试大学生每周3天推荐全身训练"""
        input_data = {
            "training_days_per_week": 3,
            "training_level": "beginner",
            "primary_goal": "hypertrophy",
            "user_type": "student"
        }
        
        options = tool._generate_split_options(input_data)
        selected = tool._select_optimal_split(options, input_data)
        
        assert selected["type"] == "full_body", "大学生每周3天应推荐全身训练"
    
    def test_student_4_days_recommends_upper_lower(self, tool):
        """测试大学生每周4天推荐上下肢分化"""
        input_data = {
            "training_days_per_week": 4,
            "training_level": "intermediate",
            "primary_goal": "hypertrophy",
            "user_type": "student"
        }
        
        options = tool._generate_split_options(input_data)
        selected = tool._select_optimal_split(options, input_data)
        
        assert selected["type"] == "upper_lower", "大学生每周4天应推荐上下肢分化"
    
    def test_student_preference_overrides_recommendation(self, tool):
        """测试用户偏好优先于推荐"""
        input_data = {
            "training_days_per_week": 3,
            "training_level": "intermediate",
            "primary_goal": "hypertrophy",
            "user_type": "student",
            "preferred_split_type": "push_pull_legs"  # 用户明确选择推拉腿
        }
        
        options = tool._generate_split_options(input_data)
        selected = tool._select_optimal_split(options, input_data)
        
        assert selected["type"] == "push_pull_legs", "用户偏好应优先于推荐"


class TestTrainingCycleCalculation:
    """测试训练周期计算"""
    
    def test_chest_back_cycle_calculation(self, tool):
        """测试胸背分化周期计算"""
        input_data = {
            "training_days_per_week": 3,
            "preferred_split_type": "chest_back"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 4, "胸背分化3天应为4天周期"
        assert cycle_info["training_pattern"] == "练三休一"
    
    def test_antagonist_cycle_calculation(self, tool):
        """测试拮抗肌分化周期计算"""
        input_data = {
            "training_days_per_week": 4,
            "preferred_split_type": "antagonist"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 5, "拮抗肌分化4天应为5天周期"
        assert cycle_info["training_pattern"] == "练四休一"
    
    def test_arnold_split_cycle_calculation(self, tool):
        """测试阿诺德分化周期计算"""
        input_data = {
            "training_days_per_week": 6,
            "preferred_split_type": "arnold_split"
        }
        
        cycle_info = tool._calculate_training_cycle(input_data)
        
        assert cycle_info["cycle_days"] == 7, "阿诺德分化应为7天周期"
        assert cycle_info["training_pattern"] == "练六休一"


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_chest_back_full_execution(self, tool):
        """测试胸背分化完整执行"""
        input_data = {
            "user_id": "test_student_001",
            "training_level": "intermediate",
            "primary_goal": "hypertrophy",
            "training_days_per_week": 3,
            "session_duration_minutes": 60,
            "available_equipment": ["杠铃", "哑铃", "拉力器"],
            "preferred_split_type": "chest_back",
            "include_cardio": True,
            "rest_day_preference": "spread_out"
        }
        
        result = await tool.execute(input_data)
        
        assert result["success"] is True
        assert result["split_plan"]["split_type"] == "chest_back"
        assert result["split_plan"]["split_name"] == "胸背分化"
    
    @pytest.mark.asyncio
    async def test_student_recommendation_full_execution(self, tool):
        """测试大学生推荐完整执行"""
        input_data = {
            "user_id": "test_student_002",
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
        # 大学生3天训练应推荐全身训练
        assert result["split_plan"]["split_type"] == "full_body"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
