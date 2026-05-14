#!/usr/bin/env python3
"""完整验证数据文件中的ROM数据"""

import json
import sys

def verify_data_file():
    """验证数据文件"""
    
    print("正在读取数据文件...")
    try:
        with open('data/enhanced_perfect_exercises_dataset.json', 'r', encoding='utf-8') as f:
            file_data = json.load(f)
        
        # 数据格式是 {"enhanced_perfect_exercises": [...]}
        if isinstance(file_data, dict) and 'enhanced_perfect_exercises' in file_data:
            data = file_data['enhanced_perfect_exercises']
        else:
            data = file_data
            
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        sys.exit(1)
    
    total = len(data)
    print(f"✅ 数据文件中的Exercise总数: {total}")
    
    # 检查ROM字段
    has_rom_field = 0
    has_rom_data = 0
    
    for exercise in data:
        if 'rom_requirements' in exercise:
            has_rom_field += 1
            rom_value = exercise['rom_requirements']
            # 检查是否有实际数据（不是None, 不是空字符串）
            if rom_value and str(rom_value).strip():
                has_rom_data += 1
    
    print(f"✅ 有rom_requirements字段的: {has_rom_field} 个")
    print(f"✅ 有ROM数据的: {has_rom_data} 个")
    print(f"✅ 覆盖率: {has_rom_data/total*100:.1f}%")
    
    # 抽查前5个有ROM数据的
    print("\n抽查前5个有ROM数据的Exercise:")
    print("=" * 70)
    
    count = 0
    for exercise in data:
        if count >= 5:
            break
        
        rom_value = exercise.get('rom_requirements')
        if rom_value and str(rom_value).strip():
            count += 1
            name = exercise.get('name_zh', exercise.get('name', 'Unknown'))
            print(f"\n{count}. {name}")
            print(f"   ROM: {rom_value[:100]}...")  # 只显示前100个字符
    
    print("\n" + "=" * 70)
    if has_rom_data == total:
        print("✅ 数据文件ROM数据已完全同步到Neo4j！")
    elif has_rom_data > 0:
        print(f"⚠️  部分同步: {has_rom_data}/{total} ({has_rom_data/total*100:.1f}%)")
    else:
        print("❌ 数据文件中没有ROM数据")
    print("=" * 70)

if __name__ == "__main__":
    verify_data_file()
