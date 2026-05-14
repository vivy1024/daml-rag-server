#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试参数提取器的路径解析功能

验证 recommendations[0].exercise_id 路径是否能正确提取数据
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.framework.orchestration.parameter_extractor import ParameterExtractor, ParamMapping

def test_parameter_extraction():
    """测试参数提取"""
    
    # 模拟 intelligent_exercise_selector 的返回结果
    upstream_results = {
        "intelligent_exercise_selector": {
            "success": True,
            "tool_name": "intelligent_exercise_selector",
            "recommendations": [
                {
                    "exercise_id": "ex_001",
                    "name_zh": "杠铃卧推",
                    "name_en": "Barbell Bench Press",
                    "category": "compound",
                    "difficulty": "intermediate"
                },
                {
                    "exercise_id": "ex_002",
                    "name_zh": "哑铃卧推",
                    "name_en": "Dumbbell Bench Press",
                    "category": "compound",
                    "difficulty": "beginner"
                }
            ],
            "total_found": 10
        }
    }
    
    # 创建参数映射配置
    param_mappings = [
        ParamMapping(
            source_task="intelligent_exercise_selector",
            source_path="recommendations[0].exercise_id",
            target_param="exercise_id",
            default_value=""
        )
    ]
    
    # 创建参数提取器
    extractor = ParameterExtractor()
    
    # 执行提取
    print("=" * 80)
    print("测试参数提取器")
    print("=" * 80)
    
    extracted_params = extractor.extract_from_upstream(
        param_mappings=param_mappings,
        upstream_results=upstream_results,
        context={"tool_name": "intelligent_weight_calculator"}
    )
    
    print("\n" + "=" * 80)
    print("提取结果")
    print("=" * 80)
    print(f"extracted_params: {extracted_params}")
    print(f"exercise_id: {extracted_params.get('exercise_id')}")
    
    # 验证结果
    if extracted_params.get("exercise_id") == "ex_001":
        print("\n✅ 测试通过：成功提取 exercise_id")
        return True
    else:
        print(f"\n❌ 测试失败：期望 'ex_001'，实际得到 '{extracted_params.get('exercise_id')}'")
        return False

def test_path_parsing():
    """测试路径解析"""
    extractor = ParameterExtractor()
    
    print("\n" + "=" * 80)
    print("测试路径解析")
    print("=" * 80)
    
    # 测试数据
    test_data = {
        "recommendations": [
            {"exercise_id": "ex_001", "name": "动作1"},
            {"exercise_id": "ex_002", "name": "动作2"}
        ]
    }
    
    # 测试不同的路径
    test_cases = [
        ("recommendations", "应该返回整个数组"),
        ("recommendations[0]", "应该返回第一个元素"),
        ("recommendations[0].exercise_id", "应该返回第一个元素的exercise_id"),
        ("recommendations[0].name", "应该返回第一个元素的name"),
        ("recommendations[*].exercise_id", "应该返回所有exercise_id"),
    ]
    
    for path, description in test_cases:
        result = extractor._extract_by_path(test_data, path)
        print(f"\n路径: {path}")
        print(f"描述: {description}")
        print(f"结果: {result}")
        print(f"类型: {type(result)}")

if __name__ == "__main__":
    print("🔍 开始测试参数提取器\n")
    
    # 测试路径解析
    test_path_parsing()
    
    # 测试参数提取
    success = test_parameter_extraction()
    
    sys.exit(0 if success else 1)
