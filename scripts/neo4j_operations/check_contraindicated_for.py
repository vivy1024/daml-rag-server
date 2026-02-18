#!/usr/bin/env python3
"""检查CONTRAINDICATED_FOR关系"""
import os
from neo4j import GraphDatabase

os.environ['NO_PROXY'] = 'localhost,127.0.0.1,fitness_neo4j'

driver = GraphDatabase.driver(
    'bolt://fitness_neo4j:7687',
    auth=('neo4j', 'build_body_2024')
)

with driver.session() as session:
    # 检查CONTRAINDICATED_FOR关系
    result = session.run('MATCH ()-[r:CONTRAINDICATED_FOR]->() RETURN count(r) as count')
    count = result.single()['count']
    print(f'CONTRAINDICATED_FOR关系数量: {count}')
    
    # 检查InjuryType节点
    result = session.run('MATCH (i:InjuryType) RETURN count(i) as count')
    injury_count = result.single()['count']
    print(f'InjuryType节点数量: {injury_count}')
    
    # 检查Exercise节点的safety相关字段
    result = session.run('''
        MATCH (e:Exercise)
        WHERE e.safety_warning_signs IS NOT NULL AND size(e.safety_warning_signs) > 0
        RETURN count(e) as count
    ''')
    safety_count = result.single()['count']
    print(f'有safety_warning_signs的Exercise: {safety_count}')
    
    # 查看InjuryType节点示例
    if injury_count > 0:
        result = session.run('''
            MATCH (i:InjuryType)
            RETURN i.name as name, i.name_zh as name_zh, i.name_en as name_en
            LIMIT 10
        ''')
        print('\nInjuryType节点示例:')
        for record in result:
            name_zh = record.get('name_zh', '')
            name_en = record.get('name_en', '')
            name = record.get('name', '')
            print(f'  {name_zh or name_en or name}')
    
    # 查看Exercise的safety_warning_signs示例
    if safety_count > 0:
        result = session.run('''
            MATCH (e:Exercise)
            WHERE e.safety_warning_signs IS NOT NULL AND size(e.safety_warning_signs) > 0
            RETURN e.name_zh as name, e.safety_warning_signs as warnings
            LIMIT 5
        ''')
        print('\nExercise的safety_warning_signs示例:')
        for record in result:
            warnings = record['warnings']
            print(f'  {record["name"]}:')
            for w in warnings[:3]:
                print(f'    - {w}')

driver.close()
