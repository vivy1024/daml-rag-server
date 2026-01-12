# -*- coding: utf-8 -*-
"""
参数验证器 - Parameter Validator

验证参数是否符合工具Schema，检查必需字段和类型匹配。

核心功能：
1. 验证参数是否符合Schema
2. 检查必需字段
3. 检查类型匹配（List、Dict、String等）
4. 生成详细错误信息（包含缺失参数名）
5. 详细的验证日志记录
6. 优先使用Schema注册表进行验证（合并自EnhancedParameterValidator）
7. 支持枚举类型验证（合并自EnhancedParameterValidator）

版本: v2.0.0
日期: 2026-01-12
Requirements: 2.1, 2.3, 2.4, 2.5
"""

import logging
from typing import Dict, List, Any, Optional, Type, TYPE_CHECKING
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from .mcp_tool_schema_registry import MCPToolSchemaRegistry

logger = logging.getLogger(__name__)


class ValidationResult:
    """验证结果"""
    
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def __bool__(self):
        return self.is_valid
    
    def get_error_message(self) -> str:
        """获取错误信息字符串"""
        if not self.errors:
            return ""
        return "\n".join(self.errors)


class ParameterValidator:
    """
    参数验证器
    
    验证参数是否符合工具Schema，提供详细的错误信息。
    支持Schema注册表优先验证和枚举类型验证（合并自EnhancedParameterValidator）。
    
    Requirements: 2.1, 2.3, 2.4, 2.5
    """
    
    def __init__(self, schema_registry: Optional["MCPToolSchemaRegistry"] = None):
        """
        初始化参数验证器
        
        Args:
            schema_registry: Schema注册表（可选，用于增强验证）
                            如果不传，将尝试获取全局注册表
        """
        self.logger = logger
        self._schema_registry = schema_registry
        self._schema_registry_initialized = False
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "registry_validations": 0  # 新增：使用注册表验证的次数
        }
    
    @property
    def schema_registry(self) -> Optional["MCPToolSchemaRegistry"]:
        """
        延迟获取Schema注册表
        
        避免循环导入问题，在首次访问时获取
        """
        if not self._schema_registry_initialized:
            if self._schema_registry is None:
                try:
                    from .mcp_tool_schema_registry import get_schema_registry
                    self._schema_registry = get_schema_registry()
                except ImportError:
                    self.logger.debug("Schema注册表不可用，使用基础验证")
            self._schema_registry_initialized = True
        return self._schema_registry

    def validate_params(
        self,
        params: Dict[str, Any],
        tool_name: str,
        tool_schema: Optional[Type[BaseModel]] = None,
        param_schema: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        验证参数是否符合Schema
        
        优先级（Requirements 2.3）：
        1. Pydantic Schema（如果提供）
        2. Schema注册表（如果可用）
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
        errors = []
        
        self.logger.info(f"🔍 开始参数验证: {tool_name}")
        
        try:
            # 1. 优先使用Pydantic Schema
            if tool_schema:
                try:
                    tool_schema(**params)
                    self.logger.info(f"✅ Pydantic验证通过: {tool_name}")
                    self.validation_stats["successful_validations"] += 1
                    return ValidationResult(is_valid=True)
                except ValidationError as e:
                    for error in e.errors():
                        field = ".".join(str(loc) for loc in error["loc"])
                        msg = error["msg"]
                        error_type = error["type"]
                        errors.append(f"字段 '{field}': {msg} (类型: {error_type})")
                    self._log_validation_errors(tool_name, errors)
                    self.validation_stats["failed_validations"] += 1
                    return ValidationResult(is_valid=False, errors=errors)
            
            # 2. 使用Schema注册表验证（Requirements 2.3）
            if self.schema_registry and self.schema_registry.has_schema(tool_name):
                return self._validate_with_registry_schema(params, tool_name)
            
            # 3. 使用param_schema字典验证
            if param_schema:
                missing_fields = self.check_required_fields(params, param_schema)
                if missing_fields:
                    for field in missing_fields:
                        errors.append(f"缺少必需参数: {field}")
                
                for param_name, param_value in params.items():
                    if param_name in param_schema:
                        expected_type = param_schema[param_name]
                        if not self.check_type_match(param_value, expected_type):
                            actual_type = type(param_value).__name__
                            errors.append(f"参数 '{param_name}' 类型不匹配: 期望 {expected_type}，实际 {actual_type}，值: {param_value}")
                
                if errors:
                    self._log_validation_errors(tool_name, errors)
                    self.validation_stats["failed_validations"] += 1
                    return ValidationResult(is_valid=False, errors=errors)
                else:
                    self.logger.info(f"✅ 参数验证通过: {tool_name}")
                    self.validation_stats["successful_validations"] += 1
                    return ValidationResult(is_valid=True)
            
            # 没有任何Schema时，记录INFO而非WARNING
            self.logger.info(f"ℹ️ 工具 {tool_name} 无Schema定义，使用基础验证")
            self.validation_stats["successful_validations"] += 1
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            error_msg = f"验证过程异常: {str(e)}"
            errors.append(error_msg)
            self.logger.error(f"❌ 参数验证异常: {tool_name}\n   错误: {str(e)}")
            self.validation_stats["failed_validations"] += 1
            return ValidationResult(is_valid=False, errors=errors)
    
    def _validate_with_registry_schema(
        self,
        params: Dict[str, Any],
        tool_name: str
    ) -> ValidationResult:
        """
        使用Schema注册表验证参数
        
        Requirements: 2.3, 2.4, 2.5
        
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
        self.validation_stats["registry_validations"] += 1
        
        # 1. 检查必需参数（Requirements 2.5）
        missing_params = self._check_required_params_from_registry(params, parameters, tool_name)
        errors.extend(missing_params)
        
        # 2. 检查参数类型
        type_errors = self._check_param_types_from_registry(params, parameters, tool_name)
        errors.extend(type_errors)
        
        # 3. 检查枚举值（Requirements 2.4）
        enum_errors = self._check_enum_values(params, parameters, tool_name)
        errors.extend(enum_errors)
        
        if errors:
            self._log_validation_errors(tool_name, errors)
            self.validation_stats["failed_validations"] += 1
            return ValidationResult(is_valid=False, errors=errors)
        
        self.logger.info(f"✅ Schema验证通过: {tool_name}")
        self.validation_stats["successful_validations"] += 1
        return ValidationResult(is_valid=True)

    def _check_required_params_from_registry(
        self,
        params: Dict[str, Any],
        parameters: Dict[str, Dict[str, Any]],
        tool_name: str
    ) -> List[str]:
        """
        检查必需参数（使用注册表Schema）
        
        Requirements: 2.5 - 记录具体缺失的参数名
        
        Args:
            params: 参数字典
            parameters: Schema参数定义
            tool_name: 工具名称
            
        Returns:
            错误信息列表
        """
        errors = []
        missing_params = []
        
        # 延迟导入避免循环依赖
        try:
            from .mcp_tool_schema_registry import ParamType
        except ImportError:
            ParamType = None
        
        for param_name, param_config in parameters.items():
            if param_config.get("required", False):
                if param_name not in params:
                    missing_params.append(param_name)
                    errors.append(f"缺少必需参数: {param_name}")
                elif params[param_name] is None:
                    missing_params.append(param_name)
                    errors.append(f"必需参数为None: {param_name}")
                elif params[param_name] == "":
                    # 空字符串对于必需的字符串参数也视为缺失
                    if ParamType and param_config.get("type") == ParamType.STRING:
                        missing_params.append(param_name)
                        errors.append(f"必需参数为空字符串: {param_name}")
        
        # Requirements 2.5: 记录具体缺失的参数名
        if missing_params:
            self.logger.warning(
                f"⚠️ 工具 {tool_name} 缺少必需参数: {', '.join(missing_params)}"
            )
        
        return errors
    
    def _check_param_types_from_registry(
        self,
        params: Dict[str, Any],
        parameters: Dict[str, Dict[str, Any]],
        tool_name: str
    ) -> List[str]:
        """
        检查参数类型（使用注册表Schema）
        
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
            
            if not self._is_valid_type_from_registry(param_value, expected_type):
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
        
        Requirements: 2.4 - 支持枚举类型验证
        
        Args:
            params: 参数字典
            parameters: Schema参数定义
            tool_name: 工具名称
            
        Returns:
            错误信息列表
        """
        errors = []
        
        # 延迟导入避免循环依赖
        try:
            from .mcp_tool_schema_registry import ParamType
        except ImportError:
            return errors  # 无法导入时跳过枚举检查
        
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
    
    def _is_valid_type_from_registry(self, value: Any, expected_type: Any) -> bool:
        """
        检查值是否符合期望类型（使用注册表类型）
        
        Args:
            value: 参数值
            expected_type: 期望类型（ParamType枚举）
            
        Returns:
            是否类型匹配
        """
        if value is None:
            return True
        
        # 延迟导入避免循环依赖
        try:
            from .mcp_tool_schema_registry import ParamType
        except ImportError:
            return True  # 无法导入时默认通过
        
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
        
        Requirements: 2.5 - 在验证失败时记录具体缺失的参数名
        
        Args:
            tool_name: 工具名称
            errors: 错误列表
        """
        error_msg = f"❌ 参数验证失败: {tool_name}\n"
        for error in errors:
            error_msg += f"   - {error}\n"
        self.logger.error(error_msg.rstrip())
    
    def check_required_fields(self, params: Dict[str, Any], param_schema: Dict[str, str]) -> List[str]:
        """检查必需字段（使用param_schema字典）"""
        missing_fields = []
        
        for field_name, field_type in param_schema.items():
            if "Optional" in field_type or "optional" in field_type:
                continue
            
            if field_name not in params:
                missing_fields.append(field_name)
                self.logger.debug(f"⚠️ 缺少必需字段: {field_name}")
            elif params[field_name] is None:
                missing_fields.append(field_name)
                self.logger.debug(f"⚠️ 必需字段为None: {field_name}")
        
        return missing_fields
    
    def check_type_match(self, value: Any, expected_type: str) -> bool:
        """检查类型匹配（使用字符串类型）"""
        if value is None:
            return "Optional" in expected_type or "optional" in expected_type
        
        expected_type_lower = expected_type.lower()
        
        type_checks = {
            "str": lambda v: isinstance(v, str),
            "string": lambda v: isinstance(v, str),
            "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "bool": lambda v: isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "list": lambda v: isinstance(v, list),
            "array": lambda v: isinstance(v, list),
            "dict": lambda v: isinstance(v, dict),
            "object": lambda v: isinstance(v, dict),
            "any": lambda v: True
        }
        
        for type_name, check_func in type_checks.items():
            if type_name in expected_type_lower:
                is_match = check_func(value)
                if not is_match:
                    self.logger.debug(f"⚠️ 类型不匹配: 期望 {expected_type}，实际 {type(value).__name__}")
                return is_match
        
        self.logger.warning(f"⚠️ 未知类型，跳过检查: {expected_type}")
        return True
    
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
        if not self.schema_registry:
            return []
        
        missing = []
        required_params = self.schema_registry.get_required_params(tool_name)
        
        # 延迟导入避免循环依赖
        try:
            from .mcp_tool_schema_registry import ParamType
        except ImportError:
            ParamType = None
        
        for param_name in required_params:
            if param_name not in params or params[param_name] is None:
                missing.append(param_name)
            elif params[param_name] == "":
                # 空字符串也视为缺失
                if ParamType:
                    param_config = self.schema_registry.get_param_config(tool_name, param_name)
                    if param_config and param_config.get("type") == ParamType.STRING:
                        missing.append(param_name)
        
        return missing
    
    def get_validation_stats(self) -> Dict[str, int]:
        """获取验证统计信息"""
        return self.validation_stats.copy()
    
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
        
        registered_tools = 0
        if self.schema_registry:
            registered_tools = len(self.schema_registry.get_all_tool_names())
        
        return {
            **stats,
            "success_rate": f"{success_rate:.1f}%",
            "registered_tools": registered_tools
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "registry_validations": 0
        }


# 向后兼容：提供EnhancedParameterValidator别名
EnhancedParameterValidator = ParameterValidator
