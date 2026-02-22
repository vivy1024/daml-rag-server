"""
补全11个孤立InjuryType的CONTRAINDICATED_FOR关系数据

孤立伤病列表:
1. wrist_injury (腕部受伤) - 手腕损伤
2. achilles_tendinitis (跟腱炎) - 脚踝损伤
3. plantar_fasciitis (足底筋膜炎) - 脚踝损伤
4. ankle_sprain (踝关节扭伤) - 脚踝损伤
5. cervical_spondylosis (颈椎病) - 颈部损伤
6. neck_injury (颈部受伤) - 颈部损伤
7. tennis_elbow (网球肘) - 肘部损伤
8. golfers_elbow (高尔夫球肘) - 肘部损伤
9. hip_impingement (髋关节撞击) - 髋部损伤
10. hip_bursitis (髋滑囊炎) - 髋部损伤
11. hip_injury (髋部受伤) - 髋部损伤

数据生成逻辑: 根据伤病涉及的身体部位，匹配相关肌群的动作
参考现有数据模式: 每种伤病一个统一reason，severity=high/moderate，confidence=0.6-1.0

作者: 薛小川
日期: 2026-02-22
"""

from neo4j import GraphDatabase
from datetime import datetime

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "build_body_2024"))

# 11个孤立伤病的禁忌规则定义
# 格式: {injury_name: {muscle_keywords, severity, reason, confidence}}
INJURY_RULES = {
    # === 手腕损伤 ===
    "wrist_injury": {
        "description": "腕部受伤",
        "severity": "high",
        "reason": "腕关节承重或屈伸动作可能加重损伤",
        "confidence": 0.8,
        "match_rules": [
            # 直接涉及前臂/腕部的动作
            {"muscle_keywords": ["前臂", "腕屈肌", "腕伸肌"], "severity": "high", "confidence": 0.9},
            # 需要握力支撑的动作（背阔肌划船、硬拉等）
            {"muscle_keywords": ["背阔肌"], "severity": "moderate", "confidence": 0.6},
            # 手腕承重动作（俯卧撑类、平板支撑类）
            {"name_keywords": ["俯卧撑", "平板支撑", "手撑", "倒立"], "severity": "high", "confidence": 0.8},
        ]
    },

    # === 脚踝损伤 ===
    "achilles_tendinitis": {
        "description": "跟腱炎",
        "severity": "high",
        "reason": "跟腱拉伸或负荷过大，可能加重炎症",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["小腿", "腓肠肌", "比目鱼肌"], "severity": "high", "confidence": 0.9},
            {"name_keywords": ["跳", "跑", "冲刺", "弹跳", "提踵"], "severity": "high", "confidence": 0.9},
            {"muscle_keywords": ["臀部", "股四头肌"], "severity": "moderate", "confidence": 0.5,
             "name_keywords": ["深蹲", "弓步", "箭步"]},
        ]
    },
    "plantar_fasciitis": {
        "description": "足底筋膜炎",
        "severity": "high",
        "reason": "足底冲击力或拉伸可能加重筋膜炎症",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["小腿", "腓肠肌", "比目鱼肌", "足部", "胫骨前肌"], "severity": "high", "confidence": 0.9},
            {"name_keywords": ["跳", "跑", "冲刺", "弹跳"], "severity": "high", "confidence": 0.9},
        ]
    },
    "ankle_sprain": {
        "description": "踝关节扭伤",
        "severity": "high",
        "reason": "踝关节不稳定，负重或侧向动作可能导致再次扭伤",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["小腿", "腓肠肌", "比目鱼肌", "足部", "胫骨前肌"], "severity": "high", "confidence": 0.9},
            {"name_keywords": ["单腿", "弓步", "箭步", "侧步", "跳", "弹跳"], "severity": "high", "confidence": 0.8},
        ]
    },

    # === 颈部损伤 ===
    "cervical_spondylosis": {
        "description": "颈椎病",
        "severity": "high",
        "reason": "颈椎负荷或极端位置可能加重椎间盘退变",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["颈部"], "severity": "high", "confidence": 0.9},
            {"muscle_keywords": ["斜方肌", "上斜方肌"], "severity": "moderate", "confidence": 0.7},
            {"name_keywords": ["颈", "头", "倒立", "肩倒立", "犁式"], "severity": "high", "confidence": 0.9},
        ]
    },
    "neck_injury": {
        "description": "颈部受伤",
        "severity": "high",
        "reason": "颈部肌肉或韧带受伤，负荷动作可能加重损伤",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["颈部"], "severity": "high", "confidence": 0.9},
            {"muscle_keywords": ["斜方肌", "上斜方肌"], "severity": "moderate", "confidence": 0.7},
            {"name_keywords": ["颈", "头", "倒立", "肩倒立", "耸肩"], "severity": "high", "confidence": 0.8},
        ]
    },

    # === 肘部损伤 ===
    "tennis_elbow": {
        "description": "网球肘（肱骨外上髁炎）",
        "severity": "high",
        "reason": "腕伸肌群反复收缩可能加重外上髁炎症",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["前臂", "腕伸肌"], "severity": "high", "confidence": 0.9},
            {"muscle_keywords": ["肱二头肌"], "severity": "moderate", "confidence": 0.6},
            {"muscle_keywords": ["背阔肌"], "severity": "moderate", "confidence": 0.5,
             "name_keywords": ["划船", "引体", "下拉"]},
        ]
    },
    "golfers_elbow": {
        "description": "高尔夫球肘（肱骨内上髁炎）",
        "severity": "high",
        "reason": "腕屈肌群反复收缩可能加重内上髁炎症",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["前臂", "腕屈肌"], "severity": "high", "confidence": 0.9},
            {"muscle_keywords": ["肱二头肌"], "severity": "moderate", "confidence": 0.7},
            {"name_keywords": ["弯举", "引体", "下拉", "划船"], "severity": "moderate", "confidence": 0.6},
        ]
    },

    # === 髋部损伤 ===
    "hip_impingement": {
        "description": "髋关节撞击（FAI）",
        "severity": "high",
        "reason": "髋关节深屈曲或内旋可能加重撞击",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["臀部", "臀大肌", "臀中肌"], "severity": "high", "confidence": 0.8},
            {"muscle_keywords": ["大腿内侧", "腹股沟"], "severity": "high", "confidence": 0.9},
            {"name_keywords": ["深蹲", "硬拉", "弓步", "箭步"], "severity": "high", "confidence": 0.7},
        ]
    },
    "hip_bursitis": {
        "description": "髋滑囊炎",
        "severity": "moderate",
        "reason": "髋关节外展或侧向动作可能刺激滑囊",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["臀中肌"], "severity": "high", "confidence": 0.9},
            {"muscle_keywords": ["大腿内侧", "腹股沟"], "severity": "moderate", "confidence": 0.7},
            {"name_keywords": ["侧卧", "侧抬腿", "蚌式", "外展"], "severity": "high", "confidence": 0.8},
            {"muscle_keywords": ["臀部"], "severity": "moderate", "confidence": 0.5,
             "name_keywords": ["侧", "外展"]},
        ]
    },
    "hip_injury": {
        "description": "髋部受伤",
        "severity": "high",
        "reason": "髋关节负荷过大，可能加重损伤",
        "confidence": 0.8,
        "match_rules": [
            {"muscle_keywords": ["臀部", "臀大肌", "臀中肌"], "severity": "high", "confidence": 0.8},
            {"muscle_keywords": ["大腿内侧", "腹股沟"], "severity": "high", "confidence": 0.9},
            {"muscle_keywords": ["股四头肌"], "severity": "moderate", "confidence": 0.5,
             "name_keywords": ["深蹲", "弓步", "箭步", "硬拉"]},
        ]
    },
}


