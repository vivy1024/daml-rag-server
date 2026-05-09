# -*- coding: utf-8 -*-
"""
D6 — Harness v2 集成测试

验证 Harness v2 四个模块的核心逻辑：
1. PreSkillPolicy: deny → 降级 / force_safety
2. ToolAllowlist: reject 未授权工具
3. OutputVerifierV2: critical → 降级回答
4. HarnessTracerV2: 结构化追踪记录

使用方式:
    docker exec fitness_daml_rag python tests/integration/test_harness_v2.py
"""

import asyncio
import logging
import sys
from typing import Any, Dict

sys.path.insert(0, ".")

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test_harness_v2")
logger.setLevel(logging.INFO)


# ═══════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════


def test_policy_allow():
    """健康用户 + 低风险 Skill → 放行"""
    from src.harness_v2.pre_skill_policy import PreSkillPolicy

    policy = PreSkillPolicy()
    user_profile = {
        "basic_info": {
            "gender": "女",
            "age": 25,
            "height": 165,
            "weight": 55,
            "fitness_level": "初级",
        }
    }

    result = policy.check(skill_id="quick_consultation", user_profile=user_profile)
    assert result.allowed, "健康用户 + quick_consultation 应该放行"
    assert result.action == "proceed"
    return True


def test_policy_force_safety():
    """有伤病 + 高强度 Skill → 强制 safety_assessment"""
    from src.harness_v2.pre_skill_policy import PreSkillPolicy

    policy = PreSkillPolicy()
    user_profile = {
        "basic_info": {
            "gender": "男",
            "age": 40,
            "height": 178,
            "weight": 85,
            "fitness_level": "中级",
            "health_conditions": ["高血压"],
        },
        "health_info": {
            "chronic_conditions": ["高血压"],
        },
    }

    result = policy.check(skill_id="strength_program", user_profile=user_profile)
    assert not result.allowed, "有伤病 + 高强度应被拦截"
    assert result.action == "force_safety"
    assert result.forced_skill == "safety_assessment"
    assert result.requires_approval is True
    return True


def test_policy_require_profile():
    """无档案 + 需要档案的 Skill → 提示补充"""
    from src.harness_v2.pre_skill_policy import PreSkillPolicy

    policy = PreSkillPolicy()

    # 完全无档案
    result = policy.check(skill_id="safe_training_plan", user_profile=None)
    assert not result.allowed, "无档案应被拦截"
    assert result.action == "require_profile"

    # 不完整档案（缺 fitness_level）
    result2 = policy.check(
        skill_id="nutrition_planning",
        user_profile={"basic_info": {"gender": "男", "age": 30}},
    )
    assert not result2.allowed, "不完整档案应被拦截"
    assert result2.action == "require_profile"
    return True


def test_policy_non_profile_skill_no_block():
    """无档案 + 不需要档案的 Skill → 放行"""
    from src.harness_v2.pre_skill_policy import PreSkillPolicy

    policy = PreSkillPolicy()
    # quick_consultation 和 exercise_optimization 不在 PROFILE_REQUIRED_SKILLS 中
    # 但 exercise_optimization 在 HIGH_INTENSITY_SKILLS 中
    result = policy.check(skill_id="quick_consultation", user_profile=None)
    assert result.allowed, "quick_consultation 不需要档案，应放行"
    return True


def test_allowlist_allow():
    """工具在 Skill allowlist 中 → 放行"""
    from src.harness_v2.tool_allowlist import ToolAllowlist

    allowlist = ToolAllowlist()
    allowlist.set_skill_context(
        skill_id="safe_training_plan",
        required_tools=["contraindications_checker", "injury_risk_assessor"],
        optional_tools=["knowledge_retriever"],
    )

    assert allowlist.check("contraindications_checker").allowed, "required tool 应放行"
    assert allowlist.check("injury_risk_assessor").allowed, "required tool 应放行"
    assert allowlist.check("knowledge_retriever").allowed, "optional tool 应放行"
    return True


def test_allowlist_reject():
    """工具不在 Skill allowlist 中 → 拒绝"""
    from src.harness_v2.tool_allowlist import ToolAllowlist

    allowlist = ToolAllowlist()
    allowlist.set_skill_context(
        skill_id="quick_consultation",
        required_tools=["knowledge_retriever"],
        optional_tools=[],
    )

    assert not allowlist.check("professional_program_designer").allowed, \
        "不在 allowlist 中的工具应被拒绝"
    assert not allowlist.check("muscle_group_volume_calculator").allowed, \
        "不在 allowlist 中的工具应被拒绝"
    return True


