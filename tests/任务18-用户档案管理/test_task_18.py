# -*- coding: utf-8 -*-
"""
任务18端到端验证测试

测试场景：
1. 训练计划生成
2. 营养规划
3. 安全检查
4. 生成测试报告

版本：v1.0.0
创建日期：2025-12-17
"""

import pytest
import pytest_asyncio
import httpx
import logging
import time
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8001"
API_ENDPOINT = f"{BASE_URL}/api/v1/chat"
TEST_USER_ID = "2"


@pytest_asyncio.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=120.0) as client:
        yield client


@pytest.mark.asyncio
async def test_training_plan_scenario(http_client):
    """测试18.1：训练计划生成场景"""
    logger.info("=" * 80)
    logger.info("测试18.1：训练计划生成场景")
    logger.info("=" * 80)

    query = "我想制定一个8周的增肌训练计划，每周训练4次，主要练胸和背，我有腰椎间盘突出的问题"
    
    start_time = time.time()
    response = await http_client.post(
        API_ENDPOINT,
        json={
            "query": query,
            "user_id": TEST_USER_ID,
            "domain": "fitness",
            "session_id": "test_18_1"
        }
    )
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200, f"请求失败: {response.status_code}"
    
    data = response.json()
    logger.info(f"响应键: {list(data.keys())}")
    
    # 处理不同的响应格式
    if 'data' in data:
        result = data['data']
    else:
        result = data
    
    response_text = result.get('response', '')
    metadata = result.get('metadata', {})
    
    logger.info(f"✅ 请求成功，耗时: {elapsed_time:.2f}秒")
    logger.info(f"响应长度: {len(response_text)}字符")
    
    # 验证MCP工具调用
    tools_called = metadata.get('tools_called', [])
    logger.info(f"调用的工具: {', '.join(tools_called)}")
    
    # 验证响应质量
    keywords = ['训练', '计划', '动作', '腰椎']
    found = [kw for kw in keywords if kw in response_text]
    logger.info(f"找到关键词: {', '.join(found)}")
    
    assert len(found) >= 3, f"响应质量不足: {found}"
    logger.info("✅ 测试18.1通过")
    
    return {
        "elapsed_time": elapsed_time,
        "tools_called": tools_called,
        "response_length": len(response_text)
    }


@pytest.mark.asyncio
async def test_nutrition_plan_scenario(http_client):
    """测试18.2：营养规划场景"""
    logger.info("=" * 80)
    logger.info("测试18.2：营养规划场景")
    logger.info("=" * 80)

    query = "帮我设计一份增肌期的营养餐食计划，我每天需要摄入多少热量和蛋白质？"
    
    start_time = time.time()
    response = await http_client.post(
        API_ENDPOINT,
        json={
            "query": query,
            "user_id": TEST_USER_ID,
            "domain": "fitness",
            "session_id": "test_18_2"
        }
    )
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200
    
    data = response.json()
    result = data.get('data', data)
    response_text = result.get('response', '')
    metadata = result.get('metadata', {})
    
    logger.info(f"✅ 请求成功，耗时: {elapsed_time:.2f}秒")
    
    # 验证营养相关内容
    keywords = ['热量', '蛋白质', '营养', '餐']
    found = [kw for kw in keywords if kw in response_text]
    logger.info(f"找到关键词: {', '.join(found)}")
    
    assert len(found) >= 3, f"营养内容不足: {found}"
    logger.info("✅ 测试18.2通过")
    
    return {
        "elapsed_time": elapsed_time,
        "response_length": len(response_text)
    }


@pytest.mark.asyncio
async def test_safety_check_scenario(http_client):
    """测试18.3：安全检查场景"""
    logger.info("=" * 80)
    logger.info("测试18.3：安全检查场景")
    logger.info("=" * 80)

    query = "我有腰椎间盘突出和肩袖损伤，哪些动作我不能做？有什么替代动作吗？"
    
    start_time = time.time()
    response = await http_client.post(
        API_ENDPOINT,
        json={
            "query": query,
            "user_id": TEST_USER_ID,
            "domain": "fitness",
            "session_id": "test_18_3"
        }
    )
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200
    
    data = response.json()
    result = data.get('data', data)
    response_text = result.get('response', '')
    metadata = result.get('metadata', {})
    
    logger.info(f"✅ 请求成功，耗时: {elapsed_time:.2f}秒")
    
    # 验证安全相关内容
    keywords = ['避免', '禁忌', '替代', '注意']
    found = [kw for kw in keywords if kw in response_text]
    logger.info(f"找到关键词: {', '.join(found)}")
    
    assert len(found) >= 2, f"安全内容不足: {found}"
    logger.info("✅ 测试18.3通过")
    
    return {
        "elapsed_time": elapsed_time,
        "response_length": len(response_text)
    }


@pytest.mark.asyncio
async def test_generate_report(http_client):
    """测试18.4：生成测试报告"""
    logger.info("=" * 80)
    logger.info("测试18.4：生成测试报告")
    logger.info("=" * 80)

    results = {
        "test_time": datetime.now().isoformat(),
        "scenarios": []
    }
    
    # 运行所有场景
    try:
        r1 = await test_training_plan_scenario(http_client)
        results["scenarios"].append({"name": "训练计划", "status": "通过", "data": r1})
    except Exception as e:
        results["scenarios"].append({"name": "训练计划", "status": "失败", "error": str(e)})
    
    try:
        r2 = await test_nutrition_plan_scenario(http_client)
        results["scenarios"].append({"name": "营养规划", "status": "通过", "data": r2})
    except Exception as e:
        results["scenarios"].append({"name": "营养规划", "status": "失败", "error": str(e)})
    
    try:
        r3 = await test_safety_check_scenario(http_client)
        results["scenarios"].append({"name": "安全检查", "status": "通过", "data": r3})
    except Exception as e:
        results["scenarios"].append({"name": "安全检查", "status": "失败", "error": str(e)})
    
    # 保存报告
    report_path = "tests/integration/E2E_TASK18_REPORT.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ 报告已保存: {report_path}")
    
    # 输出摘要
    passed = sum(1 for s in results["scenarios"] if s["status"] == "通过")
    total = len(results["scenarios"])
    logger.info(f"\n测试摘要: {passed}/{total} 通过")
    
    for scenario in results["scenarios"]:
        status_icon = "✅" if scenario["status"] == "通过" else "❌"
        logger.info(f"  {status_icon} {scenario['name']}: {scenario['status']}")
    
    assert passed >= 2, f"通过场景不足: {passed}/3"
    logger.info("\n✅ 测试18.4通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
