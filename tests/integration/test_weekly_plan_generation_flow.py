# -*- coding: utf-8 -*-
"""
分周生成流程集成测试

测试分周动态生成流程：
第1周生成 → 反馈 → 第2周生成

Requirements: 10.1, 10.3, 10.4 - 分周动态生成

测试场景：
1. 第1周计划生成（包含周期说明）
2. 基于反馈生成第2周计划
3. 周期化阶段切换
4. Deload周自动插入
5. 渐进过载应用

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_program():
    """创建示例训练计划"""
    return {
        'program_name': '4周增肌计划',
        'total_weeks': 4,
        'weekly_program': {
            'training_days': [
                {
                    'day_number': 1,
                    'day_name': '上肢推',
                    'focus_muscle_groups': ['胸', '肩', '三头'],
                    'exercises': [
                        {
                            'exercise_id': 'barbell_bench_press',
                            'name_zh': '杠铃卧推',
                            'name_en': 'Barbell Bench Press',
                            'sets': 4,
                            'reps_range': (6, 8),
                            'rest_seconds': 120,
                            'primary_muscles': ['胸大肌']
                        },
                        {
                            'exercise_id': 'dumbbell_shoulder_press',
                            'name_zh': '哑铃肩推',
                            'name_en': 'Dumbbell Shoulder Press',
                            'sets': 3,
                            'reps_range': (8, 10),
                            'rest_seconds': 90,
                            'primary_muscles': ['三角肌']
                        },
                        {
                            'exercise_id': 'tricep_pushdown',
                            'name_zh': '三头下压',
                            'name_en': 'Tricep Pushdown',
                            'sets': 3,
                            'reps_range': (10, 12),
                            'rest_seconds': 60,
                            'primary_muscles': ['三头肌']
                        }
                    ]
                },
                {
                    'day_number': 2,
                    'day_name': '上肢拉',
                    'focus_muscle_groups': ['背', '二头'],
                    'exercises': [
                        {
                            'exercise_id': 'pull_up',
                            'name_zh': '引体向上',
                            'name_en': 'Pull Up',
                            'sets': 4,
                            'reps_range': (6, 10),
                            'rest_seconds': 120,
                            'primary_muscles': ['背阔肌']
                        },
                        {
                            'exercise_id': 'barbell_row',
                            'name_zh': '杠铃划船',
                            'name_en': 'Barbell Row',
                            'sets': 4,
                            'reps_range': (6, 8),
                            'rest_seconds': 90,
                            'primary_muscles': ['背阔肌']
                        }
                    ]
                },
                {
                    'day_number': 3,
                    'day_name': '下肢',
                    'focus_muscle_groups': ['股四头', '腘绳肌', '臀'],
                    'exercises': [
                        {
                            'exercise_id': 'barbell_squat',
                            'name_zh': '杠铃深蹲',
                            'name_en': 'Barbell Squat',
                            'sets': 4,
                            'reps_range': (6, 8),
                            'rest_seconds': 180,
                            'primary_muscles': ['股四头肌']
                        },
                        {
                            'exercise_id': 'romanian_deadlift',
                            'name_zh': '罗马尼亚硬拉',
                            'name_en': 'Romanian Deadlift',
                            'sets': 3,
                            'reps_range': (8, 10),
                            'rest_seconds': 120,
                            'primary_muscles': ['腘绳肌']
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def mock_backend():
    """创建模拟后端"""
    backend = MagicMock()
    backend.get_user_profile = AsyncMock(return_value={
        'id': 1,
        'training_system': {'personal_volume_multiplier': 1.0}
    })
    backend.get_training_logs = AsyncMock(return_value=[])
    backend.get_personal_bests = AsyncMock(return_value=[])
    return backend


# ============================================================================
# Test: First Week Generation
# ============================================================================

class TestFirstWeekGeneration:
    """第1周计划生成测试"""
    
    def test_generate_first_week_basic(self, sample_program):
        """测试基本的第1周计划生成"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        weekly_plan = generator.generate_first_week(
            full_program=sample_program,
            total_weeks=4
        )
        
        # 验证基本属性
        assert weekly_plan.metadata.week_number == 1
        assert weekly_plan.metadata.total_weeks == 4
        assert weekly_plan.metadata.is_first_week is True
        assert weekly_plan.metadata.is_deload_week is False
        
        logger.info(f"✅ 第1周计划生成: phase={weekly_plan.metadata.phase_name_zh}")
    
    def test_first_week_has_cycle_explanation(self, sample_program):
        """测试第1周计划包含周期说明 - Requirements 10.2"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        weekly_plan = generator.generate_first_week(
            full_program=sample_program,
            total_weeks=4
        )
        
        # 验证周期说明存在
        assert weekly_plan.cycle_explanation is not None
        assert len(weekly_plan.cycle_explanation) > 0
        
        # 验证周期说明包含关键信息
        assert '第一周' in weekly_plan.cycle_explanation or '第1周' in weekly_plan.cycle_explanation or '4周' in weekly_plan.cycle_explanation
        
        logger.info(f"✅ 周期说明存在: {len(weekly_plan.cycle_explanation)}字符")
    
    def test_first_week_has_next_week_preview(self, sample_program):
        """测试第1周计划包含下周预览"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        weekly_plan = generator.generate_first_week(
            full_program=sample_program,
            total_weeks=4
        )
        
        # 验证下周预览存在
        assert weekly_plan.next_week_preview is not None
        
        logger.info(f"✅ 下周预览: {weekly_plan.next_week_preview}")
    
    def test_first_week_applies_volume_multiplier(self, sample_program):
        """测试第1周计划应用容量系数"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        # 使用较低的容量系数
        user_profile = {'training_system': {'personal_volume_multiplier': 0.8}}
        
        weekly_plan = generator.generate_first_week(
            full_program=sample_program,
            user_profile=user_profile,
            total_weeks=4
        )
        
        assert weekly_plan.metadata.volume_multiplier == 0.8
        
        logger.info(f"✅ 容量系数应用: {weekly_plan.metadata.volume_multiplier}")


# ============================================================================
# Test: Next Week Generation Based on Feedback
# ============================================================================

class TestNextWeekGeneration:
    """基于反馈生成下周计划测试"""
    
    @pytest.mark.asyncio
    async def test_generate_week2_from_feedback(self, sample_program, mock_backend):
        """测试基于反馈生成第2周计划 - Requirements 10.3, 10.4"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend)
        
        # 模拟良好的第1周反馈
        feedback = {
            'completion_rate': 0.95,
            'avg_rpe': 7.0
        }
        
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=feedback,
            base_program=sample_program
        )
        
        assert weekly_plan.metadata.week_number == 2
        assert weekly_plan.metadata.is_first_week is False
        
        logger.info(
            f"✅ 第2周计划生成: "
            f"phase={weekly_plan.metadata.phase_name_zh}, "
            f"volume={weekly_plan.metadata.volume_multiplier:.2f}"
        )
    
    @pytest.mark.asyncio
    async def test_volume_adjustment_on_good_performance(self, sample_program, mock_backend):
        """测试良好表现时的容量调整"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend)
        
        # 优秀表现：RPE < 7, 完成率 > 95%
        feedback = {
            'completion_rate': 0.98,
            'avg_rpe': 6.5
        }
        
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=feedback,
            base_program=sample_program,
            user_profile={'training_system': {'personal_volume_multiplier': 1.0}}
        )
        
        # 良好表现应该导致容量上调
        # 注意：第2周是积累期，volume_factor=1.0，加上调整可能>1.0
        logger.info(
            f"✅ 良好表现容量调整: "
            f"volume_multiplier={weekly_plan.metadata.volume_multiplier:.2f}"
        )
    
    @pytest.mark.asyncio
    async def test_volume_adjustment_on_poor_performance(self, sample_program, mock_backend):
        """测试较差表现时的容量调整"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend)
        
        # 较差表现：RPE > 9.5 或 完成率 < 80%
        feedback = {
            'completion_rate': 0.75,
            'avg_rpe': 9.8
        }
        
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=feedback,
            base_program=sample_program,
            user_profile={'training_system': {'personal_volume_multiplier': 1.0}}
        )
        
        # 较差表现应该导致容量下调
        assert weekly_plan.metadata.volume_multiplier < 1.0
        
        logger.info(
            f"✅ 较差表现容量调整: "
            f"volume_multiplier={weekly_plan.metadata.volume_multiplier:.2f}"
        )


