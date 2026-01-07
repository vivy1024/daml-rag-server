"""
补充所有40个Muscle节点的完整属性

基于运动学专业知识，为每个肌群补充：
- mev/mav/mrv: 训练量标准（组/周）
- training_frequency: 训练频率
- recovery_time: 恢复时间
- function: 功能描述
- movement_patterns: 动作模式
- synergy_partners: 协同肌群
- antagonist_partners: 对抗肌群
- group: 肌群分类

数据来源：Renaissance Periodization、NSCA、运动解剖学教材

作者: BUILD_BODY Team
日期: 2026-01-06
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"

# 专业训练数据 - 基于RP、NSCA标准
MUSCLE_DATA = {
    # === 臀部/髋部 ===
    "臀部": {
        "name_en": "Glutes",
        "group": "hip",
        "mev": 4, "mav": 12, "mrv": 16,
        "training_frequency": "2-3次/周",
        "recovery_time": "48-72小时",
        "function": "髋关节伸展、外展、外旋",
        "movement_patterns": ["蹲", "硬拉", "髋铰链"],
        "synergy_partners": ["腿后肌群", "下背部"],
        "antagonist_partners": ["股四头肌", "髂腰肌"]
    },
    "臀中肌": {
        "name_en": "Gluteus Medius",
        "group": "hip",
        "mev": 4, "mav": 10, "mrv": 14,
        "training_frequency": "2-3次/周",
        "recovery_time": "48小时",
        "function": "髋关节外展、稳定骨盆",
        "movement_patterns": ["外展", "侧向运动"],
        "synergy_partners": ["臀部", "阔筋膜张肌"],
        "antagonist_partners": ["大腿内侧"]
    },
    
    # === 背部 ===
    "下背部": {
        "name_en": "Lower Back / Erector Spinae",
        "group": "back",
        "mev": 6, "mav": 12, "mrv": 18,
        "training_frequency": "2次/周",
        "recovery_time": "72-96小时",
        "function": "脊柱伸展、维持姿势、核心稳定",
        "movement_patterns": ["硬拉", "背伸展"],
        "synergy_partners": ["臀部", "腿后肌群"],
        "antagonist_partners": ["腹直肌"]
    },
    "背阔肌": {
        "name_en": "Latissimus Dorsi",
        "group": "back",
        "mev": 10, "mav": 18, "mrv": 25,
        "training_frequency": "2次/周",
        "recovery_time": "48-72小时",
        "function": "肩关节伸展、内收、内旋",
        "movement_patterns": ["拉", "划船", "引体向上"],
        "synergy_partners": ["肱二头肌", "三角肌后束"],
        "antagonist_partners": ["胸部", "三角肌前束"]
    },
    "斜方肌": {
        "name_en": "Trapezius",
        "group": "back",
        "mev": 0, "mav": 12, "mrv": 20,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肩胛骨上提、后缩、下压",
        "movement_patterns": ["耸肩", "划船"],
        "synergy_partners": ["三角肌", "菱形肌"],
        "antagonist_partners": ["胸小肌"]
    },
    "斜方肌（中背）": {
        "name_en": "Middle Trapezius",
        "group": "back",
        "mev": 6, "mav": 14, "mrv": 20,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肩胛骨后缩",
        "movement_patterns": ["划船", "面拉"],
        "synergy_partners": ["菱形肌", "三角肌后束"],
        "antagonist_partners": ["胸小肌"]
    },
    "上斜方肌": {
        "name_en": "Upper Trapezius",
        "group": "back",
        "mev": 0, "mav": 8, "mrv": 14,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肩胛骨上提、颈部侧屈",
        "movement_patterns": ["耸肩"],
        "synergy_partners": ["肩胛提肌"],
        "antagonist_partners": ["下斜方肌"]
    },
    "斜方肌下部": {
        "name_en": "Lower Trapezius",
        "group": "back",
        "mev": 6, "mav": 12, "mrv": 18,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肩胛骨下压、后缩",
        "movement_patterns": ["Y字举", "面拉"],
        "synergy_partners": ["菱形肌"],
        "antagonist_partners": ["上斜方肌"]
    },
    
    # === 肩部 ===
    "三角肌前束": {
        "name_en": "Anterior Deltoid",
        "group": "shoulder",
        "mev": 0, "mav": 8, "mrv": 14,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肩关节屈曲、内旋",
        "movement_patterns": ["推", "前平举"],
        "synergy_partners": ["胸部", "肱三头肌"],
        "antagonist_partners": ["三角肌后束", "背阔肌"]
    },
    "三角肌中束": {
        "name_en": "Lateral Deltoid",
        "group": "shoulder",
        "mev": 8, "mav": 16, "mrv": 22,
        "training_frequency": "2-3次/周",
        "recovery_time": "48小时",
        "function": "肩关节外展",
        "movement_patterns": ["侧平举", "推举"],
        "synergy_partners": ["上斜方肌"],
        "antagonist_partners": ["背阔肌"]
    },
    "三角肌后束": {
        "name_en": "Posterior Deltoid",
        "group": "shoulder",
        "mev": 8, "mav": 16, "mrv": 22,
        "training_frequency": "2-3次/周",
        "recovery_time": "48小时",
        "function": "肩关节伸展、外旋",
        "movement_patterns": ["拉", "反向飞鸟"],
        "synergy_partners": ["背阔肌", "菱形肌"],
        "antagonist_partners": ["三角肌前束", "胸部"]
    },
    "肩部": {
        "name_en": "Shoulders",
        "group": "shoulder",
        "mev": 8, "mav": 16, "mrv": 22,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肩关节多方向运动",
        "movement_patterns": ["推", "举", "拉"],
        "synergy_partners": ["肱三头肌", "斜方肌"],
        "antagonist_partners": ["背阔肌"]
    },
    
    # === 手臂 ===
    "肱二头肌": {
        "name_en": "Biceps Brachii",
        "group": "arm",
        "mev": 8, "mav": 14, "mrv": 20,
        "training_frequency": "2-3次/周",
        "recovery_time": "48小时",
        "function": "肘关节屈曲、前臂旋后",
        "movement_patterns": ["拉", "弯举"],
        "synergy_partners": ["肱肌", "肱桡肌"],
        "antagonist_partners": ["肱三头肌"]
    },
    "肱二头肌长头": {
        "name_en": "Biceps Long Head",
        "group": "arm",
        "mev": 6, "mav": 12, "mrv": 18,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肘关节屈曲、肩关节屈曲",
        "movement_patterns": ["弯举", "上斜弯举"],
        "synergy_partners": ["肱二头肌短头"],
        "antagonist_partners": ["肱三头肌长头"]
    },
    "肱二头肌短头": {
        "name_en": "Biceps Short Head",
        "group": "arm",
        "mev": 6, "mav": 12, "mrv": 18,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肘关节屈曲",
        "movement_patterns": ["弯举", "牧师凳弯举"],
        "synergy_partners": ["肱二头肌长头"],
        "antagonist_partners": ["肱三头肌"]
    },
    "肱三头肌": {
        "name_en": "Triceps Brachii",
        "group": "arm",
        "mev": 6, "mav": 12, "mrv": 18,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肘关节伸展",
        "movement_patterns": ["推", "下压"],
        "synergy_partners": ["胸部", "三角肌前束"],
        "antagonist_partners": ["肱二头肌"]
    },
    "肱三头肌外侧头": {
        "name_en": "Triceps Lateral Head",
        "group": "arm",
        "mev": 4, "mav": 10, "mrv": 14,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肘关节伸展",
        "movement_patterns": ["下压", "窄距推"],
        "synergy_partners": ["肱三头肌长头"],
        "antagonist_partners": ["肱二头肌"]
    },
    "三头肌长头": {
        "name_en": "Triceps Long Head",
        "group": "arm",
        "mev": 6, "mav": 12, "mrv": 16,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "肘关节伸展、肩关节伸展",
        "movement_patterns": ["过头臂屈伸", "下压"],
        "synergy_partners": ["肱三头肌外侧头"],
        "antagonist_partners": ["肱二头肌"]
    },
    "前臂肌群": {
        "name_en": "Forearms",
        "group": "arm",
        "mev": 4, "mav": 10, "mrv": 16,
        "training_frequency": "2-3次/周",
        "recovery_time": "24-48小时",
        "function": "腕关节屈伸、握力",
        "movement_patterns": ["握", "腕弯举"],
        "synergy_partners": ["肱二头肌"],
        "antagonist_partners": []
    },
    "腕伸肌群": {
        "name_en": "Wrist Extensors",
        "group": "arm",
        "mev": 4, "mav": 8, "mrv": 12,
        "training_frequency": "2次/周",
        "recovery_time": "24-48小时",
        "function": "腕关节伸展",
        "movement_patterns": ["反向腕弯举"],
        "synergy_partners": [],
        "antagonist_partners": ["腕屈肌"]
    },
    
    # === 胸部 ===
    "胸部": {
        "name_en": "Chest / Pectoralis Major",
        "group": "chest",
        "mev": 10, "mav": 18, "mrv": 22,
        "training_frequency": "2次/周",
        "recovery_time": "48-72小时",
        "function": "肩关节水平内收、屈曲、内旋",
        "movement_patterns": ["推", "夹胸"],
        "synergy_partners": ["三角肌前束", "肱三头肌"],
        "antagonist_partners": ["背阔肌", "三角肌后束"]
    },
    "中胸与下胸": {
        "name_en": "Mid and Lower Chest",
        "group": "chest",
        "mev": 8, "mav": 16, "mrv": 20,
        "training_frequency": "2次/周",
        "recovery_time": "48-72小时",
        "function": "肩关节水平内收、内旋",
        "movement_patterns": ["平板推", "下斜推"],
        "synergy_partners": ["三角肌前束", "肱三头肌"],
        "antagonist_partners": ["背阔肌"]
    },
    "上胸": {
        "name_en": "Upper Chest",
        "group": "chest",
        "mev": 6, "mav": 14, "mrv": 18,
        "training_frequency": "2次/周",
        "recovery_time": "48-72小时",
        "function": "肩关节屈曲、水平内收",
        "movement_patterns": ["上斜推", "上斜飞鸟"],
        "synergy_partners": ["三角肌前束"],
        "antagonist_partners": ["背阔肌", "三角肌后束"]
    },
    
    # === 腿部 ===
    "股四头肌": {
        "name_en": "Quadriceps",
        "group": "leg",
        "mev": 8, "mav": 16, "mrv": 20,
        "training_frequency": "2次/周",
        "recovery_time": "72-96小时",
        "function": "膝关节伸展、髋关节屈曲",
        "movement_patterns": ["蹲", "腿举", "腿屈伸"],
        "synergy_partners": ["臀部"],
        "antagonist_partners": ["腿后肌群"]
    },
    "股四头肌内侧": {
        "name_en": "Vastus Medialis",
        "group": "leg",
        "mev": 6, "mav": 12, "mrv": 16,
        "training_frequency": "2次/周",
        "recovery_time": "72小时",
        "function": "膝关节伸展、稳定髌骨",
        "movement_patterns": ["蹲", "腿屈伸"],
        "synergy_partners": ["股四头肌"],
        "antagonist_partners": ["腿后肌群"]
    },
    "股直肌": {
        "name_en": "Rectus Femoris",
        "group": "leg",
        "mev": 6, "mav": 12, "mrv": 16,
        "training_frequency": "2次/周",
        "recovery_time": "72小时",
        "function": "膝关节伸展、髋关节屈曲",
        "movement_patterns": ["蹲", "腿举"],
        "synergy_partners": ["股四头肌"],
        "antagonist_partners": ["腿后肌群", "臀部"]
    },
    "腿后肌群": {
        "name_en": "Hamstrings",
        "group": "leg",
        "mev": 6, "mav": 12, "mrv": 16,
        "training_frequency": "2次/周",
        "recovery_time": "72小时",
        "function": "膝关节屈曲、髋关节伸展",
        "movement_patterns": ["硬拉", "腿弯举"],
        "synergy_partners": ["臀部", "下背部"],
        "antagonist_partners": ["股四头肌"]
    },
    "腘绳肌内侧": {
        "name_en": "Medial Hamstrings",
        "group": "leg",
        "mev": 6, "mav": 10, "mrv": 14,
        "training_frequency": "2次/周",
        "recovery_time": "72小时",
        "function": "膝关节屈曲、髋关节伸展、小腿内旋",
        "movement_patterns": ["硬拉", "腿弯举"],
        "synergy_partners": ["腿后肌群"],
        "antagonist_partners": ["股四头肌内侧"]
    },
    "股二头肌（外侧）": {
        "name_en": "Biceps Femoris",
        "group": "leg",
        "mev": 6, "mav": 10, "mrv": 14,
        "training_frequency": "2次/周",
        "recovery_time": "72小时",
        "function": "膝关节屈曲、髋关节伸展、小腿外旋",
        "movement_patterns": ["硬拉", "腿弯举"],
        "synergy_partners": ["腿后肌群"],
        "antagonist_partners": ["股四头肌"]
    },
    "大腿内侧": {
        "name_en": "Adductors",
        "group": "leg",
        "mev": 4, "mav": 10, "mrv": 14,
        "training_frequency": "2次/周",
        "recovery_time": "48-72小时",
        "function": "髋关节内收",
        "movement_patterns": ["内收", "宽距蹲"],
        "synergy_partners": ["臀部"],
        "antagonist_partners": ["臀中肌"]
    },
    "小腿": {
        "name_en": "Calves",
        "group": "leg",
        "mev": 8, "mav": 12, "mrv": 16,
        "training_frequency": "3-4次/周",
        "recovery_time": "24-48小时",
        "function": "踝关节跖屈",
        "movement_patterns": ["提踵"],
        "synergy_partners": [],
        "antagonist_partners": ["胫骨前肌"]
    },
    "胫骨前肌": {
        "name_en": "Tibialis Anterior",
        "group": "leg",
        "mev": 4, "mav": 8, "mrv": 12,
        "training_frequency": "2-3次/周",
        "recovery_time": "24-48小时",
        "function": "踝关节背屈",
        "movement_patterns": ["背屈"],
        "synergy_partners": [],
        "antagonist_partners": ["小腿"]
    },
    "双脚": {
        "name_en": "Feet",
        "group": "leg",
        "mev": 2, "mav": 6, "mrv": 10,
        "training_frequency": "2次/周",
        "recovery_time": "24小时",
        "function": "足部稳定、平衡",
        "movement_patterns": ["平衡训练"],
        "synergy_partners": ["小腿"],
        "antagonist_partners": []
    },
    
    # === 核心 ===
    "腹直肌": {
        "name_en": "Rectus Abdominis",
        "group": "core",
        "mev": 0, "mav": 16, "mrv": 25,
        "training_frequency": "3-4次/周",
        "recovery_time": "24-48小时",
        "function": "脊柱屈曲、骨盆后倾",
        "movement_patterns": ["卷腹", "悬垂举腿"],
        "synergy_partners": ["腹斜肌"],
        "antagonist_partners": ["下背部"]
    },
    "上腹肌": {
        "name_en": "Upper Abs",
        "group": "core",
        "mev": 0, "mav": 12, "mrv": 20,
        "training_frequency": "3次/周",
        "recovery_time": "24-48小时",
        "function": "上脊柱屈曲",
        "movement_patterns": ["卷腹"],
        "synergy_partners": ["腹直肌"],
        "antagonist_partners": ["下背部"]
    },
    "下腹部": {
        "name_en": "Lower Abs",
        "group": "core",
        "mev": 0, "mav": 12, "mrv": 20,
        "training_frequency": "3次/周",
        "recovery_time": "24-48小时",
        "function": "骨盆后倾、下脊柱屈曲",
        "movement_patterns": ["举腿", "反向卷腹"],
        "synergy_partners": ["腹直肌", "髂腰肌"],
        "antagonist_partners": ["下背部"]
    },
    "腹斜肌": {
        "name_en": "Obliques",
        "group": "core",
        "mev": 0, "mav": 12, "mrv": 18,
        "training_frequency": "2-3次/周",
        "recovery_time": "24-48小时",
        "function": "脊柱旋转、侧屈",
        "movement_patterns": ["旋转", "侧屈"],
        "synergy_partners": ["腹直肌"],
        "antagonist_partners": ["下背部"]
    },
    "腹股沟": {
        "name_en": "Hip Flexors / Iliopsoas",
        "group": "core",
        "mev": 4, "mav": 8, "mrv": 12,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "髋关节屈曲",
        "movement_patterns": ["举腿", "高抬腿"],
        "synergy_partners": ["股直肌"],
        "antagonist_partners": ["臀部"]
    },
    
    # === 颈部 ===
    "颈部": {
        "name_en": "Neck",
        "group": "neck",
        "mev": 4, "mav": 8, "mrv": 12,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "颈部屈伸、旋转",
        "movement_patterns": ["颈部训练"],
        "synergy_partners": ["上斜方肌"],
        "antagonist_partners": []
    },
    
    # === 特殊/未知 ===
    "未知": {
        "name_en": "Unknown",
        "group": "other",
        "mev": 6, "mav": 12, "mrv": 18,
        "training_frequency": "2次/周",
        "recovery_time": "48小时",
        "function": "待确认",
        "movement_patterns": [],
        "synergy_partners": [],
        "antagonist_partners": []
    }
}

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 70)
print("补充所有Muscle节点的完整属性")
print("=" * 70)

with driver.session() as session:
    # 获取当前所有Muscle节点
    result = session.run("MATCH (m:Muscle) RETURN m.name_zh as name ORDER BY name")
    muscles = [r["name"] for r in result]
    print(f"\n当前Muscle节点: {len(muscles)} 个")
    
    updated = 0
    not_found = []
    
    for muscle_name in muscles:
        if muscle_name in MUSCLE_DATA:
            data = MUSCLE_DATA[muscle_name]
            session.run("""
                MATCH (m:Muscle {name_zh: $name})
                SET m.name_en = $name_en,
                    m.group = $group,
                    m.mev = $mev,
                    m.mav = $mav,
                    m.mrv = $mrv,
                    m.training_frequency = $training_frequency,
                    m.recovery_time = $recovery_time,
                    m.function = $function,
                    m.movement_patterns = $movement_patterns,
                    m.synergy_partners = $synergy_partners,
                    m.antagonist_partners = $antagonist_partners,
                    m.updated_at = datetime()
            """, 
                name=muscle_name,
                name_en=data["name_en"],
                group=data["group"],
                mev=data["mev"],
                mav=data["mav"],
                mrv=data["mrv"],
                training_frequency=data["training_frequency"],
                recovery_time=data["recovery_time"],
                function=data["function"],
                movement_patterns=data["movement_patterns"],
                synergy_partners=data["synergy_partners"],
                antagonist_partners=data["antagonist_partners"]
            )
            updated += 1
            print(f"  ✅ {muscle_name}")
        else:
            not_found.append(muscle_name)
            print(f"  ⚠️ 未找到数据: {muscle_name}")
    
    print(f"\n更新完成: {updated}/{len(muscles)}")
    
    if not_found:
        print(f"\n未找到数据的肌群 ({len(not_found)}个):")
        for m in not_found:
            print(f"  - {m}")

print("\n" + "=" * 70)
print("✅ 补充完成!")
print("=" * 70)

driver.close()
