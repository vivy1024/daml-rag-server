# -*- coding: utf-8 -*-
"""
参数转换器（简化版）- Parameter Converter

v8.62.0 简化：移除中英文转换逻辑
- 前端已传递英文value（如'barbell', 'hypertrophy'）
- Neo4j节点也是英文name
- 无需复杂的中英文映射层

保留功能：
1. 参数类型转换
2. 枚举值验证
3. 嵌套对象处理
4. 转换日志记录

版本: v2.0.0
日期: 2026-01-06
"""

import logging
from typing import Dict, List, Any, Optional, Type
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# 有效枚举值定义（用于验证，不再用于转换）
VALID_TRAINING_GOALS = [
    "hypertrophy", "strength", "endurance", "general_fitness",
    "weight_loss", "power", "maintenance", "recomp",
    "fat_loss", "posture_correction", "functional"
]

VALID_FITNESS_LEVELS = [
    "novice", "beginner", "intermediate", "advanced", "expert"
]

VALID_SESSION_FOCUS = [
    "compound", "isolation", "balanced"
]

VALID_ACTIVITY_LEVELS = [
    "sedentary", "lightly_active", "moderately_active", 
    "very_active", "extremely_active"
]

VALID_SPLIT_TYPES = [
    "full_body", "upper_lower", "push_pull_legs", "body_part_split"
]


class ParameterConverter:
    """
    参数转换器（简化版）
    
    v8.62.0: 移除中英文转换，前端和Neo4j已统一使用英文。
    保留参数验证和类型转换功能。
    """
    
    def __init__(self):
        """初始化参数转换器"""
        self.logger = logger
        self.conversion_stats = {
            "total_conversions": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "validation_warnings": 0
        }
        
        # 有效值映射（用于验证）
        self.valid_values = {
            "training_goal": VALID_TRAINING_GOALS,
            "primary_goal": VALID_TRAINING_GOALS,
            "fitness_level": VALID_FITNESS_LEVELS,
            "difficulty_level": VALID_FITNESS_LEVELS,
            "training_level": VALID_FITNESS_LEVELS,
            "session_focus": VALID_SESSION_FOCUS,
            "activity_level": VALID_ACTIVITY_LEVELS,
            "split_type": VALID_SPLIT_TYPES
        }
    
    def convert_params(
        self,
        params: Dict[str, Any],
        tool_schema: Optional[Type[BaseModel]] = None,
        param_types: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        转换和验证参数
        
        v8.62.0: 移除中英文转换，仅保留验证和类型处理
        """
        converted_params = {}
        
        self.logger.debug(f"🔄 开始参数处理，共 {len(params)} 个参数")
        
        for param_name, param_value in params.items():
            self.conversion_stats["total_conversions"] += 1
            
            try:
                # 处理嵌套对象
                if isinstance(param_value, dict):
                    converted_params[param_name] = self._process_nested_dict(param_value)
                # 处理列表
                elif isinstance(param_value, list):
                    converted_params[param_name] = [
                        self._process_nested_dict(item) if isinstance(item, dict) else item
                        for item in param_value
                    ]
                # 处理普通值 - 验证枚举值
                else:
                    if param_name in self.valid_values and isinstance(param_value, str):
                        if not self.validate_enum_value(param_value, param_name):
                            self.conversion_stats["validation_warnings"] += 1
                    
                    converted_params[param_name] = param_value
                
                self.conversion_stats["successful_conversions"] += 1
                    
            except Exception as e:
                self.conversion_stats["failed_conversions"] += 1
                self.logger.error(f"❌ 参数处理失败: {param_name} - {str(e)}")
                converted_params[param_name] = param_value
        
        return converted_params
    
    def _process_nested_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归处理嵌套字典
        """
        processed = {}
        
        for key, value in data.items():
            # 验证枚举值
            if key in self.valid_values and isinstance(value, str):
                if not self.validate_enum_value(value, key):
                    self.conversion_stats["validation_warnings"] += 1
                processed[key] = value
            # 递归处理嵌套字典
            elif isinstance(value, dict):
                processed[key] = self._process_nested_dict(value)
            # 处理列表
            elif isinstance(value, list):
                processed[key] = [
                    self._process_nested_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                processed[key] = value
        
        return processed
    
    def validate_enum_value(
        self, 
        value: str, 
        param_name: str, 
        allowed_values: Optional[List[str]] = None
    ) -> bool:
        """
        验证枚举值是否有效
        """
        if allowed_values is None:
            allowed_values = self.valid_values.get(param_name)
        
        if allowed_values is None:
            return True  # 无验证规则，默认通过
        
        is_valid = value in allowed_values
        if not is_valid:
            self.logger.warning(
                f"⚠️ 枚举值可能无效: {param_name} = {value}\n"
                f"   允许的值: {allowed_values}"
            )
        
        return is_valid
    
    def get_conversion_stats(self) -> Dict[str, int]:
        """获取处理统计信息"""
        return self.conversion_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.conversion_stats = {
            "total_conversions": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "validation_warnings": 0
        }
