# -*- coding: utf-8 -*-
"""
PermissionClaims - Internal JWT权限声明数据类

从PHP后端签发的Internal JWT中提取的权限声明。
用于DAML-RAG端的用户身份识别和权限检查。

核心功能：
1. PermissionClaims dataclass - 权限声明数据结构
2. from_jwt_payload() - 从JWT payload反序列化
3. to_dict() - 序列化为字典

Requirements: 5.1, 5.2, 5.3, 5.4
版本: v1.0.0
日期: 2026-02-12
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any


@dataclass
class PermissionClaims:
    """
    从Internal JWT中提取的权限声明
    
    Attributes:
        user_id: 用户ID (JWT sub字段)
        tier: 会员等级 (free|warmheart|energy)
        permissions: 权限列表
        daily_dag_limit: DAG每日限制
        daily_agent_limit: Agent每日限制
        issued_at: 签发时间
        expires_at: 过期时间
    """
    user_id: int
    tier: str
    permissions: List[str]
    daily_dag_limit: int
    daily_agent_limit: int
    issued_at: datetime
    expires_at: datetime

    @classmethod
    def from_jwt_payload(cls, payload: Dict[str, Any]) -> "PermissionClaims":
        """
        从JWT payload字典构建PermissionClaims
        
        Args:
            payload: JWT解码后的payload字典
            
        Returns:
            PermissionClaims实例
            
        Raises:
            KeyError: 缺少必要字段
            ValueError: 字段值无效
        """
        required_fields = ["sub", "tier", "permissions", "daily_dag_limit",
                           "daily_agent_limit", "iat", "exp"]
        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise KeyError(f"JWT payload缺少必要字段: {', '.join(missing)}")

        user_id = int(payload["sub"])
        tier = str(payload["tier"])
        permissions = list(payload["permissions"])
        daily_dag_limit = int(payload["daily_dag_limit"])
        daily_agent_limit = int(payload["daily_agent_limit"])
        issued_at = datetime.fromtimestamp(int(payload["iat"]))
        expires_at = datetime.fromtimestamp(int(payload["exp"]))

        return cls(
            user_id=user_id,
            tier=tier,
            permissions=permissions,
            daily_dag_limit=daily_dag_limit,
            daily_agent_limit=daily_agent_limit,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        序列化为JWT payload格式的字典
        
        Returns:
            与JWT payload兼容的字典
        """
        return {
            "sub": self.user_id,
            "tier": self.tier,
            "permissions": list(self.permissions),
            "daily_dag_limit": self.daily_dag_limit,
            "daily_agent_limit": self.daily_agent_limit,
            "iat": int(self.issued_at.timestamp()),
            "exp": int(self.expires_at.timestamp()),
        }

    def has_permission(self, permission: str) -> bool:
        """检查是否拥有指定权限"""
        return permission in self.permissions

    def is_expired(self) -> bool:
        """检查Claims是否已过期"""
        return datetime.now() > self.expires_at


__all__ = ["PermissionClaims"]
