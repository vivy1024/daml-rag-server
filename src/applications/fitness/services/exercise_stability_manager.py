# -*- coding: utf-8 -*-
"""
Exercise Stability Manager Service

动作稳定性管理服务，优先使用熟悉动作，不频繁更换。
健身理论支持"熟悉的动作更安全"，不应频繁更换动作影响渐进过载追踪。

Requirements: 12.1, 12.2, 12.3, 12.4

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class JointType(str, Enum):
    """易损关节类型"""
    SHOULDER = "shoulder"           # 肩关节
    ROTATOR_CUFF = "rotator_cuff"   # 肩袖
    WRIST = "wrist"                 # 腕关节
    ELBOW = "elbow"                 # 肘关节
    KNEE = "knee"                   # 膝关节
    LOWER_BACK = "lower_back"       # 下背部
    NECK = "neck"                   # 颈部


class FatigueLevel(str, Enum):
    """疲劳等级"""
    LOW = "low"           # 低负荷
    MODERATE = "moderate" # 中等负荷
    HIGH = "high"         # 高负荷
    CRITICAL = "critical" # 危险负荷


@dataclass
class JointFatigueStatus:
    """关节疲劳状态"""
    joint: JointType
    fatigue_level: FatigueLevel
    accumulated_load: float      # 累计负荷（组数 * 强度系数）
    threshold: float             # 阈值
    load_percentage: float       # 负荷百分比
    exercises_involved: List[str]  # 涉及的动作
    recommendation: str          # 建议
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'joint': self.joint.value,
            'fatigue_level': self.fatigue_level.value,
            'accumulated_load': self.accumulated_load,
            'threshold': self.threshold,
            'load_percentage': self.load_percentage,
            'exercises_involved': self.exercises_involved,
            'recommendation': self.recommendation,
        }


@dataclass
class ExerciseReplacementSuggestion:
    """动作替换建议"""
    original_exercise_id: str
    original_exercise_name: str
    suggested_exercises: List[Dict[str, Any]]
    reason: str
    weeks_used: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'original_exercise_id': self.original_exercise_id,
            'original_exercise_name': self.original_exercise_name,
            'suggested_exercises': self.suggested_exercises,
            'reason': self.reason,
            'weeks_used': self.weeks_used,
        }


class ExerciseStabilityManager:
    """
    动作稳定性管理服务
    
    核心理念：熟悉的动作更安全，不应频繁更换动作影响渐进过载追踪。
    
    功能：
    1. 优先选择用户熟悉的动作（Requirements 12.1）
    2. 用户主动请求时提供替换建议（Requirements 12.2, 12.4）
    3. 监控易损部位累计负荷（Requirements 12.3）
    
    Requirements: 12.1, 12.2, 12.3, 12.4
    """
    
    # 动作连续使用周数阈值（超过此值可建议更换）
    EXERCISE_USAGE_THRESHOLD_WEEKS = 12
    
    # 关节负荷阈值配置（每周组数 * 强度系数）
    JOINT_LOAD_THRESHOLDS = {
        JointType.SHOULDER: 60.0,       # 肩关节：每周约20组肩部训练
        JointType.ROTATOR_CUFF: 40.0,   # 肩袖：更敏感，阈值更低
        JointType.WRIST: 50.0,          # 腕关节
        JointType.ELBOW: 55.0,          # 肘关节
        JointType.KNEE: 70.0,           # 膝关节：承重能力较强
        JointType.LOWER_BACK: 50.0,     # 下背部：需要保护
        JointType.NECK: 30.0,           # 颈部：最敏感
    }
    
    # 动作对关节的负荷系数（基于动作类型和涉及关节）
    # 格式：{动作类型/关键词: {关节: 负荷系数}}
    EXERCISE_JOINT_LOAD_MAP = {
        # 肩部动作
        'overhead_press': {JointType.SHOULDER: 3.0, JointType.ROTATOR_CUFF: 2.5},
        'lateral_raise': {JointType.SHOULDER: 2.0, JointType.ROTATOR_CUFF: 2.0},
        'front_raise': {JointType.SHOULDER: 2.0, JointType.ROTATOR_CUFF: 1.5},
        'upright_row': {JointType.SHOULDER: 2.5, JointType.ROTATOR_CUFF: 3.0},  # 高风险
        
        # 胸部动作（涉及肩关节）
        'bench_press': {JointType.SHOULDER: 2.0, JointType.ROTATOR_CUFF: 1.5, JointType.WRIST: 1.0},
        'incline_press': {JointType.SHOULDER: 2.5, JointType.ROTATOR_CUFF: 2.0},
        'fly': {JointType.SHOULDER: 2.0, JointType.ROTATOR_CUFF: 2.5},
        'dip': {JointType.SHOULDER: 2.5, JointType.ELBOW: 2.0},
        
        # 背部动作
        'pull_up': {JointType.SHOULDER: 2.0, JointType.ELBOW: 1.5},
        'lat_pulldown': {JointType.SHOULDER: 1.5, JointType.ELBOW: 1.0},
        'row': {JointType.LOWER_BACK: 2.0, JointType.ELBOW: 1.5},
        'deadlift': {JointType.LOWER_BACK: 3.5, JointType.KNEE: 2.0},
        
        # 腿部动作
        'squat': {JointType.KNEE: 3.0, JointType.LOWER_BACK: 2.5},
        'leg_press': {JointType.KNEE: 2.5},
        'lunge': {JointType.KNEE: 2.5},
        'leg_extension': {JointType.KNEE: 2.0},
        'leg_curl': {JointType.KNEE: 1.5},
        
        # 手臂动作
        'curl': {JointType.ELBOW: 2.0, JointType.WRIST: 1.5},
        'tricep_extension': {JointType.ELBOW: 2.5},
        'pushdown': {JointType.ELBOW: 2.0, JointType.WRIST: 1.0},
        
        # 核心动作
        'crunch': {JointType.NECK: 1.5, JointType.LOWER_BACK: 1.0},
        'plank': {JointType.LOWER_BACK: 1.0, JointType.SHOULDER: 1.0},
    }
    
    # 动作名称关键词映射（用于匹配动作类型）
    EXERCISE_KEYWORDS = {
        'overhead_press': ['overhead', 'military', 'shoulder press', '推举', '肩推'],
        'lateral_raise': ['lateral raise', 'side raise', '侧平举'],
        'front_raise': ['front raise', '前平举'],
        'upright_row': ['upright row', '直立划船'],
        'bench_press': ['bench press', '卧推'],
        'incline_press': ['incline', '上斜'],
        'fly': ['fly', 'flye', '飞鸟'],
        'dip': ['dip', '双杠臂屈伸'],
        'pull_up': ['pull up', 'pullup', 'chin up', '引体向上'],
        'lat_pulldown': ['pulldown', 'lat pull', '下拉'],
        'row': ['row', '划船'],
        'deadlift': ['deadlift', '硬拉'],
        'squat': ['squat', '深蹲'],
        'leg_press': ['leg press', '腿举'],
        'lunge': ['lunge', '弓步'],
        'leg_extension': ['leg extension', '腿屈伸'],
        'leg_curl': ['leg curl', '腿弯举'],
        'curl': ['curl', 'bicep', '弯举'],
        'tricep_extension': ['tricep extension', 'skull crusher', '臂屈伸'],
        'pushdown': ['pushdown', '下压'],
        'crunch': ['crunch', '卷腹'],
        'plank': ['plank', '平板支撑'],
    }
    
    def __init__(self, backend_client, neo4j_client=None):
        """
        初始化动作稳定性管理器
        
        Args:
            backend_client: BackendClient实例，用于获取训练日志
            neo4j_client: Neo4j客户端实例，用于查询动作关系（可选）
        """
        self.backend_client = backend_client
        self.neo4j_client = neo4j_client
        logger.info("ExerciseStabilityManager initialized")
    
    async def prefer_familiar_exercises(
        self,
        user_id: int,
        candidate_exercises: List[Dict[str, Any]],
        days_back: int = 84  # 默认12周
    ) -> List[Dict[str, Any]]:
        """
        优先选择用户熟悉的动作
        
        从候选动作列表中，优先返回用户历史中使用过的动作。
        熟悉的动作更安全，更容易追踪渐进过载。
        
        Args:
            user_id: 用户ID
            candidate_exercises: 候选动作列表，每个动作包含exercise_id和name
            days_back: 回溯天数，默认84天（12周）
            
        Returns:
            List[Dict]: 排序后的动作列表，熟悉的动作排在前面
            
        Requirements: 12.1 - 优先使用用户历史中熟悉的动作
        """
        if not candidate_exercises:
            return []
        
        try:
            # 获取用户训练历史
            familiar_exercise_ids = await self._get_familiar_exercise_ids(
                user_id=user_id,
                days_back=days_back
            )
            
            # 分离熟悉和不熟悉的动作
            familiar_exercises = []
            unfamiliar_exercises = []
            
            for exercise in candidate_exercises:
                exercise_id = exercise.get('exercise_id') or exercise.get('id')
                if exercise_id in familiar_exercise_ids:
                    # 添加熟悉度信息
                    exercise_with_familiarity = exercise.copy()
                    exercise_with_familiarity['is_familiar'] = True
                    exercise_with_familiarity['usage_count'] = familiar_exercise_ids[exercise_id]
                    familiar_exercises.append(exercise_with_familiarity)
                else:
                    exercise_with_familiarity = exercise.copy()
                    exercise_with_familiarity['is_familiar'] = False
                    exercise_with_familiarity['usage_count'] = 0
                    unfamiliar_exercises.append(exercise_with_familiarity)
            
            # 按使用次数排序熟悉的动作
            familiar_exercises.sort(key=lambda x: x.get('usage_count', 0), reverse=True)
            
            # 合并列表：熟悉的在前，不熟悉的在后
            result = familiar_exercises + unfamiliar_exercises
            
            logger.info(
                f"动作优先级排序完成: user_id={user_id}, "
                f"familiar={len(familiar_exercises)}, "
                f"unfamiliar={len(unfamiliar_exercises)}",
                extra={
                    'user_id': user_id,
                    'familiar_count': len(familiar_exercises),
                    'unfamiliar_count': len(unfamiliar_exercises),
                    'total_candidates': len(candidate_exercises),
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"动作优先级排序失败: user_id={user_id}, error={e}")
            # 失败时返回原始列表
            return candidate_exercises
    
    async def _get_familiar_exercise_ids(
        self,
        user_id: int,
        days_back: int = 84
    ) -> Dict[str, int]:
        """
        获取用户熟悉的动作ID及使用次数
        
        Args:
            user_id: 用户ID
            days_back: 回溯天数
            
        Returns:
            Dict[str, int]: {exercise_id: usage_count}
        """
        try:
            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            # 获取训练日志
            logs = await self.backend_client.get_training_logs(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # 统计每个动作的使用次数
            exercise_counts: Dict[str, int] = {}
            
            for log in logs:
                # 从actual_exercises中提取动作ID
                actual_exercises = log.get('actual_exercises', [])
                if isinstance(actual_exercises, str):
                    import json
                    try:
                        actual_exercises = json.loads(actual_exercises)
                    except (json.JSONDecodeError, ValueError):
                        actual_exercises = []

                for exercise in actual_exercises:
                    exercise_id = exercise.get('exercise_id')
                    if exercise_id:
                        exercise_counts[exercise_id] = exercise_counts.get(exercise_id, 0) + 1
            
            return exercise_counts
            
        except Exception as e:
            logger.error(f"获取熟悉动作失败: user_id={user_id}, error={e}")
            return {}

    
    async def suggest_replacement(
        self,
        user_id: int,
        exercise_id: str,
        exercise_name: Optional[str] = None
    ) -> ExerciseReplacementSuggestion:
        """
        用户主动请求时提供动作替换建议
        
        利用Neo4j的PROGRESSES_TO关系推荐进阶或变式动作。
        只有在用户主动请求时才提供建议，不主动推荐更换。
        
        Args:
            user_id: 用户ID
            exercise_id: 当前动作ID
            exercise_name: 当前动作名称（可选）
            
        Returns:
            ExerciseReplacementSuggestion: 替换建议
            
        Requirements: 12.2, 12.4 - 用户主动请求时提供相似动作建议
        """
        try:
            # 获取动作使用周数
            weeks_used = await self._get_exercise_usage_weeks(user_id, exercise_id)
            
            # 获取替换建议
            suggested_exercises = await self._find_replacement_exercises(
                exercise_id=exercise_id,
                exercise_name=exercise_name
            )
            
            # 生成建议原因
            if weeks_used >= self.EXERCISE_USAGE_THRESHOLD_WEEKS:
                reason = f"该动作已连续使用{weeks_used}周，可以考虑尝试变式动作以获得新的刺激"
            elif weeks_used > 0:
                reason = f"该动作已使用{weeks_used}周，以下是一些可选的变式动作"
            else:
                reason = "以下是一些可选的变式动作，可以根据需要选择"
            
            result = ExerciseReplacementSuggestion(
                original_exercise_id=exercise_id,
                original_exercise_name=exercise_name or exercise_id,
                suggested_exercises=suggested_exercises,
                reason=reason,
                weeks_used=weeks_used
            )
            
            logger.info(
                f"动作替换建议生成: user_id={user_id}, "
                f"exercise_id={exercise_id}, "
                f"weeks_used={weeks_used}, "
                f"suggestions={len(suggested_exercises)}",
                extra={
                    'user_id': user_id,
                    'exercise_id': exercise_id,
                    'weeks_used': weeks_used,
                    'suggestions_count': len(suggested_exercises),
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"动作替换建议生成失败: user_id={user_id}, "
                f"exercise_id={exercise_id}, error={e}"
            )
            return ExerciseReplacementSuggestion(
                original_exercise_id=exercise_id,
                original_exercise_name=exercise_name or exercise_id,
                suggested_exercises=[],
                reason=f"无法获取替换建议: {str(e)}",
                weeks_used=0
            )
    
    async def _get_exercise_usage_weeks(
        self,
        user_id: int,
        exercise_id: str
    ) -> int:
        """
        获取动作连续使用的周数
        
        Args:
            user_id: 用户ID
            exercise_id: 动作ID
            
        Returns:
            int: 连续使用周数
        """
        try:
            # 获取最近16周的训练日志
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=112)).strftime('%Y-%m-%d')
            
            logs = await self.backend_client.get_training_logs(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not logs:
                return 0
            
            # 按周分组
            weeks_with_exercise = set()
            
            for log in logs:
                session_date = log.get('session_date')
                if not session_date:
                    continue
                
                # 检查该日志是否包含目标动作
                actual_exercises = log.get('actual_exercises', [])
                if isinstance(actual_exercises, str):
                    import json
                    try:
                        actual_exercises = json.loads(actual_exercises)
                    except (json.JSONDecodeError, ValueError):
                        actual_exercises = []

                for exercise in actual_exercises:
                    if exercise.get('exercise_id') == exercise_id:
                        # 计算周数（从今天开始）
                        try:
                            log_date = datetime.strptime(session_date, '%Y-%m-%d')
                            days_ago = (datetime.now() - log_date).days
                            week_number = days_ago // 7
                            weeks_with_exercise.add(week_number)
                        except (ValueError, TypeError):
                            pass
                        break
            
            # 计算连续周数（从第0周开始）
            if not weeks_with_exercise:
                return 0
            
            consecutive_weeks = 0
            for week in range(max(weeks_with_exercise) + 1):
                if week in weeks_with_exercise:
                    consecutive_weeks += 1
                else:
                    # 允许1周的间隔
                    if week > 0 and (week - 1) in weeks_with_exercise:
                        continue
                    break
            
            return consecutive_weeks
            
        except Exception as e:
            logger.error(f"获取动作使用周数失败: user_id={user_id}, error={e}")
            return 0
    
    async def _find_replacement_exercises(
        self,
        exercise_id: str,
        exercise_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查找替换动作
        
        优先使用Neo4j的PROGRESSES_TO关系，如果没有则基于相同肌群推荐。
        
        Args:
            exercise_id: 动作ID
            exercise_name: 动作名称
            
        Returns:
            List[Dict]: 替换动作列表
        """
        suggestions = []
        
        # 方法1：使用Neo4j查询PROGRESSES_TO关系
        if self.neo4j_client:
            try:
                neo4j_suggestions = await self._query_progression_exercises(exercise_id)
                suggestions.extend(neo4j_suggestions)
            except Exception as e:
                logger.warning(f"Neo4j查询失败: {e}")
        
        # 方法2：如果Neo4j没有结果，基于相同肌群推荐
        if not suggestions and self.neo4j_client:
            try:
                muscle_based_suggestions = await self._query_same_muscle_exercises(
                    exercise_id, exercise_name
                )
                suggestions.extend(muscle_based_suggestions)
            except Exception as e:
                logger.warning(f"肌群查询失败: {e}")
        
        # 去重并限制数量
        seen_ids = set()
        unique_suggestions = []
        for suggestion in suggestions:
            ex_id = suggestion.get('exercise_id')
            if ex_id and ex_id not in seen_ids and ex_id != exercise_id:
                seen_ids.add(ex_id)
                unique_suggestions.append(suggestion)
                if len(unique_suggestions) >= 5:
                    break
        
        return unique_suggestions
    
    async def _query_progression_exercises(
        self,
        exercise_id: str
    ) -> List[Dict[str, Any]]:
        """
        查询动作进阶路径（使用PROGRESSES_TO关系）
        
        Args:
            exercise_id: 动作ID
            
        Returns:
            List[Dict]: 进阶动作列表
        """
        if not self.neo4j_client:
            return []
        
        try:
            # 查询进阶动作
            query = """
            MATCH (e1:Exercise {id: $exercise_id})-[:PROGRESSES_TO]->(e2:Exercise)
            RETURN e2.id as exercise_id, 
                   e2.name_zh as name_zh, 
                   e2.name_en as name_en,
                   e2.difficulty as difficulty,
                   e2.primary_muscle_zh as primary_muscle,
                   'progression' as suggestion_type
            LIMIT 3
            """
            
            result = await self.neo4j_client.run_query(query, {'exercise_id': exercise_id})
            
            suggestions = []
            for record in result:
                suggestions.append({
                    'exercise_id': record.get('exercise_id'),
                    'name_zh': record.get('name_zh'),
                    'name_en': record.get('name_en'),
                    'difficulty': record.get('difficulty'),
                    'primary_muscle': record.get('primary_muscle'),
                    'suggestion_type': 'progression',
                    'reason': '进阶动作'
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"查询进阶动作失败: exercise_id={exercise_id}, error={e}")
            return []
    
    async def _query_same_muscle_exercises(
        self,
        exercise_id: str,
        exercise_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查询相同肌群的动作
        
        Args:
            exercise_id: 动作ID
            exercise_name: 动作名称
            
        Returns:
            List[Dict]: 相同肌群动作列表
        """
        if not self.neo4j_client:
            return []
        
        try:
            # 先获取原动作的主要肌群
            query = """
            MATCH (e:Exercise {id: $exercise_id})
            RETURN e.primary_muscle_zh as primary_muscle, e.difficulty as difficulty
            """
            
            result = await self.neo4j_client.run_query(query, {'exercise_id': exercise_id})
            
            if not result:
                return []
            
            primary_muscle = result[0].get('primary_muscle')
            current_difficulty = result[0].get('difficulty', 'intermediate')
            
            if not primary_muscle:
                return []
            
            # 查询相同肌群的其他动作
            query = """
            MATCH (e:Exercise)
            WHERE e.primary_muscle_zh = $primary_muscle 
              AND e.id <> $exercise_id
            RETURN e.id as exercise_id,
                   e.name_zh as name_zh,
                   e.name_en as name_en,
                   e.difficulty as difficulty,
                   e.primary_muscle_zh as primary_muscle,
                   'same_muscle' as suggestion_type
            ORDER BY 
                CASE e.difficulty 
                    WHEN $current_difficulty THEN 0
                    ELSE 1 
                END,
                e.name_zh
            LIMIT 5
            """
            
            result = await self.neo4j_client.run_query(query, {
                'exercise_id': exercise_id,
                'primary_muscle': primary_muscle,
                'current_difficulty': current_difficulty
            })
            
            suggestions = []
            for record in result:
                suggestions.append({
                    'exercise_id': record.get('exercise_id'),
                    'name_zh': record.get('name_zh'),
                    'name_en': record.get('name_en'),
                    'difficulty': record.get('difficulty'),
                    'primary_muscle': record.get('primary_muscle'),
                    'suggestion_type': 'same_muscle',
                    'reason': f'相同肌群（{primary_muscle}）的变式动作'
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"查询相同肌群动作失败: exercise_id={exercise_id}, error={e}")
            return []

    
    async def check_joint_fatigue(
        self,
        user_id: int,
        joint: Optional[JointType] = None,
        days_back: int = 7  # 默认检查最近一周
    ) -> Dict[str, Any]:
        """
        监控易损部位累计负荷
        
        检查肩袖、腕关节等易损部位的累计负荷，
        超过阈值时提示用户注意休息或降低强度。
        
        Args:
            user_id: 用户ID
            joint: 指定检查的关节（可选，不指定则检查所有）
            days_back: 回溯天数，默认7天（一周）
            
        Returns:
            Dict[str, Any]: 关节疲劳状态报告
            
        Requirements: 12.3 - 监控易损部位累计负荷
        """
        try:
            # 获取训练日志
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            logs = await self.backend_client.get_training_logs(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # 计算各关节的累计负荷
            joint_loads = self._calculate_joint_loads(logs)
            
            # 生成疲劳状态报告
            fatigue_statuses = []
            warnings = []
            
            joints_to_check = [joint] if joint else list(JointType)
            
            for j in joints_to_check:
                status = self._evaluate_joint_fatigue(j, joint_loads.get(j, {}))
                fatigue_statuses.append(status)
                
                if status.fatigue_level in [FatigueLevel.HIGH, FatigueLevel.CRITICAL]:
                    warnings.append(status)
            
            # 生成总体建议
            overall_recommendation = self._generate_overall_recommendation(warnings)
            
            result = {
                'user_id': user_id,
                'period_days': days_back,
                'check_date': datetime.now().strftime('%Y-%m-%d'),
                'joint_statuses': [s.to_dict() for s in fatigue_statuses],
                'warnings': [w.to_dict() for w in warnings],
                'has_warnings': len(warnings) > 0,
                'overall_recommendation': overall_recommendation,
            }
            
            logger.info(
                f"关节疲劳检查完成: user_id={user_id}, "
                f"warnings={len(warnings)}",
                extra={
                    'user_id': user_id,
                    'days_back': days_back,
                    'warnings_count': len(warnings),
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"关节疲劳检查失败: user_id={user_id}, error={e}")
            return {
                'user_id': user_id,
                'period_days': days_back,
                'check_date': datetime.now().strftime('%Y-%m-%d'),
                'joint_statuses': [],
                'warnings': [],
                'has_warnings': False,
                'overall_recommendation': f"检查失败: {str(e)}",
                'error': str(e)
            }
    
    def _calculate_joint_loads(
        self,
        logs: List[Dict[str, Any]]
    ) -> Dict[JointType, Dict[str, Any]]:
        """
        计算各关节的累计负荷
        
        Args:
            logs: 训练日志列表
            
        Returns:
            Dict[JointType, Dict]: 各关节的负荷数据
        """
        joint_loads: Dict[JointType, Dict[str, Any]] = {
            j: {'load': 0.0, 'exercises': []} for j in JointType
        }
        
        for log in logs:
            actual_exercises = log.get('actual_exercises', [])
            if isinstance(actual_exercises, str):
                import json
                try:
                    actual_exercises = json.loads(actual_exercises)
                except (json.JSONDecodeError, ValueError):
                    actual_exercises = []

            for exercise in actual_exercises:
                exercise_name = exercise.get('exercise_name', '') or exercise.get('name', '')
                exercise_id = exercise.get('exercise_id', '')
                sets_completed = exercise.get('sets_completed', 0) or len(exercise.get('sets', []))
                
                # 识别动作类型
                exercise_type = self._identify_exercise_type(exercise_name)
                
                if exercise_type and exercise_type in self.EXERCISE_JOINT_LOAD_MAP:
                    joint_coefficients = self.EXERCISE_JOINT_LOAD_MAP[exercise_type]
                    
                    for joint, coefficient in joint_coefficients.items():
                        load = sets_completed * coefficient
                        joint_loads[joint]['load'] += load
                        
                        if exercise_name and exercise_name not in joint_loads[joint]['exercises']:
                            joint_loads[joint]['exercises'].append(exercise_name)
        
        return joint_loads
    
    def _identify_exercise_type(self, exercise_name: str) -> Optional[str]:
        """
        识别动作类型
        
        Args:
            exercise_name: 动作名称
            
        Returns:
            Optional[str]: 动作类型
        """
        if not exercise_name:
            return None
        
        exercise_name_lower = exercise_name.lower()
        
        for exercise_type, keywords in self.EXERCISE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in exercise_name_lower:
                    return exercise_type
        
        return None
    
    def _evaluate_joint_fatigue(
        self,
        joint: JointType,
        load_data: Dict[str, Any]
    ) -> JointFatigueStatus:
        """
        评估关节疲劳状态
        
        Args:
            joint: 关节类型
            load_data: 负荷数据
            
        Returns:
            JointFatigueStatus: 疲劳状态
        """
        accumulated_load = load_data.get('load', 0.0)
        exercises = load_data.get('exercises', [])
        threshold = self.JOINT_LOAD_THRESHOLDS.get(joint, 50.0)
        
        # 计算负荷百分比
        load_percentage = (accumulated_load / threshold * 100) if threshold > 0 else 0
        
        # 确定疲劳等级
        if load_percentage < 50:
            fatigue_level = FatigueLevel.LOW
            recommendation = "负荷正常，可以继续训练"
        elif load_percentage < 75:
            fatigue_level = FatigueLevel.MODERATE
            recommendation = "负荷适中，注意训练后的恢复"
        elif load_percentage < 100:
            fatigue_level = FatigueLevel.HIGH
            recommendation = f"⚠️ {joint.value}负荷较高，建议减少相关动作的组数或增加休息"
        else:
            fatigue_level = FatigueLevel.CRITICAL
            recommendation = f"🚨 {joint.value}负荷过高！强烈建议休息1-2天或降低训练强度"
        
        return JointFatigueStatus(
            joint=joint,
            fatigue_level=fatigue_level,
            accumulated_load=round(accumulated_load, 1),
            threshold=threshold,
            load_percentage=round(load_percentage, 1),
            exercises_involved=exercises,
            recommendation=recommendation
        )
    
    def _generate_overall_recommendation(
        self,
        warnings: List[JointFatigueStatus]
    ) -> str:
        """
        生成总体建议
        
        Args:
            warnings: 警告列表
            
        Returns:
            str: 总体建议
        """
        if not warnings:
            return "✅ 所有关节负荷正常，可以继续按计划训练"
        
        critical_joints = [w for w in warnings if w.fatigue_level == FatigueLevel.CRITICAL]
        high_joints = [w for w in warnings if w.fatigue_level == FatigueLevel.HIGH]
        
        if critical_joints:
            joint_names = [self._get_joint_chinese_name(w.joint) for w in critical_joints]
            return f"🚨 警告：{', '.join(joint_names)}负荷过高！建议：\n" \
                   f"1. 休息1-2天让关节恢复\n" \
                   f"2. 下次训练时减少相关动作的组数\n" \
                   f"3. 考虑使用替代动作减轻关节压力"
        
        if high_joints:
            joint_names = [self._get_joint_chinese_name(w.joint) for w in high_joints]
            return f"⚠️ 注意：{', '.join(joint_names)}负荷较高。建议：\n" \
                   f"1. 适当减少相关动作的组数\n" \
                   f"2. 确保训练后充分休息\n" \
                   f"3. 可以考虑增加热身和拉伸"
        
        return "✅ 关节负荷在可控范围内"
    
    def _get_joint_chinese_name(self, joint: JointType) -> str:
        """
        获取关节的中文名称
        
        Args:
            joint: 关节类型
            
        Returns:
            str: 中文名称
        """
        names = {
            JointType.SHOULDER: "肩关节",
            JointType.ROTATOR_CUFF: "肩袖",
            JointType.WRIST: "腕关节",
            JointType.ELBOW: "肘关节",
            JointType.KNEE: "膝关节",
            JointType.LOWER_BACK: "下背部",
            JointType.NECK: "颈部",
        }
        return names.get(joint, joint.value)
    
    async def get_exercise_stability_report(
        self,
        user_id: int,
        candidate_exercises: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        获取动作稳定性综合报告
        
        综合分析用户的动作使用情况和关节负荷状态。
        
        Args:
            user_id: 用户ID
            candidate_exercises: 候选动作列表（可选）
            
        Returns:
            Dict[str, Any]: 综合报告
        """
        try:
            # 检查关节疲劳
            joint_report = await self.check_joint_fatigue(user_id)
            
            # 如果有候选动作，进行优先级排序
            sorted_exercises = []
            if candidate_exercises:
                sorted_exercises = await self.prefer_familiar_exercises(
                    user_id=user_id,
                    candidate_exercises=candidate_exercises
                )
            
            # 统计熟悉动作数量
            familiar_count = sum(1 for e in sorted_exercises if e.get('is_familiar', False))
            
            return {
                'user_id': user_id,
                'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'joint_fatigue': joint_report,
                'exercise_familiarity': {
                    'total_candidates': len(sorted_exercises),
                    'familiar_count': familiar_count,
                    'unfamiliar_count': len(sorted_exercises) - familiar_count,
                    'sorted_exercises': sorted_exercises[:10],  # 只返回前10个
                },
                'recommendations': {
                    'joint_recommendation': joint_report.get('overall_recommendation', ''),
                    'exercise_recommendation': self._generate_exercise_recommendation(
                        familiar_count, len(sorted_exercises)
                    ),
                }
            }
            
        except Exception as e:
            logger.error(f"生成稳定性报告失败: user_id={user_id}, error={e}")
            return {
                'user_id': user_id,
                'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def _generate_exercise_recommendation(
        self,
        familiar_count: int,
        total_count: int
    ) -> str:
        """
        生成动作选择建议
        
        Args:
            familiar_count: 熟悉动作数量
            total_count: 总动作数量
            
        Returns:
            str: 建议
        """
        if total_count == 0:
            return "暂无候选动作"
        
        familiarity_ratio = familiar_count / total_count
        
        if familiarity_ratio >= 0.8:
            return "✅ 大部分动作都是您熟悉的，这有助于追踪渐进过载"
        elif familiarity_ratio >= 0.5:
            return "💡 建议优先选择熟悉的动作，新动作可以逐步引入"
        else:
            return "⚠️ 候选动作中熟悉的较少，建议先从基础动作开始"
