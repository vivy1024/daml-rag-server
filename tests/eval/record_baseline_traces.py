# -*- coding: utf-8 -*-
"""
Baseline Trace 录制器 — Task 5.3

录制 3 个关键模板在 harness 开启状态下的完整 trace，
作为后续回归对比的 baseline。

输出: tests/eval/results/baseline_traces.json

使用方式:
    docker exec fitness_daml_rag python tests/eval/record_baseline_traces.py
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch

sys.path.insert(0, ".")

from src.applications.fitness.config.runtime import HarnessConfig
from src.applications.fitness.workflow.nodes.step7_execute_dag import node_execute_dag
from src.applications.fitness.dag_template_system import DAGTemplateManager
from src.applications.fitness.harness import HarnessTracer

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("baseline_recorder")
logger.setLevel(logging.INFO)


# ═══════════════════════════════════════════════════════════
# Baseline 场景定义（每个模板 1 个代表性场景）
# ═══════════════════════════════════════════════════════════

BASELINE_SCENARIOS = [
    {
        "id": "baseline-ctp",
        "template": "complete_training_plan",
        "name": "增肌计划 baseline",
        "state": {
            "request_id": "baseline-ctp-001",
            "dag_template_id": "complete_training_plan",
            "user_profile": {
                "user_id": 1,
                "name": "Baseline用户A",
                "age": 28,
                "gender": "男",
                "height": 175,
                "weight": 70,
                "fitness_goal": "增肌",
                "experience_level": "中级",
                "available_equipment": ["杠铃", "哑铃", "卧推凳", "龙门架"],
                "available_time": "60分钟",
                "training_frequency": "4天/周",
            },
            "session_id": "baseline-session-ctp",
            "query_text": "帮我制定一个增肌训练计划",
            "user_id": 1,
        },
    },
    {
        "id": "baseline-sa",
        "template": "safety_assessment",
        "name": "安全评估 baseline",
        "state": {
            "request_id": "baseline-sa-001",
            "dag_template_id": "safety_assessment",
            "user_profile": {
                "user_id": 2,
                "name": "Baseline用户B",
                "age": 35,
                "gender": "男",
                "height": 180,
                "weight": 82,
                "fitness_goal": "增肌",
                "experience_level": "中级",
                "available_equipment": ["哑铃", "杠铃"],
                "health_conditions": ["腰椎间盘突出L4-L5"],
            },
            "session_id": "baseline-session-sa",
            "query_text": "我有腰椎间盘突出，评估一下我能做什么训练",
            "user_id": 2,
        },
    },
    {
        "id": "baseline-pa",
        "template": "plan_adjustment",
        "name": "计划调整 baseline",
        "state": {
            "request_id": "baseline-pa-001",
            "dag_template_id": "plan_adjustment",
            "user_profile": {
                "user_id": 3,
                "name": "Baseline用户C",
                "age": 30,
                "gender": "女",
                "height": 165,
                "weight": 58,
                "fitness_goal": "塑形",
                "experience_level": "中级",
                "available_equipment": ["哑铃", "弹力带"],
                "available_time": "30分钟",
            },
            "session_id": "baseline-session-pa",
            "query_text": "我现在只有30分钟了，帮我调整计划",
            "user_id": 3,
        },
    },
]


async def record_baseline():
    """录制 baseline traces"""
    template_manager = DAGTemplateManager()
    
    config = HarnessConfig(
        enabled=True,
        policy_enabled=True,
        verifier_enabled=True,
        tracer_enabled=True,
        memory_v2_enabled=False,  # baseline 不依赖记忆
        context_packet_enabled=False,
    )

    baselines = []

    for scenario in BASELINE_SCENARIOS:
        logger.info(f"▶ 录制 {scenario['id']}: {scenario['name']}")

        # 创建独立 tracer 来捕获 trace
        tracer = HarnessTracer()

        with patch(
            "src.applications.fitness.workflow.nodes.step7_execute_dag._get_harness_config",
            return_value=config,
        ):
            result = await node_execute_dag(
                scenario["state"],
                template_manager=template_manager,
            )

        # 收集结果
        baseline_entry = {
            "id": scenario["id"],
            "template": scenario["template"],
            "name": scenario["name"],
            "recorded_at": datetime.now().isoformat(),
            "harness_config": {
                "enabled": config.enabled,
                "policy_enabled": config.policy_enabled,
                "verifier_enabled": config.verifier_enabled,
                "tracer_enabled": config.tracer_enabled,
            },
            "result": {
                "has_dag_results": result.updates.get("dag_results") is not None,
                "policy_deny": result.updates.get("_harness_policy_deny", False),
                "deny_reason": result.updates.get("_harness_deny_reason", ""),
                "tasks_completed": result.updates.get("_dag_tasks_completed", 0),
                "tasks_failed": result.updates.get("_dag_tasks_failed", 0),
                "error": result.error,
                "warning": result.warning,
            },
        }

        # 提取 DAG 结果的工具列表（不含完整输出，避免 baseline 过大）
        dag_results = result.updates.get("dag_results")
        if dag_results:
            baseline_entry["result"]["tools_executed"] = [
                k for k in dag_results.keys() if not k.startswith("_")
            ]
            # 提取 verification 结果
            if "_harness_verification" in dag_results:
                baseline_entry["result"]["verification"] = dag_results["_harness_verification"]

        baselines.append(baseline_entry)

        status = "✅" if baseline_entry["result"]["has_dag_results"] or baseline_entry["result"]["policy_deny"] else "❌"
        logger.info(f"  {status} 完成: tasks={baseline_entry['result']['tasks_completed']}")

    # 保存
    output_dir = "tests/eval/results"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "baseline_traces.json")

    output = {
        "version": "1.0.0",
        "recorded_at": datetime.now().isoformat(),
        "harness_version": "v1.0.0",
        "scenarios_count": len(baselines),
        "baselines": baselines,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"\n📄 Baseline traces 已保存: {output_path}")

    # 打印摘要
    print("\n" + "=" * 60)
    print("  BASELINE TRACE 录制完成")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    for b in baselines:
        r = b["result"]
        if r["policy_deny"]:
            status = f"DENIED: {r['deny_reason'][:50]}"
        elif r["has_dag_results"]:
            tools = r.get("tools_executed", [])
            status = f"OK: {r['tasks_completed']} tasks, {len(tools)} tools"
        else:
            status = f"ERROR: {r.get('error', 'unknown')}"
        print(f"  [{b['id']}] {b['name']}: {status}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(record_baseline())
