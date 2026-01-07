#!/usr/bin/env python3
"""
创建TrainingParams节点 - 基于训练量地标体系
基于Mike Israetel博士的Volume Landmarks理论

训练量地标说明:
- MV (Maintenance Volume): 维持训练量 - 保持当前肌肉水平的最低组数
- MEV (Minimum Effective Volume): 最小有效训练量 - 开始产生进步的最低组数
- MAV (Maximum Adaptive Volume): 最大适应训练量 - 最佳进步的训练量范围
- MRV (Maximum Recoverable Volume): 最大可恢复训练量 - 能恢复的最大组数上限

节点设计: 8个训练目标 × 4个训练水平 = 32个TrainingParams节点

作者: 薛小川
日期: 2026-01-05
"""

import os
import sys
from neo4j import GraphDatabase

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "build_body_2024")

# 训练水平定义
TRAINING_LEVELS = [
    {"name": "beginner", "name_zh": "初学者", "experience_months": "0-6"},
    {"name": "novice", "name_zh": "新手", "experience_months": "6-18"},
    {"name": "intermediate", "name_zh": "中级", "experience_months": "18-36"},
    {"name": "advanced", "name_zh": "高级", "experience_months": "36+"},
]

# 训练目标参数配置 - 基于训练量地标体系
# 每个目标包含4个水平的参数配置
TRAINING_PARAMS = {
    # ==================== 增肌 (Hypertrophy) ====================
    "hypertrophy": {
        "goal_zh": "增肌",
        "description": "追求肌肉体积增长，强调代谢压力和机械张力",
        "levels": {
            "beginner": {
                "mv_sets": 4, "mev_sets": 6, "mav_sets_min": 8, "mav_sets_max": 12, "mrv_sets": 16,
                "reps_min": 10, "reps_max": 15, "rir_target": 3,
                "intensity_min": 55, "intensity_max": 65,
                "rest_min": 90, "rest_max": 120,
                "frequency_min": 2, "frequency_max": 3,
                "progression_rate": "slow", "deload_frequency": 8,
            },
            "novice": {
                "mv_sets": 6, "mev_sets": 8, "mav_sets_min": 10, "mav_sets_max": 16, "mrv_sets": 20,
                "reps_min": 8, "reps_max": 12, "rir_target": 2,
                "intensity_min": 60, "intensity_max": 70,
                "rest_min": 75, "rest_max": 105,
                "frequency_min": 2, "frequency_max": 3,
                "progression_rate": "moderate", "deload_frequency": 6,
            },
            "intermediate": {
                "mv_sets": 8, "mev_sets": 10, "mav_sets_min": 14, "mav_sets_max": 20, "mrv_sets": 25,
                "reps_min": 6, "reps_max": 12, "rir_target": 1,
                "intensity_min": 65, "intensity_max": 75,
                "rest_min": 60, "rest_max": 90,
                "frequency_min": 2, "frequency_max": 4,
                "progression_rate": "moderate", "deload_frequency": 5,
            },
            "advanced": {
                "mv_sets": 10, "mev_sets": 12, "mav_sets_min": 16, "mav_sets_max": 22, "mrv_sets": 30,
                "reps_min": 6, "reps_max": 12, "rir_target": 0,
                "intensity_min": 65, "intensity_max": 80,
                "rest_min": 60, "rest_max": 90,
                "frequency_min": 2, "frequency_max": 4,
                "progression_rate": "slow", "deload_frequency": 4,
            },
        },
    },

    # ==================== 减脂 (Fat Loss) ====================
    "fat_loss": {
        "goal_zh": "减脂",
        "description": "追求脂肪减少，强调高心率和热量消耗",
        "levels": {
            "beginner": {
                "mv_sets": 3, "mev_sets": 5, "mav_sets_min": 6, "mav_sets_max": 10, "mrv_sets": 14,
                "reps_min": 15, "reps_max": 20, "rir_target": 4,
                "intensity_min": 45, "intensity_max": 55,
                "rest_min": 30, "rest_max": 45,
                "frequency_min": 3, "frequency_max": 4,
                "progression_rate": "moderate", "deload_frequency": 6,
            },
            "novice": {
                "mv_sets": 4, "mev_sets": 6, "mav_sets_min": 8, "mav_sets_max": 14, "mrv_sets": 18,
                "reps_min": 12, "reps_max": 18, "rir_target": 3,
                "intensity_min": 50, "intensity_max": 60,
                "rest_min": 30, "rest_max": 45,
                "frequency_min": 3, "frequency_max": 5,
                "progression_rate": "moderate", "deload_frequency": 5,
            },
            "intermediate": {
                "mv_sets": 5, "mev_sets": 8, "mav_sets_min": 10, "mav_sets_max": 16, "mrv_sets": 22,
                "reps_min": 12, "reps_max": 20, "rir_target": 2,
                "intensity_min": 50, "intensity_max": 65,
                "rest_min": 25, "rest_max": 40,
                "frequency_min": 4, "frequency_max": 5,
                "progression_rate": "fast", "deload_frequency": 4,
            },
            "advanced": {
                "mv_sets": 6, "mev_sets": 10, "mav_sets_min": 12, "mav_sets_max": 18, "mrv_sets": 25,
                "reps_min": 12, "reps_max": 20, "rir_target": 1,
                "intensity_min": 50, "intensity_max": 65,
                "rest_min": 20, "rest_max": 35,
                "frequency_min": 4, "frequency_max": 6,
                "progression_rate": "fast", "deload_frequency": 4,
            },
        },
    },

    # ==================== 增强力量 (Strength) ====================
    "strength": {
        "goal_zh": "增强力量",
        "description": "追求最大力量提升，强调神经适应和高强度",
        "levels": {
            "beginner": {
                "mv_sets": 3, "mev_sets": 4, "mav_sets_min": 5, "mav_sets_max": 8, "mrv_sets": 12,
                "reps_min": 5, "reps_max": 8, "rir_target": 3,
                "intensity_min": 70, "intensity_max": 80,
                "rest_min": 150, "rest_max": 210,
                "frequency_min": 2, "frequency_max": 3,
                "progression_rate": "slow", "deload_frequency": 6,
            },
            "novice": {
                "mv_sets": 4, "mev_sets": 5, "mav_sets_min": 6, "mav_sets_max": 10, "mrv_sets": 15,
                "reps_min": 3, "reps_max": 6, "rir_target": 2,
                "intensity_min": 75, "intensity_max": 85,
                "rest_min": 180, "rest_max": 240,
                "frequency_min": 2, "frequency_max": 3,
                "progression_rate": "moderate", "deload_frequency": 5,
            },
            "intermediate": {
                "mv_sets": 5, "mev_sets": 6, "mav_sets_min": 8, "mav_sets_max": 12, "mrv_sets": 18,
                "reps_min": 1, "reps_max": 5, "rir_target": 1,
                "intensity_min": 80, "intensity_max": 92,
                "rest_min": 180, "rest_max": 300,
                "frequency_min": 2, "frequency_max": 4,
                "progression_rate": "slow", "deload_frequency": 4,
            },
            "advanced": {
                "mv_sets": 6, "mev_sets": 8, "mav_sets_min": 10, "mav_sets_max": 14, "mrv_sets": 20,
                "reps_min": 1, "reps_max": 5, "rir_target": 0,
                "intensity_min": 85, "intensity_max": 100,
                "rest_min": 180, "rest_max": 360,
                "frequency_min": 2, "frequency_max": 4,
                "progression_rate": "very_slow", "deload_frequency": 3,
            },
        },
    },

    # ==================== 提高耐力 (Endurance) ====================
    "endurance": {
        "goal_zh": "提高耐力",
        "description": "追求肌肉耐力和心肺适应，强调高次数低休息",
        "levels": {
            "beginner": {
                "mv_sets": 2, "mev_sets": 3, "mav_sets_min": 4, "mav_sets_max": 6, "mrv_sets": 10,
                "reps_min": 15, "reps_max": 20, "rir_target": 4,
                "intensity_min": 35, "intensity_max": 50,
                "rest_min": 20, "rest_max": 40,
                "frequency_min": 3, "frequency_max": 4,
                "progression_rate": "moderate", "deload_frequency": 6,
            },
            "novice": {
                "mv_sets": 2, "mev_sets": 4, "mav_sets_min": 5, "mav_sets_max": 8, "mrv_sets": 12,
                "reps_min": 18, "reps_max": 25, "rir_target": 3,
                "intensity_min": 40, "intensity_max": 55,
                "rest_min": 15, "rest_max": 35,
                "frequency_min": 3, "frequency_max": 5,
                "progression_rate": "moderate", "deload_frequency": 5,
            },
            "intermediate": {
                "mv_sets": 3, "mev_sets": 5, "mav_sets_min": 6, "mav_sets_max": 10, "mrv_sets": 15,
                "reps_min": 20, "reps_max": 30, "rir_target": 2,
                "intensity_min": 40, "intensity_max": 60,
                "rest_min": 10, "rest_max": 30,
                "frequency_min": 4, "frequency_max": 5,
                "progression_rate": "fast", "deload_frequency": 4,
            },
            "advanced": {
                "mv_sets": 4, "mev_sets": 6, "mav_sets_min": 8, "mav_sets_max": 12, "mrv_sets": 18,
                "reps_min": 25, "reps_max": 40, "rir_target": 1,
                "intensity_min": 40, "intensity_max": 60,
                "rest_min": 10, "rest_max": 25,
                "frequency_min": 4, "frequency_max": 6,
                "progression_rate": "fast", "deload_frequency": 4,
            },
        },
    },

    # ==================== 塑形 (Body Shaping) ====================
    "body_shaping": {
        "goal_zh": "塑形",
        "description": "追求肌肉线条和体型改善，平衡增肌和减脂",
        "levels": {
            "beginner": {
                "mv_sets": 3, "mev_sets": 5, "mav_sets_min": 6, "mav_sets_max": 10, "mrv_sets": 14,
                "reps_min": 12, "reps_max": 18, "rir_target": 3,
                "intensity_min": 50, "intensity_max": 60,
                "rest_min": 45, "rest_max": 75,
                "frequency_min": 3, "frequency_max": 4,
                "progression_rate": "moderate", "deload_frequency": 6,
            },
            "novice": {
                "mv_sets": 4, "mev_sets": 6, "mav_sets_min": 8, "mav_sets_max": 14, "mrv_sets": 18,
                "reps_min": 10, "reps_max": 15, "rir_target": 2,
                "intensity_min": 55, "intensity_max": 65,
                "rest_min": 45, "rest_max": 70,
                "frequency_min": 3, "frequency_max": 4,
                "progression_rate": "moderate", "deload_frequency": 5,
            },
            "intermediate": {
                "mv_sets": 5, "mev_sets": 8, "mav_sets_min": 10, "mav_sets_max": 16, "mrv_sets": 22,
                "reps_min": 10, "reps_max": 15, "rir_target": 1,
                "intensity_min": 60, "intensity_max": 70,
                "rest_min": 40, "rest_max": 60,
                "frequency_min": 3, "frequency_max": 5,
                "progression_rate": "moderate", "deload_frequency": 4,
            },
            "advanced": {
                "mv_sets": 6, "mev_sets": 10, "mav_sets_min": 12, "mav_sets_max": 18, "mrv_sets": 25,
                "reps_min": 10, "reps_max": 15, "rir_target": 0,
                "intensity_min": 60, "intensity_max": 70,
                "rest_min": 35, "rest_max": 55,
                "frequency_min": 4, "frequency_max": 5,
                "progression_rate": "slow", "deload_frequency": 4,
            },
        },
    },

    # ==================== 功能性训练 (Functional) ====================
    "functional": {
        "goal_zh": "功能性训练",
        "description": "追求日常功能和运动能力，强调多平面动作和协调性",
        "levels": {
            "beginner": {
                "mv_sets": 2, "mev_sets": 4, "mav_sets_min": 5, "mav_sets_max": 8, "mrv_sets": 12,
                "reps_min": 10, "reps_max": 15, "rir_target": 3,
                "intensity_min": 45, "intensity_max": 60,
                "rest_min": 60, "rest_max": 90,
                "frequency_min": 2, "frequency_max": 3,
                "progression_rate": "moderate", "deload_frequency": 6,
            },
            "novice": {
                "mv_sets": 3, "mev_sets": 5, "mav_sets_min": 6, "mav_sets_max": 10, "mrv_sets": 15,
                "reps_min": 8, "reps_max": 15, "rir_target": 2,
                "intensity_min": 50, "intensity_max": 65,
                "rest_min": 50, "rest_max": 80,
                "frequency_min": 3, "frequency_max": 4,
                "progression_rate": "moderate", "deload_frequency": 5,
            },
            "intermediate": {
                "mv_sets": 4, "mev_sets": 6, "mav_sets_min": 8, "mav_sets_max": 12, "mrv_sets": 18,
                "reps_min": 8, "reps_max": 15, "rir_target": 1,
                "intensity_min": 50, "intensity_max": 70,
                "rest_min": 45, "rest_max": 75,
                "frequency_min": 3, "frequency_max": 5,
                "progression_rate": "moderate", "deload_frequency": 4,
            },
            "advanced": {
                "mv_sets": 5, "mev_sets": 8, "mav_sets_min": 10, "mav_sets_max": 14, "mrv_sets": 20,
                "reps_min": 8, "reps_max": 15, "rir_target": 0,
                "intensity_min": 50, "intensity_max": 70,
                "rest_min": 40, "rest_max": 70,
                "frequency_min": 3, "frequency_max": 5,
                "progression_rate": "slow", "deload_frequency": 4,
            },
        },
    },

    # ==================== 运动表现 (Athletic Performance) ====================
    "athletic_performance": {
        "goal_zh": "运动表现",
        "description": "追求爆发力和运动专项能力，强调速度和力量输出",
        "levels": {
            "beginner": {
                "mv_sets": 3, "mev_sets": 4, "mav_sets_min": 5, "mav_sets_max": 8, "mrv_sets": 12,
                "reps_min": 6, "reps_max": 10, "rir_target": 3,
                "intensity_min": 60, "intensity_max": 75,
                "rest_min": 90, "rest_max": 150,
                "frequency_min": 2, "frequency_max": 3,
                "progression_rate": "slow", "deload_frequency": 6,
            },
            "novice": {
                "mv_sets": 4, "mev_sets": 5, "mav_sets_min": 6, "mav_sets_max": 10, "mrv_sets": 15,
                "reps_min": 4, "reps_max": 8, "rir_target": 2,
                "intensity_min": 65, "intensity_max": 80,
                "rest_min": 100, "rest_max": 180,
                "frequency_min": 2, "frequency_max": 4,
                "progression_rate": "moderate", "deload_frequency": 5,
            },
            "intermediate": {
                "mv_sets": 5, "mev_sets": 6, "mav_sets_min": 8, "mav_sets_max": 12, "mrv_sets": 18,
                "reps_min": 3, "reps_max": 8, "rir_target": 1,
                "intensity_min": 70, "intensity_max": 90,
                "rest_min": 120, "rest_max": 210,
                "frequency_min": 3, "frequency_max": 4,
                "progression_rate": "moderate", "deload_frequency": 4,
            },
            "advanced": {
                "mv_sets": 6, "mev_sets": 8, "mav_sets_min": 10, "mav_sets_max": 14, "mrv_sets": 20,
                "reps_min": 3, "reps_max": 8, "rir_target": 0,
                "intensity_min": 70, "intensity_max": 95,
                "rest_min": 120, "rest_max": 240,
                "frequency_min": 3, "frequency_max": 5,
                "progression_rate": "slow", "deload_frequency": 3,
            },
        },
    },

    # ==================== 康复训练 (Rehabilitation) ====================
    "rehabilitation": {
        "goal_zh": "康复训练",
        "description": "追求伤后恢复和关节稳定，强调控制和安全",
        "levels": {
            "beginner": {
                "mv_sets": 2, "mev_sets": 3, "mav_sets_min": 4, "mav_sets_max": 6, "mrv_sets": 8,
                "reps_min": 15, "reps_max": 20, "rir_target": 5,
                "intensity_min": 25, "intensity_max": 40,
                "rest_min": 60, "rest_max": 120,
                "frequency_min": 2, "frequency_max": 3,
                "progression_rate": "very_slow", "deload_frequency": 8,
            },
            "novice": {
                "mv_sets": 2, "mev_sets": 3, "mav_sets_min": 4, "mav_sets_max": 7, "mrv_sets": 10,
                "reps_min": 12, "reps_max": 18, "rir_target": 4,
                "intensity_min": 30, "intensity_max": 45,
                "rest_min": 60, "rest_max": 100,
                "frequency_min": 2, "frequency_max": 4,
                "progression_rate": "slow", "deload_frequency": 6,
            },
            "intermediate": {
                "mv_sets": 3, "mev_sets": 4, "mav_sets_min": 5, "mav_sets_max": 8, "mrv_sets": 12,
                "reps_min": 12, "reps_max": 18, "rir_target": 3,
                "intensity_min": 35, "intensity_max": 50,
                "rest_min": 50, "rest_max": 90,
                "frequency_min": 3, "frequency_max": 4,
                "progression_rate": "slow", "deload_frequency": 5,
            },
            "advanced": {
                "mv_sets": 3, "mev_sets": 5, "mav_sets_min": 6, "mav_sets_max": 10, "mrv_sets": 14,
                "reps_min": 12, "reps_max": 20, "rir_target": 2,
                "intensity_min": 35, "intensity_max": 55,
                "rest_min": 45, "rest_max": 80,
                "frequency_min": 3, "frequency_max": 5,
                "progression_rate": "slow", "deload_frequency": 4,
            },
        },
    },
}


