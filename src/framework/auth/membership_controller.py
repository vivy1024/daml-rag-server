# -*- coding: utf-8 -*-
"""
会员权限控制器 - 双策略架构权限管理

根据会员等级控制可用的执行策略和功能。

会员等级（与PHP后端一致）：
- free: 免费用户
- warmheart: 暖心会员
- energy: 能量会员

核心功能：
1. 会员等级定义
2. 策略权限控制
3. 每日使用限制
4. 功能特性控制
5. Feature Flag支持（USE_MEMBERSHIP_CONTROL）

Requirements: 8.6

版本: v2.0.0
日期: 2026-01-11
作者: 薛小川
"""

import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Feature Flag
# =============================================================================

def _is_membership_control_enabled() -> bool:
    """
    检查是否启用会员权限控制
    
    通过环境变量 USE_MEMBERSHIP_CONTROL 控制：
    - false/0/no（默认）: 禁用会员控制，所有用户享有energy权限
    - true/1/yes: 启用会员控制，按实际等级限制
    
    Returns:
        bool: 是否启用会员控制
    """
    enabled = os.getenv('USE_MEMBERSHIP_CONTROL', 'false').lower() in ('true', '1', 'yes')
    return enabled


# =============================================================================
# 枚举定义（与PHP后端一致）
# =============================================================================

class MembershipLevel(Enum):
    """
    会员等级枚举（与PHP后端一致）
    
    三个等级：
    - FREE: 免费用户
    - WARMHEART: 暖心会员
    - ENERGY: 能量会员
    """
    FREE = "free"
    WARMHEART = "warmheart"
    ENERGY = "energy"


class ExecutionStrategy(Enum):
    """执行策略枚举"""
    DAG = "dag"
    AGENT = "agent"


class Feature(Enum):
    """功能特性枚举"""
    BASIC_TRAINING = "basic_training"       # 基础训练建议
    BASIC_NUTRITION = "basic_nutrition"     # 基础营养建议
    HISTORY = "history"                     # 历史记录
    AGENT_MODE = "agent_mode"               # Agent模式
    PRIORITY_SUPPORT = "priority_support"   # 优先支持
    ADVANCED_ANALYTICS = "advanced_analytics"  # 高级分析
    CUSTOM_PLANS = "custom_plans"           # 自定义计划
    EXPORT_DATA = "export_data"             # 数据导出


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class MembershipConfig:
    """
    会员配置
    
    Attributes:
        level: 会员等级
        display_name: 显示名称
        allowed_strategies: 允许的执行策略列表
        daily_limit: 每日使用限制（-1表示无限制）
        features: 可用功能列表
        max_context_length: 最大上下文长度
        priority: 请求优先级（数字越大优先级越高）
    """
    level: MembershipLevel
    display_name: str
    allowed_strategies: List[ExecutionStrategy]
    daily_limit: int
    features: List[Feature]
    max_context_length: int = 2000
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "level": self.level.value,
            "display_name": self.display_name,
            "allowed_strategies": [s.value for s in self.allowed_strategies],
            "daily_limit": self.daily_limit,
            "features": [f.value for f in self.features],
            "max_context_length": self.max_context_length,
            "priority": self.priority
        }


@dataclass
class UsageInfo:
    """使用信息"""
    allowed: bool
    remaining: int
    limit: int
    used: int = 0
    reset_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "limit": self.limit,
            "used": self.used,
            "reset_time": self.reset_time
        }


@dataclass
class PermissionCheckResult:
    """权限检查结果"""
    allowed: bool
    reason: str
    upgrade_hint: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "upgrade_hint": self.upgrade_hint
        }


# =============================================================================
# 会员配置表（与PHP后端一致）
# =============================================================================

