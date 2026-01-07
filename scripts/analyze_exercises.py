"""分析Exercise动作数据，为热身和放松动作筛选提供依据"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://fitness_neo4j:7687', auth=('neo4j', 'build_body_2024'))

with driver.session() as session:
    # 查询恢复类动作
    print('=== 恢复类动作 ===')
    result = session.run('''
        MATCH (e:Exercise)
        WHERE '恢复' IN e.equipment_zh
        RETURN e.id as id, e.name_zh as name, e.primary_muscle_zh as muscle
        ORDER BY e.name_zh
    ''')
    for record in result:
        print(f"ID:{record['id']} | {record['name']} | {record['muscle']}")
    
    # 查询拉伸类动作
    print()
    print('=== 拉伸类动作 ===')
    result = session.run('''
        MATCH (e:Exercise)
        WHERE '拉伸' IN e.equipment_zh
        RETURN e.id as id, e.name_zh as name, e.primary_muscle_zh as muscle
        ORDER BY e.name_zh
    ''')
    for record in result:
        print(f"ID:{record['id']} | {record['name']} | {record['muscle']}")
    
    # 查询瑜伽类动作
    print()
    print('=== 瑜伽类动作 ===')
    result = session.run('''
        MATCH (e:Exercise)
        WHERE '瑜伽' IN e.equipment_zh
        RETURN e.id as id, e.name_zh as name, e.primary_muscle_zh as muscle
        ORDER BY e.name_zh
    ''')
    for record in result:
        print(f"ID:{record['id']} | {record['name']} | {record['muscle']}")
    
    # 查询有氧类动作
    print()
    print('=== 有氧类动作 ===')
    result = session.run('''
        MATCH (e:Exercise)
        WHERE '有氧训练' IN e.equipment_zh
        RETURN e.id as id, e.name_zh as name, e.primary_muscle_zh as muscle
        ORDER BY e.name_zh
    ''')
    for record in result:
        print(f"ID:{record['id']} | {record['name']} | {record['muscle']}")
    
    # 查询徒手训练动作
    print()
    print('=== 徒手训练动作 (前50个) ===')
    result = session.run('''
        MATCH (e:Exercise)
        WHERE '徒手训练' IN e.equipment_zh
        RETURN e.id as id, e.name_zh as name, e.primary_muscle_zh as muscle, e.force as force
        ORDER BY e.name_zh
        LIMIT 50
    ''')
    for record in result:
        print(f"ID:{record['id']} | {record['name']} | {record['muscle']} | {record['force']}")

driver.close()
