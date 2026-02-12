# -*- coding: utf-8 -*-
"""
DualAuthMiddleware - 双认证中间件

迁移期支持两种认证方式：
1. Internal JWT（优先）- 新模式
2. X-Internal-Token（降级）- 旧模式

Requirements: 7.1, 7.2
版本: v1.0.0
日期: 2026-02-12
"""

import logging
import os
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...framework.auth.internal_jwt_verifier import (
    InternalJwtVerifier,
    JwtExpiredError,
    JwtInvalidError,
    ClaimsMissingError,
)
from ...framework.auth.permission_claims import PermissionClaims

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit.auth")

# 不需要认证的路径
PUBLIC_PATHS = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/api/health",
    "/health/components",
    "/health/metrics",
    "/",
]


class DualAuthMiddleware(BaseHTTPMiddleware):
    """
    双认证中间件 - 迁移期支持两种认证方式
    
    优先使用Internal JWT，降级到X-Internal-Token。
    """

    def __init__(
        self,
        app,
        jwt_verifier: Optional[InternalJwtVerifier] = None,
        legacy_token: Optional[str] = None,
        legacy_auth_enabled: bool = True,
    ):
        super().__init__(app)
        self.jwt_verifier = jwt_verifier
        self.legacy_token = legacy_token or os.getenv("INTERNAL_API_TOKEN", "")
        self.legacy_auth_enabled = legacy_auth_enabled

    def _is_public_path(self, path: str) -> bool:
        """检查是否是公开路径"""
        for public_path in PUBLIC_PATHS:
            if public_path == "/":
                if path == "/":
                    return True
                continue
            if path.startswith(public_path):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        """认证流程"""
        # 公开路径跳过认证
        if self._is_public_path(request.url.path):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        # 1. 尝试Internal JWT认证
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and self.jwt_verifier:
            token = auth_header[7:]
            try:
                claims = self.jwt_verifier.verify(token)
                # JWT认证成功，存入request.state
                request.state.auth_mode = "internal_jwt"
                request.state.permission_claims = claims
                request.state.user_id = claims.user_id
                logger.debug(
                    f"JWT认证成功: user_id={claims.user_id}, tier={claims.tier}"
                )
                return await call_next(request)

            except JwtExpiredError:
                audit_logger.warning(
                    "[AUDIT] JWT验证失败: 已过期",
                    extra={
                        "audit_type": "jwt_verification_failed",
                        "failure_type": "expired",
                        "request_ip": client_ip,
                        "request_path": request.url.path,
                    },
                )
                return JSONResponse(
                    status_code=401,
                    content={"code": 401, "msg": "Internal JWT已过期", "data": None},
                )

            except JwtInvalidError as e:
                audit_logger.warning(
                    f"[AUDIT] JWT验证失败: 签名/格式无效 - {e}",
                    extra={
                        "audit_type": "jwt_verification_failed",
                        "failure_type": "invalid",
                        "request_ip": client_ip,
                        "request_path": request.url.path,
                    },
                )
                # 迁移期：JWT无效时降级到X-Internal-Token（可能是外部JWT误传）
                logger.info(
                    f"JWT验证失败，尝试降级到X-Internal-Token: {e}"
                )

            except ClaimsMissingError as e:
                audit_logger.warning(
                    f"[AUDIT] JWT验证失败: 缺少Claims - {e}",
                    extra={
                        "audit_type": "jwt_verification_failed",
                        "failure_type": "claims_missing",
                        "request_ip": client_ip,
                        "request_path": request.url.path,
                    },
                )
                return JSONResponse(
                    status_code=403,
                    content={"code": 403, "msg": f"JWT缺少必要字段: {e}", "data": None},
                )

        # 2. 降级到X-Internal-Token认证
        internal_token = request.headers.get("X-Internal-Token", "")
        if internal_token and self.legacy_auth_enabled:
            if self.legacy_token and internal_token == self.legacy_token:
                # 旧模式认证成功，从请求体提取user_id
                request.state.auth_mode = "legacy_token"
                request.state.permission_claims = None
                # user_id将由路由从请求体中提取
                logger.debug("X-Internal-Token认证成功（旧模式）")
                return await call_next(request)
            else:
                audit_logger.warning(
                    "[AUDIT] X-Internal-Token验证失败",
                    extra={
                        "audit_type": "legacy_token_failed",
                        "request_ip": client_ip,
                        "request_path": request.url.path,
                    },
                )
                return JSONResponse(
                    status_code=401,
                    content={"code": 401, "msg": "X-Internal-Token无效", "data": None},
                )

        # 3. 无认证信息
        audit_logger.warning(
            "[AUDIT] 无认证信息",
            extra={
                "audit_type": "no_auth",
                "request_ip": client_ip,
                "request_path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=401,
            content={"code": 401, "msg": "缺少认证信息", "data": None},
        )


__all__ = ["DualAuthMiddleware"]
