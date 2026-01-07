#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充Muscle节点训练数据字段

功能：
1. 从muscle_entities_comprehensive.json读取训练数据
2. 补充training_frequency、recovery_time、movement_patterns等字段到Muscle节点
3. 保持幂等性，可重复执行

字段说明：
- training_frequency: 训练频率 (如: "2-3次/周")
- recovery_time: 恢复时间 (如: "48小时")
- movement_patterns: 动作模式列表 (如: ["推", "夹胸"])
- function: 功能描述列表 (如: ["肩关节水平内收", "肩关节内旋"])
- synergy_partners: 协同肌群列表 (如: ["肱肌", "肱桡肌"])
- antagonist_partners: 对抗肌群列表 (如: ["肱三头肌"])
- group: 肌群分组 (如: "arm", "chest", "back")
"""

import os
import json
from neo4j import GraphDatabase

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

# 数据文件路径
DATA_FILE = "/app/data/muscle_data/muscle_entities_comprehensive.json"

# Neo4j细分肌肉名称 -> 数据文件通用名称映射表
# 映射原则：
# 1. 同一块肌肉的不同束/头 → 共享训练数据（因为共享神经支配和恢复时间）
# 2. 不同肌肉 → 不映射（需要独立的训练数据）
MUSCLE_NAME_MAPPING = {
    # ✅ 三角肌细分 -> 三角肌（同一块肌肉的三个束）
    "三角肌前束": "三角肌",
    "三角肌中束": "三角肌",
    "三角肌后束": "三角肌",
    "肩前部": "三角肌",  # 通用名称，主要指三角肌前束
    "肩后部": "三角肌",  # 通用名称，主要指三角肌后束
    "肩部": "三角肌",    # 通用名称，指整个三角肌
    
    # ✅ 斜方肌细分 -> 斜方肌（同一块肌肉的三个区域）
    "上斜方肌": "斜方肌",
    "中斜方肌": "斜方肌",
    "下斜方肌": "斜方肌",
    
    # ✅ 胸肌细分 -> 胸大肌（同一块肌肉的不同区域）
    "上胸肌": "胸大肌",
    "中下胸肌": "胸大肌",
    "胸肌": "胸大肌",  # 通用名称，通常指胸大肌
    
    # ✅ 腹直肌细分 -> 腹直肌（同一块肌肉的不同区域）
    "上腹肌": "腹直肌",
    "下腹肌": "腹直肌",
    # 注意："腹肌"不映射，因为可能指整个核心肌群
    
    # ✅ 肱二头肌细分 -> 肱二头肌（同一块肌肉的两个头）
    "肱二头肌长头": "肱二头肌",
    "肱二头肌短头": "肱二头肌",
    
    # ✅ 肱三头肌细分 -> 肱三头肌（同一块肌肉的三个头）
    "肱三头肌长头": "肱三头肌",
    "肱三头肌外侧头": "肱三头肌",
    "肱三头肌内侧头": "肱三头肌",
    
    # ✅ 股四头肌细分 -> 股四头肌（股四头肌包含四个头，股直肌是其中之一）
    "股四头肌内侧": "股四头肌",
    "股四头肌外侧": "股四头肌",
    "股直肌": "股四头肌",
    
    # ✅ 腿后肌群细分 -> 腘绳肌（腘绳肌是腿后肌群的学名）
    "腿后肌群": "腘绳肌",
    "腿后肌群内侧": "腘绳肌",
    "腿后肌群外侧": "腘绳肌",
    
    # ✅ 前臂细分 -> 前臂（前臂屈肌和伸肌都属于前臂肌群）
    "腕屈肌": "前臂",
    "腕伸肌": "前臂",
    
    # ✅ 其他合理映射
    "大腿内侧": "腹股沟",  # 大腿内侧主要是内收肌群，数据文件中称为"腹股沟"
    "下背部": "竖脊肌",    # 下背部主要是竖脊肌
    
    # ❌ 以下不映射，需要查阅互联网补充独立数据：
    # "臀部" - 包括臀大肌、臀中肌、臀小肌，不能只映射到臀大肌
    # "手部" - 手部肌肉和前臂肌肉不同
    # "颈部" - 包括颈屈肌和颈伸肌，不能只映射到一个
    # "腹肌" - 可能指整个核心肌群，不只是腹直肌
    # "足部" - 独立的肌肉群
}

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("📊 补充Muscle节点训练数据字段")
print("=" * 80)

# 加载数据
print(f"\n1️⃣ 加载数据文件: {DATA_FILE}")
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    muscle_data = json.load(f)
print(f"   ✅ 加载了 {len(muscle_data)} 个肌肉数据")

with driver.session() as session:
    # 2. 查询当前Muscle节点
    print("\n2️⃣ 查询当前Muscle节点")
    result = session.run("MATCH (m:Muscle) RETURN count(m) as count")
    muscle_count = result.single()["count"]
    print(f"   当前Muscle节点数量: {muscle_count}")
    
    # 3. 补充训练数据字段
    print("\n3️⃣ 补充训练数据字段（使用名称映射）")
    updated_count = 0
    skipped_count = 0
    error_count = 0
    unmatched_muscles = []  # 记录未匹配的肌肉
    
    # 创建数据文件中肌肉名称的索引
    muscle_data_index = {}
    for muscle in muscle_data:
        muscle_data_index[muscle.get("name")] = muscle
        muscle_data_index[muscle.get("nameEn")] = muscle
    
    # 查询所有Neo4j中的Muscle节点
    result = session.run("MATCH (m:Muscle) RETURN m.name_zh as name_zh, m.name_en as name_en ORDER BY m.name_zh")
    neo4j_muscles = [(r["name_zh"], r["name_en"]) for r in result]
    
    for name_zh, name_en in neo4j_muscles:
        # 尝试直接匹配
        matched_muscle = muscle_data_index.get(name_zh) or muscle_data_index.get(name_en)
        
        # 如果直接匹配失败，尝试使用映射表
        if not matched_muscle and name_zh in MUSCLE_NAME_MAPPING:
            mapped_name = MUSCLE_NAME_MAPPING[name_zh]
            matched_muscle = muscle_data_index.get(mapped_name)
            if matched_muscle:
                print(f"   🔄 映射: {name_zh} → {mapped_name}")
        
        if not matched_muscle:
            unmatched_muscles.append((name_zh, name_en))
            skipped_count += 1
            print(f"   ⚠️ 未找到匹配: {name_zh} ({name_en})")
            continue
        
        # 提取训练数据字段
        properties = matched_muscle.get("properties", {})
        training_data = {
            "training_frequency": properties.get("training_frequency"),
            "recovery_time": properties.get("recovery_time"),
            "movement_patterns": properties.get("movement_patterns", []),
            "function": properties.get("function", []),
            "synergy_partners": properties.get("synergy_partners", []),
            "antagonist_partners": properties.get("antagonist_partners", []),
            "group": properties.get("group")
        }
        
        # 过滤掉None值
        training_data = {k: v for k, v in training_data.items() if v is not None}
        
        if not training_data:
            skipped_count += 1
            continue
        
        try:
            # 更新Muscle节点
            query = """
            MATCH (m:Muscle)
            WHERE m.name_zh = $name_zh AND m.name_en = $name_en
            SET m += $training_data
            RETURN m.name_zh as name, m.name_en as name_en
            """
            
            result = session.run(query, {
                "name_zh": name_zh,
                "name_en": name_en,
                "training_data": training_data
            })
            
            record = result.single()
            if record:
                updated_count += 1
                print(f"   ✅ 更新: {record['name']} ({record['name_en']})")
        
        except Exception as e:
            error_count += 1
            print(f"   ❌ 错误: {name_zh} - {e}")
    
    # 4. 验证结果
    print("\n4️⃣ 验证补充结果")
    
    # 检查有training_frequency字段的节点数量
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.training_frequency IS NOT NULL
        RETURN count(m) as count
    """)
    with_training_freq = result.single()["count"]
    print(f"   有training_frequency字段的节点: {with_training_freq}")
    
    # 检查有recovery_time字段的节点数量
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.recovery_time IS NOT NULL
        RETURN count(m) as count
    """)
    with_recovery_time = result.single()["count"]
    print(f"   有recovery_time字段的节点: {with_recovery_time}")
    
    # 检查有movement_patterns字段的节点数量
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.movement_patterns IS NOT NULL
        RETURN count(m) as count
    """)
    with_movement_patterns = result.single()["count"]
    print(f"   有movement_patterns字段的节点: {with_movement_patterns}")
    
    # 检查有function字段的节点数量
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.function IS NOT NULL
        RETURN count(m) as count
    """)
    with_function = result.single()["count"]
    print(f"   有function字段的节点: {with_function}")
    
    # 检查有group字段的节点数量
    result = session.run("""
        MATCH (m:Muscle)
        WHERE m.group IS NOT NULL
        RETURN count(m) as count
    """)
    with_group = result.single()["count"]
    print(f"   有group字段的节点: {with_group}")
    
    # 5. 总结
    print("\n" + "=" * 80)
    print("📋 补充总结")
    print("=" * 80)
    print(f"   Neo4j中的Muscle节点: {muscle_count}")
    print(f"   数据文件中的肌肉数量: {len(muscle_data)}")
    print(f"   成功更新的节点: {updated_count}")
    print(f"   跳过的节点: {skipped_count}")
    print(f"   错误数量: {error_count}")
    print(f"   ")
    print(f"   字段覆盖率:")
    print(f"   - training_frequency: {with_training_freq}/{muscle_count} ({with_training_freq/muscle_count*100:.1f}%)")
    print(f"   - recovery_time: {with_recovery_time}/{muscle_count} ({with_recovery_time/muscle_count*100:.1f}%)")
    print(f"   - movement_patterns: {with_movement_patterns}/{muscle_count} ({with_movement_patterns/muscle_count*100:.1f}%)")
    print(f"   - function: {with_function}/{muscle_count} ({with_function/muscle_count*100:.1f}%)")
    print(f"   - group: {with_group}/{muscle_count} ({with_group/muscle_count*100:.1f}%)")
    
    # 6. 列出需要互联网补充的肌肉
    if unmatched_muscles:
        print("\n" + "=" * 80)
        print("🌐 需要查阅互联网补充训练数据的肌肉")
        print("=" * 80)
        print(f"   共 {len(unmatched_muscles)} 个肌肉需要补充：")
        for i, (name_zh, name_en) in enumerate(unmatched_muscles, 1):
            print(f"   {i}. {name_zh:15s} ({name_en})")
        print("\n   建议：")
        print("   - 这些肌肉在数据文件中没有对应的训练数据")
        print("   - 需要查阅运动解剖学资料或咨询专业教练")
        print("   - 补充字段：training_frequency, recovery_time, movement_patterns, function, group")
    
    print("=" * 80)

driver.close()
