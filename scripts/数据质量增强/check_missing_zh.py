#!/usr/bin/env python3
"""
检查缺少中文步骤的动作
"""

import json
import sys
import os
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("检查缺少中文步骤的动作")
print("=" * 80)

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 查询缺少中文步骤的动作
query = """
MATCH (e:Exercise)
WHERE e.correct_steps_en IS NOT NULL
  AND (e.correct_steps_zh IS NULL OR size(e.correct_steps_zh) = 0)
RETURN e.id as id,
       e.name_zh as name_zh,
       e.correct_steps_en as steps_en
ORDER BY e.id
"""

with driver.session() as session:
    result = session.run(query)
    exercises = [record.data() for record in result]

driver.close()

print(f"\n找到 {len(exercises)} 个缺少中文步骤的动作\n")

for i, ex in enumerate(exercises, 1):
    print(f"{'='*80}")
    print(f"动作 {i}: ID={ex['id']}, {ex['name_zh']}")
    print(f"{'='*80}")
    
    steps_en = ex['steps_en']
    
    print(f"\n英文步骤数: {len(steps_en)}")
    
    print(f"\n【英文步骤】")
    for j, step in enumerate(steps_en, 1):
        if isinstance(step, dict):
            text = step.get('text', '')
        else:
            text = step
        print(f"  {j}. {text}")
    
    print()

print("=" * 80)
print("检查完成")
print("=" * 80)
