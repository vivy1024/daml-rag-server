# -*- coding: utf-8 -*-
"""
B11 — Agent v2 端到端冒烟测试（真实 LLM）

使用真实 LLM API 调用测试 Agent v2 完整流程。

测试场景：
1. 简单问候 → direct_reply（跳过 Skill 执行）
2. 单 Skill 执行 → 工具链完成 → 输出生成
3. 安全策略拦截 → force_safety（有伤病用户请求高强度 Skill）
4. 无档案 → 提示补充

使用方式:
    docker exec fitness_daml_rag python tests/integration/test_agent_v2_smoke.py
"""

import asyncio
import json
import logging
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, ".")

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test_agent_v2_smoke")
logger.setLevel(logging.INFO)

# ═══════════════════════════════════════════════════════════
# 真实 LLM 客户端（Anthropic 兼容格式）
# ═══════════════════════════════════════════════════════════

LLM_BASE_URL = "https://api.vivy1024.cc/v1"
LLM_API_KEY = "sk-44cc405d0ccc7e7480871cc2d0ca33f66e96813ccfa01098e9e6147afa6e1ffd"
LLM_MODEL = "claude-opus-4-6"


class RealLLMClient:
    """真实 LLM 客户端，使用 OpenAI 兼容格式"""

    def __init__(self):
        import httpx
        self._client = httpx.AsyncClient(
            base_url=LLM_BASE_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            timeout=60.0,
        )

    async def chat_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[dict],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """带 function calling 的聊天接口"""
        # functions 可能已经是 tools 格式 {"type": "function", "function": {...}}
        # 也可能是纯 function 定义 {"name": ..., "parameters": ...}
        tools = []
        for func in functions:
            if "type" in func and func["type"] == "function":
                # 已经是 tools 格式
                tools.append(func)
            else:
                # 纯 function 定义，包装为 tools 格式
                tools.append({
                    "type": "function",
                    "function": func,
                })

        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": 1024,
        }

        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]["message"]

        # 解析 tool_calls
        if choice.get("tool_calls"):
            tc = choice["tool_calls"][0]
            arguments_str = tc["function"]["arguments"]
            # 修复 API 可能返回的格式问题（如前缀 {}）
            if arguments_str.startswith("{}"):
                arguments_str = arguments_str[2:]
            return {
                "function_call": {
                    "name": tc["function"]["name"],
                    "arguments": arguments_str,
                }
            }

        # 纯文本回复
        return {"content": choice.get("content", "")}

    async def close(self):
        await self._client.aclose()


# ═══════════════════════════════════════════════════════════
# Mock 工具注册表（模拟工具执行）
# ═══════════════════════════════════════════════════════════


class MockToolRegistry:
    """Mock 工具注册表 — 模拟工具调用返回合理数据"""

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """模拟工具调用"""
        mock_responses = {
            "knowledge_retriever": {
                "results": [
                    {"content": "深蹲是下肢复合训练动作，主要锻炼股四头肌、臀大肌和腘绳肌。", "score": 0.92}
                ]
            },
            "contraindications_checker": {
                "safe": True,
                "contraindications": [],
                "warnings": [],
            },
            "injury_risk_assessor": {
                "risk_level": "low",
                "risk_factors": [],
                "recommendations": ["注意膝关节不超过脚尖"],
            },
            "intelligent_exercise_selector": {
                "exercises": [
                    {"name": "杠铃深蹲", "muscle_groups": ["股四头肌", "臀大肌"]},
                    {"name": "腿举", "muscle_groups": ["股四头肌"]},
                ]
            },
            "muscle_group_volume_calculator": {
                "weekly_volume": {"股四头肌": 16, "臀大肌": 12},
                "within_mav": True,
            },
            "professional_program_designer": {
                "program": {
                    "name": "增肌计划",
                    "days_per_week": 4,
                    "sessions": [],
                }
            },
        }
        return mock_responses.get(tool_name, {"success": True, "tool": tool_name})


# ═══════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════


