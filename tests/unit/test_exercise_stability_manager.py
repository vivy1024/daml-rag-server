# -*- coding: utf-8 -*-
"""
Exercise Stability Manager Unit Tests

测试动作稳定性管理服务的核心功能。

Requirements: 12.1, 12.2, 12.3, 12.4
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.applications.fitness.services.exercise_stability_manager import (
    ExerciseStabilityManager,
    JointType,
    FatigueLevel,
    JointFatigueStatus,
    ExerciseReplacementSuggestion,
)


class TestExerciseStabilityManager:
    """ExerciseStabilityManager测试类"""
    
    @pytest.fixture
    def mock_backend_client(self):
        """创建模拟的BackendClient"""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_neo4j_client(self):
        """创建模拟的Neo4j客户端"""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def manager(self, mock_backend_client, mock_neo4j_client):
        """创建ExerciseStabilityManager实例"""
        return ExerciseStabilityManager(
            backend_client=mock_backend_client,
            neo4j_client=mock_neo4j_client
        )
    
    # ============= prefer_familiar_exercises 测试 =============
    
    @pytest.mark.asyncio
    async def test_prefer_familiar_exercises_sorts_correctly(self, manager, mock_backend_client):
        """
        测试熟悉动作优先排序
        
        Requirements: 12.1 - 优先使用用户历史中熟悉的动作
        """
        # 模拟训练日志数据
        mock_backend_client.get_training_logs.return_value = [
            {
                'session_date': '2025-12-20',
                'actual_exercises': [
                    {'exercise_id': 'ex_001', 'exercise_name': '杠铃卧推'},
                    {'exercise_id': 'ex_002', 'exercise_name': '哑铃飞鸟'},
                ]
            },
            {
                'session_date': '2025-12-18',
                'actual_exercises': [
                    {'exercise_id': 'ex_001', 'exercise_name': '杠铃卧推'},
                    {'exercise_id': 'ex_003', 'exercise_name': '上斜卧推'},
                ]
            },
        ]
        
        # 候选动作列表
        candidate_exercises = [
            {'exercise_id': 'ex_004', 'name': '下斜卧推'},      # 不熟悉
            {'exercise_id': 'ex_001', 'name': '杠铃卧推'},      # 熟悉（使用2次）
            {'exercise_id': 'ex_002', 'name': '哑铃飞鸟'},      # 熟悉（使用1次）
            {'exercise_id': 'ex_005', 'name': '绳索夹胸'},      # 不熟悉
        ]
        
        result = await manager.prefer_familiar_exercises(
            user_id=1,
            candidate_exercises=candidate_exercises
        )
        
        # 验证结果
        assert len(result) == 4
        
        # 熟悉的动作应该排在前面
        assert result[0]['exercise_id'] == 'ex_001'  # 使用次数最多
        assert result[0]['is_familiar'] == True
        assert result[0]['usage_count'] == 2
        
        assert result[1]['exercise_id'] == 'ex_002'  # 使用次数第二
        assert result[1]['is_familiar'] == True
        assert result[1]['usage_count'] == 1
        
        # 不熟悉的动作排在后面
        assert result[2]['is_familiar'] == False
        assert result[3]['is_familiar'] == False
    
    @pytest.mark.asyncio
    async def test_prefer_familiar_exercises_empty_candidates(self, manager):
        """测试空候选列表"""
        result = await manager.prefer_familiar_exercises(
            user_id=1,
            candidate_exercises=[]
        )
        assert result == []
    
    @pytest.mark.asyncio
    async def test_prefer_familiar_exercises_no_history(self, manager, mock_backend_client):
        """
        测试没有训练历史的情况
        
        Requirements: 12.1 - 没有历史时返回原始顺序
        """
        mock_backend_client.get_training_logs.return_value = []
        
        candidate_exercises = [
            {'exercise_id': 'ex_001', 'name': '杠铃卧推'},
            {'exercise_id': 'ex_002', 'name': '哑铃飞鸟'},
        ]
        
        result = await manager.prefer_familiar_exercises(
            user_id=1,
            candidate_exercises=candidate_exercises
        )
        
        # 所有动作都标记为不熟悉
        assert len(result) == 2
        assert all(not e['is_familiar'] for e in result)
    
    # ============= suggest_replacement 测试 =============
    
    @pytest.mark.asyncio
    async def test_suggest_replacement_with_progression(self, manager, mock_backend_client, mock_neo4j_client):
        """
        测试动作替换建议（使用PROGRESSES_TO关系）
        
        Requirements: 12.4 - 利用PROGRESSES_TO关系推荐进阶动作
        """
        # 模拟训练日志（动作使用了8周）
        mock_backend_client.get_training_logs.return_value = [
            {
                'session_date': (datetime.now() - timedelta(days=i*7)).strftime('%Y-%m-%d'),
                'actual_exercises': [{'exercise_id': 'ex_001'}]
            }
            for i in range(8)
        ]
        
        # 模拟Neo4j查询结果
        mock_neo4j_client.run_query.return_value = [
            {
                'exercise_id': 'ex_002',
                'name_zh': '进阶动作A',
                'name_en': 'Advanced Exercise A',
                'difficulty': 'advanced',
                'primary_muscle': '胸大肌',
            }
        ]
        
        result = await manager.suggest_replacement(
            user_id=1,
            exercise_id='ex_001',
            exercise_name='基础动作'
        )
        
        assert isinstance(result, ExerciseReplacementSuggestion)
        assert result.original_exercise_id == 'ex_001'
        assert len(result.suggested_exercises) > 0
    
    @pytest.mark.asyncio
    async def test_suggest_replacement_long_usage(self, manager, mock_backend_client, mock_neo4j_client):
        """
        测试长期使用动作的替换建议
        
        Requirements: 12.2 - 连续使用超过12周时提供建议
        """
        # 模拟训练日志（动作使用了14周）
        mock_backend_client.get_training_logs.return_value = [
            {
                'session_date': (datetime.now() - timedelta(days=i*7)).strftime('%Y-%m-%d'),
                'actual_exercises': [{'exercise_id': 'ex_001'}]
            }
            for i in range(14)
        ]
        
        mock_neo4j_client.run_query.return_value = []
        
        result = await manager.suggest_replacement(
            user_id=1,
            exercise_id='ex_001',
            exercise_name='长期使用动作'
        )
        
        # 应该提到连续使用周数
        assert result.weeks_used >= 12
        assert '连续使用' in result.reason or '已使用' in result.reason
    
    # ============= check_joint_fatigue 测试 =============
    
    @pytest.mark.asyncio
    async def test_check_joint_fatigue_normal(self, manager, mock_backend_client):
        """
        测试正常关节负荷
        
        Requirements: 12.3 - 监控易损部位累计负荷
        """
        # 模拟低负荷训练日志
        mock_backend_client.get_training_logs.return_value = [
            {
                'session_date': '2025-12-25',
                'actual_exercises': [
                    {'exercise_name': 'Bench Press', 'sets_completed': 3},
                ]
            }
        ]
        
        result = await manager.check_joint_fatigue(user_id=1)
        
        assert 'joint_statuses' in result
        assert 'has_warnings' in result
        assert 'overall_recommendation' in result
    
    @pytest.mark.asyncio
    async def test_check_joint_fatigue_high_load(self, manager, mock_backend_client):
        """
        测试高关节负荷警告
        
        Requirements: 12.3 - 超过阈值时提示用户
        """
        # 模拟高负荷训练日志（大量肩部训练）
        mock_backend_client.get_training_logs.return_value = [
            {
                'session_date': '2025-12-25',
                'actual_exercises': [
                    {'exercise_name': 'Overhead Press', 'sets_completed': 10},
                    {'exercise_name': 'Lateral Raise', 'sets_completed': 10},
                    {'exercise_name': 'Front Raise', 'sets_completed': 10},
                    {'exercise_name': 'Upright Row', 'sets_completed': 10},
                ]
            },
            {
                'session_date': '2025-12-23',
                'actual_exercises': [
                    {'exercise_name': 'Overhead Press', 'sets_completed': 10},
                    {'exercise_name': 'Lateral Raise', 'sets_completed': 10},
                ]
            }
        ]
        
        result = await manager.check_joint_fatigue(user_id=1)
        
        # 应该有警告
        assert result['has_warnings'] == True
        assert len(result['warnings']) > 0
        
        # 检查肩关节或肩袖是否有警告
        warning_joints = [w['joint'] for w in result['warnings']]
        assert 'shoulder' in warning_joints or 'rotator_cuff' in warning_joints
    
    @pytest.mark.asyncio
    async def test_check_joint_fatigue_specific_joint(self, manager, mock_backend_client):
        """测试检查特定关节"""
        mock_backend_client.get_training_logs.return_value = []
        
        result = await manager.check_joint_fatigue(
            user_id=1,
            joint=JointType.SHOULDER
        )
        
        # 只应该有一个关节状态
        assert len(result['joint_statuses']) == 1
        assert result['joint_statuses'][0]['joint'] == 'shoulder'
    
    # ============= 辅助方法测试 =============
    
    def test_identify_exercise_type(self, manager):
        """测试动作类型识别"""
        # 测试各种动作名称
        assert manager._identify_exercise_type('Bench Press') == 'bench_press'
        assert manager._identify_exercise_type('杠铃卧推') == 'bench_press'
        assert manager._identify_exercise_type('Overhead Press') == 'overhead_press'
        assert manager._identify_exercise_type('Lateral Raise') == 'lateral_raise'
        assert manager._identify_exercise_type('Squat') == 'squat'
        assert manager._identify_exercise_type('深蹲') == 'squat'
        assert manager._identify_exercise_type('Unknown Exercise') is None
    
    def test_evaluate_joint_fatigue_levels(self, manager):
        """测试关节疲劳等级评估"""
        # 低负荷
        status_low = manager._evaluate_joint_fatigue(
            JointType.SHOULDER,
            {'load': 20.0, 'exercises': ['Bench Press']}
        )
        assert status_low.fatigue_level == FatigueLevel.LOW
        
        # 中等负荷
        status_moderate = manager._evaluate_joint_fatigue(
            JointType.SHOULDER,
            {'load': 40.0, 'exercises': ['Bench Press', 'Overhead Press']}
        )
        assert status_moderate.fatigue_level == FatigueLevel.MODERATE
        
        # 高负荷
        status_high = manager._evaluate_joint_fatigue(
            JointType.SHOULDER,
            {'load': 55.0, 'exercises': ['Bench Press', 'Overhead Press', 'Lateral Raise']}
        )
        assert status_high.fatigue_level == FatigueLevel.HIGH
        
        # 危险负荷
        status_critical = manager._evaluate_joint_fatigue(
            JointType.SHOULDER,
            {'load': 70.0, 'exercises': ['Many exercises']}
        )
        assert status_critical.fatigue_level == FatigueLevel.CRITICAL
    
    def test_get_joint_chinese_name(self, manager):
        """测试关节中文名称获取"""
        assert manager._get_joint_chinese_name(JointType.SHOULDER) == "肩关节"
        assert manager._get_joint_chinese_name(JointType.ROTATOR_CUFF) == "肩袖"
        assert manager._get_joint_chinese_name(JointType.KNEE) == "膝关节"
        assert manager._get_joint_chinese_name(JointType.LOWER_BACK) == "下背部"
    
    # ============= 综合报告测试 =============
    
    @pytest.mark.asyncio
    async def test_get_exercise_stability_report(self, manager, mock_backend_client):
        """测试综合稳定性报告"""
        mock_backend_client.get_training_logs.return_value = [
            {
                'session_date': '2025-12-25',
                'actual_exercises': [
                    {'exercise_id': 'ex_001', 'exercise_name': 'Bench Press', 'sets_completed': 3},
                ]
            }
        ]
        
        candidate_exercises = [
            {'exercise_id': 'ex_001', 'name': 'Bench Press'},
            {'exercise_id': 'ex_002', 'name': 'Incline Press'},
        ]
        
        result = await manager.get_exercise_stability_report(
            user_id=1,
            candidate_exercises=candidate_exercises
        )
        
        assert 'user_id' in result
        assert 'joint_fatigue' in result
        assert 'exercise_familiarity' in result
        assert 'recommendations' in result


class TestJointFatigueStatus:
    """JointFatigueStatus数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        status = JointFatigueStatus(
            joint=JointType.SHOULDER,
            fatigue_level=FatigueLevel.HIGH,
            accumulated_load=55.0,
            threshold=60.0,
            load_percentage=91.7,
            exercises_involved=['Bench Press', 'Overhead Press'],
            recommendation='建议休息'
        )
        
        result = status.to_dict()
        
        assert result['joint'] == 'shoulder'
        assert result['fatigue_level'] == 'high'
        assert result['accumulated_load'] == 55.0
        assert result['threshold'] == 60.0
        assert len(result['exercises_involved']) == 2


class TestExerciseReplacementSuggestion:
    """ExerciseReplacementSuggestion数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        suggestion = ExerciseReplacementSuggestion(
            original_exercise_id='ex_001',
            original_exercise_name='杠铃卧推',
            suggested_exercises=[
                {'exercise_id': 'ex_002', 'name': '哑铃卧推'}
            ],
            reason='连续使用12周',
            weeks_used=12
        )
        
        result = suggestion.to_dict()
        
        assert result['original_exercise_id'] == 'ex_001'
        assert result['original_exercise_name'] == '杠铃卧推'
        assert len(result['suggested_exercises']) == 1
        assert result['weeks_used'] == 12
