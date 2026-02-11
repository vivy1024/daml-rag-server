# -*- coding: utf-8 -*-
"""
InternalJwtVerifier - Internal JWT验证器

验证PHP后端签发的Internal JWT，提取PermissionClaims。
所有验证失败路径抛出明确异常，由上层中间件处理。

Requirements: 1.3, 1.4, 2.4
版本: v1.0.0
日期: 2026-02-12
"""

import logging
from typing import Optional

import jwt

from .permission_claims import PermissionClaims

logger = logging.getLogger(__name__)


# =============================================================================
# 异常定义
# =============================================================================

class JwtVerificationError(Exception):
    """JWT验证基础异常"""
    pass


class JwtExpiredError(JwtVerificationError):
    """JWT已过期"""
    pass


class JwtInvalidError(JwtVerificationError):
    """JWT签名无效或格式错误"""
    pass


class ClaimsMissingError(JwtVerificationError):
    """JWT缺少必要的Claims字段"""
    pass


# =============================================================================
# 验证器
# =============================================================================

class InternalJwtVerifier:
    """
    验证PHP后端签发的Internal JWT
    
    使用HS256算法验证签名，检查过期时间，提取PermissionClaims。
    """

    def __init__(
        self,
        secret_key: str,
        issuer: str = "yuzhen-auth-gateway",
        algorithms: Optional[list] = None,
    ):
        if not secret_key:
            raise ValueError("secret_key不能为空")
        self.secret_key = secret_key
        self.issuer = issuer
        self.algorithms = algorithms or ["HS256"]

    def verify(self, token: str) -> PermissionClaims:
        """
        验证JWT并返回PermissionClaims
        
        Args:
            token: JWT字符串
            
        Returns:
            PermissionClaims实例
            
        Raises:
            JwtExpiredError: JWT已过期
            JwtInvalidError: JWT签名无效或格式错误
            ClaimsMissingError: 缺少必要的Claims字段
        """
        if not token or not isinstance(token, str):
            raise JwtInvalidError("JWT令牌为空或格式错误")

        # 1. 解码并验证签名和过期时间
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=self.algorithms,
                issuer=self.issuer,
                options={
                    "require": ["sub", "tier", "permissions", "iat", "exp", "iss"],
                    "verify_sub": False,  # sub是int（PHP端签发），跳过PyJWT的字符串类型检查
                },
            )
        except jwt.ExpiredSignatureError:
            raise JwtExpiredError("Internal JWT已过期")
        except jwt.InvalidIssuerError:
            raise JwtInvalidError(f"JWT签发者不匹配，期望: {self.issuer}")
        except jwt.InvalidSignatureError:
            raise JwtInvalidError("JWT签名无效")
        except jwt.DecodeError as e:
            raise JwtInvalidError(f"JWT解码失败: {e}")
        except jwt.MissingRequiredClaimError as e:
            raise ClaimsMissingError(f"JWT缺少必要字段: {e}")
        except jwt.InvalidTokenError as e:
            raise JwtInvalidError(f"JWT无效: {e}")

        # 2. 构建PermissionClaims
        try:
            claims = PermissionClaims.from_jwt_payload(payload)
        except KeyError as e:
            raise ClaimsMissingError(str(e))
        except (ValueError, TypeError) as e:
            raise ClaimsMissingError(f"Claims字段值无效: {e}")

        return claims


__all__ = [
    "InternalJwtVerifier",
    "JwtVerificationError",
    "JwtExpiredError",
    "JwtInvalidError",
    "ClaimsMissingError",
]
