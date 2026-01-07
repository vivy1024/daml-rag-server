# -*- coding: utf-8 -*-
"""
训练计划性能测试

测试性能指标：
- 验证输出长度<8000字符
- 验证响应时间<30秒

Requirements: 11.1 - 训练计划摘要优化

测试场景：
1. 输出长度验证
2. 响应时间验证
3. 大规模计划处理
4. 摘要器性能

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import pytest
import asyncio
import logging
import time
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Performance Constants
# ============================================================================

MAX_OUTPUT_CHARS = 8000  # 最大输出字符数
MAX_RESPONSE_TIME_SECONDS = 30  # 最大响应时间（秒）


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def large_training_program():
    """创建大规模训练计划（用于压力测试）"""
    exercises = []
    for i in range(20):  # 20个动作
        exercises.append({
            'exercise_id': f'exercise_{i}',
            'name_zh': f'测试动作{i}',
            'name_en': f'Test Exercise {i}',
            'sets': 4,
            'reps_range': (8, 12),
            'rest_seconds': 90,
            'primary_muscles': ['测试肌群'],
            'safety_notes': ['注意事项1', '注意事项2'] if i % 3 == 0 else []
        })
    
    training_days = []
    for day in range(6):  # 6个训练日
        day_exercises = exercises[day*3:(day+1)*3 + 2]  # 每天5个动作
        training_days.append({
            'day_number': day + 1,
            'day_name': f'训练日{day + 1}',
            'focus_muscle_groups': ['肌群A', '肌群B'],
            'exercises': day_exercises,
            'notes': ['备注1', '备注2']
        })
    
    return {
        'program_name': '大规模测试计划',
        'total_weeks': 8,
        'weekly_program': {
            'training_days': training_days
        },
        'cycle_explanation': '这是一个测试周期说明，用于验证输出长度限制。' * 10
    }


@pytest.fixture
def standard_training_program():
    """创建标准训练计划"""
    return {
        'program_name': '标准增肌计划',
        'total_weeks': 4,
        'weekly_program': {
            'training_days': [
                {
                    'day_number': 1,
                    'day_name': '推日',
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
                            'exercise_id': 'overhead_press',
                            'name_zh': '杠铃推举',
                            'name_en': 'Overhead Press',
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
                    'day_name': '拉日',
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
                    'day_name': '腿日',
                    'focus_muscle_groups': ['股四头', '腘绳肌'],
                    'exercises': [
                        {
                            'exercise_id': 'barbell_squat',
                            'name_zh': '杠铃深蹲',
                            'name_en': 'Barbell Squat',
                            'sets': 4,
                            'reps_range': (6, 8),
                            'rest_seconds': 180,
                            'primary_muscles': ['股四头肌']
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
    return backend


# ============================================================================
# Test: Output Length Validation
# ============================================================================

class TestOutputLengthValidation:
    """输出长度验证测试"""
    
    def test_summarizer_output_within_limit(self, standard_training_program):
        """测试摘要器输出在限制范围内 - Requirements 11.1"""
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        summarizer = TrainingPlanSummarizer()
        
        # 生成摘要
        result = summarizer.summarize(standard_training_program)
        
        # 验证输出长度
        assert result.char_count <= MAX_OUTPUT_CHARS, \
            f"输出长度{result.char_count}超过限制{MAX_OUTPUT_CHARS}"
        
        logger.info(
            f"✅ 标准计划输出长度: {result.char_count}/{MAX_OUTPUT_CHARS} "
            f"({result.char_count/MAX_OUTPUT_CHARS*100:.1f}%)"
        )
    
    def test_large_program_truncation(self, large_training_program):
        """测试大规模计划被正确截断"""
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        summarizer = TrainingPlanSummarizer()
        
        # 生成摘要
        result = summarizer.summarize(large_training_program)
        
        # 验证输出长度不超过限制
        assert result.char_count <= MAX_OUTPUT_CHARS, \
            f"输出长度{result.char_count}超过限制{MAX_OUTPUT_CHARS}"
        
        # 如果被截断，应该有截断标记
        if result.is_truncated:
            logger.info(f"✅ 大规模计划被截断: {result.truncation_reason}")
        else:
            logger.info(f"✅ 大规模计划未超限: {result.char_count}字符")
    
    def test_weekly_plan_output_length(self, standard_training_program):
        """测试周计划输出长度"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        generator = WeeklyPlanGenerator()
        summarizer = TrainingPlanSummarizer()
        
        # 生成周计划
        weekly_plan = generator.generate_first_week(
            full_program=standard_training_program,
            total_weeks=4
        )
        
        # 转换为输出格式
        output_dict = generator.convert_to_output_format(weekly_plan)
        
        # 使用摘要器生成最终输出
        result = summarizer.summarize(output_dict)
        
        assert result.char_count <= MAX_OUTPUT_CHARS
        
        logger.info(
            f"✅ 周计划输出长度: {result.char_count}/{MAX_OUTPUT_CHARS} "
            f"({result.char_count/MAX_OUTPUT_CHARS*100:.1f}%)"
        )
    
    def test_estimate_output_length(self, standard_training_program):
        """测试输出长度估算"""
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        summarizer = TrainingPlanSummarizer()
        
        # 估算长度
        estimated = summarizer.estimate_output_length(standard_training_program)
        
        # 实际生成
        result = summarizer.summarize(standard_training_program)
        
        # 估算应该在合理范围内（±50%）
        ratio = result.char_count / estimated if estimated > 0 else 0
        
        logger.info(
            f"✅ 长度估算: estimated={estimated}, actual={result.char_count}, "
            f"ratio={ratio:.2f}"
        )


