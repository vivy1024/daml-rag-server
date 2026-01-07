"""
字段映射配置管理模块

整合 neo4j_field_mapping.py，提供增强的字段映射功能：
- 支持从 YAML 配置文件加载映射规则
- 支持双向映射（MCP ↔ Neo4j）
- 支持动态添加映射规则
- 保持向后兼容（原有函数仍可用）

版本: v1.0.0
日期: 2025-12-28
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from threading import Lock

logger = logging.getLogger(__name__)


# ============================================================================
# 默认映射规则（从 neo4j_field_mapping.py 迁移）
# ============================================================================

# Exercise节点字段映射
DEFAULT_EXERCISE_FIELD_MAPPING = {
    # MCP工具字段 -> Neo4j实际字段
    "exercise_id": "id",
    "difficulty_level": "difficulty",
    "movement_pattern_zh": None,  # 不存在，设为None
    "force_type_zh": "force",
    "mechanics_zh": "mechanic",
    "safety_warning_signs_zh": "safety_warning_signs",
    "contraindications_zh": None,  # 不存在
    "common_mistakes_zh": None,   # 不存在
    "progression_options_zh": None,  # 不存在
}

# Muscle节点字段映射
DEFAULT_MUSCLE_FIELD_MAPPING = {
    "muscle_id": "id",
    "muscle_name_zh": "name_zh",
    "muscle_name_en": "name_en",
}


class FieldMappingManager:
    """
    字段映射管理器
    
    提供统一的字段映射管理，支持：
    - 从 YAML 配置文件加载映射规则
    - 双向映射（MCP → Neo4j，Neo4j → MCP）
    - 动态添加/更新映射规则
    - 批量映射操作
    """
    
    _instance: Optional["FieldMappingManager"] = None
    _lock = Lock()
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化字段映射管理器
        
        Args:
            config_path: YAML配置文件路径（可选）
        """
        self.config_path = config_path
        self.mappings: Dict[str, Dict[str, Dict[str, Optional[str]]]] = {}
        self._load_default_mappings()
        
        if config_path:
            self._load_config_from_yaml(config_path)
    
    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "FieldMappingManager":
        """
        获取单例实例
        
        Args:
            config_path: YAML配置文件路径（仅首次调用时有效）
            
        Returns:
            FieldMappingManager 单例实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config_path)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        with cls._lock:
            cls._instance = None
    
    def _load_default_mappings(self):
        """加载默认映射规则"""
        # Exercise 映射
        self.mappings["exercise"] = {
            "mcp_to_neo4j": DEFAULT_EXERCISE_FIELD_MAPPING.copy(),
            "neo4j_to_mcp": self._reverse_mapping(DEFAULT_EXERCISE_FIELD_MAPPING),
        }
        
        # Muscle 映射
        self.mappings["muscle"] = {
            "mcp_to_neo4j": DEFAULT_MUSCLE_FIELD_MAPPING.copy(),
            "neo4j_to_mcp": self._reverse_mapping(DEFAULT_MUSCLE_FIELD_MAPPING),
        }
    
    def _reverse_mapping(self, mapping: Dict[str, Optional[str]]) -> Dict[str, str]:
        """
        反转映射规则
        
        Args:
            mapping: 原始映射（MCP -> Neo4j）
            
        Returns:
            反转后的映射（Neo4j -> MCP）
        """
        reversed_map = {}
        for mcp_field, neo4j_field in mapping.items():
            if neo4j_field is not None:
                reversed_map[neo4j_field] = mcp_field
        return reversed_map
    
    def _load_config_from_yaml(self, config_path: str):
        """
        从 YAML 配置文件加载映射规则
        
        Args:
            config_path: YAML配置文件路径
        """
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"配置文件不存在: {config_path}，使用默认映射")
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                return
            
            # 加载字段映射配置
            field_mappings = config.get("field_mappings", {})
            for entity_type, mapping_config in field_mappings.items():
                if entity_type not in self.mappings:
                    self.mappings[entity_type] = {
                        "mcp_to_neo4j": {},
                        "neo4j_to_mcp": {},
                    }
                
                # 加载 MCP -> Neo4j 映射
                mcp_to_neo4j = mapping_config.get("mcp_to_neo4j", {})
                self.mappings[entity_type]["mcp_to_neo4j"].update(mcp_to_neo4j)
                
                # 加载 Neo4j -> MCP 映射（如果提供）
                neo4j_to_mcp = mapping_config.get("neo4j_to_mcp", {})
                if neo4j_to_mcp:
                    self.mappings[entity_type]["neo4j_to_mcp"].update(neo4j_to_mcp)
                else:
                    # 自动生成反向映射
                    self.mappings[entity_type]["neo4j_to_mcp"].update(
                        self._reverse_mapping(mcp_to_neo4j)
                    )
            
            logger.info(f"✅ 从 {config_path} 加载字段映射配置成功")
            
        except Exception as e:
            logger.error(f"加载字段映射配置失败: {e}")
    
    def reload_config(self):
        """重新加载配置文件"""
        if self.config_path:
            self._load_default_mappings()  # 先重置为默认
            self._load_config_from_yaml(self.config_path)
    
    def add_mapping(
        self,
        entity_type: str,
        mcp_field: str,
        neo4j_field: Optional[str]
    ):
        """
        动态添加映射规则
        
        Args:
            entity_type: 实体类型（如 "exercise", "muscle"）
            mcp_field: MCP工具字段名
            neo4j_field: Neo4j字段名（None表示字段不存在）
        """
        if entity_type not in self.mappings:
            self.mappings[entity_type] = {
                "mcp_to_neo4j": {},
                "neo4j_to_mcp": {},
            }
        
        self.mappings[entity_type]["mcp_to_neo4j"][mcp_field] = neo4j_field
        if neo4j_field is not None:
            self.mappings[entity_type]["neo4j_to_mcp"][neo4j_field] = mcp_field
    
    def map_to_neo4j(
        self,
        entity_type: str,
        mcp_data: Dict[str, Any],
        preserve_unmapped: bool = True
    ) -> Dict[str, Any]:
        """
        MCP参数 -> Neo4j字段
        
        Args:
            entity_type: 实体类型
            mcp_data: MCP工具数据
            preserve_unmapped: 是否保留未映射的字段
            
        Returns:
            映射后的数据
        """
        mapping = self.mappings.get(entity_type, {}).get("mcp_to_neo4j", {})
        return self._apply_mapping(mcp_data, mapping, preserve_unmapped)
    
    def map_from_neo4j(
        self,
        entity_type: str,
        neo4j_data: Dict[str, Any],
        preserve_unmapped: bool = True,
        fill_missing: bool = True
    ) -> Dict[str, Any]:
        """
        Neo4j字段 -> MCP参数
        
        Args:
            entity_type: 实体类型
            neo4j_data: Neo4j查询结果
            preserve_unmapped: 是否保留未映射的字段
            fill_missing: 是否填充缺失字段（使用默认值）
            
        Returns:
            映射后的数据
        """
        mapping = self.mappings.get(entity_type, {}).get("neo4j_to_mcp", {})
        result = self._apply_mapping(neo4j_data, mapping, preserve_unmapped)
        
        # 填充缺失字段
        if fill_missing:
            mcp_to_neo4j = self.mappings.get(entity_type, {}).get("mcp_to_neo4j", {})
            for mcp_field, neo4j_field in mcp_to_neo4j.items():
                if mcp_field not in result:
                    if neo4j_field is None:
                        # 字段不存在，使用默认值
                        if mcp_field.endswith("_zh"):
                            result[mcp_field] = []
                        else:
                            result[mcp_field] = None
        
        return result
    
    def _apply_mapping(
        self,
        data: Dict[str, Any],
        mapping: Dict[str, Optional[str]],
        preserve_unmapped: bool = True
    ) -> Dict[str, Any]:
        """
        应用映射规则
        
        Args:
            data: 原始数据
            mapping: 映射规则
            preserve_unmapped: 是否保留未映射的字段
            
        Returns:
            映射后的数据
        """
        result = {}
        mapped_keys = set()
        
        for src_field, dst_field in mapping.items():
            if src_field in data:
                if dst_field is not None:
                    result[dst_field] = data[src_field]
                mapped_keys.add(src_field)
        
        # 保留未映射的字段
        if preserve_unmapped:
            for key, value in data.items():
                if key not in mapped_keys and key not in result:
                    result[key] = value
        
        return result
    
    def batch_map_to_neo4j(
        self,
        entity_type: str,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量映射到 Neo4j
        
        Args:
            entity_type: 实体类型
            items: 数据列表
            
        Returns:
            映射后的数据列表
        """
        return [self.map_to_neo4j(entity_type, item) for item in items]
    
    def batch_map_from_neo4j(
        self,
        entity_type: str,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量映射从 Neo4j
        
        Args:
            entity_type: 实体类型
            items: 数据列表
            
        Returns:
            映射后的数据列表
        """
        return [self.map_from_neo4j(entity_type, item) for item in items]
    
    def get_mapping(self, entity_type: str) -> Dict[str, Dict[str, Optional[str]]]:
        """
        获取指定实体类型的映射规则
        
        Args:
            entity_type: 实体类型
            
        Returns:
            映射规则字典
        """
        return self.mappings.get(entity_type, {
            "mcp_to_neo4j": {},
            "neo4j_to_mcp": {},
        })
    
    def list_entity_types(self) -> List[str]:
        """
        列出所有已配置的实体类型
        
        Returns:
            实体类型列表
        """
        return list(self.mappings.keys())


# ============================================================================
# 向后兼容函数（保持原有接口可用）
# ============================================================================

# 保留原有的映射常量
EXERCISE_FIELD_MAPPING = DEFAULT_EXERCISE_FIELD_MAPPING
MUSCLE_FIELD_MAPPING = DEFAULT_MUSCLE_FIELD_MAPPING


def map_exercise_fields(neo4j_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    将Neo4j查询结果映射为MCP工具期望的格式（向后兼容）
    
    Args:
        neo4j_result: Neo4j查询返回的原始结果
        
    Returns:
        映射后的结果字典
    """
    manager = FieldMappingManager.get_instance()
    return manager.map_from_neo4j("exercise", neo4j_result)


def map_muscle_fields(neo4j_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    将Neo4j肌肉查询结果映射为MCP工具期望的格式（向后兼容）
    
    Args:
        neo4j_result: Neo4j查询返回的原始结果
        
    Returns:
        映射后的结果字典
    """
    manager = FieldMappingManager.get_instance()
    return manager.map_from_neo4j("muscle", neo4j_result)


def batch_map_exercise_fields(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量映射Exercise字段（向后兼容）
    
    Args:
        results: Neo4j查询结果列表
        
    Returns:
        映射后的结果列表
    """
    manager = FieldMappingManager.get_instance()
    return manager.batch_map_from_neo4j("exercise", results)


def batch_map_muscle_fields(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量映射Muscle字段（向后兼容）
    
    Args:
        results: Neo4j查询结果列表
        
    Returns:
        映射后的结果列表
    """
    manager = FieldMappingManager.get_instance()
    return manager.batch_map_from_neo4j("muscle", results)


# ============================================================================
# 便捷函数
# ============================================================================

def get_field_mapping_manager(config_path: Optional[str] = None) -> FieldMappingManager:
    """
    获取字段映射管理器实例
    
    Args:
        config_path: YAML配置文件路径（可选）
        
    Returns:
        FieldMappingManager 实例
    """
    return FieldMappingManager.get_instance(config_path)