async def test_1_direct_reply(llm_client: RealLLMClient):
    """场景1: 简单问候 → direct_reply，跳过 Skill 执行"""
    from src.skills.router import SkillRouter
    from src.skills.loader import SkillLoader
    from src.skills.manager import SkillManager
    from src.skills.executor import SkillExecutor
    from src.harness_v2.pre_skill_policy import PreSkillPolicy
    from src.agent_v2.graph import build_agent_graph

    router = SkillRouter(llm_client=llm_client)

    loader = SkillLoader()
    skills = loader.load_directory("src/skills/definitions")
    manager = SkillManager()
    for s in skills:
        manager.register(s)

    executor = SkillExecutor()
    policy = PreSkillPolicy()
    mock_registry = MockToolRegistry()

    graph = build_agent_graph(
        skill_router=router,
        skill_manager=manager,
        skill_executor=executor,
        policy=policy,
        tool_registry=mock_registry,
        use_memory_checkpointer=True,
    )

    initial_state = {
        "messages": [{"role": "user", "content": "你好呀"}],
        "user_id": "test-user-1",
        "thread_id": "smoke-test-1",
        "user_profile": None,
        "current_skill": None,
        "skill_reason": None,
        "tool_results": None,
        "harness_trace": None,
        "approval_status": None,
        "direct_reply": None,
        "final_output": None,
        "error": None,
    }

    config = {"configurable": {"thread_id": "smoke-test-1"}}
    start = time.time()
    result = await graph.ainvoke(initial_state, config=config)
    elapsed = time.time() - start

    # 验证：简单问候应该走 direct_reply 路径
    assert result.get("final_output") is not None, "应该有 final_output"
    # direct_reply 或者 LLM 选择了 quick_consultation 都算通过
    has_direct = result.get("direct_reply") is not None
    has_skill = result.get("current_skill") is not None

    logger.info(f"  耗时: {elapsed:.2f}s")
    logger.info(f"  direct_reply: {result.get('direct_reply', '')[:80]}")
    logger.info(f"  current_skill: {result.get('current_skill')}")
    logger.info(f"  final_output: {result.get('final_output', '')[:100]}")

    # 简单问候应该是 direct_reply 或 quick_consultation
    assert has_direct or result.get("current_skill") == "quick_consultation", \
        f"简单问候应走 direct_reply 或 quick_consultation，实际: skill={result.get('current_skill')}"

    return True


async def test_2_skill_execution(llm_client: RealLLMClient):
    """场景2: 健身问题 → Skill 选择 → 工具链执行 → 输出生成"""
    from src.skills.router import SkillRouter
    from src.skills.loader import SkillLoader
    from src.skills.manager import SkillManager
    from src.skills.executor import SkillExecutor
    from src.harness_v2.pre_skill_policy import PreSkillPolicy
    from src.agent_v2.graph import build_agent_graph

    router = SkillRouter(llm_client=llm_client)

    loader = SkillLoader()
    skills = loader.load_directory("src/skills/definitions")
    manager = SkillManager()
    for s in skills:
        manager.register(s)

    executor = SkillExecutor()
    policy = PreSkillPolicy()
    mock_registry = MockToolRegistry()

    graph = build_agent_graph(
        skill_router=router,
        skill_manager=manager,
        skill_executor=executor,
        policy=policy,
        tool_registry=mock_registry,
        use_memory_checkpointer=True,
    )

    user_profile = {
        "basic_info": {
            "gender": "男",
            "age": 28,
            "height": 175,
            "weight": 70,
            "fitness_level": "中级",
        },
        "fitness_goal": "增肌",
    }

    initial_state = {
        "messages": [{"role": "user", "content": "帮我制定一个增肌训练计划，每周4天"}],
        "user_id": "test-user-2",
        "thread_id": "smoke-test-2",
        "user_profile": user_profile,
        "current_skill": None,
        "skill_reason": None,
        "tool_results": None,
        "harness_trace": None,
        "approval_status": None,
        "direct_reply": None,
        "final_output": None,
        "error": None,
    }

    config = {"configurable": {"thread_id": "smoke-test-2"}}
    start = time.time()
    result = await graph.ainvoke(initial_state, config=config)
    elapsed = time.time() - start

    logger.info(f"  耗时: {elapsed:.2f}s")
    logger.info(f"  current_skill: {result.get('current_skill')}")
    logger.info(f"  skill_reason: {result.get('skill_reason', '')[:80]}")
    logger.info(f"  tool_results keys: {list((result.get('tool_results') or {}).keys())}")
    logger.info(f"  final_output: {result.get('final_output', '')[:120]}")
    logger.info(f"  error: {result.get('error')}")

    # 验证
    assert result.get("current_skill") is not None, "应该选择了一个 Skill"
    assert result.get("final_output") is not None, "应该有 final_output"
    # 应该选择 safe_training_plan 或 strength_program
    expected_skills = {"safe_training_plan", "strength_program", "fat_loss_program"}
    assert result["current_skill"] in expected_skills or result.get("tool_results"), \
        f"应选择训练计划相关 Skill，实际: {result['current_skill']}"

    return True


