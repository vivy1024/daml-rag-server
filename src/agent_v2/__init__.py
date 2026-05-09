# -*- coding: utf-8 -*-
"""
Agent v2 — Skills-first Agent Runtime

基于 LangGraph StateGraph 的 6 步编排：
init_thread → skill_select → safety_check → skill_execute → output_generate → record
"""

from .state import AgentState


def build_agent_graph(**kwargs):
    """延迟导入 graph 模块，避免在无 langgraph 环境下 import 失败"""
    from .graph import build_agent_graph as _build
    return _build(**kwargs)


__all__ = ["AgentState", "build_agent_graph"]
