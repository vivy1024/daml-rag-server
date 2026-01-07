#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移除冗余的ChineseFood标签

背景：
- 当前1,880个食物节点同时拥有Food和ChineseFood两个标签
- 两个标签的字段完全相同，关系完全相同
- 保留Food标签，移除ChineseFood标签以简化数据结构

操作：
1. 验证所有ChineseFood节点都有Food标签
2. 移除ChineseFood标签
3. 验证关系完整性
"""

import os
from neo4j import GraphDatabase

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 60)
print("🔧 移除冗余的ChineseFood标签")
print("=" * 60)

with driver.session() as session:
    # 1. 验证当前状态
    print("\n1️⃣ 验证当前状态")
    result = session.run("MATCH (f:Food) RETURN count(f) as count")
    food_count = result.single()["count"]
    print(f"   Food节点数量: {food_count}")
    
    result = session.run("MATCH (cf:ChineseFood) RETURN count(cf) as count")
    cf_count = result.single()["count"]
    print(f"   ChineseFood节点数量: {cf_count}")
    
    result = session.run("MATCH (n:Food:ChineseFood) RETURN count(n) as count")
    both_count = result.single()["count"]
    print(f"   同时拥有两个标签的节点: {both_count}")
    
    if both_count != food_count or both_count != cf_count:
        print("\n⚠️ 警告：Food和ChineseFood标签不完全重叠")
        print("   请手动检查数据后再执行清理")
        driver.close()
        exit(1)
    
    # 2. 检查关系
    print("\n2️⃣ 检查关系完整性")
    result = session.run("""
        MATCH (f:Food)-[r:CONTAINS_NUTRIENT]->()
        RETURN count(r) as count
    """)
    food_rel_count = result.single()["count"]
    print(f"   Food的CONTAINS_NUTRIENT关系: {food_rel_count}个")
    
    result = session.run("""
        MATCH (cf:ChineseFood)-[r:CONTAINS_NUTRIENT]->()
        RETURN count(r) as count
    """)
    cf_rel_count = result.single()["count"]
    print(f"   ChineseFood的CONTAINS_NUTRIENT关系: {cf_rel_count}个")
    
    if food_rel_count != cf_rel_count:
        print("\n⚠️ 警告：关系数量不一致")
        print("   请手动检查数据后再执行清理")
        driver.close()
        exit(1)
    
    # 3. 移除ChineseFood标签
    print("\n3️⃣ 移除ChineseFood标签")
    print("   执行中...")
    
    result = session.run("""
        MATCH (n:ChineseFood)
        REMOVE n:ChineseFood
        RETURN count(n) as count
    """)
    removed_count = result.single()["count"]
    print(f"   ✅ 已移除 {removed_count} 个节点的ChineseFood标签")
    
    # 4. 验证清理结果
    print("\n4️⃣ 验证清理结果")
    result = session.run("MATCH (f:Food) RETURN count(f) as count")
    food_count_after = result.single()["count"]
    print(f"   Food节点数量: {food_count_after}")
    
    result = session.run("MATCH (cf:ChineseFood) RETURN count(cf) as count")
    cf_count_after = result.single()["count"]
    print(f"   ChineseFood节点数量: {cf_count_after}")
    
    result = session.run("""
        MATCH (f:Food)-[r:CONTAINS_NUTRIENT]->()
        RETURN count(r) as count
    """)
    food_rel_count_after = result.single()["count"]
    print(f"   Food的CONTAINS_NUTRIENT关系: {food_rel_count_after}个")
    
    # 5. 验证结果
    if food_count_after == food_count and cf_count_after == 0 and food_rel_count_after == food_rel_count:
        print("\n✅ 清理成功！")
        print(f"   - 保留了 {food_count_after} 个Food节点")
        print(f"   - 移除了所有ChineseFood标签")
        print(f"   - 关系完整性保持不变（{food_rel_count_after}个关系）")
    else:
        print("\n⚠️ 清理结果异常，请检查：")
        print(f"   - Food节点: {food_count} → {food_count_after}")
        print(f"   - ChineseFood节点: {cf_count} → {cf_count_after}")
        print(f"   - 关系数量: {food_rel_count} → {food_rel_count_after}")

driver.close()

print("\n" + "=" * 60)
print("🎉 清理完成")
print("=" * 60)
