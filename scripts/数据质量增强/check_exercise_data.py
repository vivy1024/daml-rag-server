#!/usr/bin/env python3
"""
检查Exercise节点数据质量

查看刚才补充的数据
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', '')

driver = GraphDatabase.driver(uri, auth=(user, password))

print("=" * 60)
print("检查Exercise节点数据")
print("=" * 60)

with driver.session() as session:
    # 1. 查询哑铃高脚杯深蹲
    print("\n1. 查询哑铃高脚杯深蹲 (exercise_id=11)")
    print("-" * 60)
    
    result = session.run("""
        MATCH (e:Exercise {exercise_id: 11})
        RETURN e.name_zh as name,
               e.kinetic_chain_type as kinetic,
               e.technique_checkpoints as checkpoints,
               e.rom_requirements as rom
    """)
    
    record = result.single()
    if record:
        print(f"动作名称: {record['name']}")
        print(f"运动链类型: {record['kinetic']}")
        print(f"技术检查点: {record['checkpoints'][:100] if record['checkpoints'] else '无'}...")
        print(f"关节活动度: {record['rom'] if record['rom'] else '无'}")
    else:
        print("未找到该动作")
    
    # 2. 统计运动链类型分布
    print("\n2. 运动链类型分布")
    print("-" * 60)
    
    result = session.run("""
        MATCH (e:Exercise)
        WHERE e.kinetic_chain_type IS NOT NULL
        RETURN e.kinetic_chain_type as type, count(e) as count
        ORDER BY count DESC
    """)
    
    for record in result:
        print(f"{record['type']}: {record['count']} 个")
    
    # 3. 统计技术检查点
    print("\n3. 技术检查点统计")
    print("-" * 60)
    
    result = session.run("""
        MATCH (e:Exercise)
        WHERE e.technique_checkpoints IS NOT NULL
        RETURN count(e) as count
    """)
    
    record = result.single()
    print(f"有技术检查点的动作: {record['count']} 个")
    
    # 4. 查看几个有技术检查点的动作
    print("\n4. 技术检查点示例")
    print("-" * 60)
    
    result = session.run("""
        MATCH (e:Exercise)
        WHERE e.technique_checkpoints IS NOT NULL
        RETURN e.name_zh as name, e.technique_checkpoints as checkpoints
        LIMIT 3
    """)
    
    for record in result:
        print(f"\n{record['name']}:")
        import json
        checkpoints = json.loads(record['checkpoints'])
        for i, cp in enumerate(checkpoints, 1):
            print(f"  {i}. {cp}")
    
    # 5. 统计关节活动度
    print("\n5. 关节活动度统计")
    print("-" * 60)
    
    result = session.run("""
        MATCH (e:Exercise)
        WHERE e.rom_requirements IS NOT NULL
        RETURN count(e) as count
    """)
    
    record = result.single()
    print(f"有关节活动度要求的动作: {record['count']} 个")

driver.close()

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)
