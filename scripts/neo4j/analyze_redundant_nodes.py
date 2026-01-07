#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Neo4j中的冗余节点

检查以下节点类型：
1. MuscleGroup - 是否存在及使用情况
2. Guideline - 是否存在及使用情况
3. User - 是否存在及使用情况
4. Food vs ChineseFood - 是否重复
"""

import os
from neo4j import GraphDatabase

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 60)
print("🔍 分析Neo4j冗余节点")
print("=" * 60)

with driver.session() as session:
    # 1. 检查MuscleGroup节点
    print("\n1️⃣ MuscleGroup节点分析")
    result = session.run("MATCH (mg:MuscleGroup) RETURN count(mg) as count")
    mg_count = result.single()["count"]
    print(f"   节点数量: {mg_count}")
    
    if mg_count > 0:
        # 检查关系
        result = session.run("MATCH (mg:MuscleGroup)-[r]-() RETURN type(r) as rel_type, count(r) as count")
        print("   关系统计:")
        has_relations = False
        for record in result:
            print(f"     {record['rel_type']}: {record['count']}个")
            has_relations = True
        if not has_relations:
            print("     ⚠️ 无任何关系（孤立节点）")
        
        # 查看示例
        result = session.run("MATCH (mg:MuscleGroup) RETURN mg LIMIT 3")
        print("   示例节点:")
        for record in result:
            node = record["mg"]
            print(f"     {dict(node)}")
    
    # 2. 检查Guideline节点
    print("\n2️⃣ Guideline节点分析")
    result = session.run("MATCH (g:Guideline) RETURN count(g) as count")
    g_count = result.single()["count"]
    print(f"   节点数量: {g_count}")
    
    if g_count > 0:
        # 检查关系
        result = session.run("MATCH (g:Guideline)-[r]-() RETURN type(r) as rel_type, count(r) as count")
        print("   关系统计:")
        has_relations = False
        for record in result:
            print(f"     {record['rel_type']}: {record['count']}个")
            has_relations = True
        if not has_relations:
            print("     ⚠️ 无任何关系（孤立节点）")
        
        # 查看示例
        result = session.run("MATCH (g:Guideline) RETURN g LIMIT 3")
        print("   示例节点:")
        for record in result:
            node = record["g"]
            print(f"     {dict(node)}")
    
    # 3. 检查User节点
    print("\n3️⃣ User节点分析")
    result = session.run("MATCH (u:User) RETURN count(u) as count")
    u_count = result.single()["count"]
    print(f"   节点数量: {u_count}")
    
    if u_count > 0:
        # 检查关系
        result = session.run("MATCH (u:User)-[r]-() RETURN type(r) as rel_type, count(r) as count")
        print("   关系统计:")
        has_relations = False
        for record in result:
            print(f"     {record['rel_type']}: {record['count']}个")
            has_relations = True
        if not has_relations:
            print("     ⚠️ 无任何关系（孤立节点）")
        
        # 查看示例
        result = session.run("MATCH (u:User) RETURN u LIMIT 3")
        print("   示例节点:")
        for record in result:
            node = record["u"]
            print(f"     {dict(node)}")
    
    # 4. 检查Food vs ChineseFood
    print("\n4️⃣ Food vs ChineseFood节点对比")
    result = session.run("MATCH (f:Food) RETURN count(f) as count")
    food_count = result.single()["count"]
    print(f"   Food节点数量: {food_count}")
    
    result = session.run("MATCH (cf:ChineseFood) RETURN count(cf) as count")
    cf_count = result.single()["count"]
    print(f"   ChineseFood节点数量: {cf_count}")
    
    if food_count > 0 and cf_count > 0:
        # 检查是否有节点同时拥有两个标签
        result = session.run("MATCH (n:Food:ChineseFood) RETURN count(n) as count")
        both_count = result.single()["count"]
        print(f"   同时拥有两个标签的节点: {both_count}")
        
        # 比较字段
        result = session.run("MATCH (f:Food) RETURN keys(f) as keys LIMIT 1")
        food_keys = result.single()["keys"] if result.peek() else []
        
        result = session.run("MATCH (cf:ChineseFood) RETURN keys(cf) as keys LIMIT 1")
        cf_keys = result.single()["keys"] if result.peek() else []
        
        print(f"   Food字段: {sorted(food_keys)}")
        print(f"   ChineseFood字段: {sorted(cf_keys)}")
        
        if sorted(food_keys) == sorted(cf_keys):
            print("   ✅ 字段完全相同")
        else:
            print("   ⚠️ 字段不同")
        
        # 检查关系
        result = session.run("MATCH (f:Food)-[r]-() RETURN type(r) as rel_type, count(r) as count")
        print("   Food关系:")
        for record in result:
            print(f"     {record['rel_type']}: {record['count']}个")
        
        result = session.run("MATCH (cf:ChineseFood)-[r]-() RETURN type(r) as rel_type, count(r) as count")
        print("   ChineseFood关系:")
        for record in result:
            print(f"     {record['rel_type']}: {record['count']}个")

    print("\n" + "=" * 60)
    print("📊 分析总结")
    print("=" * 60)

    recommendations = []

    if mg_count > 0:
        result = session.run("MATCH (mg:MuscleGroup)-[r]-() RETURN count(r) as count")
        rel_count = result.single()["count"]
        if rel_count == 0:
            recommendations.append(f"✅ 可以删除 MuscleGroup 节点（{mg_count}个孤立节点）")
        else:
            recommendations.append(f"⚠️ MuscleGroup 有{rel_count}个关系，需要先处理关系")

    if g_count > 0:
        result = session.run("MATCH (g:Guideline)-[r]-() RETURN count(r) as count")
        rel_count = result.single()["count"]
        if rel_count == 0:
            recommendations.append(f"✅ 可以删除 Guideline 节点（{g_count}个孤立节点）")
        else:
            recommendations.append(f"⚠️ Guideline 有{rel_count}个关系，需要先处理关系")

    if u_count > 0:
        result = session.run("MATCH (u:User)-[r]-() RETURN count(r) as count")
        rel_count = result.single()["count"]
        if rel_count == 0:
            recommendations.append(f"✅ 可以删除 User 节点（{u_count}个孤立节点）")
        else:
            recommendations.append(f"⚠️ User 有{rel_count}个关系，需要先处理关系")

    if food_count > 0 and cf_count > 0:
        result = session.run("MATCH (n:Food:ChineseFood) RETURN count(n) as count")
        both_count = result.single()["count"]
        if both_count == food_count and both_count == cf_count:
            recommendations.append(f"✅ Food和ChineseFood完全重复，可以移除ChineseFood标签")
        else:
            recommendations.append(f"⚠️ Food和ChineseFood部分重叠，需要进一步分析")

    print("\n建议操作:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

driver.close()
