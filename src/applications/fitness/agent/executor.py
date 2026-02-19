# -*- coding: utf-8 -*-
"""
Agent 执行器（Skills 版）

封装 LangGraph 图的调用入口，提供 execute() 和 stream_execute() 方法。

v2.0 变化：
- 初始化时创建 SkillManager，从 DAG 模板注册 Skills
- System prompt 包含 Skills 列表（渐进式披露 Level 1）
- tool_schemas 包含 load_skill + 辅助工具
- LLM 通过 load_skill 获取 Skill 详情后再调用工具

版本: v2.0.0
日期: 2026-02-19
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, AsyncIterator, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .state import AgentState
from .graph import build_agent_graph
from .llm_adapter import ToolCallableLLM

logger = logging.getLogger(__name__)


def _build_skills_system_prompt(skills_prompt: str) -> str:
    """构建包含 Skills 列表的 system prompt"""
    return f"""你是玉珍健身的AI教练助手。你可以通过调用技能（Skills）来完成复杂任务。

{skills_prompt}

## 工作流程
1. 分析用户问题，判断需要哪些技能
2. 调用 load_skill(skill_id) 获取技能的详细指令和工具列表
3. 根据技能指令调用相应工具获取数据
4. 综合所有数据生成专业、友好的中文回答

## 重要规则
- 复杂问题可以组合多个技能（如：安全评估 + 训练计划 + 营养规划）
- 必须先 load_skill 再调用技能内的工具
- 简单问候或闲聊可以直接回答，不需要调用技能
- 涉及伤病、禁忌症时，必须先调用安全相关技能
- 每次只调用必要的工具，避免冗余

## 📐 输出格式要求（前端渲染）
你的回答将直接在移动端App中以Markdown渲染，必须严格遵守：
1. 使用标准Markdown：标题用 ##/###，列表用 -/1.，加粗用 **文字**
2. 每个主要段落标题前加一个相关emoji（如 💪🏋️🥗⚠️📊）
3. 结构清晰，用空行分隔段落，每段不超过4-5行
4. 禁止HTML标签和代码块包裹普通文本
5. 安全/禁忌信息用 > ⚠️ 引用块格式"""


FALLBACK_SYSTEM_PROMPT = (
    "你是玉珍健身的AI教练助手。根据用户的问题，决定是否需要调用工具获取数据，"
    "还是直接回答。每次只调用必要的工具，避免冗余调用。"
    "回答时使用中文，专业但友好。"
)


def _build_load_skill_schema(skill_ids: List[str]) -> dict:
    """构建 load_skill 的 OpenAI function-calling schema"""
    return {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": (
                "加载技能的完整指令。在执行任何技能前，必须先调用此工具获取详细指令和工具列表。"
                f"可用技能: {', '.join(skill_ids)}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": f"技能ID，可选值: {', '.join(skill_ids)}",
                        "enum": skill_ids,
                    }
                },
                "required": ["skill_id"],
            },
        },
    }


class AgentExecutor:
    """
    LangGraph Agent 执行器（Skills 版）

    用法:
        executor = AgentExecutor(
            mcp_orchestrator=orchestrator,
            tool_schemas=schemas,
            skill_manager=skill_manager,  # v2.0 新增
        )
        result = await executor.execute(user_id="1", query="帮我制定胸肌训练计划")
    """

    def __init__(
        self,
        mcp_orchestrator,
        tool_schemas: list,
        llm_client=None,
        skill_manager=None,
    ):
        self.llm_client = llm_client or ToolCallableLLM()
        self.mcp_orchestrator = mcp_orchestrator
        self.skill_manager = skill_manager

        # 构建 tool_schemas：load_skill 优先 + 原有工具
        if skill_manager and skill_manager.get_skill_count() > 0:
            skill_ids = skill_manager.list_skills()
            load_skill_schema = _build_load_skill_schema(skill_ids)
            self.tool_schemas = [load_skill_schema] + list(tool_schemas)
            self.system_prompt = _build_skills_system_prompt(
                skill_manager.get_system_prompt_skills()
            )
            logger.info(
                f"AgentExecutor initialized with Skills: "
                f"{len(skill_ids)} skills, "
                f"{len(self.tool_schemas)} tool schemas"
            )
        else:
            self.tool_schemas = tool_schemas
            self.system_prompt = FALLBACK_SYSTEM_PROMPT
            logger.info("AgentExecutor initialized without Skills (fallback mode)")

        self.graph = build_agent_graph(
            self.llm_client,
            mcp_orchestrator,
            self.tool_schemas,
            skill_manager=skill_manager,
        )

    def _build_initial_state(
        self,
        user_id: str,
        query: str,
        user_profile: Optional[Dict[str, Any]],
        conversation_history: Optional[list],
        membership_level: str,
        max_iterations: int,
        cost_limit: float,
    ) -> AgentState:
        """构建初始状态"""
        request_id = str(uuid.uuid4())[:8]

        messages = [SystemMessage(content=self.system_prompt)]
        for hist in (conversation_history or []):
            role = hist.get("role", "")
            content = hist.get("content", "")
            if not content:
                continue
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=query))

        return {
            "request_id": request_id,
            "user_id": user_id,
            "query": query,
            "user_profile": user_profile,
            "conversation_history": conversation_history or [],
            "membership_level": membership_level,
            "messages": messages,
            "tool_calls_count": 0,
            "total_cost": 0.0,
            "tool_results": [],
            "max_iterations": max_iterations,
            "cost_limit": cost_limit,
            "final_response": None,
            "errors": [],
            "step_timings": {},
            "skills_loaded": [],
        }

    async def execute(
        self,
        user_id: str,
        query: str,
        *,
        user_profile: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None,
        membership_level: str = "free",
        max_iterations: int = 5,
        cost_limit: float = 2.0,
    ) -> Dict[str, Any]:
        """同步执行（等待完整结果）"""
        start = time.time()

        initial_state = self._build_initial_state(
            user_id, query, user_profile, conversation_history,
            membership_level, max_iterations, cost_limit,
        )
        request_id = initial_state["request_id"]

        final_state = await self.graph.ainvoke(initial_state)

        # 提取最终回答
        messages = final_state.get("messages", [])
        final_response = None
        if messages:
            last = messages[-1]
            if hasattr(last, "content") and not getattr(last, "tool_calls", None):
                final_response = last.content

        elapsed = time.time() - start
        skills_loaded = final_state.get("skills_loaded", [])
        logger.info(
            f"Agent execute completed: request={request_id}, "
            f"skills={skills_loaded}, "
            f"tools={final_state.get('tool_calls_count', 0)}, "
            f"cost={final_state.get('total_cost', 0):.2f}, "
            f"time={elapsed:.2f}s"
        )

        return {
            "request_id": request_id,
            "final_response": final_response,
            "tool_results": final_state.get("tool_results", []),
            "tool_calls_count": final_state.get("tool_calls_count", 0),
            "total_cost": final_state.get("total_cost", 0.0),
            "errors": final_state.get("errors", []),
            "step_timings": final_state.get("step_timings", {}),
            "skills_loaded": skills_loaded,
            "total_time_s": round(elapsed, 3),
        }

    async def stream_execute(
        self,
        user_id: str,
        query: str,
        *,
        user_profile: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None,
        membership_level: str = "free",
        max_iterations: int = 5,
        cost_limit: float = 2.0,
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式执行（逐步返回每个节点的输出）"""
        initial_state = self._build_initial_state(
            user_id, query, user_profile, conversation_history,
            membership_level, max_iterations, cost_limit,
        )

        async for event in self.graph.astream(initial_state):
            for node_name, node_output in event.items():
                yield {"node": node_name, "data": node_output}


