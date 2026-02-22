# -*- coding: utf-8 -*-
"""
Backend API Client for Meta-Learning MCP

组合类 — 通过 Mixin 模式将方法分散到独立模块，保持 API 完全向后兼容。

拆分结构:
- models.py: 数据模型 + 枚举 + 异常类
- base_client.py: BackendConfig + HTTP 核心基础设施
- user_client.py: 用户档案 API
- credit_client.py: 会员权限 + 用量统计 API
- chat_client.py: 对话记录 API
- health_client.py: 健康检查 + 训练数据 API
"""

# Re-export models for backward compatibility
from .models import (
    MembershipTier,
    MembershipFeature,
    UserProfile,
    MembershipPermissions,
    BackendAPIError,
    BackendAuthError,
    BackendNotFoundError,
    BackendValidationError,
    BackendServerError,
)

from .base_client import BackendConfig, BackendClientBase
from .user_client import UserMixin
from .credit_client import CreditMixin
from .chat_client import ChatMixin
from .health_client import HealthMixin


class BackendClient(BackendClientBase, UserMixin, CreditMixin, ChatMixin, HealthMixin):
    """
    后端API客户端

    用于DAML-RAG Server调用yuzhen-backend的内部API。
    通过 Mixin 模式组合所有功能模块。

    使用示例:
    ```python
    client = BackendClient()
    profile = await client.get_user_profile(user_id)
    ```
    """
    pass


async def create_backend_client() -> BackendClient:
    """创建BackendClient实例（便捷函数）"""
    return BackendClient()
