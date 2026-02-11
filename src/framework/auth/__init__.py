# -*- coding: utf-8 -*-
"""
认证与权限模块

提供会员权限控制功能。
会员等级与PHP后端一致：free/warmheart/energy

核心组件：
- MembershipController: 会员权限控制器（本地权限检查）
- PermissionChecker: 权限检查器（与PHP后端集成，旧模式）
- PermissionClaims: Internal JWT权限声明数据类
- InternalJwtVerifier: Internal JWT验证器
- FailClosedPermissionChecker: 失败关闭权限检查器
- UsageReporter: 异步用量上报客户端
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

from .permission_claims import PermissionClaims

from .internal_jwt_verifier import (
    InternalJwtVerifier,
    JwtVerificationError,
    JwtExpiredError,
    JwtInvalidError,
    ClaimsMissingError,
)

from .fail_closed_checker import FailClosedPermissionChecker

from .usage_reporter import UsageReporter, UsageReportTask

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
    # PermissionChecker (旧模式)
    "PermissionChecker",
    "PermissionResult",
    "PermissionUsageInfo",
    "QueryMode",
    "create_permission_checker",
    "get_permission_checker",
    "set_permission_checker",
    # PermissionClaims (新模式)
    "PermissionClaims",
    # InternalJwtVerifier
    "InternalJwtVerifier",
    "JwtVerificationError",
    "JwtExpiredError",
    "JwtInvalidError",
    "ClaimsMissingError",
    # FailClosedPermissionChecker
    "FailClosedPermissionChecker",
    # UsageReporter
    "UsageReporter",
    "UsageReportTask",
]
