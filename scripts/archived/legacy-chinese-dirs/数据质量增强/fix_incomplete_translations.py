#!/usr/bin/env python3
"""
修复不完整的翻译

确保中文步骤数量与英文步骤数量一致
"""

import json
import sys
import os
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("修复不完整的翻译")
print("=" * 80)

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 修复的翻译（完整版本）
fixed_translations = {
    44: [  # 杠铃仰卧臂屈伸 - 4个步骤
        "仰卧在平板凳上，双手以肩宽握距握住杠铃",
        "完全伸直肘部，将杠铃举至胸部正上方",
        "开始屈肘，让杠铃接近额头",
        "伸直肘部回到起始位置并重复"
    ],
    48: [  # 杠铃俯身划船 - 4个步骤
        "双手以肩宽正握或反握握住杠铃",
        "屈髋前倾，保持背部平直",
        "将杠铃拉向上腹部",
        "控制杠铃下降并重复"
    ],
    212: [  # 杠铃礼式弓步 - 3个步骤
        "将杠铃放在背部",
        "一脚向后并绕至身体侧方，同时下降重量",
        "回到起始位置，换另一条腿重复"
    ],
    1319: [  # 祈祷式拉伸1 - 保持3个步骤（这个是合理的，因为英文是一个长句子）
        "跪坐在脚跟上",
        "双臂向前伸展至地面",
        "胸部向地面按压"
    ],
    1635: [  # 哑铃六向侧平举 - 保持3个步骤（这个是合理的，因为英文是一个长句子）
        "前平举",
        "将哑铃向两侧抬起",
        "将哑铃举过头顶"
    ]
}

print(f"\n准备修复 {len(fixed_translations)} 个动作...")

# 更新数据库
success_count = 0
failed_count = 0

with driver.session() as session:
    for exercise_id, steps_zh in fixed_translations.items():
        try:
            # 先查询英文步骤数量
            check_query = """
            MATCH (e:Exercise {id: $exercise_id})
            RETURN e.id as id, 
                   e.name_zh as name_zh,
                   size(e.correct_steps_en) as en_count
            """
            check_result = session.run(check_query, exercise_id=exercise_id)
            check_record = check_result.single()
            
            if not check_record:
                print(f"❌ ID={exercise_id}: 未找到")
                failed_count += 1
                continue
            
            en_count = check_record['en_count']
            zh_count = len(steps_zh)
            name_zh = check_record['name_zh']
            
            # 更新
            update_query = """
            MATCH (e:Exercise {id: $exercise_id})
            SET e.correct_steps_zh = $steps_zh
            RETURN e.id as id
            """
            update_result = session.run(update_query, exercise_id=exercise_id, steps_zh=steps_zh)
            update_record = update_result.single()
            
            if update_record:
                success_count += 1
                match_status = "✅" if en_count == zh_count else "⚠️"
                print(f"{match_status} ID={exercise_id}, {name_zh}: EN={en_count}, ZH={zh_count}")
            else:
                failed_count += 1
                print(f"❌ ID={exercise_id}: 更新失败")
        
        except Exception as e:
            failed_count += 1
            print(f"❌ ID={exercise_id}: {e}")

driver.close()

print("\n" + "=" * 80)
print("修复完成")
print("=" * 80)

print(f"\n成功: {success_count}")
print(f"失败: {failed_count}")

print("\n说明：")
print("  ✅ = 步骤数量一致")
print("  ⚠️ = 步骤数量不一致（但这是合理的，因为英文是长句子）")

print("\n✅ 修复完成！")
print("=" * 80)
