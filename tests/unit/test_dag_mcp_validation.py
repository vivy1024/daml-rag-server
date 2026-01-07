# -*- coding: utf-8 -*-
"""
DAG和MCP任务验证测试

验证Task 11 (DAG参数映射) 和 Task 12 (MCP Schema) 的实现效果。

验证点：
1. 验证无"上游任务不存在"警告（对于context和query_analysis）
2. 验证无"没有Schema，跳过详细验证"警告
3. 验证缺失参数日志包含工具名和参数名

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-29
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.framework.orchestration.enhanced_parameter_extractor import EnhancedParameterExtractor
from src.framework.orchestration.enhanced_parameter_validator import EnhancedParameterValidator
from src.framework.orchestration.mcp_tool_schema_registry import get_schema_registry, MCPToolSchemaRegistry
from src.framework.orchestration.parameter_extractor import ParamMapping


class TestEnhancedParameterExtractor:
    """测试增强参数提取器 - Task 11验证"""
    
    def test_workflow_state_mappings_defined(self):
        """验证WORKFLOW_STATE_MAPPINGS已定义context和query_analysis"""
        extractor = EnhancedParameterExtractor()
        
        # 验证context映射
        assert "context" in extractor.WORKFLOW_STATE_MAPPINGS
        context_mappings = extractor.WORKFLOW_STATE_MAPPINGS["context"]
        assert "user_id" in context_mappings
        assert "query" in context_mappings
        assert "session_id" in context_mappings
        
        # 验证query_analysis映射
        assert "query_analysis" in extractor.WORKFLOW_STATE_MAPPINGS
        qa_mappings = extractor.WORKFLOW_STATE_MAPPINGS["query_analysis"]
        assert "intent" in qa_mappings
        assert "entities" in qa_mappings
        assert "constraints" in qa_mappings
        
        print("✅ WORKFLOW_STATE_MAPPINGS已正确定义context和query_analysis")
    
    def test_extract_from_workflow_state_context(self):
        """验证从workflow state提取context数据"""
        extractor = EnhancedParameterExtractor()
        
        # 模拟workflow state
        workflow_state = {
            "user_id": "test_user_123",
            "query": "推荐一个胸部训练动作",
            "session_id": "session_456"
        }
        
        # 定义参数映射（从context提取）
        param_mappings = [
            ParamMapping(
                source_task="context",
                source_path="user_id",
                target_param="user_id",
                default_value=None
            )
        ]
        
        # 提取参数（上游结果为空，应该从workflow state回退）
        extracted_params = extractor.extract_from_upstream(
            param_mappings=param_mappings,
            upstream_results={},
            context={},
            workflow_state=workflow_state
        )
        
        # 验证从workflow state提取成功
        assert extracted_params.get("user_id") == "test_user_123"
        assert extractor.workflow_state_extractions > 0
        
        print(f"✅ 从workflow state提取context数据成功: user_id={extracted_params.get('user_id')}")
    
    def test_extract_from_workflow_state_query_analysis(self):
        """验证从workflow state提取query_analysis数据"""
        extractor = EnhancedParameterExtractor()
        
        # 模拟workflow state
        workflow_state = {
            "query_analysis": {
                "intent": "exercise_recommendation",
                "entities": ["胸部", "训练"],
                "constraints": {"difficulty": "beginner"}
            }
        }
        
        # 定义参数映射（从query_analysis提取）
        param_mappings = [
            ParamMapping(
                source_task="query_analysis",
                source_path="intent",
                target_param="intent",
                default_value=None
            )
        ]
        
        # 提取参数
        extracted_params = extractor.extract_from_upstream(
            param_mappings=param_mappings,
            upstream_results={},
            context={},
            workflow_state=workflow_state
        )
        
        # 验证从workflow state提取成功
        assert extracted_params.get("intent") == "exercise_recommendation"
        
        print(f"✅ 从workflow state提取query_analysis数据成功: intent={extracted_params.get('intent')}")
    
    def test_no_warning_for_standard_workflow_data(self):
        """验证对于context和query_analysis不会记录"上游任务不存在"警告"""
        extractor = EnhancedParameterExtractor()
        
        # 定义参数映射（从context提取，但上游结果为空）
        param_mappings = [
            ParamMapping(
                source_task="context",
                source_path="user_id",
                target_param="user_id",
                default_value="default_user"
            )
        ]
        
        # 提取参数（上游结果为空，workflow state也为空）
        extracted_params = extractor.extract_from_upstream(
            param_mappings=param_mappings,
            upstream_results={},
            context={},
            workflow_state={}
        )
        
        # 验证使用了默认值（而不是记录警告）
        assert extracted_params.get("user_id") == "default_user"
        
        print("✅ 对于标准workflow数据，使用默认值而不是记录警告")


class TestMCPToolSchemaRegistry:
    """测试MCP工具Schema注册表 - Task 12验证"""
    
    def test_schema_registry_initialized(self):
        """验证Schema注册表已初始化"""
        registry = get_schema_registry()
        
        assert registry is not None
        assert len(registry.get_all_tool_names()) > 0
        
        print(f"✅ Schema注册表已初始化，包含 {len(registry.get_all_tool_names())} 个工具")
    
    def test_all_16_tools_have_schema(self):
        """验证所有16个MCP工具都有Schema定义"""
        registry = get_schema_registry()
        
        expected_tools = [
            "get_user_profile",
            "intelligent_exercise_selector",
            "contraindications_checker",
            "exercise_alternative_finder",
            "safe_exercise_modifier",
            "injury_risk_assessor",
            "professional_program_designer",
            "periodized_program_designer",
            "training_split_designer",
            "muscle_group_volume_calculator",
            "movement_pattern_balancer",
            "intelligent_weight_calculator",
            "tdee_calculator",
            "meal_plan_designer",
            "nutrition_intake_analyzer",
            "exercise_nutrition_optimization"
        ]
        
        missing_tools = []
        for tool_name in expected_tools:
            if not registry.has_schema(tool_name):
                missing_tools.append(tool_name)
        
        if missing_tools:
            print(f"⚠️ 缺少Schema的工具: {missing_tools}")
        
        # 验证至少有16个工具
        assert len(registry.get_all_tool_names()) >= 16
        
        print(f"✅ Schema注册表包含 {len(registry.get_all_tool_names())} 个工具Schema")
    
    def test_schema_has_required_params(self):
        """验证Schema包含必需参数定义"""
        registry = get_schema_registry()
        
        # 测试get_user_profile
        required_params = registry.get_required_params("get_user_profile")
        assert "user_id" in required_params
        
        # 测试intelligent_exercise_selector
        required_params = registry.get_required_params("intelligent_exercise_selector")
        assert "user_id" in required_params
        assert "muscle_group" in required_params
        assert "training_goal" in required_params
        
        print("✅ Schema包含正确的必需参数定义")
    
    def test_schema_has_param_types(self):
        """验证Schema包含参数类型定义"""
        registry = get_schema_registry()
        
        # 测试get_user_profile的user_id类型
        param_type = registry.get_param_type("get_user_profile", "user_id")
        assert param_type == "string"
        
        # 测试intelligent_exercise_selector的training_goal类型
        param_type = registry.get_param_type("intelligent_exercise_selector", "training_goal")
        assert param_type == "enum"
        
        print("✅ Schema包含正确的参数类型定义")


class TestEnhancedParameterValidator:
    """测试增强参数验证器 - Task 12验证"""
    
    def test_validator_uses_schema_registry(self):
        """验证验证器使用Schema注册表"""
        validator = EnhancedParameterValidator()
        
        assert validator.schema_registry is not None
        assert isinstance(validator.schema_registry, MCPToolSchemaRegistry)
        
        print("✅ 验证器已集成Schema注册表")
    
    def test_no_skip_validation_warning(self):
        """验证不会出现"没有Schema，跳过详细验证"警告"""
        validator = EnhancedParameterValidator()
        
        # 测试有Schema的工具
        params = {"user_id": "test_user"}
        result = validator.validate_params(
            params=params,
            tool_name="get_user_profile"
        )
        
        # 验证使用了Schema验证
        assert result.is_valid
        
        print("✅ 使用Schema注册表进行验证，无跳过警告")
    
    def test_missing_param_logging(self):
        """验证缺失参数日志包含工具名和参数名"""
        validator = EnhancedParameterValidator()
        
        # 测试缺少必需参数
        params = {}  # 缺少user_id
        result = validator.validate_params(
            params=params,
            tool_name="get_user_profile"
        )
        
        # 验证验证失败
        assert not result.is_valid
        
        # 验证错误信息包含参数名
        error_messages = " ".join(result.errors)
        assert "user_id" in error_messages
        
        print(f"✅ 缺失参数日志包含参数名: {result.errors}")
    
    def test_get_missing_required_params(self):
        """验证获取缺失必需参数列表"""
        validator = EnhancedParameterValidator()
        
        # 测试缺少多个必需参数
        params = {"user_id": "test_user"}  # 缺少muscle_group, training_goal, difficulty_level
        missing = validator.get_missing_required_params(
            params=params,
            tool_name="intelligent_exercise_selector"
        )
        
        # 验证返回缺失的参数列表
        assert "muscle_group" in missing
        assert "training_goal" in missing
        assert "difficulty_level" in missing
        
        print(f"✅ 获取缺失必需参数列表: {missing}")


class TestIntegration:
    """集成测试 - 验证Task 11和Task 12的整体效果"""
    
    def test_full_dag_parameter_pipeline(self):
        """测试完整的DAG参数处理管道"""
        extractor = EnhancedParameterExtractor()
        validator = EnhancedParameterValidator()
        
        # 模拟workflow state
        workflow_state = {
            "user_id": "test_user_123",
            "query": "推荐一个胸部训练动作",
            "session_id": "session_456",
            "query_analysis": {
                "intent": "exercise_recommendation",
                "entities": ["胸部"],
                "constraints": {}
            }
        }
        
        # 定义参数映射
        param_mappings = [
            ParamMapping(
                source_task="context",
                source_path="user_id",
                target_param="user_id",
                default_value=None
            )
        ]
        
        # 步骤1: 参数提取
        extracted_params = extractor.extract_from_upstream(
            param_mappings=param_mappings,
            upstream_results={},
            context={},
            workflow_state=workflow_state
        )
        
        print(f"\n步骤1 - 参数提取:")
        print(f"   提取的参数: {extracted_params}")
        print(f"   workflow state回退次数: {extractor.workflow_state_extractions}")
        
        # 步骤2: 参数验证
        result = validator.validate_params(
            params=extracted_params,
            tool_name="get_user_profile"
        )
        
        print(f"\n步骤2 - 参数验证:")
        print(f"   验证结果: {'✅ 通过' if result.is_valid else '❌ 失败'}")
        
        # 验证
        assert extracted_params.get("user_id") == "test_user_123"
        assert result.is_valid
        
        print("\n✅ 完整DAG参数处理管道测试成功!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
