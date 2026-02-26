"""
测试所有监控API端点
验证监控层简化后API功能完整性

Feature: monitoring-simplification
Task: 8. 测试所有监控API端点

v2.2.0安全加固后：
- /api/health 公开端点直接返回 {status, timestamp, tools}（无code/data包装）
- /api/health/components, /metrics, /metrics/streaming, /metrics/prometheus 需要管理员JWT
"""

import os
import time

import jwt
import requests
from typing import Dict, Any


BASE_URL = "http://localhost:8001"

# 测试用JWT密钥（与容器环境变量一致）
TEST_JWT_SECRET = os.getenv("JWT_SECRET", "test-monitoring-jwt-secret")


def _make_admin_token() -> str:
    """生成管理员JWT token用于认证端点测试"""
    now = int(time.time())
    payload = {
        "sub": 1,
        "role": "admin",
        "iat": now,
        "exp": now + 300,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


def _admin_headers() -> Dict[str, str]:
    """返回带管理员Bearer token的请求头"""
    return {"Authorization": f"Bearer {_make_admin_token()}"}


class TestHealthEndpoints:
    """测试健康检查相关端点"""

    def test_health_endpoint(self):
        """
        Task 8.1: 测试/api/health端点（公开，无需认证）
        Property 2: API返回有效数据
        Validates: Requirements 2.5, 5.3, 9.1

        v2.2.0安全加固后，公开端点直接返回 {status, timestamp, tools}
        """
        response = requests.get(f"{BASE_URL}/api/health")

        # 验证返回200状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        json_data = response.json()

        # v2.2.0: 公开端点直接返回扁平结构
        assert "status" in json_data, "Response should contain 'status' field"
        assert json_data["status"] in ["healthy", "degraded", "unhealthy"], \
            f"Invalid status value: {json_data['status']}"

        assert "timestamp" in json_data, "Response should contain 'timestamp' field"

        # 验证工具列表（非敏感信息，公开返回）
        assert "tools" in json_data, "Response should contain 'tools' field"
        assert isinstance(json_data["tools"], list), "Tools should be a list"
        if json_data["tools"]:
            tool = json_data["tools"][0]
            assert "name" in tool, "Tool should have 'name'"
            assert "display_name" in tool, "Tool should have 'display_name'"

        # 安全加固验证：公开端点不应暴露 components 详情
        assert "components" not in json_data, \
            "Public health endpoint should NOT expose component details (security)"

    def test_health_components_requires_auth(self):
        """
        Task 8.2a: 测试/api/health/components端点 — 无认证应返回401
        Validates: Requirements 9.2
        """
        response = requests.get(f"{BASE_URL}/api/health/components")
        assert response.status_code == 401, \
            f"Expected 401 without auth, got {response.status_code}"

    def test_health_components_endpoint(self):
        """
        Task 8.2b: 测试/api/health/components端点（需要管理员认证）
        Validates: Requirements 2.5, 9.2

        注意：需要容器配置 JWT_SECRET 环境变量才能通过
        """
        if not os.getenv("JWT_SECRET"):
            import pytest
            pytest.skip("JWT_SECRET not configured — admin endpoints untestable")

        response = requests.get(
            f"{BASE_URL}/api/health/components",
            headers=_admin_headers(),
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        json_data = response.json()
        assert "data" in json_data, "Response should contain 'data' field"

        data = json_data["data"]
        assert isinstance(data, dict), "Data should be a dictionary"
        assert len(data) > 0, "Should have at least one component"

        for component_name, component_data in data.items():
            assert "status" in component_data, \
                f"Component {component_name} should have 'status' field"


class TestMetricsEndpoints:
    """测试指标相关端点"""

    def test_metrics_requires_auth(self):
        """
        Task 8.3a: 测试/api/health/metrics端点 — 无认证应返回401
        Validates: Requirements 9.2
        """
        response = requests.get(f"{BASE_URL}/api/health/metrics")
        assert response.status_code == 401, \
            f"Expected 401 without auth, got {response.status_code}"

    def test_metrics_endpoint(self):
        """
        Task 8.3b: 测试/api/health/metrics端点（需要管理员认证）
        Property 2: API返回有效数据
        Validates: Requirements 2.5, 5.4, 9.2
        """
        if not os.getenv("JWT_SECRET"):
            import pytest
            pytest.skip("JWT_SECRET not configured — admin endpoints untestable")

        response = requests.get(
            f"{BASE_URL}/api/health/metrics",
            headers=_admin_headers(),
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        json_data = response.json()
        assert "data" in json_data, "Response should contain 'data' field"

        data = json_data["data"]

        has_system = "system" in data
        has_process = "process" in data
        assert has_system or has_process, \
            "Data should contain 'system' or 'process' metrics"

    def test_streaming_metrics_requires_auth(self):
        """
        Task 8.4a: 测试/api/health/metrics/streaming端点 — 无认证应返回401
        Validates: Requirements 9.2
        """
        response = requests.get(f"{BASE_URL}/api/health/metrics/streaming")
        assert response.status_code == 401, \
            f"Expected 401 without auth, got {response.status_code}"

    def test_streaming_metrics_endpoint(self):
        """
        Task 8.4b: 测试/api/health/metrics/streaming端点（需要管理员认证）
        Property 2: API返回有效数据
        Validates: Requirements 2.5, 5.5, 9.2
        """
        if not os.getenv("JWT_SECRET"):
            import pytest
            pytest.skip("JWT_SECRET not configured — admin endpoints untestable")

        response = requests.get(
            f"{BASE_URL}/api/health/metrics/streaming",
            headers=_admin_headers(),
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        json_data = response.json()
        assert "data" in json_data, "Response should contain 'data' field"

        data = json_data["data"]

        expected_fields = ["total_sessions", "successful_sessions", "failed_sessions",
                          "success_rate", "avg_ttfb_ms", "avg_duration_ms"]

        has_required_fields = any(field in data for field in expected_fields)
        assert has_required_fields, \
            f"Data should contain at least one of: {expected_fields}"

    def test_prometheus_metrics_requires_auth(self):
        """
        Task 8.5a: 测试/api/health/metrics/prometheus端点 — 无认证应返回401
        Validates: Requirements 9.2
        """
        response = requests.get(f"{BASE_URL}/api/health/metrics/prometheus")
        assert response.status_code == 401, \
            f"Expected 401 without auth, got {response.status_code}"

    def test_prometheus_metrics_endpoint(self):
        """
        Task 8.5b: 测试/api/health/metrics/prometheus端点（需要管理员认证）
        Property 2: API返回有效数据
        Validates: Requirements 2.8, 4.2, 4.3, 4.4, 5.6, 9.2
        """
        if not os.getenv("JWT_SECRET"):
            import pytest
            pytest.skip("JWT_SECRET not configured — admin endpoints untestable")

        response = requests.get(
            f"{BASE_URL}/api/health/metrics/prometheus",
            headers=_admin_headers(),
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        text = response.text
        assert text, "Response should not be empty"

        has_help = "# HELP" in text
        has_type = "# TYPE" in text

        metric_lines = [line for line in text.split('\n')
                       if line and not line.startswith('#')]
        has_metrics = len(metric_lines) > 0

        assert has_help or has_type or has_metrics, \
            "Response should contain Prometheus format data (HELP, TYPE, or metrics)"


