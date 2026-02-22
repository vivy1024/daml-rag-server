# -*- coding: utf-8 -*-
"""
健身应用层客户端

包含健身领域特定的客户端实现：
- BackendClient: 用于调用yuzhen-backend API
- UserProfile: 用户档案数据模型
- MembershipPermissions: 会员权限数据模型
"""

from .models import (
    UserProfile,
    MembershipPermissions,
    MembershipTier,
    MembershipFeature,
    BackendAPIError,
    BackendAuthError,
    BackendNotFoundError,
    BackendValidationError,
    BackendServerError,
)

from .base_client import BackendConfig
from .backend_client import BackendClient

__all__ = [
    'BackendClient',
    'BackendConfig',
    'UserProfile',
    'MembershipPermissions',
    'MembershipTier',
    'MembershipFeature',
    'BackendAPIError',
    'BackendAuthError',
    'BackendNotFoundError',
    'BackendValidationError',
    'BackendServerError',
]
