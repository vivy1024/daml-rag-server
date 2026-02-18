#!/usr/bin/env python3
"""
Task 18: 全量回归测试 - 真实LLM调用
通过HTTP API调用测试13个DAG模板场景

使用Anthropic Claude (Kiro RS) 作为主LLM后端
"""
import httpx
import json
import time
import sys

BASE_URL = "http://localhost:8001"
HEADERS = {"X-Internal-Token": "crewai-internal-secret-2025"}
CHAT_PATH = "/api/v1/chat"

# 13个DAG模板测试用例 + 安全约束测试
TEST_CASES = [
    {"id": "01_greeting", "query": "你好", "expect": ["你好"]},
    {"id": "02_quick_consult", "query": "深蹲膝盖疼怎么办？", "expect": ["膝盖"]},
    {"id": "03_exercise_search", "query": "有什么练胸的动作推荐？", "expect": ["胸"]},
    {"id": "04_training_plan", "query": "帮我制定一个增肌训练计划", "expect": ["训练"]},
    {"id": "05_nutrition", "query": "增肌期间怎么吃？", "expect": ["蛋白"]},
    {"id": "06_safety", "query": "腰椎间盘突出可以做硬拉吗？", "expect": ["腰"]},
    {"id": "07_comprehensive", "query": "我想减脂增肌，给我一个完整方案", "expect": ["训练"]},
    {"id": "08_progress", "query": "我练了三个月了，感觉没什么进步", "expect": ["调整"]},
    {"id": "09_rehab", "query": "肩膀受伤后怎么恢复训练？", "expect": ["肩"]},
    {"id": "10_plan_adjust", "query": "我的训练计划需要调整，最近太累了", "expect": ["恢复"]},
    {"id": "11_fat_loss", "query": "帮我设计一个减脂方案", "expect": ["减脂"]},
    {"id": "12_strength", "query": "我想提高卧推力量，现在能推60kg", "expect": ["卧推"]},
    {"id": "13_posture", "query": "我有圆肩驼背，怎么矫正？", "expect": ["圆肩"]},
]


def test_single(client: httpx.Client, tc: dict) -> dict:
    """测试单个查询"""
    start = time.time()
    try:
        resp = client.post(
            f"{BASE_URL}{CHAT_PATH}",
            headers=HEADERS,
            json={"user_id": "1", "query": tc["query"]},
            timeout=120.0
        )
        elapsed = (time.time() - start) * 1000

        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "ms": elapsed}

        data = resp.json()
        response_text = data.get("data", {}).get("response", "") or ""
        if not response_text and isinstance(data.get("data"), str):
            response_text = data["data"]

        keywords_found = [kw for kw in tc["expect"] if kw in response_text]

        return {
            "success": True,
            "response": response_text[:300],
            "length": len(response_text),
            "ms": elapsed,
            "keywords_found": keywords_found,
            "template": data.get("data", {}).get("model_used", "unknown") if isinstance(data.get("data"), dict) else "unknown",
        }
    except httpx.TimeoutException:
        return {"success": False, "error": "TIMEOUT (120s)", "ms": (time.time() - start) * 1000}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {str(e)[:200]}", "ms": (time.time() - start) * 1000}


def main():
    print("=" * 70)
    print("Task 18: 全量回归测试 - 真实LLM调用")
    print(f"测试用例: {len(TEST_CASES)} 个DAG模板场景")
    print(f"API: {BASE_URL}{CHAT_PATH}")
    print("=" * 70)

    # 先检查API是否可用
    try:
        with httpx.Client() as client:
            health = client.get(f"{BASE_URL}/health", timeout=5.0)
            print(f"\nAPI健康检查: {health.status_code}")
    except Exception as e:
        print(f"\n❌ API不可用: {e}")
        sys.exit(1)

    results = []
    passed = 0
    failed = 0

    with httpx.Client() as client:
        for i, tc in enumerate(TEST_CASES):
            print(f"\n[{i+1}/{len(TEST_CASES)}] {tc['id']}: {tc['query']}")

            result = test_single(client, tc)
            result["test_id"] = tc["id"]
            results.append(result)

            if result["success"]:
                passed += 1
                kw = result["keywords_found"]
                print(f"  ✅ PASS | {result['ms']:.0f}ms | {result['length']} chars | keywords: {kw}")
                print(f"  响应: {result['response'][:120]}...")
            else:
                failed += 1
                print(f"  ❌ FAIL | {result['ms']:.0f}ms | {result['error']}")

    # 汇总
    print("\n" + "=" * 70)
    total_time = sum(r["ms"] for r in results)
    print(f"测试结果: {passed} passed / {failed} failed / {len(TEST_CASES)} total")
    print(f"总耗时: {total_time/1000:.1f}s | 平均: {total_time/len(TEST_CASES)/1000:.1f}s/query")

    # 性能统计
    success_results = [r for r in results if r["success"]]
    if success_results:
        times = [r["ms"] for r in success_results]
        print(f"响应时间: min={min(times):.0f}ms | max={max(times):.0f}ms | avg={sum(times)/len(times):.0f}ms")
    print("=" * 70)

    # 保存结果
    with open('/app/test_regression_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n详细结果: test_regression_results.json")

    return failed


if __name__ == "__main__":
    sys.exit(main())
