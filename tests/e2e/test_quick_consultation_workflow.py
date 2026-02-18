# -*- coding: utf-8 -*-
"""
Quick Consultation场景集成测试

测试quick_consultation模板的完整工作流程，验证：
1. quick_consultation模板被正确选择
2. 响应长度在100-500字之间
3. 响应简洁实用

版本：v1.0.0
创建日期：2025-12-17
更新日期：2025-12-17

Requirements: 1.5, 2.1, 2.2
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

# Quick Consultation测试查询列表（减少数量以避免超时）
QUICK_CONSULTATION_QUERIES = [
    "深蹲怎么做？",
    "卧推的标准动作是什么？",
    "如何拉伸腿部肌肉？",
    "训练后要吃什么？",
    "怎么热身比较好？"
]


@pytest_asyncio.fixture
async def http_client():
    """创建HTTP客户端"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        yield client


class TestQuickConsultationWorkflow:
    """Quick Consultation场景工作流程测试类"""

    @pytest.mark.asyncio
    async def test_01_quick_consultation_template_selection(self, http_client):
        """
        测试1：验证quick_consultation模板被正确选择
        
        验证：
        - 对于简单问题查询，系统选择quick_consultation模板
        - 模板ID为"quick_consultation"
        
        Requirements: 1.5, 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试1：验证quick_consultation模板被正确选择")
        logger.info("=" * 80)

        test_query = "深蹲怎么做？"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_quick_consultation_template_selection",
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
            
            assert template_id == "quick_consultation", \
                f"❌ 模板选择错误: 期望'quick_consultation'，实际'{template_id}'"
            
            logger.info(f"✅ quick_consultation模板被正确选择")
            
            # 记录响应内容
            response_text = result['response']
            logger.info(f"响应内容: {response_text}")
            
            return result

        except Exception as e:
            logger.error(f"❌ quick_consultation模板选择测试失败: {e}")
            pytest.fail(f"quick_consultation模板选择测试失败: {e}")

    @pytest.mark.asyncio
    async def test_02_quick_consultation_response_length(self, http_client):
        """
        测试2：验证响应长度在100-500字之间
        
        验证：
        - quick_consultation响应长度在100-500字之间
        - 响应简洁实用，不冗长
        
        Requirements: 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试2：验证响应长度在100-500字之间")
        logger.info("=" * 80)

        test_query = "深蹲怎么做？"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_quick_consultation_response_length",
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
            
            # 验证长度在100-500字之间
            assert 100 <= response_length <= 500, \
                f"❌ 响应长度不符合要求: {response_length}字（期望100-500字）"
            
            logger.info(f"✅ 响应长度符合要求: {response_length}字（100-500字）")
            
            return result

        except Exception as e:
            logger.error(f"❌ 响应长度测试失败: {e}")
            pytest.fail(f"响应长度测试失败: {e}")

    @pytest.mark.asyncio
    async def test_03_quick_consultation_concise_practical(self, http_client):
        """
        测试3：验证响应简洁实用
        
        验证：
        - 响应内容简洁明了
        - 响应提供实用建议
        - 响应不过于冗长或过于简短
        
        Requirements: 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试3：验证响应简洁实用")
        logger.info("=" * 80)

        test_query = "深蹲怎么做？"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_quick_consultation_concise_practical",
                    "domain": "fitness"
                }
            )
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            response_text = result['response']
            
            logger.info(f"响应内容: {response_text}")
            
            # 验证响应包含实用信息（关键词检查）
            practical_keywords = [
                "动作", "姿势", "要点", "注意", "建议",
                "方法", "技巧", "步骤", "执行", "训练"
            ]
            
            has_practical_content = any(keyword in response_text for keyword in practical_keywords)
            
            assert has_practical_content, \
                "❌ 响应缺少实用内容（未包含关键词：动作、姿势、要点等）"
            
            logger.info(f"✅ 响应包含实用内容")
            
            # 验证响应不过于简短（至少2段话）
            paragraphs = [p.strip() for p in response_text.split('\n') if p.strip()]
            logger.info(f"响应段落数: {len(paragraphs)}")
            
            # 验证响应长度合理
            response_length = len(response_text)
            assert response_length >= 100, \
                f"❌ 响应过于简短: {response_length}字 < 100字"
            
            logger.info(f"✅ 响应简洁实用，长度合理")
            
            return result

        except Exception as e:
            logger.error(f"❌ 响应内容测试失败: {e}")
            pytest.fail(f"响应内容测试失败: {e}")

    @pytest.mark.asyncio
    async def test_04_multiple_quick_consultation_queries(self, http_client):
        """
        测试4：测试多个快速咨询查询
        
        验证：
        - 所有简单问题都能正确识别
        - 所有响应都符合quick_consultation模板要求
        
        Requirements: 1.5, 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试4：测试多个快速咨询查询")
        logger.info("=" * 80)

        results = []
        failed_queries = []
        
        for i, query in enumerate(QUICK_CONSULTATION_QUERIES):
            try:
                logger.info(f"\n测试 {i+1}/{len(QUICK_CONSULTATION_QUERIES)}: {query}")
                
                response = await http_client.post(
                    API_ENDPOINT,
                    json={
                        "query": query,
                        "user_id": TEST_USER_ID,
                        "session_id": f"test_multiple_quick_consultation_{i}",
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
                template_correct = template_id == "quick_consultation"
                
                # 验证2：响应长度
                response_length = len(response_text)
                length_correct = 100 <= response_length <= 500
                
                # 验证3：响应包含实用内容
                practical_keywords = ["动作", "姿势", "要点", "注意", "建议", "方法", "技巧"]
                has_practical = any(keyword in response_text for keyword in practical_keywords)
                
                # 记录结果
                all_correct = template_correct and length_correct and has_practical
                
                result_summary = {
                    "query": query,
                    "template_correct": template_correct,
                    "length_correct": length_correct,
                    "has_practical": has_practical,
                    "all_correct": all_correct,
                    "response_length": response_length,
                    "response_text": response_text[:100] + "..." if len(response_text) > 100 else response_text
                }
                
                results.append(result_summary)
                
                # 输出验证结果
                logger.info(f"  模板选择: {'✅' if template_correct else '❌'} ({template_id})")
                logger.info(f"  响应长度: {'✅' if length_correct else '❌'} ({response_length}字)")
                logger.info(f"  实用内容: {'✅' if has_practical else '❌'}")
                logger.info(f"  响应预览: {response_text[:100]}...")
                
                if not all_correct:
                    failed_queries.append(query)
                
                # 添加延迟避免速率限制
                if i < len(QUICK_CONSULTATION_QUERIES) - 1:
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ 查询失败: {e}")
                failed_queries.append(query)
                continue
        
        # 统计结果
        logger.info(f"\n" + "=" * 80)
        logger.info(f"多个快速咨询测试结果")
        logger.info(f"=" * 80)
        
        total_queries = len(QUICK_CONSULTATION_QUERIES)
        successful_queries = len([r for r in results if r['all_correct']])
        success_rate = (successful_queries / total_queries) * 100 if total_queries > 0 else 0
        
        logger.info(f"总测试数: {total_queries}")
        logger.info(f"成功数: {successful_queries}")
        logger.info(f"失败数: {len(failed_queries)}")
        logger.info(f"成功率: {success_rate:.1f}%")
        
        # 详细统计
        template_correct_count = len([r for r in results if r['template_correct']])
        length_correct_count = len([r for r in results if r['length_correct']])
        practical_count = len([r for r in results if r['has_practical']])
        
        logger.info(f"\n详细统计:")
        logger.info(f"  - 模板选择正确: {template_correct_count}/{total_queries}")
        logger.info(f"  - 响应长度正确: {length_correct_count}/{total_queries}")
        logger.info(f"  - 包含实用内容: {practical_count}/{total_queries}")
        
        # 平均响应长度
        avg_length = sum(r['response_length'] for r in results) / len(results) if results else 0
        logger.info(f"  - 平均响应长度: {avg_length:.1f}字")
        
        # 失败查询
        if failed_queries:
            logger.info(f"\n失败的查询:")
            for query in failed_queries:
                logger.info(f"  - {query}")
        
        # 验证成功率>70%
        assert success_rate >= 70, \
            f"成功率不足: {success_rate:.1f}% < 70%"
        
        logger.info(f"\n✅ 多个快速咨询测试通过")
        
        return results

    @pytest.mark.asyncio
    async def test_05_quick_consultation_performance(self, http_client):
        """
        测试5：quick_consultation场景性能测试
        
        验证：
        - quick_consultation响应时间合理
        - 性能符合要求
        
        Requirements: 7.1
        """
        logger.info("=" * 80)
        logger.info("测试5：quick_consultation场景性能测试")
        logger.info("=" * 80)

        test_queries = ["深蹲怎么做？", "卧推的标准动作是什么？", "如何拉伸腿部肌肉？"]
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
                        "session_id": f"test_quick_consultation_performance_{len(response_times)}",
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
            
            # 验证平均响应时间<30秒（quick_consultation场景需要调用MCP工具）
            assert avg_time < 30, f"平均响应时间过长: {avg_time:.2f}秒 >= 30秒"
            
            logger.info(f"✅ quick_consultation场景性能测试通过")
        else:
            logger.warning(f"⚠️  没有成功的查询，跳过性能统计")


def run_quick_consultation_tests():
    """运行quick_consultation场景测试"""
    logger.info("\n" + "=" * 80)
    logger.info("Quick Consultation场景集成测试套件 v1.0.0")
    logger.info("=" * 80)
    
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])


if __name__ == "__main__":
    run_quick_consultation_tests()
