#!/usr/bin/env python3
"""
真实DAML-RAG API测试
实际调用DAML-RAG API进行个性化推荐测试
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealDAMLRAGAPITester:
    """真实DAML-RAG API测试器"""

    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.results_dir = "F:/build_body/mcp-servers/daml-rag-server/tests/results"
        self.results = []

    def load_test_cases(self):
        """加载测试用例"""
        try:
            with open("F:/build_body/mcp-servers/daml-rag-server/tests/llm_test_cases.json", 'r', encoding='utf-8') as f:
                test_cases_data = json.load(f)

            test_cases = test_cases_data.get('test_cases', [])
            logger.info(f"✅ 加载了 {len(test_cases)} 个测试用例")
            return test_cases
        except Exception as e:
            logger.error(f"❌ 加载测试用例失败: {e}")
            return []

    def check_api_health(self):
        """检查API健康状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ DAML-RAG API服务健康")
                return True
            else:
                logger.error(f"❌ API状态码: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 无法连接到DAML-RAG API: {e}")
            return False

    def test_real_api_recommendation(self, test_case: Dict[str, Any]):
        """测试真实API推荐"""
        logger.info(f"🧪 测试真实API推荐: {test_case['name']}")

        try:
            # 构造请求数据
            request_data = {
                "user_query": test_case['user_query'],
                "user_profile": test_case.get('user_profile', {}),
                "conversation_history": [],
                "preferences": {
                    "response_style": "professional",
                    "detail_level": "comprehensive"
                }
            }

            # 记录开始时间
            start_time = datetime.now()

            # 调用DAML-RAG API
            response = requests.post(
                f"{self.base_url}/api/graphrag/query",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()

            # 处理响应
            if response.status_code == 200:
                result_data = response.json()

                api_response = {
                    "timestamp": datetime.now().isoformat(),
                    "test_case_id": test_case['case_id'],
                    "user_query": test_case['user_query'],
                    "prompt_type": "real_api",
                    "api_response": result_data,
                    "execution_time": execution_time,
                    "status": "success"
                }

                logger.info(f"✅ API调用成功: {test_case['name']}, 耗时: {execution_time:.2f}s")

            else:
                api_response = {
                    "timestamp": datetime.now().isoformat(),
                    "test_case_id": test_case['case_id'],
                    "user_query": test_case['user_query'],
                    "prompt_type": "real_api",
                    "error": response.text,
                    "execution_time": execution_time,
                    "status": "failed",
                    "status_code": response.status_code
                }

                logger.error(f"❌ API调用失败: {test_case['name']}, 状态码: {response.status_code}")

            self.results.append(api_response)
            return api_response

        except requests.exceptions.Timeout:
            logger.error(f"❌ API请求超时: {test_case['name']}")
            return None
        except Exception as e:
            logger.error(f"❌ API调用异常: {test_case['name']} - {e}")
            return None

    def save_results(self):
        """保存测试结果"""
        try:
            os.makedirs(self.results_dir, exist_ok=True)

            output_file = os.path.join(self.results_dir, 'real_api_test_results.json')

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_session': {
                        'timestamp': datetime.now().isoformat(),
                        'total_tests': len(self.results),
                        'test_type': 'real_daml_rag_api'
                    },
                    'results': self.results
                }, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 真实API测试结果已保存到: {output_file}")

        except Exception as e:
            logger.error(f"❌ 保存测试结果失败: {e}")

    def analyze_results(self):
        """分析测试结果"""
        logger.info("📊 分析真实API测试结果...")

        if not self.results:
            logger.warning("⚠️ 没有测试结果可分析")
            return

        successful_tests = [r for r in self.results if r.get('status') == 'success']
        failed_tests = [r for r in self.results if r.get('status') == 'failed']

        success_rate = len(successful_tests) / len(self.results) * 100 if self.results else 0
        avg_execution_time = sum(r.get('execution_time', 0) for r in successful_tests) / len(successful_tests) if successful_tests else 0

        logger.info(f"📋 真实API测试结果统计:")
        logger.info(f"   - 总测试数: {len(self.results)}")
        logger.info(f"   - 成功测试: {len(successful_tests)}")
        logger.info(f"   - 失败测试: {len(failed_tests)}")
        logger.info(f"   - 成功率: {success_rate:.1f}%")
        logger.info(f"   - 平均执行时间: {avg_execution_time:.2f} 秒")

        # 分析成功测试的响应
        for result in successful_tests:
            api_response = result.get('api_response', {})
            if 'data' in api_response:
                response_data = api_response['data']
                response_length = len(str(response_data))
                logger.info(f"   - {result['test_case_id']}: 响应长度 {response_length} 字符")

        return {
            'total_tests': len(self.results),
            'successful_tests': len(successful_tests),
            'success_rate': success_rate,
            'avg_execution_time': avg_execution_time
        }

def main():
    """主函数"""
    logger.info("🚀 开始真实DAML-RAG API测试")
    logger.info("=" * 50)

    tester = RealDAMLRAGAPITester()

    try:
        # 1. 检查API健康状态
        if not tester.check_api_health():
            logger.error("❌ DAML-RAG API服务不健康，测试终止")
            return

        # 2. 加载测试用例
        test_cases = tester.load_test_cases()

        if not test_cases:
            logger.error("❌ 没有加载到测试用例，测试终止")
            return

        # 3. 执行真实API测试
        successful_tests = 0
        for test_case in test_cases:
            result = tester.test_real_api_recommendation(test_case)
            if result and result.get('status') == 'success':
                successful_tests += 1

        # 4. 保存结果
        tester.save_results()

        # 5. 分析结果
        analysis = tester.analyze_results()

        logger.info("🎉 真实DAML-RAG API测试完成!")
        logger.info(f"📊 测试统计: 成功 {successful_tests}/{len(test_cases)} 个测试")

        if analysis and analysis['success_rate'] == 100:
            logger.info("✅ DAML-RAG API功能正常，可以在生产环境使用")
        else:
            logger.warning(f"⚠️ API存在问题，成功率: {analysis['success_rate'] if analysis else 0:.1f}%")

    except Exception as e:
        logger.error(f"❌ 测试过程失败: {e}")

if __name__ == "__main__":
    main()