# -*- coding: utf-8 -*-
"""检查杠铃片节点的使用情况"""

from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://fitness_neo4j:7687', auth=('neo4j', 'build_body_2024'))

with driver.session() as session:
    # 查看杠铃相关节点
    result = session.run('MATCH (e:Equipment) WHERE e.name_zh CONTAINS "杠铃" RETURN e.name, e.name_zh')
    print('=== 杠铃相关节点 ===')
    for r in result:
        print(f'  {r["e.name"]} - {r["e.name_zh"]}')
    
    # 查看有多少Exercise使用杠铃片
    result = session.run('MATCH (ex:Exercise)-[:REQUIRES]->(e:Equipment {name_zh: "杠铃片"}) RETURN count(ex) as count')
    count = result.single()['count']
    print(f'\n使用杠铃片的Exercise数量: {count}')
    
    # 查看几个使用杠铃片的动作
    result = session.run('MATCH (ex:Exercise)-[:REQUIRES]->(e:Equipment {name_zh: "杠铃片"}) RETURN ex.name_zh, ex.id LIMIT 10')
    print('\n使用杠铃片的动作示例:')
    for r in result:
        print(f'  - {r["ex.name_zh"]} (ID: {r["ex.id"]})')
    
    # 对比：使用杠铃的动作数量
    result = session.run('MATCH (ex:Exercise)-[:REQUIRES]->(e:Equipment {name_zh: "杠铃"}) RETURN count(ex) as count')
    count = result.single()['count']
    print(f'\n使用杠铃的Exercise数量: {count}')

driver.close()
