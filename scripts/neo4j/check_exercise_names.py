#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查Exercise节点名称"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager

def main():
    manager = Neo4jManager(
        uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "build_body_2024"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    # 查找包含'face'的动作
    result = manager.execute_query('''
        MATCH (e:Exercise)
        WHERE toLower(e.name) CONTAINS 'face' OR toLower(e.name_zh) CONTAINS '面拉'
        RETURN e.name, e.name_zh
        LIMIT 5
    ''', {})
    print('包含face的动作:')
    for r in result:
        print(f'  {r["e.name"]}: {r["e.name_zh"]}')
    
    # 查找包含'plank'的动作
    result = manager.execute_query('''
        MATCH (e:Exercise)
        WHERE toLower(e.name) CONTAINS 'plank' OR toLower(e.name_zh) CONTAINS '平板'
        RETURN e.name, e.name_zh
        LIMIT 5
    ''', {})
    print('\n包含plank的动作:')
    for r in result:
        print(f'  {r["e.name"]}: {r["e.name_zh"]}')
    
    # 查找包含'squat'的动作
    result = manager.execute_query('''
        MATCH (e:Exercise)
        WHERE toLower(e.name) CONTAINS 'squat' OR toLower(e.name_zh) CONTAINS '深蹲'
        RETURN e.name, e.name_zh
        LIMIT 5
    ''', {})
    print('\n包含squat的动作:')
    for r in result:
        print(f'  {r["e.name"]}: {r["e.name_zh"]}')
    
    manager.close()

if __name__ == "__main__":
    main()
