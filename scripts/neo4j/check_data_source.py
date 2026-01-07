# -*- coding: utf-8 -*-
"""检查数据源中的force和mechanic属性"""

import json
import os

# 检查enhanced_perfect_exercises数据
data_paths = [
    '/app/data/enhanced_perfect_exercises_dataset.json',
    '/app/perfect_enhanced_dataset/data/enhanced_perfect_exercises_dataset.json',
]

data = None
for data_path in data_paths:
    if os.path.exists(data_path):
        print(f"找到数据文件: {data_path}")
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        break

if data is None:
    # 尝试查找其他可能的数据文件
    print("未找到数据文件，尝试搜索...")
    import subprocess
    result = subprocess.run(['find', '/app', '-name', '*.json', '-type', 'f'], 
                          capture_output=True, text=True)
    print("找到的JSON文件:")
    for line in result.stdout.split('\n')[:20]:
        if line:
            print(f"  {line}")
    exit(1)

print(f"数据类型: {type(data)}")

# 处理不同的数据格式
if isinstance(data, dict):
    # 如果是字典，检查结构
    print(f"字典键: {list(data.keys())[:10]}")
    if 'enhanced_perfect_exercises' in data:
        data = data['enhanced_perfect_exercises']
    elif 'exercises' in data:
        data = data['exercises']
    elif 'data' in data:
        data = data['data']

print(f"数据集大小: {len(data)}")

# 检查第一个样本的属性
if data:
    sample = data[0] if isinstance(data, list) else list(data.values())[0]
    print("\n样本属性:")
    for key in sorted(sample.keys()):
        value = sample[key]
        if isinstance(value, str) and len(value) > 50:
            value = value[:50] + '...'
        elif isinstance(value, list) and len(value) > 3:
            value = str(value[:3]) + '...'
        print(f"  {key}: {value}")
    
    # 检查force_en属性分布
    print("\n\nforce_en属性分布:")
    force_dist = {}
    for item in data:
        force = item.get('force_en', '') or ''
        force_dist[force] = force_dist.get(force, 0) + 1
    for k, v in sorted(force_dist.items(), key=lambda x: -x[1]):
        print(f'  "{k}": {v}')
    
    # 检查mechanic_en属性分布
    print("\nmechanic_en属性分布:")
    mechanic_dist = {}
    for item in data:
        mechanic = item.get('mechanic_en', '') or ''
        mechanic_dist[mechanic] = mechanic_dist.get(mechanic, 0) + 1
    for k, v in sorted(mechanic_dist.items(), key=lambda x: -x[1]):
        print(f'  "{k}": {v}')
    
    # 检查kinetic_chain_type属性分布
    print("\nkinetic_chain_type属性分布:")
    kc_dist = {}
    for item in data:
        kc = item.get('kinetic_chain_type', '') or ''
        kc_dist[kc] = kc_dist.get(kc, 0) + 1
    for k, v in sorted(kc_dist.items(), key=lambda x: -x[1]):
        print(f'  "{k}": {v}')
    
    # 检查grips_en属性分布
    print("\ngrips_en属性分布:")
    grips_dist = {}
    for item in data:
        grips = item.get('grips_en', []) or []
        if isinstance(grips, list):
            for grip in grips:
                grips_dist[grip] = grips_dist.get(grip, 0) + 1
        else:
            grips_dist[grips] = grips_dist.get(grips, 0) + 1
    for k, v in sorted(grips_dist.items(), key=lambda x: -x[1])[:10]:
        print(f'  "{k}": {v}')
    
    # 检查difficulty_en属性分布
    print("\ndifficulty_en属性分布:")
    diff_dist = {}
    for item in data:
        diff = item.get('difficulty_en', '') or ''
        diff_dist[diff] = diff_dist.get(diff, 0) + 1
    for k, v in sorted(diff_dist.items(), key=lambda x: -x[1]):
        print(f'  "{k}": {v}')