MEMBERSHIP_CONFIGS: Dict[MembershipLevel, MembershipConfig] = {
    MembershipLevel.FREE: MembershipConfig(
        level=MembershipLevel.FREE,
        display_name="免费用户",
        allowed_strategies=[ExecutionStrategy.DAG],
        daily_limit=5,
        features=[
            Feature.BASIC_TRAINING,
            Feature.BASIC_NUTRITION
        ],
        max_context_length=1000,
        priority=0
    ),
    MembershipLevel.WARMHEART: MembershipConfig(
        level=MembershipLevel.WARMHEART,
        display_name="暖心会员",
        allowed_strategies=[ExecutionStrategy.DAG],
        daily_limit=30,
        features=[
            Feature.BASIC_TRAINING,
            Feature.BASIC_NUTRITION,
            Feature.HISTORY,
            Feature.CUSTOM_PLANS
        ],
        max_context_length=2000,
        priority=1
    ),
    MembershipLevel.ENERGY: MembershipConfig(
        level=MembershipLevel.ENERGY,
        display_name="能量会员",
        allowed_strategies=[ExecutionStrategy.DAG, ExecutionStrategy.AGENT],
        daily_limit=-1,  # 无限制
        features=[
            Feature.BASIC_TRAINING,
            Feature.BASIC_NUTRITION,
            Feature.HISTORY,
            Feature.AGENT_MODE,
            Feature.PRIORITY_SUPPORT,
            Feature.ADVANCED_ANALYTICS,
            Feature.CUSTOM_PLANS,
            Feature.EXPORT_DATA
        ],
        max_context_length=4000,
        priority=2
    ),
}


# =============================================================================
# 会员权限控制器
# =============================================================================

