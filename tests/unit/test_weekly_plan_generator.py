# -*- coding: utf-8 -*-
"""
WeeklyPlanGenerator单元测试

测试分周计划生成器的核心功能

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import pytest
from src.applications.fitness.services.weekly_plan_generator import (
    WeeklyPlanGenerator,
    WeeklyPlan,
    WeeklyPlanMetadata,
    PeriodizationPhase
)


class TestWeeklyPlanGenerator:
    """WeeklyPlanGenerator测试类"""
    
    @pytest.fixture
    def generator(self):
        """创建WeeklyPlanGenerator实例"""
        return WeeklyPlanGenerator()
    
    @pytest.fixture
    def sample_full_program(self):
        """创建示例完整训练计划"""
        return {
            "success": True,
            "program_overview": {
                "training_goal": "hypertrophy",
                "training_split": "push_pull_legs",
                "training_days_per_week": 3,
                "training_weeks": 4
            },
            "weekly_program": {
                "week_number": 1,
                "training_days": [
                    {
                        "day_number": 1,
                        "day_name": "推日",
                        "focus_muscle_groups": ["胸大肌", "三角肌", "肱三头肌"],
                        "exercises": [
                            {
                                "exercise_id": "ex_001",
                                "name_zh": "杠铃卧推",
                                "name_en": "Barbell Bench Press",
                                "sets": 4,
                                "reps_range": (8, 12),
                                "rest_seconds": 90,
                                "primary_muscles": ["胸大肌"],
                                "safety_level": "MODERATE",
                                "safety_notes": []
                            },
                            {
                                "exercise_id": "ex_002",
                                "name_zh": "哑铃肩推",
                                "name_en": "Dumbbell Shoulder Press",
                                "sets": 3,
                                "reps_range": (10, 12),
                                "rest_seconds": 60,
                                "primary_muscles": ["三角肌"],
                                "safety_level": "LOW",
                                "safety_notes": []
                            }
                        ],
                        "total_sets": 7,
                        "estimated_duration_minutes": 45,
                        "notes": ["专注于胸肩训练"]
                    },
                    {
                        "day_number": 3,
                        "day_name": "拉日",
                        "focus_muscle_groups": ["背阔肌", "肱二头肌"],
                        "exercises": [
                            {
                                "exercise_id": "ex_003",
                                "name_zh": "引体向上",
                                "name_en": "Pull-up",
                                "sets": 4,
                                "reps_range": (6, 10),
                                "rest_seconds": 120,
                                "primary_muscles": ["背阔肌"],
                                "safety_level": "LOW",
                                "safety_notes": []
                            }
                        ],
                        "total_sets": 4,
                        "estimated_duration_minutes": 30,
                        "notes": ["专注于背部训练"]
                    }
                ],
                "rest_days": [2, 4, 5, 6, 7],
                "total_weekly_sets": 11
            }
        }
    
    def test_generate_first_week_basic(self, generator, sample_full_program):
        """测试生成第1周计划的基本功能"""
        # 执行
        weekly_plan = generator.generate_first_week(
            full_program=sample_full_program,
            user_profile=None,
            total_weeks=4
        )
        
        # 验证
        assert isinstance(weekly_plan, WeeklyPlan)
        assert weekly_plan.metadata.week_number == 1
        assert weekly_plan.metadata.total_weeks == 4
        assert weekly_plan.metadata.is_first_week is True
        assert weekly_plan.metadata.phase == PeriodizationPhase.ACCUMULATION
        assert weekly_plan.metadata.phase_name_zh == "积累期"
    
    def test_generate_first_week_with_user_profile(self, generator, sample_full_program):
        """测试带用户档案的第1周计划生成"""
        user_profile = {
            "personal_volume_multiplier": 1.2,
            "fitness_goal": "hypertrophy"
        }
        
        # 执行
        weekly_plan = generator.generate_first_week(
            full_program=sample_full_program,
            user_profile=user_profile,
            total_weeks=4
        )
        
        # 验证
        assert weekly_plan.metadata.volume_multiplier == 1.2
    
    def test_cycle_explanation_first_week(self, generator, sample_full_program):
        """测试第1周的周期说明文案"""
        # 执行
        weekly_plan = generator.generate_first_week(
            full_program=sample_full_program,
            total_weeks=4
        )
        
        # 验证 - Requirements: 10.2
        assert "4周周期的第一周" in weekly_plan.cycle_explanation
        assert "积累期" in weekly_plan.cycle_explanation
        assert "后续每周根据您的完成反馈" in weekly_plan.cycle_explanation
    
    def test_convert_to_output_format(self, generator, sample_full_program):
        """测试转换为输出格式"""
        # 生成计划
        weekly_plan = generator.generate_first_week(
            full_program=sample_full_program,
            total_weeks=4
        )
        
        # 转换为输出格式
        output = generator.convert_to_output_format(weekly_plan)
        
        # 验证输出格式
        assert "week_number" in output
        assert "total_weeks" in output
        assert "phase" in output
        assert "training_days" in output
        assert "cycle_explanation" in output
        assert output["week_number"] == 1
        assert output["total_weeks"] == 4
    
    def test_apply_volume_multiplier(self, generator, sample_full_program):
        """测试应用容量系数"""
        # 执行
        adjusted_plan = generator.apply_volume_multiplier(
            base_plan=sample_full_program["weekly_program"],
            multiplier=0.8
        )
        
        # 验证 - 组数应该减少
        original_sets = sample_full_program["weekly_program"]["total_weekly_sets"]
        adjusted_sets = adjusted_plan["total_weekly_sets"]
        assert adjusted_sets < original_sets
    
    def test_volume_multiplier_bounds(self, generator, sample_full_program):
        """测试容量系数边界约束"""
        # 测试下限
        adjusted_plan_low = generator.apply_volume_multiplier(
            base_plan=sample_full_program["weekly_program"],
            multiplier=0.5  # 低于下限0.7
        )
        # 应该被限制在0.7
        
        # 测试上限
        adjusted_plan_high = generator.apply_volume_multiplier(
            base_plan=sample_full_program["weekly_program"],
            multiplier=2.0  # 高于上限1.5
        )
        # 应该被限制在1.5
        
        # 验证计划仍然有效
        assert adjusted_plan_low["total_weekly_sets"] > 0
        assert adjusted_plan_high["total_weekly_sets"] > 0
    
    def test_insert_deload_week(self, generator, sample_full_program):
        """测试生成Deload周计划"""
        # 执行
        deload_plan = generator.insert_deload_week(
            base_program=sample_full_program,
            week_number=4,
            total_weeks=4
        )
        
        # 验证
        assert deload_plan.metadata.is_deload_week is True
        assert deload_plan.metadata.phase == PeriodizationPhase.DELOAD
        assert "减量" in deload_plan.cycle_explanation
    
    def test_calculate_volume_adjustment_increase(self, generator):
        """测试容量上调条件 - Requirements: 7.2"""
        # RPE < 7 且 完成率 > 95%
        adjustment = generator._calculate_volume_adjustment(
            completion_rate=0.98,
            avg_rpe=6.0
        )
        
        # 验证调整值在+0.05到+0.1之间
        assert 0.05 <= adjustment <= 0.1
    
    def test_calculate_volume_adjustment_decrease(self, generator):
        """测试容量下调条件 - Requirements: 7.3"""
        # RPE > 9.5 或 完成率 < 80%
        adjustment = generator._calculate_volume_adjustment(
            completion_rate=0.75,
            avg_rpe=9.8
        )
        
        # 验证调整值在-0.1到-0.15之间
        assert -0.15 <= adjustment <= -0.1
    
    def test_calculate_volume_adjustment_maintain(self, generator):
        """测试容量保持条件"""
        # 正常范围内
        adjustment = generator._calculate_volume_adjustment(
            completion_rate=0.90,
            avg_rpe=7.5
        )
        
        # 验证调整值接近0
        assert -0.05 <= adjustment <= 0.05
    
    def test_should_force_deload(self, generator):
        """测试强制Deload判断 - Requirements: 9.2"""
        # 连续两周高RPE
        should_deload = generator._should_force_deload(
            completion_rate=0.80,
            avg_rpe=9.2,
            last_week_feedback={
                "previous_avg_rpe": 9.3,
                "previous_completion_rate": 0.82
            }
        )
        
        assert should_deload is True
    
    def test_should_not_force_deload(self, generator):
        """测试不需要强制Deload的情况"""
        should_deload = generator._should_force_deload(
            completion_rate=0.92,
            avg_rpe=7.5,
            last_week_feedback={
                "previous_avg_rpe": 7.2,
                "previous_completion_rate": 0.95
            }
        )
        
        assert should_deload is False
    
    def test_phase_config_week_1(self, generator):
        """测试第1周阶段配置"""
        config = generator.PHASE_CONFIG[1]
        assert config["phase"] == PeriodizationPhase.ACCUMULATION
        assert config["name_zh"] == "积累期"
        assert config["volume_factor"] == 1.0
    
    def test_phase_config_week_3(self, generator):
        """测试第3周阶段配置（冲刺期）"""
        config = generator.PHASE_CONFIG[3]
        assert config["phase"] == PeriodizationPhase.INTENSIFICATION
        assert config["name_zh"] == "冲刺期"
        assert config["volume_factor"] == 1.2
    
    def test_phase_config_week_4(self, generator):
        """测试第4周阶段配置（减量期）"""
        config = generator.PHASE_CONFIG[4]
        assert config["phase"] == PeriodizationPhase.DELOAD
        assert config["name_zh"] == "减量期"
        assert config["volume_factor"] == 0.6


class TestWeeklyPlanGeneratorAsync:
    """WeeklyPlanGenerator异步方法测试类"""
    
    @pytest.fixture
    def generator(self):
        """创建WeeklyPlanGenerator实例"""
        return WeeklyPlanGenerator()
    
    @pytest.fixture
    def sample_full_program(self):
        """创建示例完整训练计划"""
        return {
            "success": True,
            "program_overview": {
                "training_goal": "hypertrophy",
                "training_split": "push_pull_legs",
                "training_days_per_week": 3,
                "training_weeks": 4
            },
            "weekly_program": {
                "week_number": 1,
                "training_days": [
                    {
                        "day_number": 1,
                        "day_name": "推日",
                        "focus_muscle_groups": ["胸大肌"],
                        "exercises": [
                            {
                                "exercise_id": "ex_001",
                                "name_zh": "杠铃卧推",
                                "name_en": "Barbell Bench Press",
                                "sets": 4,
                                "reps_range": (8, 12),
                                "rest_seconds": 90,
                                "primary_muscles": ["胸大肌"],
                                "safety_level": "MODERATE",
                                "safety_notes": []
                            }
                        ],
                        "total_sets": 4,
                        "estimated_duration_minutes": 30,
                        "notes": []
                    }
                ],
                "rest_days": [2, 3, 4, 5, 6, 7],
                "total_weekly_sets": 4
            }
        }
    
    @pytest.mark.asyncio
    async def test_generate_next_week(self, generator, sample_full_program):
        """测试生成下周计划"""
        # 准备反馈数据
        last_week_feedback = {
            "completion_rate": 0.92,
            "avg_rpe": 7.5,
            "previous_avg_rpe": 7.0,
            "previous_completion_rate": 0.90
        }
        
        # 执行
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=last_week_feedback,
            base_program=sample_full_program,
            user_profile=None
        )
        
        # 验证
        assert isinstance(weekly_plan, WeeklyPlan)
        assert weekly_plan.metadata.week_number == 2
        assert weekly_plan.metadata.is_first_week is False
    
    @pytest.mark.asyncio
    async def test_generate_next_week_with_force_deload(self, generator, sample_full_program):
        """测试强制Deload的下周计划生成"""
        # 准备高疲劳反馈数据
        last_week_feedback = {
            "completion_rate": 0.75,
            "avg_rpe": 9.5,
            "previous_avg_rpe": 9.3,
            "previous_completion_rate": 0.78
        }
        
        # 执行
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=last_week_feedback,
            base_program=sample_full_program,
            user_profile=None
        )
        
        # 验证 - 应该强制进入Deload
        assert weekly_plan.metadata.is_deload_week is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
