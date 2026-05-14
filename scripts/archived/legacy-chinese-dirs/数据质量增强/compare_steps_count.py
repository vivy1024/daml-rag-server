#!/usr/bin/env python3
"""
对比英文和中文步骤数量

检查翻译是否完整
"""

import json
import sys
import os
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("对比英文和中文步骤数量")
print("=" * 80)

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 查询所有动作
query = """
MATCH (e:Exercise)
WHERE e.correct_steps_en IS NOT NULL
RETURN e.id as id,
       e.name_zh as name_zh,
       e.correct_steps_en as steps_en,
       e.correct_steps_zh as steps_zh
ORDER BY e.id
"""

with driver.session() as session:
    result = session.run(query)
    exercises = [record.data() for record in result]

driver.close()

# 统计
stats = {
    "total": len(exercises),
    "steps_match": 0,  # 步骤数量一致
    "steps_mismatch": 0,  # 步骤数量不一致
    "zh_missing": 0,  # 缺少中文步骤
    "zh_more": 0,  # 中文步骤更多
    "zh_less": 0,  # 中文步骤更少
}

mismatches = []

for ex in exercises:
    steps_en = ex['steps_en'] or []
    steps_zh = ex['steps_zh'] or []
    
    en_count = len(steps_en)
    zh_count = len(steps_zh)
    
    if zh_count == 0:
        stats["zh_missing"] += 1
    elif en_count == zh_count:
        stats["steps_match"] += 1
    else:
        stats["steps_mismatch"] += 1
        if zh_count > en_count:
            stats["zh_more"] += 1
        else:
            stats["zh_less"] += 1
        
        # 记录不匹配的动作
        if len(mismatches) < 20:
            mismatches.append({
                "id": ex['id'],
                "name_zh": ex['name_zh'],
                "en_count": en_count,
                "zh_count": zh_count,
                "steps_en": steps_en,
                "steps_zh": steps_zh
            })

print(f"\n总动作数: {stats['total']}")
print(f"\n步骤数量统计：")
print(f"  步骤数量一致: {stats['steps_match']} ({stats['steps_match']/stats['total']*100:.1f}%)")
print(f"  步骤数量不一致: {stats['steps_mismatch']} ({stats['steps_mismatch']/stats['total']*100:.1f}%)")
print(f"    - 中文步骤更多: {stats['zh_more']}")
print(f"    - 中文步骤更少: {stats['zh_less']}")
print(f"  缺少中文步骤: {stats['zh_missing']} ({stats['zh_missing']/stats['total']*100:.1f}%)")

print(f"\n\n前20个步骤数量不一致的动作：")
print("=" * 80)

for i, ex in enumerate(mismatches, 1):
    print(f"\n{i}. ID={ex['id']}, {ex['name_zh']}")
    print(f"   英文步骤: {ex['en_count']} 个")
    print(f"   中文步骤: {ex['zh_count']} 个")
    
    print(f"\n   【英文步骤】")
    for j, step in enumerate(ex['steps_en'], 1):
        if isinstance(step, dict):
            text = step.get('text', '')
        else:
            text = step
        print(f"     {j}. {text[:80]}...")
    
    print(f"\n   【中文步骤】")
    for j, step in enumerate(ex['steps_zh'], 1):
        print(f"     {j}. {step[:80]}...")

print("\n" + "=" * 80)
print("对比完成")
print("=" * 80)
