#!/usr/bin/env python3
"""
从 Neo4j 同步数据到 JSON 文件

将 Neo4j 中清理后的数据导出到 enhanced_perfect_exercises_dataset.json
"""

import json
import sys
import os
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("从 Neo4j 同步数据到 JSON 文件")
print("=" * 80)

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

print(f"\n连接 Neo4j: {NEO4J_URI}")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("✅ Neo4j 连接成功")
except Exception as e:
    print(f"❌ Neo4j 连接失败: {e}")
    sys.exit(1)

def convert_neo4j_types(obj):
    """转换 Neo4j 特殊类型为 JSON 可序列化类型"""
    from neo4j.time import DateTime
    
    if isinstance(obj, DateTime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_neo4j_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_neo4j_types(item) for item in obj]
    else:
        return obj

def get_all_exercises(session):
    """获取所有 Exercise 节点"""
    query = """
    MATCH (e:Exercise)
    RETURN e
    ORDER BY e.id
    """
    result = session.run(query)
    exercises = []
    for record in result:
        node = record['e']
        # 转换为字典并处理特殊类型
        exercise = convert_neo4j_types(dict(node))
        exercises.append(exercise)
    return exercises

# 读取原始JSON文件
json_file = 'data/enhanced_perfect_exercises_dataset.json'
print(f"\n读取原始 JSON 文件: {json_file}")

try:
    with open(json_file, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    print(f"✅ 原始文件读取成功")
except Exception as e:
    print(f"⚠️ 读取失败: {e}")
    print("  将跳过备份，直接从 Neo4j 重建文件")
    original_data = None

# 从 Neo4j 获取最新数据
print("\n从 Neo4j 获取最新数据...")

with driver.session() as session:
    exercises = get_all_exercises(session)

driver.close()

print(f"✅ 获取了 {len(exercises)} 个动作")

# 备份原始文件
if original_data:
    backup_file = 'data/enhanced_perfect_exercises_dataset.json.backup'
    print(f"\n备份原始文件到: {backup_file}")
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(original_data, f, indent=2, ensure_ascii=False)
        print("✅ 备份成功")
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        sys.exit(1)
else:
    print("\n⏭️ 跳过备份（原始文件无法读取）")

# 构建新的数据结构
new_data = {
    "enhanced_perfect_exercises": exercises
}

# 写入新文件
print(f"\n写入更新后的数据到: {json_file}")

try:
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print("✅ 写入成功")
except Exception as e:
    print(f"❌ 写入失败: {e}")
    sys.exit(1)

# 统计变化
print("\n\n" + "=" * 80)
print("同步完成")
print("=" * 80)

print(f"\n总动作数: {len(exercises)}")

# 统计字段状态
stats = {
    "has_correct_steps_zh": 0,
    "has_description_zh": 0,
    "has_description_en": 0,
    "has_description_zh_professional": 0,
}

for ex in exercises:
    if ex.get('correct_steps_zh') and len(ex.get('correct_steps_zh', [])) > 0:
        stats["has_correct_steps_zh"] += 1
    if ex.get('description_zh'):
        stats["has_description_zh"] += 1
    if ex.get('description_en'):
        stats["has_description_en"] += 1
    if ex.get('description_zh_professional'):
        stats["has_description_zh_professional"] += 1

print(f"\n字段统计：")
print(f"  correct_steps_zh: {stats['has_correct_steps_zh']} ({stats['has_correct_steps_zh']/len(exercises)*100:.1f}%)")
print(f"  description_zh: {stats['has_description_zh']} ({stats['has_description_zh']/len(exercises)*100:.1f}%)")
print(f"  description_en: {stats['has_description_en']} ({stats['has_description_en']/len(exercises)*100:.1f}%)")
print(f"  description_zh_professional: {stats['has_description_zh_professional']} ({stats['has_description_zh_professional']/len(exercises)*100:.1f}%)")

print(f"\n✅ JSON 文件已更新！")
if original_data:
    print(f"✅ 原始文件已备份到: data/enhanced_perfect_exercises_dataset.json.backup")

print("\n" + "=" * 80)
