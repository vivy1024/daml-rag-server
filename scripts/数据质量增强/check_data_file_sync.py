#!/usr/bin/env python3
"""检查数据文件中的ROM数据同步状态"""

import json

def check_data_file_rom():
    """检查数据文件中的ROM数据"""
    
    # 读取数据文件
    with open('data/enhanced_perfect_exercises_dataset.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total = len(data)
    print(f"✅ 数据文件中的Exercise数量: {total}")
    
    # 检查有ROM数据的数量（ROM数据是JSON字符串，不是空字符串就算有数据）
    rom_count = len([e for e in data if 'rom_requirements' in e and e['rom_requirements'] and e['rom_requirements'].strip()])
    print(f"✅ 有ROM数据的Exercise数量: {rom_count}")
    print(f"✅ 覆盖率: {rom_count/total*100:.1f}%")
    
    # 随机抽查3个
    samples = [e for e in data if 'rom_requirements' in e and e['rom_requirements'] and e['rom_requirements'].strip()][:3]
    
    print("\n随机抽查3个Exercise的ROM数据:")
    print("-" * 60)
    for i, exercise in enumerate(samples, 1):
        print(f"\n{i}. 动作: {exercise.get('name_zh', 'N/A')}")
        rom = exercise.get('rom_requirements', '')
        if rom:
            try:
                rom_data = json.loads(rom)
                print(f"   ROM数据: {json.dumps(rom_data, ensure_ascii=False)}")
            except:
                print(f"   ROM数据: {rom}")
    
    print("\n" + "=" * 60)
    if rom_count == total:
        print("✅ 数据文件ROM数据已完全同步！")
    else:
        print(f"⚠️  数据文件ROM数据未完全同步，缺少 {total - rom_count} 个")
    print("=" * 60)

if __name__ == "__main__":
    check_data_file_rom()
