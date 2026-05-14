#!/usr/bin/env python3
"""
查找哑铃高脚杯深蹲
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from neo4j import GraphDatabase
from dotenv import load_dotenv
import json

load_dotenv()

uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', '')

driver = GraphDatabase.driver(uri, auth=(user, password))

with driver.session() as session:
    # 查询包含"高脚杯"的动作
    result = session.run("""
        MATCH (e:Exercise)
        WHERE e.name_zh CONTAINS '高脚杯'
        RETURN e.id as id,
               e.name_zh as name,
               e.description_zh as desc_zh,
               e.description_en as desc_en,
               e.correct_steps_zh as steps_zh,
               e.correct_steps_en as steps_en,
               e.kinetic_chain_type as kinetic,
               e.technique_checkpoints as checkpoints
        LIMIT 1
    """)
    
    record = result.single()
    if record:
        print("=" * 60)
        print("找到动作：哑铃高脚杯深蹲")
        print("=" * 60)
        print(f"\nID: {record['id']}")
        print(f"名称: {record['name']}")
        print(f"\n运动链类型: {record['kinetic']}")
        
        print(f"\n描述(中文)长度: {len(record['desc_zh']) if record['desc_zh'] else 0} 字符")
        if record['desc_zh']:
            print(f"内容: {record['desc_zh'][:100]}...")
        
        print(f"\n描述(英文)长度: {len(record['desc_en']) if record['desc_en'] else 0} 字符")
        if record['desc_en']:
            print(f"内容: {record['desc_en'][:100]}...")
        
        print(f"\n正确步骤(中文): {record['steps_zh']}")
        print(f"正确步骤(英文): {record['steps_en'][:100] if record['steps_en'] else None}...")
        
        print(f"\n技术检查点: {record['checkpoints']}")
        
        # 检查是否有重复问题
        if record['desc_zh'] and record['steps_zh']:
            if record['desc_zh'] == record['steps_zh']:
                print("\n⚠️ 警告：description_zh 和 correct_steps_zh 内容重复！")
        
        if not record['steps_zh'] or record['steps_zh'] == '[]':
            print("\n⚠️ 警告：correct_steps_zh 为空！")
    else:
        print("未找到包含'高脚杯'的动作")

driver.close()
