# -*- coding: utf-8 -*-
"""
DAG参数映射器（简化版）

v8.62.0 简化：移除中英文转换逻辑
- 前端已传递英文value（如'barbell', 'hypertrophy'）
- Neo4j节点也是英文name
- 无需复杂的中英文映射层

保留功能：
1. 字段名映射（MCP ↔ Neo4j）
2. 参数类型转换
3. 参数验证
4. 动作ID提取

作者: BUILD_BODY Team
版本: v2.0.0
日期: 2026-01-06
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ParameterMapper:
    """
    参数映射器（简化版）
    
    处理DAG任务参数到MCP工具的映射。
    v8.62.0: 移除中英文转换，前端和Neo4j已统一使用英文。
    """

    def __init__(self, field_mapping_manager=None):
        """
        初始化参数映射器
        
        Args:
            field_mapping_manager: 字段映射管理器（可选）
        """
        self.field_mapping_manager = field_mapping_manager

    def map_params_to_mcp(
        self,
        params: Dict[str, Any],
        tool_name: str
    ) -> Dict[str, Any]:
        """
        将DAG参数映射到MCP工具参数
        
        v8.62.0: 移除中英文转换，直接传递参数
        
        Args:
            params: 原始参数
            tool_name: 工具名称
            
        Returns:
            Dict[str, Any]: 映射后的参数
        """
        mapped_params = params.copy()
        
        # 使用字段映射管理器进行字段名映射（如果有）
        if self.field_mapping_manager:
            mapped_params = self.field_mapping_manager.map_to_mcp(mapped_params, tool_name)
        
        return mapped_params

    def map_result_from_mcp(
        self,
        result: Dict[str, Any],
        tool_name: str
    ) -> Dict[str, Any]:
        """
        将MCP工具结果映射回DAG格式
        
        Args:
            result: MCP工具结果
            tool_name: 工具名称
            
        Returns:
            Dict[str, Any]: 映射后的结果
        """
        mapped_result = result.copy()
        
        # 使用字段映射管理器进行字段名映射
        if self.field_mapping_manager:
            mapped_result = self.field_mapping_manager.map_from_mcp(mapped_result, tool_name)
        
        return mapped_result

    def extract_exercise_ids(
        self,
        result: Dict[str, Any],
        source_fields: List[str] = None
    ) -> List[str]:
        """
        从结果中提取动作ID列表
        
        Args:
            result: 工具结果
            source_fields: 要搜索的字段列表
            
        Returns:
            List[str]: 动作ID列表
        """
        if source_fields is None:
            source_fields = ["recommendations", "selected_exercises", "exercises", "results"]
        
        exercise_ids = []
        
        for field in source_fields:
            if field in result:
                items = result[field]
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            exercise_id = item.get("exercise_id") or item.get("id")
                            if exercise_id:
                                exercise_ids.append(exercise_id)
        
        return exercise_ids

    def extract_first_exercise_id(
        self,
        result: Dict[str, Any],
        source_fields: List[str] = None
    ) -> Optional[str]:
        """
        从结果中提取第一个动作ID
        
        Args:
            result: 工具结果
            source_fields: 要搜索的字段列表
            
        Returns:
            Optional[str]: 第一个动作ID
        """
        exercise_ids = self.extract_exercise_ids(result, source_fields)
        return exercise_ids[0] if exercise_ids else None

    def map_training_split(self, training_days: int) -> str:
        """
        根据训练天数映射训练分化

        Args:
            training_days: 每星期训练天数
            
        Returns:
            str: 训练分化类型
        """
        split_mapping = {
            1: "full_body",
            2: "upper_lower",
            3: "push_pull_legs",
            4: "upper_lower",
            5: "push_pull_legs",
            6: "push_pull_legs",
            7: "bro_split"
        }
        return split_mapping.get(training_days, "push_pull_legs")

    def map_recovery_capacity(self, recovery_value: Any) -> str:
        """
        映射恢复能力值
        
        Args:
            recovery_value: 恢复能力值（数值或字符串）
            
        Returns:
            str: 恢复能力等级
        """
        if isinstance(recovery_value, (int, float)):
            if recovery_value < 0.4:
                return "low"
            elif recovery_value < 0.7:
                return "moderate"
            else:
                return "high"
        elif isinstance(recovery_value, str):
            if recovery_value in ["low", "moderate", "high"]:
                return recovery_value
        return "moderate"

    def validate_enum_value(
        self,
        value: str,
        valid_values: List[str],
        default: str = None
    ) -> str:
        """
        验证枚举值
        
        Args:
            value: 要验证的值
            valid_values: 有效值列表
            default: 默认值
            
        Returns:
            str: 验证后的值
        """
        if value in valid_values:
            return value
        
        # 返回默认值
        if default:
            return default
        
        # 返回第一个有效值
        return valid_values[0] if valid_values else value
