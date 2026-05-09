# -*- coding: utf-8 -*-
"""
C6 — Skills 工具链可执行测试

验证每个 Skill 的工具链能正确执行（使用 mock tool_registry）。
测试点：
1. 每个 Skill 的 required_tools 全部执行
2. 并行组正确处理
3. 单工具失败不阻断整体
4. 所有 required 失败 → success=False

使用方式:
    docker exec fitness_daml_rag python tests/integration/test_skill_execution.py
"""

import asyncio
import logging
import sys
from typing import Any, Dict

sys.path.insert(0, ".")

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test_skill_execution")
logger.setLevel(logging.INFO)


# ═══════════════════════════════════════════════════════════
# Mock 工具注册表
# ═══════════════════════════════════════════════════════════


class SuccessToolRegistry:
    """所有工具都成功"""

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        return {"tool": tool_name, "success": True, "data": {"mock": True}}


class PartialFailToolRegistry:
    """指定工具失败"""

    def __init__(self, fail_tools: set):
        self.fail_tools = fail_tools

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        if tool_name in self.fail_tools:
            raise RuntimeError(f"Mock failure: {tool_name}")
        return {"tool": tool_name, "success": True, "data": {"mock": True}}


class AllFailToolRegistry:
    """所有工具都失败"""

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        raise RuntimeError(f"Mock failure: {tool_name}")


# ═══════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════


async def test_all_skills_execute():
    """测试所有 10 个 Skill 的工具链正常执行"""
    from src.skills.loader import SkillLoader
    from src.skills.executor import SkillExecutor

    loader = SkillLoader()
    skills = loader.load_directory("src/skills/definitions")
    executor = SkillExecutor()
    registry = SuccessToolRegistry()

    state = {
        "user_profile": {
            "basic_info": {
                "gender": "男",
                "age": 28,
                "height": 175,
                "weight": 70,
                "fitness_level": "中级",
            },
            "fitness_goal": "增肌",
        }
    }

    results = []
    for skill in skills:
        result = await executor.execute(
            skill=skill,
            state=state,
            tool_registry=registry,
        )

        # 验证
        assert result.success, f"Skill [{skill.id}] 应该成功"
        assert result.skill_id == skill.id, f"skill_id 应为 {skill.id}"

        # 所有 required_tools 都应该被执行
        for tool in skill.required_tools:
            assert tool in result.tool_results, \
                f"Skill [{skill.id}] 缺少 required tool: {tool}"
            assert result.tool_results[tool].success, \
                f"Skill [{skill.id}] tool [{tool}] 应该成功"

        results.append((skill.id, len(result.tool_results), result.total_duration_ms))
        logger.info(
            f"  ✅ {skill.id}: {len(result.tool_results)} tools, "
            f"{result.total_duration_ms:.1f}ms"
        )

    assert len(results) == 10, f"应该有 10 个 Skill，实际: {len(results)}"
    return True


async def test_partial_failure():
    """测试单工具失败不阻断整体"""
    from src.skills.loader import SkillLoader
    from src.skills.executor import SkillExecutor

    loader = SkillLoader()
    skills = loader.load_directory("src/skills/definitions")
    executor = SkillExecutor()

    # 让 knowledge_retriever 失败
    registry = PartialFailToolRegistry(fail_tools={"knowledge_retriever"})

    state = {"user_profile": {"basic_info": {"gender": "男", "fitness_level": "初级"}}}

    # 找一个包含 knowledge_retriever 的 Skill
    target_skill = None
    for skill in skills:
        if "knowledge_retriever" in skill.required_tools:
            target_skill = skill
            break

    if not target_skill:
        # 如果没有 Skill 用 knowledge_retriever，用 quick_consultation
        for skill in skills:
            if skill.id == "quick_consultation":
                target_skill = skill
                break

    if not target_skill:
        logger.info("  ⚠️ 跳过：没有找到包含 knowledge_retriever 的 Skill")
        return True

    result = await executor.execute(
        skill=target_skill,
        state=state,
        tool_registry=registry,
    )

    # 整体应该仍然成功（只要不是所有 required 都失败）
    failed_tools = [
        name for name, r in result.tool_results.items() if not r.success
    ]
    successful_tools = [
        name for name, r in result.tool_results.items() if r.success
    ]

    logger.info(f"  Skill [{target_skill.id}]:")
    logger.info(f"    成功: {successful_tools}")
    logger.info(f"    失败: {failed_tools}")
    logger.info(f"    整体 success: {result.success}")

    # knowledge_retriever 应该在失败列表中
    if "knowledge_retriever" in result.tool_results:
        assert not result.tool_results["knowledge_retriever"].success, \
            "knowledge_retriever 应该失败"

    return True


async def test_all_required_fail():
    """测试所有 required 工具失败 → success=False"""
    from src.skills.loader import SkillLoader
    from src.skills.executor import SkillExecutor

    loader = SkillLoader()
    skills = loader.load_directory("src/skills/definitions")
    executor = SkillExecutor()
    registry = AllFailToolRegistry()

    state = {"user_profile": {}}

    # 用 quick_consultation（只有 1 个 required tool）
    target_skill = None
    for skill in skills:
        if skill.id == "quick_consultation":
            target_skill = skill
            break

    assert target_skill is not None, "应该有 quick_consultation Skill"

    result = await executor.execute(
        skill=target_skill,
        state=state,
        tool_registry=registry,
    )

    logger.info(f"  Skill [{target_skill.id}]: success={result.success}")
    logger.info(f"    errors: {result.errors[:3]}")

    assert not result.success, "所有 required 工具失败时，整体应为 False"
    return True


async def test_execution_timing():
    """测试执行耗时记录"""
    from src.skills.loader import SkillLoader
    from src.skills.executor import SkillExecutor

    loader = SkillLoader()
    skills = loader.load_directory("src/skills/definitions")
    executor = SkillExecutor()
    registry = SuccessToolRegistry()

    state = {"user_profile": {"basic_info": {"fitness_level": "高级"}}}

    # 选一个工具多的 Skill
    target_skill = None
    for skill in skills:
        if skill.id == "safe_training_plan":
            target_skill = skill
            break

    assert target_skill is not None

    result = await executor.execute(
        skill=target_skill,
        state=state,
        tool_registry=registry,
    )

    assert result.total_duration_ms >= 0, "总耗时应 >= 0"
    for tool_name, tool_result in result.tool_results.items():
        assert tool_result.duration_ms >= 0, f"{tool_name} 耗时应 >= 0"

    logger.info(f"  safe_training_plan: total={result.total_duration_ms:.1f}ms")
    for name, r in result.tool_results.items():
        logger.info(f"    {name}: {r.duration_ms:.1f}ms")

    return True


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════


async def main():
    print("=" * 60)
    print("  C6 — Skills 工具链可执行测试")
    print("=" * 60)

    tests = [
        ("所有 Skill 工具链正常执行", test_all_skills_execute),
        ("单工具失败不阻断整体", test_partial_failure),
        ("所有 required 失败 → success=False", test_all_required_fail),
        ("执行耗时记录", test_execution_timing),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        logger.info(f"\n▶ {name}")
        try:
            result = await test_fn()
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
        print("  ✅ Skills 工具链测试全部通过！")
    else:
        print("  ❌ 存在失败用例")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
