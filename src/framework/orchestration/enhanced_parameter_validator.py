# -*- coding: utf-8 -*-
"""
增强参数验证器 - Enhanced Parameter Validator

继承ParameterValidator，优先使用Schema注册表进行验证。

核心功能：
1. 优先使用MCPToolSchemaRegistry进行验证
2. 消除"没有Schema，跳过详细验证"警告
3. 在验证失败时记录具体缺失的参数名
4. 支持枚举类型验证

版本: v1.0.0
日期: 2025-12-29
Requirements: 8.2, 8.3, 8.4
"""

import logging
from typing import Dict, List, Any, Optional, Type
from pydantic import BaseModel

from .parameter_validator import ParameterValidator, ValidationResult
from .mcp_tool_schema_registry import get_schema_registry, MCPToolSchemaRegistry, ParamType

logger = logging.getLogger(__name__)


class EnhancedParameterValidator(ParameterValidator):
    """
    增强参数验证器
    
    继承ParameterValidator，优先使用Schema注册表进行验证。
    消除"没有Schema，跳过详细验证"警告。
    
    Requirements: 8.2, 8.3, 8.4
    """
    
    def __init__(self):
        """初始化增强参数验证器"""
        super().__init__()
        self.schema_registry: MCPToolSchemaRegistry = get_schema_registry()
        self.logger = logger
        self.logger.info("✅ EnhancedParameterValidator初始化完成")
    
    def validate_params(
        self,
        params: Dict[str, Any],
        tool_name: str,
        tool_schema: Optional[Type[BaseModel]] = None,
        param_schema: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        验证参数是否符合Schema
        
        优先级：
        1. Pydantic Schema（如果提供）
        2. Schema注册表
        3. param_schema字典
        
        Args:
            params: 参数字典
            tool_name: 工具名称
            tool_schema: Pydantic Schema类（可选）
            param_schema: 参数Schema字典（可选）
            
        Returns:
            ValidationResult对象
        """
        self.validation_stats["total_validations"] += 1
        
        self.logger.info(f"🔍 开始参数验证: {tool_name}")
        
        # 优先使用Pydantic Schema
        if tool_schema:
            return super().validate_params(params, tool_name, tool_schema, param_schema)
        
        # 使用Schema注册表验证
        if self.schema_registry.has_schema(tool_name):
            return self._validate_with_registry_schema(params, tool_name)
        
        # 使用param_schema字典验证
        if param_schema:
            return super().validate_params(params, tool_name, None, param_schema)
        
        # 没有任何Schema时，记录INFO而非WARNING
        self.logger.info(f"ℹ️ 工具 {tool_name} 无Schema定义，使用基础验证")
        self.validation_stats["successful_validations"] += 1
        return ValidationResult(is_valid=True)
    
    def _validate_with_registry_schema(
        self,
        params: Dict[str, Any],
        tool_name: str
    ) -> ValidationResult:
        """
        使用Schema注册表验证参数
        
        Requirements: 8.2, 8.3
        
        Args:
            params: 参数字典
            tool_name: 工具名称
            
        Returns:
            ValidationResult对象
        """
        errors = []
        schema = self.schema_registry.get_schema(tool_name)
        
        if not schema:
            self.logger.warning(f"⚠️ Schema注册表中不存在: {tool_name}")
            self.validation_stats["successful_validations"] += 1
            return ValidationResult(is_valid=True)
        
        parameters = schema.get("parameters", {})
        
        # 1. 检查必需参数
        missing_params = self._check_required_params(params, parameters, tool_name)
        errors.extend(missing_params)
        
        # 2. 检查参数类型
        type_errors = self._check_param_types(params, parameters, tool_name)
        errors.extend(type_errors)
        
        # 3. 检查枚举值
        enum_errors = self._check_enum_values(params, parameters, tool_name)
        errors.extend(enum_errors)
        
        if errors:
            self._log_validation_errors(tool_name, errors)
            self.validation_stats["failed_validations"] += 1
            return ValidationResult(is_valid=False, errors=errors)
        
        self.logger.info(f"✅ Schema验证通过: {tool_name}")
        self.validation_stats["successful_validations"] += 1
        return ValidationResult(is_valid=True)
    
    def _check_required_params(
        self,
        params: Dict[str, Any],
        parameters: Dict[str, Dict[str, Any]],
        tool_name: str
    ) -> List[str]:
        """
        检查必需参数
        
        Requirements: 8.4 - 记录具体缺失的参数名
        
        Args:
            params: 参数字典
            parameters: Schema参数定义
            tool_name: 工具名称
            
        Returns:
            错误信息列表
        """
        errors = []
        missing_params = []
        
        for param_name, param_config in parameters.items():
            if param_config.get("required", False):
                if param_name not in params:
                    missing_params.append(param_name)
                    errors.append(f"缺少必需参数: {param_name}")
                elif params[param_name] is None:
                    missing_params.append(param_name)
                    errors.append(f"必需参数为None: {param_name}")
                elif params[param_name] == "" and param_config.get("type") == ParamType.STRING:
                    # 空字符串对于必需的字符串参数也视为缺失
                    missing_params.append(param_name)
                    errors.append(f"必需参数为空字符串: {param_name}")
        
        # Requirements 8.4: 记录具体缺失的参数名
        if missing_params:
            self.logger.warning(
                f"⚠️ 工具 {tool_name} 缺少必需参数: {', '.join(missing_params)}"
            )
        
        return errors
    
    def _check_param_types(
        self,
        params: Dict[str, Any],
        parameters: Dict[str, Dict[str, Any]],
        tool_name: str
    ) -> List[str]:
        """
        检查参数类型
        
        Args:
            params: 参数字典
            parameters: Schema参数定义
            tool_name: 工具名称
            
        Returns:
            错误信息列表
        """
        errors = []
        
        for param_name, param_value in params.items():
            if param_name not in parameters:
                continue
            
            if param_value is None:
                continue
            
            param_config = parameters[param_name]
            expected_type = param_config.get("type")
            
            if not self._is_valid_type(param_value, expected_type):
                actual_type = type(param_value).__name__
                errors.append(
                    f"参数 '{param_name}' 类型不匹配: 期望 {expected_type}，实际 {actual_type}"
                )
                self.logger.debug(
                    f"⚠️ {tool_name}.{param_name} 类型不匹配: "
                    f"期望 {expected_type}，实际 {actual_type}，值: {param_value}"
                )
        
        return errors
    
    def _check_enum_values(
        self,
        params: Dict[str, Any],
        parameters: Dict[str, Dict[str, Any]],
        tool_name: str
    ) -> List[str]:
        """
        检查枚举值
        
        Args:
            params: 参数字典
            parameters: Schema参数定义
            tool_name: 工具名称
            
        Returns:
            错误信息列表
        """
        errors = []
        
        for param_name, param_value in params.items():
            if param_name not in parameters:
                continue
            
            if param_value is None:
                continue
            
            param_config = parameters[param_name]
            
            if param_config.get("type") == ParamType.ENUM:
                enum_values = param_config.get("enum_values", [])
                if enum_values and param_value not in enum_values:
                    errors.append(
                        f"参数 '{param_name}' 枚举值无效: '{param_value}'，"
                        f"有效值: {enum_values}"
                    )
                    self.logger.debug(
                        f"⚠️ {tool_name}.{param_name} 枚举值无效: "
                        f"'{param_value}'，有效值: {enum_values}"
                    )
        
        return errors
    
    def _is_valid_type(self, value: Any, expected_type: str) -> bool:
        """
        检查值是否符合期望类型
        
        Args:
            value: 参数值
            expected_type: 期望类型
            
        Returns:
            是否类型匹配
        """
        if value is None:
            return True
        
        type_checks = {
            ParamType.STRING: lambda v: isinstance(v, str),
            ParamType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            ParamType.FLOAT: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            ParamType.BOOLEAN: lambda v: isinstance(v, bool),
            ParamType.LIST: lambda v: isinstance(v, list),
            ParamType.DICT: lambda v: isinstance(v, dict),
            ParamType.ENUM: lambda v: isinstance(v, str),  # 枚举值单独检查
        }
        
        check_func = type_checks.get(expected_type)
        if check_func:
            return check_func(value)
        
        return True  # 未知类型默认通过
    
    def _log_validation_errors(self, tool_name: str, errors: List[str]):
        """
        记录验证错误
        
        Requirements: 8.4 - 在验证失败时记录具体缺失的参数名
        
        Args:
            tool_name: 工具名称
            errors: 错误列表
        """
        error_msg = f"❌ 参数验证失败: {tool_name}\n"
        for error in errors:
            error_msg += f"   - {error}\n"
        self.logger.error(error_msg.rstrip())
    
    def get_missing_required_params(
        self,
        params: Dict[str, Any],
        tool_name: str
    ) -> List[str]:
        """
        获取缺失的必需参数列表
        
        Args:
            params: 参数字典
            tool_name: 工具名称
            
        Returns:
            缺失的必需参数名称列表
        """
        missing = []
        required_params = self.schema_registry.get_required_params(tool_name)
        
        for param_name in required_params:
            if param_name not in params or params[param_name] is None:
                missing.append(param_name)
            elif params[param_name] == "":
                # 空字符串也视为缺失
                param_config = self.schema_registry.get_param_config(tool_name, param_name)
                if param_config and param_config.get("type") == ParamType.STRING:
                    missing.append(param_name)
        
        return missing
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        获取验证统计摘要
        
        Returns:
            统计信息字典
        """
        stats = self.get_validation_stats()
        total = stats["total_validations"]
        success_rate = (
            stats["successful_validations"] / total * 100
            if total > 0 else 0
        )
        
        return {
            **stats,
            "success_rate": f"{success_rate:.1f}%",
            "registered_tools": len(self.schema_registry.get_all_tool_names())
        }
