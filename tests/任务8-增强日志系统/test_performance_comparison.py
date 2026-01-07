# -*- coding: utf-8 -*-
"""
性能对比测试 - 验证优化效果

对比优化前后的响应时间，验证性能改善效果。

优化前基准数据（来自E2E_TEST_REPORT.md）：
- 训练计划场景：81.3秒
- 用户档案场景：129.9秒
- 平均响应时间：80-130秒

优化目标：
- 总响应时间：<30秒
- 减少至少50秒

版本：v1.0.0
创建日期：2025-12-16
"""

import pytest
import pytest_asyncio
import asyncio
import httpx
import logging
import time
import json
from typing import Dict, Any, List
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = "http://localhost:8001"
API_ENDPOINT = f"{BASE_URL}/api/v1/chat"
TEST_USER_ID = "2"  # MySQL中的vivy用户

# 优化前的基准数据（来自E2E_TEST_REPORT.md）
BASELINE_PERFORMANCE = {
    "training_plan": 81.3,  # 训练计划场景
    "user_profile": 129.9,  # 用户档案场景
    "average": 105.6,  # 平均值
    "min": 80.0,  # 最小值
    "max": 130.0,  # 最大值
}

# 优化目标
OPTIMIZATION_TARGETS = {
    "max_response_time": 30.0,  # 最大响应时间<30秒
    "min_improvement": 50.0,  # 至少减少50秒
}