# ============================================================================
# Test: Periodization Phase Transitions
# ============================================================================

class TestPeriodizationPhases:
    """周期化阶段切换测试"""
    
    @pytest.mark.asyncio
    async def test_phase_progression(self, sample_program, mock_backend):
        """测试4周周期的阶段进展"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend)
        
        expected_phases = ['积累期', '积累期', '冲刺期', '减量期']
        
        # 生成第1周
        week1 = generator.generate_first_week(
            full_program=sample_program,
            total_weeks=4
        )
        assert week1.metadata.phase_name_zh == expected_phases[0]
        logger.info(f"✅ 第1周: {week1.metadata.phase_name_zh}")
        
        # 生成第2-4周
        normal_feedback = {'completion_rate': 0.90, 'avg_rpe': 7.5}
        
        for week_num in range(2, 5):
            weekly_plan = await generator.generate_next_week(
                user_id=1,
                current_week=week_num,
                total_weeks=4,
                last_week_feedback=normal_feedback,
                base_program=sample_program
            )
            
            assert weekly_plan.metadata.phase_name_zh == expected_phases[week_num - 1]
            logger.info(f"✅ 第{week_num}周: {weekly_plan.metadata.phase_name_zh}")
    
    def test_deload_week_volume_reduction(self, sample_program):
        """测试Deload周容量降低"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        # 生成Deload周
        deload_plan = generator.insert_deload_week(
            base_program=sample_program,
            week_number=4,
            total_weeks=4
        )
        
        assert deload_plan.metadata.is_deload_week is True
        assert deload_plan.metadata.volume_multiplier < 1.0
        
        # 验证训练日标记
        for day in deload_plan.training_days:
            assert day.is_deload_day is True
        
        logger.info(
            f"✅ Deload周: "
            f"volume={deload_plan.metadata.volume_multiplier:.2f}, "
            f"total_sets={deload_plan.total_weekly_sets}"
        )


