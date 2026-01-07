#!/usr/bin/env python3
"""
检查已翻译动作的质量
"""

import json
import sys
import os
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("检查翻译质量")
print("=" * 80)

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 查询最近翻译的5个动作
query = """
MATCH (e:Exercise)
WHERE e.correct_steps_zh IS NOT NULL 
  AND size(e.correct_steps_zh) > 0
  AND e.id IN [44, 48, 212, 1319, 1635]
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

print(f"\n找到 {len(exercises)} 个已翻译的动作\n")

for i, ex in enumerate(exercises, 1):
    print(f"{'='*80}")
    print(f"动作 {i}: ID={ex['id']}, {ex['name_zh']}")
    print(f"{'='*80}")
    
    steps_en = ex['steps_en']
    steps_zh = ex['steps_zh']
    
    print(f"\n英文步骤数: {len(steps_en)}")
    print(f"中文步骤数: {len(steps_zh)}")
    
    print(f"\n【英文步骤】")
    for j, step in enumerate(steps_en, 1):
        if isinstance(step, dict):
            text = step.get('text', '')
        else:
            text = step
        print(f"  {j}. {text}")
    
    print(f"\n【中文步骤】")
    for j, step in enumerate(steps_zh, 1):
        print(f"  {j}. {step}")
    
    print()

print("=" * 80)
print("检查完成")
print("=" * 80)
