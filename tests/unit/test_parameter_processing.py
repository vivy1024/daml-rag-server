# -*- coding: utf-8 -*-
"""
参数处理层单元测试

测试ParameterExtractor、ParameterConverter和ParameterValidator的基本功能。

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-22
"""

import pytest
from src.framework.orchestration.parameter_extractor import ParameterExtractor, ParamMapping
from src.framework.orchestration.parameter_converter import ParameterConverter
from src.framework.orchestration.parameter_validator import ParameterValidator


class TestParameterExtractor:
    """测试参数提取器"""
    
    def test_extract_simple_field(self):
        """测试提取简单字段（通过_extract_by_path内部方法）"""
        extractor = ParameterExtractor()
        
        user_profile = {
            "user_id": 123,
            "name": "测试用户"
        }
        
        # 使用内部方法测试路径提取
        value = extractor._extract_by_path(user_profile, "user_id")
        
        assert value == 123
    
    def test_extract_nested_field(self):
        """测试提取嵌套字段"""
        extractor = ParameterExtractor()
        
        user_profile = {
            "fitness_goals": {
                "primary_goals": ["增肌", "力量"]
            }
        }
        
        value = extractor._extract_by_path(
            user_profile,
            "fitness_goals.primary_goals"
        )
        
        assert value == ["增肌", "力量"]
    
    def test_extract_array_index(self):
        """测试提取数组索引"""
        extractor = ParameterExtractor()
        
        user_profile = {
            "fitness_goals": {
                "primary_goals": ["增肌", "力量", "耐力"]
            }
        }
        
        value = extractor._extract_by_path(
            user_profile,
            "fitness_goals.primary_goals[0]"
        )
        
        assert value == "增肌"
    
    def test_extract_with_default_value(self):
        """测试使用默认值（通过extract_from_upstream）"""
        extractor = ParameterExtractor()
        
        upstream_results = {}
        context = {}
        
        mappings = [
            ParamMapping(
                source_task="get_user_profile",
                source_path="nonexistent_field",
                target_param="test_field",
                default_value="default"
            )
        ]
        
        result = extractor.extract_from_upstream(mappings, upstream_results, context)
        
        assert result["test_field"] == "default"
    
    def test_extract_from_upstream(self):
        """测试从上游任务提取参数"""
        extractor = ParameterExtractor()
        
        upstream_results = {
            "get_user_profile": {
                "user_id": 123,
                "fitness_goals": {
                    "primary_goals": ["增肌"]
                }
            }
        }
        
        context = {}
        
        mappings = [
            ParamMapping(
                source_task="get_user_profile",
                source_path="user_id",
                target_param="user_id"
            ),
            ParamMapping(
                source_task="get_user_profile",
                source_path="fitness_goals.primary_goals[0]",
                target_param="training_goal"
            )
        ]
        
        result = extractor.extract_from_upstream(mappings, upstream_results, context)
        
        assert result["user_id"] == 123
        assert result["training_goal"] == "增肌"


class TestParameterConverter:
    """测试参数转换器（v8.62.0简化版）"""
    
    def test_convert_params_batch(self):
        """测试批量处理参数（v8.62.0: 不再转换，仅验证）"""
        converter = ParameterConverter()
        
        # 前端已传递英文值
        params = {
            "training_goal": "hypertrophy",
            "fitness_level": "intermediate",
            "user_id": 123
        }
        
        result = converter.convert_params(params)
        
        # 值保持不变（不再转换）
        assert result["training_goal"] == "hypertrophy"
        assert result["fitness_level"] == "intermediate"
        assert result["user_id"] == 123
    
    def test_validate_enum_value(self):
        """测试枚举值验证"""
        converter = ParameterConverter()
        
        # 有效值
        assert converter.validate_enum_value("hypertrophy", "training_goal") is True
        assert converter.validate_enum_value("intermediate", "fitness_level") is True
        
        # 无效值
        assert converter.validate_enum_value("invalid", "training_goal") is False
    
    def test_nested_dict_processing(self):
        """测试嵌套字典处理"""
        converter = ParameterConverter()
        
        params = {
            "user_profile": {
                "training_goal": "hypertrophy",
                "fitness_level": "intermediate"
            },
            "user_id": 123
        }
        
        result = converter.convert_params(params)
        
        assert result["user_profile"]["training_goal"] == "hypertrophy"
        assert result["user_profile"]["fitness_level"] == "intermediate"
        assert result["user_id"] == 123
    
    def test_list_processing(self):
        """测试列表处理"""
        converter = ParameterConverter()
        
        params = {
            "exercises": [
                {"id": 1, "name": "卧推"},
                {"id": 2, "name": "深蹲"}
            ]
        }
        
        result = converter.convert_params(params)
        
        assert len(result["exercises"]) == 2
        assert result["exercises"][0]["id"] == 1


class TestParameterValidator:
    """测试参数验证器"""
    
    def test_validate_required_fields(self):
        """测试必需字段检查"""
        validator = ParameterValidator()
        
        param_schema = {
            "user_id": "int",
            "training_goal": "str"
        }
        
        # 缺少必需字段
        params = {"user_id": 123}
        missing = validator.check_required_fields(params, param_schema)
        assert "training_goal" in missing
        
        # 所有必需字段都存在
        params = {"user_id": 123, "training_goal": "hypertrophy"}
        missing = validator.check_required_fields(params, param_schema)
        assert len(missing) == 0
    
    def test_validate_type_match(self):
        """测试类型匹配检查"""
        validator = ParameterValidator()
        
        # 字符串类型
        assert validator.check_type_match("test", "str") is True
        assert validator.check_type_match(123, "str") is False
        
        # 整数类型
        assert validator.check_type_match(123, "int") is True
        assert validator.check_type_match("123", "int") is False
        
        # 列表类型
        assert validator.check_type_match([1, 2, 3], "list") is True
        assert validator.check_type_match("not a list", "list") is False
        
        # 字典类型
        assert validator.check_type_match({"key": "value"}, "dict") is True
        assert validator.check_type_match("not a dict", "dict") is False
    
    def test_validate_params_success(self):
        """测试参数验证成功"""
        validator = ParameterValidator()
        
        params = {
            "user_id": 123,
            "training_goal": "hypertrophy",
            "exercises": [{"id": 1}]
        }
        
        param_schema = {
            "user_id": "int",
            "training_goal": "str",
            "exercises": "list"
        }
        
        result = validator.validate_params(params, "test_tool", param_schema=param_schema)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_params_failure(self):
        """测试参数验证失败"""
        validator = ParameterValidator()
        
        params = {
            "user_id": "not an int",  # 类型错误
            "training_goal": "hypertrophy"
            # 缺少 exercises
        }
        
        param_schema = {
            "user_id": "int",
            "training_goal": "str",
            "exercises": "list"
        }
        
        result = validator.validate_params(params, "test_tool", param_schema=param_schema)
        
        assert result.is_valid is False
        assert len(result.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
