"""
测试周期化训练量功能

验证professional_program_designer工具的周期化训练量分配：
- 第1-2周使用MAV（最大适应训练量）
- 第3周使用MRV（最大可恢复训练量，冲刺周）
- 第4周使用MEV（最小有效训练量，减量周）

作者: BUILD_BODY Team
日期: 2025-12-19
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.applications.fitness.mcp_tools.training.professional_program_designer import (
    ProfessionalProgramDesigner
)


async def test_periodization_volume():
    """测试周期化训练量功能"""
    
    print("=" * 80)
    print("测试周期化训练量功能")
    print("=" * 80)
    
    # 创建工具实例（不需要实际的客户端）
    tool = ProfessionalProgramDesigner(
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None,
        tool_registry=None
    )
    
    # 测试数据：基础训练量
    base_volume_data = {
        "mev": 10,
        "mav": 16,
        "mrv": 22,
        "volume_recommendation": {
            "recommended_weekly_sets": 16,
            "sets_per_session": 4,
            "reps_per_set_range": (8, 12),
            "rest_period_seconds": 90
        }
    }
    
    print("\n基础训练量数据:")
    print(f"  MEV（最小有效量）: {base_volume_data['mev']}组/周")
    print(f"  MAV（最大适应量）: {base_volume_data['mav']}组/周")
    print(f"  MRV（最大可恢复量）: {base_volume_data['mrv']}组/周")
    print(f"  推荐周训练量: {base_volume_data['volume_recommendation']['recommended_weekly_sets']}组/周")
    
    # 测试4周的周期化训练量
    print("\n" + "=" * 80)
    print("测试4周周期化训练量分配")
    print("=" * 80)
    
    for week_num in range(1, 5):
        print(f"\n第{week_num}周:")
        print("-" * 40)
        
        # 应用周期化训练量
        periodized_volume = tool.apply_periodization_volume(
            base_volume_data.copy(),
            week_num
        )
        
        # 提取结果
        vol_rec = periodized_volume.get("volume_recommendation", {})
        phase_name = vol_rec.get("periodization_phase", "未知")
        phase_desc = vol_rec.get("phase_description", "")
        target_volume = vol_rec.get("target_volume", 0)
        weekly_sets = vol_rec.get("recommended_weekly_sets", 0)
        
        print(f"  阶段: {phase_name}")
        print(f"  描述: {phase_desc}")
        print(f"  目标训练量: {target_volume}组/周")
        print(f"  实际周训练量: {weekly_sets}组/周")
        
        # 验证训练量是否符合预期
        if week_num in [1, 2]:
            expected_volume = base_volume_data["mav"]
            expected_phase = "积累期"
        elif week_num == 3:
            expected_volume = base_volume_data["mrv"]
            expected_phase = "冲刺期"
        elif week_num == 4:
            expected_volume = base_volume_data["mev"]
            expected_phase = "减量期"
        
        if target_volume == expected_volume and phase_name == expected_phase:
            print(f"  ✅ 验证通过: 训练量={target_volume}组/周, 阶段={phase_name}")
        else:
            print(f"  ❌ 验证失败: 期望{expected_volume}组/周（{expected_phase}），实际{target_volume}组/周（{phase_name}）")
    
    # 测试超过4周的情况（应该循环）
    print("\n" + "=" * 80)
    print("测试超过4周的周期循环")
    print("=" * 80)
    
    for week_num in [5, 6, 7, 8]:
        print(f"\n第{week_num}周:")
        print("-" * 40)
        
        periodized_volume = tool.apply_periodization_volume(
            base_volume_data.copy(),
            week_num
        )
        
        vol_rec = periodized_volume.get("volume_recommendation", {})
        phase_name = vol_rec.get("periodization_phase", "未知")
        target_volume = vol_rec.get("target_volume", 0)
        
        print(f"  阶段: {phase_name}")
        print(f"  目标训练量: {target_volume}组/周")
        
        # 验证循环逻辑
        cycle_week = ((week_num - 1) % 4) + 1
        print(f"  对应周期第{cycle_week}周")
    
    # 测试训练水平调整 + 周期化
    print("\n" + "=" * 80)
    print("测试训练水平调整 + 周期化")
    print("=" * 80)
    
    fitness_levels = ["beginner", "intermediate", "advanced", "elite"]
    
    for level in fitness_levels:
        print(f"\n训练水平: {level}")
        print("-" * 40)
        
        # 先应用训练水平调整
        adjusted_volume = tool.adjust_volume_by_level(
            base_volume_data.copy(),
            level
        )
        
        # 再应用第3周（冲刺期）的周期化
        periodized_volume = tool.apply_periodization_volume(
            adjusted_volume,
            week_number=3
        )
        
        vol_rec = periodized_volume.get("volume_recommendation", {})
        target_volume = vol_rec.get("target_volume", 0)
        
        print(f"  第3周（冲刺期）目标训练量: {target_volume}组/周")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_periodization_volume())
