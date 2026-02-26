# -*- coding: utf-8 -*-
"""
MCP工具参数修复验证测试

验证：
1. 所有参数构建器都存在
2. 参数构建器返回正确的参数
3. 成功判断逻辑正确

更新日期: 2025-12-29
更新说明: 适配重构后的TaskParamBuilder API
"""

import pytest
from src.applications.fitness.dag.task_executor import TaskParamBuilder


class TestMCPParamsFix:
    """MCP工具参数修复验证"""
    
    @pytest.fixture
    def user_profile(self):
        """测试用户档案"""
        return {
            "user_id": 2,
            "fitness_goals": ["增肌"],
            "fitness_level": "beginner",
            "preferred_training_days": 3,
            "target_muscle_groups": ["胸部", "背部"],
            "activity_level": "moderate"
        }
    
    @pytest.fixture
    def param_builder(self, user_profile):
        """创建参数构建器实例"""
        return TaskParamBuilder(user_profile)
    
    def test_periodized_program_params_builder_exists(self, param_builder):
        """测试周期化训练计划参数构建器存在"""
        params = param_builder.build_params("periodized_program_designer")
        
        assert "training_goal" in params
        assert "program_duration_weeks" in params
        assert "difficulty_level" in params
        assert params["training_goal"] == "hypertrophy"  # 增肌映射为hypertrophy
        assert params["program_duration_weeks"] == 12
        print(f"✅ periodized_program_designer 参数构建器正常")
    
    def test_training_split_params_builder_exists(self, param_builder):
        """测试训练分化参数构建器存在"""
        params = param_builder.build_params("training_split_designer")
        
        assert "training_days_per_week" in params
        assert "training_level" in params
        assert "primary_goal" in params
        assert params["training_days_per_week"] == 3
        assert params["training_level"] == "beginner"
        print(f"✅ training_split_designer 参数构建器正常")
    
    def test_contraindications_params_builder_exists(self, param_builder):
        """测试禁忌症检查参数构建器存在"""
        params = param_builder.build_params("contraindications_checker")
        
        assert "exercise_ids" in params
        assert "strict_mode" in params
        assert params["strict_mode"] is True
        print(f"✅ contraindications_checker 参数构建器正常")
    
    def test_injury_risk_params_builder_exists(self, param_builder):
        """测试损伤风险评估参数构建器存在"""
        params = param_builder.build_params("injury_risk_assessor")
        
        assert "planned_exercises" in params
        assert "include_prevention_plan" in params
        assert params["include_prevention_plan"] is True
        print(f"✅ injury_risk_assessor 参数构建器正常")
    
    def test_movement_pattern_params_builder_exists(self, param_builder):
        """测试动作模式平衡参数构建器存在"""
        params = param_builder.build_params("movement_pattern_balancer")
        
        assert "current_program" in params
        assert "target_muscle_groups" in params
        print(f"✅ movement_pattern_balancer 参数构建器正常")
    
    def test_tdee_params_builder_exists(self, param_builder):
        """测试TDEE计算参数构建器存在"""
        params = param_builder.build_params("tdee_calculator")
        
        assert "daily_activity_level" in params
        assert "fitness_goal" in params
        assert params["daily_activity_level"] == "moderate"
        assert params["fitness_goal"] == "hypertrophy"
        print(f"✅ tdee_calculator 参数构建器正常")
    
    def test_program_designer_params_fixed(self, param_builder):
        """测试专业训练计划参数名修复"""
        params = param_builder.build_params("professional_program_designer")
        
        # 验证使用正确的参数名
        assert "training_goal" in params
        assert params["training_goal"] == "hypertrophy"  # 增肌映射为hypertrophy
        print(f"✅ professional_program_designer 参数名已修复")
    
    def test_all_param_builders_return_dict(self, param_builder):
        """测试所有参数构建器都返回字典"""
        tool_names = [
            "periodized_program_designer",
            "training_split_designer",
            "contraindications_checker",
            "injury_risk_assessor",
            "movement_pattern_balancer",
            "tdee_calculator",
            "professional_program_designer"
        ]
        
        for tool_name in tool_names:
            params = param_builder.build_params(tool_name)
            assert isinstance(params, dict), f"{tool_name} 应返回字典"
            assert "user_id" in params, f"{tool_name} 应包含 user_id"
            assert "user_profile" in params, f"{tool_name} 应包含 user_profile"
        
        print(f"✅ 所有参数构建器都返回正确的字典格式")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
