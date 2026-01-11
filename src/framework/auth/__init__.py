# -*- coding: utf-8 -*-
"""
认证与权限模块

提供会员权限控制功能。
会员等级与PHP后端一致：free/warmheart/energy

核心组件：
- MembershipController: 会员权限控制器（本地权限检查）
- PermissionChecker: 权限检查器（与PHP后端集成）
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

from .permission_checker import (
    PermissionChecker,
    PermissionResult,
    UsageInfo as PermissionUsageInfo,
    QueryMode,
    create_permission_checker,
    get_permission_checker,
    set_permission_checker,
)

__all__ = [
    # MembershipController
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
    "MEMBERSHIP_CONFIGS",
    # PermissionChecker
    "PermissionChecker",
    "PermissionResult",
    "PermissionUsageInfo",
    "QueryMode",
    "create_permission_checker",
    "get_permission_checker",
    "set_permission_checker",
]
