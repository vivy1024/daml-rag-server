# -*- coding: utf-8 -*-
"""
Layer1降级方案测试

测试场景：
1. 模拟Layer1失败，验证降级到Layer2
2. 模拟Layer1和Layer2都失败，验证降级到规则匹配
3. 验证降级后仍能返回有用结果
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.framework.retrieval.true_three_layer_engine import (
    TrueThreeLayerEngine,
    LayerExecutionResult
)


@pytest.mark.asyncio
async def test_layer1_fallback_to_layer2():
    """测试Layer1失败时降级到Layer2"""
    engine = TrueThreeLayerEngine()
    
    # 模拟Layer1失败
    with patch.object(engine, '_execute_layer1_vector_search') as mock_layer1:
        mock_layer1.return_value = LayerExecutionResult(
            layer_name="Layer1-Vector",
            success=False,
            results=[],
            execution_time_ms=100.0,
            confidence=0.0,
            error="Layer1失败"
        )
        
        # 模拟Layer2降级成功
        with patch.object(engine, '_execute_layer2_graph_reasoning_fallback') as mock_layer2:
            mock_layer2.return_value = LayerExecutionResult(
                layer_name="Layer2-Graph-Fallback",
                success=True,
                results=[
                    {"exercise_name_zh": "俯卧撑", "source": "neo4j_direct_fallback"},
                    {"exercise_name_zh": "哑铃卧推", "source": "neo4j_direct_fallback"}
                ],
                execution_time_ms=200.0,
                confidence=0.7
            )
            
            # 模拟Layer3
            with patch.object(engine, '_execute_layer3_business_rules') as mock_layer3:
                mock_layer3.return_value = LayerExecutionResult(
                    layer_name="Layer3-Rules",
                    success=True,
                    results=[
                        {"exercise_name_zh": "俯卧撑", "validation_passed": True}
                    ],
                    execution_time_ms=50.0,
                    confidence=0.95
                )
                
                # 执行查询
                result = await engine.execute_three_layer_query(
                    query="胸部训练",
                    domain="fitness_exercises",
                    top_k=5
                )
                
                # 验证结果
                assert result is not None
                assert len(result.final_results) > 0
                assert result.layer_1_result.success is False
                assert result.layer_2_result.success is True
                assert result.layer_3_result.success is True
                assert "降级" in result.reasoning or "Layer2" in result.reasoning
                
                print(f"✅ Layer1降级到Layer2测试通过")
                print(f"   - Layer1: 失败")
                print(f"   - Layer2: 成功（{len(result.layer_2_result.results)}个结果）")
                print(f"   - Layer3: 成功（{len(result.final_results)}个结果）")


@pytest.mark.asyncio
async def test_layer1_and_layer2_fallback_to_rules():
    """测试Layer1和Layer2都失败时降级到规则匹配"""
    engine = TrueThreeLayerEngine()
    
    # 模拟Layer1失败
    with patch.object(engine, '_execute_layer1_vector_search') as mock_layer1:
        mock_layer1.return_value = LayerExecutionResult(
            layer_name="Layer1-Vector",
            success=False,
            results=[],
            execution_time_ms=100.0,
            confidence=0.0,
            error="Layer1失败"
        )
        
        # 模拟Layer2降级也失败
        with patch.object(engine, '_execute_layer2_graph_reasoning_fallback') as mock_layer2:
            mock_layer2.return_value = LayerExecutionResult(
                layer_name="Layer2-Graph-Fallback",
                success=False,
                results=[],
                execution_time_ms=200.0,
                confidence=0.0,
                error="Layer2降级失败"
            )
            
            # 模拟规则匹配成功
            with patch.object(engine, '_execute_rule_based_fallback') as mock_rules:
                mock_rules.return_value = LayerExecutionResult(
                    layer_name="Layer2-RuleBased-Fallback",
                    success=True,
                    results=[
                        {"exercise_name_zh": "俯卧撑", "source": "rule_based_fallback"},
                        {"exercise_name_zh": "哑铃卧推", "source": "rule_based_fallback"},
                        {"exercise_name_zh": "杠铃卧推", "source": "rule_based_fallback"}
                    ],
                    execution_time_ms=50.0,
                    confidence=0.5
                )
                
                # 模拟Layer3
                with patch.object(engine, '_execute_layer3_business_rules') as mock_layer3:
                    mock_layer3.return_value = LayerExecutionResult(
                        layer_name="Layer3-Rules",
                        success=True,
                        results=[
                            {"exercise_name_zh": "俯卧撑", "validation_passed": True},
                            {"exercise_name_zh": "哑铃卧推", "validation_passed": True}
                        ],
                        execution_time_ms=50.0,
                        confidence=0.95
                    )
                    
                    # 执行查询
                    result = await engine.execute_three_layer_query(
                        query="胸部训练",
                        domain="fitness_exercises",
                        top_k=5
                    )
                    
                    # 验证结果
                    assert result is not None
                    assert len(result.final_results) > 0
                    assert result.layer_1_result.success is False
                    assert result.layer_2_result.success is True  # 规则匹配作为Layer2
                    assert result.layer_3_result.success is True
                    assert "rule_based_fallback" in str(result.layer_2_result.results)
                    
                    print(f"✅ Layer1和Layer2降级到规则匹配测试通过")
                    print(f"   - Layer1: 失败")
                    print(f"   - Layer2: 失败")
                    print(f"   - 规则匹配: 成功（{len(result.layer_2_result.results)}个结果）")
                    print(f"   - Layer3: 成功（{len(result.final_results)}个结果）")


@pytest.mark.asyncio
async def test_rule_based_fallback_keyword_matching():
    """测试规则匹配的关键词匹配功能"""
    engine = TrueThreeLayerEngine()
    
    # 测试不同的关键词
    test_cases = [
        ("胸部训练", ["俯卧撑", "哑铃卧推", "杠铃卧推"]),
        ("背部训练", ["引体向上", "哑铃划船", "杠铃划船"]),
        ("腿部训练", ["深蹲", "杠铃深蹲", "腿举"]),
        ("肩部训练", ["哑铃推举", "侧平举", "杠铃推举"]),
    ]
    
    for query, expected_exercises in test_cases:
        result = await engine._execute_rule_based_fallback(
            query=query,
            user_profile={"fitness_level": "intermediate"},
            top_k=10
        )
        
        assert result.success is True
        assert len(result.results) > 0
        
        # 验证返回的动作名称
        exercise_names = [r.get("exercise_name_zh") for r in result.results]
        matched = any(expected in exercise_names for expected in expected_exercises)
        assert matched, f"查询'{query}'应该返回{expected_exercises}中的至少一个"
        
        print(f"✅ 关键词'{query}'匹配测试通过: {exercise_names[:3]}")


@pytest.mark.asyncio
async def test_rule_based_fallback_difficulty_filtering():
    """测试规则匹配的难度过滤功能"""
    engine = TrueThreeLayerEngine()
    
    # 测试不同的用户等级
    test_cases = [
        ("beginner", ["beginner"]),
        ("intermediate", ["beginner", "intermediate"]),
        ("advanced", ["beginner", "intermediate", "advanced"]),
    ]
    
    for user_level, expected_difficulties in test_cases:
        result = await engine._execute_rule_based_fallback(
            query="胸部训练",
            user_profile={"fitness_level": user_level},
            top_k=10
        )
        
        assert result.success is True
        assert len(result.results) > 0
        
        # 验证返回的动作难度
        for exercise in result.results:
            difficulty = exercise.get("difficulty")
            assert difficulty in expected_difficulties, \
                f"用户等级'{user_level}'不应该返回难度'{difficulty}'"
        
        print(f"✅ 用户等级'{user_level}'难度过滤测试通过")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_layer1_fallback_to_layer2())
    asyncio.run(test_layer1_and_layer2_fallback_to_rules())
    asyncio.run(test_rule_based_fallback_keyword_matching())
    asyncio.run(test_rule_based_fallback_difficulty_filtering())
    print("\n✅ 所有Layer1降级方案测试通过！")
