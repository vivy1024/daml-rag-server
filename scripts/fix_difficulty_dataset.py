#!/usr/bin/env python3
"""
修复目标数据集的difficulty_zh字段

问题：
- 目标数据集中 "新手"(433个) 应该是 "零基础"
- 目标数据集中 "初学者"(599个) 应该是 "初级"

源文件正确分布：
- 零基础: 433个 (novice)
- 初级: 615个 (beginner)
- 中级: 417个 (intermediate)
- 高级: 173个 (advanced)
"""
import json
import os
from collections import Counter
from datetime import datetime

# 路径配置
TARGET_FILE = "perfect_enhanced_dataset/data/enhanced_perfect_exercises_dataset.json"
BACKUP_FILE = f"perfect_enhanced_dataset/data/enhanced_perfect_exercises_dataset_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# 修复映射
DIFFICULTY_FIX_MAP = {
    "新手": "零基础",      # novice -> 零基础
    "初学者": "初级",      # beginner -> 初级
}

def main():
    print("=" * 60)
    print("修复目标数据集的difficulty_zh字段")
    print("=" * 60)
    
    # 读取目标数据集
    print(f"\n读取文件: {TARGET_FILE}")
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    exercises = data.get('enhanced_perfect_exercises', [])
    print(f"动作数量: {len(exercises)}")
    
    # 修复前统计
    before_dist = Counter(e.get('difficulty_zh', '') for e in exercises)
    print("\n修复前 difficulty_zh 分布:")
    for k, v in before_dist.most_common():
        print(f"  {k or '(空)'}: {v}")
    
    # 执行修复
    fix_count = 0
    fix_details = Counter()
    
    for ex in exercises:
        old_diff = ex.get('difficulty_zh', '')
        if old_diff in DIFFICULTY_FIX_MAP:
            new_diff = DIFFICULTY_FIX_MAP[old_diff]
            ex['difficulty_zh'] = new_diff
            fix_count += 1
            fix_details[f"{old_diff} -> {new_diff}"] += 1
    
    print(f"\n修复数量: {fix_count}")
    print("修复详情:")
    for change, count in fix_details.most_common():
        print(f"  {change}: {count}")
    
    # 修复后统计
    after_dist = Counter(e.get('difficulty_zh', '') for e in exercises)
    print("\n修复后 difficulty_zh 分布:")
    for k, v in after_dist.most_common():
        print(f"  {k or '(空)'}: {v}")
    
    # 备份原文件
    print(f"\n备份原文件到: {BACKUP_FILE}")
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        original_content = f.read()
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        f.write(original_content)
    
    # 保存修复后的文件
    print(f"保存修复后的文件: {TARGET_FILE}")
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 修复完成!")
    print(f"   - 修复了 {fix_count} 个动作的 difficulty_zh 字段")
    print(f"   - 备份文件: {BACKUP_FILE}")

if __name__ == "__main__":
    main()
