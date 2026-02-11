# -*- coding: utf-8 -*-
"""
FailClosedPermissionChecker - 失败关闭权限检查器

所有异常路径默认拒绝访问（fail-closed）。
权限信息从传入的PermissionClaims获取，不再调用后端API。

Requirements: 1.1, 1.2, 1.5
版本: v1.0.0
日期: 2026-02-12
"""

import logging
from typing import Optional

from .permission_claims import PermissionClaims
from .permission_checker import PermissionResult

logger = logging.getLogger(__name__)

# 审计日志使用独立logger
audit_logger = logging.getLogger("audit.permission")


class FailClosedPermissionChecker:
    """
    失败关闭的权限检查器
    
    所有异常路径默认拒绝访问。
    权限信息直接从PermissionClaims获取，无需调用后端API。
    """

    def check_permission(
        self,
        claims: Optional[PermissionClaims],
        required_permission: str,
        request_ip: str = "unknown",
        request_path: str = "unknown",
    ) -> PermissionResult:
        """
        检查权限 - 失败关闭模式
        
        任何异常都返回 allowed=False
        
        Args:
            claims: 从Internal JWT提取的权限声明，None表示无认证信息
            required_permission: 需要的权限字符串
            request_ip: 请求来源IP（审计日志用）
            request_path: 请求路径（审计日志用）
            
        Returns:
            PermissionResult
        """
        try:
            # 无Claims → 拒绝
            if claims is None:
                audit_logger.warning(
                    "[AUDIT] 权限检查失败: 无认证信息",
                    extra={
                        "audit_type": "permission_denied",
                        "reason": "no_claims",
                        "request_ip": request_ip,
                        "request_path": request_path,
                    },
                )
                return PermissionResult(
                    allowed=False,
                    tier="unknown",
                    remaining=0,
                    message="无认证信息，拒绝访问",
                )

            # Claims已过期 → 拒绝
            if claims.is_expired():
                audit_logger.warning(
                    "[AUDIT] 权限检查失败: Claims已过期",
                    extra={
                        "audit_type": "permission_denied",
                        "reason": "claims_expired",
                        "user_id": claims.user_id,
                        "request_ip": request_ip,
                        "request_path": request_path,
                    },
                )
                return PermissionResult(
                    allowed=False,
                    tier=claims.tier,
                    remaining=0,
                    message="认证信息已过期",
                )

            # 检查权限
            if not claims.has_permission(required_permission):
                audit_logger.warning(
                    "[AUDIT] 权限检查失败: 权限不足",
                    extra={
                        "audit_type": "permission_denied",
                        "reason": "insufficient_permission",
                        "user_id": claims.user_id,
                        "tier": claims.tier,
                        "required": required_permission,
                        "request_ip": request_ip,
                        "request_path": request_path,
                    },
                )
                upgrade_hint = None
                if claims.tier == "free":
                    upgrade_hint = "升级会员可获得更多权限"
                return PermissionResult(
                    allowed=False,
                    tier=claims.tier,
                    remaining=0,
                    message=f"权限不足: 需要 {required_permission}",
                    upgrade_hint=upgrade_hint,
                )

            # 权限通过
            remaining = (
                claims.daily_dag_limit
                if required_permission.startswith("dag:")
                else claims.daily_agent_limit
            )

            return PermissionResult(
                allowed=True,
                tier=claims.tier,
                remaining=remaining,
                message="权限检查通过",
            )

        except Exception as e:
            # fail-closed: 任何异常都拒绝
            audit_logger.error(
                f"[AUDIT] 权限检查异常: {e}",
                extra={
                    "audit_type": "permission_error",
                    "reason": "internal_exception",
                    "error": str(e),
                    "request_ip": request_ip,
                    "request_path": request_path,
                },
            )
            return PermissionResult(
                allowed=False,
                tier="unknown",
                remaining=0,
                message="权限检查异常，拒绝访问",
            )


__all__ = ["FailClosedPermissionChecker"]
