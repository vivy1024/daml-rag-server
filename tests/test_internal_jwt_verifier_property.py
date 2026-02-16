# -*- coding: utf-8 -*-
"""
InternalJwtVerifier属性测试

验证Internal JWT验证器的关键属性：
- Property 2: 无效JWT全部拒绝并返回正确错误码

使用pytest参数化测试覆盖各种无效JWT场景。

版本: v1.0.0
日期: 2026-02-16
Requirements: 1.3, 1.4
"""

import time
from datetime import datetime, timedelta

import jwt
import pytest

from src.framework.auth.internal_jwt_verifier import (
    ClaimsMissingError,
    InternalJwtVerifier,
    JwtExpiredError,
    JwtInvalidError,
)
from src.framework.auth.permission_claims import PermissionClaims


# =============================================================================
# 测试配置
# =============================================================================

TEST_SECRET = "test-internal-jwt-secret-32chars-minimum-length"
TEST_ISSUER = "yuzhen-auth-gateway"
WRONG_SECRET = "wrong-secret-key-for-testing-32chars-minimum"


# =============================================================================
# 辅助函数
# =============================================================================

def create_valid_jwt(
    user_id: int = 1,
    tier: str = "free",
    permissions: list = None,
    ttl_seconds: int = 60,
    secret: str = TEST_SECRET,
    issuer: str = TEST_ISSUER,
) -> str:
    """创建有效的Internal JWT"""
    if permissions is None:
        permissions = ["dag:query", "profile:read"]

    now = int(time.time())
    payload = {
        "sub": user_id,
        "tier": tier,
        "permissions": permissions,
        "daily_dag_limit": 5,
        "daily_agent_limit": 0,
        "iat": now,
        "exp": now + ttl_seconds,
        "iss": issuer,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_expired_jwt() -> str:
    """创建已过期的JWT"""
    now = int(time.time())
    payload = {
        "sub": 1,
        "tier": "free",
        "permissions": ["dag:query"],
        "daily_dag_limit": 5,
        "daily_agent_limit": 0,
        "iat": now - 120,  # 2分钟前签发
        "exp": now - 60,   # 1分钟前过期
        "iss": TEST_ISSUER,
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


def create_jwt_missing_field(missing_field: str) -> str:
    """创建缺少指定字段的JWT"""
    now = int(time.time())
    payload = {
        "sub": 1,
        "tier": "free",
        "permissions": ["dag:query"],
        "daily_dag_limit": 5,
        "daily_agent_limit": 0,
        "iat": now,
        "exp": now + 60,
        "iss": TEST_ISSUER,
    }
    # 删除指定字段
    if missing_field in payload:
        del payload[missing_field]
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


# =============================================================================
# Property 2: 无效JWT全部拒绝并返回正确错误码
# =============================================================================

class TestProperty2InvalidJwtRejection:
    """
    Property 2: 无效JWT全部拒绝并返回正确错误码

    验证各种无效JWT场景都能被正确拒绝，并抛出相应的异常类型。
    """

    @pytest.fixture
    def verifier(self):
        """创建验证器实例"""
        return InternalJwtVerifier(secret_key=TEST_SECRET, issuer=TEST_ISSUER)

    # -------------------------------------------------------------------------
    # 测试过期JWT
    # -------------------------------------------------------------------------

    def test_expired_jwt_raises_jwt_expired_error(self, verifier):
        """过期的JWT应抛出JwtExpiredError"""
        expired_token = create_expired_jwt()

        with pytest.raises(JwtExpiredError) as exc_info:
            verifier.verify(expired_token)

        assert "已过期" in str(exc_info.value)

    # -------------------------------------------------------------------------
    # 测试签名错误JWT
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("wrong_secret", [
        WRONG_SECRET,
        "another-wrong-secret-32chars-minimum-length",
        "completely-different-key-32chars-minimum",
    ])
    def test_wrong_signature_raises_jwt_invalid_error(self, verifier, wrong_secret):
        """签名错误的JWT应抛出JwtInvalidError"""
        # 使用错误的密钥签名
        token = create_valid_jwt(secret=wrong_secret)

        with pytest.raises(JwtInvalidError) as exc_info:
            verifier.verify(token)

        assert "签名无效" in str(exc_info.value)

    # -------------------------------------------------------------------------
    # 测试缺少必要字段的JWT
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("missing_field", [
        "sub",
        "tier",
        "permissions",
        "iat",
        "exp",
        "iss",
    ])
    def test_missing_required_field_raises_claims_missing_error(
        self, verifier, missing_field
    ):
        """缺少必要字段的JWT应抛出ClaimsMissingError"""
        token = create_jwt_missing_field(missing_field)

        with pytest.raises(ClaimsMissingError) as exc_info:
            verifier.verify(token)

        # 验证错误消息包含缺少的字段信息
        error_msg = str(exc_info.value)
        assert "缺少" in error_msg or "必要" in error_msg

    # -------------------------------------------------------------------------
    # 测试格式错误的JWT
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("invalid_token", [
        "",                          # 空字符串
        "not.a.jwt",                 # 格式错误
        "invalid-jwt-format",        # 无效格式
        "a.b",                       # 缺少部分
        "a.b.c.d",                   # 多余部分
        None,                        # None值
        123,                         # 非字符串类型
    ])
    def test_malformed_jwt_raises_jwt_invalid_error(self, verifier, invalid_token):
        """格式错误的JWT应抛出JwtInvalidError"""
        with pytest.raises(JwtInvalidError):
            verifier.verify(invalid_token)

    # -------------------------------------------------------------------------
    # 测试签发者不匹配的JWT
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("wrong_issuer", [
        "wrong-issuer",
        "malicious-gateway",
        "",
    ])
    def test_wrong_issuer_raises_jwt_invalid_error(self, verifier, wrong_issuer):
        """签发者不匹配的JWT应抛出JwtInvalidError"""
        token = create_valid_jwt(issuer=wrong_issuer)

        with pytest.raises(JwtInvalidError) as exc_info:
            verifier.verify(token)

        assert "签发者不匹配" in str(exc_info.value)

    # -------------------------------------------------------------------------
    # 测试字段类型错误的JWT
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("invalid_payload", [
        # permissions不是数组
        {
            "sub": 1,
            "tier": "free",
            "permissions": "not-an-array",  # 应为数组
            "daily_dag_limit": 5,
            "daily_agent_limit": 0,
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
            "iss": TEST_ISSUER,
        },
        # tier不是字符串
        {
            "sub": 1,
            "tier": 123,  # 应为字符串
            "permissions": ["dag:query"],
            "daily_dag_limit": 5,
            "daily_agent_limit": 0,
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
            "iss": TEST_ISSUER,
        },
    ])
    def test_invalid_field_type_raises_claims_missing_error(
        self, verifier, invalid_payload
    ):
        """字段类型错误的JWT应抛出ClaimsMissingError"""
        token = jwt.encode(invalid_payload, TEST_SECRET, algorithm="HS256")

        with pytest.raises(ClaimsMissingError) as exc_info:
            verifier.verify(token)

        assert "无效" in str(exc_info.value) or "缺少" in str(exc_info.value)


# =============================================================================
# 额外测试：验证有效JWT可以通过
# =============================================================================

class TestValidJwtAcceptance:
    """验证有效的JWT可以被正确接受"""

    @pytest.fixture
    def verifier(self):
        return InternalJwtVerifier(secret_key=TEST_SECRET, issuer=TEST_ISSUER)

    @pytest.mark.parametrize("tier,permissions", [
        ("free", ["dag:query", "profile:read"]),
        ("warmheart", ["dag:query", "dag:template:basic", "profile:read", "profile:write"]),
        ("energy", [
            "dag:query",
            "dag:template:basic",
            "dag:template:advanced",
            "agent:query",
            "profile:read",
            "profile:write",
            "analysis:advanced",
        ]),
    ])
    def test_valid_jwt_returns_permission_claims(
        self, verifier, tier, permissions
    ):
        """有效的JWT应返回PermissionClaims"""
        user_id = 123
        token = create_valid_jwt(
            user_id=user_id,
            tier=tier,
            permissions=permissions,
        )

        claims = verifier.verify(token)

        assert isinstance(claims, PermissionClaims)
        assert claims.user_id == user_id
        assert claims.tier == tier
        assert set(claims.permissions) == set(permissions)

    def test_jwt_with_chinese_permissions_works(self, verifier):
        """包含中文字符的权限应正常工作"""
        token = create_valid_jwt(
            permissions=["dag:query", "特殊权限:测试"],
        )

        claims = verifier.verify(token)
        assert "特殊权限:测试" in claims.permissions


# =============================================================================
# 额外测试：验证器配置验证
# =============================================================================

class TestVerifierConfiguration:
    """验证器配置验证"""

    def test_empty_secret_raises_value_error(self):
        """空密钥应抛出ValueError"""
        with pytest.raises(ValueError) as exc_info:
            InternalJwtVerifier(secret_key="")

        assert "不能为空" in str(exc_info.value)

    def test_custom_algorithms_accepted(self):
        """自定义算法列表应被接受"""
        verifier = InternalJwtVerifier(
            secret_key=TEST_SECRET,
            algorithms=["HS256", "HS512"],
        )
        assert verifier.algorithms == ["HS256", "HS512"]

    def test_default_algorithms_is_hs256(self):
        """默认算法应为HS256"""
        verifier = InternalJwtVerifier(secret_key=TEST_SECRET)
        assert verifier.algorithms == ["HS256"]