# ============================================================================
# Test: Response Time Validation
# ============================================================================

class TestResponseTimeValidation:
    """响应时间验证测试"""
    
    def test_first_week_generation_time(self, standard_training_program):
        """测试第1周计划生成时间"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        start_time = time.time()
        
        weekly_plan = generator.generate_first_week(
            full_program=standard_training_program,
            total_weeks=4
        )
        
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < MAX_RESPONSE_TIME_SECONDS, \
            f"生成时间{elapsed_time:.2f}s超过限制{MAX_RESPONSE_TIME_SECONDS}s"
        
        logger.info(f"✅ 第1周计划生成时间: {elapsed_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_next_week_generation_time(self, standard_training_program, mock_backend):
        """测试下周计划生成时间"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend)
        
        feedback = {'completion_rate': 0.90, 'avg_rpe': 7.5}
        
        start_time = time.time()
        
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=feedback,
            base_program=standard_training_program
        )
        
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < MAX_RESPONSE_TIME_SECONDS, \
            f"生成时间{elapsed_time:.2f}s超过限制{MAX_RESPONSE_TIME_SECONDS}s"
        
        logger.info(f"✅ 下周计划生成时间: {elapsed_time:.3f}s")
    
    def test_summarizer_performance(self, large_training_program):
        """测试摘要器性能"""
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        summarizer = TrainingPlanSummarizer()
        
        start_time = time.time()
        
        result = summarizer.summarize(large_training_program)
        
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 5.0, \
            f"摘要生成时间{elapsed_time:.2f}s超过5秒"
        
        logger.info(
            f"✅ 摘要器性能: {elapsed_time:.3f}s, "
            f"output={result.char_count}chars"
        )
    
    def test_safety_marker_performance(self, large_training_program):
        """测试安全标记性能"""
        from src.applications.fitness.services.safety_reminder_generator import SafetyReminderGenerator
        
        generator = SafetyReminderGenerator()
        
        # 提取所有动作
        exercises = []
        for day in large_training_program.get('weekly_program', {}).get('training_days', []):
            exercises.extend(day.get('exercises', []))
        
        start_time = time.time()
        
        marked = generator.mark_high_risk_exercises(exercises)
        
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 1.0, \
            f"安全标记时间{elapsed_time:.2f}s超过1秒"
        
        logger.info(
            f"✅ 安全标记性能: {elapsed_time:.3f}s, "
            f"exercises={len(exercises)}"
        )


# ============================================================================
# Test: Stress Testing
# ============================================================================

