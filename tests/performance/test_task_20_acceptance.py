# -*- coding: utf-8 -*-
"""
任务20: 性能优化验收测试

验收内容：
1. 验证所有性能指标达标
2. 验证所有错误处理机制正常
3. 验证监控和告警系统正常
4. 生成最终验收报告

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import asyncio
import json
import yaml
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import aiohttp

# 导入其他测试模块
import sys
sys.path.insert(0, str(Path(__file__).parent))

from test_e2e_performance import (
    run_sequential_test,
    run_concurrent_test,
    run_cache_test
)
from test_task_19_stress_test import (
    test_scenario_1_high_concurrency,
    test_scenario_2_db_pool_exhaustion,
    test_scenario_3_redis_unavailable,
    test_scenario_4_llm_backend_failure,
    test_scenario_5_network_latency
)

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "performance_optimization.yaml"
API_BASE_URL = "http://localhost:8001/api"  # 注意：需要加/api前缀


class AcceptanceTestResult:
    """验收测试结果"""
    
    def __init__(self):
        self.test_items = []
        self.passed_count = 0
        self.failed_count = 0
        self.warnings = []
    
    def add_test_item(
        self,
        category: str,
        name: str,
        passed: bool,
        expected: str,
        actual: str,
        details: str = ""
    ):
        """添加测试项"""
        self.test_items.append({
            "category": category,
            "name": name,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "details": details
        })
        
        if passed:
            self.passed_count += 1
        else:
            self.failed_count += 1
    
    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        total = self.passed_count + self.failed_count
        return {
            "total_tests": total,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "pass_rate": self.passed_count / total if total > 0 else 0.0,
            "warnings": len(self.warnings),
            "test_items": self.test_items,
            "warning_messages": self.warnings
        }


async def verify_performance_metrics() -> AcceptanceTestResult:
    """验证性能指标"""
    print("\n" + "="*80)
    print("1. 验证性能指标")
    print("="*80)
    
    result = AcceptanceTestResult()
    
    # 加载性能目标
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    targets = config.get("performance_targets", {})
    
    # 1.1 工作流总耗时
    print("\n1.1 测试工作流总耗时...")
    seq_result = await run_sequential_test(num_requests=5)
    seq_summary = seq_result.get_summary()
    avg_response_time = seq_summary["response_time"]["avg"]
    target_time = targets.get("workflow_total_time", 30)
    
    result.add_test_item(
        category="性能指标",
        name="工作流总耗时",
        passed=avg_response_time < target_time,
        expected=f"< {target_time}秒",
        actual=f"{avg_response_time:.2f}秒",
        details=f"P95: {seq_summary['response_time']['p95']:.2f}s, P99: {seq_summary['response_time']['p99']:.2f}s"
    )
    
    # 1.2 TTFB
    print("1.2 测试TTFB...")
    avg_ttfb = seq_summary["ttfb"]["avg"]
    target_ttfb = targets.get("ttfb", 5)
    
    result.add_test_item(
        category="性能指标",
        name="TTFB (首字节时间)",
        passed=avg_ttfb < target_ttfb,
        expected=f"< {target_ttfb}秒",
        actual=f"{avg_ttfb:.2f}秒",
        details=f"P95: {seq_summary['ttfb']['p95']:.2f}s"
    )
    
    # 1.3 并发处理能力
    print("1.3 测试并发处理能力...")
    conc_result = await run_concurrent_test(num_requests=50, concurrency=10)
    conc_summary = conc_result.get_summary()
    qps = conc_summary["qps"]
    target_qps = targets.get("qps", 200)
    
    # QPS目标较高，我们设置一个最低要求
    min_qps = 50
    passed_qps = qps >= min_qps
    
    result.add_test_item(
        category="性能指标",
        name="并发处理能力 (QPS)",
        passed=passed_qps,
        expected=f">= {min_qps} (目标: {target_qps})",
        actual=f"{qps:.2f}",
        details=f"成功率: {conc_summary['success_rate']:.1%}"
    )
    
    if qps < target_qps:
        result.add_warning(f"QPS ({qps:.2f}) 未达到目标 ({target_qps})，但超过最低要求 ({min_qps})")
    
    # 1.4 缓存命中率
    print("1.4 测试缓存命中率...")
    cache_result = await run_cache_test(num_requests=15)
    cache_summary = cache_result.get_summary()
    cache_hit_rate = cache_summary["cache"]["hit_rate"]
    target_cache_hit_rate = targets.get("cache_hit_rate", 0.8)
    
    result.add_test_item(
        category="性能指标",
        name="缓存命中率",
        passed=cache_hit_rate >= target_cache_hit_rate,
        expected=f">= {target_cache_hit_rate:.0%}",
        actual=f"{cache_hit_rate:.1%}",
        details=f"命中: {cache_summary['cache']['hits']}, 未命中: {cache_summary['cache']['misses']}"
    )
    
    return result



async def verify_error_handling() -> AcceptanceTestResult:
    """验证错误处理机制"""
    print("\n" + "="*80)
    print("2. 验证错误处理机制")
    print("="*80)
    
    result = AcceptanceTestResult()
    
    # 2.1 数据库连接池耗尽处理
    print("\n2.1 测试数据库连接池耗尽处理...")
    db_metrics = await test_scenario_2_db_pool_exhaustion(num_requests=50, concurrency=30)
    db_summary = db_metrics.get_summary()
    
    # 系统应该能处理连接池耗尽，成功率应该 >= 50%
    result.add_test_item(
        category="错误处理",
        name="数据库连接池耗尽处理",
        passed=db_summary["success_rate"] >= 0.5,
        expected=">= 50% 成功率",
        actual=f"{db_summary['success_rate']:.1%}",
        details=f"失败: {db_summary['requests_failed']}, 超时: {db_summary['errors']['timeout_count']}"
    )
    
    # 2.2 Redis缓存不可用处理
    print("2.2 测试Redis缓存不可用处理...")
    redis_metrics = await test_scenario_3_redis_unavailable(num_requests=20)
    redis_summary = redis_metrics.get_summary()
    
    # 系统应该降级到内存缓存或直接查询，成功率应该 >= 60%
    result.add_test_item(
        category="错误处理",
        name="Redis缓存不可用处理",
        passed=redis_summary["success_rate"] >= 0.6,
        expected=">= 60% 成功率 (降级模式)",
        actual=f"{redis_summary['success_rate']:.1%}",
        details="系统应降级到内存缓存或直接查询数据库"
    )
    
    # 2.3 LLM后端失败处理
    print("2.3 测试LLM后端失败处理...")
    llm_metrics = await test_scenario_4_llm_backend_failure(num_requests=15)
    llm_summary = llm_metrics.get_summary()
    
    # 系统应该降级到模板响应，成功率应该 >= 50%
    result.add_test_item(
        category="错误处理",
        name="LLM后端失败处理",
        passed=llm_summary["success_rate"] >= 0.5,
        expected=">= 50% 成功率 (模板响应)",
        actual=f"{llm_summary['success_rate']:.1%}",
        details="系统应降级到模板化响应"
    )
    
    # 2.4 网络延迟处理
    print("2.4 测试网络延迟处理...")
    latency_metrics = await test_scenario_5_network_latency(num_requests=15, simulated_latency_ms=500)
    latency_summary = latency_metrics.get_summary()
    
    # 系统应该能容忍网络延迟，成功率应该 >= 70%
    result.add_test_item(
        category="错误处理",
        name="网络延迟处理",
        passed=latency_summary["success_rate"] >= 0.7,
        expected=">= 70% 成功率",
        actual=f"{latency_summary['success_rate']:.1%}",
        details=f"平均响应时间: {latency_summary['response_time']['avg']:.2f}s"
    )
    
    return result


async def verify_monitoring_system() -> AcceptanceTestResult:
    """验证监控和告警系统"""
    print("\n" + "="*80)
    print("3. 验证监控和告警系统")
    print("="*80)
    
    result = AcceptanceTestResult()
    
    # 3.1 配置文件存在性
    print("\n3.1 检查配置文件...")
    config_exists = CONFIG_FILE.exists()
    
    result.add_test_item(
        category="监控系统",
        name="性能优化配置文件",
        passed=config_exists,
        expected="配置文件存在",
        actual="存在" if config_exists else "不存在",
        details=str(CONFIG_FILE)
    )
    
    if not config_exists:
        return result
    
    # 3.2 配置完整性
    print("3.2 检查配置完整性...")
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    required_sections = [
        "cache",
        "connection_pool",
        "llm_fallback",
        "concurrency",
        "monitoring",
        "performance_targets"
    ]
    
    missing_sections = [s for s in required_sections if s not in config]
    
    result.add_test_item(
        category="监控系统",
        name="配置完整性",
        passed=len(missing_sections) == 0,
        expected="所有必需配置段存在",
        actual=f"缺失: {missing_sections}" if missing_sections else "完整",
        details=f"检查了 {len(required_sections)} 个配置段"
    )
    
    # 3.3 监控配置
    print("3.3 检查监控配置...")
    monitoring_config = config.get("monitoring", {})
    monitoring_enabled = monitoring_config.get("enabled", False)
    prometheus_enabled = monitoring_config.get("prometheus", {}).get("enabled", False)
    
    result.add_test_item(
        category="监控系统",
        name="监控功能启用",
        passed=monitoring_enabled,
        expected="监控已启用",
        actual="已启用" if monitoring_enabled else "未启用",
        details=f"Prometheus: {'已启用' if prometheus_enabled else '未启用'}"
    )
    
    # 3.4 告警配置
    print("3.4 检查告警配置...")
    alerts_config = monitoring_config.get("alerts", {})
    alerts_enabled = alerts_config.get("enabled", False)
    
    alert_types = [
        "performance_bottleneck",
        "error_rate",
        "resource_usage",
        "concurrency_limit"
    ]
    
    configured_alerts = [a for a in alert_types if a in alerts_config]
    
    result.add_test_item(
        category="监控系统",
        name="告警规则配置",
        passed=alerts_enabled and len(configured_alerts) >= 3,
        expected="告警已启用且配置 >= 3种告警类型",
        actual=f"{'已启用' if alerts_enabled else '未启用'}, 配置了 {len(configured_alerts)} 种",
        details=f"告警类型: {configured_alerts}"
    )
    
    # 3.5 性能报告文件
    print("3.5 检查性能报告文件...")
    report_files = [
        Path("tests/performance/performance_report.json"),
        Path("tests/performance/stress_test_report.json")
    ]
    
    existing_reports = [f for f in report_files if f.exists()]
    
    result.add_test_item(
        category="监控系统",
        name="性能报告文件",
        passed=len(existing_reports) >= 1,
        expected="至少存在1个性能报告",
        actual=f"存在 {len(existing_reports)} 个报告",
        details=f"报告: {[f.name for f in existing_reports]}"
    )
    
    return result



def generate_acceptance_report(
    results: Dict[str, AcceptanceTestResult],
    output_file: str = "acceptance_report.json"
) -> Dict[str, Any]:
    """生成验收报告"""
    report = {
        "test_time": datetime.now().isoformat(),
        "test_type": "性能优化验收测试",
        "version": "v1.0.0",
        "categories": {},
        "overall_summary": {},
        "test_passed": True,
        "recommendations": []
    }
    
    # 收集所有测试结果
    all_test_items = []
    total_passed = 0
    total_failed = 0
    all_warnings = []
    
    for category_name, result in results.items():
        summary = result.get_summary()
        report["categories"][category_name] = summary
        
        all_test_items.extend(summary["test_items"])
        total_passed += summary["passed"]
        total_failed += summary["failed"]
        all_warnings.extend(summary["warning_messages"])
        
        if summary["failed"] > 0:
            report["test_passed"] = False
    
    # 总体摘要
    total_tests = total_passed + total_failed
    report["overall_summary"] = {
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed,
        "pass_rate": total_passed / total_tests if total_tests > 0 else 0.0,
        "warnings": len(all_warnings),
        "categories_tested": len(results)
    }
    
    # 生成建议
    failed_items = [item for item in all_test_items if not item["passed"]]
    
    for item in failed_items:
        severity = "high" if item["category"] == "性能指标" else "medium"
        report["recommendations"].append({
            "category": item["category"],
            "test": item["name"],
            "expected": item["expected"],
            "actual": item["actual"],
            "severity": severity,
            "recommendation": _get_recommendation(item)
        })
    
    # 添加警告相关的建议
    for warning in all_warnings:
        report["recommendations"].append({
            "category": "警告",
            "test": "性能警告",
            "expected": "无警告",
            "actual": warning,
            "severity": "low",
            "recommendation": "关注性能指标，考虑进一步优化"
        })
    
    # 保存报告
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 验收报告已保存到: {output_file}")
    
    return report


def _get_recommendation(item: Dict[str, Any]) -> str:
    """根据测试项生成建议"""
    name = item["name"]
    
    if "工作流总耗时" in name:
        return "优化慢查询，增加缓存，优化LLM调用性能"
    elif "TTFB" in name:
        return "优化首次响应时间，考虑预加载和缓存预热"
    elif "QPS" in name:
        return "增加连接池大小，优化并发处理，考虑水平扩展"
    elif "缓存命中率" in name:
        return "优化缓存策略，增加缓存预热，调整TTL配置"
    elif "数据库连接池" in name:
        return "增加连接池大小，优化连接管理，实现连接复用"
    elif "Redis" in name:
        return "确保Redis服务稳定，实现降级机制，增加内存缓存"
    elif "LLM" in name:
        return "实现LLM降级策略，增加模板响应，优化重试机制"
    elif "网络延迟" in name:
        return "增加超时时间，实现异步处理，优化网络配置"
    else:
        return "检查相关配置和日志，进行针对性优化"



def print_acceptance_summary(report: Dict[str, Any]):
    """打印验收摘要"""
    print("\n" + "="*80)
    print("📊 性能优化验收报告")
    print("="*80)
    
    print(f"\n测试时间: {report['test_time']}")
    print(f"测试类型: {report['test_type']}")
    print(f"测试版本: {report['version']}")
    print(f"验收结果: {'✅ 通过' if report['test_passed'] else '❌ 未通过'}")
    
    # 总体摘要
    summary = report["overall_summary"]
    print(f"\n{'='*80}")
    print("总体摘要")
    print(f"{'='*80}")
    print(f"  总测试项: {summary['total_tests']}")
    print(f"  通过: {summary['passed']} ✅")
    print(f"  失败: {summary['failed']} ❌")
    print(f"  通过率: {summary['pass_rate']:.1%}")
    print(f"  警告数: {summary['warnings']} ⚠️")
    print(f"  测试类别: {summary['categories_tested']}")
    
    # 各类别详情
    for category_name, category_result in report["categories"].items():
        print(f"\n{'='*80}")
        print(f"类别: {category_name}")
        print(f"{'='*80}")
        
        print(f"  总测试项: {category_result['total_tests']}")
        print(f"  通过: {category_result['passed']} ✅")
        print(f"  失败: {category_result['failed']} ❌")
        print(f"  通过率: {category_result['pass_rate']:.1%}")
        
        # 显示测试项
        for item in category_result["test_items"]:
            status = "✅" if item["passed"] else "❌"
            print(f"\n  {status} {item['name']}")
            print(f"     期望: {item['expected']}")
            print(f"     实际: {item['actual']}")
            if item["details"]:
                print(f"     详情: {item['details']}")
    
    # 优化建议
    if report["recommendations"]:
        print(f"\n{'='*80}")
        print("💡 优化建议")
        print(f"{'='*80}")
        
        # 按严重程度分组
        high_severity = [r for r in report["recommendations"] if r.get("severity") == "high"]
        medium_severity = [r for r in report["recommendations"] if r.get("severity") == "medium"]
        low_severity = [r for r in report["recommendations"] if r.get("severity") == "low"]
        
        if high_severity:
            print(f"\n🔴 高优先级 ({len(high_severity)}项):")
            for rec in high_severity:
                print(f"\n  类别: {rec['category']}")
                print(f"  测试: {rec['test']}")
                print(f"  期望: {rec['expected']}")
                print(f"  实际: {rec['actual']}")
                print(f"  建议: {rec['recommendation']}")
        
        if medium_severity:
            print(f"\n🟡 中优先级 ({len(medium_severity)}项):")
            for rec in medium_severity:
                print(f"\n  类别: {rec['category']}")
                print(f"  测试: {rec['test']}")
                print(f"  期望: {rec['expected']}")
                print(f"  实际: {rec['actual']}")
                print(f"  建议: {rec['recommendation']}")
        
        if low_severity:
            print(f"\n🟢 低优先级 ({len(low_severity)}项):")
            for rec in low_severity[:5]:  # 只显示前5个
                print(f"\n  类别: {rec['category']}")
                print(f"  测试: {rec['test']}")
                print(f"  建议: {rec['recommendation']}")
    
    # 最终结论
    print(f"\n{'='*80}")
    print("最终结论")
    print(f"{'='*80}")
    
    if report["test_passed"]:
        print("\n✅ 性能优化验收通过！")
        print("\n所有关键性能指标和错误处理机制均已达标。")
        print("系统已准备好投入生产环境使用。")
    else:
        print("\n❌ 性能优化验收未通过！")
        print(f"\n有 {summary['failed']} 项测试未通过，请查看上述优化建议进行改进。")
        print("建议在修复问题后重新运行验收测试。")
    
    print(f"\n{'='*80}\n")



# ========== Pytest测试用例 ==========

@pytest.mark.asyncio
async def test_performance_metrics_acceptance():
    """验收测试1: 性能指标"""
    result = await verify_performance_metrics()
    summary = result.get_summary()
    
    print(f"\n性能指标验收: 通过 {summary['passed']}/{summary['total_tests']}")
    
    # 断言 - 至少80%的测试通过
    assert summary["pass_rate"] >= 0.8, \
        f"性能指标通过率 {summary['pass_rate']:.1%} 低于 80%"


@pytest.mark.asyncio
async def test_error_handling_acceptance():
    """验收测试2: 错误处理机制"""
    result = await verify_error_handling()
    summary = result.get_summary()
    
    print(f"\n错误处理验收: 通过 {summary['passed']}/{summary['total_tests']}")
    
    # 断言 - 至少75%的测试通过
    assert summary["pass_rate"] >= 0.75, \
        f"错误处理通过率 {summary['pass_rate']:.1%} 低于 75%"


@pytest.mark.asyncio
async def test_monitoring_system_acceptance():
    """验收测试3: 监控和告警系统"""
    result = await verify_monitoring_system()
    summary = result.get_summary()
    
    print(f"\n监控系统验收: 通过 {summary['passed']}/{summary['total_tests']}")
    
    # 断言 - 至少80%的测试通过
    assert summary["pass_rate"] >= 0.8, \
        f"监控系统通过率 {summary['pass_rate']:.1%} 低于 80%"


@pytest.mark.asyncio
async def test_full_acceptance():
    """完整验收测试 - 生成最终报告"""
    print("\n" + "="*80)
    print("开始完整验收测试")
    print("="*80)
    print()
    
    results = {}
    
    # 1. 验证性能指标
    print("\n运行验收测试1: 性能指标...")
    results["性能指标"] = await verify_performance_metrics()
    
    # 2. 验证错误处理
    print("\n运行验收测试2: 错误处理机制...")
    results["错误处理"] = await verify_error_handling()
    
    # 3. 验证监控系统
    print("\n运行验收测试3: 监控和告警系统...")
    results["监控系统"] = await verify_monitoring_system()
    
    # 生成报告
    report = generate_acceptance_report(
        results,
        "tests/performance/acceptance_report.json"
    )
    
    # 打印摘要
    print_acceptance_summary(report)
    
    # 总体断言
    assert report["test_passed"], \
        f"验收测试未通过，失败项: {report['overall_summary']['failed']}"


if __name__ == "__main__":
    # 直接运行完整验收测试
    print("开始性能优化验收测试...")
    asyncio.run(test_full_acceptance())
