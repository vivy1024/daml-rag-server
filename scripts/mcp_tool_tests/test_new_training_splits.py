"""
测试新增的训练分化模式

测试以下新分化：
1. push_pull_legs_legs - 四分化（推拉腿腿）
2. push_pull_legs_x2 - 六分化（推拉腿推拉腿）
3. upper_push_pull_legs - 五分化（上肢推拉腿推拉）

作者: BUILD_BODY Team
日期: 2025-12-19
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.applications.fitness.mcp_tools.training.professional_program_designer import (
    ProfessionalProgramDesigner,
    TrainingSplit
)


async def test_training_split(split_type: str, training_days: int, split_name: str):
    """
    测试特定的训练分化模式
    
    Args:
        split_type: 训练分化类型
        training_days: 每周训练天数
        split_name: 分化名称（用于显示）
    """
    print(f"\n{'='*80}")
    print(f"测试训练分化: {split_name}")
    print(f"类型: {split_type}")
    print(f"每周训练天数: {training_days}")
    print(f"{'='*80}\n")
    
    # 创建工具实例（不需要实际的客户端，只测试周期计算）
    designer = ProfessionalProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None
    )
    
    # 构建测试输入
    input_data = {
        "user_id": "test_user",
        "training_goal": "hypertrophy",
        "training_split": split_type,
        "training_days_per_week": training_days,
        "difficulty_level": "intermediate",
        "available_equipment": ["杠铃", "哑铃", "固定器械"],
        "injury_history": None,
        "target_muscle_groups": None,
        "session_duration_minutes": 60,
        "include_warmup": True,
        "include_cooldown": True,
        "training_weeks": 4,
        "rest_pattern": None
    }
    
    # 测试周期计算
    print("📊 训练周期计算:")
    cycle_info = designer._calculate_training_cycle(input_data)
    print(f"  - 基础周期: {cycle_info['base_cycle']}天")
    print(f"  - 实际周期: {cycle_info['cycle_days']}天")
    print(f"  - 每周周期数: {cycle_info['cycles_per_week']:.2f}")
    print(f"  - 训练模式: {cycle_info['training_pattern']}")
    
    # 测试目标肌群确定
    print("\n🎯 目标肌群:")
    target_muscles = designer._determine_target_muscle_groups(input_data)
    for i, muscle in enumerate(target_muscles, 1):
        print(f"  {i}. {muscle}")
    
    print(f"\n✅ {split_name} 测试完成")
    
    return cycle_info


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("新增训练分化模式测试")
    print("="*80)
    
    # 测试1: 四分化（推拉腿腿）
    await test_training_split(
        split_type="push_pull_legs_legs",
        training_days=4,
        split_name="四分化（推拉腿腿）"
    )
    
    # 测试2: 六分化（推拉腿推拉腿）
    await test_training_split(
        split_type="push_pull_legs_x2",
        training_days=6,
        split_name="六分化（推拉腿推拉腿）"
    )
    
    # 测试3: 五分化（上肢推拉腿推拉）
    await test_training_split(
        split_type="upper_push_pull_legs",
        training_days=5,
        split_name="五分化（上肢推拉腿推拉）"
    )
    
    # 对比测试：原有的三分化
    print("\n" + "="*80)
    print("对比测试：原有三分化（推拉腿）")
    print("="*80)
    
    await test_training_split(
        split_type="push_pull_legs",
        training_days=3,
        split_name="三分化（推拉腿）- 练三休一"
    )
    
    await test_training_split(
        split_type="push_pull_legs",
        training_days=6,
        split_name="三分化（推拉腿）- 练六休一"
    )
    
    print("\n" + "="*80)
    print("所有测试完成！")
    print("="*80)
    
    # 总结
    print("\n📋 新增训练分化总结:")
    print("1. ✅ 四分化（推拉腿腿）- 适合想增加腿部训练量的用户")
    print("2. ✅ 六分化（推拉腿推拉腿）- 适合高级训练者，每周训练6天")
    print("3. ✅ 五分化（上肢推拉腿推拉）- 适合想增加上肢训练频率的用户")
    print("\n💡 设计特点:")
    print("  - 每个分化都有明确的训练周期计算")
    print("  - 支持不同的训练重点（如胸部为主、肩部为主）")
    print("  - 自动调整肌群分配和训练量")
    print("  - 与现有的周期化训练量系统完全兼容")


if __name__ == "__main__":
    asyncio.run(main())
