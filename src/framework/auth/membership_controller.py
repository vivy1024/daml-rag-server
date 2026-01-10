# -*- coding: utf-8 -*-
"""
会员权限控制器 - 双策略架构权限管理

根据会员等级控制可用的执行策略和功能。

核心功能：
1. 会员等级定义（普通用户/普通会员/能量会员）
2. 策略权限控制
3. 每日使用限制
4. 功能特性控制

Requirements: 8.6

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举定义
# =============================================================================

class MembershipLevel(Enum):
    """
    会员等级枚举
    
    三个等级：
    - FREE: 普通用户（未付费）
    - BASIC: 普通会员（基础付费）
    - PREMIUM: 能量会员（高级付费）
    """
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"


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
        allowed_strategies: 允许的执行策略列表
        daily_limit: 每日使用限制（-1表示无限制）
        features: 可用功能列表
        max_context_length: 最大上下文长度
        priority: 请求优先级（数字越大优先级越高）
    """
    level: MembershipLevel
    allowed_strategies: List[ExecutionStrategy]
    daily_limit: int
    features: List[Feature]
    max_context_length: int = 2000
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "level": self.level.value,
            "allowed_strategies": [s.value for s in self.allowed_strategies],
            "daily_limit": self.daily_limit,
            "features": [f.value for f in self.features],
            "max_context_length": self.max_context_length,
            "priority": self.priority
        }


@dataclass
class UsageInfo:
    """
    使用信息
    
    Attributes:
        allowed: 是否允许继续使用
        remaining: 剩余次数（-1表示无限制）
        limit: 每日限制
        used: 已使用次数
        reset_time: 重置时间
    """
    allowed: bool
    remaining: int
    limit: int
    used: int = 0
    reset_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "limit": self.limit,
            "used": self.used,
            "reset_time": self.reset_time
        }


@dataclass
class PermissionCheckResult:
    """
    权限检查结果
    
    Attributes:
        allowed: 是否允许
        reason: 原因说明
        upgrade_hint: 升级提示（如果不允许）
    """
    allowed: bool
    reason: str
    upgrade_hint: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "upgrade_hint": self.upgrade_hint
        }


# =============================================================================
# 会员配置表
# =============================================================================

