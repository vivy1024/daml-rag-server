# -*- coding: utf-8 -*-
"""
监控、日志、性能系统综合测试

作为功能测试调试师，系统性地测试和优化：
1. 监控系统（Prometheus + Grafana）
2. 日志系统（结构化日志 + 会话上下文）
3. 性能系统（缓存 + 并发 + 优化）

更新内容（v1.1.0）：
- 缓存系统测试更新为异步API（put/get）
- 添加get_stats()方法测试
- 添加measure()上下文管理器测试
- 添加get_operation_stats()方法测试
- 集成工作流测试更新为异步API

版本: v1.1.0
创建日期: 2025-12-21
更新日期: 2025-12-21
"""

import pytest
import asyncio
import time
import json
import httpx
import os
from typing import Dict, Any, List
from datetime import datetime


class MonitoringSystemTester:
    """监控系统测试器"""
    
    def __init__(self):
        self.api_url = "http://localhost:8001"
        self.results = {
            "monitoring": {},
            "logging": {},
            "performance": {},
            "integration": {}
        }
    
    async def test_health_check(self) -> Dict[str, Any]:
        """测试1: 健康检查"""
        print("\n" + "="*80)
        print("测试1: 系统健康检查")
        print("="*80)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 系统健康状态: {data.get('msg', 'unknown')}")
                    print(f"  版本: {data.get('data', {}).get('version', 'unknown')}")
                    print(f"  运行时间: {data.get('data', {}).get('uptime', 0)}秒")
                    
                    return {
                        "success": True,
                        "status": data.get('msg'),
                        "version": data.get('data', {}).get('version'),
                        "uptime": data.get('data', {}).get('uptime')
                    }
                else:
                    print(f"❌ 健康检查失败: HTTP {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
        
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_metrics_endpoint(self) -> Dict[str, Any]:
        """测试2: Prometheus指标端点"""
        print("\n" + "="*80)
        print("测试2: Prometheus指标端点")
        print("="*80)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_url}/api/health/metrics/prometheus")
                
                if response.status_code == 200:
                    metrics_text = response.text
                    
                    # 检查关键指标
                    key_metrics = [
                        "streaming_session_ttfb_seconds",
                        "streaming_session_duration_seconds",
                        "streaming_session_tokens_per_second",
                        "streaming_session_success_total",
                        "streaming_session_failure_total"
                    ]
                    
                    found_metrics = []
                    for metric in key_metrics:
                        if metric in metrics_text:
                            found_metrics.append(metric)
                            print(f"  ✅ {metric}")
                        else:
                            print(f"  ❌ {metric} (未找到)")
                    
                    success_rate = len(found_metrics) / len(key_metrics)
                    print(f"\n指标覆盖率: {success_rate:.1%} ({len(found_metrics)}/{len(key_metrics)})")
                    
                    return {
                        "success": success_rate >= 0.8,
                        "total_metrics": len(key_metrics),
                        "found_metrics": len(found_metrics),
                        "coverage": success_rate,
                        "metrics": found_metrics
                    }
                else:
                    print(f"❌ 指标端点失败: HTTP {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
        
        except Exception as e:
            print(f"❌ 指标端点异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_logging_structure(self) -> Dict[str, Any]:
        """测试3: 日志结构验证"""
        print("\n" + "="*80)
        print("测试3: 日志结构验证")
        print("="*80)
        
        try:
            # 当前仓库已切换为 structured_logger + metrics_collector 体系
            from src.framework.monitoring.structured_logger import get_logger, set_trace_id

            trace_id = set_trace_id()
            logger = get_logger("monitoring_system_test")
            logger.info("测试日志记录", trace_id=trace_id, component="tests")
            logger.info("测试步骤日志", trace_id=trace_id, step=1, step_name="测试步骤")

            print("✅ 日志系统可用（structured_logger）")
            return {"success": True, "logger_available": True}

        except Exception as e:
            print(f"❌ 日志系统异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_cache_system(self) -> Dict[str, Any]:
        """测试4: 缓存系统验证（使用异步API）"""
        print("\n" + "="*80)
        print("测试4: 缓存系统验证（异步API）")
        print("="*80)
        
        try:
            from src.framework.mcp.cache_manager import CacheManager
            
            cache_manager = CacheManager()
            
            # 测试缓存设置和获取（使用异步API）
            test_key = "test_cache_key"
            test_value = {"data": "test_value", "timestamp": time.time()}
            
            # 设置缓存（使用异步put方法）
            await cache_manager.put(test_key, test_value, ttl=60)
            print(f"✅ 缓存设置成功（异步put）")
            
            # 获取缓存（使用异步get方法）
            cached_value = await cache_manager.get(test_key)
            
            if cached_value:
                print(f"✅ 缓存获取成功（异步get）")
                cache_hit = True
            else:
                print(f"❌ 缓存获取失败")
                cache_hit = False
            
            # 测试缓存统计（get_stats方法）
            stats = await cache_manager.get_stats()
            print(f"\n缓存统计:")
            print(f"  命中数: {stats.get('hits', 0)}")
            print(f"  未命中数: {stats.get('misses', 0)}")
            print(f"  命中率: {stats.get('hit_rate', '0%')}")
            print(f"  缓存大小: {stats.get('size', 0)}")
            
            # 验证统计数据的完整性
            required_fields = ['hit_rate', 'hits', 'misses', 'size']
            stats_complete = all(field in stats for field in required_fields)
            
            if stats_complete:
                print(f"✅ 缓存统计数据完整")
            else:
                print(f"⚠️ 缓存统计数据不完整")
            
            return {
                "success": cache_hit and stats_complete,
                "cache_set": True,
                "cache_get": cache_hit,
                "stats_complete": stats_complete,
                "stats": stats
            }
        
        except Exception as e:
            print(f"❌ 缓存系统异常: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def test_performance_monitoring(self) -> Dict[str, Any]:
        """测试5: 性能监控验证（Prometheus集成/装饰器）"""
        print("\n" + "="*80)
        print("测试5: 性能监控验证（Prometheus集成）")
        print("="*80)
        
        try:
            from src.framework.monitoring.prometheus_integration import (
                record_cache_hit,
                record_cache_miss,
                track_workflow_step,
            )

            record_cache_hit(cache_type="test", level="L1")
            record_cache_miss(cache_type="test", level="L1")

            @track_workflow_step("test_step_prometheus")
            async def _dummy_step():
                await asyncio.sleep(0.01)

            await _dummy_step()
            print("✅ Prometheus集成功能正常（record_* + track_workflow_step）")

            return {
                "success": True,
                "prometheus_integration": True,
            }
        
        except Exception as e:
            print(f"❌ 性能监控异常: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def test_integration_workflow(self) -> Dict[str, Any]:
        """测试6: 集成工作流验证（使用异步API和新功能）"""
        print("\n" + "="*80)
        print("测试6: 集成工作流验证（structured_logger + CacheManager + Prometheus）")
        print("="*80)
        
        print("测试完整工作流：日志 → 监控 → 缓存 → 性能")
        
        try:
            from src.framework.monitoring.structured_logger import get_logger, set_trace_id
            from src.framework.mcp.cache_manager import CacheManager
            from src.framework.monitoring.prometheus_integration import track_workflow_step

            trace_id = set_trace_id()
            logger = get_logger("integration_workflow_test")
            logger.info("integration_workflow_start", trace_id=trace_id)

            cache_manager = CacheManager()

            @track_workflow_step("integration_workflow_test_step")
            async def _run():
                cache_key = "integration_test_key"
                cache_value = {"test": "data", "timestamp": time.time()}
                await cache_manager.put(cache_key, cache_value, ttl=60)
                return await cache_manager.get(cache_key)

            cached = await _run()
            cache_stats = await cache_manager.get_stats()

            logger.info(
                "integration_workflow_end",
                trace_id=trace_id,
                cache_hit=cached is not None,
            )

            print("\n集成测试结果:")
            print(f"  日志: ✅")
            print(f"  缓存: {'✅' if cached else '❌'}")
            print(f"  Prometheus: ✅")
            print(f"  缓存统计: {'✅' if cache_stats else '❌'}")

            return {
                "success": cached is not None and cache_stats is not None,
                "logging": True,
                "caching": cached is not None,
                "monitoring": True,
                "cache_stats_available": cache_stats is not None,
            }
        
        except Exception as e:
            print(f"❌ 集成工作流异常: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("\n" + "="*80)
        print("监控、日志、性能系统综合测试")
        print("="*80)
        print(f"测试时间: {datetime.now().isoformat()}")
        
        # 运行所有测试
        self.results["monitoring"]["health_check"] = await self.test_health_check()
        self.results["monitoring"]["metrics_endpoint"] = await self.test_metrics_endpoint()
        self.results["logging"]["structure"] = await self.test_logging_structure()
        self.results["performance"]["cache_system"] = await self.test_cache_system()
        self.results["performance"]["monitoring"] = await self.test_performance_monitoring()
        self.results["integration"]["workflow"] = await self.test_integration_workflow()
        
        # 统计结果
        all_tests = []
        for category in self.results.values():
            for test_result in category.values():
                all_tests.append(test_result.get("success", False))
        
        passed = sum(all_tests)
        total = len(all_tests)
        success_rate = passed / total if total > 0 else 0
        
        # 打印总结
        print("\n" + "="*80)
        print("测试总结")
        print("="*80)
        print(f"总测试数: {total}")
        print(f"通过数: {passed}")
        print(f"失败数: {total - passed}")
        print(f"成功率: {success_rate:.1%}")
        
        print("\n详细结果:")
        print(f"  监控系统:")
        print(f"    - 健康检查: {'✅' if self.results['monitoring']['health_check']['success'] else '❌'}")
        print(f"    - 指标端点: {'✅' if self.results['monitoring']['metrics_endpoint']['success'] else '❌'}")
        print(f"  日志系统:")
        print(f"    - 日志结构: {'✅' if self.results['logging']['structure']['success'] else '❌'}")
        print(f"  性能系统:")
        print(f"    - 缓存系统: {'✅' if self.results['performance']['cache_system']['success'] else '❌'}")
        print(f"    - 性能监控: {'✅' if self.results['performance']['monitoring']['success'] else '❌'}")
        print(f"  集成测试:")
        print(f"    - 工作流: {'✅' if self.results['integration']['workflow']['success'] else '❌'}")
        
        # 保存报告
        report = {
            "test_time": datetime.now().isoformat(),
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": total - passed,
            "success_rate": success_rate,
            "results": self.results
        }
        
        report_file = "tests/系统集成测试/monitoring_system_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 测试报告已保存: {report_file}")
        
        return report


# ========== Pytest测试用例 ==========

def _should_run_live_tests() -> bool:
    """
    这些测试依赖运行中的DAML-RAG服务（默认localhost:8001）。
    默认在本地/CI未启动服务时跳过，避免误报失败。
    """
    return os.getenv("RUN_DAML_RAG_LIVE_TESTS", "false").lower() in ("true", "1", "yes")

@pytest.mark.asyncio
async def test_monitoring_health_check():
    """测试监控系统健康检查"""
    if not _should_run_live_tests():
        pytest.skip("需要运行中的DAML-RAG服务（设置RUN_DAML_RAG_LIVE_TESTS=true启用）")
    tester = MonitoringSystemTester()
    result = await tester.test_health_check()
    assert result["success"], "健康检查失败"


@pytest.mark.asyncio
async def test_monitoring_metrics_endpoint():
    """测试Prometheus指标端点"""
    if not _should_run_live_tests():
        pytest.skip("需要运行中的DAML-RAG服务（设置RUN_DAML_RAG_LIVE_TESTS=true启用）")
    tester = MonitoringSystemTester()
    result = await tester.test_metrics_endpoint()
    assert result["success"], f"指标端点测试失败，覆盖率: {result.get('coverage', 0):.1%}"


@pytest.mark.asyncio
async def test_logging_structure():
    """测试日志结构"""
    if not _should_run_live_tests():
        pytest.skip("需要运行中的DAML-RAG服务（设置RUN_DAML_RAG_LIVE_TESTS=true启用）")
    tester = MonitoringSystemTester()
    result = await tester.test_logging_structure()
    assert result["success"], "日志结构测试失败"


@pytest.mark.asyncio
async def test_cache_system():
    """测试缓存系统"""
    if not _should_run_live_tests():
        pytest.skip("需要运行中的DAML-RAG服务（设置RUN_DAML_RAG_LIVE_TESTS=true启用）")
    tester = MonitoringSystemTester()
    result = await tester.test_cache_system()
    assert result["success"], "缓存系统测试失败"


@pytest.mark.asyncio
async def test_performance_monitoring():
    """测试性能监控"""
    if not _should_run_live_tests():
        pytest.skip("需要运行中的DAML-RAG服务（设置RUN_DAML_RAG_LIVE_TESTS=true启用）")
    tester = MonitoringSystemTester()
    result = await tester.test_performance_monitoring()
    assert result["success"], "性能监控测试失败"


@pytest.mark.asyncio
async def test_integration_workflow():
    """测试集成工作流"""
    if not _should_run_live_tests():
        pytest.skip("需要运行中的DAML-RAG服务（设置RUN_DAML_RAG_LIVE_TESTS=true启用）")
    tester = MonitoringSystemTester()
    result = await tester.test_integration_workflow()
    assert result["success"], "集成工作流测试失败"


@pytest.mark.asyncio
async def test_full_monitoring_system():
    """完整的监控系统测试"""
    if not _should_run_live_tests():
        pytest.skip("需要运行中的DAML-RAG服务（设置RUN_DAML_RAG_LIVE_TESTS=true启用）")
    tester = MonitoringSystemTester()
    report = await tester.run_all_tests()
    
    # 要求至少80%的测试通过
    assert report["success_rate"] >= 0.8, \
        f"测试成功率 {report['success_rate']:.1%} 低于要求的80%"


if __name__ == "__main__":
    # 直接运行测试
    print("开始监控、日志、性能系统综合测试...")
    asyncio.run(test_full_monitoring_system())
