# -*- coding: utf-8 -*-
"""
参数验证器 - Parameter Validator

验证参数是否符合工具Schema，检查必需字段和类型匹配。

核心功能：
1. 验证参数是否符合Schema
2. 检查必需字段
3. 检查类型匹配（List、Dict、String等）
4. 生成详细错误信息
5. 详细的验证日志记录

版本: v1.0.0
日期: 2025-12-22
"""

import logging
from typing import Dict, List, Any, Optional, Type, Tuple
from pydantic import BaseModel, ValidationError

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
    """
    
    def __init__(self):
        """初始化参数验证器"""
        self.logger = logger
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0
        }
    
    def validate_params(
        self,
        params: Dict[str, Any],
        tool_name: str,
        tool_schema: Optional[Type[BaseModel]] = None,
        param_schema: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """验证参数是否符合Schema"""
        self.validation_stats["total_validations"] += 1
        errors = []
        
        self.logger.info(f"🔍 开始参数验证: {tool_name}")
        
        try:
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
                    self.logger.error(f"❌ Pydantic验证失败: {tool_name}\n   错误: {errors}")
                    self.validation_stats["failed_validations"] += 1
                    return ValidationResult(is_valid=False, errors=errors)
            
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
                    self.logger.error(f"❌ 参数验证失败: {tool_name}\n   错误: {errors}")
                    self.validation_stats["failed_validations"] += 1
                    return ValidationResult(is_valid=False, errors=errors)
                else:
                    self.logger.info(f"✅ 参数验证通过: {tool_name}")
                    self.validation_stats["successful_validations"] += 1
                    return ValidationResult(is_valid=True)
            
            self.logger.warning(f"⚠️ 没有Schema，跳过详细验证: {tool_name}")
            self.validation_stats["successful_validations"] += 1
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            error_msg = f"验证过程异常: {str(e)}"
            errors.append(error_msg)
            self.logger.error(f"❌ 参数验证异常: {tool_name}\n   错误: {str(e)}")
            self.validation_stats["failed_validations"] += 1
            return ValidationResult(is_valid=False, errors=errors)
    
    def check_required_fields(self, params: Dict[str, Any], param_schema: Dict[str, str]) -> List[str]:
        """检查必需字段"""
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
        """检查类型匹配"""
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
    
    def get_validation_stats(self) -> Dict[str, int]:
        """获取验证统计信息"""
        return self.validation_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0
        }