def create_training_params_nodes(driver):
    """创建TrainingParams节点"""
    
    with driver.session() as session:
        # 先删除已有的TrainingParams节点
        result = session.run("MATCH (p:TrainingParams) DETACH DELETE p RETURN count(p) as deleted")
        deleted = result.single()["deleted"]
        if deleted > 0:
            print(f"已删除 {deleted} 个旧的TrainingParams节点")
        
        created_count = 0
        
        for goal_name, goal_data in TRAINING_PARAMS.items():
            goal_zh = goal_data["goal_zh"]
            description = goal_data["description"]
            
            for level_name, params in goal_data["levels"].items():
                # 获取水平中文名
                level_zh = next(
                    (l["name_zh"] for l in TRAINING_LEVELS if l["name"] == level_name),
                    level_name
                )
                
                # 创建节点
                query = """
                CREATE (p:TrainingParams {
                    goal: $goal,
                    goal_zh: $goal_zh,
                    level: $level,
                    level_zh: $level_zh,
                    description: $description,
                    
                    mv_sets: $mv_sets,
                    mev_sets: $mev_sets,
                    mav_sets_min: $mav_sets_min,
                    mav_sets_max: $mav_sets_max,
                    mrv_sets: $mrv_sets,
                    
                    reps_min: $reps_min,
                    reps_max: $reps_max,
                    rir_target: $rir_target,
                    
                    intensity_min: $intensity_min,
                    intensity_max: $intensity_max,
                    
                    rest_min: $rest_min,
                    rest_max: $rest_max,
                    
                    frequency_min: $frequency_min,
                    frequency_max: $frequency_max,
                    
                    progression_rate: $progression_rate,
                    deload_frequency: $deload_frequency
                })
                RETURN p
                """
                
                session.run(query, 
                    goal=goal_name,
                    goal_zh=goal_zh,
                    level=level_name,
                    level_zh=level_zh,
                    description=description,
                    **params
                )
                
                created_count += 1
                print(f"  创建: {goal_zh} + {level_zh}")
        
        print(f"\n✅ 共创建 {created_count} 个TrainingParams节点")
        return created_count


