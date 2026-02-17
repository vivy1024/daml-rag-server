# -*- coding: utf-8 -*-
"""
Agent 执行器

封装 LangGraph 图的调用入口，提供 execute() 和 stream_execute() 方法。

版本: v1.0.0
日期: 2026-02-17
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage

from .state import AgentState
from .graph import build_agent_graph

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是玉珍健身的AI教练助手。根据用户的问题，决定是否需要调用工具获取数据，"
    "还是直接回答。每次只调用必要的工具，避免冗余调用。"
    "回答时使用中文，专业但友好。"
)


class AgentExecutor:
    """
    LangGraph Agent 执行器

    用法:
        executor = AgentExecutor(llm_client, mcp_orchestrator, tool_schemas)
        result = await executor.execute(user_id="1", query="帮我制定胸肌训练计划")
    """

    def __init__(
        self,
        llm_client,
        mcp_orchestrator,
        tool_schemas: list,
    ):
        self.llm_client = llm_client
        self.mcp_orchestrator = mcp_orchestrator
        self.tool_schemas = tool_schemas
        self.graph = build_agent_graph(llm_client, mcp_orchestrator, tool_schemas)

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
        """
        同步执行（等待完整结果）

        Args:
            user_id: 用户ID
            query: 用户查询
            user_profile: 预加载的用户档案
            conversation_history: 对话历史
            membership_level: 会员等级
            max_iterations: 最大迭代次数
            cost_limit: 成本上限（元）

        Returns:
            包含 final_response, tool_results, step_timings 等的结果字典
        """
        start = time.time()
        request_id = str(uuid.uuid4())[:8]

        initial_state: AgentState = {
            "request_id": request_id,
            "user_id": user_id,
            "query": query,
            "user_profile": user_profile,
            "conversation_history": conversation_history or [],
            "membership_level": membership_level,
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=query),
            ],
            "tool_calls_count": 0,
            "total_cost": 0.0,
            "tool_results": [],
            "max_iterations": max_iterations,
            "cost_limit": cost_limit,
            "final_response": None,
            "errors": [],
            "step_timings": {},
        }

        final_state = await self.graph.ainvoke(initial_state)

        # 提取最终回答
        messages = final_state.get("messages", [])
        final_response = None
        if messages:
            last = messages[-1]
            if hasattr(last, "content") and not getattr(last, "tool_calls", None):
                final_response = last.content

        elapsed = time.time() - start
        logger.info(
            f"Agent execute completed: request={request_id}, "
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
        """
        流式执行（逐步返回每个节点的输出）

        Yields:
            每个节点执行后的状态增量，格式:
            {"node": "agent"|"tools"|"safety_check", "data": {...}}
        """
        request_id = str(uuid.uuid4())[:8]

        initial_state: AgentState = {
            "request_id": request_id,
            "user_id": user_id,
            "query": query,
            "user_profile": user_profile,
            "conversation_history": conversation_history or [],
            "membership_level": membership_level,
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=query),
            ],
            "tool_calls_count": 0,
            "total_cost": 0.0,
            "tool_results": [],
            "max_iterations": max_iterations,
            "cost_limit": cost_limit,
            "final_response": None,
            "errors": [],
            "step_timings": {},
        }

        async for event in self.graph.astream(initial_state):
            for node_name, node_output in event.items():
                yield {"node": node_name, "data": node_output}
