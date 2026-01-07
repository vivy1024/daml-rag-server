#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证Food节点状态"""

import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    result = session.run("MATCH (f:Food) RETURN count(f) as count")
    food_count = result.single()["count"]
    print(f"✅ Food节点: {food_count}")
    
    result = session.run("MATCH (cf:ChineseFood) RETURN count(cf) as count")
    cf_count = result.single()["count"]
    print(f"✅ ChineseFood节点: {cf_count}")
    
    result = session.run("MATCH (f:Food)-[r:CONTAINS_NUTRIENT]->() RETURN count(r) as count")
    rel_count = result.single()["count"]
    print(f"✅ CONTAINS_NUTRIENT关系: {rel_count}")

driver.close()