def create_relationships(driver):
    """创建TrainingParams与TrainingGoal、TrainingLevel的关系"""
    
    with driver.session() as session:
        # 创建与TrainingGoal的关系
        result = session.run("""
            MATCH (p:TrainingParams), (g:TrainingGoal)
            WHERE p.goal = g.name
            MERGE (p)-[r:FOR_GOAL]->(g)
            RETURN count(r) as created
        """)
        goal_rels = result.single()["created"]
        print(f"创建 {goal_rels} 个 FOR_GOAL 关系")
        
        # 创建与TrainingLevel的关系
        result = session.run("""
            MATCH (p:TrainingParams), (l:TrainingLevel)
            WHERE p.level = l.name
            MERGE (p)-[r:FOR_LEVEL]->(l)
            RETURN count(r) as created
        """)
        level_rels = result.single()["created"]
        print(f"创建 {level_rels} 个 FOR_LEVEL 关系")
        
        return goal_rels, level_rels


def verify_nodes(driver):
    """验证创建的节点"""
    
    with driver.session() as session:
        # 统计节点数量
        result = session.run("MATCH (p:TrainingParams) RETURN count(p) as count")
        count = result.single()["count"]
        print(f"\n📊 TrainingParams节点总数: {count}")
        
        # 按目标统计
        result = session.run("""
            MATCH (p:TrainingParams)
            RETURN p.goal_zh as goal, count(p) as count
            ORDER BY p.goal
        """)
        print("\n按训练目标统计:")
        for record in result:
            print(f"  {record['goal']}: {record['count']}个")
        
        # 按水平统计
        result = session.run("""
            MATCH (p:TrainingParams)
            RETURN p.level_zh as level, count(p) as count
            ORDER BY p.level
        """)
        print("\n按训练水平统计:")
        for record in result:
            print(f"  {record['level']}: {record['count']}个")
        
        # 示例查询
        print("\n📋 示例查询 - 增肌+中级:")
        result = session.run("""
            MATCH (p:TrainingParams {goal: 'hypertrophy', level: 'intermediate'})
            RETURN p.goal_zh, p.level_zh, 
                   p.mav_sets_min, p.mav_sets_max, 
                   p.reps_min, p.reps_max,
                   p.intensity_min, p.intensity_max,
                   p.rir_target
        """)
        for record in result:
            print(f"  目标: {record['p.goal_zh']}, 水平: {record['p.level_zh']}")
            print(f"  MAV组数: {record['p.mav_sets_min']}-{record['p.mav_sets_max']}组/周/肌群")
            print(f"  次数: {record['p.reps_min']}-{record['p.reps_max']}次/组")
            print(f"  强度: {record['p.intensity_min']}-{record['p.intensity_max']}% 1RM")
            print(f"  RIR: {record['p.rir_target']}")


def main():
    print("=" * 60)
    print("创建TrainingParams节点 - 基于训练量地标体系")
    print("=" * 60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # 创建节点
        print("\n📦 创建TrainingParams节点...")
        create_training_params_nodes(driver)
        
        # 创建关系
        print("\n🔗 创建关系...")
        create_relationships(driver)
        
        # 验证
        verify_nodes(driver)
        
        print("\n" + "=" * 60)
        print("✅ TrainingParams节点创建完成!")
        print("=" * 60)
        
    finally:
        driver.close()


if __name__ == "__main__":
    main()
