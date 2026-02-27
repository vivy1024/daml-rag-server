# -*- coding: utf-8 -*-
"""
权限系统重构 - DAML-RAG端单元测试

测试组件：
- PermissionClaims: 数据类序列化/反序列化
- InternalJwtVerifier: JWT验证
- FailClosedPermissionChecker: 失败关闭权限检查
- UsageReporter: 用量上报重试队列

Requirements: 1.1-1.5, 2.4, 4.3-4.4, 5.1-5.4, 7.1-7.2, 8.1-8.2
"""

import time
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta

from src.framework.auth.permission_claims import PermissionClaims
from src.framework.auth.internal_jwt_verifier import (
    InternalJwtVerifier,
    JwtExpiredError,
    JwtInvalidError,
    ClaimsMissingError,
)
from src.framework.auth.fail_closed_checker import FailClosedPermissionChecker
from src.framework.auth.permission_checker import PermissionResult
from src.framework.auth.usage_reporter import UsageReporter, UsageReportTask


# =============================================================================
# 测试常量
# =============================================================================

TEST_SECRET = "TestInternalJwtSecret2026AtLeast32Chars!!"
TEST_ISSUER = "yuzhen-auth-gateway"


def _make_valid_payload(**overrides):
    """生成有效的JWT payload"""
    now = int(time.time())
    payload = {
        "sub": 123,
        "tier": "warmheart",
        "permissions": ["dag:query", "dag:template:*", "profile:read", "profile:write"],
        "daily_dag_limit": 10,
        "daily_agent_limit": 0,
        "iat": now,
        "exp": now + 60,
        "iss": TEST_ISSUER,
    }
    payload.update(overrides)
    return payload


def _make_valid_token(**overrides):
    """生成有效的JWT token"""
    payload = _make_valid_payload(**overrides)
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


# =============================================================================
# PermissionClaims 测试
# =============================================================================

class TestPermissionClaims:
    """PermissionClaims 数据类测试"""

    def test_from_jwt_payload_valid(self):
        """有效payload正确解析"""
        payload = _make_valid_payload()
        claims = PermissionClaims.from_jwt_payload(payload)

        assert claims.user_id == 123
        assert claims.tier == "warmheart"
        assert "dag:query" in claims.permissions
        assert claims.daily_dag_limit == 10
        assert claims.daily_agent_limit == 0

    def test_roundtrip_consistency(self):
        """往返一致性: from_jwt_payload(claims.to_dict()) == 原始claims"""
        payload = _make_valid_payload()
        original = PermissionClaims.from_jwt_payload(payload)
        roundtrip = PermissionClaims.from_jwt_payload(original.to_dict())

        assert original.user_id == roundtrip.user_id
        assert original.tier == roundtrip.tier
        assert original.permissions == roundtrip.permissions
        assert original.daily_dag_limit == roundtrip.daily_dag_limit
        assert original.daily_agent_limit == roundtrip.daily_agent_limit

    def test_roundtrip_with_chinese_tier(self):
        """中文字符往返一致性"""
        payload = _make_valid_payload(tier="能量会员")
        original = PermissionClaims.from_jwt_payload(payload)
        roundtrip = PermissionClaims.from_jwt_payload(original.to_dict())
        assert original.tier == roundtrip.tier == "能量会员"

    def test_missing_field_raises_key_error(self):
        """缺少必要字段抛出KeyError"""
        payload = _make_valid_payload()
        del payload["tier"]
        with pytest.raises(KeyError):
            PermissionClaims.from_jwt_payload(payload)

    def test_has_permission(self):
        """权限检查方法"""
        claims = PermissionClaims.from_jwt_payload(_make_valid_payload())
        assert claims.has_permission("dag:query") is True
        assert claims.has_permission("agent:query") is False

    def test_is_expired(self):
        """过期检查"""
        now = int(time.time())
        claims = PermissionClaims.from_jwt_payload(
            _make_valid_payload(exp=now - 10)
        )
        assert claims.is_expired() is True

    def test_not_expired(self):
        """未过期"""
        claims = PermissionClaims.from_jwt_payload(_make_valid_payload())
        assert claims.is_expired() is False

    def test_all_three_tiers(self):
        """三种会员等级都能正确解析"""
        for tier in ["free", "warmheart", "energy"]:
            payload = _make_valid_payload(tier=tier)
            claims = PermissionClaims.from_jwt_payload(payload)
            assert claims.tier == tier


