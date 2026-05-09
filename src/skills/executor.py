# -*- coding: utf-8 -*-
"""
SkillExecutor

按 Skill 定义的工具链执行工具调用，支持并行组和容错。
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Protocol

from .definition import SkillDefinition

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """单个工具执行结果

    Attributes:
        tool_name: 工具名称
        success: 是否成功
        data: 工具返回数据
        error: 错误信息（失败时）
        duration_ms: 执行耗时（毫秒）
    """

    tool_name: str
    success: bool
    data: Any = None
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class ExecutionResult:
    """Skill 执行总结果

    Attributes:
        skill_id: 执行的 Skill ID
        tool_results: 各工具执行结果
        success: 整体是否成功（至少一个 required 工具成功）
        total_duration_ms: 总耗时
        errors: 错误列表
    """

    skill_id: str
    tool_results: Dict[str, ToolResult] = field(default_factory=dict)
    success: bool = True
    total_duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class ToolRegistryProtocol(Protocol):
    """工具注册表协议"""

    async def call_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Any:
        """调用指定工具"""
        ...


class SkillExecutor:
    """Skill 执行器

    按 SkillDefinition 中定义的 required_tools 顺序执行工具，
    支持并行组（无依赖的工具可并行执行）和单工具容错。
    """

    def __init__(
        self,
        parallel_groups: Optional[Dict[str, List[List[str]]]] = None,
    ) -> None:
        """初始化执行器

        Args:
            parallel_groups: 并行组配置，格式为
                {skill_id: [[tool1, tool2], [tool3]]}
                同一子列表内的工具并行执行，子列表之间顺序执行。
                如果未配置，则所有 required_tools 顺序执行。
        """
        self._parallel_groups = parallel_groups or {}

    async def execute(
        self,
        skill: SkillDefinition,
        state: Dict[str, Any],
        tool_registry: ToolRegistryProtocol,
    ) -> ExecutionResult:
        """执行 Skill 的工具链

        Args:
            skill: Skill 定义
            state: 当前状态（包含用户档案、对话历史等）
            tool_registry: 工具注册表

        Returns:
            ExecutionResult 执行结果
        """
        start_time = time.time()
        result = ExecutionResult(skill_id=skill.id)

        # 确定执行顺序
        groups = self._get_execution_groups(skill)

        for group in groups:
            if len(group) == 1:
                # 单工具顺序执行
                tool_result = await self._execute_tool(
                    group[0], state, tool_registry, result
                )
                result.tool_results[group[0]] = tool_result
            else:
                # 并行执行组内工具
                tasks = [
                    self._execute_tool(tool_name, state, tool_registry, result)
                    for tool_name in group
                ]
                group_results = await asyncio.gather(*tasks)
                for tool_name, tool_result in zip(group, group_results):
                    result.tool_results[tool_name] = tool_result

        # 执行可选工具（根据上下文判断）
        for tool_name in skill.optional_tools:
            if self._should_run_optional(tool_name, state, result):
                tool_result = await self._execute_tool(
                    tool_name, state, tool_registry, result
                )
                result.tool_results[tool_name] = tool_result

        # 计算总耗时和整体状态
        result.total_duration_ms = (time.time() - start_time) * 1000

        # 如果所有 required 工具都失败，标记整体失败
        required_results = [
            result.tool_results.get(t)
            for t in skill.required_tools
            if result.tool_results.get(t)
        ]
        if required_results and all(not r.success for r in required_results):
            result.success = False

        logger.info(
            f"Skill [{skill.id}] 执行完成: "
            f"{sum(1 for r in result.tool_results.values() if r.success)}"
            f"/{len(result.tool_results)} 工具成功, "
            f"耗时 {result.total_duration_ms:.1f}ms"
        )

        return result

    async def _execute_tool(
        self,
        tool_name: str,
        state: Dict[str, Any],
        tool_registry: ToolRegistryProtocol,
        current_result: ExecutionResult,
    ) -> ToolResult:
        """执行单个工具

        Args:
            tool_name: 工具名称
            state: 当前状态
            tool_registry: 工具注册表
            current_result: 当前执行结果（可用于获取前序工具结果）

        Returns:
            ToolResult 工具执行结果
        """
        start_time = time.time()

        try:
            # 构建工具参数（包含状态和前序结果）
            params = self._build_tool_params(
                tool_name, state, current_result
            )
            data = await tool_registry.call_tool(tool_name, params)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"工具 [{tool_name}] 执行成功, 耗时 {duration_ms:.1f}ms"
            )
            return ToolResult(
                tool_name=tool_name,
                success=True,
                data=data,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"工具 [{tool_name}] 执行失败: {str(e)}"
            logger.warning(error_msg)
            current_result.errors.append(error_msg)

            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    def _get_execution_groups(
        self, skill: SkillDefinition
    ) -> List[List[str]]:
        """获取工具执行分组

        如果有并行组配置则使用配置，否则每个工具单独一组（顺序执行）。

        Args:
            skill: Skill 定义

        Returns:
            执行分组列表
        """
        if skill.id in self._parallel_groups:
            return self._parallel_groups[skill.id]

        # 默认：每个 required_tool 单独一组，顺序执行
        return [[tool] for tool in skill.required_tools]

    def _build_tool_params(
        self,
        tool_name: str,
        state: Dict[str, Any],
        current_result: ExecutionResult,
    ) -> Dict[str, Any]:
        """构建工具调用参数

        Args:
            tool_name: 工具名称
            state: 当前状态
            current_result: 当前已有的执行结果

        Returns:
            工具参数字典
        """
        params: Dict[str, Any] = {}

        # 传递用户档案
        if "user_profile" in state:
            params["user_profile"] = state["user_profile"]

        # 传递用户消息
        if "messages" in state:
            params["messages"] = state["messages"]

        # 传递前序工具结果
        if current_result.tool_results:
            params["previous_results"] = {
                name: r.data
                for name, r in current_result.tool_results.items()
                if r.success
            }

        # 传递额外上下文
        if "context" in state:
            params["context"] = state["context"]

        return params

    def _should_run_optional(
        self,
        tool_name: str,
        state: Dict[str, Any],
        current_result: ExecutionResult,
    ) -> bool:
        """判断是否应该执行可选工具

        Args:
            tool_name: 工具名称
            state: 当前状态
            current_result: 当前执行结果

        Returns:
            是否应该执行
        """
        # 如果前序工具全部失败，不执行可选工具
        if not current_result.success:
            return False

        # movement_pattern_balancer: 当有多个动作时执行
        if tool_name == "movement_pattern_balancer":
            exercises = current_result.tool_results.get(
                "intelligent_exercise_selector"
            )
            if exercises and exercises.success:
                data = exercises.data
                if isinstance(data, dict):
                    return len(data.get("exercises", [])) > 3
                if isinstance(data, list):
                    return len(data) > 3

        # periodized_program_designer: 当用户有明确周期化需求时
        if tool_name == "periodized_program_designer":
            user_profile = state.get("user_profile", {})
            return user_profile.get("experience_level") in (
                "intermediate",
                "advanced",
            )

        # 默认执行
        return True
