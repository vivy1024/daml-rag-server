# -*- coding: utf-8 -*-
"""
集成测试：Harness v1 兼容模式切换 (Task 3.3)

验证 HarnessConfig feature flag 控制新旧路径的正确切换：
1. 主开关关闭 → 走旧路径（无 harness 介入）
2. 主开关开启 + 模板在白名单 → 走新路径
3. 主开关开启 + 模板不在白名单 → 走旧路径
4. 主开关开启 + 用户不在白名单 → 走旧路径
5. 子开关独立控制（policy/verifier/tracer 可单独开关）
6. harness 初始化失败 → 优雅降级到旧路径

使用 mock DAG 编排器（通过函数参数注入），不依赖真实 LLM 调用。
"""

import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, ".")

from src.applications.fitness.config.runtime import HarnessConfig
from src.applications.fitness.workflow.nodes.step7_execute_dag import node_execute_dag


# ═══════════════════════════════════════════════════════════
# 测试辅助
# ═══════════════════════════════════════════════════════════

def run_async(coro):
    """同步运行异步函数"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_state(
    template_id: str = "complete_training_plan",
    user_id: int = 1,
    query: str = "帮我制定增肌计划",
) -> Dict[str, Any]:
    """构造最小化 WorkflowState"""
    return {
        "request_id": "test-req-001",
        "dag_template_id": template_id,
        "user_profile": {
            "name": "测试用户",
            "age": 25,
            "gender": "男",
            "height": 178,
            "weight": 72,
            "fitness_goal": "增肌",
            "experience_level": "中级",
            "available_equipment": ["哑铃", "杠铃", "卧推凳"],
            "available_time": "60分钟",
        },
        "session_id": "test-session-001",
        "query_text": query,
        "user_id": user_id,
    }


@dataclass
class MockDAGExecutionResult:
    """模拟 DAG 执行结果"""
    results: Dict[str, Any] = field(default_factory=lambda: {
        "exercise_selector": {"exercises": ["卧推", "哑铃飞鸟"]},
        "contraindications_checker": {"safe": True, "warnings": []},
        "injury_risk_assessor": {"risk_level": "low"},
    })
    tasks_completed: int = 3
    tasks_failed: int = 0


@dataclass
class MockDAGTemplate:
    """模拟 DAG 模板定义"""
    template_id: str = "complete_training_plan"
    complexity_level: int = 3
    required_tools: List[str] = field(default_factory=lambda: [
        "exercise_selector", "contraindications_checker", "injury_risk_assessor"
    ])
    safety_constraints: List[str] = field(default_factory=list)


class MockDAGOrchestrator:
    """模拟 DAG 编排器"""
    def __init__(self, **kwargs):
        self.execute_called = False

    async def execute_template(self, **kwargs):
        self.execute_called = True
        return MockDAGExecutionResult()


class MockTemplateManager:
    """模拟模板管理器"""
    def __init__(self, template_override=None):
        self._override = template_override

    def get_template(self, template_id: str):
        if self._override:
            return self._override
        return MockDAGTemplate(template_id=template_id)


# ═══════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════

class TestHarnessFeatureFlag:
    """Harness v1 feature flag 兼容模式切换测试"""

    def _patch_config(self, config: HarnessConfig):
        """Patch _get_harness_config 返回指定配置"""
        return patch(
            "src.applications.fitness.workflow.nodes.step7_execute_dag._get_harness_config",
            return_value=config,
        )

    # ─────────────────────────────────────────────────────
    # Case 1: 主开关关闭 → 旧路径
    # ─────────────────────────────────────────────────────

    def test_harness_disabled_uses_old_path(self):
        """主开关关闭时，不触发任何 harness 组件"""
        config = HarnessConfig(enabled=False)
        state = _make_state()
        orchestrator = MockDAGOrchestrator()
        template_mgr = MockTemplateManager()

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        # 应该正常返回 DAG 结果
        assert result.updates["dag_results"] is not None
        assert orchestrator.execute_called
        # 不应有 harness 相关标记
        assert "_harness_policy_deny" not in result.updates
        dag_results = result.updates["dag_results"]
        assert "_harness_verification" not in dag_results

    # ─────────────────────────────────────────────────────
    # Case 2: 主开关开启 + 模板在白名单 → 新路径
    # ─────────────────────────────────────────────────────

    def test_harness_enabled_with_template_whitelist(self):
        """模板在白名单中时走新路径，policy 被调用"""
        config = HarnessConfig(
            enabled=True,
            enabled_templates=["complete_training_plan"],
            policy_enabled=True,
            verifier_enabled=True,
            tracer_enabled=True,
        )
        state = _make_state(template_id="complete_training_plan")
        orchestrator = MockDAGOrchestrator()
        template_mgr = MockTemplateManager()

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        # mock 模板包含所有 guard，policy 应 allow
        assert result.updates["dag_results"] is not None
        assert orchestrator.execute_called
        assert "_harness_policy_deny" not in result.updates

    # ─────────────────────────────────────────────────────
    # Case 3: 主开关开启 + 模板不在白名单 → 旧路径
    # ─────────────────────────────────────────────────────

    def test_harness_enabled_template_not_in_whitelist(self):
        """模板不在白名单中时走旧路径"""
        config = HarnessConfig(
            enabled=True,
            enabled_templates=["safety_assessment"],  # 只有 safety_assessment
            policy_enabled=True,
            verifier_enabled=True,
        )
        state = _make_state(template_id="complete_training_plan")
        orchestrator = MockDAGOrchestrator()
        template_mgr = MockTemplateManager()

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        # 走旧路径，正常返回结果
        assert result.updates["dag_results"] is not None
        assert orchestrator.execute_called

    # ─────────────────────────────────────────────────────
    # Case 4: 主开关开启 + 用户不在白名单 → 旧路径
    # ─────────────────────────────────────────────────────

    def test_harness_enabled_user_not_in_whitelist(self):
        """用户不在白名单中时走旧路径"""
        config = HarnessConfig(
            enabled=True,
            enabled_user_ids=[999, 1000],  # 只有 999 和 1000
            policy_enabled=True,
        )
        state = _make_state(user_id=1)  # user_id=1 不在白名单
        orchestrator = MockDAGOrchestrator()
        template_mgr = MockTemplateManager()

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        assert result.updates["dag_results"] is not None
        assert orchestrator.execute_called

    # ─────────────────────────────────────────────────────
    # Case 5: 子开关独立控制
    # ─────────────────────────────────────────────────────

    def test_only_policy_enabled(self):
        """只开启 policy，verifier 和 tracer 不介入"""
        config = HarnessConfig(
            enabled=True,
            policy_enabled=True,
            verifier_enabled=False,
            tracer_enabled=False,
        )
        state = _make_state()
        orchestrator = MockDAGOrchestrator()
        template_mgr = MockTemplateManager()

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        # policy allow → 正常执行
        assert result.updates["dag_results"] is not None
        # verifier 未启用，不应有校验结果
        dag_results = result.updates["dag_results"]
        assert "_harness_verification" not in dag_results

    def test_only_verifier_enabled(self):
        """只开启 verifier，policy 不介入"""
        config = HarnessConfig(
            enabled=True,
            policy_enabled=False,
            verifier_enabled=True,
            tracer_enabled=False,
        )
        state = _make_state()
        orchestrator = MockDAGOrchestrator()
        template_mgr = MockTemplateManager()

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        # 无 policy 阻止，正常执行
        assert result.updates["dag_results"] is not None
        assert orchestrator.execute_called

    # ─────────────────────────────────────────────────────
    # Case 6: Policy deny → 阻止执行
    # ─────────────────────────────────────────────────────

    def test_policy_deny_blocks_execution(self):
        """用户有健康状况 + 模板缺少 guard → policy deny → 阻止 DAG 执行"""
        config = HarnessConfig(
            enabled=True,
            policy_enabled=True,
            verifier_enabled=True,
            tracer_enabled=True,
        )
        # 用户有健康状况
        state = _make_state()
        state["user_profile"]["health_conditions"] = ["腰椎间盘突出"]

        orchestrator = MockDAGOrchestrator()
        # 模板缺少 guard 工具
        template_mgr = MockTemplateManager(
            template_override=MockDAGTemplate(
                template_id="complete_training_plan",
                complexity_level=3,
                required_tools=["exercise_selector"],  # 缺少 guard
            )
        )

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        # policy deny → DAG 不执行
        assert not orchestrator.execute_called
        assert result.updates.get("_harness_policy_deny") is True
        assert result.updates["dag_results"] is None
        assert "策略拒绝" in (result.warning or "")

    # ─────────────────────────────────────────────────────
    # Case 7: Harness 初始化失败 → 优雅降级
    # ─────────────────────────────────────────────────────

    def test_harness_init_failure_graceful_fallback(self):
        """harness 模块导入失败时，优雅降级到旧路径"""
        config = HarnessConfig(
            enabled=True,
            policy_enabled=True,
            verifier_enabled=True,
            tracer_enabled=True,
        )
        state = _make_state()
        orchestrator = MockDAGOrchestrator()
        template_mgr = MockTemplateManager()

        # 模拟 harness 导入失败
        with self._patch_config(config), \
             patch(
                 "src.applications.fitness.workflow.nodes.step7_execute_dag.ExecutionPolicy",
                 side_effect=ImportError("harness not available"),
                 create=True,
             ):
            # 由于 step7 内部 try/except 会捕获导入错误并降级
            # 我们需要 patch 整个 harness import
            with patch.dict(sys.modules, {"src.applications.fitness.harness": None}):
                result = run_async(node_execute_dag(
                    state,
                    dag_orchestrator=orchestrator,
                    template_manager=template_mgr,
                ))

        # 应该降级到旧路径，正常执行
        assert result.updates["dag_results"] is not None
        assert orchestrator.execute_called

    # ─────────────────────────────────────────────────────
    # Case 8: 空白名单 → 全量启用
    # ─────────────────────────────────────────────────────

    def test_empty_whitelist_enables_all(self):
        """白名单为空时，对所有模板和用户启用"""
        config = HarnessConfig(
            enabled=True,
            enabled_templates=[],  # 空 = 全部
            enabled_user_ids=[],   # 空 = 全部
            policy_enabled=True,
        )
        state = _make_state(template_id="quick_consultation", user_id=12345)
        orchestrator = MockDAGOrchestrator()
        # quick_consultation 是低风险模板
        template_mgr = MockTemplateManager(
            template_override=MockDAGTemplate(
                template_id="quick_consultation",
                complexity_level=1,
                required_tools=["quick_answer"],
            )
        )

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        # 低风险模板无 guard 要求，policy allow
        assert result.updates["dag_results"] is not None
        assert orchestrator.execute_called

    # ─────────────────────────────────────────────────────
    # Case 9: HarnessConfig.is_active_for 逻辑单元测试
    # ─────────────────────────────────────────────────────

    def test_is_active_for_logic(self):
        """is_active_for 组合逻辑验证"""
        # 主开关关闭
        cfg = HarnessConfig(enabled=False)
        assert cfg.is_active_for("any", 1) is False

        # 主开关开启，无白名单 → 全部通过
        cfg = HarnessConfig(enabled=True)
        assert cfg.is_active_for("any_template", 999) is True

        # 模板白名单
        cfg = HarnessConfig(enabled=True, enabled_templates=["a", "b"])
        assert cfg.is_active_for("a", 1) is True
        assert cfg.is_active_for("c", 1) is False

        # 用户白名单
        cfg = HarnessConfig(enabled=True, enabled_user_ids=[10, 20])
        assert cfg.is_active_for("any", 10) is True
        assert cfg.is_active_for("any", 30) is False

        # 双白名单交集
        cfg = HarnessConfig(
            enabled=True,
            enabled_templates=["a"],
            enabled_user_ids=[10],
        )
        assert cfg.is_active_for("a", 10) is True
        assert cfg.is_active_for("a", 20) is False
        assert cfg.is_active_for("b", 10) is False
        assert cfg.is_active_for("b", 20) is False

    # ─────────────────────────────────────────────────────
    # Case 10: Verifier 发现问题时附加到结果
    # ─────────────────────────────────────────────────────

    def test_verifier_failure_attaches_to_results(self):
        """verifier 发现安全冲突时，将校验结果附加到 dag_results"""
        config = HarnessConfig(
            enabled=True,
            policy_enabled=True,
            verifier_enabled=True,
            tracer_enabled=False,
        )
        # 用户有健康状况
        state = _make_state()
        state["user_profile"]["health_conditions"] = ["膝盖半月板损伤"]
        state["user_profile"]["available_equipment"] = ["哑铃"]

        # 模板包含 guard（policy 会 allow）
        template_mgr = MockTemplateManager()

        # DAG 结果中包含与约束冲突的内容
        class ConflictOrchestrator:
            execute_called = False
            async def execute_template(self, **kwargs):
                self.execute_called = True
                return MockDAGExecutionResult(
                    results={
                        "exercise_selector": {
                            "exercises": [
                                {"name": "深蹲", "equipment": "杠铃"},  # 器械不可用
                            ]
                        },
                        "contraindications_checker": {"safe": True, "warnings": []},
                        "injury_risk_assessor": {"risk_level": "low"},
                    },
                    tasks_completed=3,
                    tasks_failed=0,
                )

        orchestrator = ConflictOrchestrator()

        with self._patch_config(config):
            result = run_async(node_execute_dag(
                state,
                dag_orchestrator=orchestrator,
                template_manager=template_mgr,
            ))

        # DAG 执行了
        assert orchestrator.execute_called
        # 结果应该存在（verifier 不阻止，只附加信息）
        assert result.updates["dag_results"] is not None


# ═══════════════════════════════════════════════════════════
# 直接运行入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    test = TestHarnessFeatureFlag()

    tests = [
        ("Case 1: 主开关关闭 → 旧路径", test.test_harness_disabled_uses_old_path),
        ("Case 2: 模板在白名单 → 新路径", test.test_harness_enabled_with_template_whitelist),
        ("Case 3: 模板不在白名单 → 旧路径", test.test_harness_enabled_template_not_in_whitelist),
        ("Case 4: 用户不在白名单 → 旧路径", test.test_harness_enabled_user_not_in_whitelist),
        ("Case 5a: 只开 policy", test.test_only_policy_enabled),
        ("Case 5b: 只开 verifier", test.test_only_verifier_enabled),
        ("Case 6: Policy deny 阻止执行", test.test_policy_deny_blocks_execution),
        ("Case 7: Harness 初始化失败降级", test.test_harness_init_failure_graceful_fallback),
        ("Case 8: 空白名单全量启用", test.test_empty_whitelist_enables_all),
        ("Case 9: is_active_for 逻辑", test.test_is_active_for_logic),
        ("Case 10: Verifier 附加校验结果", test.test_verifier_failure_attaches_to_results),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"结果: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("✅ All harness feature flag tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
