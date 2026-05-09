# -*- coding: utf-8 -*-
"""
回归评估运行器 — Task 5.2

对比旧路径（harness off）和新路径（harness on）的执行差异。
输出结构化评估报告到 tests/eval/results/。

使用方式：
    docker exec fitness_daml_rag python tests/eval/run_harness_eval.py [--case CTP-01] [--dry-run]

评估维度：
1. safety: 安全约束遵守
2. completeness: 工具链完整性
3. constraint_adherence: 硬约束体现
4. context_utilization: 上下文利用率
5. tool_call_integrity: 工具调用正确性
"""

import asyncio
import json
import logging
import sys
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

sys.path.insert(0, ".")

from src.applications.fitness.config.runtime import HarnessConfig
from src.applications.fitness.workflow.nodes.step7_execute_dag import node_execute_dag
from src.applications.fitness.dag_template_system import DAGTemplateManager

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger("eval_runner")
logger.setLevel(logging.INFO)


# ═══════════════════════════════════════════════════════════
# 评估结果数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class PathResult:
    """单条路径的执行结果"""
    path_type: str  # "old" or "harness"
    dag_executed: bool = False
    dag_results: Optional[Dict] = None
    policy_deny: bool = False
    deny_reason: str = ""
    verification_result: Optional[Dict] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0


@dataclass
class EvalResult:
    """单个用例的评估结果"""
    case_id: str
    case_name: str
    template: str
    old_path: Optional[PathResult] = None
    harness_path: Optional[PathResult] = None
    dimension_scores: Dict[str, str] = field(default_factory=dict)
    passed: bool = False
    notes: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# 评估运行器
# ═══════════════════════════════════════════════════════════

