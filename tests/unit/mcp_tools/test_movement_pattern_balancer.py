"""
测试movement_pattern_balancer工具

验证工具的基本功能和平衡分析逻辑
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.applications.fitness.mcp_tools.training.movement_pattern_balancer import (
    MovementPatternBalancer,
    MovementPatternBalancerInput
)


@pytest.fixture
def mock_neo4j_client():
    """模拟Neo4j客户端"""
    return Mock()


@pytest.fixture
def mock_qdrant_client():
    """模拟Qdrant客户端"""
    return Mock()


@pytest.fixture
def mock_three_layer_engine():
    """模拟三层检索引擎"""
    return Mock()


@pytest.fixture
def balancer(mock_neo4j_client, mock_qdrant_client, mock_three_layer_engine):
    """创建MovementPatternBalancer实例"""
    return MovementPatternBalancer(
        neo4j_client=mock_neo4j_client,
        qdrant_client=mock_qdrant_client,
        three_layer_engine=mock_three_layer_engine
    )


class TestMovementPatternBalancer:
    """测试MovementPatternBalancer类"""
    
    def test_get_name(self, balancer):
        """测试工具名称"""
        assert balancer.get_name() == "movement_pattern_balancer"
    
    def test_get_description(self, balancer):
        """测试工具描述"""
        description = balancer.get_description()
        assert "动作模式平衡器" in description
        assert "肌群平衡性" in description
    
    def test_get_category(self, balancer):
        """测试工具分类"""
        assert balancer.get_category() == "training"
    
    def test_get_complexity(self, balancer):
        """测试工具复杂度"""
        assert balancer.get_complexity() == "complex"
    
    def test_get_estimated_duration(self, balancer):
        """测试预估执行时间"""
        assert balancer.get_estimated_duration() == 600.0
    
    def test_input_schema(self, balancer):
        """测试输入Schema"""
        schema = balancer.get_input_schema()
        assert schema == MovementPatternBalancerInput
    
    @pytest.mark.asyncio
    async def test_execute_basic_balance_analysis(self, balancer, mock_neo4j_client):
        """测试基本平衡分析"""
        # execute调用链：
        # 1. _get_exercises_in_program -> execute_query
        # 2. _get_muscle_synergy_relations -> execute_query
        # 3. _analyze_force_type_balance -> execute_query
        mock_neo4j_client.execute_query = AsyncMock(side_effect=[
            # 第1次：_get_exercises_in_program
            [
                {
                    "e": {"exercise_id": "1", "name_zh": "卧推"},
                    "target_muscles": ["胸大肌", "三角肌前束"]
                },
                {
                    "e": {"exercise_id": "2", "name_zh": "引体向上"},
                    "target_muscles": ["背阔肌"]
                }
            ],
            # 第2次：_get_muscle_synergy_relations
            [
                {
                    "muscle": "胸大肌",
                    "synergy_partners": ["三角肌前束", "肱三头肌"],
                    "antagonist_partners": ["背阔肌"]
                },
                {
                    "muscle": "背阔肌",
                    "synergy_partners": ["斜方肌", "菱形肌"],
                    "antagonist_partners": ["胸大肌"]
                }
            ],
            # 第3次：_analyze_force_type_balance
            [
                {"force_type": "push", "count": 1},
                {"force_type": "pull", "count": 1}
            ]
        ])
        
        input_data = {
            "user_id": "test_user_123",
            "current_program": ["1", "2"],
            "target_muscle_groups": ["胸大肌", "背阔肌"]
        }
        
        result = await balancer.execute(input_data)
        
        # 验证结果结构
        assert result["success"] is True
        assert result["tool_name"] == "movement_pattern_balancer"
        assert "balance_analysis" in result
        assert "program_adjustments" in result
        assert "execution_time_ms" in result
        
        # 验证平衡分析
        balance = result["balance_analysis"]
        assert "balanced_score" in balance
        assert "imbalanced_patterns" in balance
        assert "synergy_coverage" in balance
        assert "antagonist_balance" in balance
        assert "adjustment_suggestions" in balance
        
        # 验证平衡分数
        assert 0.0 <= balance["balanced_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_execute_empty_program(self, balancer, mock_neo4j_client):
        """测试空计划"""
        # 空program: _get_exercises_in_program直接返回[]不调query
        # 空target_muscle_groups: _get_muscle_synergy_relations仍调query(1次)
        # 空program: _analyze_force_type_balance直接返回不调query
        mock_neo4j_client.execute_query = AsyncMock(return_value=[])

        input_data = {
            "user_id": "test_user_456",
            "current_program": [],
            "target_muscle_groups": []
        }

        result = await balancer.execute(input_data)

        assert result["success"] is True
        # 空计划: base_score=0.0, force_type_balance.is_balanced=False -> force_balance_score=0.5
        # balanced_score = 0.0 * 0.6 + 0.5 * 0.4 = 0.2
        assert result["balance_analysis"]["balanced_score"] == 0.2
    
    @pytest.mark.asyncio
    async def test_execute_single_muscle_group(self, balancer, mock_neo4j_client):
        """测试单一肌群训练"""
        mock_neo4j_client.execute_query = AsyncMock(side_effect=[
            # 第1次：_get_exercises_in_program
            [
                {
                    "e": {"exercise_id": "1", "name_zh": "卧推"},
                    "target_muscles": ["胸大肌"]
                }
            ],
            # 第2次：_get_muscle_synergy_relations
            [
                {
                    "muscle": "胸大肌",
                    "synergy_partners": ["三角肌前束"],
                    "antagonist_partners": []
                }
            ],
            # 第3次：_analyze_force_type_balance
            [
                {"force_type": "push", "count": 1}
            ]
        ])
        
        input_data = {
            "user_id": "test_user_789",
            "current_program": ["1"],
            "target_muscle_groups": ["胸大肌"]
        }
        
        result = await balancer.execute(input_data)
        
        assert result["success"] is True
        # 单一肌群且缺少拮抗肌群，平衡分数应该较低
        assert result["balance_analysis"]["balanced_score"] < 1.0
        # 应该有不平衡模式
        assert len(result["balance_analysis"]["imbalanced_patterns"]) > 0
    
    @pytest.mark.asyncio
    async def test_calculate_balance_score(self, balancer):
        """测试平衡分数计算"""
        muscles = {"胸大肌", "背阔肌"}
        relations = {
            "胸大肌": {
                "synergy": ["三角肌前束"],
                "antagonist": ["背阔肌"]
            },
            "背阔肌": {
                "synergy": ["斜方肌"],
                "antagonist": ["胸大肌"]
            }
        }
        
        score = balancer._calculate_balance_score(muscles, relations)
        
        # 两个肌群都有协同和拮抗关系，分数应该是1.0
        assert score == 1.0
    
    @pytest.mark.asyncio
    async def test_identify_imbalanced_patterns(self, balancer):
        """测试识别不平衡模式"""
        muscles = {"胸大肌", "背阔肌"}
        relations = {
            "胸大肌": {
                "synergy": [],  # 缺乏协同肌群
                "antagonist": ["背阔肌"]
            },
            "背阔肌": {
                "synergy": ["斜方肌", "菱形肌"],
                "antagonist": []  # 拮抗肌群不足
            }
        }
        
        patterns = balancer._identify_imbalanced_patterns(muscles, relations)
        
        # 应该识别出两个不平衡模式
        assert len(patterns) >= 2
        assert any("缺乏协同肌群训练" in p for p in patterns)
        assert any("拮抗肌群训练不足" in p for p in patterns)
    
    @pytest.mark.asyncio
    async def test_calculate_antagonist_balance(self, balancer):
        """测试计算拮抗平衡"""
        relations = {
            "胸大肌": {
                "synergy": ["三角肌前束"],
                "antagonist": ["背阔肌"]
            },
            "背阔肌": {
                "synergy": ["斜方肌"],
                "antagonist": ["胸大肌"]
            }
        }
        
        balance = balancer._calculate_antagonist_balance(relations)
        
        # 胸大肌和背阔肌互为拮抗肌群，应该是平衡的
        assert "胸大肌" in balance
        assert "背阔肌" in balance
        assert "平衡" in balance["胸大肌"]
        assert "平衡" in balance["背阔肌"]
    
    @pytest.mark.asyncio
    async def test_generate_adjustments(self, balancer):
        """测试生成调整建议"""
        analysis = {
            "balanced_score": 0.5,  # 低于0.7
            "imbalanced_patterns": [
                "胸大肌: 缺乏协同肌群训练",
                "背阔肌: 拮抗肌群训练不足"
            ],
            "synergy_coverage": {},
            "antagonist_balance": {},
            "adjustment_suggestions": []
        }
        
        adjustments = balancer._generate_adjustments(analysis, ["胸大肌", "背阔肌"])
        
        # 应该包含基本建议
        assert len(adjustments) > 0
        assert any("整体平衡性偏低" in adj for adj in adjustments)
        assert any("胸大肌" in adj for adj in adjustments)
        assert any("背阔肌" in adj for adj in adjustments)
        assert any("推拉动作平衡" in adj for adj in adjustments)
    
    @pytest.mark.asyncio
    async def test_validate_params_missing_current_program(self, balancer):
        """测试参数验证 - 缺少current_program"""
        with pytest.raises(ValueError, match="缺少参数: current_program"):
            balancer._validate_params({"user_id": "test"})
    
    @pytest.mark.asyncio
    async def test_execute_error_handling(self, balancer, mock_neo4j_client):
        """测试错误处理"""
        # 模拟数据库错误
        mock_neo4j_client.execute_query = AsyncMock(side_effect=Exception("数据库连接失败"))
        
        input_data = {
            "user_id": "test_user",
            "current_program": ["1"],
            "target_muscle_groups": ["胸大肌"]
        }
        
        result = await balancer.execute(input_data)
        
        # 应该返回失败结果，而不是抛出异常
        assert result["success"] is False
        assert result["balance_analysis"]["balanced_score"] == 0.0
        assert result["confidence_score"] == 0.0
