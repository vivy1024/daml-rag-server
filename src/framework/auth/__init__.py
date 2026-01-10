# -*- coding: utf-8 -*-
"""
认证与权限模块

提供会员权限控制功能。
会员等级与PHP后端一致：free/warmheart/energy
"""

from .membership_controller import (
    MembershipController,
    MembershipLevel,
    MembershipConfig,
    Feature,
    ExecutionStrategy,
    UsageInfo,
    PermissionCheckResult,
    create_membership_controller,
    get_membership_level_from_string,
    get_user_membership_from_backend,
    MEMBERSHIP_CONFIGS
)

__all__ = [
    "MembershipController",
    "MembershipLevel",
    "MembershipConfig",
    "Feature",
    "ExecutionStrategy",
    "UsageInfo",
    "PermissionCheckResult",
    "create_membership_controller",
    "get_membership_level_from_string",
    "get_user_membership_from_backend",
    "MEMBERSHIP_CONFIGS"
]
