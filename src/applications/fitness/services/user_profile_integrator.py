# -*- coding: utf-8 -*-
"""
User Profile Integrator Service - 增强版

用户档案整合服务，确保训练日志与用户档案MCP的数据一致性。
增强版支持Layer3规则引擎所需的所有约束提取。

Requirements: 
- 16.1-16.7: 用户档案完整覆盖
- 18.1-18.6: 领域专业条件约束

作者: BUILD_BODY Team
版本: 2.0.0
日期: 2026-01-06
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============ 枚举定义 ============

class BodyType(Enum):
    """体型分类"""
    ECTOMORPH = "ectomorph"      # 外胚型（瘦长型）
    MESOMORPH = "mesomorph"      # 中胚型（肌肉型）
    ENDOMORPH = "endomorph"      # 内胚型（圆润型）
    UNKNOWN = "unknown"


class FitnessLevel(Enum):
    """健身等级"""
    BEGINNER = "beginner"
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ELITE = "elite"


class TrainingGoal(Enum):
    """训练目标"""
    MUSCLE_GAIN = "muscle_gain"
    FAT_LOSS = "fat_loss"
    STRENGTH = "strength"
    ENDURANCE = "endurance"
    BODY_SHAPING = "body_shaping"
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    REHABILITATION = "rehabilitation"
    GENERAL_FITNESS = "general_fitness"


# ============ 数据类定义 ============

@dataclass
class UserProfileDefaults:
    """用户档案默认值配置"""
    
    # 基础信息默认值
    DEFAULT_AGE = 25
    DEFAULT_HEIGHT = 170  # cm
    DEFAULT_WEIGHT = 65   # kg
    DEFAULT_GENDER = 'unknown'
    DEFAULT_BODY_TYPE = 'unknown'
    
    # 训练系统默认值
    DEFAULT_VOLUME_MULTIPLIER = 1.0
    DEFAULT_RECOVERY_FACTOR = 1.0
    DEFAULT_USER_TYPE = 'other'
    DEFAULT_CONSECUTIVE_WEEKS = 0
    
    # 健身配置默认值
    DEFAULT_FITNESS_LEVEL = 'beginner'
    DEFAULT_TRAINING_DAYS = 3
    DEFAULT_SESSION_DURATION = 60  # minutes
    DEFAULT_PREFERRED_TIME = None
    
    # 健身目标默认值
    DEFAULT_PRIMARY_GOAL = 'general_fitness'
    
    # 营养默认值
    DEFAULT_DAILY_CALORIES = 2000
    DEFAULT_PROTEIN_G = 100
    DEFAULT_CARBS_G = 250
    DEFAULT_FAT_G = 65


@dataclass
class Layer3Constraints:
    """Layer3规则约束集合"""
    
    # 基础约束
    fitness_level: str = "beginner"
    age: int = 25
    gender: str = "unknown"
    
    # 体型约束 (Requirements 18.1)
    body_type: str = "unknown"
    body_type_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # 训练频率约束 (Requirements 18.2)
    training_days_per_week: int = 3
    training_frequency_strategy: str = "balanced"
    
    # 训练时长约束 (Requirements 18.3)
    session_duration_minutes: int = 60
    max_exercises_per_session: int = 8
    
    # 目标对齐约束 (Requirements 18.4)
    primary_goal: str = "general_fitness"
    goal_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # 渐进超负荷约束 (Requirements 18.5)
    consecutive_training_weeks: int = 0
    training_phase: str = "novice"
    allowed_difficulties: List[str] = field(default_factory=list)
    
    # 营养约束 (Requirements 18.6)
    daily_calories: int = 2000
    protein_g: int = 100
    nutrition_status: str = "adequate"
    intensity_limit: str = "any"
    
    # 安全约束
    injuries: List[Dict[str, Any]] = field(default_factory=list)
    postural_issues: List[str] = field(default_factory=list)
    medical_conditions: List[str] = field(default_factory=list)
    
    # 器械约束
    available_equipment: List[str] = field(default_factory=list)
    
    # 恢复约束
    personal_recovery_factor: float = 1.0
    personal_volume_multiplier: float = 1.0


class UserProfileIntegrator:
    """
    用户档案整合服务
    
    职责：
    1. 确保训练日志与用户档案的数据一致性
    2. 提供用户档案不完整时的默认值策略
    3. 同步训练系统字段到用户档案
    
    Requirements: 16.2, 16.3, 16.4
    """
    
    def __init__(self, backend_client):
        """
        初始化用户档案整合器
        
        Args:
            backend_client: BackendClient实例
        """
        self.backend_client = backend_client
        self.defaults = UserProfileDefaults()
        logger.info("UserProfileIntegrator initialized")
    
    async def get_user_profile_with_defaults(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        获取用户档案，不完整时使用默认值填充
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 完整的用户档案（含默认值）
            
        Requirements: 16.4 - 用户档案不完整时使用合理默认值
        """
        try:
            # 从后端获取用户档案
            profile = await self.backend_client.get_user_profile(user_id)
            
            # 应用默认值策略
            profile = self._apply_defaults(profile)
            
            logger.info(
                f"获取用户档案成功（含默认值）: user_id={user_id}",
                extra={'user_id': user_id}
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"获取用户档案失败: user_id={user_id}, error={e}")
            # 返回完整的默认档案
            return self._get_full_default_profile(user_id)
    
    def _apply_defaults(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        为不完整的档案字段应用默认值
        
        Args:
            profile: 原始用户档案
            
        Returns:
            Dict[str, Any]: 填充默认值后的档案
        """
        # 确保basic_info存在
        if 'basic_info' not in profile or not profile['basic_info']:
            profile['basic_info'] = {}
        
        basic_info = profile['basic_info']
        basic_info.setdefault('age', self.defaults.DEFAULT_AGE)
        basic_info.setdefault('height', self.defaults.DEFAULT_HEIGHT)
        basic_info.setdefault('weight', self.defaults.DEFAULT_WEIGHT)
        basic_info.setdefault('gender', self.defaults.DEFAULT_GENDER)
        
        # 确保training_system存在
        if 'training_system' not in profile or not profile['training_system']:
            profile['training_system'] = {}
        
        training_system = profile['training_system']
        training_system.setdefault('personal_volume_multiplier', self.defaults.DEFAULT_VOLUME_MULTIPLIER)
        training_system.setdefault('personal_recovery_factor', self.defaults.DEFAULT_RECOVERY_FACTOR)
        training_system.setdefault('user_type', self.defaults.DEFAULT_USER_TYPE)
        training_system.setdefault('consecutive_training_weeks', self.defaults.DEFAULT_CONSECUTIVE_WEEKS)
        
        # 确保fitness_config存在
        if 'fitness_config' not in profile or not profile['fitness_config']:
            profile['fitness_config'] = {}
        
        fitness_config = profile['fitness_config']
        fitness_config.setdefault('fitness_level', self.defaults.DEFAULT_FITNESS_LEVEL)
        fitness_config.setdefault('training_days_per_week', self.defaults.DEFAULT_TRAINING_DAYS)
        fitness_config.setdefault('training_duration_per_session', self.defaults.DEFAULT_SESSION_DURATION)
        
        # 确保fitness_goals存在
        if 'fitness_goals' not in profile or not profile['fitness_goals']:
            profile['fitness_goals'] = {}
        
        fitness_goals = profile['fitness_goals']
        fitness_goals.setdefault('primary_goal', self.defaults.DEFAULT_PRIMARY_GOAL)
        
        # 确保其他必要字段存在
        profile.setdefault('nutrition_profile', {})
        profile.setdefault('strength_levels', {})
        profile.setdefault('health_profile', {'injuries': [], 'medical_conditions': []})
        
        return profile
    
    def _get_full_default_profile(self, user_id: int) -> Dict[str, Any]:
        """
        获取完整的默认用户档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 默认用户档案
        """
        return {
            'user_id': str(user_id),
            'basic_info': {
                'age': self.defaults.DEFAULT_AGE,
                'gender': self.defaults.DEFAULT_GENDER,
                'height': self.defaults.DEFAULT_HEIGHT,
                'weight': self.defaults.DEFAULT_WEIGHT,
                'body_type': None,
                'user_type': self.defaults.DEFAULT_USER_TYPE,
            },
            'nutrition_profile': {
                'daily_calories': 2000,
                'protein_g': 100,
                'carbs_g': 250,
                'fat_g': 65
            },
            'fitness_config': {
                'fitness_level': self.defaults.DEFAULT_FITNESS_LEVEL,
                'training_days_per_week': self.defaults.DEFAULT_TRAINING_DAYS,
                'training_duration_per_session': self.defaults.DEFAULT_SESSION_DURATION,
                'preferred_training_time': None,
                'preferred_rest_pattern': None,
            },
            'fitness_goals': {
                'primary_goal': self.defaults.DEFAULT_PRIMARY_GOAL,
                'target_weight': self.defaults.DEFAULT_WEIGHT
            },
            'strength_levels': {},
            'health_profile': {
                'injuries': [],
                'medical_conditions': []
            },
            'training_system': {
                'preferred_training_time': None,
                'body_type': None,
                'user_type': self.defaults.DEFAULT_USER_TYPE,
                'campus_name': None,
                'personal_volume_multiplier': self.defaults.DEFAULT_VOLUME_MULTIPLIER,
                'personal_recovery_factor': self.defaults.DEFAULT_RECOVERY_FACTOR,
                'last_volume_adjusted_at': None,
                'consecutive_training_weeks': self.defaults.DEFAULT_CONSECUTIVE_WEEKS,
            },
            'created_at': None,
            'updated_at': None,
            '_default': True  # 标记为默认档案
        }
    
    def get_volume_multiplier(self, profile: Dict[str, Any]) -> float:
        """
        从用户档案获取容量系数（带边界检查）
        
        Args:
            profile: 用户档案
            
        Returns:
            float: 容量系数（0.7-1.5）
        """
        training_system = profile.get('training_system', {})
        multiplier = training_system.get('personal_volume_multiplier', self.defaults.DEFAULT_VOLUME_MULTIPLIER)
        
        # 边界检查
        return max(0.7, min(1.5, float(multiplier)))
    
    def get_user_type(self, profile: Dict[str, Any]) -> str:
        """
        从用户档案获取用户类型
        
        Args:
            profile: 用户档案
            
        Returns:
            str: 用户类型（student/worker/other）
        """
        training_system = profile.get('training_system', {})
        return training_system.get('user_type', self.defaults.DEFAULT_USER_TYPE)
    
    def is_student(self, profile: Dict[str, Any]) -> bool:
        """
        判断是否为大学生用户
        
        Args:
            profile: 用户档案
            
        Returns:
            bool: 是否为大学生
        """
        return self.get_user_type(profile) == 'student'
    
    def is_worker(self, profile: Dict[str, Any]) -> bool:
        """
        判断是否为上班族用户
        
        Args:
            profile: 用户档案
            
        Returns:
            bool: 是否为上班族
        """
        return self.get_user_type(profile) == 'worker'
    
    def get_preferred_training_time(self, profile: Dict[str, Any]) -> Optional[str]:
        """
        获取用户偏好的训练时间
        
        Args:
            profile: 用户档案
            
        Returns:
            Optional[str]: 训练时间偏好
        """
        # 优先从training_system获取
        training_system = profile.get('training_system', {})
        time_pref = training_system.get('preferred_training_time')
        
        if time_pref:
            return time_pref
        
        # 降级从fitness_config获取
        fitness_config = profile.get('fitness_config', {})
        return fitness_config.get('preferred_training_time')
    
    def get_consecutive_training_weeks(self, profile: Dict[str, Any]) -> int:
        """
        获取连续训练周数
        
        Args:
            profile: 用户档案
            
        Returns:
            int: 连续训练周数
        """
        training_system = profile.get('training_system', {})
        return int(training_system.get('consecutive_training_weeks', 0))
    
    def validate_profile_completeness(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证用户档案完整性
        
        Args:
            profile: 用户档案
            
        Returns:
            Dict[str, Any]: 验证结果，包含缺失字段列表
        """
        missing_fields = []
        warnings = []
        
        # 检查基础信息
        basic_info = profile.get('basic_info', {})
        if not basic_info.get('age'):
            missing_fields.append('basic_info.age')
        if not basic_info.get('height'):
            missing_fields.append('basic_info.height')
        if not basic_info.get('weight'):
            missing_fields.append('basic_info.weight')
        if not basic_info.get('gender'):
            missing_fields.append('basic_info.gender')
        
        # 检查健身配置
        fitness_config = profile.get('fitness_config', {})
        if not fitness_config.get('fitness_level'):
            missing_fields.append('fitness_config.fitness_level')
        if not fitness_config.get('training_days_per_week'):
            warnings.append('fitness_config.training_days_per_week 未设置，将使用默认值3天')
        
        # 检查健身目标
        fitness_goals = profile.get('fitness_goals', {})
        if not fitness_goals.get('primary_goal'):
            warnings.append('fitness_goals.primary_goal 未设置，将使用默认目标')
        
        is_complete = len(missing_fields) == 0
        
        return {
            'is_complete': is_complete,
            'missing_fields': missing_fields,
            'warnings': warnings,
            'completeness_score': 1.0 - (len(missing_fields) / 10.0)  # 简单的完整度评分
        }
    
    # ============ Layer3约束提取方法 (Requirements 16.1-16.7, 18.1-18.6) ============
    
    def extract_layer3_constraints(self, profile: Dict[str, Any]) -> Layer3Constraints:
        """
        从用户档案提取Layer3规则所需的所有约束
        
        Requirements: 16.1-16.7
        
        Args:
            profile: 用户档案
            
        Returns:
            Layer3Constraints: 约束集合
        """
        # 应用默认值
        profile = self._apply_defaults(profile)
        
        # 提取各类约束
        basic_info = profile.get('basic_info', {})
        fitness_config = profile.get('fitness_config', {})
        fitness_goals = profile.get('fitness_goals', {})
        training_system = profile.get('training_system', {})
        nutrition_profile = profile.get('nutrition_profile', {})
        health_profile = profile.get('health_profile', {})
        
        # 计算训练阶段
        consecutive_weeks = training_system.get('consecutive_training_weeks', 0)
        training_phase, allowed_difficulties = self._calculate_training_phase(
            consecutive_weeks,
            fitness_config.get('fitness_level', 'beginner')
        )
        
        # 计算营养状态
        weight = basic_info.get('weight', 70)
        daily_calories = nutrition_profile.get('daily_calories', 2000)
        nutrition_status, intensity_limit = self._calculate_nutrition_status(
            daily_calories, weight
        )
        
        # 计算体型偏好
        body_type = basic_info.get('body_type', 'unknown')
        body_type_preferences = self._get_body_type_preferences(body_type)
        
        # 计算目标偏好
        primary_goal = fitness_goals.get('primary_goal', 'general_fitness')
        goal_preferences = self._get_goal_preferences(primary_goal)
        
        # 计算训练频率策略
        training_days = fitness_config.get('training_days_per_week', 3)
        frequency_strategy = self._calculate_frequency_strategy(training_days)
        
        # 计算每次训练最大动作数
        session_duration = fitness_config.get('training_duration_per_session', 60)
        max_exercises = self._calculate_max_exercises(session_duration)
        
        return Layer3Constraints(
            # 基础约束
            fitness_level=fitness_config.get('fitness_level', 'beginner'),
            age=basic_info.get('age', 25),
            gender=basic_info.get('gender', 'unknown'),
            
            # 体型约束 (18.1)
            body_type=body_type,
            body_type_preferences=body_type_preferences,
            
            # 训练频率约束 (18.2)
            training_days_per_week=training_days,
            training_frequency_strategy=frequency_strategy,
            
            # 训练时长约束 (18.3)
            session_duration_minutes=session_duration,
            max_exercises_per_session=max_exercises,
            
            # 目标对齐约束 (18.4)
            primary_goal=primary_goal,
            goal_preferences=goal_preferences,
            
            # 渐进超负荷约束 (18.5)
            consecutive_training_weeks=consecutive_weeks,
            training_phase=training_phase,
            allowed_difficulties=allowed_difficulties,
            
            # 营养约束 (18.6)
            daily_calories=daily_calories,
            protein_g=nutrition_profile.get('protein_g', 100),
            nutrition_status=nutrition_status,
            intensity_limit=intensity_limit,
            
            # 安全约束
            injuries=health_profile.get('injuries', []),
            postural_issues=health_profile.get('postural_issues', []),
            medical_conditions=health_profile.get('medical_conditions', []),
            
            # 器械约束
            available_equipment=fitness_config.get('available_equipment', []),
            
            # 恢复约束
            personal_recovery_factor=training_system.get('personal_recovery_factor', 1.0),
            personal_volume_multiplier=training_system.get('personal_volume_multiplier', 1.0)
        )
    
    def _calculate_training_phase(
        self,
        consecutive_weeks: int,
        fitness_level: str
    ) -> Tuple[str, List[str]]:
        """
        计算训练阶段和允许的难度
        
        Requirements: 18.5 - 渐进超负荷约束
        """
        # 根据训练周数确定阶段
        if consecutive_weeks < 4:
            phase = "novice"
            base_difficulties = ["beginner", "easy", "novice", "初级", "简单"]
        elif consecutive_weeks < 12:
            phase = "adaptation"
            base_difficulties = ["beginner", "intermediate", "easy", "moderate", 
                               "初级", "中级", "简单", "中等"]
        else:
            phase = "mature"
            base_difficulties = ["beginner", "intermediate", "advanced", 
                               "初级", "中级", "高级"]
        
        # 根据用户等级进一步调整
        fitness_level_lower = fitness_level.lower()
        if fitness_level_lower in ["advanced", "elite", "高级", "精英"]:
            base_difficulties.extend(["advanced", "elite", "hard", "高级", "困难", "精英"])
        
        return phase, list(set(base_difficulties))
    
    def _calculate_nutrition_status(
        self,
        daily_calories: int,
        weight: float
    ) -> Tuple[str, str]:
        """
        计算营养状态和强度限制
        
        Requirements: 18.6 - 营养约束
        """
        # 基础代谢估算（简化版）
        bmr_estimate = weight * 24
        calorie_ratio = daily_calories / bmr_estimate if bmr_estimate > 0 else 1.0
        
        if calorie_ratio < 0.8:
            return "deficit", "moderate"
        elif calorie_ratio < 1.0:
            return "slight_deficit", "high"
        else:
            return "adequate", "any"
    
    def _get_body_type_preferences(self, body_type: str) -> Dict[str, Any]:
        """
        获取体型偏好配置
        
        Requirements: 18.1 - 体型约束
        """
        preferences = {
            "ectomorph": {
                "preferred_mechanics": ["compound"],
                "boost_keywords": ["深蹲", "硬拉", "卧推", "划船"],
                "description": "外胚型优先复合动作，增加训练量"
            },
            "mesomorph": {
                "preferred_mechanics": ["compound", "isolation"],
                "boost_keywords": [],
                "description": "中胚型均衡推荐"
            },
            "endomorph": {
                "preferred_mechanics": ["compound"],
                "boost_keywords": ["深蹲", "硬拉", "波比跳", "登山者"],
                "description": "内胚型优先高代谢复合动作"
            }
        }
        
        return preferences.get(body_type.lower(), {
            "preferred_mechanics": ["compound", "isolation"],
            "boost_keywords": [],
            "description": "默认均衡推荐"
        })
    
    def _get_goal_preferences(self, primary_goal: str) -> Dict[str, Any]:
        """
        获取目标偏好配置
        
        Requirements: 18.4 - 目标对齐约束
        """
        goal_mapping = {
            "muscle_gain": {
                "preferred_mechanics": ["compound", "isolation"],
                "preferred_force": ["push", "pull"],
                "rep_range": (8, 12),
                "intensity_range": (0.65, 0.75),
                "rest_seconds": (60, 90)
            },
            "增肌": {
                "preferred_mechanics": ["compound", "isolation"],
                "preferred_force": ["push", "pull"],
                "rep_range": (8, 12),
                "intensity_range": (0.65, 0.75),
                "rest_seconds": (60, 90)
            },
            "fat_loss": {
                "preferred_mechanics": ["compound"],
                "preferred_force": ["push", "pull"],
                "rep_range": (12, 20),
                "intensity_range": (0.50, 0.65),
                "rest_seconds": (30, 45)
            },
            "减脂": {
                "preferred_mechanics": ["compound"],
                "preferred_force": ["push", "pull"],
                "rep_range": (12, 20),
                "intensity_range": (0.50, 0.65),
                "rest_seconds": (30, 45)
            },
            "strength": {
                "preferred_mechanics": ["compound"],
                "preferred_force": ["push", "pull"],
                "rep_range": (1, 5),
                "intensity_range": (0.85, 1.0),
                "rest_seconds": (180, 300)
            },
            "力量": {
                "preferred_mechanics": ["compound"],
                "preferred_force": ["push", "pull"],
                "rep_range": (1, 5),
                "intensity_range": (0.85, 1.0),
                "rest_seconds": (180, 300)
            },
            "rehabilitation": {
                "preferred_mechanics": ["isolation"],
                "preferred_force": ["hold"],
                "preferred_kinetic_chain": ["closed_chain"],
                "rep_range": (12, 20),
                "intensity_range": (0.30, 0.50),
                "rest_seconds": (60, 90)
            },
            "康复": {
                "preferred_mechanics": ["isolation"],
                "preferred_force": ["hold"],
                "preferred_kinetic_chain": ["closed_chain"],
                "rep_range": (12, 20),
                "intensity_range": (0.30, 0.50),
                "rest_seconds": (60, 90)
            }
        }
        
        return goal_mapping.get(primary_goal, {
            "preferred_mechanics": ["compound", "isolation"],
            "preferred_force": ["push", "pull"],
            "rep_range": (8, 15),
            "intensity_range": (0.60, 0.75),
            "rest_seconds": (60, 90)
        })
    
    def _calculate_frequency_strategy(self, training_days: int) -> str:
        """
        计算训练频率策略
        
        Requirements: 18.2 - 训练频率约束
        """
        if training_days <= 2:
            return "full_body"
        elif training_days <= 4:
            return "split"
        else:
            return "detailed_split"
    
    def _calculate_max_exercises(self, session_duration: int) -> int:
        """
        计算每次训练最大动作数
        
        Requirements: 18.3 - 训练时长约束
        """
        if session_duration < 45:
            return 5
        elif session_duration <= 75:
            return 8
        else:
            return 12
    
    # ============ 体态问题约束 ============
    
    def get_postural_issues_constraint(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取体态问题约束
        
        Requirements: 新增 - 体态矫正功能
        
        Args:
            profile: 用户档案
            
        Returns:
            Dict: 体态问题约束配置
        """
        health_profile = profile.get('health_profile', {})
        postural_issues = health_profile.get('postural_issues', [])
        
        if not postural_issues:
            return {
                "has_issues": False,
                "issues": [],
                "corrective_keywords": [],
                "aggravating_keywords": []
            }
        
        # 体态问题配置
        postural_config = {
            "骨盆前倾": {
                "corrective": ["臀桥", "死虫", "平板支撑", "腘绳肌拉伸"],
                "aggravating": ["深蹲", "硬拉", "弓步蹲"]
            },
            "骨盆后倾": {
                "corrective": ["髋屈肌拉伸", "猫牛式", "超人式"],
                "aggravating": ["卷腹", "仰卧起坐"]
            },
            "圆肩": {
                "corrective": ["面拉", "反向飞鸟", "YTWL", "胸椎伸展"],
                "aggravating": ["卧推", "俯卧撑", "前平举"]
            },
            "头前伸": {
                "corrective": ["颈部收缩", "下巴收紧", "颈部拉伸"],
                "aggravating": ["耸肩", "颈后推举"]
            },
            "驼背": {
                "corrective": ["胸椎伸展", "猫牛式", "眼镜蛇式", "面拉"],
                "aggravating": ["卷腹", "仰卧起坐", "俯身划船"]
            }
        }
        
        corrective_keywords = set()
        aggravating_keywords = set()
        
        for issue in postural_issues:
            issue_name = issue if isinstance(issue, str) else issue.get("name", "")
            if issue_name in postural_config:
                config = postural_config[issue_name]
                corrective_keywords.update(config.get("corrective", []))
                aggravating_keywords.update(config.get("aggravating", []))
        
        return {
            "has_issues": True,
            "issues": postural_issues,
            "corrective_keywords": list(corrective_keywords),
            "aggravating_keywords": list(aggravating_keywords)
        }

