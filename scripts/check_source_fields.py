#!/usr/bin/env python3
"""检查源文件中的字段情况"""

import json
from pathlib import Path

source_dir = Path('/app/yuzhen-backend/storage/app/public/exercises_v2')
sample_ids = [1, 2, 3, 4, 5, 100, 200, 500, 1000]

for ex_id in sample_ids:
    # 计算路径
    range_start = (ex_id // 100) * 100
    range_end = range_start + 99
    sub_start = (ex_id // 10) * 10
    sub_end = sub_start + 9
    path = source_dir / f'{range_start:04d}-{range_end:04d}' / f'{sub_start:04d}-{sub_end:04d}' / str(ex_id) / 'data.json'
    
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        force = data.get('force_zh', 'N/A')
        mechanic = data.get('mechanic_zh', 'N/A')
        desc = data.get('description_zh', '')
        desc_preview = desc[:30] if desc else 'None'
        print(f'ID {ex_id}: force_zh={force}, mechanic_zh={mechanic}, desc={desc_preview}')
    else:
        print(f'ID {ex_id}: 文件不存在 {path}')