def match_exercise(exercise, rule):
    """检查动作是否匹配规则"""
    name = exercise.get("name_zh", "") or ""
    muscles = exercise.get("muscles_primary_zh") or []
    all_muscles = exercise.get("all_muscles_zh") or []

    muscle_keywords = rule.get("muscle_keywords", [])
    name_keywords = rule.get("name_keywords", [])

    muscle_match = False
    name_match = False

    # 肌群匹配
    if muscle_keywords:
        for kw in muscle_keywords:
            if any(kw in m for m in muscles) or any(kw in m for m in all_muscles):
                muscle_match = True
                break

    # 名称匹配
    if name_keywords:
        for kw in name_keywords:
            if kw in name:
                name_match = True
                break

    # 如果规则同时有 muscle_keywords 和 name_keywords，需要两者都匹配
    if muscle_keywords and name_keywords:
        return muscle_match and name_match
    # 只有一种条件时，匹配即可
    return muscle_match or name_match


def backfill():
    """执行补数据"""
    with driver.session() as session:
        # 获取所有动作
        result = session.run("""
            MATCH (e:Exercise)
            RETURN e.id AS id, e.name_zh AS name_zh,
                   e.muscles_primary_zh AS muscles_primary_zh,
                   e.all_muscles_zh AS all_muscles_zh
        """)
        exercises = [dict(rec) for rec in result]
        print(f"总动作数: {len(exercises)}")

        total_created = 0
        now = datetime.now().isoformat()

        for injury_name, config in INJURY_RULES.items():
            matched_exercises = set()
            exercise_rule_map = {}  # exercise_id -> best matching rule

            for rule in config["match_rules"]:
                for ex in exercises:
                    if ex["id"] in matched_exercises:
                        continue
                    if match_exercise(ex, rule):
                        matched_exercises.add(ex["id"])
                        exercise_rule_map[ex["id"]] = rule

            if not matched_exercises:
                print(f"⚠️ {injury_name} ({config['description']}): 无匹配动作")
                continue

            # 批量创建关系
            count = 0
            for ex_id in matched_exercises:
                rule = exercise_rule_map[ex_id]
                severity = rule.get("severity", config["severity"])
                confidence = rule.get("confidence", config["confidence"])
                reason = config["reason"]

                session.run("""
                    MATCH (e:Exercise {id: $exercise_id})
                    MATCH (i:InjuryType {name: $injury_name})
                    MERGE (e)-[r:CONTRAINDICATED_FOR]->(i)
                    ON CREATE SET r.severity = $severity,
                                  r.reason = $reason,
                                  r.confidence = $confidence,
                                  r.created_at = $created_at
                """, {
                    "exercise_id": ex_id,
                    "injury_name": injury_name,
                    "severity": severity,
                    "reason": reason,
                    "confidence": confidence,
                    "created_at": now,
                })
                count += 1

            total_created += count
            print(f"✅ {injury_name} ({config['description']}): 创建 {count} 条禁忌关系")

        print(f"\n总计创建: {total_created} 条禁忌关系")

        # 验证
        result = session.run("""
            MATCH ()-[r:CONTRAINDICATED_FOR]->()
            RETURN count(r) AS total
        """)
        for rec in result:
            print(f"数据库总禁忌关系数: {rec['total']}")

        # 验证孤立节点
        result = session.run("""
            MATCH (i:InjuryType)
            WHERE NOT (:Exercise)-[:CONTRAINDICATED_FOR]->(i)
            RETURN i.name AS name, i.name_zh AS name_zh
        """)
        orphans = [dict(rec) for rec in result]
        if orphans:
            print(f"\n⚠️ 仍有 {len(orphans)} 个孤立节点:")
            for o in orphans:
                print(f"  - {o['name']} ({o['name_zh']})")
        else:
            print("\n✅ 所有 InjuryType 节点均有禁忌关系数据")


if __name__ == "__main__":
    backfill()
    driver.close()
