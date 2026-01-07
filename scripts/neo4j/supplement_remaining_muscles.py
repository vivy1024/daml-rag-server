#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充剩余4个Muscle节点的训练数据

基于互联网查阅的运动解剖学和训练科学资料，为以下肌肉补充训练数据：
1. 手部 (Hands) - 手部内在肌群
2. 腹肌 (Abdominals) - 整个腹部肌群（包括腹直肌、腹斜肌、腹横肌）
3. 臀部 (Glutes) - 整个臀部肌群（包括臀大肌、臀中肌、臀小肌）
4. 颈部 (Neck) - 颈部肌群（包括颈屈肌和颈伸肌）

数据来源：
- Biology Insights (运动生理学)
- Quora专家回答
- 健身训练指南
"""

import os
from neo4j import GraphDatabase

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

# 补充的训练数据（基于专业资料）
SUPPLEMENTAL_MUSCLE_DATA = {
    "手部": {
        "name_en": "Hands",
        "training_data": {
            "training_frequency": "2-3次/周",
            "recovery_time": "48-72小时",
            "movement_patterns": ["握力", "手指屈伸", "精细动作"],
            "function": ["握力", "手部稳定", "精细运动控制"],
            "synergy_partners": [],
            "antagonist_partners": [],
            "group": "arm"
        },
        "source": "Biology Insights - Grip training frequency research",
        "notes": "手部内在肌群（鱼际肌、骨间肌等）恢复较快，可以较频繁训练，但需避免过度训练导致疲劳"
    },
    "腹肌": {
        "name_en": "Abdominals",
        "training_data": {
            "training_frequency": "3-4次/周",
            "recovery_time": "48小时",
            "movement_patterns": ["核心稳定", "躯干屈曲", "躯干旋转"],
            "function": ["核心稳定", "脊柱屈曲", "躯干旋转", "骨盆稳定"],
            "synergy_partners": [],
            "antagonist_partners": [],
            "group": "core"
        },
        "source": "Hey Wellness & Community Strength Austin - Core training frequency",
        "notes": "腹部肌群（腹直肌、腹斜肌、腹横肌）恢复较快，可以高频训练（3-4次/周），是核心稳定的关键"
    },
    "臀部": {
        "name_en": "Glutes",
        "training_data": {
            "training_frequency": "2-3次/周",
            "recovery_time": "48-72小时",
            "movement_patterns": ["髋关节主导", "深蹲", "硬拉", "臀桥"],
            "function": ["髋关节伸展", "大腿外展", "骨盆稳定", "髋关节旋转"],
            "synergy_partners": [],
            "antagonist_partners": [],
            "group": "hip"
        },
        "source": "Biology Insights & TTrening - Glute training frequency research",
        "notes": "臀部肌群（臀大肌、臀中肌、臀小肌）是人体最大的肌群之一，需要充足恢复时间（48-72小时）"
    },
    "颈部": {
        "name_en": "Neck",
        "training_data": {
            "training_frequency": "2-3次/周",
            "recovery_time": "48-72小时",
            "movement_patterns": ["颈部屈伸", "颈部侧屈", "颈部旋转"],
            "function": ["颈部屈曲", "颈部伸展", "头部稳定", "颈部侧屈"],
            "synergy_partners": [],
            "antagonist_partners": [],
            "group": "neck"
        },
        "source": "Biology Insights & Fight Sense - Neck training frequency research",
        "notes": "颈部肌群（颈屈肌、颈伸肌）需要谨慎训练，避免过度训练导致损伤，2-3次/周为最佳频率"
    }
}

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("🌐 补充剩余Muscle节点训练数据（基于互联网专业资料）")
print("=" * 80)

with driver.session() as session:
    updated_count = 0
    error_count = 0
    
    for muscle_name_zh, data in SUPPLEMENTAL_MUSCLE_DATA.items():
        muscle_name_en = data["name_en"]
        training_data = data["training_data"]
        source = data["source"]
        notes = data["notes"]
        
        print(f"\n📚 补充: {muscle_name_zh} ({muscle_name_en})")
        print(f"   数据来源: {source}")
        print(f"   说明: {notes}")
        
        try:
            # 更新Muscle节点
            query = """
            MATCH (m:Muscle)
            WHERE m.name_zh = $name_zh AND m.name_en = $name_en
            SET m += $training_data
            RETURN m.name_zh as name, m.name_en as name_en
            """
            
            result = session.run(query, {
                "name_zh": muscle_name_zh,
                "name_en": muscle_name_en,
                "training_data": training_data
            })
            
            record = result.single()
            if record:
                updated_count += 1
                print(f"   ✅ 成功更新: {record['name']} ({record['name_en']})")
            else:
                print(f"   ⚠️ 未找到节点: {muscle_name_zh} ({muscle_name_en})")
        
        except Exception as e:
            error_count += 1
            print(f"   ❌ 错误: {muscle_name_zh} - {e}")
    
    # 验证最终结果
    print("\n" + "=" * 80)
    print("📊 最终验证")
    print("=" * 80)
    
    result = session.run("MATCH (m:Muscle) RETURN count(m) as count")
    muscle_count = result.single()["count"]
    
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.training_frequency IS NOT NULL
        RETURN count(m) as count
    """)
    with_training_freq = result.single()["count"]
    
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.recovery_time IS NOT NULL
        RETURN count(m) as count
    """)
    with_recovery_time = result.single()["count"]
    
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.movement_patterns IS NOT NULL
        RETURN count(m) as count
    """)
    with_movement_patterns = result.single()["count"]
    
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.function IS NOT NULL
        RETURN count(m) as count
    """)
    with_function = result.single()["count"]
    
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.group IS NOT NULL
        RETURN count(m) as count
    """)
    with_group = result.single()["count"]
    
    print(f"   Muscle节点总数: {muscle_count}")
    print(f"   本次更新节点数: {updated_count}")
    print(f"   错误数量: {error_count}")
    print(f"   ")
    print(f"   最终字段覆盖率:")
    print(f"   - training_frequency: {with_training_freq}/{muscle_count} ({with_training_freq/muscle_count*100:.1f}%)")
    print(f"   - recovery_time: {with_recovery_time}/{muscle_count} ({with_recovery_time/muscle_count*100:.1f}%)")
    print(f"   - movement_patterns: {with_movement_patterns}/{muscle_count} ({with_movement_patterns/muscle_count*100:.1f}%)")
    print(f"   - function: {with_function}/{muscle_count} ({with_function/muscle_count*100:.1f}%)")
    print(f"   - group: {with_group}/{muscle_count} ({with_group/muscle_count*100:.1f}%)")
    
    if with_training_freq == muscle_count:
        print("\n   🎉 所有Muscle节点的训练数据字段已100%补充完成！")
    
    print("=" * 80)

driver.close()
