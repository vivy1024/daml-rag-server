#!/usr/bin/env python3
"""
分析Exercise数据质量

检查所有1603个动作的数据质量问题：
1. description_en 和 correct_steps_en 是否相同
2. description_zh 和 correct_steps_zh 是否相同
3. correct_steps_zh 是否为空
4. 提取样本供人工审查
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("Exercise数据质量分析")
print("=" * 80)

# 读取源数据
data_file = 'data/enhanced_perfect_exercises_dataset.json'
print(f"\n读取数据文件: {data_file}")

with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 提取exercises数组
if isinstance(data, dict):
    if 'enhanced_perfect_exercises' in data:
        exercises = data['enhanced_perfect_exercises']
    elif 'exercises' in data:
        exercises = data['exercises']
    else:
        print(f"错误：无法识别的数据格式，可用键: {list(data.keys())}")
        sys.exit(1)
elif isinstance(data, list):
    exercises = data
else:
    print("错误：无法识别的数据格式")
    sys.exit(1)

print(f"总动作数: {len(exercises)}")

# 统计变量
stats = {
    "total": len(exercises),
    "desc_en_equals_steps_en": 0,  # description_en 和 correct_steps_en 内容相同
    "desc_zh_equals_steps_zh": 0,  # description_zh 和 correct_steps_zh 内容相同
    "steps_zh_empty": 0,  # correct_steps_zh 为空
    "steps_en_empty": 0,  # correct_steps_en 为空
    "both_steps_empty": 0,  # 两者都为空
    "has_professional_desc": 0,  # 有 description_zh_professional
}

# 样本收集
samples = {
    "desc_en_equals_steps_en": [],  # description_en = correct_steps_en
    "desc_zh_equals_steps_zh": [],  # description_zh = correct_steps_zh
    "steps_zh_empty": [],  # correct_steps_zh 为空
    "normal": [],  # 正常的（都不相同且都不为空）
}

print("\n开始分析...")

for exercise in exercises:
    ex_id = exercise.get('id')
    name_zh = exercise.get('name_zh', '')
    
    # 获取字段（处理None值）
    desc_en = (exercise.get('description_en') or '').strip()
    desc_zh = (exercise.get('description_zh') or '').strip()
    steps_en = exercise.get('correct_steps_en') or []
    steps_zh = exercise.get('correct_steps_zh') or []
    desc_zh_prof = exercise.get('description_zh_professional') or ''
    
    # 统计 description_zh_professional
    if desc_zh_prof:
        stats["has_professional_desc"] += 1
    
    # 检查 correct_steps_zh 是否为空
    if not steps_zh or len(steps_zh) == 0:
        stats["steps_zh_empty"] += 1
        if len(samples["steps_zh_empty"]) < 5:
            samples["steps_zh_empty"].append({
                "id": ex_id,
                "name_zh": name_zh,
                "desc_zh": desc_zh[:100],
                "steps_zh": steps_zh,
                "desc_zh_prof": desc_zh_prof[:100] if desc_zh_prof else None
            })
    
    # 检查 correct_steps_en 是否为空
    if not steps_en or len(steps_en) == 0:
        stats["steps_en_empty"] += 1
    
    # 检查两者都为空
    if (not steps_zh or len(steps_zh) == 0) and (not steps_en or len(steps_en) == 0):
        stats["both_steps_empty"] += 1
    
    # 将 correct_steps_en 数组转换为文本（用于比较）
    if steps_en and len(steps_en) > 0:
        # 提取 text 字段
        if isinstance(steps_en[0], dict):
            steps_en_text = '\n'.join([step.get('text', '') for step in steps_en])
        else:
            steps_en_text = '\n'.join(steps_en)
        
        # 清理 description_en 中的格式标记
        desc_en_clean = desc_en.replace('**Correct Steps:**', '').replace('**', '').strip()
        desc_en_clean = '\n'.join([line.strip() for line in desc_en_clean.split('\n') if line.strip()])
        
        # 比较内容（忽略格式差异）
        # 移除数字编号和标点
        import re
        desc_en_normalized = re.sub(r'^\d+\.\s*', '', desc_en_clean, flags=re.MULTILINE)
        steps_en_normalized = re.sub(r'^\d+\.\s*', '', steps_en_text, flags=re.MULTILINE)
        
        # 比较核心内容
        if desc_en_normalized.replace(' ', '').replace('\n', '') == steps_en_normalized.replace(' ', '').replace('\n', ''):
            stats["desc_en_equals_steps_en"] += 1
            if len(samples["desc_en_equals_steps_en"]) < 5:
                samples["desc_en_equals_steps_en"].append({
                    "id": ex_id,
                    "name_zh": name_zh,
                    "desc_en": desc_en[:150],
                    "steps_en": steps_en_text[:150]
                })
    
    # 检查 description_zh 和 correct_steps_zh
    if steps_zh and len(steps_zh) > 0:
        if isinstance(steps_zh[0], dict):
            steps_zh_text = '\n'.join([step.get('text', '') for step in steps_zh])
        else:
            steps_zh_text = '\n'.join(steps_zh)
        
        if desc_zh == steps_zh_text:
            stats["desc_zh_equals_steps_zh"] += 1
            if len(samples["desc_zh_equals_steps_zh"]) < 5:
                samples["desc_zh_equals_steps_zh"].append({
                    "id": ex_id,
                    "name_zh": name_zh,
                    "desc_zh": desc_zh[:100],
                    "steps_zh": steps_zh_text[:100]
                })
    
    # 收集正常样本
    if (steps_zh and len(steps_zh) > 0 and 
        steps_en and len(steps_en) > 0 and
        len(samples["normal"]) < 5):
        samples["normal"].append({
            "id": ex_id,
            "name_zh": name_zh,
            "desc_zh": desc_zh[:100],
            "desc_en": desc_en[:100]
        })

# 输出统计结果
print("\n" + "=" * 80)
print("统计结果")
print("=" * 80)

print(f"\n总动作数: {stats['total']}")
print(f"\n数据质量问题：")
print(f"  1. description_en 和 correct_steps_en 内容相同: {stats['desc_en_equals_steps_en']} ({stats['desc_en_equals_steps_en']/stats['total']*100:.1f}%)")
print(f"  2. description_zh 和 correct_steps_zh 内容相同: {stats['desc_zh_equals_steps_zh']} ({stats['desc_zh_equals_steps_zh']/stats['total']*100:.1f}%)")
print(f"  3. correct_steps_zh 为空: {stats['steps_zh_empty']} ({stats['steps_zh_empty']/stats['total']*100:.1f}%)")
print(f"  4. correct_steps_en 为空: {stats['steps_en_empty']} ({stats['steps_en_empty']/stats['total']*100:.1f}%)")
print(f"  5. 两者都为空: {stats['both_steps_empty']} ({stats['both_steps_empty']/stats['total']*100:.1f}%)")

print(f"\n数据增强：")
print(f"  有 description_zh_professional: {stats['has_professional_desc']} ({stats['has_professional_desc']/stats['total']*100:.1f}%)")

# 保存详细报告
report = {
    "statistics": stats,
    "samples": samples
}

report_file = 'data_quality_report.json'
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n详细报告已保存到: {report_file}")

# 输出样本
print("\n" + "=" * 80)
print("样本数据（供人工审查）")
print("=" * 80)

print("\n【样本1】description_en = correct_steps_en (前5个)")
print("-" * 80)
for i, sample in enumerate(samples["desc_en_equals_steps_en"][:5], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   description_en: {sample['desc_en']}...")
    print(f"   correct_steps_en: {sample['steps_en']}...")

print("\n【样本2】correct_steps_zh 为空 (前5个)")
print("-" * 80)
for i, sample in enumerate(samples["steps_zh_empty"][:5], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   description_zh: {sample['desc_zh']}...")
    print(f"   correct_steps_zh: {sample['steps_zh']}")
    print(f"   description_zh_professional: {sample['desc_zh_prof']}...")

print("\n【样本3】description_zh = correct_steps_zh (前5个)")
print("-" * 80)
if samples["desc_zh_equals_steps_zh"]:
    for i, sample in enumerate(samples["desc_zh_equals_steps_zh"][:5], 1):
        print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
        print(f"   description_zh: {sample['desc_zh']}...")
        print(f"   correct_steps_zh: {sample['steps_zh']}...")
else:
    print("   没有发现此类问题")

print("\n【样本4】正常数据 (前5个)")
print("-" * 80)
for i, sample in enumerate(samples["normal"][:5], 1):
    print(f"\n{i}. ID={sample['id']}, 名称={sample['name_zh']}")
    print(f"   description_zh: {sample['desc_zh']}...")
    print(f"   description_en: {sample['desc_en']}...")

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
