# -*- coding: utf-8 -*-
"""
认证与权限模块

提供会员权限控制功能。
"""

from .membership_controller import (
    MembershipController,
    MembershipLevel,
    MembershipConfig,
    Feature,
    UsageInfo,
    PermissionCheckResult,
    create_membership_controller,
    get_membership_level_from_string,
    MEMBERSHIP_CONFIGS
)

# 重新导出ExecutionStrategy以便统一使用
from ..orchestration.strategy_selector import ExecutionStrategy

__all__ = [
    "MembershipController",
    "MembershipLevel",
    "MembershipConfig",
    "Feature",
    "UsageInfo",
    "PermissionCheckResult",
    "ExecutionStrategy",
    "create_membership_controller",
    "get_membership_level_from_string",
    "MEMBERSHIP_CONFIGS"
]
