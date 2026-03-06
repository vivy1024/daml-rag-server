# -*- coding: utf-8 -*-
"""
参数处理集成测试

测试参数处理层（提取器、转换器、验证器）与DAG编排器的集成。

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-22
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.framework.orchestration.config_loader import ConfigLoader, get_config_loader
from src.framework.orchestration.parameter_extractor import ParameterExtractor, ParamMapping
from src.framework.orchestration.parameter_converter import ParameterConverter
from src.framework.orchestration.parameter_validator import ParameterValidator


class TestConfigLoader:
    """测试配置加载器"""
    
    def test_load_config(self):
        """测试加载配置文件"""
        config_loader = get_config_loader()
        
        assert config_loader is not None
        assert len(config_loader.tool_configs) > 0
        assert len(config_loader.retry_policies) > 0
        assert len(config_loader.cache_configs) > 0
        assert isinstance(config_loader.converters, dict)
    
    def test_get_tool_config(self):
        """测试获取工具配置"""
        config_loader = get_config_loader()
        
        # 测试获取智能动作选择器配置
        tool_config = config_loader.get_tool_config("intelligent_exercise_selector")
        
        assert tool_config is not None
        assert tool_config.tool_name == "intelligent_exercise_selector"
        assert len(tool_config.param_mappings) > 0
        assert len(tool_config.required_params) > 0
        
        print(f"✅ 工具配置获取成功: {tool_config.tool_name}")
        print(f"   - 参数映射: {len(tool_config.param_mappings)} 个")
        print(f"   - 必需参数: {tool_config.required_params}")
    
    def test_get_valid_values_reference(self):
        """测试获取有效值参考 — converters 可选，为空时不报错"""
        config_loader = get_config_loader()
        converters = config_loader.converters
        assert isinstance(converters, dict)


class TestParameterExtractor:
    """测试参数提取器"""
    
    def test_extract_from_upstream(self):
        """测试从上游任务结果提取参数"""
        extractor = ParameterExtractor()
        
        # 模拟上游任务结果
        upstream_results = {
            "get_user_profile": {
                "user_id": "test_user_123",
                "fitness_goals": {
                    "primary_goals": ["增肌", "力量"]
                },
                "basic_info": {
                    "fitness_level": "中级"
                }
            }
        }
        
        context = {}  # 添加context参数
        
        # 定义参数映射规则
        param_mappings = [
            ParamMapping(
                source_task="get_user_profile",
                source_path="user_id",
                target_param="user_id"
            ),
            ParamMapping(
                source_task="get_user_profile",
                source_path="fitness_goals.primary_goals[0]",
                target_param="training_goal"
            ),
            ParamMapping(
                source_task="get_user_profile",
                source_path="basic_info.fitness_level",
                target_param="fitness_level"
            )
        ]
        
        # 提取参数
        extracted_params = extractor.extract_from_upstream(
            param_mappings=param_mappings,
            upstream_results=upstream_results,
            context=context  # 添加context参数
        )
        
        assert extracted_params["user_id"] == "test_user_123"
        assert extracted_params["training_goal"] == "增肌"
        assert extracted_params["fitness_level"] == "中级"
        
        print(f"✅ 参数提取成功:")
        print(f"   - user_id: {extracted_params['user_id']}")
        print(f"   - training_goal: {extracted_params['training_goal']}")
        print(f"   - fitness_level: {extracted_params['fitness_level']}")
    
    def test_extract_with_default_value(self):
        """测试使用默认值提取参数"""
        extractor = ParameterExtractor()
        
        # 模拟空的上游任务结果
        upstream_results = {}
        context = {}  # 添加context参数
        
        # 定义带默认值的参数映射规则
        param_mappings = [
            ParamMapping(
                source_task="get_user_profile",
                source_path="user_id",
                target_param="user_id",
                default_value="default_user"
            )
        ]
        
        # 提取参数
        extracted_params = extractor.extract_from_upstream(
            param_mappings=param_mappings,
            upstream_results=upstream_results,
            context=context  # 添加context参数
        )
        
        assert extracted_params["user_id"] == "default_user"
        
        print(f"✅ 默认值提取成功:")
        print(f"   - user_id: {extracted_params['user_id']} (使用默认值)")


class TestParameterConverter:
    """测试参数转换器（v8.62.0简化版）"""
    
    def test_validate_enum_value(self):
        """测试枚举值验证"""
        converter = ParameterConverter()
        
        # 测试训练目标验证
        assert converter.validate_enum_value("hypertrophy", "training_goal") is True
        assert converter.validate_enum_value("strength", "training_goal") is True
        
        # 测试健身水平验证
        assert converter.validate_enum_value("intermediate", "fitness_level") is True
        assert converter.validate_enum_value("beginner", "fitness_level") is True
        
        # 测试无效值
        assert converter.validate_enum_value("invalid_value", "training_goal") is False
        
        print(f"✅ 枚举值验证成功:")
        print(f"   - hypertrophy (training_goal): 有效")
        print(f"   - intermediate (fitness_level): 有效")
        print(f"   - invalid_value: 无效")
    
    def test_convert_params(self):
        """测试参数处理（v8.62.0: 不再转换，仅验证）"""
        converter = ParameterConverter()
        
        # 前端已传递英文值
        params = {
            "user_id": "test_user",
            "training_goal": "hypertrophy",
            "fitness_level": "intermediate",
            "session_focus": "compound"
        }
        
        # 处理参数（不再转换，仅验证）
        converted_params = converter.convert_params(params)
        
        # 值保持不变
        assert converted_params["user_id"] == "test_user"
        assert converted_params["training_goal"] == "hypertrophy"
        assert converted_params["fitness_level"] == "intermediate"
        assert converted_params["session_focus"] == "compound"
        
        print(f"✅ 参数处理成功（v8.62.0简化版）:")
        print(f"   - training_goal: {converted_params['training_goal']}")
        print(f"   - fitness_level: {converted_params['fitness_level']}")
        print(f"   - session_focus: {converted_params['session_focus']}")


class TestParameterValidator:
    """测试参数验证器"""
    
    def test_validate_params_success(self):
        """测试参数验证成功"""
        validator = ParameterValidator()
        
        # 测试参数 - 使用虚拟工具名避免Schema注册表干扰
        # 或提供intelligent_exercise_selector的所有必需参数
        params = {
            "user_id": "test_user",
            "training_goal": "hypertrophy",
            "difficulty_level": "intermediate",
            "muscle_group": "chest",
            "available_equipment": ["dumbbell", "barbell"]
        }
        
        # 参数Schema
        param_schema = {
            "user_id": "str",
            "training_goal": "str",
            "difficulty_level": "str",
            "muscle_group": "str",
            "available_equipment": "list"
        }
        
        # 验证参数
        result = validator.validate_params(
            params=params,
            tool_name="intelligent_exercise_selector",
            param_schema=param_schema
        )
        
        assert result.is_valid
        assert len(result.errors) == 0
        
        print(f"✅ 参数验证成功")
    
    def test_validate_params_missing_required(self):
        """测试缺少必需参数"""
        validator = ParameterValidator()
        
        # 测试参数（缺少user_id）
        params = {
            "training_goal": "hypertrophy"
        }
        
        # 参数Schema
        param_schema = {
            "user_id": "str",
            "training_goal": "str"
        }
        
        # 验证参数
        result = validator.validate_params(
            params=params,
            tool_name="test_tool",
            param_schema=param_schema
        )
        
        assert not result.is_valid
        assert len(result.errors) > 0
        
        print(f"✅ 缺少必需参数检测成功:")
        print(f"   - 错误: {result.errors}")


class TestIntegration:
    """测试完整的参数处理管道"""
    
    def test_full_pipeline(self):
        """测试完整的参数处理管道：提取 → 处理 → 验证（v8.62.0简化版）"""
        # 初始化组件
        config_loader = get_config_loader()
        extractor = ParameterExtractor()
        converter = ParameterConverter()
        validator = ParameterValidator()
        
        # 步骤1: 从配置获取工具配置
        tool_config = config_loader.get_tool_config("intelligent_exercise_selector")
        assert tool_config is not None
        
        # 步骤2: 模拟上游任务结果（v8.62.0: 前端已传递英文值）
        upstream_results = {
            "get_user_profile": {
                "user_id": "test_user_123",
                "fitness_goals": {
                    "primary_goals": ["hypertrophy"]  # 前端已传递英文
                },
                "basic_info": {
                    "fitness_level": "intermediate"  # 前端已传递英文
                },
                "training_config": {
                    "available_equipment": ["dumbbell", "barbell"]  # 前端已传递英文
                },
                "target_muscle_groups": ["chest"],  # 前端已传递英文
                "muscle_group": "chest",  # 添加必需参数
                "available_equipment": ["dumbbell", "barbell"]  # Schema注册表要求的必需参数
            }
        }
        
        context = {}  # 添加context参数
        
        # 步骤3: 提取参数
        from src.framework.orchestration.parameter_extractor import ParamMapping
        
        param_mappings = [
            ParamMapping(
                source_task=mapping.source_task,
                source_path=mapping.source_path,
                target_param=mapping.target_param,
                default_value=mapping.default_value
            )
            for mapping in tool_config.param_mappings
        ]
        
        # 添加available_equipment的映射（Schema注册表要求）
        param_mappings.append(ParamMapping(
            source_task="get_user_profile",
            source_path="available_equipment",
            target_param="available_equipment",
            default_value=["dumbbell"]
        ))
        
        extracted_params = extractor.extract_from_upstream(
            param_mappings=param_mappings,
            upstream_results=upstream_results,
            context=context  # 添加context参数
        )
        
        print(f"\n步骤1 - 参数提取:")
        print(f"   提取的参数: {list(extracted_params.keys())}")
        
        # 步骤4: 处理参数（v8.62.0: 不再转换，仅验证）
        converted_params = converter.convert_params(extracted_params)
        
        print(f"\n步骤2 - 参数处理（v8.62.0简化版）:")
        print(f"   参数值保持不变（前端已传递英文）")
        
        # 步骤5: 验证参数
        param_schema = {param: "Any" for param in tool_config.required_params}
        
        validation_result = validator.validate_params(
            params=converted_params,
            tool_name="intelligent_exercise_selector",
            param_schema=param_schema
        )
        
        print(f"\n步骤3 - 参数验证:")
        print(f"   验证结果: {'✅ 通过' if validation_result.is_valid else '❌ 失败'}")
        
        # 断言（v8.62.0: 值保持不变，不再转换）
        assert "user_id" in converted_params
        assert "training_goal" in converted_params
        assert converted_params["training_goal"] == "hypertrophy"  # 保持英文
        assert converted_params["difficulty_level"] == "intermediate"  # 保持英文
        assert validation_result.is_valid
        
        print(f"\n✅ 完整参数处理管道测试成功（v8.62.0简化版）!")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
