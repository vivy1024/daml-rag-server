#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理Neo4j中的空标签定义

问题：
- 虽然移除了节点的ChineseFood标签，但Neo4j schema中仍保留标签定义
- Dashboard界面仍显示ChineseFood、MuscleGroup、Guideline、User等空标签

解决方案：
- Neo4j不支持直接删除标签定义
- 需要通过APOC插件的schema清理功能
- 或者重启Neo4j让其自动清理未使用的标签
"""

import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 60)
print("🧹 清理Neo4j空标签定义")
print("=" * 60)

with driver.session() as session:
    # 1. 检查当前所有标签
    print("\n1️⃣ 检查当前所有标签")
    result = session.run("CALL db.labels()")
    all_labels = [record["label"] for record in result]
    print(f"   当前标签总数: {len(all_labels)}")
    
    # 2. 检查每个标签的节点数量
    print("\n2️⃣ 检查每个标签的节点数量")
    empty_labels = []
    for label in all_labels:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
        count = result.single()["count"]
        if count == 0:
            empty_labels.append(label)
            print(f"   ⚠️ {label}: 0个节点（空标签）")
        else:
            print(f"   ✅ {label}: {count}个节点")
    
    # 3. 显示空标签列表
    if empty_labels:
        print(f"\n3️⃣ 发现 {len(empty_labels)} 个空标签:")
        for label in empty_labels:
            print(f"   - {label}")
        
        print("\n" + "=" * 60)
        print("📋 清理说明")
        print("=" * 60)
        print("\nNeo4j不支持直接删除标签定义。")
        print("空标签会在以下情况下自动清理：")
        print("1. 重启Neo4j容器")
        print("2. 执行数据库维护操作")
        print("\n建议操作：")
        print("docker-compose restart fitness_neo4j")
        print("\n重启后，未使用的标签定义将自动从schema中移除。")
    else:
        print("\n✅ 没有发现空标签，数据库schema干净！")

driver.close()

print("\n" + "=" * 60)
print("🎉 检查完成")
print("=" * 60)
