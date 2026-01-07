#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试Neo4j连接"""

import os
from neo4j import GraphDatabase

neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
neo4j_password = os.getenv('NEO4J_PASSWORD')

print(f"连接信息:")
print(f"  URI: {neo4j_uri}")
print(f"  User: {neo4j_user}")
print(f"  Password: {'***' if neo4j_password else 'None'}")

try:
    driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password) if neo4j_password else None
    )
    with driver.session() as session:
        result = session.run('RETURN 1 AS test')
        test_value = result.single()['test']
        print(f'\n✅ Neo4j连接成功: {test_value}')
    driver.close()
except Exception as e:
    print(f'\n❌ Neo4j连接失败: {e}')

