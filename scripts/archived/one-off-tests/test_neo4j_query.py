#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试Neo4j查询"""

from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

with driver.session() as session:
    # 测试查询1：查看胸大肌相关的动作及其器械
    result = session.run('''
        MATCH (m:Muscle)
        WHERE m.name_zh CONTAINS '胸'
        MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
        RETURN e.name_zh AS name, e.equipment_zh AS equipment
        LIMIT 10
    ''')
    
    print('胸部相关动作（前10个）:')
    for record in result:
        print(f'  - {record["name"]}: {record["equipment"]}')
    
    # 测试查询2：使用ANY函数匹配列表中的任意元素
    result2 = session.run('''
        MATCH (m:Muscle)
        WHERE m.name_zh CONTAINS '胸'
        MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
        WHERE ANY(equip IN e.equipment_zh WHERE equip IN $equipment)
        RETURN e.name_zh AS name, e.equipment_zh AS equipment
        LIMIT 10
    ''', equipment=['哑铃', '杠铃'])
    
    print('\n使用ANY函数的查询结果（前10个）:')
    for record in result2:
        print(f'  - {record["name"]}: {record["equipment"]}')
    
    # 测试查询3：使用列表交集
    result3 = session.run('''
        MATCH (m:Muscle)
        WHERE m.name_zh CONTAINS '胸'
        MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m)
        WHERE size([x IN e.equipment_zh WHERE x IN $equipment | 1]) > 0
        RETURN e.name_zh AS name, e.equipment_zh AS equipment
        LIMIT 10
    ''', equipment=['哑铃', '杠铃'])
    
    print('\n使用列表交集的查询结果（前10个）:')
    for record in result3:
        print(f'  - {record["name"]}: {record["equipment"]}')

driver.close()
