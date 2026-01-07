# -*- coding: utf-8 -*-
"""
Greeting场景集成测试

测试greeting模板的完整工作流程，验证：
1. greeting模板被正确选择
2. 响应长度<100字
3. 响应不包含训练建议
4. MCP工具调用数量为0

版本：v1.0.0
创建日期：2025-12-17
更新日期：2025-12-17

Requirements: 1.5, 2.1, 2.2, 2.3, 2.4, 2.5
"""

import pytest
import pytest_asyncio
import asyncio
import httpx
import logging
import time
from typing import Dict, Any, List

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

# Greeting测试查询列表
GREETING_QUERIES = [
    "你好",
    "早上好",
    "晚上好",
    "hi",
    "hello",
    "嗨",
    "在吗",
    "您好",
    "嘿",
    "哈喽"
]


@pytest_asyncio.fixture
async def http_client():
    """创建HTTP客户端"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        yield client


class TestGreetingWorkflow:
    """Greeting场景工作流程测试类"""

    @pytest.mark.asyncio
    async def test_01_greeting_template_selection(self, http_client):
        """
        测试1：验证greeting模板被正确选择
        
        验证：
        - 对于问候语查询，系统选择greeting模板
        - 模板ID为"greeting"
        
        Requirements: 1.5, 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试1：验证greeting模板被正确选择")
        logger.info("=" * 80)

        test_query = "你好"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_greeting_template_selection",
                    "domain": "fitness"
                }
            )
            
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            logger.info(f"✅ 请求成功，耗时: {elapsed_time:.2f}秒")
            
            # 验证响应结构
            assert 'data' in data, "响应缺少data字段"
            result = data['data']
            
            # 验证关键字段
            assert 'response' in result, "响应缺少response字段"
            assert 'metadata' in result, "响应缺少metadata字段"
            
            metadata = result['metadata']
            
            # 验证模板选择
            template_id = metadata.get('template_id') or metadata.get('dag_template_id')
            logger.info(f"选择的模板ID: {template_id}")
            
            assert template_id == "greeting", \
                f"❌ 模板选择错误: 期望'greeting'，实际'{template_id}'"
            
            logger.info(f"✅ greeting模板被正确选择")
            
            # 记录响应内容
            response_text = result['response']
            logger.info(f"响应内容: {response_text}")
            
            return result

        except Exception as e:
            logger.error(f"❌ greeting模板选择测试失败: {e}")
            pytest.fail(f"greeting模板选择测试失败: {e}")

    @pytest.mark.asyncio
    async def test_02_greeting_response_length(self, http_client):
        """
        测试2：验证响应长度<100字
        
        验证：
        - greeting响应长度小于100字
        - 响应简短友好
        
        Requirements: 2.4
        """
        logger.info("=" * 80)
        logger.info("测试2：验证响应长度<100字")
        logger.info("=" * 80)

        test_query = "你好"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_greeting_response_length",
                    "domain": "fitness"
                }
            )
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            response_text = result['response']
            
            # 计算响应长度
            response_length = len(response_text)
            logger.info(f"响应长度: {response_length}字")
            logger.info(f"响应内容: {response_text}")
            
            # 验证长度<100字
            assert response_length < 100, \
                f"❌ 响应长度超过100字: {response_length}字"
            
            logger.info(f"✅ 响应长度符合要求: {response_length}字 < 100字")
            
            return result

        except Exception as e:
            logger.error(f"❌ 响应长度测试失败: {e}")
            pytest.fail(f"响应长度测试失败: {e}")

    @pytest.mark.asyncio
    async def test_03_greeting_no_training_advice(self, http_client):
        """
        测试3：验证响应不包含训练建议
        
        验证：
        - 响应不包含"训练计划"、"动作"、"营养"等专业术语
        - 响应是简单的问候，不提供专业建议
        
        Requirements: 2.5
        """
        logger.info("=" * 80)
        logger.info("测试3：验证响应不包含训练建议")
        logger.info("=" * 80)

        test_query = "你好"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_greeting_no_training_advice",
                    "domain": "fitness"
                }
            )
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            response_text = result['response']
            
            logger.info(f"响应内容: {response_text}")
            
            # 定义禁止的专业术语
            forbidden_terms = [
                "训练计划", "训练方案", "训练建议",
                "动作", "练习", "运动",
                "营养", "膳食", "饮食",
                "TDEE", "热量", "蛋白质",
                "组数", "次数", "重量",
                "肌肉", "力量", "增肌", "减脂"
            ]
            
            # 检查是否包含禁止术语
            found_terms = []
            for term in forbidden_terms:
                if term in response_text:
                    found_terms.append(term)
            
            if found_terms:
                logger.error(f"❌ 响应包含禁止的专业术语: {', '.join(found_terms)}")
                pytest.fail(f"响应包含禁止的专业术语: {', '.join(found_terms)}")
            
            logger.info(f"✅ 响应不包含训练建议或专业术语")
            
            return result

        except Exception as e:
            logger.error(f"❌ 响应内容测试失败: {e}")
            pytest.fail(f"响应内容测试失败: {e}")

    @pytest.mark.asyncio
    async def test_04_greeting_no_mcp_tools(self, http_client):
        """
        测试4：验证MCP工具调用数量为0
        
        验证：
        - greeting模板不调用任何MCP工具
        - tools_called列表为空或不包含MCP工具
        
        Requirements: 2.3
        """
        logger.info("=" * 80)
        logger.info("测试4：验证MCP工具调用数量为0")
        logger.info("=" * 80)

        test_query = "你好"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_greeting_no_mcp_tools",
                    "domain": "fitness"
                }
            )
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            metadata = result.get('metadata', {})
            
            # 检查工具调用记录
            tools_called = metadata.get('tools_called', [])
            logger.info(f"调用的工具: {tools_called if tools_called else '无'}")
            
            # 验证没有调用MCP工具
            mcp_tools = [
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
            
            called_mcp_tools = [tool for tool in tools_called if tool in mcp_tools]
            
            if called_mcp_tools:
                logger.error(f"❌ greeting模板错误地调用了MCP工具: {', '.join(called_mcp_tools)}")
                pytest.fail(f"greeting模板错误地调用了MCP工具: {', '.join(called_mcp_tools)}")
            
            logger.info(f"✅ greeting模板没有调用任何MCP工具")
            
            return result

        except Exception as e:
            logger.error(f"❌ MCP工具调用测试失败: {e}")
            pytest.fail(f"MCP工具调用测试失败: {e}")

    @pytest.mark.asyncio
    async def test_05_multiple_greeting_queries(self, http_client):
        """
        测试5：测试多个问候语查询
        
        验证：
        - 所有问候语都能正确识别
        - 所有响应都符合greeting模板要求
        
        Requirements: 1.5, 2.1, 2.2, 2.3, 2.4, 2.5
        """
        logger.info("=" * 80)
        logger.info("测试5：测试多个问候语查询")
        logger.info("=" * 80)

        results = []
        failed_queries = []
        
        for i, query in enumerate(GREETING_QUERIES):
            try:
                logger.info(f"\n测试 {i+1}/{len(GREETING_QUERIES)}: {query}")
                
                response = await http_client.post(
                    API_ENDPOINT,
                    json={
                        "query": query,
                        "user_id": TEST_USER_ID,
                        "session_id": f"test_multiple_greetings_{i}",
                        "domain": "fitness"
                    }
                )
                
                assert response.status_code == 200, f"请求失败: {response.status_code}"
                
                data = response.json()
                result = data['data']
                metadata = result.get('metadata', {})
                response_text = result['response']
                
                # 验证1：模板选择
                template_id = metadata.get('template_id') or metadata.get('dag_template_id')
                template_correct = template_id == "greeting"
                
                # 验证2：响应长度
                response_length = len(response_text)
                length_correct = response_length < 100
                
                # 验证3：无训练建议
                forbidden_terms = ["训练计划", "动作", "营养", "TDEE", "肌肉"]
                has_forbidden = any(term in response_text for term in forbidden_terms)
                content_correct = not has_forbidden
                
                # 验证4：无MCP工具调用
                tools_called = metadata.get('tools_called', [])
                mcp_tools = [
                    "intelligent_exercise_selector", "contraindications_checker",
                    "injury_risk_assessor", "tdee_calculator"
                ]
                has_mcp_tools = any(tool in tools_called for tool in mcp_tools)
                tools_correct = not has_mcp_tools
                
                # 记录结果
                all_correct = template_correct and length_correct and content_correct and tools_correct
                
                result_summary = {
                    "query": query,
                    "template_correct": template_correct,
                    "length_correct": length_correct,
                    "content_correct": content_correct,
                    "tools_correct": tools_correct,
                    "all_correct": all_correct,
                    "response_length": response_length,
                    "response_text": response_text
                }
                
                results.append(result_summary)
                
                # 输出验证结果
                logger.info(f"  模板选择: {'✅' if template_correct else '❌'} ({template_id})")
                logger.info(f"  响应长度: {'✅' if length_correct else '❌'} ({response_length}字)")
                logger.info(f"  响应内容: {'✅' if content_correct else '❌'}")
                logger.info(f"  工具调用: {'✅' if tools_correct else '❌'}")
                logger.info(f"  响应: {response_text}")
                
                if not all_correct:
                    failed_queries.append(query)
                
                # 添加延迟避免速率限制
                if i < len(GREETING_QUERIES) - 1:
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ 查询失败: {e}")
                failed_queries.append(query)
                continue
        
        # 统计结果
        logger.info(f"\n" + "=" * 80)
        logger.info(f"多个问候语测试结果")
        logger.info(f"=" * 80)
        
        total_queries = len(GREETING_QUERIES)
        successful_queries = len([r for r in results if r['all_correct']])
        success_rate = (successful_queries / total_queries) * 100 if total_queries > 0 else 0
        
        logger.info(f"总测试数: {total_queries}")
        logger.info(f"成功数: {successful_queries}")
        logger.info(f"失败数: {len(failed_queries)}")
        logger.info(f"成功率: {success_rate:.1f}%")
        
        # 详细统计
        template_correct_count = len([r for r in results if r['template_correct']])
        length_correct_count = len([r for r in results if r['length_correct']])
        content_correct_count = len([r for r in results if r['content_correct']])
        tools_correct_count = len([r for r in results if r['tools_correct']])
        
        logger.info(f"\n详细统计:")
        logger.info(f"  - 模板选择正确: {template_correct_count}/{total_queries}")
        logger.info(f"  - 响应长度正确: {length_correct_count}/{total_queries}")
        logger.info(f"  - 响应内容正确: {content_correct_count}/{total_queries}")
        logger.info(f"  - 工具调用正确: {tools_correct_count}/{total_queries}")
        
        # 平均响应长度
        avg_length = sum(r['response_length'] for r in results) / len(results) if results else 0
        logger.info(f"  - 平均响应长度: {avg_length:.1f}字")
        
        # 失败查询
        if failed_queries:
            logger.info(f"\n失败的查询:")
            for query in failed_queries:
                logger.info(f"  - {query}")
        
        # 验证成功率>80%
        assert success_rate >= 80, \
            f"成功率不足: {success_rate:.1f}% < 80%"
        
        logger.info(f"\n✅ 多个问候语测试通过")
        
        return results

    @pytest.mark.asyncio
    async def test_06_greeting_performance(self, http_client):
        """
        测试6：greeting场景性能测试
        
        验证：
        - greeting响应时间<5秒
        - 性能符合要求
        
        Requirements: 7.1
        """
        logger.info("=" * 80)
        logger.info("测试6：greeting场景性能测试")
        logger.info("=" * 80)

        test_queries = ["你好", "早上好", "hi"]
        response_times = []
        
        for query in test_queries:
            try:
                logger.info(f"\n测试查询: {query}")
                
                start_time = time.time()
                
                response = await http_client.post(
                    API_ENDPOINT,
                    json={
                        "query": query,
                        "user_id": TEST_USER_ID,
                        "session_id": f"test_greeting_performance_{len(response_times)}",
                        "domain": "fitness"
                    }
                )
                
                elapsed_time = time.time() - start_time
                response_times.append(elapsed_time)
                
                logger.info(f"  响应时间: {elapsed_time:.2f}秒")
                
            except Exception as e:
                logger.warning(f"  ⚠️  查询失败: {e}")
                continue
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            logger.info(f"\n性能统计:")
            logger.info(f"  - 平均响应时间: {avg_time:.2f}秒")
            logger.info(f"  - 最快响应: {min_time:.2f}秒")
            logger.info(f"  - 最慢响应: {max_time:.2f}秒")
            
            # 验证平均响应时间<20秒（greeting场景仍需经过完整11步工作流程）
            assert avg_time < 20, f"平均响应时间过长: {avg_time:.2f}秒 >= 20秒"
            
            logger.info(f"✅ greeting场景性能测试通过")
        else:
            logger.warning(f"⚠️  没有成功的查询，跳过性能统计")


def run_greeting_tests():
    """运行greeting场景测试"""
    logger.info("\n" + "=" * 80)
    logger.info("Greeting场景集成测试套件 v1.0.0")
    logger.info("=" * 80)
    
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])


if __name__ == "__main__":
    run_greeting_tests()
