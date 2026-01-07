# -*- coding: utf-8 -*-
"""
Neo4j查询结果处理器

统一处理Neo4j查询结果，解决以下问题：
1. 'list' object has no attribute 'records' 错误
2. 属性不存在时的安全访问
3. 空结果的统一处理

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-26
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Neo4jResultHandler:
    """
    统一的Neo4j查询结果处理器
    
    解决两种常见的Neo4j查询结果格式：
    1. Result对象（有.records属性）- neo4j-driver返回
    2. 列表格式 - 某些查询方式直接返回列表
    
    使用示例：
        result = await neo4j_client.execute_query(query, params)
        records = Neo4jResultHandler.to_records(result)
        for record in records:
            name = Neo4jResultHandler.get_property(record, "name_zh", "未知")
    """
    
    @staticmethod
    def to_records(result: Any) -> List[Dict[str, Any]]:
        """
        将Neo4j查询结果转换为记录列表
        
        处理多种情况：
        1. result.records (neo4j-driver返回的Result对象)
        2. result本身是列表 (某些查询方式返回的列表)
        3. result是None或其他类型
        
        Args:
            result: Neo4j查询结果，可能是Result对象、列表或其他类型
        
        Returns:
            记录列表，每个记录是一个字典
            
        Examples:
            >>> # 处理Result对象
            >>> result = await neo4j_client.execute_query(query, params)
            >>> records = Neo4jResultHandler.to_records(result)
            
            >>> # 处理列表结果
            >>> result = [{"name": "test"}]
            >>> records = Neo4jResultHandler.to_records(result)
            >>> # records == [{"name": "test"}]
        """
        if result is None:
            logger.debug("Neo4j结果为None，返回空列表")
            return []
        
        # 情况1: Result对象（有records属性）
        if hasattr(result, 'records'):
            try:
                records = []
                for record in result.records:
                    # 将Record对象转换为字典
                    if hasattr(record, 'data'):
                        records.append(record.data())
                    elif hasattr(record, 'keys'):
                        # 使用keys()方法构建字典
                        records.append({key: record[key] for key in record.keys()})
                    elif isinstance(record, dict):
                        records.append(record)
                    else:
                        # 尝试直接转换为字典
                        records.append(dict(record))
                return records
            except Exception as e:
                logger.warning(f"处理Result.records时出错: {e}，尝试其他方式")
        
        # 情况2: 已经是列表
        if isinstance(result, list):
            records = []
            for item in result:
                if isinstance(item, dict):
                    records.append(item)
                elif hasattr(item, 'data'):
                    records.append(item.data())
                elif hasattr(item, 'keys'):
                    records.append({key: item[key] for key in item.keys()})
                else:
                    try:
                        records.append(dict(item))
                    except (TypeError, ValueError):
                        logger.warning(f"无法转换记录为字典: {type(item)}")
                        continue
            return records
        
        # 情况3: 单个记录（非列表）
        if isinstance(result, dict):
            return [result]
        
        if hasattr(result, 'data'):
            return [result.data()]
        
        # 情况4: 无法处理的类型
        logger.warning(f"无法处理的Neo4j结果类型: {type(result)}")
        return []
    
    @staticmethod
    def get_property(
        record: Dict[str, Any],
        key: str,
        default: T = None
    ) -> Union[Any, T]:
        """
        安全获取记录属性，处理属性不存在的情况
        
        Args:
            record: 记录字典
            key: 属性名
            default: 默认值，当属性不存在或为None时返回
        
        Returns:
            属性值或默认值
            
        Examples:
            >>> record = {"name_zh": "深蹲", "category": "腿部"}
            >>> Neo4jResultHandler.get_property(record, "name_zh", "未知")
            '深蹲'
            >>> Neo4jResultHandler.get_property(record, "name_en", "Unknown")
            'Unknown'
        """
        if record is None:
            return default
        
        if not isinstance(record, dict):
            # 尝试转换为字典
            try:
                if hasattr(record, 'data'):
                    record = record.data()
                elif hasattr(record, 'keys'):
                    record = {k: record[k] for k in record.keys()}
                else:
                    record = dict(record)
            except (TypeError, ValueError):
                logger.warning(f"无法将记录转换为字典: {type(record)}")
                return default
        
        value = record.get(key)
        
        # 如果值为None，返回默认值
        if value is None:
            return default
        
        return value
    
    @staticmethod
    def get_nested_property(
        record: Dict[str, Any],
        keys: List[str],
        default: T = None
    ) -> Union[Any, T]:
        """
        安全获取嵌套属性
        
        Args:
            record: 记录字典
            keys: 属性路径列表，如 ["exercise", "name_zh"]
            default: 默认值
        
        Returns:
            嵌套属性值或默认值
            
        Examples:
            >>> record = {"exercise": {"name_zh": "深蹲"}}
            >>> Neo4jResultHandler.get_nested_property(record, ["exercise", "name_zh"], "未知")
            '深蹲'
        """
        if record is None or not keys:
            return default
        
        current = record
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif hasattr(current, key):
                current = getattr(current, key)
            else:
                return default
            
            if current is None:
                return default
        
        return current
    
    @staticmethod
    def safe_list(value: Any, default: Optional[List] = None) -> List:
        """
        确保返回列表类型
        
        Args:
            value: 可能是列表、单个值或None
            default: 默认值，默认为空列表
        
        Returns:
            列表
            
        Examples:
            >>> Neo4jResultHandler.safe_list(["a", "b"])
            ['a', 'b']
            >>> Neo4jResultHandler.safe_list("single")
            ['single']
            >>> Neo4jResultHandler.safe_list(None)
            []
        """
        if default is None:
            default = []
        
        if value is None:
            return default
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, (str, int, float, bool)):
            return [value]
        
        # 尝试转换为列表
        try:
            return list(value)
        except (TypeError, ValueError):
            return [value]
    
    @staticmethod
    def is_empty_result(result: Any) -> bool:
        """
        检查结果是否为空
        
        Args:
            result: Neo4j查询结果
        
        Returns:
            True如果结果为空，否则False
        """
        if result is None:
            return True
        
        if hasattr(result, 'records'):
            try:
                return len(list(result.records)) == 0
            except Exception:
                return True
        
        if isinstance(result, list):
            return len(result) == 0
        
        return False
