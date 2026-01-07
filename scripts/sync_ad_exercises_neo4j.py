#!/usr/bin/env python3
"""同步广告动作修复到Neo4j"""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"

FIXES = {
    306: {
        'name_zh': '杠铃交错站姿硬拉',
        'description_zh': '杠铃交错站姿硬拉是一种单侧训练变体，通过前后脚站位增加核心稳定性挑战，主要锻炼臀部和腿后肌群。',
        'primary_muscle_zh': '臀部'
    },
    308: {
        'name_zh': '杠铃单腿硬拉',
        'description_zh': '杠铃单腿硬拉是一种高级单侧训练动作，通过单腿支撑增强平衡能力和核心稳定性，主要锻炼臀部和腿后肌群。',
        'primary_muscle_zh': '臀部'
    },
    1224: {
        'name_zh': 'Y字伸展',
        'description_zh': 'Y字伸展是一种肩部康复和强化动作，通过俯卧抬臂锻炼三角肌后束和肩袖肌群。',
        'primary_muscle_zh': '三角肌后束'
    }
}

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=== 更新Neo4j Exercise节点 ===")

with driver.session() as session:
    for ex_id, data in FIXES.items():
        result = session.run("""
            MATCH (e:Exercise {id: $id})
            SET e.name_zh = $name_zh,
                e.description_zh = $description_zh,
                e.primary_muscle_zh = $primary_muscle_zh
            RETURN e.name_zh
        """, id=ex_id, **data)
        record = result.single()
        if record:
            print(f"更新 ID {ex_id}: {record['e.name_zh']}")

driver.close()
print("\nNeo4j更新完成!")