# =============================================================================
# InternalJwtVerifier 测试
# =============================================================================

class TestInternalJwtVerifier:
    """InternalJwtVerifier JWT验证器测试"""

    def setup_method(self):
        self.verifier = InternalJwtVerifier(
            secret_key=TEST_SECRET,
            issuer=TEST_ISSUER,
        )

    def test_valid_token(self):
        """有效JWT验证通过"""
        token = _make_valid_token()
        claims = self.verifier.verify(token)
        assert claims.user_id == 123
        assert claims.tier == "warmheart"

    def test_expired_token_raises(self):
        """过期JWT抛出JwtExpiredError"""
        now = int(time.time())
        token = _make_valid_token(iat=now - 120, exp=now - 60)
        with pytest.raises(JwtExpiredError):
            self.verifier.verify(token)

    def test_wrong_secret_raises(self):
        """错误密钥签名的JWT抛出JwtInvalidError"""
        payload = _make_valid_payload()
        token = pyjwt.encode(payload, "wrong-secret-key-32chars-long!!!", algorithm="HS256")
        with pytest.raises(JwtInvalidError):
            self.verifier.verify(token)

    def test_wrong_issuer_raises(self):
        """错误issuer的JWT抛出JwtInvalidError"""
        token = _make_valid_token(iss="wrong-issuer")
        with pytest.raises(JwtInvalidError):
            self.verifier.verify(token)

    def test_missing_claims_raises(self):
        """缺少必要Claims的JWT抛出ClaimsMissingError"""
        now = int(time.time())
        payload = {"sub": 1, "iat": now, "exp": now + 60, "iss": TEST_ISSUER}
        token = pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")
        with pytest.raises(ClaimsMissingError):
            self.verifier.verify(token)

    def test_empty_token_raises(self):
        """空token抛出JwtInvalidError"""
        with pytest.raises(JwtInvalidError):
            self.verifier.verify("")

    def test_none_token_raises(self):
        """None token抛出JwtInvalidError"""
        with pytest.raises(JwtInvalidError):
            self.verifier.verify(None)

    def test_malformed_token_raises(self):
        """格式错误的token抛出JwtInvalidError"""
        with pytest.raises(JwtInvalidError):
            self.verifier.verify("not.a.valid.jwt.token")

    def test_empty_secret_raises_on_init(self):
        """空密钥初始化抛出ValueError"""
        with pytest.raises(ValueError):
            InternalJwtVerifier(secret_key="")

    def test_energy_user_full_permissions(self):
        """energy用户完整权限验证"""
        all_perms = [
            "dag:query", "dag:template:*", "agent:query",
            "profile:read", "profile:write", "analysis:advanced",
        ]
        token = _make_valid_token(
            sub=42, tier="energy", permissions=all_perms,
            daily_dag_limit=999999, daily_agent_limit=999999,
        )
        claims = self.verifier.verify(token)
        assert claims.user_id == 42
        assert claims.tier == "energy"
        assert len(claims.permissions) == 6


# =============================================================================
# FailClosedPermissionChecker 测试
# =============================================================================

