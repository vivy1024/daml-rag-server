"""
训练知识导入器基类

功能：
1. 提供训练知识导入的基础架构
2. 定义通用的导入方法和错误处理
3. 支持幂等性检查

作者：薛小川
日期：2025-12-19
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from neo4j import AsyncDriver

from .models import SupplementResult

logger = logging.getLogger(__name__)


class TrainingKnowledgeSupplementer(ABC):
    """训练知识导入器基类"""
    
    def __init__(self, neo4j_driver: AsyncDriver):
        """
        初始化导入器
        
        Args:
            neo4j_driver: Neo4j异步驱动
        """
        self.driver = neo4j_driver
    
    @abstractmethod
    async def supplement(self, data_file_path: str) -> SupplementResult:
        """
        执行数据导入
        
        Args:
            data_file_path: 数据文件路径
        
        Returns:
            SupplementResult: 导入结果
        """
        pass
    
    def _load_json_data(self, file_path: str) -> Any:
        """
        加载JSON数据文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            Any: 解析后的数据
        
        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON格式错误
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"成功加载数据文件: {file_path}")
            return data
        except FileNotFoundError:
            logger.error(f"数据文件不存在: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON格式错误: {file_path}, 错误: {e}")
            raise
    
    def _check_node_exists(self, session, label: str, properties: Dict[str, Any]) -> bool:
        """
        检查节点是否已存在（幂等性检查）
        
        Args:
            session: Neo4j会话
            label: 节点标签
            properties: 节点属性（用于匹配）
        
        Returns:
            bool: 节点是否存在
        """
        # 构建WHERE子句
        where_clauses = [f"n.{key} = ${key}" for key in properties.keys()]
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
        MATCH (n:{label})
        WHERE {where_clause}
        RETURN count(n) as count
        """
        
        result = session.run(query, properties)
        record = result.single()
        return record["count"] > 0
    
    def _check_relationship_exists(
        self,
        session,
        start_label: str,
        start_properties: Dict[str, Any],
        rel_type: str,
        end_label: str,
        end_properties: Dict[str, Any]
    ) -> bool:
        """
        检查关系是否已存在（幂等性检查）
        
        Args:
            session: Neo4j会话
            start_label: 起始节点标签
            start_properties: 起始节点属性
            rel_type: 关系类型
            end_label: 结束节点标签
            end_properties: 结束节点属性
        
        Returns:
            bool: 关系是否存在
        """
        # 构建WHERE子句
        start_where = [f"start.{key} = $start_{key}" for key in start_properties.keys()]
        end_where = [f"end.{key} = $end_{key}" for key in end_properties.keys()]
        where_clause = " AND ".join(start_where + end_where)
        
        # 构建参数字典
        params = {}
        for key, value in start_properties.items():
            params[f"start_{key}"] = value
        for key, value in end_properties.items():
            params[f"end_{key}"] = value
        
        query = f"""
        MATCH (start:{start_label})-[r:{rel_type}]->(end:{end_label})
        WHERE {where_clause}
        RETURN count(r) as count
        """
        
        result = session.run(query, params)
        record = result.single()
        return record["count"] > 0
    
    def _create_supplement_result(
        self,
        total_nodes: int,
        updated_nodes: int,
        created_nodes: int,
        errors: List[Dict[str, Any]],
        execution_time: float
    ) -> SupplementResult:
        """
        创建导入结果对象
        
        Args:
            total_nodes: 总节点数
            updated_nodes: 更新的节点数
            created_nodes: 创建的节点数
            errors: 错误列表
            execution_time: 执行时间
        
        Returns:
            SupplementResult: 导入结果
        """
        return SupplementResult(
            total_nodes=total_nodes,
            updated_nodes=updated_nodes,
            created_nodes=created_nodes,
            errors=errors,
            execution_time=execution_time
        )
    
    def _log_progress(self, current: int, total: int, operation: str):
        """
        记录进度日志
        
        Args:
            current: 当前进度
            total: 总数
            operation: 操作描述
        """
        if total > 0:
            percentage = (current / total) * 100
            logger.info(f"{operation}: {current}/{total} ({percentage:.1f}%)")
