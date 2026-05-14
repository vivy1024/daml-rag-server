#!/usr/bin/env python3
"""检查Neo4j Exercise节点的空值字段"""

from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://fitness_neo4j:7687', auth=('neo4j', 'build_body_2024'))

with driver.session() as session:
    # 统计空值
    result = session.run('''
        MATCH (e:Exercise)
        RETURN 
            count(e) as total,
            sum(CASE WHEN e.description_zh IS NULL OR e.description_zh = '' THEN 1 ELSE 0 END) as empty_desc_zh,
            sum(CASE WHEN e.description_en IS NULL OR e.description_en = '' THEN 1 ELSE 0 END) as empty_desc_en,
            sum(CASE WHEN e.grips_zh IS NULL OR size(e.grips_zh) = 0 THEN 1 ELSE 0 END) as empty_grips_zh,
            sum(CASE WHEN e.grips_en IS NULL OR size(e.grips_en) = 0 THEN 1 ELSE 0 END) as empty_grips_en,
            sum(CASE WHEN e.force_zh IS NULL OR e.force_zh = '' THEN 1 ELSE 0 END) as empty_force_zh,
            sum(CASE WHEN e.mechanic_zh IS NULL OR e.mechanic_zh = '' THEN 1 ELSE 0 END) as empty_mechanic_zh
    ''')
    record = result.single()
    print('Neo4j Exercise空值统计:')
    print(f"总数: {record['total']}")
    print(f"description_zh空值: {record['empty_desc_zh']}")
    print(f"description_en空值: {record['empty_desc_en']}")
    print(f"grips_zh空值: {record['empty_grips_zh']}")
    print(f"grips_en空值: {record['empty_grips_en']}")
    print(f"force_zh空值: {record['empty_force_zh']}")
    print(f"mechanic_zh空值: {record['empty_mechanic_zh']}")

driver.close()
