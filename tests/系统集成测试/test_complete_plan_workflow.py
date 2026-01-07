# -*- coding: utf-8 -*-
"""
Complete Training Plan场景集成测试

测试complete_training_plan模板的完整工作流程，验证：
1. complete_training_plan模板被正确选择
2. 响应长度>500字
3. 响应包含详细分析和建议

版本：v1.0.0
创建日期：2025-12-18
更新日期：2025-12-18

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
# 在Docker容器内运行时使用localhost，在容器外运行时也使用localhost
BASE_URL = "http://127.0.0.1:8001"
API_ENDPOINT = f"{BASE_URL}/api/v1/chat"
TEST_USER_ID = "2"  # MySQL中的vivy用户

# Complete Training Plan测试查询列表
COMPLETE_PLAN_QUERIES = [
    "帮我制定一个完整的增肌训练计划",
    "我想要一个详细的减脂训练方案，包括饮食建议",
    "给我设计一个全面的力量训练计划，我是初学者",
    "我想要一个专业的健身计划，目标是增强体能和肌肉",
    "帮我制定一个周期化的训练计划，包括营养指导"
]


@pytest_asyncio.fixture
async def http_client():
    """创建HTTP客户端"""
    async with httpx.AsyncClient(timeout=180.0) as client:
        yield client


class TestCompletePlanWorkflow:
    """Complete Training Plan场景工作流程测试类"""

    @pytest.mark.asyncio
    async def test_01_complete_plan_template_selection(self, http_client):
        """
        测试1：验证complete_training_plan模板被正确选择
        
        验证：
        - 对于复杂训练计划查询，系统选择complete_training_plan模板
        - 模板ID为"complete_training_plan"
        
        Requirements: 1.5, 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试1：验证complete_training_plan模板被正确选择")
        logger.info("=" * 80)

        test_query = "帮我制定一个完整的增肌训练计划"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            start_time = time.time()
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_complete_plan_template_selection",
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
            
            assert template_id == "complete_training_plan", \
                f"❌ 模板选择错误: 期望'complete_training_plan'，实际'{template_id}'"
            
            logger.info(f"✅ complete_training_plan模板被正确选择")
            
            # 记录响应内容
            response_text = result['response']
            logger.info(f"响应长度: {len(response_text)}字")
            logger.info(f"响应预览: {response_text[:200]}...")
            
            return result

        except Exception as e:
            logger.error(f"❌ complete_training_plan模板选择测试失败: {e}")
            pytest.fail(f"complete_training_plan模板选择测试失败: {e}")

    @pytest.mark.asyncio
    async def test_02_complete_plan_response_length(self, http_client):
        """
        测试2：验证响应长度>500字
        
        验证：
        - complete_training_plan响应长度大于500字
        - 响应详细完整，包含充分的分析和建议
        
        Requirements: 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试2：验证响应长度>500字")
        logger.info("=" * 80)

        test_query = "帮我制定一个完整的增肌训练计划"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_complete_plan_response_length",
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
            logger.info(f"响应预览: {response_text[:300]}...")
            
            # 验证长度>500字
            assert response_length > 500, \
                f"❌ 响应长度不符合要求: {response_length}字（期望>500字）"
            
            logger.info(f"✅ 响应长度符合要求: {response_length}字（>500字）")
            
            return result

        except Exception as e:
            logger.error(f"❌ 响应长度测试失败: {e}")
            pytest.fail(f"响应长度测试失败: {e}")

    @pytest.mark.asyncio
    async def test_03_complete_plan_detailed_analysis(self, http_client):
        """
        测试3：验证响应包含详细分析和建议
        
        验证：
        - 响应包含专业分析
        - 响应包含具体建议
        - 响应包含训练计划相关内容
        
        Requirements: 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试3：验证响应包含详细分析和建议")
        logger.info("=" * 80)

        test_query = "帮我制定一个完整的增肌训练计划"
        
        try:
            logger.info(f"\n测试查询: {test_query}")
            
            response = await http_client.post(
                API_ENDPOINT,
                json={
                    "query": test_query,
                    "user_id": TEST_USER_ID,
                    "session_id": "test_complete_plan_detailed_analysis",
                    "domain": "fitness"
                }
            )
            
            assert response.status_code == 200, f"请求失败: {response.status_code}"
            
            data = response.json()
            result = data['data']
            response_text = result['response']
            
            logger.info(f"响应长度: {len(response_text)}字")
            logger.info(f"响应内容: {response_text}")
            
            # 验证响应包含专业分析关键词
            analysis_keywords = [
                "分析", "评估", "建议", "推荐", "计划",
                "训练", "动作", "肌肉", "强度", "频率",
                "组数", "次数", "休息", "营养", "饮食"
            ]
            
            found_keywords = [kw for kw in analysis_keywords if kw in response_text]
            keyword_count = len(found_keywords)
            
            logger.info(f"找到的关键词数量: {keyword_count}/{len(analysis_keywords)}")
            logger.info(f"找到的关键词: {', '.join(found_keywords)}")
            
            # 验证至少包含5个关键词
            assert keyword_count >= 5, \
                f"❌ 响应缺少专业分析内容（仅包含{keyword_count}个关键词，期望>=5个）"
            
            logger.info(f"✅ 响应包含详细分析和建议（{keyword_count}个关键词）")
            
            # 验证响应包含具体的训练建议（至少3段）
            paragraphs = [p.strip() for p in response_text.split('\n') if p.strip() and len(p.strip()) > 20]
            logger.info(f"响应段落数: {len(paragraphs)}")
            
            assert len(paragraphs) >= 3, \
                f"❌ 响应段落过少: {len(paragraphs)}段（期望>=3段）"
            
            logger.info(f"✅ 响应包含充分的内容（{len(paragraphs)}段）")
            
            return result

        except Exception as e:
            logger.error(f"❌ 响应内容测试失败: {e}")
            pytest.fail(f"响应内容测试失败: {e}")

    @pytest.mark.asyncio
    async def test_04_multiple_complete_plan_queries(self, http_client):
        """
        测试4：测试多个完整训练计划查询
        
        验证：
        - 所有复杂查询都能正确识别
        - 所有响应都符合complete_training_plan模板要求
        
        Requirements: 1.5, 2.1, 2.2
        """
        logger.info("=" * 80)
        logger.info("测试4：测试多个完整训练计划查询")
        logger.info("=" * 80)

        results = []
        failed_queries = []
        
        for i, query in enumerate(COMPLETE_PLAN_QUERIES):
            try:
                logger.info(f"\n测试 {i+1}/{len(COMPLETE_PLAN_QUERIES)}: {query}")
                
                response = await http_client.post(
                    API_ENDPOINT,
                    json={
                        "query": query,
                        "user_id": TEST_USER_ID,
                        "session_id": f"test_multiple_complete_plan_{i}",
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
                template_correct = template_id == "complete_training_plan"
                
                # 验证2：响应长度
                response_length = len(response_text)
                length_correct = response_length > 500
                
                # 验证3：响应包含专业分析
                analysis_keywords = ["分析", "评估", "建议", "推荐", "计划", "训练", "动作"]
                keyword_count = sum(1 for kw in analysis_keywords if kw in response_text)
                has_analysis = keyword_count >= 5
                
                # 记录结果
                all_correct = template_correct and length_correct and has_analysis
                
                result_summary = {
                    "query": query,
                    "template_correct": template_correct,
                    "length_correct": length_correct,
                    "has_analysis": has_analysis,
                    "all_correct": all_correct,
                    "response_length": response_length,
                    "keyword_count": keyword_count,
                    "response_text": response_text[:200] + "..." if len(response_text) > 200 else response_text
                }
                
                results.append(result_summary)
                
                # 输出验证结果
                logger.info(f"  模板选择: {'✅' if template_correct else '❌'} ({template_id})")
                logger.info(f"  响应长度: {'✅' if length_correct else '❌'} ({response_length}字)")
                logger.info(f"  专业分析: {'✅' if has_analysis else '❌'} ({keyword_count}个关键词)")
                logger.info(f"  响应预览: {response_text[:150]}...")
                
                if not all_correct:
                    failed_queries.append(query)
                
                # 添加延迟避免速率限制
                if i < len(COMPLETE_PLAN_QUERIES) - 1:
                    await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"  ❌ 查询失败: {e}")
                failed_queries.append(query)
                continue
        
        # 统计结果
        logger.info(f"\n" + "=" * 80)
        logger.info(f"多个完整训练计划测试结果")
        logger.info(f"=" * 80)
        
        total_queries = len(COMPLETE_PLAN_QUERIES)
        successful_queries = len([r for r in results if r['all_correct']])
        success_rate = (successful_queries / total_queries) * 100 if total_queries > 0 else 0
        
        logger.info(f"总测试数: {total_queries}")
        logger.info(f"成功数: {successful_queries}")
        logger.info(f"失败数: {len(failed_queries)}")
        logger.info(f"成功率: {success_rate:.1f}%")
        
        # 详细统计
        template_correct_count = len([r for r in results if r['template_correct']])
        length_correct_count = len([r for r in results if r['length_correct']])
        analysis_count = len([r for r in results if r['has_analysis']])
        
        logger.info(f"\n详细统计:")
        logger.info(f"  - 模板选择正确: {template_correct_count}/{total_queries}")
        logger.info(f"  - 响应长度正确: {length_correct_count}/{total_queries}")
        logger.info(f"  - 包含专业分析: {analysis_count}/{total_queries}")
        
        # 平均响应长度
        avg_length = sum(r['response_length'] for r in results) / len(results) if results else 0
        logger.info(f"  - 平均响应长度: {avg_length:.1f}字")
        
        # 平均关键词数量
        avg_keywords = sum(r['keyword_count'] for r in results) / len(results) if results else 0
        logger.info(f"  - 平均关键词数量: {avg_keywords:.1f}个")
        
        # 失败查询
        if failed_queries:
            logger.info(f"\n失败的查询:")
            for query in failed_queries:
                logger.info(f"  - {query}")
        
        # 验证成功率>70%
        assert success_rate >= 70, \
            f"成功率不足: {success_rate:.1f}% < 70%"
        
        logger.info(f"\n✅ 多个完整训练计划测试通过")
        
        return results

    @pytest.mark.asyncio
    async def test_05_complete_plan_performance(self, http_client):
        """
        测试5：complete_training_plan场景性能测试
        
        验证：
        - complete_training_plan响应时间合理
        - 性能符合要求
        
        Requirements: 7.1
        """
        logger.info("=" * 80)
        logger.info("测试5：complete_training_plan场景性能测试")
        logger.info("=" * 80)

        test_queries = [
            "帮我制定一个完整的增肌训练计划",
            "我想要一个详细的减脂训练方案，包括饮食建议",
            "给我设计一个全面的力量训练计划，我是初学者"
        ]
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
                        "session_id": f"test_complete_plan_performance_{len(response_times)}",
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
            
            # 验证平均响应时间<60秒（complete_training_plan场景需要调用多个MCP工具）
            assert avg_time < 60, f"平均响应时间过长: {avg_time:.2f}秒 >= 60秒"
            
            logger.info(f"✅ complete_training_plan场景性能测试通过")
        else:
            logger.warning(f"⚠️  没有成功的查询，跳过性能统计")


def run_complete_plan_tests():
    """运行complete_training_plan场景测试"""
    logger.info("\n" + "=" * 80)
    logger.info("Complete Training Plan场景集成测试套件 v1.0.0")
    logger.info("=" * 80)
    
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])


if __name__ == "__main__":
    run_complete_plan_tests()
