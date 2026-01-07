# -*- coding: utf-8 -*-
"""
分析Neo4j数据与用户档案的关联性

检查哪些Neo4j节点类型在用户档案中有对应的输入途径
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager


def main():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    manager = Neo4jManager(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password,
        database=neo4j_database
    )
    
    print("=" * 70)
    print("Neo4j数据与用户档案关联性分析")
    print("=" * 70)
    
    # 1. InjuryType节点
    print("\n1. InjuryType节点 (17个)")
    print("-" * 50)
    query = "MATCH (n:InjuryType) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "无")
        print(f"  {name}: {name_zh}")
    
    # 2. Joint节点
    print("\n2. Joint节点 (9个)")
    print("-" * 50)
    query = "MATCH (n:Joint) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "无")
        print(f"  {name}: {name_zh}")
    
    # 3. TrainingGoal节点
    print("\n3. TrainingGoal节点 (7个)")
    print("-" * 50)
    query = "MATCH (n:TrainingGoal) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "无")
        print(f"  {name}: {name_zh}")
    
    # 4. Equipment节点
    print("\n4. Equipment节点 (17个)")
    print("-" * 50)
    query = "MATCH (n:Equipment) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "无")
        print(f"  {name}: {name_zh}")
    
    # 5. TrainingLevel节点
    print("\n5. TrainingLevel节点 (4个)")
    print("-" * 50)
    query = "MATCH (n:TrainingLevel) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "无")
        print(f"  {name}: {name_zh}")
    
    # 6. RehabilitationPhase节点
    print("\n6. RehabilitationPhase节点 (3个)")
    print("-" * 50)
    query = "MATCH (n:RehabilitationPhase) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "无")
        print(f"  {name}: {name_zh}")
    
    # 7. Muscle节点
    print("\n7. Muscle节点 (48个) - 前10个")
    print("-" * 50)
    query = "MATCH (n:Muscle) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name LIMIT 10"
    results = manager.execute_query(query, {})
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "无")
        print(f"  {name}: {name_zh}")
    
    print("\n" + "=" * 70)
    print("用户档案字段对照分析")
    print("=" * 70)
    
    print("""
用户档案中的相关字段:
----------------------
1. health_status.injury_history: ['无', '腰部损伤', '膝盖损伤', '肩部损伤', '手腕损伤', '脚踝损伤', '颈部损伤', '其他']
2. health_status.chronic_diseases: ['无', '高血压', '糖尿病', '心脏病', '哮喘', '关节炎', '其他']
3. training_preferences.available_equipment: ['杠铃', '哑铃', '固定器械', '自由重量架', '史密斯架', '龙门架', '弹力带', '壶铃', '健身球', '跳箱', '战绳', '徒手']
4. fitness_goals.primary_goals: ['增肌', '减脂', '增强力量', '提高耐力', '塑形', '功能性训练', '运动表现', '康复训练']
5. basic_info.fitness_level: ['novice', 'beginner', 'intermediate', 'advanced']
""")
    
    print("=" * 70)
    print("问题分析")
    print("=" * 70)
    
    print("""
❌ 问题1: InjuryType节点与用户档案不匹配
   - Neo4j: 17种专业伤病类型 (如 achilles_tendinitis, acl_tear, ankle_sprain...)
   - 用户档案: 7种简化伤病部位 (腰部损伤, 膝盖损伤, 肩部损伤...)
   - 影响: 无法精确匹配用户伤病与动作禁忌

❌ 问题2: Joint节点与用户档案无直接关联
   - Neo4j: 9种关节 (ankle, elbow, hip, knee, shoulder, spine, wrist...)
   - 用户档案: 无关节字段
   - 影响: 无法基于关节问题过滤动作

❌ 问题3: Equipment节点与用户档案不完全匹配
   - Neo4j: 17种器械 (需要检查具体名称)
   - 用户档案: 12种器械 (杠铃, 哑铃, 固定器械...)
   - 影响: 可能存在名称不一致导致匹配失败

❌ 问题4: TrainingGoal节点与用户档案不完全匹配
   - Neo4j: 7种目标 (需要检查具体名称)
   - 用户档案: 8种目标 (增肌, 减脂, 增强力量...)
   - 影响: 目标匹配可能不准确

✅ 正常: TrainingLevel节点与用户档案匹配
   - Neo4j: novice, beginner, intermediate, advanced
   - 用户档案: novice, beginner, intermediate, advanced
   - 状态: 完全匹配
""")
    
    manager.close()


if __name__ == "__main__":
    main()
