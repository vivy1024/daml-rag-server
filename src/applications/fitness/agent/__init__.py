# -*- coding: utf-8 -*-
"""
LangGraph Agent 执行引擎

基于 LangGraph StateGraph 的 Agent 模式执行器，
通过 LLM 自主决策调用 MCP 工具，替代固定 DAG 模板。

版本: v1.0.0
日期: 2026-02-17
"""

from .state import AgentState
from .executor import AgentExecutor, create_agent_executor_from_singletons
from .llm_adapter import ToolCallableLLM

__all__ = [
    "AgentExecutor",
    "AgentState",
    "ToolCallableLLM",
    "create_agent_executor_from_singletons",
]
