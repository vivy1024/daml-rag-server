# -*- coding: utf-8 -*-
"""测试GraphRAG过滤条件修复

验证_build_qdrant_filters方法的字段映射和值转换
"""

import sys
sys.path.insert(0, '/app')

def test_build_qdrant_filters():
    """测试_build_qdrant_filters方法"""
    print("=" * 60)
    print("🔍 测试GraphRAG过滤条件修复")
    print("=" * 60)
    
    # 模拟GraphRAGQueryTool的_build_qdrant_filters方法
    def build_qdrant_filters(domain, filters):
        """复制自graphrag.py的_build_qdrant_filters方法"""
        if not filters:
            return None
            
        qdrant_filters = {}
        
        # 字段名映射：业务字段 → Qdrant payload字段
        field_mapping = {
            "muscle_group": "primary_muscle_zh",
            "difficulty_level": "difficulty",
            "available_equipment": "equipment_zh",
            "injury_history": None,
            "label": None,
        }
        
        # difficulty值映射：英文 → 中文
        difficulty_mapping = {
            "beginner": "新手",
            "intermediate": "中级",
            "advanced": "高级",
            "expert": "专家",
            "新手": "新手",
            "中级": "中级",
            "高级": "高级",
            "专家": "专家",
        }
        
        for key, value in filters.items():
            if value is None or value == "" or value == []:
                continue
                
            mapped_key = field_mapping.get(key, key)
            
            if mapped_key is None:
                print(f"  跳过不支持的字段: {key}")
                continue
            
            if mapped_key == "difficulty" and isinstance(value, str):
                mapped_value = difficulty_mapping.get(value.lower(), value)
                qdrant_filters[mapped_key] = mapped_value
                print(f"  difficulty转换: {value} → {mapped_value}")
            else:
                qdrant_filters[mapped_key] = value
        
        return qdrant_filters if qdrant_filters else None
    
    # 测试用例
    test_cases = [
        {
            "name": "业务层典型过滤条件",
            "filters": {
                "muscle_group": "胸部",
                "difficulty_level": "beginner",
                "available_equipment": ["哑铃", "杠铃"],
                "injury_history": []
            }
        },
        {
            "name": "中文difficulty值",
            "filters": {
                "difficulty_level": "新手"
            }
        },
        {
            "name": "空过滤条件",
            "filters": {}
        },
        {
            "name": "包含label字段（应跳过）",
            "filters": {
                "label": "Exercise",
                "difficulty_level": "intermediate"
            }
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n📋 测试用例 {i+1}: {case['name']}")
        print(f"  输入: {case['filters']}")
        result = build_qdrant_filters("fitness_exercises", case['filters'])
        print(f"  输出: {result}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_build_qdrant_filters()
