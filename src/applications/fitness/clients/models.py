# -*- coding: utf-8 -*-
"""
数据模型 + 枚举 + 异常类

从 backend_client.py 拆分，包含所有共享的数据结构。
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


# ============= 枚举 =============

class MembershipTier(str, Enum):
    """会员等级"""
    FREE = "free"
    WARMHEART = "warmheart"      # 暖心会员
    ENERGY = "energy"            # 能量会员


class MembershipFeature(str, Enum):
    """会员功能"""
    AI_RECOMMENDATION = "ai_recommendation"    # AI推荐
    DATA_ANALYSIS = "data_analysis"            # 数据分析
    COACH_SERVICE = "coach_service"            # 教练服务


# ============= 数据模型 =============

@dataclass
class UserProfile:
    """用户档案数据结构"""
    user_id: str
    basic_info: Dict[str, Any]
    nutrition_profile: Dict[str, Any]
    fitness_config: Dict[str, Any]
    fitness_goals: Dict[str, Any]
    strength_levels: Dict[str, Any]
    health_profile: Dict[str, Any]
    training_system: Dict[str, Any] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.training_system is None:
            self.training_system = {}

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'UserProfile':
        return cls(
            user_id=data.get('user_id', ''),
            basic_info=data.get('basic_info', {}),
            nutrition_profile=data.get('nutrition_profile', {}),
            fitness_config=data.get('fitness_config', {}),
            fitness_goals=data.get('fitness_goals', {}),
            strength_levels=data.get('strength_levels', {}),
            health_profile=data.get('health_profile', {}),
            training_system=data.get('training_system', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'basic_info': self.basic_info,
            'nutrition_profile': self.nutrition_profile,
            'fitness_config': self.fitness_config,
            'fitness_goals': self.fitness_goals,
            'strength_levels': self.strength_levels,
            'health_profile': self.health_profile,
            'training_system': self.training_system,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    def get_volume_multiplier(self) -> float:
        multiplier = self.training_system.get('personal_volume_multiplier', 1.0)
        return max(0.7, min(1.5, float(multiplier)))

    def get_user_type(self) -> str:
        return self.training_system.get('user_type', 'other')

    def is_student(self) -> bool:
        return self.get_user_type() == 'student'

    def is_worker(self) -> bool:
        return self.get_user_type() == 'worker'

    def __iter__(self):
        return iter(self.to_dict().items())

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()

    def __getitem__(self, key):
        return self.to_dict()[key]

    def get(self, key, default=None):
        return self.to_dict().get(key, default)


@dataclass
class MembershipPermissions:
    """会员权限数据结构"""
    user_id: int
    tier: MembershipTier
    status: str
    permissions: Dict[str, bool]
    started_at: Optional[str] = None
    expired_at: Optional[str] = None

    def get(self, key: str, default=None):
        if key == 'tier':
            return self.tier.value if hasattr(self.tier, 'value') else str(self.tier)
        elif key == 'status':
            return self.status
        elif key == 'permissions':
            return self.permissions
        elif key == 'user_id':
            return self.user_id
        elif key == 'started_at':
            return self.started_at
        elif key == 'expired_at':
            return self.expired_at
        else:
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'tier': self.tier.value if hasattr(self.tier, 'value') else str(self.tier),
            'status': self.status,
            'permissions': self.permissions,
            'started_at': self.started_at,
            'expired_at': self.expired_at
        }


# ============= 异常类 =============

class BackendAPIError(Exception):
    """后端API错误基类"""
    pass


class BackendAuthError(BackendAPIError):
    """认证错误（401）"""
    pass


class BackendNotFoundError(BackendAPIError):
    """资源未找到（404）"""
    pass


class BackendValidationError(BackendAPIError):
    """验证错误（400/422）"""
    pass


class BackendServerError(BackendAPIError):
    """服务器错误（500+）"""
    pass
