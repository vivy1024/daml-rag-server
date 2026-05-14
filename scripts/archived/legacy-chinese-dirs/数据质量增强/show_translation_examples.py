#!/usr/bin/env python3
"""
展示翻译效果示例
"""

import json
import sys
import os
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("翻译效果展示")
print("=" * 80)

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 选择几个代表性的动作
example_ids = [8, 39, 27, 45, 190, 303]

query = """
MATCH (e:Exercise)
WHERE e.id IN $ids
RETURN e.id as id,
       e.name_zh as name_zh,
       e.correct_steps_en as steps_en,
       e.correct_steps_zh as steps_zh
ORDER BY e.id
"""

with driver.session() as session:
    result = session.run(query, ids=example_ids)
    exercises = [record.data() for record in result]

driver.close()

for i, ex in enumerate(exercises, 1):
    print(f"\n{'='*80}")
    print(f"示例 {i}: {ex['name_zh']} (ID={ex['id']})")
    print(f"{'='*80}")
    
    steps_en = ex['steps_en']
    steps_zh = ex['steps_zh']
    
    print(f"\n步骤数量: 英文 {len(steps_en)} 个, 中文 {len(steps_zh)} 个")
    
    max_steps = max(len(steps_en), len(steps_zh))
    
    for j in range(max_steps):
        print(f"\n步骤 {j+1}:")
        
        if j < len(steps_en):
            if isinstance(steps_en[j], dict):
                en_text = steps_en[j].get('text', '')
            else:
                en_text = steps_en[j]
            print(f"  🇬🇧 {en_text}")
        else:
            print(f"  🇬🇧 (无)")
        
        if j < len(steps_zh):
            print(f"  🇨🇳 {steps_zh[j]}")
        else:
            print(f"  🇨🇳 (无)")

print(f"\n{'='*80}")
print("展示完成")
print(f"{'='*80}")
