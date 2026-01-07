# -*- coding: utf-8 -*-
"""
Neo4j数据与用户档案映射分析

详细分析每个节点类型的数据流通问题，并提出解决方案
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager


# 用户档案中的选项定义
USER_PROFILE_OPTIONS = {
    "injury_history": ['无', '腰部损伤', '膝盖损伤', '肩部损伤', '手腕损伤', '脚踝损伤', '颈部损伤', '其他'],
    "chronic_diseases": ['无', '高血压', '糖尿病', '心脏病', '哮喘', '关节炎', '其他'],
    "available_equipment": ['杠铃', '哑铃', '固定器械', '自由重量架', '史密斯架', '龙门架', '弹力带', '壶铃', '健身球', '跳箱', '战绳', '徒手'],
    "primary_goals": ['增肌', '减脂', '增强力量', '提高耐力', '塑形', '功能性训练', '运动表现', '康复训练'],
    "fitness_level": ['novice', 'beginner', 'intermediate', 'advanced'],
}


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
    
    print("=" * 80)
    print("Neo4j数据与用户档案映射详细分析")
    print("=" * 80)
    
    # ========== 1. InjuryType分析 ==========
    print("\n" + "=" * 80)
    print("1. InjuryType节点分析")
    print("=" * 80)
    
    query = "MATCH (n:InjuryType) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    injury_types = manager.execute_query(query, {})
    
    print("\nNeo4j InjuryType节点:")
    for r in injury_types:
        print(f"  - {r.get('name', '')}: {r.get('name_zh', '')}")
    
    print("\n用户档案 injury_history 选项:")
    for opt in USER_PROFILE_OPTIONS["injury_history"]:
        print(f"  - {opt}")
    
    # 建立映射关系
    injury_mapping = {
        "腰部损伤": ["下背部疼痛", "腰椎间盘突出"],
        "膝盖损伤": ["前交叉韧带损伤", "膝盖受伤", "髌骨软化症", "髂胫束综合征"],
        "肩部损伤": ["肩峰撞击", "肩袖损伤", "肩部受伤"],
        "手腕损伤": ["腕管综合征", "腕部受伤"],
        "脚踝损伤": ["跟腱炎", "足底筋膜炎"],
        "颈部损伤": ["颈椎病", "颈部受伤"],
    }
    
    print("\n建议的映射关系:")
    for user_opt, neo4j_types in injury_mapping.items():
        print(f"  {user_opt} -> {neo4j_types}")
    
    # 未映射的InjuryType
    mapped_types = set()
    for types in injury_mapping.values():
        mapped_types.update(types)
    
    unmapped = [r.get('name_zh', '') for r in injury_types if r.get('name_zh', '') not in mapped_types]
    print(f"\n未映射的InjuryType: {unmapped}")
    print("  - 网球肘、高尔夫球肘: 可归类为'其他'或新增'肘部损伤'选项")
    
    # ========== 2. Equipment分析 ==========
    print("\n" + "=" * 80)
    print("2. Equipment节点分析")
    print("=" * 80)
    
    query = "MATCH (n:Equipment) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    equipment_types = manager.execute_query(query, {})
    
    print("\nNeo4j Equipment节点:")
    for r in equipment_types:
        name = r.get('name', '')
        name_zh = r.get('name_zh', '')
        print(f"  - {name}: {name_zh}")
    
    print("\n用户档案 available_equipment 选项:")
    for opt in USER_PROFILE_OPTIONS["available_equipment"]:
        print(f"  - {opt}")
    
    # 分析问题
    print("\n问题分析:")
    print("  ❌ Neo4j中有非器械项目: 恢复, 拉伸, 有氧训练, 瑜伽")
    print("  ❌ 名称不一致: '固定器械' vs '器械', '弹力带' vs '阻力带'")
    print("  ❌ 缺少映射: Bosu-Ball, TRX, Vitruvian, 药球, 杠铃片")
    print("  ❌ 用户档案缺少: 绳索训练")
    
    equipment_mapping = {
        "杠铃": ["杠铃", "杠铃片"],
        "哑铃": ["哑铃"],
        "固定器械": ["器械"],
        "史密斯架": ["史密斯机"],
        "弹力带": ["阻力带"],
        "壶铃": ["壶铃"],
        "徒手": ["徒手训练"],
        "健身球": ["药球"],  # 或者需要区分
    }
    
    print("\n建议的映射关系:")
    for user_opt, neo4j_types in equipment_mapping.items():
        print(f"  {user_opt} -> {neo4j_types}")
    
    # ========== 3. TrainingGoal分析 ==========
    print("\n" + "=" * 80)
    print("3. TrainingGoal节点分析")
    print("=" * 80)
    
    query = "MATCH (n:TrainingGoal) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    goal_types = manager.execute_query(query, {})
    
    print("\nNeo4j TrainingGoal节点:")
    for r in goal_types:
        name = r.get('name', '')
        name_zh = r.get('name_zh', '')
        print(f"  - {name}: {name_zh}")
    
    print("\n用户档案 primary_goals 选项:")
    for opt in USER_PROFILE_OPTIONS["primary_goals"]:
        print(f"  - {opt}")
    
    print("\n问题分析:")
    print("  ❌ 数据重复: 'Lose Weight/减脂' 和 '减脂' 是重复的")
    print("  ❌ 缺少name_zh: '减脂', '增力', '维持' 没有英文名")
    print("  ❌ 名称不一致: 'Gain Muscle/增肌' vs '增肌'")
    
    goal_mapping = {
        "增肌": ["Gain Muscle", "增肌"],
        "减脂": ["Lose Weight", "减脂"],
        "增强力量": ["Powerlifting", "增力"],
        "提高耐力": ["Improve Fitness"],
        "塑形": [],  # 无对应
        "功能性训练": [],  # 无对应
        "运动表现": [],  # 无对应
        "康复训练": [],  # 无对应
    }
    
    print("\n建议的映射关系:")
    for user_opt, neo4j_types in goal_mapping.items():
        status = "✅" if neo4j_types else "❌ 无对应"
        print(f"  {user_opt} -> {neo4j_types if neo4j_types else status}")
    
    # ========== 4. Joint分析 ==========
    print("\n" + "=" * 80)
    print("4. Joint节点分析")
    print("=" * 80)
    
    query = "MATCH (n:Joint) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    joint_types = manager.execute_query(query, {})
    
    print("\nNeo4j Joint节点:")
    for r in joint_types:
        name = r.get('name', '')
        name_zh = r.get('name_zh', '')
        print(f"  - {name}: {name_zh}")
    
    print("\n用户档案中无直接关节字段")
    print("但可以通过 injury_history 间接关联:")
    
    joint_injury_mapping = {
        "肩关节": "肩部损伤",
        "肘关节": "其他",  # 或新增肘部损伤
        "腕关节": "手腕损伤",
        "髋关节": "其他",  # 或新增髋部损伤
        "膝关节": "膝盖损伤",
        "踝关节": "脚踝损伤",
        "脊柱": "腰部损伤",
        "颈椎": "颈部损伤",
    }
    
    print("\n建议的关节-伤病映射:")
    for joint, injury in joint_injury_mapping.items():
        print(f"  {joint} -> {injury}")
    
    # ========== 5. 总结和建议 ==========
    print("\n" + "=" * 80)
    print("总结和解决方案")
    print("=" * 80)
    
    print("""
解决方案1: 创建映射服务 (推荐)
------------------------------
在 src/applications/fitness/services/ 创建 data_mapper.py
- 实现用户档案选项到Neo4j节点的映射
- 支持双向查询
- 处理模糊匹配

解决方案2: 清理Neo4j数据
------------------------------
- 删除Equipment中的非器械项目 (恢复, 拉伸, 有氧训练, 瑜伽)
- 合并重复的TrainingGoal节点
- 统一命名规范

解决方案3: 扩展用户档案选项
------------------------------
- 添加更多伤病选项 (肘部损伤, 髋部损伤)
- 添加更多器械选项 (TRX, 药球, 绳索)
- 添加更多目标选项 (维持体重)

优先级建议:
1. 先实现映射服务 (不改变现有数据)
2. 清理明显错误的数据 (Equipment中的非器械)
3. 逐步扩展用户档案选项 (需要前后端配合)
""")
    
    manager.close()


if __name__ == "__main__":
    main()