MEMBERSHIP_CONFIGS: Dict[MembershipLevel, MembershipConfig] = {
    MembershipLevel.FREE: MembershipConfig(
        level=MembershipLevel.FREE,
        allowed_strategies=[ExecutionStrategy.DAG],
        daily_limit=10,
        features=[
            Feature.BASIC_TRAINING,
            Feature.BASIC_NUTRITION
        ],
        max_context_length=1000,
        priority=0
    ),
    MembershipLevel.BASIC: MembershipConfig(
        level=MembershipLevel.BASIC,
        allowed_strategies=[ExecutionStrategy.DAG],
        daily_limit=100,
        features=[
            Feature.BASIC_TRAINING,
            Feature.BASIC_NUTRITION,
            Feature.HISTORY,
            Feature.CUSTOM_PLANS
        ],
        max_context_length=2000,
        priority=1
    ),
    MembershipLevel.PREMIUM: MembershipConfig(
        level=MembershipLevel.PREMIUM,
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
    
    核心功能：
    1. 获取会员配置
    2. 检查策略权限
    3. 检查每日使用限制
    4. 检查功能权限
    
    使用示例:
    ```python
    from src.framework.auth.membership_controller import MembershipController
    
    # 创建控制器
    controller = MembershipController(redis_client=redis)
    
    # 检查策略权限
    result = controller.can_use_strategy(
        user_level=MembershipLevel.FREE,
        strategy=ExecutionStrategy.AGENT
    )
    print(f"允许: {result.allowed}, 原因: {result.reason}")
    
    # 检查每日限制
    usage = await controller.check_daily_limit(
        user_id="user_123",
        user_level=MembershipLevel.FREE
    )
    print(f"剩余: {usage.remaining}")
    ```
    
    Requirements: 8.6
    """
    
    def __init__(self, redis_client=None):
        """
        初始化会员权限控制器
        
        Args:
            redis_client: Redis客户端（用于存储使用次数）
        """
        self.redis_client = redis_client
        self._usage_cache: Dict[str, int] = {}  # 内存缓存（Redis不可用时使用）
        
        logger.info(
            f"✅ MembershipController初始化完成: "
            f"Redis={'已连接' if redis_client else '未连接'}"
        )
    
    def get_config(self, level: MembershipLevel) -> MembershipConfig:
        """
        获取会员配置
        
        Args:
            level: 会员等级
        
        Returns:
            MembershipConfig: 会员配置
        """
        return MEMBERSHIP_CONFIGS.get(level, MEMBERSHIP_CONFIGS[MembershipLevel.FREE])
    
    def can_use_strategy(
        self,
        user_level: MembershipLevel,
        strategy: ExecutionStrategy
    ) -> PermissionCheckResult:
        """
        检查用户是否可以使用指定策略
        
        Args:
            user_level: 用户会员等级
            strategy: 要使用的策略
        
        Returns:
            PermissionCheckResult: 权限检查结果
        """
        config = self.get_config(user_level)
        
        if strategy in config.allowed_strategies:
            return PermissionCheckResult(
                allowed=True,
                reason=f"{user_level.value}会员可以使用{strategy.value}策略"
            )
        
        # 不允许，提供升级提示
        if strategy == ExecutionStrategy.AGENT:
            return PermissionCheckResult(
                allowed=False,
                reason=f"{user_level.value}会员不支持Agent模式",
                upgrade_hint="升级到能量会员可解锁Agent模式，享受更智能的AI助手"
            )
        
        return PermissionCheckResult(
            allowed=False,
            reason=f"{user_level.value}会员不支持{strategy.value}策略"
        )
    
    def can_use_feature(
        self,
        user_level: MembershipLevel,
        feature: Feature
    ) -> PermissionCheckResult:
        """
        检查用户是否可以使用指定功能
        
        Args:
            user_level: 用户会员等级
            feature: 要使用的功能
        
        Returns:
            PermissionCheckResult: 权限检查结果
        """
        config = self.get_config(user_level)
        
        if feature in config.features:
            return PermissionCheckResult(
                allowed=True,
                reason=f"{user_level.value}会员可以使用{feature.value}功能"
            )
        
        # 不允许，提供升级提示
        upgrade_hints = {
            Feature.AGENT_MODE: "升级到能量会员可解锁Agent模式",
            Feature.HISTORY: "升级到普通会员可查看历史记录",
            Feature.ADVANCED_ANALYTICS: "升级到能量会员可使用高级分析",
            Feature.EXPORT_DATA: "升级到能量会员可导出数据",
            Feature.PRIORITY_SUPPORT: "升级到能量会员可享受优先支持"
        }
        
        return PermissionCheckResult(
            allowed=False,
            reason=f"{user_level.value}会员不支持{feature.value}功能",
            upgrade_hint=upgrade_hints.get(feature, "升级会员可解锁更多功能")
        )
    
    async def check_daily_limit(
        self,
        user_id: str,
        user_level: MembershipLevel
    ) -> UsageInfo:
        """
        检查每日使用限制
        
        Args:
            user_id: 用户ID
            user_level: 用户会员等级
        
        Returns:
            UsageInfo: 使用信息
        """
        config = self.get_config(user_level)
        
        # 无限制
        if config.daily_limit == -1:
            return UsageInfo(
                allowed=True,
                remaining=-1,
                limit=-1,
                used=0
            )
        
        # 获取今日使用次数
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"usage:{user_id}:{today}"
        
        usage = await self._get_usage(key)
        remaining = config.daily_limit - usage
        
        # 计算重置时间（明天0点）
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
        """
        增加使用次数
        
        Args:
            user_id: 用户ID
        
        Returns:
            当前使用次数
        """
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"usage:{user_id}:{today}"
        
        return await self._increment_usage(key)
    
    async def _get_usage(self, key: str) -> int:
        """获取使用次数"""
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                return int(value) if value else 0
            except Exception as e:
                logger.warning(f"Redis获取失败: {e}, 使用内存缓存")
        
        return self._usage_cache.get(key, 0)
    
    async def _increment_usage(self, key: str) -> int:
        """增加使用次数"""
        if self.redis_client:
            try:
                new_value = await self.redis_client.incr(key)
                await self.redis_client.expire(key, 86400)  # 24小时过期
                return new_value
            except Exception as e:
                logger.warning(f"Redis增加失败: {e}, 使用内存缓存")
        
        self._usage_cache[key] = self._usage_cache.get(key, 0) + 1
        return self._usage_cache[key]
    
    def get_level_comparison(self) -> List[Dict[str, Any]]:
        """
        获取会员等级对比信息
        
        Returns:
            会员等级对比列表
        """
        comparison = []
        for level, config in MEMBERSHIP_CONFIGS.items():
            comparison.append({
                "level": level.value,
                "level_name": {
                    MembershipLevel.FREE: "普通用户",
                    MembershipLevel.BASIC: "普通会员",
                    MembershipLevel.PREMIUM: "能量会员"
                }.get(level, level.value),
                "daily_limit": config.daily_limit if config.daily_limit > 0 else "无限制",
                "strategies": [s.value for s in config.allowed_strategies],
                "features": [f.value for f in config.features],
                "max_context_length": config.max_context_length,
                "priority": config.priority
            })
        return comparison


# =============================================================================
# 工厂函数
# =============================================================================

def create_membership_controller(redis_client=None) -> MembershipController:
    """
    创建会员权限控制器实例
    
    Args:
        redis_client: Redis客户端
    
    Returns:
        MembershipController: 会员权限控制器实例
    """
    return MembershipController(redis_client=redis_client)


def get_membership_level_from_string(level_str: str) -> MembershipLevel:
    """
    从字符串获取会员等级
    
    Args:
        level_str: 等级字符串
    
    Returns:
        MembershipLevel: 会员等级
    """
    level_map = {
        "free": MembershipLevel.FREE,
        "basic": MembershipLevel.BASIC,
        "premium": MembershipLevel.PREMIUM,
        "普通用户": MembershipLevel.FREE,
        "普通会员": MembershipLevel.BASIC,
        "能量会员": MembershipLevel.PREMIUM
    }
    return level_map.get(level_str.lower(), MembershipLevel.FREE)
