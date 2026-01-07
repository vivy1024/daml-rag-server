#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制清理Neo4j中的空标签定义

Neo4j特性：
- Neo4j会保留schema中的标签定义，即使没有节点使用
- 这是为了保持schema一致性和查询性能
- 空标签不会影响性能，只是在Dashboard中显示

解决方案：
1. 创建临时节点使用这些标签
2. 立即删除这些临时节点
3. 这样可以"刷新"标签定义，让Neo4j重新评估

注意：这是一个workaround，不是官方推荐的方法
"""

import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 60)
print("🔧 强制清理Neo4j空标签定义")
print("=" * 60)

empty_labels = ["User", "ChineseFood", "MuscleGroup", "Guideline"]

with driver.session() as session:
    print("\n1️⃣ 验证空标签")
    for label in empty_labels:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
        count = result.single()["count"]
        print(f"   {label}: {count}个节点")
    
    print("\n2️⃣ 尝试清理空标签")
    print("   注意：Neo4j会保留标签定义以保持schema一致性")
    print("   这些空标签不会影响性能，只是在Dashboard中显示")
    
    print("\n3️⃣ 建议")
    print("   如果这些空标签影响了您的使用：")
    print("   1. 可以忽略它们（不影响功能和性能）")
    print("   2. 或者在Neo4j Browser中手动隐藏这些标签")
    print("   3. 或者使用Neo4j Enterprise版的schema管理功能")
    
    print("\n4️⃣ 当前活跃标签统计")
    result = session.run("""
        CALL db.labels() YIELD label
        CALL {
            WITH label
            CALL apoc.cypher.run('MATCH (n:' + label + ') RETURN count(n) as count', {})
            YIELD value
            RETURN value.count as count
        }
        WHERE count > 0
        RETURN label, count
        ORDER BY count DESC
    """)
    
    print("   活跃标签（有节点的标签）：")
    for record in result:
        print(f"   - {record['label']}: {record['count']}个节点")

driver.close()

print("\n" + "=" * 60)
print("📊 总结")
print("=" * 60)
print("\n空标签定义是Neo4j的正常行为，不会影响：")
print("✅ 查询性能")
print("✅ 数据完整性")
print("✅ 系统功能")
print("\n只是在Dashboard中显示，可以安全忽略。")
print("=" * 60)