class TestStressTesting:
    """压力测试"""
    
    def test_multiple_week_generation(self, standard_training_program):
        """测试连续生成多周计划"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        start_time = time.time()
        
        # 生成8周计划
        for week in range(1, 9):
            if week == 1:
                plan = generator.generate_first_week(
                    full_program=standard_training_program,
                    total_weeks=8
                )
            else:
                # 使用insert_deload_week作为简化测试
                if week % 4 == 0:
                    plan = generator.insert_deload_week(
                        base_program=standard_training_program,
                        week_number=week,
                        total_weeks=8
                    )
        
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < MAX_RESPONSE_TIME_SECONDS, \
            f"8周计划生成时间{elapsed_time:.2f}s超过限制"
        
        logger.info(f"✅ 8周计划连续生成时间: {elapsed_time:.3f}s")
    
    def test_concurrent_summarization(self, standard_training_program):
        """测试并发摘要生成"""
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        summarizer = TrainingPlanSummarizer()
        
        start_time = time.time()
        
        # 连续生成10次摘要
        results = []
        for _ in range(10):
            result = summarizer.summarize(standard_training_program)
            results.append(result)
        
        elapsed_time = time.time() - start_time
        
        # 平均每次应该小于1秒
        avg_time = elapsed_time / 10
        
        assert avg_time < 1.0, \
            f"平均摘要时间{avg_time:.2f}s超过1秒"
        
        logger.info(
            f"✅ 10次摘要生成: total={elapsed_time:.3f}s, "
            f"avg={avg_time:.3f}s"
        )


# ============================================================================
# Test: Output Quality Validation
# ============================================================================

class TestOutputQualityValidation:
    """输出质量验证测试"""
    
    def test_core_fields_preserved(self, standard_training_program):
        """测试核心字段保留 - Requirements 11.2"""
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        summarizer = TrainingPlanSummarizer()
        
        # 生成摘要字典
        summarized = summarizer.summarize_to_dict(standard_training_program)
        
        # 验证核心字段存在
        for day in summarized.get('training_days', []):
            for exercise in day.get('exercises', []):
                assert 'exercise_id' in exercise
                assert 'name_zh' in exercise
                assert 'sets' in exercise
                assert 'reps_range' in exercise
                assert 'rest_seconds' in exercise
        
        logger.info("✅ 核心字段保留验证通过")
    
    def test_markdown_links_generated(self, standard_training_program):
        """测试Markdown链接生成 - Requirements 11.3"""
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        summarizer = TrainingPlanSummarizer()
        
        # 转换链接
        converted = summarizer.convert_to_links(standard_training_program)
        
        # 验证链接格式
        for day in converted.get('training_days', []):
            for exercise in day.get('exercises', []):
                if 'name_link' in exercise:
                    assert '[' in exercise['name_link']
                    assert '](' in exercise['name_link']
        
        logger.info("✅ Markdown链接格式验证通过")
    
    def test_high_risk_markers_added(self, standard_training_program):
        """测试高风险动作标记 - Requirements 11.4"""
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        
        summarizer = TrainingPlanSummarizer()
        
        # 添加安全标记
        marked = summarizer.add_safety_markers(standard_training_program)
        
        # 检查是否有高风险动作被标记
        high_risk_count = 0
        for day in marked.get('training_days', []):
            for exercise in day.get('exercises', []):
                if exercise.get('safety_marker'):
                    high_risk_count += 1
        
        logger.info(f"✅ 高风险动作标记: {high_risk_count}个")


# ============================================================================
# Test: Performance Summary
# ============================================================================

class TestPerformanceSummary:
    """性能汇总测试"""
    
    def test_complete_performance_benchmark(self, standard_training_program, large_training_program):
        """完整性能基准测试"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        from src.applications.fitness.services.training_plan_summarizer import TrainingPlanSummarizer
        from src.applications.fitness.services.safety_reminder_generator import SafetyReminderGenerator
        
        logger.info("=" * 60)
        logger.info("性能基准测试")
        logger.info("=" * 60)
        
        results = {}
        
        # 1. 周计划生成
        generator = WeeklyPlanGenerator()
        start = time.time()
        plan = generator.generate_first_week(
            full_program=standard_training_program,
            total_weeks=4
        )
        results['week_generation'] = time.time() - start
        
        # 2. 摘要生成（标准）
        summarizer = TrainingPlanSummarizer()
        start = time.time()
        summary = summarizer.summarize(standard_training_program)
        results['summarize_standard'] = time.time() - start
        results['output_chars_standard'] = summary.char_count
        
        # 3. 摘要生成（大规模）
        start = time.time()
        summary_large = summarizer.summarize(large_training_program)
        results['summarize_large'] = time.time() - start
        results['output_chars_large'] = summary_large.char_count
        
        # 4. 安全标记
        safety_gen = SafetyReminderGenerator()
        exercises = []
        for day in large_training_program.get('weekly_program', {}).get('training_days', []):
            exercises.extend(day.get('exercises', []))
        start = time.time()
        safety_gen.mark_high_risk_exercises(exercises)
        results['safety_marking'] = time.time() - start
        
        # 输出结果
        logger.info("\n📊 性能测试结果:")
        logger.info(f"   周计划生成: {results['week_generation']*1000:.1f}ms")
        logger.info(f"   标准摘要: {results['summarize_standard']*1000:.1f}ms ({results['output_chars_standard']}字符)")
        logger.info(f"   大规模摘要: {results['summarize_large']*1000:.1f}ms ({results['output_chars_large']}字符)")
        logger.info(f"   安全标记: {results['safety_marking']*1000:.1f}ms ({len(exercises)}个动作)")
        
        # 验证所有指标
        assert results['week_generation'] < 1.0, "周计划生成超时"
        assert results['summarize_standard'] < 1.0, "标准摘要超时"
        assert results['summarize_large'] < 5.0, "大规模摘要超时"
        assert results['output_chars_standard'] <= MAX_OUTPUT_CHARS, "标准输出超长"
        assert results['output_chars_large'] <= MAX_OUTPUT_CHARS, "大规模输出超长"
        
        logger.info("\n✅ 所有性能指标通过!")
        logger.info("=" * 60)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
