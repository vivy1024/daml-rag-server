"""
测试ExerciseAlternativeFinder工具

验证替代动作查找逻辑的正确性
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import logging

from src.applications.fitness.mcp_tools.exercise import (
    ExerciseAlternativeFinder,
    ExerciseAlternativeFinderInput
)


@pytest.fixture
def mock_neo4j_client():
    """模拟Neo4j客户端"""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_logger():
    """模拟日志记录器"""
    return logging.getLogger("test")


@pytest.fixture
def tool(mock_neo4j_client, mock_logger):
    """创建工具实例"""
    return ExerciseAlternativeFinder(
        neo4j_client=mock_neo4j_client,
        qdrant_client=None,
        three_layer_engine=None,
        logger=mock_logger
    )


class TestExerciseAlternativeFinder:
    """测试ExerciseAlternativeFinder工具"""
    
    def test_get_name(self, tool):
        """测试工具名称"""
        assert tool.get_name() == "exercise_alternative_finder"
    
    def test_get_description(self, tool):
        """测试工具描述"""
        description = tool.get_description()
        assert "替代动作" in description
        assert "智能查找" in description
    
    def test_get_category(self, tool):
        """测试工具分类"""
        assert tool.get_category() == "exercise"
    
    def test_get_complexity(self, tool):
        """测试工具复杂度"""
        assert tool.get_complexity() == "medium"
    
    def test_get_estimated_duration(self, tool):
        """测试预估执行时间"""
        assert tool.get_estimated_duration() == 800.0
    
    def test_requires_user_profile(self, tool):
        """测试是否需要用户档案"""
        assert tool.requires_user_profile() is True
    
    def test_get_dependencies(self, tool):
        """测试依赖列表"""
        dependencies = tool.get_dependencies()
        assert "neo4j" in dependencies
        assert "user_profile_mcp" in dependencies
    
    @pytest.mark.asyncio
    async def test_execute_with_valid_input(self, tool, mock_neo4j_client):
        """测试正常执行流程"""
        # 模拟原动作查询结果
        mock_neo4j_client.execute_query = AsyncMock(side_effect=[
            # 第一次调用：获取原动作信息
            [{
                "e": {
                    "id": 1,
                    "name_zh": "杠铃卧推",
                    "name_en": "Barbell Bench Press",
                    "movement_pattern_zh": "推",
                    "difficulty": "intermediate",
                    "equipment_zh": ["杠铃", "卧推凳"],
                    "force": "push",
                    "mechanic": "compound"
                },
                "target_muscles": ["胸", "肩", "臂"]
            }],
            # 第二次调用：查找替代动作
            [
                {
                    "e": {
                        "id": 2,
                        "name_zh": "哑铃卧推",
                        "name_en": "Dumbbell Press",
                        "movement_pattern_zh": "推",
                        "difficulty": "intermediate",
                        "equipment_zh": ["哑铃", "卧推凳"],
                        "force": "push",
                        "mechanic": "compound"
                    },
                    "target_muscles": ["胸", "肩", "臂"]
                },
                {
                    "e": {
                        "id": 3,
                        "name_zh": "器械推胸",
                        "name_en": "Machine Press",
                        "movement_pattern_zh": "推",
                        "difficulty": "beginner",
                        "equipment_zh": ["器械"],
                        "force": "push",
                        "mechanic": "compound"
                    },
                    "target_muscles": ["胸", "肩"]
                }
            ]
        ])
        
        input_data = {
            "user_id": "test_user",
            "original_exercise_id": "1",  # 使用整数ID
            "reason": "injury",
            "constraints": {
                "injury_limitations": ["肩部"],
                "available_equipment": ["哑铃", "器械"],
                "skill_level": "intermediate"
            }
        }
        
        result = await tool.execute(input_data)
        
        # 验证结果
        assert result["success"] is True
        assert result["tool_name"] == "exercise_alternative_finder"
        assert len(result["alternatives"]) > 0
        assert "selection_rationale" in result
        assert "usage_guidelines" in result
        assert "progression_path" in result
        assert result["execution_time_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_execute_with_nonexistent_exercise(self, tool, mock_neo4j_client):
        """测试原动作不存在的情况"""
        # 模拟查询返回空结果
        mock_neo4j_client.execute_query = AsyncMock(return_value=[])
        
        input_data = {
            "user_id": "test_user",
            "original_exercise_id": "999",  # 不存在的ID
            "reason": "injury",
            "constraints": {}
        }
        
        result = await tool.execute(input_data)
        
        # 验证错误处理
        assert result["success"] is False
        assert len(result["alternatives"]) == 0
        assert "未找到原动作" in result["selection_rationale"] or "999" in result["selection_rationale"]
    
    def test_calculate_overlap(self, tool):
        """测试集合重叠度计算"""
        # 完全重叠
        overlap = tool._calculate_overlap(["胸", "肩"], ["胸", "肩"])
        assert overlap == 1.0
        
        # 部分重叠
        overlap = tool._calculate_overlap(["胸", "肩", "臂"], ["胸", "肩"])
        assert 0.6 < overlap < 0.7
        
        # 无重叠
        overlap = tool._calculate_overlap(["胸"], ["背"])
        assert overlap == 0.0
        
        # 空集合
        overlap = tool._calculate_overlap([], ["胸"])
        assert overlap == 0.0
    
    def test_calculate_similarity(self, tool):
        """测试相似度计算"""
        original = {
            "target_muscles": ["胸", "肩", "臂"],
            "movement_pattern": "推",
            "equipment_type": ["杠铃", "卧推凳"],
            "mechanic": "compound"
        }
        
        # 高度相似的候选
        candidate_high = {
            "target_muscles": ["胸", "肩", "臂"],
            "movement_pattern_zh": "推",
            "equipment_zh": ["哑铃", "卧推凳"],
            "mechanic": "compound"
        }
        
        similarity = tool._calculate_similarity(original, candidate_high)
        assert similarity > 0.8
        
        # 中等相似的候选
        candidate_medium = {
            "target_muscles": ["胸", "肩"],
            "movement_pattern_zh": "推",
            "equipment_zh": ["器械"],
            "mechanic": "compound"
        }
        
        similarity = tool._calculate_similarity(original, candidate_medium)
        assert 0.5 < similarity < 0.8
        
        # 低相似度的候选
        candidate_low = {
            "target_muscles": ["背"],
            "movement_pattern_zh": "拉",
            "equipment_zh": ["杠铃"],
            "mechanic": "compound"
        }
        
        similarity = tool._calculate_similarity(original, candidate_low)
        assert similarity < 0.5
    
    def test_generate_match_reasons(self, tool):
        """测试匹配原因生成"""
        original = {
            "target_muscles": ["胸", "肩", "臂"],
            "movement_pattern": "推",
            "equipment_type": ["杠铃", "卧推凳"],
            "mechanic": "compound"
        }
        
        candidate = {
            "target_muscles": ["胸", "肩", "臂"],
            "movement_pattern_zh": "推",
            "equipment_zh": ["哑铃", "卧推凳"],
            "mechanic": "compound"
        }
        
        reasons = tool._generate_match_reasons(original, candidate)
        
        assert len(reasons) > 0
        assert any("肌群" in reason for reason in reasons)
        assert any("运动模式" in reason for reason in reasons)
    
    def test_generate_adjustments(self, tool):
        """测试调整建议生成"""
        original = {
            "target_muscles": ["胸", "肩"],
            "movement_pattern": "推"
        }
        
        candidate = {
            "difficulty": "advanced",
            "equipment_zh": ["杠铃"]
        }
        
        constraints = {
            "skill_level": "beginner",
            "injury_limitations": ["肩部"],
            "available_equipment": ["哑铃"]
        }
        
        adjustments = tool._generate_adjustments(original, candidate, constraints)
        
        assert len(adjustments) > 0
        assert any("降低训练强度" in adj for adj in adjustments)
        assert any("保护受伤部位" in adj for adj in adjustments)
        assert any("热身" in adj for adj in adjustments)
    
    def test_generate_selection_rationale(self, tool):
        """测试选择依据生成"""
        # 损伤原因
        rationale = tool._generate_selection_rationale("injury", {"skill_level": "intermediate"})
        assert "医学安全" in rationale
        assert "intermediate" in rationale
        
        # 器械不可用原因
        rationale = tool._generate_selection_rationale("equipment_unavailable", {})
        assert "器械约束" in rationale
        
        # 难度过高原因
        rationale = tool._generate_selection_rationale("difficulty_too_high", {})
        assert "技能水平" in rationale
    
    def test_generate_usage_guidelines(self, tool):
        """测试使用指南生成"""
        # 损伤场景
        guidelines = tool._generate_usage_guidelines("injury", {"injury_limitations": ["肩部"]})
        assert len(guidelines) > 0
        assert any("疼痛" in g for g in guidelines)
        assert any("保护" in g for g in guidelines)
        
        # 一般场景
        guidelines = tool._generate_usage_guidelines("variety", {})
        assert len(guidelines) > 0
        assert any("循序渐进" in g for g in guidelines)
    
    def test_generate_progression_path(self, tool):
        """测试进阶路径生成"""
        alternatives = [
            {"name_zh": "器械推胸"},
            {"name_zh": "哑铃卧推"}
        ]
        
        path = tool._generate_progression_path("barbell_bench_press", alternatives)
        
        assert len(path) > 0
        assert any("第1阶段" in p for p in path)
        assert any("器械推胸" in p for p in path)
        assert any("barbell_bench_press" in p for p in path)
    
    def test_build_query_text(self, tool):
        """测试查询文本构建"""
        original_exercise = {
            "name_zh": "杠铃卧推",
            "target_muscles": ["胸", "肩"],
            "movement_pattern_zh": "推"
        }
        
        constraints = {
            "injury_limitations": ["肩部"],
            "available_equipment": ["哑铃", "器械"]
        }
        
        query_text = tool._build_query_text(original_exercise, "injury", constraints)
        
        assert "杠铃卧推" in query_text
        assert "胸" in query_text or "肩" in query_text
        assert "肩部" in query_text