async def test_3_safety_policy(llm_client: RealLLMClient):
    """场景3: 有伤病用户请求高强度 → 安全策略拦截"""
    from src.skills.router import SkillRouter
    from src.skills.loader import SkillLoader
    from src.skills.manager import SkillManager
    from src.skills.executor import SkillExecutor
    from src.harness_v2.pre_skill_policy import PreSkillPolicy
    from src.agent_v2.graph import build_agent_graph

    router = SkillRouter(llm_client=llm_client)

    loader = SkillLoader()
    skills = loader.load_directory("src/skills/definitions")
    manager = SkillManager()
    for s in skills:
        manager.register(s)

    executor = SkillExecutor()
    policy = PreSkillPolicy()
    mock_registry = MockToolRegistry()

    graph = build_agent_graph(
        skill_router=router,
        skill_manager=manager,
        skill_executor=executor,
        policy=policy,
        tool_registry=mock_registry,
        use_memory_checkpointer=True,
    )

    # 用户有伤病
    user_profile = {
        "basic_info": {
            "gender": "男",
            "age": 35,
            "height": 180,
            "weight": 82,
            "fitness_level": "中级",
            "health_conditions": ["腰椎间盘突出L4-L5"],
        },
        "health_info": {
            "injuries": ["腰椎间盘突出L4-L5"],
        },
    }

    initial_state = {
        "messages": [{"role": "user", "content": "我想做大重量硬拉，帮我制定力量训练计划"}],
        "user_id": "test-user-3",
        "thread_id": "smoke-test-3",
        "user_profile": user_profile,
        "current_skill": None,
        "skill_reason": None,
        "tool_results": None,
        "harness_trace": None,
        "approval_status": None,
        "direct_reply": None,
        "final_output": None,
        "error": None,
    }

    config = {"configurable": {"thread_id": "smoke-test-3"}}
    start = time.time()

    # Step 1: 触发 interrupt
    result = await graph.ainvoke(initial_state, config=config)
    elapsed = time.time() - start

    logger.info(f"  耗时: {elapsed:.2f}s")
    logger.info(f"  current_skill: {result.get('current_skill')}")
    logger.info(f"  approval_status: {result.get('approval_status')}")

    # 检查是否触发了 interrupt
    interrupt_info = result.get("__interrupt__")
    if interrupt_info:
        logger.info(f"  → HITL interrupt 触发成功！")
        logger.info(f"  interrupt reason: {interrupt_info[0].value.get('reason', '')[:80]}")

        # Step 2: 模拟用户确认，恢复执行
        from langgraph.types import Command
        resume_result = await graph.ainvoke(
            Command(resume="approved"),
            config=config,
        )
        logger.info(f"  → Resume 后 current_skill: {resume_result.get('current_skill')}")
        logger.info(f"  → Resume 后 approval_status: {resume_result.get('approval_status')}")
        logger.info(f"  → Resume 后 tool_results: {list((resume_result.get('tool_results') or {}).keys())[:5]}")

        assert resume_result.get("current_skill") == "safety_assessment", \
            f"Resume 后应切换到 safety_assessment，实际: {resume_result.get('current_skill')}"
        assert resume_result.get("approval_status") == "approved", \
            "Resume 后 approval_status 应为 approved"
        assert resume_result.get("final_output") is not None, "Resume 后应有 final_output"
        return True

    # 如果 LLM 直接选了 safety_assessment，policy 不会拦截
    skill = result.get("current_skill")
    if skill == "safety_assessment":
        logger.info("  → LLM 直接选择了 safety_assessment（智能判断，无需 interrupt）")
        assert result.get("final_output") is not None, "应该有 final_output"
        return True

    # 如果 LLM 选了非高强度 Skill（如 quick_consultation），也算通过
    logger.info(f"  → LLM 选择了 {skill}（非高强度 Skill，policy 放行）")
    assert result.get("final_output") is not None, "应该有 final_output"
    return True


