#!/usr/bin/env python3
"""
分析固定值字段和无效动作数据

1. 识别所有动作都相同的固定值字段（无意义数据）
2. 找出广告内容动作（如"随时随地简化您的训练"）
"""
import json
import glob
from collections import Counter, defaultdict

# 源文件路径
SOURCE_DIR = "yuzhen-backend/storage/app/public/exercises_v2"
DATASET_FILE = "perfect_enhanced_dataset/data/enhanced_perfect_exercises_dataset.json"

def analyze_fixed_fields():
    """分析固定值字段"""
    print("=" * 60)
    print("分析固定值字段（所有动作都相同的无意义数据）")
    print("=" * 60)
    
    # 加载数据集
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    exercises = data.get('enhanced_perfect_exercises', [])
    print(f"数据集动作数量: {len(exercises)}")
    
    # 统计每个字段的值分布
    field_values = defaultdict(Counter)
    
    for ex in exercises:
        for field, value in ex.items():
            # 转换为可哈希的字符串
            if isinstance(value, list):
                value_str = json.dumps(value, ensure_ascii=False, sort_keys=True)
            elif isinstance(value, dict):
                value_str = json.dumps(value, ensure_ascii=False, sort_keys=True)
            else:
                value_str = str(value) if value is not None else "(空)"
            
            field_values[field][value_str] += 1
    
    # 找出固定值字段（只有1-2个不同值，且最常见值占比>95%）
    print("\n=== 疑似固定值字段 ===")
    fixed_fields = []
    
    for field, counter in sorted(field_values.items()):
        total = sum(counter.values())
        unique_values = len(counter)
        most_common_value, most_common_count = counter.most_common(1)[0]
        ratio = most_common_count / total * 100
        
        # 固定值判断：唯一值<=3 且 最常见值占比>90%
        if unique_values <= 3 and ratio > 90:
            fixed_fields.append({
                'field': field,
                'unique_values': unique_values,
                'most_common': most_common_value[:100] + '...' if len(most_common_value) > 100 else most_common_value,
                'ratio': ratio,
                'count': most_common_count
            })
    
    # 按占比排序
    fixed_fields.sort(key=lambda x: -x['ratio'])
    
    print(f"\n发现 {len(fixed_fields)} 个疑似固定值字段:")
    for f in fixed_fields:
        print(f"\n  {f['field']}:")
        print(f"    唯一值数量: {f['unique_values']}")
        print(f"    最常见值: {f['most_common']}")
        print(f"    占比: {f['ratio']:.1f}% ({f['count']}/{len(exercises)})")
    
    return fixed_fields

def find_invalid_exercises():
    """找出无效动作（广告内容等）"""
    print("\n" + "=" * 60)
    print("查找无效动作（广告内容、错误数据）")
    print("=" * 60)
    
    # 加载数据集
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    exercises = data.get('enhanced_perfect_exercises', [])
    
    invalid_exercises = []
    
    # 检查条件
    for ex in exercises:
        ex_id = ex.get('id')
        name_zh = ex.get('name_zh', '')
        name_en = ex.get('name_en', '')
        primary_muscle = ex.get('primary_muscle_zh', '')
        description = ex.get('description_zh', '')
        
        reasons = []
        
        # 1. 名称包含广告关键词
        ad_keywords = ['随时随地', '简化您的训练', 'Simplify Your', 'Anywhere']
        for kw in ad_keywords:
            if kw in name_zh or kw in name_en:
                reasons.append(f"名称包含广告词: {kw}")
                break
        
        # 2. 没有主要肌群
        if not primary_muscle:
            reasons.append("缺少主要肌群")
        
        # 3. 名称过短或过长
        if len(name_zh) < 2:
            reasons.append(f"名称过短: {name_zh}")
        
        # 4. 描述为空或过短
        if not description or len(description) < 10:
            reasons.append("描述为空或过短")
        
        if reasons:
            invalid_exercises.append({
                'id': ex_id,
                'name_zh': name_zh,
                'name_en': name_en,
                'primary_muscle': primary_muscle,
                'reasons': reasons
            })
    
    print(f"\n发现 {len(invalid_exercises)} 个疑似无效动作:")
    
    # 按ID排序
    invalid_exercises.sort(key=lambda x: x['id'])
    
    for ex in invalid_exercises[:30]:  # 显示前30个
        print(f"\n  ID {ex['id']}: {ex['name_zh']}")
        print(f"    英文名: {ex['name_en']}")
        print(f"    主要肌群: {ex['primary_muscle'] or '(空)'}")
        print(f"    问题: {', '.join(ex['reasons'])}")
    
    if len(invalid_exercises) > 30:
        print(f"\n  ... 还有 {len(invalid_exercises) - 30} 个")
    
    # 输出ID列表
    print("\n=== 无效动作ID列表 ===")
    invalid_ids = [ex['id'] for ex in invalid_exercises]
    print(f"共 {len(invalid_ids)} 个: {invalid_ids}")
    
    return invalid_exercises

def main():
    fixed_fields = analyze_fixed_fields()
    invalid_exercises = find_invalid_exercises()
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    
    print(f"\n需要删除的固定值字段:")
    for f in fixed_fields:
        if f['ratio'] > 99:  # 只列出99%以上相同的
            print(f"  - {f['field']}")
    
    print(f"\n需要处理的无效动作: {len(invalid_exercises)} 个")

if __name__ == "__main__":
    main()