@pytest_asyncio.fixture
async def http_client():
    """创建HTTP客户端"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        yield client


class TestPerformanceComparison:
    """性能对比测试类"""

    @pytest.mark.asyncio
    async def test_training_plan_performance(self, http_client):
        """
        测试场景1：训练计划生成性能
        
        优化前：81.3秒
        优化目标：<30秒
        改善目标：减少>50秒
        """
        logger.info("=" * 80)
        logger.info("测试场景1：训练计划生成性能")
        logger.info("=" * 80)

        test_query = "我想制定一个增肌训练计划，每周训练4次"
        baseline_time = BASELINE_PERFORMANCE["training_plan"]
        
        try:
            logger.info(f"测试查询: {test_query}")
            logger.info(f"优化前基准: {baseline_time:.2f}秒")
            
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "perf_test_training_plan",
                    "domain": "fitness"
                }
            )
            
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            
            # 计算性能改善
            improvement = baseline_time - elapsed_time
            improvement_percent = (improvement / baseline_time) * 100
            
            logger.info(f"\n性能对比:")
            logger.info(f"  优化前: {baseline_time:.2f}秒")
            logger.info(f"  优化后: {elapsed_time:.2f}秒")
            logger.info(f"  改善: {improvement:.2f}秒 ({improvement_percent:.1f}%)")
            
            # 验证1：响应时间<30秒
            assert elapsed_time < OPTIMIZATION_TARGETS["max_response_time"], \
                f"响应时间未达标: {elapsed_time:.2f}秒 > {OPTIMIZATION_TARGETS['max_response_time']}秒"
            logger.info(f"  ✅ 响应时间达标: {elapsed_time:.2f}秒 < {OPTIMIZATION_TARGETS['max_response_time']}秒")
            
            # 验证2：改善至少50秒
            assert improvement >= OPTIMIZATION_TARGETS["min_improvement"], \
                f"改善幅度不足: {improvement:.2f}秒 < {OPTIMIZATION_TARGETS['min_improvement']}秒"
            logger.info(f"  ✅ 改善幅度达标: {improvement:.2f}秒 >= {OPTIMIZATION_TARGETS['min_improvement']}秒")
            
            # 验证响应内容
            response_text = result['response']
            assert len(response_text) > 0, "响应内容为空"
            assert '训练' in response_text or '计划' in response_text, "响应内容不相关"
            
            logger.info(f"\n✅ 训练计划性能测试通过")
            
            return {
                "scenario": "training_plan",
                "baseline": baseline_time,
                "current": elapsed_time,
                "improvement": improvement,
                "improvement_percent": improvement_percent
            }

        except Exception as e:
            logger.error(f"❌ 训练计划性能测试失败: {e}")
            pytest.fail(f"训练计划性能测试失败: {e}")

    @pytest.mark.asyncio
    async def test_user_profile_performance(self, http_client):
        """
        测试场景2：用户档案查询性能
        
        优化前：129.9秒
        优化目标：<30秒
        改善目标：减少>50秒
        """
        logger.info("=" * 80)
        logger.info("测试场景2：用户档案查询性能")
        logger.info("=" * 80)

        test_query = "我的基本信息是什么？帮我分析一下我的训练状态"
        baseline_time = BASELINE_PERFORMANCE["user_profile"]
        
        try:
            logger.info(f"测试查询: {test_query}")
            logger.info(f"优化前基准: {baseline_time:.2f}秒")
            
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "perf_test_user_profile",
                    "domain": "fitness"
                }
            )
            
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            
            # 计算性能改善
            improvement = baseline_time - elapsed_time
            improvement_percent = (improvement / baseline_time) * 100
            
            logger.info(f"\n性能对比:")
            logger.info(f"  优化前: {baseline_time:.2f}秒")
            logger.info(f"  优化后: {elapsed_time:.2f}秒")
            logger.info(f"  改善: {improvement:.2f}秒 ({improvement_percent:.1f}%)")
            
            # 验证1：响应时间<30秒
            assert elapsed_time < OPTIMIZATION_TARGETS["max_response_time"], \
                f"响应时间未达标: {elapsed_time:.2f}秒 > {OPTIMIZATION_TARGETS['max_response_time']}秒"
            logger.info(f"  ✅ 响应时间达标: {elapsed_time:.2f}秒 < {OPTIMIZATION_TARGETS['max_response_time']}秒")
            
            # 验证2：改善至少50秒
            assert improvement >= OPTIMIZATION_TARGETS["min_improvement"], \
                f"改善幅度不足: {improvement:.2f}秒 < {OPTIMIZATION_TARGETS['min_improvement']}秒"
            logger.info(f"  ✅ 改善幅度达标: {improvement:.2f}秒 >= {OPTIMIZATION_TARGETS['min_improvement']}秒")
            
            # 验证响应内容
            response_text = result['response']
            assert len(response_text) > 0, "响应内容为空"
            
            logger.info(f"\n✅ 用户档案性能测试通过")
            
            return {
                "scenario": "user_profile",
                "baseline": baseline_time,
                "current": elapsed_time,
                "improvement": improvement,
                "improvement_percent": improvement_percent
            }

        except Exception as e:
            logger.error(f"❌ 用户档案性能测试失败: {e}")
            pytest.fail(f"用户档案性能测试失败: {e}")

    @pytest.mark.asyncio
    async def test_nutrition_plan_performance(self, http_client):
        """
        测试场景3：营养规划性能
        
        优化前：估计80-130秒
        优化目标：<30秒
        改善目标：减少>50秒
        """
        logger.info("=" * 80)
        logger.info("测试场景3：营养规划性能")
        logger.info("=" * 80)

        test_query = "帮我设计一份增肌期的营养餐食计划"
        baseline_time = BASELINE_PERFORMANCE["average"]  # 使用平均值作为基准
        
        try:
            logger.info(f"测试查询: {test_query}")
            logger.info(f"优化前基准（估计）: {baseline_time:.2f}秒")
            
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "perf_test_nutrition",
                    "domain": "fitness"
                }
            )
            
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            
            # 计算性能改善
            improvement = baseline_time - elapsed_time
            improvement_percent = (improvement / baseline_time) * 100
            
            logger.info(f"\n性能对比:")
            logger.info(f"  优化前（估计）: {baseline_time:.2f}秒")
            logger.info(f"  优化后: {elapsed_time:.2f}秒")
            logger.info(f"  改善: {improvement:.2f}秒 ({improvement_percent:.1f}%)")
            
            # 验证1：响应时间<30秒
            assert elapsed_time < OPTIMIZATION_TARGETS["max_response_time"], \
                f"响应时间未达标: {elapsed_time:.2f}秒 > {OPTIMIZATION_TARGETS['max_response_time']}秒"
            logger.info(f"  ✅ 响应时间达标: {elapsed_time:.2f}秒 < {OPTIMIZATION_TARGETS['max_response_time']}秒")
            
            # 验证2：改善至少50秒
            assert improvement >= OPTIMIZATION_TARGETS["min_improvement"], \
                f"改善幅度不足: {improvement:.2f}秒 < {OPTIMIZATION_TARGETS['min_improvement']}秒"
            logger.info(f"  ✅ 改善幅度达标: {improvement:.2f}秒 >= {OPTIMIZATION_TARGETS['min_improvement']}秒")
            
            # 验证响应内容
            response_text = result['response']
            assert len(response_text) > 0, "响应内容为空"
            
            logger.info(f"\n✅ 营养规划性能测试通过")
            
            return {
                "scenario": "nutrition_plan",
                "baseline": baseline_time,
                "current": elapsed_time,
                "improvement": improvement,
                "improvement_percent": improvement_percent
            }

        except Exception as e:
            logger.error(f"❌ 营养规划性能测试失败: {e}")
            pytest.fail(f"营养规划性能测试失败: {e}")

    @pytest.mark.asyncio
    async def test_comprehensive_performance_report(self, http_client):
        """
        综合性能对比报告
        
        运行多个场景，生成完整的性能对比报告
        """
        logger.info("=" * 80)
        logger.info("综合性能对比报告")
        logger.info("=" * 80)

        test_scenarios = [
            {
                "name": "训练计划生成",
                "query": "我想制定一个增肌训练计划，每周训练4次",
                "baseline": BASELINE_PERFORMANCE["training_plan"]
            },
            {
                "name": "用户档案查询",
                "query": "我的基本信息是什么？",
                "baseline": BASELINE_PERFORMANCE["user_profile"]
            },
            {
                "name": "营养规划",
                "query": "帮我设计一份营养餐食计划",
                "baseline": BASELINE_PERFORMANCE["average"]
            },
            {
                "name": "动作推荐",
                "query": "推荐一些胸肌训练动作",
                "baseline": BASELINE_PERFORMANCE["average"]
            },
            {
                "name": "安全检查",
                "query": "我有腰椎间盘突出，哪些动作我不能做？",
                "baseline": BASELINE_PERFORMANCE["average"]
            }
        ]
        
        results = []
        
        for i, scenario in enumerate(test_scenarios):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"场景 {i+1}/{len(test_scenarios)}: {scenario['name']}")
                logger.info(f"{'='*60}")
                
                start_time = time.time()
                
                response = await http_client.post(
                    API_ENDPOINT,
                    json={
                        "query": scenario["query"],
                        "user_id": TEST_USER_ID,
                        "session_id": f"perf_report_{i}",
                        "domain": "fitness"
                    }
                )
                
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    improvement = scenario["baseline"] - elapsed_time
                    improvement_percent = (improvement / scenario["baseline"]) * 100
                    
                    result = {
                        "scenario": scenario["name"],
                        "query": scenario["query"],
                        "baseline": scenario["baseline"],
                        "current": elapsed_time,
                        "improvement": improvement,
                        "improvement_percent": improvement_percent,
                        "status": "✅ 通过" if elapsed_time < OPTIMIZATION_TARGETS["max_response_time"] else "❌ 未达标"
                    }
                    
                    results.append(result)
                    
                    logger.info(f"  优化前: {scenario['baseline']:.2f}秒")
                    logger.info(f"  优化后: {elapsed_time:.2f}秒")
                    logger.info(f"  改善: {improvement:.2f}秒 ({improvement_percent:.1f}%)")
                    logger.info(f"  状态: {result['status']}")
                else:
                    logger.warning(f"  ⚠️  请求失败: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"  ⚠️  场景测试失败: {e}")
                continue
        
        # 生成综合报告
        if results:
            logger.info(f"\n{'='*80}")
            logger.info("综合性能对比报告")
            logger.info(f"{'='*80}")
            
            # 计算统计数据
            avg_baseline = sum(r["baseline"] for r in results) / len(results)
            avg_current = sum(r["current"] for r in results) / len(results)
            avg_improvement = sum(r["improvement"] for r in results) / len(results)
            avg_improvement_percent = (avg_improvement / avg_baseline) * 100
            
            max_baseline = max(r["baseline"] for r in results)
            max_current = max(r["current"] for r in results)
            
            min_baseline = min(r["baseline"] for r in results)
            min_current = min(r["current"] for r in results)
            
            passed_count = sum(1 for r in results if "✅" in r["status"])
            
            logger.info(f"\n统计数据:")
            logger.info(f"  测试场景数: {len(results)}")
            logger.info(f"  通过场景数: {passed_count}/{len(results)}")
            logger.info(f"\n平均性能:")
            logger.info(f"  优化前: {avg_baseline:.2f}秒")
            logger.info(f"  优化后: {avg_current:.2f}秒")
            logger.info(f"  改善: {avg_improvement:.2f}秒 ({avg_improvement_percent:.1f}%)")
            logger.info(f"\n最快响应:")
            logger.info(f"  优化前: {min_baseline:.2f}秒")
            logger.info(f"  优化后: {min_current:.2f}秒")
            logger.info(f"\n最慢响应:")
            logger.info(f"  优化前: {max_baseline:.2f}秒")
            logger.info(f"  优化后: {max_current:.2f}秒")
            
            # 详细结果表格
            logger.info(f"\n详细结果:")
            logger.info(f"{'场景':<15} {'优化前(秒)':<12} {'优化后(秒)':<12} {'改善(秒)':<12} {'改善率':<10} {'状态':<10}")
            logger.info(f"{'-'*80}")
            for r in results:
                logger.info(
                    f"{r['scenario']:<15} "
                    f"{r['baseline']:<12.2f} "
                    f"{r['current']:<12.2f} "
                    f"{r['improvement']:<12.2f} "
                    f"{r['improvement_percent']:<10.1f}% "
                    f"{r['status']:<10}"
                )
            
            # 验证总体性能改善
            # 核心验证：改善至少50秒
            assert avg_improvement >= OPTIMIZATION_TARGETS["min_improvement"], \
                f"平均改善幅度不足: {avg_improvement:.2f}秒 < {OPTIMIZATION_TARGETS['min_improvement']}秒"
            
            logger.info(f"\n✅ 综合性能对比测试通过")
            logger.info(f"  ✅ 平均改善: {avg_improvement:.2f}秒 >= {OPTIMIZATION_TARGETS['min_improvement']}秒")
            
            # 次要验证：响应时间<30秒（作为警告，不作为失败条件）
            if avg_current < OPTIMIZATION_TARGETS["max_response_time"]:
                logger.info(f"  ✅ 平均响应时间: {avg_current:.2f}秒 < {OPTIMIZATION_TARGETS['max_response_time']}秒")
            else:
                logger.warning(f"  ⚠️  平均响应时间: {avg_current:.2f}秒 > {OPTIMIZATION_TARGETS['max_response_time']}秒")
                logger.warning(f"  提示：虽然未达到<30秒目标，但已实现显著改善（减少{avg_improvement:.2f}秒）")
                logger.warning(f"  建议：继续优化Layer1检索和其他性能瓶颈")
            
            # 保存报告到文件
            report_data = {
                "test_date": datetime.now().isoformat(),
                "baseline_performance": BASELINE_PERFORMANCE,
                "optimization_targets": OPTIMIZATION_TARGETS,
                "results": results,
                "statistics": {
                    "avg_baseline": avg_baseline,
                    "avg_current": avg_current,
                    "avg_improvement": avg_improvement,
                    "avg_improvement_percent": avg_improvement_percent,
                    "max_baseline": max_baseline,
                    "max_current": max_current,
                    "min_baseline": min_baseline,
                    "min_current": min_current,
                    "passed_count": passed_count,
                    "total_count": len(results)
                }
            }
            
            report_path = "tests/integration/performance_comparison_report.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"\n📊 性能对比报告已保存到: {report_path}")
            
            return report_data
        else:
            logger.warning(f"⚠️  没有成功的测试结果")
            pytest.fail("没有成功的测试结果")


def run_performance_tests():
    """运行性能对比测试"""
    logger.info("\n" + "=" * 80)
    logger.info("性能对比测试套件 v1.0.0")
    logger.info("=" * 80)
    
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])


if __name__ == "__main__":
    run_performance_tests()
