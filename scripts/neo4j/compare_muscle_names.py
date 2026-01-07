#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比Neo4j和数据文件中的Muscle名称"""

import os
import json
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")
DATA_FILE = "/app/data/muscle_data/muscle_entities_comprehensive.json"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 加载数据文件
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    muscle_data = json.load(f)

with driver.session() as session:
    # 查询Neo4j中的Muscle节点
    result = session.run("MATCH (m:Muscle) RETURN m.name_zh as name_zh, m.name_en as name_en ORDER BY m.name_zh")
    neo4j_muscles = [(r["name_zh"], r["name_en"]) for r in result]
    
    print("=" * 80)
    print("Neo4j中的Muscle节点 (48个)")
    print("=" * 80)
    for i, (name_zh, name_en) in enumerate(neo4j_muscles, 1):
        print(f"{i:2d}. {name_zh:15s} ({name_en})")
    
    print("\n" + "=" * 80)
    print("数据文件中的Muscle (42个)")
    print("=" * 80)
    for i, muscle in enumerate(muscle_data, 1):
        print(f"{i:2d}. {muscle['name']:15s} ({muscle['nameEn']})")
    
    print("\n" + "=" * 80)
    print("未匹配的Neo4j节点")
    print("=" * 80)
    
    data_names_zh = {m['name'] for m in muscle_data}
    data_names_en = {m['nameEn'] for m in muscle_data}
    
    unmatched = []
    for name_zh, name_en in neo4j_muscles:
        if name_zh not in data_names_zh and name_en not in data_names_en:
            unmatched.append((name_zh, name_en))
            print(f"  {name_zh:15s} ({name_en})")
    
    print(f"\n总计: {len(unmatched)} 个未匹配")

driver.close()