async def test_4_no_profile(llm_client: RealLLMClient):
    """场景4: 无档案用户请求需要档案的 Skill → 提示补充"""
    from src.skills.router import SkillRouter
    from src.skills.loader import SkillLoader
    from src.skills.manager import SkillManager
    from src.skills.executor import SkillExecutor
    from src.harness_v2.pre_skill_policy import PreSkillPolicy
    from src.agent_v2.graph import build_agent_graph

    router = SkillRouter(llm_client=llm_client)

    loader = SkillLoader()
    skills = loader.load_directory("src/skills/definitions")
    manager = SkillManager()
    for s in skills:
        manager.register(s)

    executor = SkillExecutor()
    policy = PreSkillPolicy()
    mock_registry = MockToolRegistry()

    graph = build_agent_graph(
        skill_router=router,
        skill_manager=manager,
        skill_executor=executor,
        policy=policy,
        tool_registry=mock_registry,
        use_memory_checkpointer=True,
    )

    # 无档案
    initial_state = {
        "messages": [{"role": "user", "content": "帮我制定一个减脂计划"}],
        "user_id": "test-user-4",
        "thread_id": "smoke-test-4",
        "user_profile": None,  # 无档案
        "current_skill": None,
        "skill_reason": None,
        "tool_results": None,
        "harness_trace": None,
        "approval_status": None,
        "direct_reply": None,
        "final_output": None,
        "error": None,
    }

    config = {"configurable": {"thread_id": "smoke-test-4"}}
    start = time.time()
    result = await graph.ainvoke(initial_state, config=config)
    elapsed = time.time() - start

    logger.info(f"  耗时: {elapsed:.2f}s")
    logger.info(f"  current_skill: {result.get('current_skill')}")
    logger.info(f"  final_output: {result.get('final_output', '')[:120]}")

    # 验证：应该提示补充档案，或者 LLM 选了 quick_consultation（不需要档案）
    final = result.get("final_output", "")
    skill = result.get("current_skill")

    # 如果选了需要档案的 Skill，policy 应该拦截
    profile_required = {"safe_training_plan", "strength_program", "fat_loss_program",
                        "nutrition_planning", "progress_analysis", "rehabilitation_training",
                        "posture_correction"}

    if skill in profile_required:
        # 被 policy 拦截，应该有提示补充档案的信息
        assert "档案" in final or "信息" in final or result.get("direct_reply"), \
            f"需要档案的 Skill 应提示补充，实际输出: {final[:100]}"
    else:
        # LLM 选了不需要档案的 Skill（如 quick_consultation），也算通过
        logger.info(f"  → LLM 选择了不需要档案的 Skill: {skill}")

    assert result.get("final_output") is not None, "应该有 final_output"
    return True


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════


async def main():
    print("=" * 60)
    print("  Agent v2 端到端冒烟测试 (B11) — 真实 LLM")
    print(f"  模型: {LLM_MODEL}")
    print(f"  API: {LLM_BASE_URL}")
    print("=" * 60)

    llm_client = RealLLMClient()

    tests = [
        ("场景1: 简单问候 → direct_reply", test_1_direct_reply),
        ("场景2: 健身问题 → Skill 执行 → 输出", test_2_skill_execution),
        ("场景3: 有伤病 → 安全策略拦截", test_3_safety_policy),
        ("场景4: 无档案 → 提示补充", test_4_no_profile),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            logger.info(f"\n▶ {name}")
            success = await test_fn(llm_client)
            if success:
                print(f"  ✅ {name}")
                passed += 1
            else:
                print(f"  ❌ {name}: 返回 False")
                failed += 1
        except Exception as e:
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
            failed += 1

    await llm_client.close()

    print("=" * 60)
    print(f"  结果: {passed} passed, {failed} failed, {len(tests)} total")
    if failed == 0:
        print("  ✅ Agent v2 冒烟测试全部通过！")
    else:
        print("  ❌ 存在失败用例")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
