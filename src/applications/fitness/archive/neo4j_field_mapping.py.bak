"""
Neo4j字段映射配置

将MCP工具使用的字段名映射到Neo4j实际字段名

⚠️ 此文件已迁移到 config/field_mapping.py
为保持向后兼容，此文件重新导出所有接口。
新代码请直接使用 config.field_mapping 模块。

版本: v2.0.0 (迁移版本)
日期: 2025-12-28
"""

# 从新模块导入所有接口（向后兼容）
from .config.field_mapping import (
    # 映射常量
    EXERCISE_FIELD_MAPPING,
    MUSCLE_FIELD_MAPPING,
    # 映射函数
    map_exercise_fields,
    map_muscle_fields,
    batch_map_exercise_fields,
    batch_map_muscle_fields,
    # 新增的管理器类
    FieldMappingManager,
    get_field_mapping_manager,
)

__all__ = [
    "EXERCISE_FIELD_MAPPING",
    "MUSCLE_FIELD_MAPPING",
    "map_exercise_fields",
    "map_muscle_fields",
    "batch_map_exercise_fields",
    "batch_map_muscle_fields",
    "FieldMappingManager",
    "get_field_mapping_manager",
]