class HarnessEvalRunner:
    """回归评估运行器"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.template_manager = DAGTemplateManager()
        self.results: List[EvalResult] = []

    async def run_case(self, case: Dict[str, Any]) -> EvalResult:
        """运行单个评估用例"""
        case_id = case["id"]
        logger.info(f"▶ 运行用例 {case_id}: {case['name']}")

        eval_result = EvalResult(
            case_id=case_id,
            case_name=case["name"],
            template=case["template"],
        )

        state = self._build_state(case)

        # ── 旧路径（harness off）──
        try:
            old_result = await self._run_path(state, harness_enabled=False)
            eval_result.old_path = old_result
        except Exception as e:
            eval_result.old_path = PathResult(path_type="old", error=str(e))
            eval_result.notes.append(f"旧路径异常: {e}")

        # ── 新路径（harness on）──
        try:
            harness_result = await self._run_path(state, harness_enabled=True)
            eval_result.harness_path = harness_result
        except Exception as e:
            eval_result.harness_path = PathResult(path_type="harness", error=str(e))
            eval_result.notes.append(f"新路径异常: {e}")

        # ── 评估维度打分 ──
        self._score_dimensions(case, eval_result)

        self.results.append(eval_result)
        return eval_result

    async def _run_path(
        self, state: Dict[str, Any], harness_enabled: bool
    ) -> PathResult:
        """执行单条路径"""
        path_type = "harness" if harness_enabled else "old"

        if harness_enabled:
            config = HarnessConfig(
                enabled=True,
                policy_enabled=True,
                verifier_enabled=True,
                tracer_enabled=True,
            )
        else:
            config = HarnessConfig(enabled=False)

        from unittest.mock import patch
        start = time.monotonic()

        with patch(
            "src.applications.fitness.workflow.nodes.step7_execute_dag._get_harness_config",
            return_value=config,
        ):
            result = await node_execute_dag(
                state.copy(),
                template_manager=self.template_manager,
            )

        duration_ms = (time.monotonic() - start) * 1000

        path_result = PathResult(path_type=path_type, duration_ms=duration_ms)

        if result.error:
            path_result.error = result.error
            return path_result

        updates = result.updates
        dag_results = updates.get("dag_results")

        if updates.get("_harness_policy_deny"):
            path_result.policy_deny = True
            path_result.deny_reason = updates.get("_harness_deny_reason", "")
            return path_result

        if dag_results:
            path_result.dag_executed = True
            path_result.dag_results = dag_results
            path_result.tasks_completed = updates.get("_dag_tasks_completed", 0)
            path_result.tasks_failed = updates.get("_dag_tasks_failed", 0)

            # 提取 harness 校验结果
            if "_harness_verification" in dag_results:
                path_result.verification_result = dag_results["_harness_verification"]

        return path_result

    def _build_state(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """从用例构建 WorkflowState"""
        inp = case["input"]
        return {
            "request_id": f"eval-{case['id']}",
            "dag_template_id": case["template"],
            "user_profile": inp["user_profile"],
            "session_id": f"eval-session-{case['id']}",
            "query_text": inp["query"],
            "user_id": inp["user_profile"].get("user_id", 1),
        }

    def _score_dimensions(self, case: Dict[str, Any], eval_result: EvalResult):
        """对评估维度打分"""
        expected = case.get("expected", {})
        harness = eval_result.harness_path

        if not harness:
            eval_result.passed = False
            return

        scores = {}

        # 1. Policy 判定是否符合预期
        expected_policy = expected.get("policy_decision", "allow")
        if harness.policy_deny:
            actual_policy = "deny"
        else:
            actual_policy = "allow"

        if actual_policy == expected_policy:
            scores["policy"] = "✅ PASS"
        else:
            scores["policy"] = f"❌ FAIL (expected={expected_policy}, actual={actual_policy})"

        # 2. DAG 是否执行
        expected_dag = expected.get("dag_should_execute", True)
        if harness.dag_executed == expected_dag:
            scores["dag_execution"] = "✅ PASS"
        else:
            scores["dag_execution"] = f"❌ FAIL (expected={expected_dag}, actual={harness.dag_executed})"

        # 3. 工具完整性
        if harness.dag_executed and harness.dag_results:
            executed_tools = list(harness.dag_results.keys())
            safety_tools = expected.get("safety_tools_required", [])
            missing_safety = [t for t in safety_tools if t not in executed_tools]
            if not missing_safety:
                scores["tool_completeness"] = f"✅ PASS ({len(executed_tools)} tools)"
            else:
                scores["tool_completeness"] = f"❌ FAIL (missing: {missing_safety})"
        elif harness.policy_deny and expected_policy == "deny":
            scores["tool_completeness"] = "✅ PASS (correctly denied)"
        else:
            scores["tool_completeness"] = "⚠️ SKIP (no DAG results)"

        # 4. Verifier 结果
        if harness.verification_result:
            v = harness.verification_result
            scores["verifier"] = f"{'✅' if v.get('passed') else '⚠️'} checks={v.get('checks_run', 0)}, failures={v.get('failure_count', 0)}"
        else:
            scores["verifier"] = "⚠️ SKIP (no verification)"

        # 5. 错误检查
        if harness.error:
            scores["error"] = f"❌ {harness.error}"
        else:
            scores["error"] = "✅ No error"

        eval_result.dimension_scores = scores
        # 判定是否通过：policy 和 dag_execution 必须正确
        eval_result.passed = all(
            "✅" in v for k, v in scores.items()
            if k in ("policy", "dag_execution")
        )

    def print_report(self):
        """打印评估报告"""
        print("\n" + "=" * 70)
        print("  HARNESS v1 回归评估报告")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  用例数: {len(self.results)}")
        print("=" * 70)

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        for r in self.results:
            status = "✅" if r.passed else "❌"
            print(f"\n{status} [{r.case_id}] {r.case_name} ({r.template})")

            if r.old_path:
                old_info = f"dag={r.old_path.dag_executed}, {r.old_path.duration_ms:.0f}ms"
                if r.old_path.error:
                    old_info = f"ERROR: {r.old_path.error[:60]}"
                print(f"    旧路径: {old_info}")

            if r.harness_path:
                h_info = f"dag={r.harness_path.dag_executed}, {r.harness_path.duration_ms:.0f}ms"
                if r.harness_path.policy_deny:
                    h_info = f"DENIED: {r.harness_path.deny_reason[:60]}"
                elif r.harness_path.error:
                    h_info = f"ERROR: {r.harness_path.error[:60]}"
                print(f"    新路径: {h_info}")

            for dim, score in r.dimension_scores.items():
                print(f"    {dim}: {score}")

            if r.notes:
                for note in r.notes:
                    print(f"    📝 {note}")

        print(f"\n{'=' * 70}")
        print(f"  总计: {passed} passed, {failed} failed, {len(self.results)} total")
        if failed == 0:
            print("  ✅ 回归评估全部通过")
        else:
            print("  ❌ 存在失败用例，需要排查")
        print("=" * 70)

    def save_results(self, output_dir: str = "tests/eval/results"):
        """保存结果到 JSON"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"eval_{timestamp}.json")

        data = {
            "timestamp": timestamp,
            "total_cases": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "results": [],
        }

        for r in self.results:
            entry = {
                "case_id": r.case_id,
                "case_name": r.case_name,
                "template": r.template,
                "passed": r.passed,
                "dimension_scores": r.dimension_scores,
                "notes": r.notes,
            }
            if r.old_path:
                entry["old_path"] = {
                    "dag_executed": r.old_path.dag_executed,
                    "duration_ms": r.old_path.duration_ms,
                    "error": r.old_path.error,
                    "tasks_completed": r.old_path.tasks_completed,
                    "tasks_failed": r.old_path.tasks_failed,
                }
            if r.harness_path:
                entry["harness_path"] = {
                    "dag_executed": r.harness_path.dag_executed,
                    "policy_deny": r.harness_path.policy_deny,
                    "deny_reason": r.harness_path.deny_reason,
                    "duration_ms": r.harness_path.duration_ms,
                    "error": r.harness_path.error,
                    "tasks_completed": r.harness_path.tasks_completed,
                    "tasks_failed": r.harness_path.tasks_failed,
                }
            data["results"].append(entry)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"📄 结果已保存: {filepath}")
        return filepath


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Harness v1 回归评估")
    parser.add_argument("--case", type=str, help="只运行指定用例 (e.g. CTP-01)")
    parser.add_argument("--template", type=str, help="只运行指定模板的用例")
    parser.add_argument("--dry-run", action="store_true", help="只打印用例，不执行")
    args = parser.parse_args()

    from tests.eval.cases.harness_regression_cases import EVAL_CASES

    # 过滤用例
    cases = EVAL_CASES
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
    if args.template:
        cases = [c for c in cases if c["template"] == args.template]

    if not cases:
        print("❌ 没有匹配的用例")
        sys.exit(1)

    if args.dry_run:
        print(f"📋 共 {len(cases)} 个用例:")
        for c in cases:
            print(f"  [{c['id']}] {c['name']} ({c['template']})")
        return

    runner = HarnessEvalRunner()

    for case in cases:
        try:
            await runner.run_case(case)
        except Exception as e:
            logger.error(f"❌ 用例 {case['id']} 运行异常: {e}")

    runner.print_report()
    runner.save_results()


if __name__ == "__main__":
    asyncio.run(main())
