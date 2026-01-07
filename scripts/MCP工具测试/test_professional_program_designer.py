#!/usr/bin/env python3
"""
测试专业程序设计器工具
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.clients.neo4j_client import Neo4jClient
from src.applications.fitness.mcp_tools.training.professional_program_designer import ProfessionalProgramDesigner
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_professional_program_designer():
    """测试专业程序设计器"""
    
    print("\n" + "="*80)
    print("测试专业程序设计器工具")
    print("="*80)
    
    # 初始化Neo4j连接
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    try:
        # 创建工具实例
        designer = ProfessionalProgramDesigner(
            neo4j_client=neo4j_client,
            qdrant_client=None,
            three_layer_engine=None,
            logger=logger
        )
        
        print(f"\n✅ 工具名称: {designer.get_name()}")
        print(f"✅ 工具描述: {designer.get_description()}")
        print(f"✅ 工具分类: {designer.get_category()}")
        print(f"✅ 工具复杂度: {designer.get_complexity()}")
        
        # 测试场景1：增肌训练计划
        print("\n" + "="*80)
        print("测试场景1：增肌训练计划（4天分化）")
        print("="*80)
        
        result1 = await designer.execute({
            "user_id": "test_user_123",
            "training_goal": "hypertrophy",
            "training_split": "upper_lower",
            "training_days_per_week": 4,
            "difficulty_level": "intermediate",
            "available_equipment": ["barbell", "dumbbell", "cable"],
            "injury_history": []
        })
        
        print(f"\n✅ 执行成功: {result1['success']}")
        print(f"⏱️  执行时间: {result1.get('metadata', {}).get('execution_time_ms', 0):.2f}ms")
        print(f"🎯 置信度: {result1.get('confidence_score', 0)}%")
        
        if result1['success']:
            data = result1.get('data', {})
            print(f"\n📋 计划概览:")
            print(f"  计划名称: {data.get('program_name', 'N/A')}")
            print(f"  训练周期: {data.get('total_weeks', 0)}周")
            print(f"  每周训练: {data.get('training_days_per_week', 0)}天")
            print(f"  总动作数: {data.get('total_exercises', 0)}个")
            
            weekly_plan = data.get('weekly_plan', [])
            print(f"\n📅 每周训练安排 ({len(weekly_plan)}天):")
            for day in weekly_plan[:2]:  # 只显示前2天
                print(f"\n  {day.get('day_name', 'N/A')}:")
                print(f"    目标肌群: {', '.join(day.get('target_muscles', []))}")
                print(f"    动作数量: {len(day.get('exercises', []))}个")
                print(f"    预估时长: {day.get('estimated_duration_minutes', 0)}分钟")
        
        # 测试场景2：力量训练计划
        print("\n" + "="*80)
        print("测试场景2：力量训练计划（3天全身）")
        print("="*80)
        
        result2 = await designer.execute({
            "user_id": "test_user_456",
            "training_goal": "strength",
            "training_split": "full_body",
            "training_days_per_week": 3,
            "difficulty_level": "advanced",
            "available_equipment": ["barbell", "rack"],
            "injury_history": ["shoulder"]
        })
        
        print(f"\n✅ 执行成功: {result2['success']}")
        print(f"⏱️  执行时间: {result2.get('metadata', {}).get('execution_time_ms', 0):.2f}ms")
        
        if result2['success']:
            data = result2.get('data', {})
            print(f"\n📋 计划概览:")
            print(f"  计划名称: {data.get('program_name', 'N/A')}")
            print(f"  训练目标: 力量提升")
            print(f"  每周训练: {data.get('training_days_per_week', 0)}天")
            
            safety_notes = data.get('safety_notes', [])
            if safety_notes:
                print(f"\n⚠️  安全提醒 ({len(safety_notes)}条):")
                for note in safety_notes[:3]:
                    print(f"    • {note}")
        
        # 测试场景3：新手训练计划
        print("\n" + "="*80)
        print("测试场景3：新手训练计划（2天全身）")
        print("="*80)
        
        result3 = await designer.execute({
            "user_id": "test_user_789",
            "training_goal": "general_fitness",
            "training_split": "full_body",
            "training_days_per_week": 2,
            "difficulty_level": "beginner",
            "available_equipment": ["dumbbell", "bodyweight"],
            "injury_history": []
        })
        
        print(f"\n✅ 执行成功: {result3['success']}")
        
        if result3['success']:
            data = result3.get('data', {})
            print(f"\n📋 计划概览:")
            print(f"  适合人群: 健身新手")
            print(f"  训练周期: {data.get('total_weeks', 0)}周")
            print(f"  每周训练: {data.get('training_days_per_week', 0)}天")
            
            progression = data.get('progression_strategy', {})
            print(f"\n📈 进阶策略:")
            print(f"  {progression.get('description', 'N/A')}")
        
        print("\n" + "="*80)
        print("✅ 所有测试完成")
        print("="*80)
        
    finally:
        print("\n✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_professional_program_designer())