# =============================================================================
# 工厂函数：从 singletons 构建 AgentExecutor
# =============================================================================

def _build_tool_schemas_from_registry(registry) -> List[dict]:
    """
    从 MCPToolRegistry 构建 OpenAI function-calling 格式的 tool schemas。

    每个 BaseMCPTool 提供 get_input_schema() → Pydantic BaseModel，
    通过 model_json_schema() 转为 JSON Schema。
    """
    schemas = []
    if registry is None:
        return schemas

    for tool_name in registry.list_tool_names():
        tool = registry.get_tool(tool_name)
        if tool is None:
            continue
        try:
            input_model = tool.get_input_schema()
            json_schema = input_model.model_json_schema()

            # 移除 Pydantic 自动生成的冗余字段
            json_schema.pop("title", None)
            json_schema.pop("$defs", None)
            json_schema.pop("definitions", None)

            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.get_name(),
                    "description": tool.get_description()[:200],
                    "parameters": json_schema,
                },
            })
        except Exception as e:
            logger.warning(f"跳过工具 {tool_name} 的 schema 构建: {e}")

    return schemas


def create_agent_executor_from_singletons() -> "AgentExecutor":
    """
    从 singletons 和 SkillsIntegration 构建完整的 AgentExecutor。

    调用链：
    1. get_mcp_orchestrator() → MCPOrchestrator
    2. get_mcp_tool_registry() → MCPToolRegistry → tool_schemas
    3. SkillsIntegration → SkillManager
    4. AgentExecutor(mcp_orchestrator, tool_schemas, skill_manager)
    """
    from ..workflow.singletons import get_mcp_orchestrator, get_mcp_tool_registry

    # 1. MCP 编排器
    mcp_orchestrator = get_mcp_orchestrator()

    # 2. 工具 schemas
    tool_registry = get_mcp_tool_registry()
    tool_schemas = _build_tool_schemas_from_registry(tool_registry)
    logger.info(f"Agent tool schemas: {len(tool_schemas)} tools from registry")

    # 3. SkillManager（从 SkillsIntegration 获取）
    skill_manager = None
    try:
        from ...framework.skills import get_skills_integration
        integration = get_skills_integration()
        skill_manager = integration.get_skill_manager()
        if skill_manager:
            logger.info(
                f"Agent SkillManager: {skill_manager.get_skill_count()} skills loaded"
            )
    except Exception as e:
        logger.warning(f"SkillManager 加载失败，Agent 将以无 Skills 模式运行: {e}")

    # 4. 构建 AgentExecutor
    return AgentExecutor(
        mcp_orchestrator=mcp_orchestrator,
        tool_schemas=tool_schemas,
        skill_manager=skill_manager,
    )