class MembershipController:
    """
    会员权限控制器
    
    Feature Flag说明：
    - USE_MEMBERSHIP_CONTROL=false（默认）: 禁用会员控制，所有用户享有energy权限
    - USE_MEMBERSHIP_CONTROL=true: 启用会员控制，按实际等级限制
    
    Requirements: 8.6
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self._usage_cache: Dict[str, int] = {}
        self._membership_control_enabled = _is_membership_control_enabled()
        
        logger.info(
            f"✅ MembershipController初始化完成: "
            f"Redis={'已连接' if redis_client else '未连接'}, "
            f"会员控制={'启用' if self._membership_control_enabled else '禁用（所有用户享有energy权限）'}"
        )
    
    def get_config(self, level: MembershipLevel) -> MembershipConfig:
        """获取会员配置"""
        if not self._membership_control_enabled:
            return MEMBERSHIP_CONFIGS[MembershipLevel.ENERGY]
        return MEMBERSHIP_CONFIGS.get(level, MEMBERSHIP_CONFIGS[MembershipLevel.FREE])
    
    def is_membership_control_enabled(self) -> bool:
        """检查会员控制是否启用"""
        return self._membership_control_enabled
    
    def can_use_strategy(
        self,
        user_level: MembershipLevel,
        strategy: ExecutionStrategy
    ) -> PermissionCheckResult:
        """检查用户是否可以使用指定策略"""
        if not self._membership_control_enabled:
            return PermissionCheckResult(
                allowed=True,
                reason="会员控制已禁用，所有策略可用"
            )
        
        config = self.get_config(user_level)
        
        if strategy in config.allowed_strategies:
            return PermissionCheckResult(
                allowed=True,
                reason=f"{config.display_name}可以使用{strategy.value}策略"
            )
        
        if strategy == ExecutionStrategy.AGENT:
            return PermissionCheckResult(
                allowed=False,
                reason=f"{config.display_name}不支持Agent模式",
                upgrade_hint="升级到能量会员可解锁Agent模式"
            )
        
        return PermissionCheckResult(
            allowed=False,
            reason=f"{config.display_name}不支持{strategy.value}策略"
        )
    
    def can_use_feature(
        self,
        user_level: MembershipLevel,
        feature: Feature
    ) -> PermissionCheckResult:
        """检查用户是否可以使用指定功能"""
        if not self._membership_control_enabled:
            return PermissionCheckResult(
                allowed=True,
                reason="会员控制已禁用，所有功能可用"
            )
        
        config = self.get_config(user_level)
        
        if feature in config.features:
            return PermissionCheckResult(
                allowed=True,
                reason=f"{config.display_name}可以使用{feature.value}功能"
            )
        
        upgrade_hints = {
            Feature.AGENT_MODE: "升级到能量会员可解锁Agent模式",
            Feature.HISTORY: "升级到暖心会员可查看历史记录",
            Feature.ADVANCED_ANALYTICS: "升级到能量会员可使用高级分析",
            Feature.EXPORT_DATA: "升级到能量会员可导出数据",
            Feature.PRIORITY_SUPPORT: "升级到能量会员可享受优先支持"
        }
        
        return PermissionCheckResult(
            allowed=False,
            reason=f"{config.display_name}不支持{feature.value}功能",
            upgrade_hint=upgrade_hints.get(feature, "升级会员可解锁更多功能")
        )
    
    async def check_daily_limit(
        self,
        user_id: str,
        user_level: MembershipLevel
    ) -> UsageInfo:
        """检查每日使用限制"""
        if not self._membership_control_enabled:
            return UsageInfo(allowed=True, remaining=-1, limit=-1, used=0)
        
        config = self.get_config(user_level)
        
        if config.daily_limit == -1:
            return UsageInfo(allowed=True, remaining=-1, limit=-1, used=0)
        
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"usage:{user_id}:{today}"
        
        usage = await self._get_usage(key)
        remaining = config.daily_limit - usage
        
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = tomorrow.replace(day=tomorrow.day + 1)
        reset_time = tomorrow.strftime('%Y-%m-%d %H:%M:%S')
        
        return UsageInfo(
            allowed=remaining > 0,
            remaining=max(0, remaining),
            limit=config.daily_limit,
            used=usage,
            reset_time=reset_time
        )
    
    async def increment_usage(self, user_id: str) -> int:
        """增加使用次数"""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"usage:{user_id}:{today}"
        return await self._increment_usage(key)
    
    async def _get_usage(self, key: str) -> int:
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                return int(value) if value else 0
            except Exception as e:
                logger.warning(f"Redis获取失败: {e}")
        return self._usage_cache.get(key, 0)
    
    async def _increment_usage(self, key: str) -> int:
        if self.redis_client:
            try:
                new_value = await self.redis_client.incr(key)
                await self.redis_client.expire(key, 86400)
                return new_value
            except Exception as e:
                logger.warning(f"Redis增加失败: {e}")
        self._usage_cache[key] = self._usage_cache.get(key, 0) + 1
        return self._usage_cache[key]
    
    def get_level_comparison(self) -> List[Dict[str, Any]]:
        """获取会员等级对比信息"""
        return [config.to_dict() for config in MEMBERSHIP_CONFIGS.values()]


# =============================================================================
# 工厂函数
# =============================================================================

def create_membership_controller(redis_client=None) -> MembershipController:
    """创建会员权限控制器实例"""
    return MembershipController(redis_client=redis_client)


def get_membership_level_from_string(level_str: str) -> MembershipLevel:
    """
    从字符串获取会员等级
    
    Args:
        level_str: 等级字符串（free/warmheart/energy）
    
    Returns:
        MembershipLevel: 会员等级
    """
    level_map = {
        "free": MembershipLevel.FREE,
        "warmheart": MembershipLevel.WARMHEART,
        "energy": MembershipLevel.ENERGY,
    }
    return level_map.get(level_str.lower() if level_str else "free", MembershipLevel.FREE)


# =============================================================================
# PHP后端集成
# =============================================================================

async def get_user_membership_from_backend(backend_client, user_id: int) -> MembershipLevel:
    """
    从PHP后端获取用户会员等级
    
    Args:
        backend_client: BackendClient实例
        user_id: 用户ID
    
    Returns:
        MembershipLevel: 会员等级
    """
    try:
        membership = await backend_client.get_user_membership(user_id)
        tier_str = membership.get('tier', 'free') if isinstance(membership, dict) else getattr(membership, 'tier', 'free')
        if hasattr(tier_str, 'value'):
            tier_str = tier_str.value
        
        level = get_membership_level_from_string(str(tier_str))
        logger.info(f"✅ 从PHP后端获取会员等级: user_id={user_id}, tier={tier_str}")
        return level
        
    except Exception as e:
        logger.warning(f"⚠️ 获取会员等级失败，使用默认FREE: user_id={user_id}, error={e}")
        return MembershipLevel.FREE
