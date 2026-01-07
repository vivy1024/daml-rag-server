# -*- coding: utf-8 -*-
"""
测试LLM决策引擎优化

验证任务4的改进：
1. 关键词权重优化
2. 完整训练计划识别准确性
3. 决策日志增强
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.applications.fitness.llm_decision_engine import LLMDecisionEngine, DAGSelectionRequest
from src.applications.fitness.dag_template_system import DAGTemplateManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_decision_engine():
    """测试LLM决策引擎"""
    
    print("=" * 80)
    print("测试LLM决策引擎优化")
    print("=" * 80)
    
    # 初始化
    engine = LLMDecisionEngine()
    
    # 模拟用户档案
    user_profile = {
        "user_id": "test_user_123",
        "basic_info": {
            "age": 28,
            "gender": "男",
            "weight": 75,
            "height": 175
        },
        "fitness_config": {
            "fitness_level": "intermediate",
            "training_days_per_week": 4
        },
        "fitness_goals": {
            "primary_goals": ["增肌", "力量提升"]
        },
        "health_profile": {
            "chronic_diseases": [],
            "injury_history": []
        }
    }
    
    # 测试用例（重点测试完整训练计划的识别）
    test_cases = [
        {
            "query": "帮我设计一个完整的4周增肌训练计划",
            "expected_template": "complete_training_plan",
            "expected_confidence_min": 0.85,
            "description": "高权重关键词：完整 + 4周"
        },
        {
            "query": "我想制定一个详细的力量训练计划",
            "expected_template": "complete_training_plan",
            "expected_confidence_min": 0.80,
            "description": "高权重关键词：详细"
        },
        {
            "query": "给我一个系统的增肌方案",
            "expected_template": "complete_training_plan",
            "expected_confidence_min": 0.80,
            "description": "高权重关键词：系统"
        },
        {
            "query": "我需要一个12周的训练计划",
            "expected_template": "complete_training_plan",
            "expected_confidence_min": 0.85,
            "description": "高权重关键词：12周"
        },
        {
            "query": "帮我设计增肌训练",
            "expected_template": "complete_training_plan",
            "expected_confidence_min": 0.70,
            "description": "中等权重关键词：设计"
        },
        {
            "query": "我应该吃什么来增肌？",
            "expected_template": "nutrition_planning",
            "expected_confidence_min": 0.75,
            "description": "营养相关查询"
        },
        {
            "query": "深蹲可以换成什么动作？",
            "expected_template": "exercise_optimization",
            "expected_confidence_min": 0.70,
            "description": "动作替代查询"
        },
        {
            "query": "什么是渐进超负荷？",
            "expected_template": "quick_consultation",
            "expected_confidence_min": 0.60,
            "description": "简单概念查询"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试用例 {i}/{len(test_cases)}: {test_case['description']}")
        print(f"{'='*80}")
        print(f"用户查询: {test_case['query']}")
        print(f"预期模板: {test_case['expected_template']}")
        print(f"预期最低置信度: {test_case['expected_confidence_min']:.2f}")
        
        # 创建请求
        request = DAGSelectionRequest(
            user_query=test_case['query'],
            user_profile=user_profile,
            available_templates=engine.template_manager.get_all_templates()
        )
        
        # 执行选择
        try:
            result = await engine.select_dag_template(request)
            
            # 输出结果
            print(f"\n实际结果:")
            print(f"  选择模板: {result.selected_template_id}")
            print(f"  置信度: {result.confidence:.2f} ({result.confidence_level.value})")
            print(f"  选择理由: {result.selection_reason}")
            if result.matched_keywords:
                print(f"  匹配关键词: {', '.join(result.matched_keywords)}")
            if result.alternative_templates:
                print(f"  备选模板: {', '.join(result.alternative_templates)}")
            if result.fallback_used:
                print(f"  ⚠️ 使用了降级策略")
            
            # 验证结果
            template_match = result.selected_template_id == test_case['expected_template']
            confidence_match = result.confidence >= test_case['expected_confidence_min']
            
            if template_match and confidence_match:
                print(f"\n✅ 测试通过")
                passed += 1
            else:
                print(f"\n❌ 测试失败")
                if not template_match:
                    print(f"   模板不匹配: 预期 {test_case['expected_template']}, 实际 {result.selected_template_id}")
                if not confidence_match:
                    print(f"   置信度不足: 预期 >={test_case['expected_confidence_min']:.2f}, 实际 {result.confidence:.2f}")
                failed += 1
                
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            logger.error(f"测试失败: {e}", exc_info=True)
            failed += 1
    
    # 输出统计
    print(f"\n{'='*80}")
    print("测试统计:")
    print(f"{'='*80}")
    print(f"总测试数: {len(test_cases)}")
    print(f"通过: {passed} ({passed/len(test_cases)*100:.1f}%)")
    print(f"失败: {failed} ({failed/len(test_cases)*100:.1f}%)")
    
    # 输出引擎统计
    stats = engine.get_selection_statistics()
    print(f"\n引擎统计:")
    print(f"  总选择次数: {stats['total_selections']}")
    print(f"  成功率: {stats['success_rate']:.1%}")
    print(f"  降级率: {stats['fallback_rate']:.1%}")
    print(f"  平均置信度: {stats['average_confidence']:.2f}")
    print(f"  按模板统计: {stats['by_template']}")
    
    return passed == len(test_cases)


if __name__ == "__main__":
    success = asyncio.run(test_decision_engine())
    sys.exit(0 if success else 1)
