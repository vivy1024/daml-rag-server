# -*- coding: utf-8 -*-
"""
更新Neo4j TrainingGoal节点

添加训练参数属性：sets、reps、rest_seconds、intensity_percent等

版本: v1.0.0
日期: 2026-01-05
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from neo4j import GraphDatabase
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://fitness_neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "build_body_2024")


# 训练目标参数定义
TRAINING_GOAL_PARAMS = {
    # 增肌
    "hypertrophy": {
        "name": "hypertrophy",
        "name_zh": "增肌",
        "reps_min": 8,
        "reps_max": 12,
        "sets_min": 3,
        "sets_max": 4,
        "rest_seconds_min": 60,
        "rest_seconds_max": 90,
        "intensity_percent_min": 65,
        "intensity_percent_max": 75,
        "rir_target": 2,
        "description": "中等负重，中等次数，适度休息，追求肌肉泵感和代谢压力",
    },
    # 减脂
    "fat_loss": {
        "name": "fat_loss",
        "name_zh": "减脂",
        "reps_min": 12,
        "reps_max": 20,
        "sets_min": 3,
        "sets_max": 5,
        "rest_seconds_min": 30,
        "rest_seconds_max": 45,
        "intensity_percent_min": 50,
        "intensity_percent_max": 65,
        "rir_target": 3,
        "description": "轻中负重，高次数，短休息，追求高心率和热量消耗",
    },
    # 增强力量
    "strength": {
        "name": "strength",
        "name_zh": "增强力量",
        "reps_min": 1,
        "reps_max": 5,
        "sets_min": 4,
        "sets_max": 6,
        "rest_seconds_min": 180,
        "rest_seconds_max": 300,
        "intensity_percent_min": 85,
        "intensity_percent_max": 100,
        "rir_target": 1,
        "description": "大负重，低次数，长休息，追求神经适应和最大力量",
    },
    # 提高耐力
    "endurance": {
        "name": "endurance",
        "name_zh": "提高耐力",
        "reps_min": 15,
        "reps_max": 25,
        "sets_min": 2,
        "sets_max": 3,
        "rest_seconds_min": 15,
        "rest_seconds_max": 30,
        "intensity_percent_min": 40,
        "intensity_percent_max": 60,
        "rir_target": 4,
        "description": "轻负重，高次数，极短休息，追求肌肉耐力和心肺适应",
    },
    # 塑形
    "body_shaping": {
        "name": "body_shaping",
        "name_zh": "塑形",
        "reps_min": 10,
        "reps_max": 15,
        "sets_min": 3,
        "sets_max": 4,
        "rest_seconds_min": 45,
        "rest_seconds_max": 60,
        "intensity_percent_min": 60,
        "intensity_percent_max": 70,
        "rir_target": 2,
        "description": "中等负重，中高次数，适度休息，追求肌肉线条和体型改善",
    },
    # 功能性训练
    "functional": {
        "name": "functional",
        "name_zh": "功能性训练",
        "reps_min": 8,
        "reps_max": 15,
        "sets_min": 2,
        "sets_max": 4,
        "rest_seconds_min": 60,
        "rest_seconds_max": 90,
        "intensity_percent_min": 50,
        "intensity_percent_max": 70,
        "rir_target": 3,
        "description": "多平面动作，复合运动，强调动作质量和身体协调",
    },
    # 运动表现
    "athletic_performance": {
        "name": "athletic_performance",
        "name_zh": "运动表现",
        "reps_min": 3,
        "reps_max": 8,
        "sets_min": 3,
        "sets_max": 5,
        "rest_seconds_min": 120,
        "rest_seconds_max": 180,
        "intensity_percent_min": 70,
        "intensity_percent_max": 90,
        "rir_target": 2,
        "description": "爆发力动作，中高负重，充分休息，追求速度和力量输出",
    },
    # 康复训练
    "rehabilitation": {
        "name": "rehabilitation",
        "name_zh": "康复训练",
        "reps_min": 12,
        "reps_max": 20,
        "sets_min": 2,
        "sets_max": 3,
        "rest_seconds_min": 60,
        "rest_seconds_max": 90,
        "intensity_percent_min": 30,
        "intensity_percent_max": 50,
        "rir_target": 5,
        "description": "轻负重，高次数，慢节奏，强调控制和关节稳定",
    },
}

# 旧节点名称到新名称的映射
OLD_TO_NEW_MAPPING = {
    "Gain Muscle": "hypertrophy",
    "Lose Weight": "fat_loss",
    "Powerlifting": "strength",
    "Improve Fitness": "endurance",
}


def update_training_goals():
    """更新TrainingGoal节点"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("=" * 60)
            print("更新Neo4j TrainingGoal节点")
            print("=" * 60)
            
            # 1. 查看现有节点
            print("\n1. 现有TrainingGoal节点:")
            result = session.run("MATCH (t:TrainingGoal) RETURN t.name, t.name_zh ORDER BY t.name")
            existing_nodes = []
            for record in result:
                print(f"   - {record['t.name']}: {record['t.name_zh']}")
                existing_nodes.append(record['t.name'])
            
            # 2. 更新现有节点
            print("\n2. 更新现有节点:")
            for old_name, new_name in OLD_TO_NEW_MAPPING.items():
                if old_name in existing_nodes:
                    params = TRAINING_GOAL_PARAMS[new_name]
                    query = """
                    MATCH (t:TrainingGoal {name: $old_name})
                    SET t.name = $name,
                        t.name_zh = $name_zh,
                        t.reps_min = $reps_min,
                        t.reps_max = $reps_max,
                        t.sets_min = $sets_min,
                        t.sets_max = $sets_max,
                        t.rest_seconds_min = $rest_seconds_min,
                        t.rest_seconds_max = $rest_seconds_max,
                        t.intensity_percent_min = $intensity_percent_min,
                        t.intensity_percent_max = $intensity_percent_max,
                        t.rir_target = $rir_target,
                        t.description = $description
                    RETURN t.name, t.name_zh
                    """
                    result = session.run(query, old_name=old_name, **params)
                    record = result.single()
                    if record:
                        print(f"   ✅ 更新: {old_name} -> {record['t.name']} ({record['t.name_zh']})")
            
            # 3. 创建新节点（如果不存在）
            print("\n3. 创建新节点:")
            new_goals = ["body_shaping", "functional", "athletic_performance", "rehabilitation"]
            for goal_name in new_goals:
                params = TRAINING_GOAL_PARAMS[goal_name]
                # 检查是否已存在
                check_query = "MATCH (t:TrainingGoal {name: $name}) RETURN count(t) as count"
                result = session.run(check_query, name=goal_name)
                count = result.single()["count"]
                
                if count == 0:
                    create_query = """
                    CREATE (t:TrainingGoal {
                        name: $name,
                        name_zh: $name_zh,
                        reps_min: $reps_min,
                        reps_max: $reps_max,
                        sets_min: $sets_min,
                        sets_max: $sets_max,
                        rest_seconds_min: $rest_seconds_min,
                        rest_seconds_max: $rest_seconds_max,
                        intensity_percent_min: $intensity_percent_min,
                        intensity_percent_max: $intensity_percent_max,
                        rir_target: $rir_target,
                        description: $description
                    })
                    RETURN t.name, t.name_zh
                    """
                    result = session.run(create_query, **params)
                    record = result.single()
                    if record:
                        print(f"   ✅ 创建: {record['t.name']} ({record['t.name_zh']})")
                else:
                    # 更新已存在的节点
                    update_query = """
                    MATCH (t:TrainingGoal {name: $name})
                    SET t.name_zh = $name_zh,
                        t.reps_min = $reps_min,
                        t.reps_max = $reps_max,
                        t.sets_min = $sets_min,
                        t.sets_max = $sets_max,
                        t.rest_seconds_min = $rest_seconds_min,
                        t.rest_seconds_max = $rest_seconds_max,
                        t.intensity_percent_min = $intensity_percent_min,
                        t.intensity_percent_max = $intensity_percent_max,
                        t.rir_target = $rir_target,
                        t.description = $description
                    RETURN t.name, t.name_zh
                    """
                    result = session.run(update_query, **params)
                    record = result.single()
                    if record:
                        print(f"   ✅ 已存在，更新: {record['t.name']} ({record['t.name_zh']})")
            
            # 4. 验证结果
            print("\n4. 验证结果:")
            result = session.run("""
                MATCH (t:TrainingGoal) 
                RETURN t.name, t.name_zh, t.reps_min, t.reps_max, t.sets_min, t.sets_max
                ORDER BY t.name
            """)
            print(f"   {'名称':<25} {'中文':<12} {'次数':<10} {'组数':<10}")
            print("   " + "-" * 60)
            for record in result:
                name = record['t.name'] or 'N/A'
                name_zh = record['t.name_zh'] or 'N/A'
                reps = f"{record['t.reps_min']}-{record['t.reps_max']}" if record['t.reps_min'] else 'N/A'
                sets = f"{record['t.sets_min']}-{record['t.sets_max']}" if record['t.sets_min'] else 'N/A'
                print(f"   {name:<25} {name_zh:<12} {reps:<10} {sets:<10}")
            
            # 5. 统计
            result = session.run("MATCH (t:TrainingGoal) RETURN count(t) as count")
            count = result.single()["count"]
            print(f"\n✅ TrainingGoal节点总数: {count}")
            
    finally:
        driver.close()


if __name__ == "__main__":
    update_training_goals()
