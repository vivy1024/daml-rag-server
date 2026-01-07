"""
配置管理模块

提供统一的配置管理，包括：
- 提示词配置加载（支持热加载）
- 字段映射配置
- 运行时配置

版本: v1.1.0
日期: 2025-12-28

模块结构:
- prompts.py: 提示词配置管理（PromptConfigManager）
- field_mapping.py: 字段映射配置（FieldMappingManager）
- runtime.py: 运行时配置（RuntimeConfig）

Requirements: 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 7.4
"""

# 字段映射配置
from .field_mapping import (
    FieldMappingManager,
    get_field_mapping_manager,
    # 向后兼容函数
    map_exercise_fields,
    map_muscle_fields,
    batch_map_exercise_fields,
    batch_map_muscle_fields,
    # 向后兼容常量
    EXERCISE_FIELD_MAPPING,
    MUSCLE_FIELD_MAPPING,
)

# 提示词配置
from .prompts import (
    PromptConfigManager,
    PromptTemplate,
    get_prompt_config_manager,
    get_prompt,
    get_prompt_config,
)

# 运行时配置
from .runtime import (
    RuntimeConfig,
    RuntimeConfigManager,
    CacheConfig,
    ConnectionPoolConfig,
    LLMConfig,
    ConcurrencyConfig,
    WorkflowConfig,
    MonitoringConfig,
    PromptOptimizationConfig,
    ConfigValidationError,
    UserLevel,
    get_runtime_config,
    get_runtime_config_manager,
    reload_runtime_config,
)

__all__ = [
    # 字段映射
    "FieldMappingManager",
    "get_field_mapping_manager",
    "map_exercise_fields",
    "map_muscle_fields",
    "batch_map_exercise_fields",
    "batch_map_muscle_fields",
    "EXERCISE_FIELD_MAPPING",
    "MUSCLE_FIELD_MAPPING",
    
    # 提示词配置
    "PromptConfigManager",
    "PromptTemplate",
    "get_prompt_config_manager",
    "get_prompt",
    "get_prompt_config",
    
    # 运行时配置
    "RuntimeConfig",
    "RuntimeConfigManager",
    "CacheConfig",
    "ConnectionPoolConfig",
    "LLMConfig",
    "ConcurrencyConfig",
    "WorkflowConfig",
    "MonitoringConfig",
    "PromptOptimizationConfig",
    "ConfigValidationError",
    "UserLevel",
    "get_runtime_config",
    "get_runtime_config_manager",
    "reload_runtime_config",
]
