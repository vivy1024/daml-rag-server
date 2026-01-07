# -*- coding: utf-8 -*-
"""
条件分支执行器 - DAG编排层组件

支持基于工具执行结果的条件分支逻辑，实现动态工作流调整。

核心功能：
1. 条件表达式评估
2. 分支选择逻辑
3. 多条件支持
4. 默认分支处理

版本: v1.0.0
日期: 2026-01-05
作者: BUILD_BODY Team
"""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConditionOperator(Enum):
    """条件运算符"""
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    IN = "in"
    NOT_IN = "not in"
    CONTAINS = "contains"


@dataclass
class ConditionalBranch:
    """条件分支定义"""
    condition: str                  # 条件表达式，如 "result.risk_level == 'high'"
    branch_to: str                  # 目标工具名称
    priority: int = 0               # 优先级（数字越小优先级越高）
    description: str = ""           # 分支描述
    
    def __post_init__(self):
        """验证分支定义"""
        if not self.condition or not self.branch_to:
            raise ValueError("条件和目标工具名称不能为空")


class ConditionalBranchExecutor:
    """
    条件分支执行器
    
    支持的条件格式：
    - result.field == value
    - result.field > value
    - result.field < value
    - result.field in [value1, value2]
    - result.field contains value
    
    示例：
    - "result.risk_level == 'high'"
    - "result.score > 0.8"
    - "result.count < 5"
    - "result.status in ['pending', 'processing']"
    """
    
    def __init__(self):
        """初始化条件分支执行器"""
        self.evaluation_history = []
        logger.info("✅ 条件分支执行器初始化完成")
    
    def evaluate_condition(
        self,
        condition: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        评估条件表达式
        
        Args:
            condition: 条件表达式字符串
            result: 工具执行结果
        
        Returns:
            bool: 条件是否满足
        
        Raises:
            ValueError: 条件表达式格式错误
        """
        try:
            # 解析条件表达式
            parsed = self._parse_condition(condition)
            if not parsed:
                logger.error(f"❌ 无法解析条件表达式: {condition}")
                return False
            
            field_path, operator, expected_value = parsed
            
            # 获取实际值
            actual_value = self._get_field_value(result, field_path)
            
            # 执行比较
            result_bool = self._compare_values(actual_value, operator, expected_value)
            
            # 记录评估历史
            self.evaluation_history.append({
                "condition": condition,
                "field_path": field_path,
                "operator": operator,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "result": result_bool
            })
            
            logger.debug(
                f"条件评估: {condition} | "
                f"实际值: {actual_value} | "
                f"结果: {'✅ 满足' if result_bool else '❌ 不满足'}"
            )
            
            return result_bool
            
        except Exception as e:
            logger.error(f"❌ 条件评估失败: {condition}, 错误: {e}")
            return False
    
    def select_branch(
        self,
        branches: List[ConditionalBranch],
        result: Dict[str, Any]
    ) -> Optional[str]:
        """
        选择分支
        
        Args:
            branches: 分支列表
            result: 工具执行结果
        
        Returns:
            Optional[str]: 选中的目标工具名称，如果没有匹配则返回None
        """
        if not branches:
            logger.warning("⚠️ 分支列表为空")
            return None
        
        # 按优先级排序
        sorted_branches = sorted(branches, key=lambda b: b.priority)
        
        # 逐个评估条件
        for branch in sorted_branches:
            if self.evaluate_condition(branch.condition, result):
                logger.info(
                    f"✅ 选择分支: {branch.branch_to} | "
                    f"条件: {branch.condition} | "
                    f"描述: {branch.description or '无'}"
                )
                return branch.branch_to
        
        logger.info("ℹ️ 没有匹配的分支条件")
        return None
    
    def select_branch_with_default(
        self,
        branches: List[ConditionalBranch],
        result: Dict[str, Any],
        default_branch: str
    ) -> str:
        """
        选择分支（带默认分支）
        
        Args:
            branches: 分支列表
            result: 工具执行结果
            default_branch: 默认分支工具名称
        
        Returns:
            str: 选中的目标工具名称
        """
        selected = self.select_branch(branches, result)
        
        if selected is None:
            logger.info(f"ℹ️ 使用默认分支: {default_branch}")
            return default_branch
        
        return selected
    
    def _parse_condition(self, condition: str) -> Optional[tuple]:
        """
        解析条件表达式
        
        Args:
            condition: 条件表达式字符串
        
        Returns:
            Optional[tuple]: (field_path, operator, expected_value) 或 None
        """
        # 移除多余空格
        condition = condition.strip()
        
        # 支持的运算符（按长度降序，避免误匹配）
        operators = [
            ("not in", ConditionOperator.NOT_IN),
            ("contains", ConditionOperator.CONTAINS),
            (">=", ConditionOperator.GREATER_EQUAL),
            ("<=", ConditionOperator.LESS_EQUAL),
            ("==", ConditionOperator.EQUAL),
            ("!=", ConditionOperator.NOT_EQUAL),
            (">", ConditionOperator.GREATER_THAN),
            ("<", ConditionOperator.LESS_THAN),
            (" in ", ConditionOperator.IN),
        ]
        
        for op_str, op_enum in operators:
            if op_str in condition:
                parts = condition.split(op_str, 1)
                if len(parts) == 2:
                    field_path = parts[0].strip()
                    value_str = parts[1].strip()
                    
                    # 解析值
                    expected_value = self._parse_value(value_str)
                    
                    return (field_path, op_enum, expected_value)
        
        logger.error(f"❌ 无法识别的条件表达式: {condition}")
        return None
    
    def _parse_value(self, value_str: str) -> Any:
        """
        解析值字符串
        
        Args:
            value_str: 值字符串
        
        Returns:
            Any: 解析后的值
        """
        value_str = value_str.strip()
        
        # 字符串（单引号或双引号）
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]
        
        # 列表
        if value_str.startswith("[") and value_str.endswith("]"):
            # 简单解析，支持字符串列表
            items_str = value_str[1:-1]
            items = []
            for item in items_str.split(","):
                item = item.strip()
                if (item.startswith("'") and item.endswith("'")) or \
                   (item.startswith('"') and item.endswith('"')):
                    items.append(item[1:-1])
                else:
                    items.append(item)
            return items
        
        # 布尔值
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False
        
        # None
        if value_str.lower() == "none" or value_str.lower() == "null":
            return None
        
        # 数字
        try:
            if "." in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass
        
        # 默认返回字符串
        return value_str
    
    def _get_field_value(self, result: Dict[str, Any], field_path: str) -> Any:
        """
        获取字段值（支持嵌套路径）
        
        Args:
            result: 结果字典
            field_path: 字段路径，如 "result.risk_level" 或 "data.score"
        
        Returns:
            Any: 字段值
        """
        # 移除 "result." 前缀（如果存在）
        if field_path.startswith("result."):
            field_path = field_path[7:]
        
        # 分割路径
        parts = field_path.split(".")
        
        # 逐级获取值
        current = result
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None
        
        return current
    
    def _compare_values(
        self,
        actual: Any,
        operator: ConditionOperator,
        expected: Any
    ) -> bool:
        """
        比较值
        
        Args:
            actual: 实际值
            operator: 运算符
            expected: 期望值
        
        Returns:
            bool: 比较结果
        """
        try:
            if operator == ConditionOperator.EQUAL:
                return actual == expected
            
            elif operator == ConditionOperator.NOT_EQUAL:
                return actual != expected
            
            elif operator == ConditionOperator.GREATER_THAN:
                return actual > expected
            
            elif operator == ConditionOperator.LESS_THAN:
                return actual < expected
            
            elif operator == ConditionOperator.GREATER_EQUAL:
                return actual >= expected
            
            elif operator == ConditionOperator.LESS_EQUAL:
                return actual <= expected
            
            elif operator == ConditionOperator.IN:
                return actual in expected
            
            elif operator == ConditionOperator.NOT_IN:
                return actual not in expected
            
            elif operator == ConditionOperator.CONTAINS:
                if isinstance(actual, str):
                    return expected in actual
                elif isinstance(actual, (list, tuple)):
                    return expected in actual
                else:
                    return False
            
            else:
                logger.error(f"❌ 不支持的运算符: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 值比较失败: {actual} {operator} {expected}, 错误: {e}")
            return False
    
    def get_evaluation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取评估历史
        
        Args:
            limit: 返回的历史记录数量
        
        Returns:
            List[Dict]: 评估历史列表
        """
        return self.evaluation_history[-limit:]
    
    def clear_history(self):
        """清空评估历史"""
        self.evaluation_history.clear()
        logger.info("✅ 评估历史已清空")


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建执行器
    executor = ConditionalBranchExecutor()
    
    # 测试用例1: 简单相等比较
    result1 = {"risk_level": "high", "score": 0.85}
    condition1 = "result.risk_level == 'high'"
    print(f"\n测试1: {condition1}")
    print(f"结果: {executor.evaluate_condition(condition1, result1)}")  # True
    
    # 测试用例2: 数值比较
    condition2 = "result.score > 0.8"
    print(f"\n测试2: {condition2}")
    print(f"结果: {executor.evaluate_condition(condition2, result1)}")  # True
    
    # 测试用例3: in 运算符
    result3 = {"status": "processing"}
    condition3 = "result.status in ['pending', 'processing']"
    print(f"\n测试3: {condition3}")
    print(f"结果: {executor.evaluate_condition(condition3, result3)}")  # True
    
    # 测试用例4: 分支选择
    branches = [
        ConditionalBranch(
            condition="result.risk_level == 'high'",
            branch_to="safe_exercise_modifier",
            priority=1,
            description="高风险场景"
        ),
        ConditionalBranch(
            condition="result.risk_level == 'low'",
            branch_to="intelligent_exercise_selector",
            priority=2,
            description="低风险场景"
        )
    ]
    
    print(f"\n测试4: 分支选择")
    selected = executor.select_branch(branches, result1)
    print(f"选中分支: {selected}")  # safe_exercise_modifier
    
    # 查看评估历史
    print(f"\n评估历史:")
    for record in executor.get_evaluation_history():
        print(f"  - {record['condition']}: {record['result']}")
