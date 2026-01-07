# -*- coding: utf-8 -*-
"""
健身应用层客户端

包含健身领域特定的客户端实现：
- BackendClient: 用于调用yuzhen-backend API
- UserProfile: 用户档案数据模型
- MembershipPermissions: 会员权限数据模型

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-13
"""

from .backend_client import (
    BackendClient,
    BackendConfig,
    UserProfile,
    MembershipPermissions,
    MembershipTier,
    MembershipFeature
)

__all__ = [
    'BackendClient',
    'BackendConfig',
    'UserProfile',
    'MembershipPermissions',
    'MembershipTier',
    'MembershipFeature'
]