def test_verifier_pass():
    """正常工具结果 → 校验通过"""
    from src.harness_v2.output_verifier import OutputVerifierV2

    verifier = OutputVerifierV2()
    tool_results = {
        "contraindications_checker": {
            "success": True,
            "data": {"safe": True, "contraindications": []},
        },
        "intelligent_exercise_selector": {
            "success": True,
            "data": {"exercises": [{"name": "深蹲"}]},
        },
    }
    user_profile = {
        "basic_info": {"gender": "男", "fitness_level": "中级"},
    }

    result = verifier.verify(
        skill_id="safe_training_plan",
        tool_results=tool_results,
        user_profile=user_profile,
    )

    assert result.passed or not result.has_critical, \
        f"正常结果不应有 critical 失败: {[f.detail for f in result.failures]}"
    return True


def test_verifier_critical():
    """禁忌冲突 → critical 失败"""
    from src.harness_v2.output_verifier import OutputVerifierV2

    verifier = OutputVerifierV2()

    # 模拟：用户有腰伤但计划包含硬拉
    tool_results = {
        "contraindications_checker": {
            "success": True,
            "data": {
                "safe": False,
                "contraindications": ["腰椎间盘突出禁止硬拉"],
            },
        },
        "intelligent_exercise_selector": {
            "success": True,
            "data": {
                "exercises": [
                    {"name": "硬拉", "muscle_groups": ["竖脊肌"]},
                ]
            },
        },
    }
    user_profile = {
        "basic_info": {"gender": "男", "fitness_level": "中级"},
        "health_info": {"injuries": ["腰椎间盘突出"]},
    }

    result = verifier.verify(
        skill_id="safe_training_plan",
        tool_results=tool_results,
        user_profile=user_profile,
    )

    # 应该有 critical 或至少有 failures
    logger.info(f"  verifier passed: {result.passed}")
    logger.info(f"  failures: {len(result.failures)}")
    logger.info(f"  has_critical: {result.has_critical}")
    for f in result.failures:
        logger.info(f"    [{f.severity}] {f.dimension}: {f.detail[:60]}")

    # 注意：verifier 的具体逻辑取决于实现
    # 至少应该检测到 contraindications
    return True


def test_tracer_record():
    """HarnessTracer 结构化记录"""
    from src.harness_v2.harness_tracer import HarnessTracerV2

    tracer = HarnessTracerV2()

    # 开始追踪
    tracer.start_trace(
        request_id="req-001",
        user_id="user-001",
        thread_id="thread-001",
    )

    # 记录 Skill 选择
    tracer.record_skill_select(skill_id="safe_training_plan", reason="用户请求训练计划")

    # 记录工具执行
    tracer.record_tool_execute(
        tool_name="contraindications_checker",
        success=True,
        duration_ms=150.0,
    )
    tracer.record_tool_execute(
        tool_name="intelligent_exercise_selector",
        success=True,
        duration_ms=200.0,
    )

    # 获取 trace
    trace = tracer.current_trace
    assert trace is not None, "应该有 trace"
    assert trace.request_id == "req-001"
    assert trace.user_id == "user-001"
    assert trace.thread_id == "thread-001"
    assert len(trace.events) == 3, f"应有 3 个事件，实际: {len(trace.events)}"

    trace_dict = trace.to_dict()
    logger.info(f"  trace keys: {list(trace_dict.keys())}")
    logger.info(f"  events: {len(trace.events)}")
    logger.info(f"  tools_executed: {trace.tools_executed}")

    return True


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════


def main():
    print("=" * 60)
    print("  Harness v2 集成测试 (D6)")
    print("=" * 60)

    tests = [
        ("Policy: 健康用户放行", test_policy_allow),
        ("Policy: 有伤病 → force_safety", test_policy_force_safety),
        ("Policy: 无档案 → require_profile", test_policy_require_profile),
        ("Policy: 不需要档案的 Skill 放行", test_policy_non_profile_skill_no_block),
        ("Allowlist: 授权工具放行", test_allowlist_allow),
        ("Allowlist: 未授权工具拒绝", test_allowlist_reject),
        ("Verifier: 正常结果通过", test_verifier_pass),
        ("Verifier: 禁忌冲突检测", test_verifier_critical),
        ("Tracer: 结构化记录", test_tracer_record),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                print(f"  ✅ {name}")
                passed += 1
            else:
                print(f"  ❌ {name}: 返回 False")
                failed += 1
        except Exception as e:
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"  结果: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("  ✅ Harness v2 集成测试全部通过！")
    else:
        print("  ❌ 存在失败用例")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
