"""
测试禁忌症检查器工具

测试内容：
1. 工具基本信息
2. 健康状况列表构建
3. 禁忌症查询和匹配
4. 风险评估逻辑
5. 建议生成
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.applications.fitness.mcp_tools.safety.contraindications_checker import (
    ContraindicationsChecker,
    ContraindicationsCheckerInput,
    ContraindicationsCheckerOutput
)


@pytest.fixture
def mock_neo4j_client():
    """模拟Neo4j客户端"""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_qdrant_client():
    """模拟Qdrant客户端"""
    client = MagicMock()
    return client


@pytest.fixture
def mock_three_layer_engine():
    """模拟三层检索引擎"""
    engine = AsyncMock()
    return engine


@pytest.fixture
def mock_logger():
    """模拟日志记录器"""
    logger = MagicMock()
    return logger


@pytest.fixture
def checker(mock_neo4j_client, mock_qdrant_client, mock_three_layer_engine, mock_logger):
    """创建禁忌症检查器实例"""
    return ContraindicationsChecker(
        neo4j_client=mock_neo4j_client,
        qdrant_client=mock_qdrant_client,
        three_layer_engine=mock_three_layer_engine,
        logger=mock_logger
    )


class TestContraindicationsCheckerBasics:
    """测试工具基本信息"""
    
    def test_get_name(self, checker):
        """测试工具名称"""
        assert checker.get_name() == "contraindications_checker"
    
    def test_get_description(self, checker):
        """测试工具描述"""
        description = checker.get_description()
        assert "禁忌症检查器" in description
        assert "Neo4j" in description
    
    def test_get_category(self, checker):
        """测试工具分类"""
        assert checker.get_category() == "safety"
    
    def test_get_complexity(self, checker):
        """测试工具复杂度"""
        assert checker.get_complexity() == "complex"
    
    def test_requires_user_profile(self, checker):
        """测试是否需要用户档案"""
        assert checker.requires_user_profile() is True
    
    def test_get_dependencies(self, checker):
        """测试依赖列表"""
        deps = checker.get_dependencies()
        assert "neo4j" in deps
        assert "user_profile_mcp" in deps


class TestHealthConditionsBuilder:
    """测试健康状况列表构建"""
    
    def test_build_health_conditions_empty(self, checker):
        """测试空用户档案"""
        input_data = {"user_id": "user_123"}
        user_profile = {}
        
        conditions = checker._build_health_conditions(input_data, user_profile)
        assert isinstance(conditions, list)
        assert len(conditions) == 0
    
    def test_build_health_conditions_with_chronic_conditions(self, checker):
        """测试慢性病"""
        input_data = {"user_id": "user_123"}
        user_profile = {
            "health_profile": {
                "chronic_conditions": [
                    {"name": "高血压", "severity": "轻度"},
                    {"name": "糖尿病", "severity": "中度"}
                ]
            }
        }
        
        conditions = checker._build_health_conditions(input_data, user_profile)
        assert "高血压" in conditions
        assert "糖尿病" in conditions
        assert "高血压_轻度" in conditions
        assert "糖尿病_中度" in conditions
    
    def test_build_health_conditions_with_injury_history(self, checker):
        """测试损伤史"""
        input_data = {"user_id": "user_123"}
        user_profile = {
            "health_profile": {
                "injury_history": [
                    {"type": "肩部损伤", "body_part": "左肩"},
                    {"type": "膝盖损伤", "body_part": "右膝"}
                ]
            }
        }
        
        conditions = checker._build_health_conditions(input_data, user_profile)
        assert "肩部损伤" in conditions
        assert "膝盖损伤" in conditions
        assert "肩部损伤_左肩" in conditions
        assert "膝盖损伤_右膝" in conditions
    
    def test_build_health_conditions_with_input_conditions(self, checker):
        """测试输入参数中的健康状况"""
        input_data = {
            "user_id": "user_123",
            "health_conditions": ["腰椎间盘突出", "颈椎病"]
        }
        user_profile = {}
        
        conditions = checker._build_health_conditions(input_data, user_profile)
        assert "腰椎间盘突出" in conditions
        assert "颈椎病" in conditions
    
    def test_build_health_conditions_combined(self, checker):
        """测试组合健康状况"""
        input_data = {
            "user_id": "user_123",
            "health_conditions": ["腰椎间盘突出"]
        }
        user_profile = {
            "health_profile": {
                "chronic_conditions": [{"name": "高血压"}],
                "injury_history": [{"type": "肩部损伤"}],
                "current_symptoms": ["头晕"]
            }
        }
        
        conditions = checker._build_health_conditions(input_data, user_profile)
        assert "高血压" in conditions
        assert "肩部损伤" in conditions
        assert "头晕" in conditions
        assert "腰椎间盘突出" in conditions


class TestRiskAssessment:
    """测试风险评估逻辑"""
    
    def test_assess_risk_level_no_contraindications(self, checker):
        """测试无禁忌症"""
        contraindications = []
        risk = checker._assess_risk_level(contraindications, strict_mode=False)
        
        assert risk["total_score"] == 0
        assert risk["max_level"] == "LOW"
    
    def test_assess_risk_level_low(self, checker):
        """测试低风险"""
        contraindications = [
            {"severity_score": 2},
            {"severity_score": 3}
        ]
        risk = checker._assess_risk_level(contraindications, strict_mode=False)
        
        assert risk["total_score"] == 5
        assert risk["max_level"] == "LOW"
    
    def test_assess_risk_level_moderate(self, checker):
        """测试中等风险"""
        contraindications = [
            {"severity_score": 4},
            {"severity_score": 5}
        ]
        risk = checker._assess_risk_level(contraindications, strict_mode=False)
        
        assert risk["total_score"] == 9
        assert risk["max_level"] == "MODERATE"
    
    def test_assess_risk_level_high(self, checker):
        """测试高风险"""
        contraindications = [
            {"severity_score": 6},
            {"severity_score": 7}
        ]
        risk = checker._assess_risk_level(contraindications, strict_mode=False)
        
        assert risk["total_score"] == 13
        assert risk["max_level"] == "HIGH"
    
    def test_assess_risk_level_critical(self, checker):
        """测试严重风险"""
        contraindications = [
            {"severity_score": 8},
            {"severity_score": 9}
        ]
        risk = checker._assess_risk_level(contraindications, strict_mode=False)
        
        assert risk["total_score"] == 17
        assert risk["max_level"] == "CRITICAL"
    
    def test_assess_risk_level_strict_mode(self, checker):
        """测试严格模式"""
        contraindications = [
            {"severity_score": 4}
        ]
        
        # 非严格模式
        risk_normal = checker._assess_risk_level(contraindications, strict_mode=False)
        assert risk_normal["max_level"] == "MODERATE"
        
        # 严格模式（提升一级）
        risk_strict = checker._assess_risk_level(contraindications, strict_mode=True)
        assert risk_strict["max_level"] == "HIGH"


class TestRecommendationsGeneration:
    """测试建议生成"""
    
    def test_generate_recommendations_critical(self, checker):
        """测试严重风险建议"""
        exercise_info = {"name_zh": "深蹲"}
        contraindications = []
        risk_assessment = {"max_level": "CRITICAL", "total_score": 10}
        health_conditions = []
        
        recommendations = checker._generate_exercise_recommendations(
            exercise_info, contraindications, risk_assessment, health_conditions
        )
        
        assert recommendations["can_perform"] is False
        assert recommendations["medical_consultation_needed"] is True
        # 检查precautions列表是否包含"避免"相关内容（如果有的话）
        if recommendations["precautions"]:
            assert any("避免" in p or "禁止" in p or "不建议" in p for p in recommendations["precautions"])
    
    def test_generate_recommendations_high(self, checker):
        """测试高风险建议"""
        exercise_info = {"name_zh": "深蹲"}
        contraindications = []
        risk_assessment = {"max_level": "HIGH", "total_score": 7}
        health_conditions = []
        
        recommendations = checker._generate_exercise_recommendations(
            exercise_info, contraindications, risk_assessment, health_conditions
        )
        
        assert recommendations["can_perform"] is True
        assert recommendations["medical_consultation_needed"] is True
        assert len(recommendations["precautions"]) > 0
        assert len(recommendations["modifications"]) > 0
    
    def test_generate_recommendations_moderate(self, checker):
        """测试中等风险建议"""
        exercise_info = {"name_zh": "深蹲"}
        contraindications = []
        risk_assessment = {"max_level": "MODERATE", "total_score": 5}
        health_conditions = []
        
        recommendations = checker._generate_exercise_recommendations(
            exercise_info, contraindications, risk_assessment, health_conditions
        )
        
        assert recommendations["can_perform"] is True
        assert recommendations["medical_consultation_needed"] is False
        assert len(recommendations["precautions"]) > 0
    
    def test_generate_recommendations_with_heart_condition(self, checker):
        """测试心脏相关建议"""
        exercise_info = {"name_zh": "深蹲"}
        contraindications = [
            {"contraindication_type": "心脏疾病", "severity_score": 5}
        ]
        risk_assessment = {"max_level": "MODERATE", "total_score": 5}
        health_conditions = []
        
        recommendations = checker._generate_exercise_recommendations(
            exercise_info, contraindications, risk_assessment, health_conditions
        )
        
        # 应该包含心率监控建议
        precautions_text = " ".join(recommendations["precautions"])
        assert "心率" in precautions_text or "憋气" in precautions_text
    
    def test_generate_recommendations_with_joint_condition(self, checker):
        """测试关节相关建议"""
        exercise_info = {"name_zh": "深蹲"}
        contraindications = [
            {"contraindication_type": "关节炎", "severity_score": 5}
        ]
        risk_assessment = {"max_level": "MODERATE", "total_score": 5}
        health_conditions = []
        
        recommendations = checker._generate_exercise_recommendations(
            exercise_info, contraindications, risk_assessment, health_conditions
        )
        
        # 应该包含关节活动建议
        precautions_text = " ".join(recommendations["precautions"])
        assert "关节" in precautions_text


class TestOverallAssessment:
    """测试总体评估"""
    
    def test_generate_overall_assessment_low_risk(self, checker):
        """测试低风险总体评估"""
        exercise_results = [
            {"total_risk_score": 2, "max_risk_level": "LOW"},
            {"total_risk_score": 3, "max_risk_level": "LOW"}
        ]
        user_profile = {}
        
        assessment = checker._generate_overall_assessment(exercise_results, user_profile)
        
        assert assessment["risk_level"] == "LOW"
        assert assessment["total_risk_score"] == 5
        assert len(assessment["critical_issues"]) == 0
    
    def test_generate_overall_assessment_moderate_risk(self, checker):
        """测试中等风险总体评估"""
        exercise_results = [
            {"total_risk_score": 5, "max_risk_level": "MODERATE"},
            {"total_risk_score": 6, "max_risk_level": "MODERATE"}
        ]
        user_profile = {}
        
        assessment = checker._generate_overall_assessment(exercise_results, user_profile)
        
        assert assessment["risk_level"] == "MODERATE"
        assert assessment["total_risk_score"] == 11
    
    def test_generate_overall_assessment_high_risk(self, checker):
        """测试高风险总体评估"""
        exercise_results = [
            {"total_risk_score": 10, "max_risk_level": "HIGH"},
            {"total_risk_score": 12, "max_risk_level": "HIGH"}
        ]
        user_profile = {}
        
        assessment = checker._generate_overall_assessment(exercise_results, user_profile)
        
        assert assessment["risk_level"] == "HIGH"
        assert assessment["total_risk_score"] == 22
    
    def test_generate_overall_assessment_with_critical(self, checker):
        """测试包含严重禁忌症的总体评估"""
        exercise_results = [
            {
                "total_risk_score": 5,
                "max_risk_level": "CRITICAL",
                "exercise_name_zh": "硬拉"
            }
        ]
        user_profile = {}
        
        assessment = checker._generate_overall_assessment(exercise_results, user_profile)
        
        assert assessment["risk_level"] == "HIGH"
        assert len(assessment["critical_issues"]) > 0
        assert "硬拉" in assessment["critical_issues"][0]


class TestMedicalGuidance:
    """测试医学建议生成"""
    
    def test_generate_medical_guidance_low_risk(self, checker):
        """测试低风险医学建议"""
        overall_assessment = {
            "risk_level": "LOW",
            "total_risk_score": 5
        }
        user_profile = {}
        
        guidance = checker._generate_medical_guidance(overall_assessment, user_profile)
        
        assert "常规训练" in guidance
    
    def test_generate_medical_guidance_moderate_risk(self, checker):
        """测试中等风险医学建议"""
        overall_assessment = {
            "risk_level": "MODERATE",
            "total_risk_score": 12
        }
        user_profile = {}
        
        guidance = checker._generate_medical_guidance(overall_assessment, user_profile)
        
        assert "适度训练" in guidance or "身体信号" in guidance
    
    def test_generate_medical_guidance_high_risk(self, checker):
        """测试高风险医学建议"""
        overall_assessment = {
            "risk_level": "HIGH",
            "total_risk_score": 25
        }
        user_profile = {}
        
        guidance = checker._generate_medical_guidance(overall_assessment, user_profile)
        
        assert "医疗专业人士" in guidance or "健康检查" in guidance
    
    def test_generate_medical_guidance_with_chronic_conditions(self, checker):
        """测试有慢性病的医学建议"""
        overall_assessment = {
            "risk_level": "MODERATE",
            "total_risk_score": 10
        }
        user_profile = {
            "health_profile": {
                "chronic_conditions": [{"name": "高血压"}]
            }
        }
        
        guidance = checker._generate_medical_guidance(overall_assessment, user_profile)
        
        assert "医生" in guidance


class TestRiskLevelMapping:
    """测试风险等级映射"""
    
    def test_map_risk_level_critical(self, checker):
        """测试CRITICAL映射"""
        assert checker._map_risk_level("CRITICAL") == "CRITICAL"
        assert checker._map_risk_level("critical") == "CRITICAL"
    
    def test_map_risk_level_high(self, checker):
        """测试HIGH映射"""
        assert checker._map_risk_level("HIGH") == "HIGH"
        assert checker._map_risk_level("high") == "HIGH"
    
    def test_map_risk_level_moderate(self, checker):
        """测试MODERATE映射"""
        assert checker._map_risk_level("MODERATE") == "MODERATE"
        assert checker._map_risk_level("moderate") == "MODERATE"
    
    def test_map_risk_level_low(self, checker):
        """测试LOW映射"""
        assert checker._map_risk_level("LOW") == "LOW"
        assert checker._map_risk_level("low") == "LOW"
    
    def test_map_risk_level_none(self, checker):
        """测试None映射"""
        assert checker._map_risk_level(None) == "LOW"
    
    def test_map_risk_level_unknown(self, checker):
        """测试未知值映射"""
        assert checker._map_risk_level("unknown") == "LOW"


@pytest.mark.asyncio
class TestExecuteIntegration:
    """测试完整执行流程"""
    
    async def test_execute_no_contraindications(self, checker, mock_neo4j_client):
        """测试无禁忌症场景"""
        # 模拟Neo4j返回
        mock_neo4j_client.query.side_effect = [
            # 第一次调用：获取动作信息
            [
                {
                    "exercise_id": "ex_001",
                    "name_zh": "深蹲",
                    "name_en": "Squat",
                    "category": "力量",
                    "difficulty": "中级",
                    "safety_level": "MEDIUM_RISK",
                    "primary_muscle_zh": "股四头肌"
                }
            ],
            # 第二次调用：查询禁忌症（无结果）
            []
        ]
        
        input_data = {
            "user_id": "user_123",
            "exercise_ids": ["ex_001"],
            "include_recommendations": True,
            "strict_mode": False
        }
        
        result = await checker.execute(input_data)
        
        assert result["success"] is True
        assert result["checked_exercises"] == 1
        assert result["exercises_with_contraindications"] == 0
        assert result["high_risk_exercises"] == 0
    
    async def test_execute_with_contraindications(self, checker, mock_neo4j_client):
        """测试有禁忌症场景"""
        # 模拟Neo4j返回
        mock_neo4j_client.query.side_effect = [
            # 第一次调用：获取动作信息
            [
                {
                    "exercise_id": "ex_001",
                    "name_zh": "深蹲",
                    "name_en": "Squat",
                    "category": "力量",
                    "difficulty": "中级",
                    "safety_level": "MEDIUM_RISK",
                    "primary_muscle_zh": "股四头肌"
                }
            ],
            # 第二次调用：查询禁忌症
            [
                {
                    "injury_name_zh": "膝盖损伤",
                    "injury_name_en": "Knee Injury",
                    "category_zh": "关节损伤",
                    "risk_level": "HIGH",
                    "reason": "可能加重膝盖负担",
                    "severity_score": 7,
                    "body_parts": ["膝盖"],
                    "medical_source": "运动医学指南"
                }
            ]
        ]
        
        input_data = {
            "user_id": "user_123",
            "exercise_ids": ["ex_001"],
            "health_conditions": ["膝盖损伤"],
            "include_recommendations": True,
            "strict_mode": False
        }
        
        result = await checker.execute(input_data)
        
        assert result["success"] is True
        assert result["checked_exercises"] == 1
        assert result["exercises_with_contraindications"] == 1
        assert result["high_risk_exercises"] == 1
        assert len(result["exercise_results"]) == 1
        
        exercise_result = result["exercise_results"][0]
        assert exercise_result["has_contraindications"] is True
        assert len(exercise_result["contraindications"]) == 1
        assert exercise_result["max_risk_level"] == "HIGH"
    
    async def test_execute_exercise_not_found(self, checker, mock_neo4j_client):
        """测试动作不存在场景"""
        # 模拟Neo4j返回空结果
        mock_neo4j_client.query.return_value = []
        
        input_data = {
            "user_id": "user_123",
            "exercise_ids": ["ex_999"],
            "include_recommendations": True,
            "strict_mode": False
        }
        
        result = await checker.execute(input_data)
        
        assert result["success"] is True
        assert result["checked_exercises"] == 1
        assert result["exercises_with_contraindications"] == 1
        
        exercise_result = result["exercise_results"][0]
        assert exercise_result["exercise_name_zh"] == "Unknown"
        assert exercise_result["has_contraindications"] is True
        assert exercise_result["recommendations"]["can_perform"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
