# -*- coding: utf-8 -*-
"""
Skills架构模块

渐进式披露（Progressive Disclosure）架构实现。

核心组件：
- SkillMetadata: Level 1 轻量元数据（始终在system prompt）
- SkillContent: Level 2 完整指令（按需加载）
- SkillExecution: Level 3 执行资源（执行时加载）
- SkillManager: 技能管理器
- LoadSkillTool: load_skill MCP工具
- SkillsAgentExecutor: 基于Skills的Agent执行器

集成模块：
- skills_integration: Feature Flag控制和单例管理

Requirements: 8.1-8.7

版本: v1.1.0
日期: 2026-01-11
作者: 薛小川
"""

from .skill_definition import (
    SkillCategory,
    SkillMetadata,
    SkillContent,
    SkillExecution,
    Skill,
)

from .skill_manager import SkillManager, create_skill_manager, create_skill_manager_from_templates

from .load_skill_tool import LoadSkillTool, LoadSkillInput

from .skills_agent_executor import (
    AgentAction,
    AgentDecision,
    AgentExecutionResult,
    SkillsAgentExecutor,
)

from .skills_integration import (
    # Feature Flags
    is_skills_mode_enabled,
    is_agent_mode_enabled,
    get_skills_config,
    # 集成器
    SkillsIntegration,
    get_skills_integration,
    initialize_skills_from_adapter,
)

__all__ = [
    # 数据结构
    "SkillCategory",
    "SkillMetadata",
    "SkillContent",
    "SkillExecution",
    "Skill",
    # 管理器
    "SkillManager",
    "create_skill_manager",
    "create_skill_manager_from_templates",
    # MCP工具
    "LoadSkillTool",
    "LoadSkillInput",
    # Agent执行器
    "AgentAction",
    "AgentDecision",
    "AgentExecutionResult",
    "SkillsAgentExecutor",
    # Feature Flags
    "is_skills_mode_enabled",
    "is_agent_mode_enabled",
    "get_skills_config",
    # 集成器
    "SkillsIntegration",
    "get_skills_integration",
    "initialize_skills_from_adapter",
]
