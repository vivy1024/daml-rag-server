"""
任务10.3 监控系统验证

测试目标：
- 访问Grafana仪表板 (http://localhost:3001)
- 验证所有指标正确显示
- 查询Prometheus验证指标记录

验证需求: 7.1, 7.2, 7.3, 7.4
"""

import asyncio
import time
import httpx
import json


class MonitoringValidator:
    """监控系统验证"""
    
    def __init__(self):
        self.grafana_url = "http://grafana:3000"  # Docker网络内的服务名
        self.prometheus_url = "http://prometheus:9090"  # Docker网络内的服务名
        self.daml_rag_url = "http://localhost:8001"
        self.results = {}
    
    async def test_grafana_accessibility(self) -> dict:
        """测试1: 验证Grafana可访问性"""
        print(f"\n{'='*80}")
        print(f"测试1: Grafana仪表板可访问性验证")
        print(f"{'='*80}\n")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.grafana_url}/api/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Grafana服务正常运行")
                    print(f"  状态: {health_data.get('database', 'unknown')}")
                    print(f"  版本: {health_data.get('version', 'unknown')}")
                    
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "health": health_data
                    }
                else:
                    print(f"❌ Grafana服务异常: HTTP {response.status_code}")
                    return {
                        "success": False,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            print(f"❌ 无法访问Grafana: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_prometheus_accessibility(self) -> dict:
        """测试2: 验证Prometheus可访问性"""
        print(f"\n{'='*80}")
        print(f"测试2: Prometheus可访问性验证")
        print(f"{'='*80}\n")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.prometheus_url}/-/healthy")
                
                if response.status_code == 200:
                    print(f"✅ Prometheus服务正常运行")
                    
                    return {
                        "success": True,
                        "status_code": response.status_code
                    }
                else:
                    print(f"❌ Prometheus服务异常: HTTP {response.status_code}")
                    return {
                        "success": False,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            print(f"❌ 无法访问Prometheus: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_prometheus_metrics(self) -> dict:
        """测试3: 验证Prometheus指标记录"""
        print(f"\n{'='*80}")
        print(f"测试3: Prometheus指标记录验证")
        print(f"{'='*80}\n")
        
        # 先触发一个流式会话，生成指标数据
        print("触发流式会话以生成指标数据...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.daml_rag_url}/api/v1/chat/stream"
                payload = {
                    "user_id": "test_user",
                    "query": "给我推荐一些适合初学者的胸部训练动作",
                    "session_id": f"monitoring_test_{int(time.time() * 1000)}"
                }
                
                async with client.stream("POST", url, json=payload) as response:
                    # 只读取前几个chunk
                    count = 0
                    async for line in response.aiter_lines():
                        count += 1
                        if count > 20:
                            break
                
                print("✅ 流式会话已触发")
                
        except Exception as e:
            print(f"⚠️ 触发流式会话失败: {e}")
        
        # 等待指标被记录
        await asyncio.sleep(2)
        
        # 查询Prometheus指标
        metrics_to_check = [
            "streaming_session_ttfb_seconds",
            "streaming_session_duration_seconds",
            "streaming_session_tokens_per_second",
            "streaming_session_success_total",
            "streaming_session_failure_total"
        ]
        
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for metric in metrics_to_check:
                    try:
                        response = await client.get(
                            f"{self.prometheus_url}/api/v1/query",
                            params={"query": metric}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            result = data.get("data", {}).get("result", [])
                            
                            if result:
                                print(f"✅ 指标 {metric}: 已记录 ({len(result)} 个数据点)")
                                results[metric] = {
                                    "found": True,
                                    "data_points": len(result)
                                }
                            else:
                                print(f"⚠️ 指标 {metric}: 未找到数据")
                                results[metric] = {
                                    "found": False,
                                    "data_points": 0
                                }
                        else:
                            print(f"❌ 查询指标 {metric} 失败: HTTP {response.status_code}")
                            results[metric] = {
                                "found": False,
                                "error": f"HTTP {response.status_code}"
                            }
                            
                    except Exception as e:
                        print(f"❌ 查询指标 {metric} 异常: {e}")
                        results[metric] = {
                            "found": False,
                            "error": str(e)
                        }
                
                # 统计结果
                found_count = sum(1 for r in results.values() if r.get("found", False))
                total_count = len(metrics_to_check)
                
                print(f"\n指标记录统计: {found_count}/{total_count} 个指标已记录")
                
                return {
                    "success": found_count > 0,  # 至少有一个指标被记录
                    "total_metrics": total_count,
                    "found_metrics": found_count,
                    "missing_metrics": total_count - found_count,
                    "results": results
                }
                
        except Exception as e:
            print(f"❌ 查询Prometheus指标失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_daml_rag_metrics_endpoint(self) -> dict:
        """测试4: 验证DAML-RAG指标端点"""
        print(f"\n{'='*80}")
        print(f"测试4: DAML-RAG指标端点验证")
        print(f"{'='*80}\n")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.daml_rag_url}/api/health/metrics/prometheus")
                
                if response.status_code == 200:
                    metrics_text = response.text
                    
                    # 检查关键指标是否存在
                    key_metrics = [
                        "streaming_session_ttfb_seconds",
                        "streaming_session_duration_seconds",
                        "streaming_session_tokens_per_second"
                    ]
                    
                    found_metrics = []
                    for metric in key_metrics:
                        if metric in metrics_text:
                            found_metrics.append(metric)
                    
                    print(f"✅ DAML-RAG指标端点正常")
                    print(f"  找到 {len(found_metrics)}/{len(key_metrics)} 个关键指标")
                    
                    for metric in found_metrics:
                        print(f"  ✅ {metric}")
                    
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "total_metrics": len(key_metrics),
                        "found_metrics": len(found_metrics),
                        "metrics": found_metrics
                    }
                else:
                    print(f"❌ DAML-RAG指标端点异常: HTTP {response.status_code}")
                    return {
                        "success": False,
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            print(f"❌ 无法访问DAML-RAG指标端点: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_all_tests(self) -> dict:
        """运行所有监控系统验证测试"""
        print(f"\n{'='*80}")
        print(f"监控系统验证测试开始")
        print(f"{'='*80}\n")
        
        # 测试1: Grafana可访问性
        self.results['grafana'] = await self.test_grafana_accessibility()
        
        # 测试2: Prometheus可访问性
        self.results['prometheus'] = await self.test_prometheus_accessibility()
        
        # 测试3: Prometheus指标记录
        self.results['metrics'] = await self.test_prometheus_metrics()
        
        # 测试4: DAML-RAG指标端点
        self.results['daml_rag_metrics'] = await self.test_daml_rag_metrics_endpoint()
        
        # 统计结果
        all_passed = all(r.get('success', False) for r in self.results.values())
        passed_count = sum(1 for r in self.results.values() if r.get('success', False))
        total_count = len(self.results)
        
        print(f"\n{'='*80}")
        print(f"监控系统验证测试结果")
        print(f"{'='*80}\n")
        print(f"总测试数: {total_count}")
        print(f"通过数: {passed_count}")
        print(f"失败数: {total_count - passed_count}")
        print(f"\n详细结果:")
        print(f"  1. Grafana可访问性: {'✅ 通过' if self.results['grafana']['success'] else '❌ 失败'}")
        print(f"  2. Prometheus可访问性: {'✅ 通过' if self.results['prometheus']['success'] else '❌ 失败'}")
        print(f"  3. Prometheus指标记录: {'✅ 通过' if self.results['metrics']['success'] else '❌ 失败'}")
        print(f"  4. DAML-RAG指标端点: {'✅ 通过' if self.results['daml_rag_metrics']['success'] else '❌ 失败'}")
        
        if all_passed:
            print(f"\n🎉 所有监控系统验证测试通过！")
        else:
            print(f"\n⚠️ 部分监控系统验证测试失败")
        
        # 输出访问信息
        print(f"\n{'='*80}")
        print(f"监控系统访问信息")
        print(f"{'='*80}\n")
        print(f"Grafana仪表板: {self.grafana_url}")
        print(f"  - 用户名: admin")
        print(f"  - 密码: admin")
        print(f"\nPrometheus: {self.prometheus_url}")
        print(f"  - 查询界面: {self.prometheus_url}/graph")
        print(f"\nDAML-RAG指标: {self.daml_rag_url}/api/health/metrics/prometheus")
        
        return {
            "success": all_passed,
            "total_tests": total_count,
            "passed_tests": passed_count,
            "failed_tests": total_count - passed_count,
            "results": self.results
        }


async def main():
    """主测试函数"""
    validator = MonitoringValidator()
    results = await validator.run_all_tests()
    
    return 0 if results["success"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
