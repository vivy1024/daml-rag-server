#!/usr/bin/env python3
"""检查缺失节点的唯一键"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
AUTH = ("neo4j", "build_body_2024")

missing_labels = ['Exercise', 'StrengthStandard', 'Muscle', 'TrainingParams', 'Equipment', 'ACSMStandard', 'NSCAStandard']

driver = GraphDatabase.driver(LOCAL_URI, auth=AUTH)

for label in missing_labels:
    with driver.session() as session:
        # 获取前3个节点的所有属性
        result = session.run(f"MATCH (n:{label}) RETURN properties(n) as props LIMIT 3")
        print(f"\n{label} 示例节点:")
        for i, record in enumerate(result, 1):
            props = record['props']
            print(f"  节点{i}: {list(props.keys())}")
            # 检查是否有预期的唯一键
            if label == 'Exercise':
                print(f"    exercise_id: {props.get('exercise_id')}")
            elif label == 'Muscle':
                print(f"    muscle_id: {props.get('muscle_id')}")
            elif label == 'Equipment':
                print(f"    equipment_id: {props.get('equipment_id')}")
            else:
                print(f"    name: {props.get('name')}")

driver.close()
