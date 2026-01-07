# -*- coding: utf-8 -*-
"""
闭环学习系统集成测试

测试完整的闭环流程：
训练日志记录 → 分析 → 调整 → 生成新计划

Requirements: 全部（闭环学习系统）

测试场景：
1. 训练日志记录和分析
2. 容量动态调整
3. 渐进过载计算
4. 分周计划生成
5. 完整闭环流程

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Mock Classes for Testing
# ============================================================================

class MockBackendClient:
    """模拟后端客户端"""
    
    def __init__(self):
        self.training_logs = []
        self.personal_bests = {}
        self.user_profiles = {}
        self._setup_default_data()
    
    def _setup_default_data(self):
        """设置默认测试数据"""
        # 默认用户档案
        self.user_profiles[1] = {
            'id': 1,
            'name': 'Test User',
            'training_system': {
                'personal_volume_multiplier': 1.0,
                'personal_recovery_factor': 1.0,
            },
            'injury_history': []
        }
        
        # 默认训练日志（模拟4周训练数据）
        base_date = datetime.now() - timedelta(days=28)
        for week in range(4):
            for day in range(3):  # 每周3次训练
                session_date = base_date + timedelta(days=week*7 + day*2)
                self.training_logs.append({
                    'id': len(self.training_logs) + 1,
                    'user_id': 1,
                    'session_date': session_date.strftime('%Y-%m-%d'),
                    'completion_rate': 0.85 + (week * 0.02),  # 逐周提升
                    'avg_rpe': 7.5 - (week * 0.1),  # 逐周降低
                    'planned_exercises': [],
                    'actual_exercises': []
                })
        
        # 默认个人最佳记录
        self.personal_bests[1] = {
            'barbell_squat': {'best_weight': 100.0, 'best_reps': 5},
            'barbell_bench_press': {'best_weight': 80.0, 'best_reps': 5},
            'barbell_deadlift': {'best_weight': 120.0, 'best_reps': 5},
        }
    
    async def get_training_logs(
        self,
        user_id: int,
        start_date: str = None,
        end_date: str = None,
        mesocycle_id: str = None
    ) -> List[Dict[str, Any]]:
        """获取训练日志"""
        logs = [log for log in self.training_logs if log['user_id'] == user_id]
        
        if start_date:
            logs = [log for log in logs if log['session_date'] >= start_date]
        if end_date:
            logs = [log for log in logs if log['session_date'] <= end_date]
        
        return logs
    
    async def get_personal_bests(self, user_id: int) -> List[Dict[str, Any]]:
        """获取个人最佳记录"""
        pbs = self.personal_bests.get(user_id, {})
        return [
            {'exercise_id': ex_id, **data}
            for ex_id, data in pbs.items()
        ]
    
    async def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """获取用户档案"""
        return self.user_profiles.get(user_id, {
            'id': user_id,
            'training_system': {'personal_volume_multiplier': 1.0}
        })
    
    async def update_volume_multiplier(
        self,
        user_id: int,
        new_multiplier: float,
        adjustment: float,
        reason: str
    ) -> Dict[str, Any]:
        """更新容量系数"""
        if user_id in self.user_profiles:
            self.user_profiles[user_id]['training_system']['personal_volume_multiplier'] = new_multiplier
        return {'success': True, 'new_multiplier': new_multiplier}
    
    def add_training_log(self, log: Dict[str, Any]):
        """添加训练日志（用于测试）"""
        self.training_logs.append(log)
    
    def set_user_profile(self, user_id: int, profile: Dict[str, Any]):
        """设置用户档案（用于测试）"""
        self.user_profiles[user_id] = profile


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_backend_client():
    """创建模拟后端客户端"""
    return MockBackendClient()


@pytest.fixture
def sample_full_program():
    """创建示例完整训练计划"""
    return {
        'program_name': '8周增肌计划',
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
                            'primary_muscles': ['三角肌前束']
                        }
                    ]
                },
                {
                    'day_number': 2,
                    'day_name': '拉日',
                    'focus_muscle_groups': ['背', '二头'],
                    'exercises': [
                        {
                            'exercise_id': 'barbell_row',
                            'name_zh': '杠铃划船',
                            'name_en': 'Barbell Row',
                            'sets': 4,
                            'reps_range': (6, 8),
                            'rest_seconds': 120,
                            'primary_muscles': ['背阔肌']
                        }
                    ]
                },
                {
                    'day_number': 3,
                    'day_name': '腿日',
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
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def sample_last_week_feedback():
    """创建示例上周反馈"""
    return {
        'completion_rate': 0.92,
        'avg_rpe': 7.5,
        'previous_avg_rpe': 7.8,
        'previous_completion_rate': 0.88
    }


# ============================================================================
# Test: Training Log Analyzer
# ============================================================================

class TestTrainingLogAnalyzer:
    """训练日志分析器测试"""
    
    @pytest.mark.asyncio
    async def test_get_user_training_history(self, mock_backend_client):
        """测试获取用户训练历史"""
        from src.applications.fitness.services.training_log_analyzer import TrainingLogAnalyzer
        
        analyzer = TrainingLogAnalyzer(backend_client=mock_backend_client)
        
        # 获取训练历史
        logs = await analyzer.get_user_training_history(user_id=1, days_back=28)
        
        assert len(logs) > 0
        assert all(log['user_id'] == 1 for log in logs)
        logger.info(f"✅ 获取到{len(logs)}条训练日志")
    
    @pytest.mark.asyncio
    async def test_analyze_completion_trend(self, mock_backend_client):
        """测试完成率趋势分析"""
        from src.applications.fitness.services.training_log_analyzer import TrainingLogAnalyzer
        
        analyzer = TrainingLogAnalyzer(backend_client=mock_backend_client)
        
        # 分析完成率趋势
        result = await analyzer.analyze_completion_trend(user_id=1, weeks=4)
        
        assert result.avg_completion_rate >= 0
        assert result.avg_completion_rate <= 1
        assert result.weeks_analyzed == 4
        logger.info(f"✅ 完成率趋势分析: avg={result.avg_completion_rate:.2f}, direction={result.direction.value}")
    
    @pytest.mark.asyncio
    async def test_analyze_rpe_trend(self, mock_backend_client):
        """测试RPE趋势分析"""
        from src.applications.fitness.services.training_log_analyzer import TrainingLogAnalyzer
        
        analyzer = TrainingLogAnalyzer(backend_client=mock_backend_client)
        
        # 分析RPE趋势
        result = await analyzer.analyze_rpe_trend(user_id=1, weeks=4)
        
        assert result.avg_rpe >= 0
        assert result.avg_rpe <= 10
        logger.info(f"✅ RPE趋势分析: avg={result.avg_rpe:.1f}, direction={result.direction.value}")
    
    @pytest.mark.asyncio
    async def test_analyze_mesocycle(self, mock_backend_client):
        """测试中周期分析"""
        from src.applications.fitness.services.training_log_analyzer import TrainingLogAnalyzer
        
        analyzer = TrainingLogAnalyzer(backend_client=mock_backend_client)
        
        # 分析中周期
        result = await analyzer.analyze_mesocycle(user_id=1, mesocycle_weeks=4)
        
        assert result.user_id == 1
        assert result.mesocycle_weeks == 4
        assert result.total_sessions > 0
        logger.info(
            f"✅ 中周期分析: sessions={result.total_sessions}, "
            f"avg_rpe={result.avg_rpe:.1f}, "
            f"avg_completion={result.avg_completion_rate:.2f}"
        )


# ============================================================================
# Test: Volume Adjuster
# ============================================================================

class TestVolumeAdjuster:
    """容量调整器测试"""
    
    def test_calculate_adjustment_increase(self):
        """测试容量上调条件 - RPE<7且完成率>95%"""
        from src.applications.fitness.services.volume_adjuster import VolumeAdjuster
        
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # RPE < 7 且 完成率 > 95% -> 上调
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=6.5,
            avg_completion_rate=0.97,
            current_multiplier=1.0
        )
        
        assert adjustment > 0
        assert 0.05 <= adjustment <= 0.10
        assert direction.value == 'increase'
        logger.info(f"✅ 容量上调测试: adjustment={adjustment:+.2f}, reason={reason}")
    
    def test_calculate_adjustment_decrease(self):
        """测试容量下调条件 - RPE>9.5或完成率<80%"""
        from src.applications.fitness.services.volume_adjuster import VolumeAdjuster
        
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # RPE > 9.5 -> 下调
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=9.8,
            avg_completion_rate=0.85,
            current_multiplier=1.0
        )
        
        assert adjustment < 0
        assert -0.15 <= adjustment <= -0.10
        assert direction.value == 'decrease'
        logger.info(f"✅ 容量下调测试(高RPE): adjustment={adjustment:+.2f}")
        
        # 完成率 < 80% -> 下调
        adjustment2, direction2, reason2 = adjuster.calculate_adjustment(
            avg_rpe=7.5,
            avg_completion_rate=0.75,
            current_multiplier=1.0
        )
        
        assert adjustment2 < 0
        assert direction2.value == 'decrease'
        logger.info(f"✅ 容量下调测试(低完成率): adjustment={adjustment2:+.2f}")
    
    def test_clamp_multiplier(self):
        """测试容量系数边界约束"""
        from src.applications.fitness.services.volume_adjuster import VolumeAdjuster
        
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # 测试下限
        assert adjuster.clamp_multiplier(0.5) == 0.7
        # 测试上限
        assert adjuster.clamp_multiplier(2.0) == 1.5
        # 测试正常范围
        assert adjuster.clamp_multiplier(1.0) == 1.0
        
        logger.info("✅ 容量系数边界约束测试通过")
    
    def test_should_suggest_deload(self):
        """测试Deload建议触发条件"""
        from src.applications.fitness.services.volume_adjuster import VolumeAdjuster
        
        adjuster = VolumeAdjuster(
            training_log_analyzer=MagicMock(),
            backend_client=MagicMock()
        )
        
        # 连续2周高RPE -> 建议Deload
        should_deload, reason = adjuster.should_suggest_deload(
            avg_rpe=9.2,
            avg_completion_rate=0.82,
            previous_week_rpe=9.3,
            previous_week_completion=0.80
        )
        
        assert should_deload is True
        assert reason is not None
        logger.info(f"✅ Deload建议测试: should_deload={should_deload}, reason={reason}")


# ============================================================================
# Test: Progressive Overload Calculator
# ============================================================================

class TestProgressiveOverloadCalculator:
    """渐进过载计算器测试"""
    
    def test_calculate_next_weight_increase(self):
        """测试渐进过载正向调整"""
        from src.applications.fitness.services.progressive_overload import (
            ProgressiveOverloadCalculator, ExerciseType
        )
        
        calculator = ProgressiveOverloadCalculator()
        
        # 完成所有目标次数 -> 增加重量
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=100.0,
            completed_all_reps=True,
            exercise_type=ExerciseType.COMPOUND
        )
        
        assert next_weight == 102.5  # 复合动作+2.5kg
        assert decision.value == 'increase'
        logger.info(f"✅ 渐进过载正向调整: 100kg -> {next_weight}kg")
    
    def test_calculate_next_weight_maintain(self):
        """测试渐进过载保守调整"""
        from src.applications.fitness.services.progressive_overload import (
            ProgressiveOverloadCalculator, ExerciseType
        )
        
        calculator = ProgressiveOverloadCalculator()
        
        # 未完成目标次数 -> 保持重量
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=100.0,
            completed_all_reps=False,
            exercise_type=ExerciseType.COMPOUND
        )
        
        assert next_weight == 100.0  # 保持不变
        assert decision.value == 'maintain'
        logger.info(f"✅ 渐进过载保守调整: 保持{next_weight}kg")
    
    def test_detect_regression(self):
        """测试重量退步检测"""
        from src.applications.fitness.services.progressive_overload import ProgressiveOverloadCalculator
        
        calculator = ProgressiveOverloadCalculator()
        
        # 重量下降超过10% -> 检测到退步
        regression, message = calculator.detect_regression(
            current_weight=85.0,
            personal_best=100.0,
            exercise_name='杠铃深蹲'
        )
        
        assert regression is True
        assert message is not None
        logger.info(f"✅ 重量退步检测: regression={regression}")
    
    def test_isolation_exercise_increment(self):
        """测试孤立动作增幅"""
        from src.applications.fitness.services.progressive_overload import (
            ProgressiveOverloadCalculator, ExerciseType
        )
        
        calculator = ProgressiveOverloadCalculator()
        
        # 孤立动作 -> +1.25kg
        next_weight, decision, reason = calculator.calculate_next_weight(
            last_weight=20.0,
            completed_all_reps=True,
            exercise_type=ExerciseType.ISOLATION
        )
        
        assert next_weight == 21.25  # 孤立动作+1.25kg
        logger.info(f"✅ 孤立动作增幅: 20kg -> {next_weight}kg")


# ============================================================================
# Test: Weekly Plan Generator
# ============================================================================

class TestWeeklyPlanGenerator:
    """分周计划生成器测试"""
    
    def test_generate_first_week(self, sample_full_program):
        """测试生成第1周计划"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        # 生成第1周计划
        weekly_plan = generator.generate_first_week(
            full_program=sample_full_program,
            user_profile={'training_system': {'personal_volume_multiplier': 1.0}},
            total_weeks=4
        )
        
        assert weekly_plan.metadata.week_number == 1
        assert weekly_plan.metadata.is_first_week is True
        assert len(weekly_plan.training_days) > 0
        assert weekly_plan.cycle_explanation is not None
        
        logger.info(
            f"✅ 第1周计划生成: "
            f"training_days={len(weekly_plan.training_days)}, "
            f"total_sets={weekly_plan.total_weekly_sets}"
        )
    
    @pytest.mark.asyncio
    async def test_generate_next_week(self, mock_backend_client, sample_full_program, sample_last_week_feedback):
        """测试基于反馈生成下周计划"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator(backend_client=mock_backend_client)
        
        # 生成第2周计划
        weekly_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback=sample_last_week_feedback,
            base_program=sample_full_program,
            user_profile={'training_system': {'personal_volume_multiplier': 1.0}}
        )
        
        assert weekly_plan.metadata.week_number == 2
        assert weekly_plan.metadata.is_first_week is False
        assert len(weekly_plan.training_days) > 0
        
        logger.info(
            f"✅ 第2周计划生成: "
            f"phase={weekly_plan.metadata.phase_name_zh}, "
            f"volume_multiplier={weekly_plan.metadata.volume_multiplier:.2f}"
        )
    
    def test_insert_deload_week(self, sample_full_program):
        """测试生成Deload周计划"""
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        generator = WeeklyPlanGenerator()
        
        # 生成Deload周
        weekly_plan = generator.insert_deload_week(
            base_program=sample_full_program,
            week_number=4,
            total_weeks=4
        )
        
        assert weekly_plan.metadata.is_deload_week is True
        assert weekly_plan.metadata.volume_multiplier < 1.0  # Deload周容量降低
        
        logger.info(
            f"✅ Deload周计划生成: "
            f"volume_multiplier={weekly_plan.metadata.volume_multiplier:.2f}"
        )


# ============================================================================
# Test: Complete Closed Loop Flow
# ============================================================================

class TestClosedLoopFlow:
    """完整闭环流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_closed_loop_flow(self, mock_backend_client, sample_full_program):
        """
        测试完整闭环流程：
        训练日志记录 → 分析 → 调整 → 生成新计划
        """
        from src.applications.fitness.services.training_log_analyzer import TrainingLogAnalyzer
        from src.applications.fitness.services.volume_adjuster import VolumeAdjuster
        from src.applications.fitness.services.weekly_plan_generator import WeeklyPlanGenerator
        
        logger.info("=" * 60)
        logger.info("开始完整闭环流程测试")
        logger.info("=" * 60)
        
        # Step 1: 初始化服务
        analyzer = TrainingLogAnalyzer(backend_client=mock_backend_client)
        adjuster = VolumeAdjuster(
            training_log_analyzer=analyzer,
            backend_client=mock_backend_client
        )
        generator = WeeklyPlanGenerator(
            training_log_analyzer=analyzer,
            backend_client=mock_backend_client
        )
        
        # Step 2: 生成第1周计划
        logger.info("\n📅 Step 1: 生成第1周计划")
        week1_plan = generator.generate_first_week(
            full_program=sample_full_program,
            user_profile=await mock_backend_client.get_user_profile(1),
            total_weeks=4
        )
        assert week1_plan.metadata.week_number == 1
        logger.info(f"✅ 第1周计划生成完成: {len(week1_plan.training_days)}个训练日")
        
        # Step 3: 模拟用户完成训练并记录日志
        logger.info("\n📝 Step 2: 记录训练日志")
        mock_backend_client.add_training_log({
            'id': 100,
            'user_id': 1,
            'session_date': datetime.now().strftime('%Y-%m-%d'),
            'completion_rate': 0.96,  # 高完成率
            'avg_rpe': 6.8,  # 低RPE
            'planned_exercises': [],
            'actual_exercises': []
        })
        logger.info("✅ 训练日志记录完成")
        
        # Step 4: 分析训练表现
        logger.info("\n📊 Step 3: 分析训练表现")
        analysis = await analyzer.analyze_mesocycle(user_id=1, mesocycle_weeks=4)
        logger.info(
            f"✅ 分析完成: "
            f"avg_rpe={analysis.avg_rpe:.1f}, "
            f"avg_completion={analysis.avg_completion_rate:.2f}"
        )
        
        # Step 5: 计算容量调整
        logger.info("\n⚙️ Step 4: 计算容量调整")
        adjustment, direction, reason = adjuster.calculate_adjustment(
            avg_rpe=analysis.avg_rpe,
            avg_completion_rate=analysis.avg_completion_rate
        )
        logger.info(f"✅ 调整计算: {direction.value}, adjustment={adjustment:+.2f}")
        
        # Step 6: 生成第2周计划
        logger.info("\n📅 Step 5: 生成第2周计划")
        week2_plan = await generator.generate_next_week(
            user_id=1,
            current_week=2,
            total_weeks=4,
            last_week_feedback={
                'completion_rate': analysis.avg_completion_rate,
                'avg_rpe': analysis.avg_rpe
            },
            base_program=sample_full_program,
            user_profile=await mock_backend_client.get_user_profile(1)
        )
        assert week2_plan.metadata.week_number == 2
        logger.info(
            f"✅ 第2周计划生成完成: "
            f"phase={week2_plan.metadata.phase_name_zh}, "
            f"volume_multiplier={week2_plan.metadata.volume_multiplier:.2f}"
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 完整闭环流程测试通过！")
        logger.info("=" * 60)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