class TestFailClosedPermissionChecker:
    """FailClosedPermissionChecker 失败关闭测试"""

    def setup_method(self):
        self.checker = FailClosedPermissionChecker()

    def _make_claims(self, **overrides):
        return PermissionClaims.from_jwt_payload(_make_valid_payload(**overrides))

    def test_valid_permission_allowed(self):
        """有权限时允许"""
        claims = self._make_claims()
        result = self.checker.check_permission(claims, "dag:query")
        assert result.allowed is True

    def test_missing_permission_denied(self):
        """无权限时拒绝"""
        claims = self._make_claims()
        result = self.checker.check_permission(claims, "agent:query")
        assert result.allowed is False

    def test_none_claims_denied(self):
        """无Claims时拒绝"""
        result = self.checker.check_permission(None, "dag:query")
        assert result.allowed is False

    def test_expired_claims_denied(self):
        """过期Claims时拒绝"""
        now = int(time.time())
        claims = self._make_claims(exp=now - 10)
        result = self.checker.check_permission(claims, "dag:query")
        assert result.allowed is False

    def test_exception_in_check_denied(self):
        """检查过程中异常时拒绝（fail-closed）"""
        # 构造一个会导致异常的claims（permissions不是list）
        claims = self._make_claims()
        claims.permissions = None  # 强制设为None触发异常
        result = self.checker.check_permission(claims, "dag:query")
        assert result.allowed is False

    def test_free_user_upgrade_hint(self):
        """free用户权限不足时返回升级提示"""
        claims = self._make_claims(
            tier="free",
            permissions=["dag:query", "profile:read"],
        )
        result = self.checker.check_permission(claims, "agent:query")
        assert result.allowed is False
        assert result.upgrade_hint is not None


# =============================================================================
# UsageReporter 测试（重试队列逻辑）
# =============================================================================

class TestUsageReporter:
    """UsageReporter 重试队列测试"""

    def test_enqueue_retry_on_failure(self):
        """上报失败时任务进入重试队列"""
        reporter = UsageReporter(
            backend_url="http://localhost:99999",  # 不可达
            internal_token="test-token",
        )
        task = UsageReportTask(
            user_id=1,
            mode="dag",
            session_id="sess_test",
            timestamp="2026-02-12T10:00:00Z",
        )
        reporter._enqueue_retry(task)

        assert reporter.pending_count == 1
        pending = reporter.get_pending_tasks()
        assert pending[0].user_id == 1
        assert pending[0].retry_count == 1

    def test_max_retries_exceeded_discards(self):
        """超过最大重试次数时丢弃任务"""
        reporter = UsageReporter(backend_url="http://localhost:99999")
        task = UsageReportTask(
            user_id=1,
            mode="dag",
            session_id="sess_test",
            timestamp="2026-02-12T10:00:00Z",
            retry_count=3,
            max_retries=3,
        )
        reporter._enqueue_retry(task)
        assert reporter.pending_count == 0

    def test_exponential_backoff(self):
        """重试使用指数退避"""
        reporter = UsageReporter(backend_url="http://localhost:99999")
        task = UsageReportTask(
            user_id=1,
            mode="dag",
            session_id="sess_test",
            timestamp="2026-02-12T10:00:00Z",
            retry_count=0,
        )
        now = time.time()
        reporter._enqueue_retry(task)

        pending = reporter.get_pending_tasks()
        # retry_count变为1，退避时间 = 2^1 = 2秒
        assert pending[0].retry_count == 1
        assert pending[0].next_retry_at >= now + 1.5  # 大约2秒后

    def test_task_fields_preserved_in_queue(self):
        """重试队列中的任务保留完整信息"""
        reporter = UsageReporter(backend_url="http://localhost:99999")
        task = UsageReportTask(
            user_id=42,
            mode="agent",
            session_id="sess_xyz",
            timestamp="2026-02-12T12:00:00Z",
            execution_time_ms=1500,
        )
        reporter._enqueue_retry(task)

        pending = reporter.get_pending_tasks()
        assert pending[0].user_id == 42
        assert pending[0].mode == "agent"
        assert pending[0].session_id == "sess_xyz"
        assert pending[0].timestamp == "2026-02-12T12:00:00Z"
