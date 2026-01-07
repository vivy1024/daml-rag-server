#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析Neo4j关系类型和结构
"""

import json
from neo4j import GraphDatabase

NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USER = 'neo4j'
NEO4J_PASSWORD = 'build_body_2024'

def analyze_relationships():
    driver = None
    try:
        print("Connecting to Neo4j...")
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

        with driver.session() as session:
            # 1. 详细分析所有关系类型
            print("\n" + "=" * 80)
            print("ALL RELATIONSHIP TYPES ANALYSIS")
            print("=" * 80)

            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type,
                       count(*) as count,
                       collect(DISTINCT labels(startNode(r))[0]) as from_labels,
                       collect(DISTINCT labels(endNode(r))[0]) as to_labels
                ORDER BY count DESC
            """)

            relationships = []
            for record in result:
                rel_info = {
                    'type': record['rel_type'],
                    'count': record['count'],
                    'from_labels': list(set(record['from_labels'])),
                    'to_labels': list(set(record['to_labels']))
                }
                relationships.append(rel_info)

            for rel in relationships:
                print(f"\n{rel['type']}: {rel['count']:,} 个关系")
                print(f"  FROM: {rel['from_labels']}")
                print(f"  TO: {rel['to_labels']}")

            # 2. 分析关键关系示例
            print("\n" + "=" * 80)
            print("KEY RELATIONSHIP EXAMPLES")
            print("=" * 80)

            key_relationships = [
                "TARGETS_PRIMARY",
                "TARGETS_SECONDARY",
                "CONTAINS_NUTRIENT",
                "SUITABLE_FOR_LEVEL",
                "RECOMMENDED_FOR_GOAL"
            ]

            for rel_type in key_relationships:
                print(f"\n--- {rel_type} 示例 ---")
                result = session.run(f"""
                    MATCH (a)-[r:{rel_type}]->(b)
                    RETURN labels(a)[0] as from_label, keys(a)[0..3] as from_sample_keys,
                           labels(b)[0] as to_label, keys(b)[0..3] as to_sample_keys,
                           count(*) as sample_count
                    LIMIT 5
                """)

                sample = result.single()
                if sample:
                    print(f"  FROM ({sample['from_label']}): {sample['from_sample_keys']}")
                    print(f"  TO ({sample['to_label']}): {sample['to_sample_keys']}")
                    print(f"  总计: {sample['sample_count']} 个")

            # 3. 检查Exercise到Muscle的完整关系
            print("\n" + "=" * 80)
            print("EXERCISE-MUSCLE RELATIONSHIP ANALYSIS")
            print("=" * 80)

            result = session.run("""
                MATCH (e:Exercise)-[r]->(m:Muscle)
                RETURN type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """)
            print("所有Exercise-Muscle关系:")
            for record in result:
                print(f"  {record['rel_type']}: {record['count']}")

            # 4. 检查Food-Nutrient关系
            print("\n" + "=" * 80)
            print("FOOD-NUTRIENT RELATIONSHIP ANALYSIS")
            print("=" * 80)

            result = session.run("""
                MATCH (f:Food)-[r:CONTAINS_NUTRIENT]->(n:Nutrient)
                RETURN count(f) as foods_with_nutrients,
                       count(n) as nutrients_in_foods,
                       count(*) as total_relationships,
                       count(DISTINCT f) as unique_foods,
                       count(DISTINCT n) as unique_nutrients
            """)
            record = result.single()
            print(f"Food包含Nutrient关系统计:")
            print(f"  有营养信息的食物: {record['foods_with_nutrients']}")
            print(f"  被包含的营养素: {record['nutrients_in_foods']}")
            print(f"  总关系数: {record['total_relationships']}")
            print(f"  独特食物数: {record['unique_foods']}")
            print(f"  独特营养素数: {record['unique_nutrients']}")

            # 5. 检查PeriodizationModel相关关系
            print("\n" + "=" * 80)
            print("PERIODIZATION MODEL RELATIONSHIPS")
            print("=" * 80)

            result = session.run("""
                MATCH ()-[r]->(pm:PeriodizationModel)
                RETURN type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """)
            print("指向PeriodizationModel的关系:")
            for record in result:
                print(f"  {record['rel_type']}: {record['count']}")

            # 6. 检查TrainingLevel相关关系
            print("\n" + "=" * 80)
            print("TRAINING LEVEL RELATIONSHIPS")
            print("=" * 80)

            result = session.run("""
                MATCH ()-[r]->(tl:TrainingLevel)
                RETURN type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """)
            print("指向TrainingLevel的关系:")
            for record in result:
                print(f"  {record['rel_type']}: {record['count']}")

            # 7. 寻找孤立节点
            print("\n" + "=" * 80)
            print("ISOLATED NODES ANALYSIS")
            print("=" * 80)

            result = session.run("""
                MATCH (n)
                WHERE NOT (n)--()
                RETURN labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
            """)
            isolated_nodes = list(result)
            if isolated_nodes:
                print("孤立节点:")
                for record in isolated_nodes:
                    print(f"  {record['label']}: {record['count']}")
            else:
                print("✓ 没有孤立节点")

            # 8. 检查多跳关系路径
            print("\n" + "=" * 80)
            print("MULTI-HOP RELATIONSHIP PATHS")
            print("=" * 80)

            # 检查Exercise -> Muscle -> MovementPattern的路径
            result = session.run("""
                MATCH path = (e:Exercise)-[:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m:Muscle)
                WHERE ANY(pattern IN m.movement_patterns WHERE pattern IS NOT NULL)
                RETURN e.name_zh as exercise, m.name as muscle,
                       m.movement_patterns[0] as movement_pattern,
                       length(path) as path_length
                LIMIT 5
            """)
            print("Exercise -> Muscle -> MovementPattern 路径示例:")
            for record in result:
                print(f"  {record['exercise']} -> {record['muscle']} ({record['movement_pattern']})")

            # 9. 生成关系映射JSON
            print("\n" + "=" * 80)
            print("GENERATING RELATIONSHIP MAP")
            print("=" * 80)

            relationship_map = {
                "total_relationship_types": len(relationships),
                "relationships": relationships,
                "key_relationships": {
                    "exercise_to_muscle": [
                        {"type": "TARGETS_PRIMARY", "description": "主要目标肌群"},
                        {"type": "TARGETS_SECONDARY", "description": "次要目标肌群"}
                    ],
                    "food_to_nutrient": [
                        {"type": "CONTAINS_NUTRIENT", "description": "食物包含的营养素"}
                    ],
                    "training_relationships": [
                        {"type": "SUITABLE_FOR_LEVEL", "description": "适合的训练水平"},
                        {"type": "RECOMMENDED_FOR_GOAL", "description": "推荐的目标"}
                    ],
                    "periodization_relationships": [
                        {"type": "HAS_PHASE", "description": "包含的训练阶段"},
                        {"type": "PROGRESSES_TO", "description": "进阶到下一阶段"}
                    ]
                }
            }

            with open('neo4j_relationships_map.json', 'w', encoding='utf-8') as f:
                json.dump(relationship_map, f, ensure_ascii=False, indent=2)
            print("✓ 关系映射已保存到 neo4j_relationships_map.json")

            print("\n" + "=" * 80)
            print("ANALYSIS COMPLETE")
            print("=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            driver.close()
            print("\nConnection closed")

if __name__ == "__main__":
    analyze_relationships()
