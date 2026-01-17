#!/usr/bin/env python3
"""诊断缺失的关系"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
PRODUCTION_URI = "bolt://182.92.78.183:32372"
AUTH = ("neo4j", "build_body_2024")

# 检查缺失的关系类型
missing_rel_types = [
    'CONTRAINDICATED_FOR',
    'HAS_KINETIC_CHAIN', 
    'SUITABLE_FOR_LEVEL',
    'USES_FORCE',
    'HAS_MECHANIC',
    'TARGETS_SECONDARY',
    'USES_GRIP',
    'FOR_GOAL',
    'FOR_LEVEL'
]

local_driver = GraphDatabase.driver(LOCAL_URI, auth=AUTH)
production_driver = GraphDatabase.driver(PRODUCTION_URI, auth=AUTH)

print("诊断缺失关系...\n")

for rel_type in missing_rel_types[:3]:  # 只检查前3个
    print(f"\n{'='*60}")
    print(f"关系类型: {rel_type}")
    print(f"{'='*60}")
    
    # 获取本地的一个示例关系
    with local_driver.session() as session:
        result = session.run(f"""
            MATCH (a)-[r:{rel_type}]->(b)
            RETURN labels(a)[0] as start_label, labels(b)[0] as end_label,
                   properties(a) as start_props, properties(b) as end_props
            LIMIT 1
        """)
        
        for record in result:
            start_label = record['start_label']
            end_label = record['end_label']
            start_props = record['start_props']
            end_props = record['end_props']
            
            print(f"\n示例关系: ({start_label})-[{rel_type}]->({end_label})")
            print(f"起始节点属性: {list(start_props.keys())[:5]}")
            print(f"结束节点属性: {list(end_props.keys())[:5]}")
            
            # 检查生产环境是否有这些节点
            with production_driver.session() as prod_session:
                # 检查起始节点
                start_count = prod_session.run(
                    f"MATCH (n:{start_label}) RETURN count(n) as count"
                ).single()['count']
                
                # 检查结束节点
                end_count = prod_session.run(
                    f"MATCH (n:{end_label}) RETURN count(n) as count"
                ).single()['count']
                
                print(f"\n生产环境节点:")
                print(f"  {start_label}: {start_count}")
                print(f"  {end_label}: {end_count}")
                
                if start_count == 0:
                    print(f"  ❌ 缺少 {start_label} 节点！")
                if end_count == 0:
                    print(f"  ❌ 缺少 {end_label} 节点！")

local_driver.close()
production_driver.close()