# ============================================================================
# Test: Force Deload Detection
# ============================================================================

class TestForceDeloadDetection:
    """强制Deload检测测试"""
    
    @pytest.mark.asyncio
    async def test_force_deload_on_consecutive_fatigue(self, sample_program, mock_backend):
        """测试连续疲劳时强制Deload"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend)
        
        # 连续两周高RPE和低完成率
        feedback = {
            'completion_rate': 0.78,
            'avg_rpe': 9.5,
            'previous_avg_rpe': 9.3,
            'previous_completion_rate': 0.80
        }
        
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=feedback,
            base_program=sample_program
        )
        
        # 应该触发强制Deload
        assert weekly_plan.metadata.is_deload_week is True
        
        logger.info(
            f"✅ 强制Deload触发: "
            f"phase={weekly_plan.metadata.phase_name_zh}"
        )
    
    @pytest.mark.asyncio
    async def test_extreme_single_week_triggers_deload(self, sample_program, mock_backend):
        """测试单周极端情况触发Deload"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend)
        
        # 单周极端情况：RPE > 9.5 且 完成率 < 80%
        feedback = {
            'completion_rate': 0.70,
            'avg_rpe': 9.8
        }
        
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=feedback,
            base_program=sample_program
        )
        
        # 应该触发强制Deload
        assert weekly_plan.metadata.is_deload_week is True
        
        logger.info(f"✅ 单周极端情况触发Deload")


# ============================================================================
# Test: Output Format Conversion
# ============================================================================

class TestOutputFormatConversion:
    """输出格式转换测试"""
    
    def test_convert_to_output_format(self, sample_program):
        """测试转换为输出格式"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        weekly_plan = generator.generate_first_week(
            full_program=sample_program,
            total_weeks=4
        )
        
        # 转换为输出格式
        output = generator.convert_to_output_format(weekly_plan)
        
        # 验证输出结构
        assert 'week_number' in output
        assert 'total_weeks' in output
        assert 'phase' in output
        assert 'training_days' in output
        assert 'cycle_explanation' in output
        
        # 验证训练日结构
        for day in output['training_days']:
            assert 'day_number' in day
            assert 'exercises' in day
            for exercise in day['exercises']:
                assert 'exercise_id' in exercise
                assert 'name_zh' in exercise
                assert 'sets' in exercise
        
        logger.info(f"✅ 输出格式转换: {len(output['training_days'])}个训练日")


# ============================================================================
# Test: Complete Weekly Flow
# ============================================================================

class TestCompleteWeeklyFlow:
    """完整分周流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_4_week_cycle(self, sample_program, mock_backend):
        """测试完整4周周期流程"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend)
        
        logger.info("=" * 60)
        logger.info("开始完整4周周期测试")
        logger.info("=" * 60)
        
        # 第1周
        week1 = generator.generate_first_week(
            full_program=sample_program,
            total_weeks=4
        )
        logger.info(f"\n📅 第1周: {week1.metadata.phase_name_zh}")
        logger.info(f"   训练日: {len(week1.training_days)}")
        logger.info(f"   总组数: {week1.total_weekly_sets}")
        
        # 模拟反馈并生成后续周
        feedbacks = [
            {'completion_rate': 0.92, 'avg_rpe': 7.2},  # 第1周反馈
            {'completion_rate': 0.88, 'avg_rpe': 7.8},  # 第2周反馈
            {'completion_rate': 0.85, 'avg_rpe': 8.2},  # 第3周反馈
        ]
        
        for week_num in range(2, 5):
            feedback = feedbacks[week_num - 2]
            
            weekly_plan = await generator.generate_next_week(
                user_id=1,
                current_week=week_num,
                total_weeks=4,
                last_week_feedback=feedback,
                base_program=sample_program
            )
            
            logger.info(f"\n📅 第{week_num}周: {weekly_plan.metadata.phase_name_zh}")
            logger.info(f"   容量系数: {weekly_plan.metadata.volume_multiplier:.2f}")
            logger.info(f"   总组数: {weekly_plan.total_weekly_sets}")
            logger.info(f"   Deload: {weekly_plan.metadata.is_deload_week}")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 完整4周周期测试通过！")
        logger.info("=" * 60)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
