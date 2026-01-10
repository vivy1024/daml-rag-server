"""
测试所有监控API端点
验证监控层简化后API功能完整性

Feature: monitoring-simplification
Task: 8. 测试所有监控API端点
"""

import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8001"


class TestHealthEndpoints:
    """测试健康检查相关端点"""
    
    def test_health_endpoint(self):
        """
        Task 8.1: 测试/api/health端点
        Property 2: API返回有效数据
        Validates: Requirements 2.5, 5.3
        """
        response = requests.get(f"{BASE_URL}/api/health")
        
        # 验证返回200状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # 验证返回JSON格式
        json_data = response.json()
        
        # 验证统一响应格式
        assert "code" in json_data, "Response should contain 'code' field"
        assert "data" in json_data, "Response should contain 'data' field"
        
        data = json_data["data"]
        
        # 验证返回JSON包含status字段
        assert "status" in data, "Data should contain 'status' field"
        assert data["status"] in ["healthy", "degraded", "unhealthy"], \
            f"Invalid status value: {data['status']}"
        
        # 验证返回JSON包含components字段
        assert "components" in data, "Data should contain 'components' field"
        assert isinstance(data["components"], dict), "Components should be a dictionary"
        
        print(f"✅ /api/health endpoint working correctly")
        print(f"   Status: {data['status']}")
        print(f"   Components: {len(data['components'])} components")
    
    def test_health_components_endpoint(self):
        """
        Task 8.2: 测试/api/health/components端点
        Validates: Requirements 2.5
        """
        response = requests.get(f"{BASE_URL}/api/health/components")
        
        # 验证返回200状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # 验证返回组件详细状态
        json_data = response.json()
        assert "data" in json_data, "Response should contain 'data' field"
        
        data = json_data["data"]
        assert isinstance(data, dict), "Data should be a dictionary"
        
        # 验证至少有一些组件
        assert len(data) > 0, "Should have at least one component"
        
        # 验证每个组件都有status字段
        for component_name, component_data in data.items():
            assert "status" in component_data, \
                f"Component {component_name} should have 'status' field"
        
        print(f"✅ /api/health/components endpoint working correctly")
        print(f"   Components: {list(data.keys())}")


class TestMetricsEndpoints:
    """测试指标相关端点"""
    
    def test_metrics_endpoint(self):
        """
        Task 8.3: 测试/api/health/metrics端点
        Property 2: API返回有效数据
        Validates: Requirements 2.5, 5.4
        """
        response = requests.get(f"{BASE_URL}/api/health/metrics")
        
        # 验证返回200状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # 验证返回系统和进程指标
        json_data = response.json()
        assert "data" in json_data, "Response should contain 'data' field"
        
        data = json_data["data"]
        
        # 验证包含system或process字段
        has_system = "system" in data
        has_process = "process" in data
        assert has_system or has_process, \
            "Data should contain 'system' or 'process' metrics"
        
        if has_system:
            system_metrics = data["system"]
            assert "cpu_percent" in system_metrics or "memory_percent" in system_metrics, \
                "System metrics should contain CPU or memory data"
        
        if has_process:
            process_metrics = data["process"]
            assert "cpu_percent" in process_metrics or "memory_mb" in process_metrics, \
                "Process metrics should contain CPU or memory data"
        
        print(f"✅ /api/health/metrics endpoint working correctly")
        print(f"   Has system metrics: {has_system}")
        print(f"   Has process metrics: {has_process}")
    
    def test_streaming_metrics_endpoint(self):
        """
        Task 8.4: 测试/api/health/metrics/streaming端点
        Property 2: API返回有效数据
        Validates: Requirements 2.5, 5.5
        """
        response = requests.get(f"{BASE_URL}/api/health/metrics/streaming")
        
        # 验证返回200状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # 验证返回流式统计数据
        json_data = response.json()
        assert "data" in json_data, "Response should contain 'data' field"
        
        data = json_data["data"]
        
        # 验证包含流式监控的关键字段
        expected_fields = ["total_sessions", "successful_sessions", "failed_sessions", 
                          "success_rate", "avg_ttfb_ms", "avg_duration_ms"]
        
        has_required_fields = any(field in data for field in expected_fields)
        assert has_required_fields, \
            f"Data should contain at least one of: {expected_fields}"
        
        print(f"✅ /api/health/metrics/streaming endpoint working correctly")
        print(f"   Total sessions: {data.get('total_sessions', 0)}")
        print(f"   Success rate: {data.get('success_rate', 0):.1%}")
    
    def test_prometheus_metrics_endpoint(self):
        """
        Task 8.5: 测试/api/health/metrics/prometheus端点
        Property 2: API返回有效数据
        Validates: Requirements 2.8, 4.2, 4.3, 4.4, 5.6
        """
        response = requests.get(f"{BASE_URL}/api/health/metrics/prometheus")
        
        # 验证返回200状态码
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # 验证返回Prometheus格式文本
        text = response.text
        assert text, "Response should not be empty"
        
        # 验证包含HELP、TYPE、指标行
        has_help = "# HELP" in text
        has_type = "# TYPE" in text
        
        # 至少应该有一些指标行（不以#开头的行）
        metric_lines = [line for line in text.split('\n') 
                       if line and not line.startswith('#')]
        has_metrics = len(metric_lines) > 0
        
        assert has_help or has_type or has_metrics, \
            "Response should contain Prometheus format data (HELP, TYPE, or metrics)"
        
        print(f"✅ /api/health/metrics/prometheus endpoint working correctly")
        print(f"   Has HELP lines: {has_help}")
        print(f"   Has TYPE lines: {has_type}")
        print(f"   Has metric lines: {has_metrics} ({len(metric_lines)} lines)")


def run_all_tests():
    """运行所有测试并生成报告"""
    print("\n" + "="*60)
    print("监控API端点测试")
    print("="*60 + "\n")
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    # 测试健康检查端点
    health_tests = TestHealthEndpoints()
    
    try:
        print("\n[测试 8.1] /api/health 端点")
        health_tests.test_health_endpoint()
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(("8.1 /api/health", str(e)))
    
    try:
        print("\n[测试 8.2] /api/health/components 端点")
        health_tests.test_health_components_endpoint()
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(("8.2 /api/health/components", str(e)))
    
    # 测试指标端点
    metrics_tests = TestMetricsEndpoints()
    
    try:
        print("\n[测试 8.3] /api/health/metrics 端点")
        metrics_tests.test_metrics_endpoint()
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(("8.3 /api/health/metrics", str(e)))
    
    try:
        print("\n[测试 8.4] /api/health/metrics/streaming 端点")
        metrics_tests.test_streaming_metrics_endpoint()
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(("8.4 /api/health/metrics/streaming", str(e)))
    
    try:
        print("\n[测试 8.5] /api/health/metrics/prometheus 端点")
        metrics_tests.test_prometheus_metrics_endpoint()
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(("8.5 /api/health/metrics/prometheus", str(e)))
    
    # 打印测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"✅ 通过: {test_results['passed']}")
    print(f"❌ 失败: {test_results['failed']}")
    
    if test_results["errors"]:
        print("\n失败的测试:")
        for test_name, error in test_results["errors"]:
            print(f"  - {test_name}: {error}")
    
    print("\n" + "="*60)
    
    return test_results


if __name__ == "__main__":
    results = run_all_tests()
    exit(0 if results["failed"] == 0 else 1)
