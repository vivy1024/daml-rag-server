#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询孤立节点"""

import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    print("=" * 80)
    print("孤立节点统计（没有任何关系的节点）")
    print("=" * 80)
    
    result = session.run("""
        MATCH (n)
        WHERE NOT (n)--()
        RETURN labels(n) as labels, count(*) as count
        ORDER BY count DESC
    """)
    
    total = 0
    for record in result:
        labels = ', '.join(record["labels"])
        count = record["count"]
        total += count
        print(f"  {labels:30s} : {count:>6,} 个")
    
    print(f"\n  {'总计':30s} : {total:>6,} 个孤立节点")
    print("=" * 80)
    
    # 查询需要关系的节点类型
    print("\n需要建立关系的节点类型分析：")
    print("-" * 80)
    
    # StrengthStandard应该与Exercise建立关系
    result = session.run("MATCH (s:StrengthStandard) RETURN count(s) as count")
    strength_count = result.single()["count"]
    print(f"  StrengthStandard: {strength_count} 个（应与Exercise建立HAS_STRENGTH_STANDARD关系）")
    
    # WorkoutProgram应该与Exercise建立关系
    result = session.run("MATCH (w:WorkoutProgram) RETURN count(w) as count")
    workout_count = result.single()["count"]
    print(f"  WorkoutProgram: {workout_count} 个（应与Exercise建立INCLUDES_EXERCISE关系）")
    
    # InjuryType应该与Exercise建立关系
    result = session.run("""
        MATCH (i:InjuryType)
        WHERE NOT (i)<-[:CONTRAINDICATED_FOR]-()
        RETURN count(i) as count
    """)
    injury_isolated = result.single()["count"]
    print(f"  InjuryType: {injury_isolated} 个孤立（应与Exercise建立CONTRAINDICATED_FOR关系）")
    
    # Equipment应该与Exercise建立关系
    result = session.run("""
        MATCH (e:Equipment)
        WHERE NOT (e)<-[:REQUIRES]-()
        RETURN count(e) as count
    """)
    equipment_isolated = result.single()["count"]
    print(f"  Equipment: {equipment_isolated} 个孤立（应与Exercise建立REQUIRES关系）")
    
    # RehabilitationPhase应该与Exercise建立关系
    result = session.run("""
        MATCH (r:RehabilitationPhase)
        WHERE NOT (r)--()
        RETURN count(r) as count
    """)
    rehab_isolated = result.single()["count"]
    print(f"  RehabilitationPhase: {rehab_isolated} 个孤立（应与Exercise建立REHAB_PROGRESSION关系）")
    
    # GripType应该与Exercise建立关系
    result = session.run("""
        MATCH (g:GripType)
        WHERE NOT (g)<-[:USES_GRIP]-()
        RETURN count(g) as count
    """)
    grip_isolated = result.single()["count"]
    print(f"  GripType: {grip_isolated} 个孤立（应与Exercise建立USES_GRIP关系）")
    
    # Joint应该与Exercise建立关系
    result = session.run("MATCH (j:Joint) RETURN count(j) as count")
    joint_count = result.single()["count"]
    print(f"  Joint: {joint_count} 个（应与Exercise建立INVOLVES_JOINT关系）")
    
    # ACSMStandard和NSCAStandard是知识库节点，可以保持孤立
    result = session.run("MATCH (a:ACSMStandard) RETURN count(a) as count")
    acsm_count = result.single()["count"]
    print(f"  ACSMStandard: {acsm_count} 个（知识库节点，可保持孤立）")
    
    result = session.run("MATCH (n:NSCAStandard) RETURN count(n) as count")
    nsca_count = result.single()["count"]
    print(f"  NSCAStandard: {nsca_count} 个（知识库节点，可保持孤立）")
    
    print("=" * 80)

driver.close()
