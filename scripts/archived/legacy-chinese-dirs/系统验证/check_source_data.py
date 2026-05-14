"""
检查源数据文件的结构
"""

import json
import sys

# 读取源数据文件
source_file = "perfect_enhanced_dataset/data/enhanced_perfect_exercises_dataset.json"

try:
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "="*80)
    print("📊 源数据文件结构分析")
    print("="*80)
    
    # 获取第一个exercise示例
    exercises = data.get("enhanced_perfect_exercises", [])
    
    if exercises:
        first_exercise = exercises[0]
        
        print(f"\n✅ 总共有 {len(exercises)} 个Exercise")
        print(f"\n第一个Exercise的所有字段 ({len(first_exercise)}个):")
        print("-"*80)
        
        for key in sorted(first_exercise.keys()):
            value = first_exercise[key]
            value_type = type(value).__name__
            
            # 显示值的预览
            if isinstance(value, (list, dict)):
                value_preview = f"{value_type} (长度: {len(value)})"
            elif isinstance(value, str) and len(value) > 50:
                value_preview = f"{value[:50]}..."
            else:
                value_preview = str(value)
            
            print(f"  {key:30s} : {value_preview}")
        
        # 统计字段覆盖率
        print("\n" + "="*80)
        print("📊 字段覆盖率统计")
        print("="*80)
        
        field_coverage = {}
        for exercise in exercises:
            for key, value in exercise.items():
                if key not in field_coverage:
                    field_coverage[key] = 0
                
                # 检查字段是否有值
                if value is not None and value != "" and value != []:
                    field_coverage[key] += 1
        
        print(f"\n字段覆盖率 (共{len(exercises)}个Exercise):")
        print("-"*80)
        for key in sorted(field_coverage.keys()):
            count = field_coverage[key]
            percentage = (count / len(exercises)) * 100
            status = "✅" if percentage >= 90 else "⚠️" if percentage >= 50 else "❌"
            print(f"{status} {key:30s} : {count:4d}/{len(exercises)} ({percentage:5.1f}%)")
        
        # 检查关键字段
        print("\n" + "="*80)
        print("🔍 关键字段检查")
        print("="*80)
        
        key_fields = [
            "id", "name_zh", "name_en", "difficulty", "equipment_zh",
            "safety_level", "force", "mechanic", "primary_muscle_zh",
            "rep_range", "set_range", "rest_period"
        ]
        
        print("\nMCP工具需要的关键字段:")
        print("-"*80)
        for field in key_fields:
            if field in field_coverage:
                count = field_coverage[field]
                percentage = (count / len(exercises)) * 100
                status = "✅" if percentage >= 90 else "⚠️" if percentage >= 50 else "❌"
                print(f"{status} {field:30s} : {count:4d}/{len(exercises)} ({percentage:5.1f}%)")
            else:
                print(f"❌ {field:30s} : 不存在")
        
    else:
        print("❌ 未找到Exercise数据")
        
except Exception as e:
    print(f"❌ 读取文件失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
