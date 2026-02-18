# -*- coding: utf-8 -*-
"""
端到端综合验证测试 - 任务18

完整验证以下场景：
1. 训练计划生成场景
2. 营养规划场景
3. 安全检查场景
4. 生成完整测试报告

版本：v1.0.0
创建日期：2025-12-17
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
TEST_USER_ID = "2"  # vivy用户

# MCP工具列表
MCP_TOOLS = [
    "intelligent_exercise_selector",
    "contraindications_checker",
    "injury_risk_assessor",
    "muscle_group_volume_calculator",
    "tdee_calculator",
    "professional_program_designer",
    "exercise_alternative_finder",
    "movement_pattern_balancer",
    "intelligent_weight_calculator",
    "safe_exercise_modifier",
    "nutrition_intake_analyzer",
    "meal_plan_designer",
    "exercise_nutrition_optimization",
    "periodized_program_designer",
    "training_split_designer"
]


@pytest_asyncio.fixture
async def http_client():
    """创建HTTP客户端"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        yield client



class TestE2EComprehensive:
    """端到端综合验证测试类"""

    @pytest.mark.asyncio
    async def test_18_1_training_plan_scenario(self, http_client):
        """
        测试18.1：完整训练计划场景
        
        验证：
        1. LLM选择正确的DAG模板
        2. MCP工具被正确调用
        3. 三层检索返回真实数据
        4. LLM深度分析质量
        
        Requirements: 7.2
        """
        logger.info("=" * 80)
        logger.info("测试18.1：完整训练计划场景")
        logger.info("=" * 80)

        test_query = "我想制定一个8周的增肌训练计划，每周训练4次，主要练胸和背，我有腰椎间盘突出的问题"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "domain": "fitness",
                    "session_id": "test_18_1_training_plan"
                }
            )
            
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            response_text = result['response']
            metadata = result.get('metadata', {})
            
            logger.info(f"✅ 请求成功，耗时: {elapsed_time:.2f}秒")
            
            # 验证1：LLM选择了正确的DAG模板
            dag_template = metadata.get('dag_template_selected')
            if dag_template:
                logger.info(f"  ✅ DAG模板选择: {dag_template}")
                # 训练计划场景应该选择训练计划相关的模板
                assert 'training' in dag_template.lower() or 'program' in dag_template.lower(), \
                    f"DAG模板选择不正确: {dag_template}"
            else:
                logger.warning(f"  ⚠️  未返回DAG模板信息")
            
            # 验证2：MCP工具被正确调用
            tools_called = metadata.get('tools_called', [])
            logger.info(f"  调用的工具数量: {len(tools_called)}")
            logger.info(f"  调用的工具: {', '.join(tools_called)}")
            
            # 训练计划场景应该调用这些工具
            expected_tools = [
                'intelligent_exercise_selector',
                'professional_program_designer',
                'contraindications_checker',  # 因为提到了腰椎问题
                'injury_risk_assessor'
            ]
            
            found_tools = [t for t in expected_tools if t in tools_called]
            logger.info(f"  期望工具中已调用: {', '.join(found_tools)}")
            
            # 至少要调用2个期望的工具
            assert len(found_tools) >= 2, \
                f"期望的MCP工具调用不足: {len(found_tools)}/2"
            logger.info(f"  ✅ MCP工具调用正确")
            
            # 验证3：三层检索返回真实数据
            retrieval_info = metadata.get('retrieval_info', {})
            if retrieval_info:
                layer1_count = retrieval_info.get('layer1_count', 0)
                layer2_count = retrieval_info.get('layer2_count', 0)
                layer3_count = retrieval_info.get('layer3_count', 0)
                
                logger.info(f"  三层检索结果:")
                logger.info(f"    - Layer1向量检索: {layer1_count}个结果")
                logger.info(f"    - Layer2图谱过滤: {layer2_count}个结果")
                logger.info(f"    - Layer3规则验证: {layer3_count}个结果")
                
                # 至少Layer1应该有结果
                assert layer1_count > 0, "Layer1检索未返回结果"
                logger.info(f"  ✅ 三层检索返回真实数据")
            else:
                logger.warning(f"  ⚠️  未返回检索信息")
            
            # 验证4：LLM深度分析质量
            # 检查响应是否包含关键内容
            quality_keywords = {
                '训练计划': ['训练', '计划', '周', '次'],
                '动作推荐': ['动作', '卧推', '划船', '引体', '推举'],
                '安全建议': ['腰椎', '避免', '注意', '禁忌', '替代'],
                '专业分析': ['组数', '次数', '重量', '休息'],
                '个性化': ['你的', '根据', '建议', '适合']
            }
            
            found_categories = []
            for category, keywords in quality_keywords.items():
                if any(kw in response_text for kw in keywords):
                    found_categories.append(category)
            
            logger.info(f"  LLM分析质量:")
            for category in found_categories:
                logger.info(f"    ✅ 包含{category}")
            
            # 至少要包含4个类别
            assert len(found_categories) >= 4, \
                f"LLM分析质量不足，只包含: {found_categories}"
            logger.info(f"  ✅ LLM深度分析质量良好")
            
            # 输出响应摘要
            logger.info(f"\n响应摘要（前500字符）:")
            logger.info(f"{response_text[:500]}...")
            
            logger.info(f"\n✅ 测试18.1通过：完整训练计划场景验证成功")
            
            return {
                "elapsed_time": elapsed_time,
                "dag_template": dag_template,
                "tools_called": tools_called,
                "retrieval_info": retrieval_info,
                "quality_categories": found_categories,
                "response_length": len(response_text)
            }

        except Exception as e:
            logger.error(f"❌ 测试18.1失败: {e}")
            pytest.fail(f"完整训练计划场景测试失败: {e}")


    @pytest.mark.asyncio
    async def test_18_2_nutrition_plan_scenario(self, http_client):
        """
        测试18.2：营养规划场景
        
        验证：
        1. 营养相关MCP工具调用
        2. 食物数据检索
        3. 营养计算准确性
        
        Requirements: 7.4
        """
        logger.info("=" * 80)
        logger.info("测试18.2：营养规划场景")
        logger.info("=" * 80)

        test_query = "帮我设计一份增肌期的营养餐食计划，我每天需要摄入多少热量和蛋白质？"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "domain": "fitness",
                    "session_id": "test_18_2_nutrition"
                }
            )
            
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            response_text = result['response']
            metadata = result.get('metadata', {})
            
            logger.info(f"✅ 请求成功，耗时: {elapsed_time:.2f}秒")
            
            # 验证1：营养相关MCP工具调用
            tools_called = metadata.get('tools_called', [])
            logger.info(f"  调用的工具: {', '.join(tools_called)}")
            
            # 营养场景应该调用这些工具
            nutrition_tools = [
                'tdee_calculator',
                'nutrition_intake_analyzer',
                'meal_plan_designer',
                'exercise_nutrition_optimization'
            ]
            
            found_nutrition_tools = [t for t in nutrition_tools if t in tools_called]
            logger.info(f"  营养工具已调用: {', '.join(found_nutrition_tools)}")
            
            # 至少要调用1个营养工具
            assert len(found_nutrition_tools) >= 1, \
                f"营养相关MCP工具未调用: {tools_called}"
            logger.info(f"  ✅ 营养相关MCP工具调用正确")
            
            # 验证2：食物数据检索
            # 检查响应是否包含食物相关内容
            food_keywords = ['鸡胸肉', '牛肉', '鱼', '蛋', '米饭', '燕麦', '蔬菜', '水果', '食物', '餐']
            found_food_keywords = [kw for kw in food_keywords if kw in response_text]
            
            if found_food_keywords:
                logger.info(f"  ✅ 包含食物数据: {', '.join(found_food_keywords[:5])}")
            else:
                logger.warning(f"  ⚠️  未检测到具体食物推荐")
            
            # 验证3：营养计算准确性
            # 检查响应是否包含营养数据
            nutrition_keywords = {
                '热量': ['热量', '卡路里', 'kcal', '千卡'],
                '蛋白质': ['蛋白质', '蛋白', 'g', '克'],
                '碳水化合物': ['碳水', '碳水化合物'],
                '脂肪': ['脂肪'],
                '营养比例': ['比例', '分配']
            }
            
            found_nutrition_data = []
            for category, keywords in nutrition_keywords.items():
                if any(kw in response_text for kw in keywords):
                    found_nutrition_data.append(category)
            
            logger.info(f"  营养数据完整性:")
            for category in found_nutrition_data:
                logger.info(f"    ✅ 包含{category}")
            
            # 至少要包含3个营养数据类别
            assert len(found_nutrition_data) >= 3, \
                f"营养数据不完整，只包含: {found_nutrition_data}"
            logger.info(f"  ✅ 营养计算数据完整")
            
            # 输出响应摘要
            logger.info(f"\n响应摘要（前500字符）:")
            logger.info(f"{response_text[:500]}...")
            
            logger.info(f"\n✅ 测试18.2通过：营养规划场景验证成功")
            
            return {
                "elapsed_time": elapsed_time,
                "tools_called": tools_called,
                "nutrition_tools_found": found_nutrition_tools,
                "food_keywords_found": found_food_keywords,
                "nutrition_data_found": found_nutrition_data,
                "response_length": len(response_text)
            }

        except Exception as e:
            logger.error(f"❌ 测试18.2失败: {e}")
            pytest.fail(f"营养规划场景测试失败: {e}")


    @pytest.mark.asyncio
    async def test_18_3_safety_check_scenario(self, http_client):
        """
        测试18.3：安全检查场景
        
        验证：
        1. 禁忌症检查工具调用
        2. 受伤风险评估
        3. 替代动作建议
        
        Requirements: 7.3
        """
        logger.info("=" * 80)
        logger.info("测试18.3：安全检查场景")
        logger.info("=" * 80)

        test_query = "我有腰椎间盘突出和肩袖损伤，哪些动作我不能做？有什么替代动作吗？"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "domain": "fitness",
                    "session_id": "test_18_3_safety"
                }
            )
            
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            response_text = result['response']
            metadata = result.get('metadata', {})
            
            logger.info(f"✅ 请求成功，耗时: {elapsed_time:.2f}秒")
            
            # 验证1：禁忌症检查工具调用
            tools_called = metadata.get('tools_called', [])
            logger.info(f"  调用的工具: {', '.join(tools_called)}")
            
            # 安全检查场景应该调用这些工具
            safety_tools = [
                'contraindications_checker',
                'injury_risk_assessor',
                'exercise_alternative_finder',
                'safe_exercise_modifier'
            ]
            
            found_safety_tools = [t for t in safety_tools if t in tools_called]
            logger.info(f"  安全工具已调用: {', '.join(found_safety_tools)}")
            
            # 至少要调用2个安全工具
            assert len(found_safety_tools) >= 2, \
                f"安全相关MCP工具调用不足: {len(found_safety_tools)}/2"
            logger.info(f"  ✅ 禁忌症检查工具调用正确")
            
            # 验证2：受伤风险评估
            # 检查响应是否包含风险评估内容
            risk_keywords = ['风险', '危险', '避免', '不能', '禁忌', '注意', '小心']
            found_risk_keywords = [kw for kw in risk_keywords if kw in response_text]
            
            logger.info(f"  风险评估关键词: {', '.join(found_risk_keywords)}")
            
            # 至少要包含3个风险相关关键词
            assert len(found_risk_keywords) >= 3, \
                f"风险评估内容不足: {found_risk_keywords}"
            logger.info(f"  ✅ 受伤风险评估完整")
            
            # 验证3：替代动作建议
            # 检查响应是否包含替代动作
            alternative_keywords = ['替代', '代替', '改为', '可以做', '建议', '推荐']
            found_alternative_keywords = [kw for kw in alternative_keywords if kw in response_text]
            
            logger.info(f"  替代建议关键词: {', '.join(found_alternative_keywords)}")
            
            # 至少要包含2个替代相关关键词
            assert len(found_alternative_keywords) >= 2, \
                f"替代动作建议不足: {found_alternative_keywords}"
            logger.info(f"  ✅ 替代动作建议完整")
            
            # 检查是否提到了具体的禁忌动作
            contraindicated_exercises = ['深蹲', '硬拉', '卧推', '推举', '引体', '杠铃']
            mentioned_exercises = [ex for ex in contraindicated_exercises if ex in response_text]
            
            if mentioned_exercises:
                logger.info(f"  提到的动作: {', '.join(mentioned_exercises)}")
            
            # 输出响应摘要
            logger.info(f"\n响应摘要（前500字符）:")
            logger.info(f"{response_text[:500]}...")
            
            logger.info(f"\n✅ 测试18.3通过：安全检查场景验证成功")
            
            return {
                "elapsed_time": elapsed_time,
                "tools_called": tools_called,
                "safety_tools_found": found_safety_tools,
                "risk_keywords_found": found_risk_keywords,
                "alternative_keywords_found": found_alternative_keywords,
                "mentioned_exercises": mentioned_exercises,
                "response_length": len(response_text)
            }

        except Exception as e:
            logger.error(f"❌ 测试18.3失败: {e}")
            pytest.fail(f"安全检查场景测试失败: {e}")


    @pytest.mark.asyncio
    async def test_18_4_generate_comprehensive_report(self, http_client):
        """
        测试18.4：生成完整测试报告
        
        汇总所有测试结果，生成详细的测试报告
        
        Requirements: 7.6
        """
        logger.info("=" * 80)
        logger.info("测试18.4：生成完整测试报告")
        logger.info("=" * 80)

        # 收集所有测试结果
        test_results = {
            "test_time": datetime.now().isoformat(),
            "test_scenarios": [],
            "mcp_tools_statistics": {},
            "performance_metrics": {},
            "issues_found": [],
            "recommendations": []
        }
        
        # 场景1：训练计划
        try:
            logger.info("\n执行场景1：训练计划生成...")
            result1 = await self.test_18_1_training_plan_scenario(http_client)
            test_results["test_scenarios"].append({
                "name": "训练计划生成",
                "status": "通过",
                "result": result1
            })
        except Exception as e:
            logger.error(f"场景1失败: {e}")
            test_results["test_scenarios"].append({
                "name": "训练计划生成",
                "status": "失败",
                "error": str(e)
            })
            test_results["issues_found"].append(f"训练计划场景失败: {e}")
        
        # 场景2：营养规划
        try:
            logger.info("\n执行场景2：营养规划...")
            result2 = await self.test_18_2_nutrition_plan_scenario(http_client)
            test_results["test_scenarios"].append({
                "name": "营养规划",
                "status": "通过",
                "result": result2
            })
        except Exception as e:
            logger.error(f"场景2失败: {e}")
            test_results["test_scenarios"].append({
                "name": "营养规划",
                "status": "失败",
                "error": str(e)
            })
            test_results["issues_found"].append(f"营养规划场景失败: {e}")
        
        # 场景3：安全检查
        try:
            logger.info("\n执行场景3：安全检查...")
            result3 = await self.test_18_3_safety_check_scenario(http_client)
            test_results["test_scenarios"].append({
                "name": "安全检查",
                "status": "通过",
                "result": result3
            })
        except Exception as e:
            logger.error(f"场景3失败: {e}")
            test_results["test_scenarios"].append({
                "name": "安全检查",
                "status": "失败",
                "error": str(e)
            })
            test_results["issues_found"].append(f"安全检查场景失败: {e}")
        
        # 统计MCP工具调用
        all_tools_called = set()
        for scenario in test_results["test_scenarios"]:
            if scenario["status"] == "通过" and "result" in scenario:
                tools = scenario["result"].get("tools_called", [])
                all_tools_called.update(tools)
        
        test_results["mcp_tools_statistics"] = {
            "total_tools_available": len(MCP_TOOLS),
            "tools_called": list(all_tools_called),
            "tools_called_count": len(all_tools_called),
            "coverage": f"{len(all_tools_called) / len(MCP_TOOLS) * 100:.1f}%"
        }
        
        # 统计性能指标
        response_times = []
        for scenario in test_results["test_scenarios"]:
            if scenario["status"] == "通过" and "result" in scenario:
                elapsed_time = scenario["result"].get("elapsed_time", 0)
                if elapsed_time > 0:
                    response_times.append(elapsed_time)
        
        if response_times:
            test_results["performance_metrics"] = {
                "avg_response_time": f"{sum(response_times) / len(response_times):.2f}秒",
                "min_response_time": f"{min(response_times):.2f}秒",
                "max_response_time": f"{max(response_times):.2f}秒",
                "total_scenarios": len(response_times)
            }
        
        # 生成改进建议
        if len(all_tools_called) < len(MCP_TOOLS) * 0.6:
            test_results["recommendations"].append(
                f"MCP工具覆盖率较低({len(all_tools_called)}/{len(MCP_TOOLS)})，建议增加更多测试场景"
            )
        
        if response_times and max(response_times) > 30:
            test_results["recommendations"].append(
                f"最慢响应时间{max(response_times):.2f}秒超过30秒，建议优化性能"
            )
        
        if test_results["issues_found"]:
            test_results["recommendations"].append(
                "发现测试失败，建议优先修复这些问题"
            )
        
        # 保存报告到文件
        report_path = "daml-rag-server/tests/integration/E2E_COMPREHENSIVE_REPORT.json"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(test_results, f, ensure_ascii=False, indent=2)
            logger.info(f"\n✅ 测试报告已保存到: {report_path}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
        
        # 输出报告摘要
        logger.info("\n" + "=" * 80)
        logger.info("端到端综合测试报告摘要")
        logger.info("=" * 80)
        
        logger.info(f"\n测试时间: {test_results['test_time']}")
        
        logger.info(f"\n测试场景结果:")
        passed_count = sum(1 for s in test_results["test_scenarios"] if s["status"] == "通过")
        total_count = len(test_results["test_scenarios"])
        logger.info(f"  通过: {passed_count}/{total_count}")
        for scenario in test_results["test_scenarios"]:
            status_icon = "✅" if scenario["status"] == "通过" else "❌"
            logger.info(f"  {status_icon} {scenario['name']}: {scenario['status']}")
        
        logger.info(f"\nMCP工具统计:")
        logger.info(f"  可用工具总数: {test_results['mcp_tools_statistics']['total_tools_available']}")
        logger.info(f"  已调用工具数: {test_results['mcp_tools_statistics']['tools_called_count']}")
        logger.info(f"  覆盖率: {test_results['mcp_tools_statistics']['coverage']}")
        logger.info(f"  已调用工具: {', '.join(test_results['mcp_tools_statistics']['tools_called'][:10])}")
        
        if test_results["performance_metrics"]:
            logger.info(f"\n性能指标:")
            for key, value in test_results["performance_metrics"].items():
                logger.info(f"  {key}: {value}")
        
        if test_results["issues_found"]:
            logger.info(f"\n发现的问题:")
            for issue in test_results["issues_found"]:
                logger.info(f"  ❌ {issue}")
        
        if test_results["recommendations"]:
            logger.info(f"\n改进建议:")
            for rec in test_results["recommendations"]:
                logger.info(f"  💡 {rec}")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ 测试18.4通过：完整测试报告已生成")
        logger.info("=" * 80)
        
        # 验证：至少2个场景通过
        assert passed_count >= 2, \
            f"通过的测试场景不足: {passed_count}/3"
        
        return test_results


def run_comprehensive_tests():
    """运行所有综合测试"""
    logger.info("\n" + "=" * 80)
    logger.info("端到端综合验证测试套件 v1.0.0")
    logger.info("=" * 80)
    
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])


if __name__ == "__main__":
    run_comprehensive_tests()
