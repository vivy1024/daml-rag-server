#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正后的Neo4j验证脚本 - 使用正确的字段名
"""

import json
import os
from neo4j import GraphDatabase

NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USER = 'neo4j'
NEO4J_PASSWORD = 'build_body_2024'

def connect_and_verify():
    driver = None
    try:
        print("Connecting to Neo4j...")
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=30
        )

        with driver.session() as session:
            # Test connection
            result = session.run("RETURN 1 as test")
            if result.single()['test'] != 1:
                print("Connection test failed")
                return

            print("Connection successful!\n")

            # 1. 验证Exercise节点字段
            print("=== EXERCISE NODES VERIFICATION ===")
            result = session.run("""
                MATCH (e:Exercise)
                RETURN e.id as id, e.name_zh as name_zh, e.difficulty as difficulty,
                       e.equipment_zh as equipment, e.primary_muscle_zh as primary_muscle
                LIMIT 5
            """)
            print("Sample Exercise data:")
            for record in result:
                print(f"  ID: {record['id']}")
                print(f"  Name: {record['name_zh']}")
                print(f"  Difficulty: {record['difficulty']}")
                print(f"  Equipment: {record['equipment']}")
                print(f"  Primary Muscle: {record['primary_muscle']}")
                print()

            # 2. 检查所有Exercise字段
            print("\n=== EXERCISE FIELD AVAILABILITY ===")
            sample_id = 9  # 您提到的ID
            result = session.run("""
                MATCH (e:Exercise {id: $id})
                RETURN keys(e) as fields
            """, {"id": sample_id})

            fields = result.single()['fields']
            print(f"Exercise node (ID={sample_id}) has {len(fields)} fields:")
            for field in sorted(fields):
                print(f"  - {field}")

            # 3. 验证Muscle节点字段
            print("\n=== MUSCLE NODES VERIFICATION ===")
            result = session.run("""
                MATCH (m:Muscle)
                RETURN m.name as name, keys(m) as fields
                LIMIT 3
            """)
            print("Sample Muscle node fields:")
            for record in result:
                print(f"  Muscle: {record['name']}")
                print(f"  Fields: {record['fields']}")

            # 4. 检查MEV/MAV/MRV是否存在
            print("\n=== CHECKING MEV/MAV/MRV ===")
            result = session.run("""
                MATCH (m:Muscle)
                WITH m, keys(m) as fields
                WHERE any(field in fields WHERE field IN ['MEV', 'MAV', 'MRV'])
                RETURN m.name as name, m.MEV as MEV, m.MAV as MAV, m.MRV as MRV
                LIMIT 5
            """)
            muscles_with_training_volume = []
            for record in result:
                muscles_with_training_volume.append(record)
                print(f"  {record['name']}: MEV={record['MEV']}, MAV={record['MAV']}, MRV={record['MRV']}")

            if not muscles_with_training_volume:
                print("  No Muscle nodes with MEV/MAV/MRV fields found")

            # 5. 检查关系完整性
            print("\n=== RELATIONSHIP COMPLETENESS ===")
            result = session.run("""
                MATCH (e:Exercise)-[r]->(m:Muscle)
                WITH e, count(m) as muscle_count
                RETURN min(muscle_count) as min_muscles, max(muscle_count) as max_muscles,
                       avg(muscle_count) as avg_muscles
            """)
            record = result.single()
            print(f"  Each Exercise targets {record['min_muscles']}-{record['max_muscles']} muscles (avg: {record['avg_muscles']:.1f})")

            # 6. 总计
            print("\n=== SUMMARY ===")
            result = session.run("MATCH (e:Exercise) RETURN count(e) as count")
            exercise_count = result.single()['count']
            print(f"Total Exercise nodes: {exercise_count}")

            result = session.run("MATCH (m:Muscle) RETURN count(m) as count")
            muscle_count = result.single()['count']
            print(f"Total Muscle nodes: {muscle_count}")

            result = session.run("MATCH ()-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->() RETURN count(r) as count")
            rel_count = result.single()['count']
            print(f"Total TARGETS relationships: {rel_count}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            driver.close()
            print("\nConnection closed")

if __name__ == "__main__":
    connect_and_verify()
