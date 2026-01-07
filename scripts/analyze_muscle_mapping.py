#!/usr/bin/env python3
"""分析Neo4j Muscle节点与Exercise中肌肉的匹配情况"""
import json
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://fitness_neo4j:7687', auth=('neo4j', 'build_body_2024'))

# 1. 获取Neo4j中的Muscle节点
print("=== Neo4j Muscle节点 (53个) ===")
with driver.session() as session:
    result = session.run("MATCH (m:Muscle) RETURN m.name_zh as name_zh, m.name_en as name_en ORDER BY m.name_zh")
    neo4j_muscles = [(r["name_zh"], r["name_en"]) for r in result]
    neo4j_muscle_names_zh = set(m[0] for m in neo4j_muscles if m[0])
    neo4j_muscle_names_en = set(m[1] for m in neo4j_muscles if m[1])

print(f"Neo4j肌肉(中文): {len(neo4j_muscle_names_zh)}个")
print(sorted(neo4j_muscle_names_zh)[:20], "...")

# 2. 获取Exercise中的所有肌肉
print("\n=== Exercise中的肌肉 ===")
with open('/app/data/enhanced_perfect_exercises_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
exercises = data['enhanced_perfect_exercises']

# 从 all_muscles_zh 收集
exercise_muscles_zh = set()
for e in exercises:
    muscles = e.get('all_muscles_zh', [])
    if muscles:
        exercise_muscles_zh.update(muscles)

# 从 muscles_tree 收集
muscles_tree_zh = set()
muscles_tree_en = set()
for e in exercises:
    tree = e.get('muscles_tree', [])
    if tree:
        for m in tree:
            if m.get('name_zh'):
                muscles_tree_zh.add(m['name_zh'])
            if m.get('name'):
                muscles_tree_en.add(m['name'])

print(f"Exercise all_muscles_zh: {len(exercise_muscles_zh)}个")
print(f"Exercise muscles_tree(中文): {len(muscles_tree_zh)}个")
print(f"Exercise muscles_tree(英文): {len(muscles_tree_en)}个")

# 3. 匹配分析
print("\n=== 匹配分析 ===")
matched_zh = exercise_muscles_zh & neo4j_muscle_names_zh
unmatched_in_exercise = exercise_muscles_zh - neo4j_muscle_names_zh
unmatched_in_neo4j = neo4j_muscle_names_zh - exercise_muscles_zh

print(f"匹配的肌肉: {len(matched_zh)}个")
print(f"Exercise中有但Neo4j没有: {len(unmatched_in_exercise)}个")
print(f"Neo4j中有但Exercise没有: {len(unmatched_in_neo4j)}个")

print("\n--- Exercise中有但Neo4j没有的肌肉 ---")
for m in sorted(unmatched_in_exercise):
    print(f"  - {m}")

print("\n--- Neo4j中有但Exercise没有的肌肉 ---")
for m in sorted(unmatched_in_neo4j):
    print(f"  - {m}")

# 4. muscles_tree 层级分析
print("\n=== muscles_tree 层级分析 ===")
level_0 = set()  # 主肌群
level_1 = set()  # 子肌群
for e in exercises:
    tree = e.get('muscles_tree') or []
    for m in tree:
        if m and m.get('level') == 0:
            level_0.add(m.get('name_zh'))
        elif m and m.get('level') == 1:
            level_1.add(m.get('name_zh'))

print(f"Level 0 (主肌群): {len(level_0)}个")
print(sorted(level_0))
print(f"\nLevel 1 (子肌群): {len(level_1)}个")
print(sorted(level_1))

driver.close()
