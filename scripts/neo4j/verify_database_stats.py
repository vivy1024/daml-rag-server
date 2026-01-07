#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo4j数据库统计验证脚本

功能：
1. 查询所有节点类型及数量
2. 查询所有关系类型及数量
3. 检查Food节点的标签情况
4. 检查孤立节点
5. 核心节点类型详细统计
6. 核心关系类型详细统计
"""

import os
from neo4j import GraphDatabase

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("📊 Neo4j数据库统计数据验证")
print("=" * 80)

with driver.session() as session:
    # 1. 查询所有节点类型及数量
    print("\n1️⃣ 节点类型统计")
    print("-" * 80)
    result = session.run("""
        MATCH (n)
        RETURN labels(n) as labels, count(*) as count
        ORDER BY count DESC
    """)
    
    total_nodes = 0
    node_stats = []
    for record in result:
        labels = record["labels"]
        count = record["count"]
        total_nodes += count
        node_stats.append((labels, count))
        print(f"   {', '.join(labels):30s} : {count:>6,} 个节点")
    
    print(f"\n   {'总计':30s} : {total_nodes:>6,} 个节点")
    
    # 2. 查询所有关系类型及数量
    print("\n2️⃣ 关系类型统计")
    print("-" * 80)
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(*) as count
        ORDER BY count DESC
    """)
    
    total_relationships = 0
    rel_stats = []
    for record in result:
        rel_type = record["type"]
        count = record["count"]
        total_relationships += count
        rel_stats.append((rel_type, count))
        print(f"   {rel_type:30s} : {count:>6,} 个关系")
    
    print(f"\n   {'总计':30s} : {total_relationships:>6,} 个关系")
    
    # 3. 检查Food节点的标签情况
    print("\n3️⃣ Food节点标签检查")
    print("-" * 80)
    result = session.run("MATCH (f:Food) RETURN count(f) as count")
    food_count = result.single()["count"]
    print(f"   Food节点数量: {food_count:,}")
    
    result = session.run("MATCH (cf:ChineseFood) RETURN count(cf) as count")
    cf_count = result.single()["count"]
    print(f"   ChineseFood节点数量: {cf_count:,}")
    
    result = session.run("MATCH (n:Food:ChineseFood) RETURN count(n) as count")
    both_count = result.single()["count"]
    print(f"   同时拥有两个标签的节点: {both_count:,}")
    
    if cf_count == 0:
        print("   ✅ ChineseFood标签已完全移除")
    elif both_count == food_count:
        print("   ⚠️ 所有Food节点都有ChineseFood标签（冗余）")
    
    # 4. 检查孤立节点
    print("\n4️⃣ 孤立节点检查")
    print("-" * 80)
    result = session.run("""
        MATCH (n)
        WHERE NOT (n)--()
        RETURN labels(n) as labels, count(*) as count
        ORDER BY count DESC
    """)
    
    isolated_nodes = []
    total_isolated = 0
    for record in result:
        labels = record["labels"]
        count = record["count"]
        total_isolated += count
        isolated_nodes.append((labels, count))
        print(f"   {', '.join(labels):30s} : {count:>6,} 个孤立节点")
    
    if total_isolated == 0:
        print("   ✅ 没有孤立节点")
    else:
        print(f"\n   {'总计':30s} : {total_isolated:>6,} 个孤立节点")
    
    # 5. 核心节点类型详细统计
    print("\n5️⃣ 核心节点类型详细统计")
    print("-" * 80)
    
    core_node_types = [
        ("Exercise", "动作"),
        ("Muscle", "肌肉"),
        ("Food", "食物"),
        ("Nutrient", "营养素"),
        ("Equipment", "器械"),
        ("BodyPart", "身体部位"),
        ("MuscleGroup", "肌群"),
        ("ExerciseCategory", "动作分类"),
        ("ExerciseType", "动作类型"),
        ("Difficulty", "难度"),
        ("Force", "发力类型"),
        ("Mechanic", "力学类型"),
    ]
    
    for node_type, chinese_name in core_node_types:
        result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
        count = result.single()["count"]
        print(f"   {chinese_name}({node_type}):".ljust(35) + f"{count:>6,} 个")
    
    # 6. 核心关系类型详细统计
    print("\n6️⃣ 核心关系类型详细统计")
    print("-" * 80)
    
    core_rel_types = [
        ("TARGETS", "目标肌肉"),
        ("SYNERGISTS", "协同肌肉"),
        ("STABILIZERS", "稳定肌肉"),
        ("DYNAMIC_STABILIZERS", "动态稳定肌肉"),
        ("ANTAGONIST_STABILIZERS", "拮抗稳定肌肉"),
        ("USES_EQUIPMENT", "使用器械"),
        ("BELONGS_TO_CATEGORY", "属于分类"),
        ("HAS_TYPE", "动作类型"),
        ("HAS_DIFFICULTY", "难度等级"),
        ("HAS_FORCE", "发力类型"),
        ("HAS_MECHANIC", "力学类型"),
        ("CONTAINS_NUTRIENT", "包含营养素"),
        ("PART_OF", "部位关系"),
        ("BELONGS_TO_GROUP", "属于肌群"),
    ]
    
    for rel_type, chinese_name in core_rel_types:
        result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
        count = result.single()["count"]
        print(f"   {chinese_name}({rel_type}):".ljust(45) + f"{count:>6,} 个")
    
    # 7. 数据完整性检查
    print("\n7️⃣ 数据完整性检查")
    print("-" * 80)
    
    # 检查Exercise节点的必要关系
    result = session.run("""
        MATCH (e:Exercise)
        WHERE NOT (e)-[:TARGETS]->()
        RETURN count(e) as count
    """)
    no_target = result.single()["count"]
    print(f"   没有目标肌肉的动作: {no_target:,} 个")
    
    result = session.run("""
        MATCH (e:Exercise)
        WHERE NOT (e)-[:USES_EQUIPMENT]->()
        RETURN count(e) as count
    """)
    no_equipment = result.single()["count"]
    print(f"   没有器械的动作: {no_equipment:,} 个")
    
    result = session.run("""
        MATCH (e:Exercise)
        WHERE NOT (e)-[:HAS_DIFFICULTY]->()
        RETURN count(e) as count
    """)
    no_difficulty = result.single()["count"]
    print(f"   没有难度的动作: {no_difficulty:,} 个")
    
    # 检查Food节点的营养素关系
    result = session.run("""
        MATCH (f:Food)
        WHERE NOT (f)-[:CONTAINS_NUTRIENT]->()
        RETURN count(f) as count
    """)
    no_nutrient = result.single()["count"]
    print(f"   没有营养素的食物: {no_nutrient:,} 个")
    
    # 8. 总结
    print("\n" + "=" * 80)
    print("📋 统计总结")
    print("=" * 80)
    print(f"   总节点数: {total_nodes:,}")
    print(f"   总关系数: {total_relationships:,}")
    print(f"   节点类型数: {len(node_stats)}")
    print(f"   关系类型数: {len(rel_stats)}")
    print(f"   孤立节点数: {total_isolated:,}")
    print("=" * 80)

driver.close()
