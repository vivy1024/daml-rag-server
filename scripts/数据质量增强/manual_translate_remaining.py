#!/usr/bin/env python3
"""
手动翻译剩余的36个动作

由AI助手直接提供高质量翻译
"""

import json
import sys
import os
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("手动翻译剩余动作")
print("=" * 80)

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 手动翻译映射（高质量翻译）
manual_translations = {
    8: [  # 杠铃深蹲
        "双脚与肩同宽站立，杠铃放在斜方肌上部",
        "保持背部挺直，屈髋屈膝下蹲至大腿平行地面",
        "通过脚跟发力，推动身体回到起始位置",
        "重复动作，保持核心稳定"
    ],
    27: [  # 杠铃直腿硬拉
        "双脚与髋同宽站立，双手正握杠铃",
        "保持膝盖微屈，背部平直",
        "屈髋向前倾，杠铃沿腿部下降",
        "感受腘绳肌拉伸后，收缩臀部和腘绳肌回到起始位置",
        "重复动作"
    ],
    39: [  # 杠铃硬拉
        "双脚与髋同宽站立，杠铃贴近小腿",
        "屈髋屈膝，双手正握杠铃，背部保持平直",
        "同时伸展髋关节和膝关节，将杠铃拉起",
        "站直后，控制杠铃下降回到起始位置"
    ],
    45: [  # 坐姿哑铃推举
        "坐在有靠背的凳子上，双手持哑铃置于肩部两侧",
        "向上推举哑铃至手臂伸直",
        "控制哑铃下降回到起始位置"
    ],
    190: [  # 前箭步蹲
        "站立，双手持哑铃或杠铃",
        "向前迈出一大步，前腿屈膝至90度",
        "后腿膝盖接近地面",
        "前脚发力推回起始位置，换腿重复"
    ],
    211: [  # 杠铃窄握卧推
        "仰卧在平板凳上，双手窄握杠铃（略窄于肩宽）",
        "将杠铃下降至胸部中央",
        "推举杠铃至手臂伸直"
    ],
    213: [  # 杠铃Silverback耸肩
        "站立，双手正握杠铃，手臂自然下垂",
        "耸肩将杠铃向上提起，肩胛骨上提",
        "保持手臂伸直，不要弯曲肘部",
        "控制下降回到起始位置"
    ],
    241: [  # 绳索下压
        "站在绳索机前，双手握住绳索把手",
        "保持肘部固定，向下压绳索至手臂伸直"
    ],
    290: [  # 哑铃耸肩
        "站立，双手持哑铃自然下垂于身体两侧，耸肩将哑铃向上提起"
    ],
    303: [  # 杠铃推举
        "站立或坐姿，杠铃置于肩部前方",
        "向上推举杠铃至手臂伸直",
        "控制杠铃下降回到肩部",
        "重复动作"
    ],
    304: [  # 杠铃直立划船
        "站立，双手正握杠铃，握距略窄于肩宽",
        "沿身体前侧向上拉起杠铃至下巴高度"
    ],
    307: [  # 杠铃仰卧臂屈伸
        "仰卧在平板凳上，双手握杠铃，手臂伸直于胸部上方",
        "屈肘将杠铃下降至额头附近，然后伸肘回到起始位置"
    ],
    309: [  # 杠铃仰卧起坐
        "仰卧，双手持杠铃于胸前",
        "收缩腹肌，将上半身抬起"
    ],
    310: [  # 反手杠铃弯举
        "站立，双手反握杠铃（掌心向上）",
        "屈肘将杠铃弯举至肩部高度"
    ],
    313: [  # 杠铃罗马尼亚硬拉
        "站立，双手正握杠铃，膝盖微屈",
        "屈髋向前倾，杠铃沿大腿下降",
        "感受腘绳肌拉伸后，收缩臀部回到起始位置"
    ],
    327: [  # 直臂平板支撑
        "俯卧撑起始姿势，手臂伸直支撑身体",
        "保持身体从头到脚呈一条直线，收紧核心"
    ],
    398: [  # 上斜哑铃卧推
        "仰卧在上斜凳上（30-45度角），双手持哑铃",
        "将哑铃推举至手臂伸直",
        "控制哑铃下降至胸部两侧"
    ],
    420: [  # 哑铃交替阿诺德推举
        "坐姿，双手持哑铃于肩前，掌心朝向自己，交替向上推举并旋转手腕"
    ],
    1095: [  # 有氧交叉开合跳
        "进行开合跳，同时双臂在身体前方交叉"
    ],
    1109: [  # 有氧快速脚步
        "原地快速交替抬脚，保持高频率"
    ],
    1181: [  # 哑铃地板卧推
        "仰卧在地板上，双手持哑铃推举"
    ],
    1199: [  # 跑步机慢跑
        "在跑步机上以中等速度慢跑"
    ],
    1200: [  # 跑步机冲刺
        "在跑步机上以高速冲刺"
    ],
    1201: [  # 跑步机步行
        "在跑步机上以慢速步行"
    ],
    1283: [  # 肩外旋/肩内旋
        "使用弹力带或哑铃进行肩关节外旋和内旋训练"
    ],
    1315: [  # 祈祷式拉伸2（泡沫轴）
        "使用泡沫轴辅助进行祈祷式拉伸"
    ],
    1573: [  # 自重单腿稳定平衡
        "单腿站立，保持身体平衡和稳定"
    ],
    1665: [  # 站姿器械侧平举
        "站在器械旁，单手握住把手，向侧方抬起至肩部高度"
    ]
}

print(f"\n准备翻译 {len(manual_translations)} 个动作...")

# 更新数据库
success_count = 0
failed_count = 0

with driver.session() as session:
    for exercise_id, steps_zh in manual_translations.items():
        try:
            query = """
            MATCH (e:Exercise {id: $exercise_id})
            SET e.correct_steps_zh = $steps_zh
            RETURN e.id as id, e.name_zh as name_zh
            """
            result = session.run(query, exercise_id=exercise_id, steps_zh=steps_zh)
            record = result.single()
            
            if record:
                success_count += 1
                print(f"✅ ID={exercise_id}, {record['name_zh']}: {len(steps_zh)} 个步骤")
            else:
                failed_count += 1
                print(f"❌ ID={exercise_id}: 未找到")
        
        except Exception as e:
            failed_count += 1
            print(f"❌ ID={exercise_id}: {e}")

driver.close()

print("\n" + "=" * 80)
print("翻译完成")
print("=" * 80)

print(f"\n成功: {success_count}")
print(f"失败: {failed_count}")

print("\n✅ 手动翻译完成！")
print("=" * 80)
