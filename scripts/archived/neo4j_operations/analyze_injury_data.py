#!/usr/bin/env python3
"""分析损伤相关数据"""
import os
from neo4j import GraphDatabase

os.environ['NO_PROXY'] = 'localhost,127.0.0.1,fitness_neo4j'

driver = GraphDatabase.driver(
    'bolt://fitness_neo4j:7687',
    auth=('neo4j', 'build_body_2024')
)

with driver.session() as session:
    # 查看equipment_risks字段
    result = session.run('''
        MATCH (e:Exercise)
        WHERE e.equipment_risks IS NOT NULL AND size(e.equipment_risks) > 0
        RETURN e.name_zh as name, e.equipment_risks as risks
        LIMIT 5
    ''')
    print('Exercise的equipment_risks示例:')
    for record in result:
        print(f'\n{record["name"]}:')
        for risk in record['risks'][:3]:
            print(f'  - {risk}')
    
    # 查看safety_level分布
    result = session.run('''
        MATCH (e:Exercise)
        RETURN e.safety_level as level, count(*) as count
        ORDER BY count DESC
    ''')
    print('\n\nsafety_level分布:')
    for record in result:
        print(f'  {record["level"]}: {record["count"]}个')
    
    # 查看是否有与损伤相关的描述
    result = session.run('''
        MATCH (e:Exercise)
        WHERE e.description_zh CONTAINS '损伤' 
           OR e.description_zh CONTAINS '受伤'
           OR e.description_zh CONTAINS '禁忌'
        RETURN e.name_zh as name, e.description_zh as desc
        LIMIT 3
    ''')
    print('\n\n包含损伤相关描述的Exercise:')
    for record in result:
        desc = record['desc'][:100] if record['desc'] else ''
        print(f'  {record["name"]}: {desc}...')
    
    # 统计有多少Exercise有equipment_risks
    result = session.run('''
        MATCH (e:Exercise)
        WHERE e.equipment_risks IS NOT NULL AND size(e.equipment_risks) > 0
        RETURN count(e) as count
    ''')
    count = result.single()['count']
    print(f'\n\n有equipment_risks的Exercise: {count}个')

driver.close()
