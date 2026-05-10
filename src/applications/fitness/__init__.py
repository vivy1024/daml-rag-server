# -*- coding: utf-8 -*-
"""
健身应用层 - 基于DAML-RAG框架的健身领域应用

v3.1.0 (Phase 5): Agent/Workflow/DAG 已迁移到 YuzhenFork TypeScript 侧。
本模块仅保留：
- mcp_tools/: MCP 工具实现（供 MCP Server 调用）
- services/: 领域服务
- config/: 配置管理
- clients/: 领域客户端
- types/: 类型定义

版本: v3.1.0
日期: 2026-05-11
"""

# 配置管理模块（仍需要）
try:
    from .config import (
        FieldMappingManager,
        get_field_mapping_manager,
        map_exercise_fields,
        map_muscle_fields,
        batch_map_exercise_fields,
        batch_map_muscle_fields,
        EXERCISE_FIELD_MAPPING,
        MUSCLE_FIELD_MAPPING,
        PromptConfigManager,
        PromptTemplate,
        get_prompt_config_manager,
        get_prompt,
        get_prompt_config,
        RuntimeConfig,
        RuntimeConfigManager,
        get_runtime_config,
        get_runtime_config_manager,
        reload_runtime_config,
    )
except ImportError:
    pass

__all__ = [
    "FieldMappingManager",
    "get_field_mapping_manager",
    "map_exercise_fields",
    "map_muscle_fields",
    "batch_map_exercise_fields",
    "batch_map_muscle_fields",
    "EXERCISE_FIELD_MAPPING",
    "MUSCLE_FIELD_MAPPING",
    "PromptConfigManager",
    "PromptTemplate",
    "get_prompt_config_manager",
    "get_prompt",
    "get_prompt_config",
    "RuntimeConfig",
    "RuntimeConfigManager",
    "get_runtime_config",
    "get_runtime_config_manager",
    "reload_runtime_config",
]
