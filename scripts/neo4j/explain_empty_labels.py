#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解释Neo4j中的空标签现象

为什么空标签无法删除：
1. Neo4j Community版不支持删除标签定义
2. 标签定义是schema的一部分，会被持久化
3. 即使没有节点使用，标签定义仍会保留
4. 这是Neo4j的设计特性，不是bug

影响：
- ✅ 不影响查询性能
- ✅ 不影响数据完整性
- ✅ 不影响系统功能
- ⚠️ 只是在Dashboard中显示

解决方案：
1. 忽略它们（推荐）
2. 在Neo4j Browser中过滤显示
3. 使用Neo4j Enterprise版的schema管理
"""

import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 60)
print("📊 Neo4j标签统计报告")
print("=" * 60)

with driver.session() as session:
    # 获取所有标签
    result = session.run("CALL db.labels()")
    all_labels = [record["label"] for record in result]
    
    # 统计每个标签的节点数
    active_labels = []
    empty_labels = []
    
    for label in all_labels:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
        count = result.single()["count"]
        if count > 0:
            active_labels.append((label, count))
        else:
            empty_labels.append(label)
    
    # 显示活跃标签
    print(f"\n✅ 活跃标签（{len(active_labels)}个）：")
    active_labels.sort(key=lambda x: x[1], reverse=True)
    for label, count in active_labels:
        print(f"   {label:25s} {count:6d} 个节点")
    
    # 显示空标签
    print(f"\n⚠️ 空标签（{len(empty_labels)}个）：")
    for label in empty_labels:
        print(f"   {label:25s} 0 个节点")
    
    print("\n" + "=" * 60)
    print("📋 关于空标签的说明")
    print("=" * 60)
    print("\n这些空标签是历史遗留的标签定义：")
    for label in empty_labels:
        if label == "ChineseFood":
            print(f"   • {label}: 已合并到Food标签（v8.44.0）")
        elif label == "MuscleGroup":
            print(f"   • {label}: 已废弃，使用Muscle标签")
        elif label == "Guideline":
            print(f"   • {label}: 已废弃，未使用")
        elif label == "User":
            print(f"   • {label}: 已废弃，用户数据在MySQL中")
    
    print("\n为什么无法删除：")
    print("   Neo4j Community版不支持删除标签定义")
    print("   标签定义是schema的一部分，会被持久化")
    print("   这是Neo4j的设计特性，不是bug")
    
    print("\n影响评估：")
    print("   ✅ 不影响查询性能")
    print("   ✅ 不影响数据完整性")
    print("   ✅ 不影响系统功能")
    print("   ⚠️ 只在Dashboard中显示")
    
    print("\n建议：")
    print("   可以安全忽略这些空标签")
    print("   它们不会对系统造成任何负面影响")

driver.close()

print("\n" + "=" * 60)
print("🎉 报告完成")
print("=" * 60)
