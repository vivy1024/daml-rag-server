#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版禁忌症规则

基于医学损伤专家、运动学教授和康复学专家的讨论制定
参考文档: docs/运动损伤禁忌症专家讨论.md

版本: v2.0.0
日期: 2025-12-15
"""

# ===========================================================================
# Phase 1: 立即实施的核心损伤类型
# ===========================================================================

PHASE1_CONTRAINDICATION_RULES = {
    # 1. 肩袖损伤 (Rotator Cuff Injury)
    "肩袖损伤": {
        "keywords_zh": [
            "肩推", "推举", "侧平举", "前平举", "引体", "过头",
            "抓举", "挺举", "上斜卧推", "军事推举", "阿诺德推举"
        ],
        "keywords_en": [
            "shoulder press", "overhead press", "lateral raise", "front raise",
            "pull-up", "overhead", "snatch", "clean", "incline press", "arnold press"
        ],
        "primary_muscles": ["前肩", "中肩", "后肩", "三角肌前束", "三角肌中束", "三角肌后束"],
        "severity": "absolute",  # 绝对禁忌
        "description": "肩袖损伤：避免肩关节外展超过90度和过头推举动作，这些动作会增加肩峰下空间压力"
    },
    
    # 2. 肩峰撞击综合征 (Shoulder Impingement)
    "肩峰撞击": {
        "keywords_zh": [
            "侧平举", "前平举", "引体", "过头", "肩推",
            "直立划船", "耸肩", "上斜卧推"
        ],
        "keywords_en": [
            "lateral raise", "front raise", "pull-up", "overhead",
            "upright row", "shrug", "incline press"
        ],
        "primary_muscles": ["前肩", "中肩", "三角肌前束", "三角肌中束", "上斜方肌"],
        "severity": "absolute",
        "description": "肩峰撞击：避免肩关节外展和内旋组合动作，特别是直立划船和高位侧平举"
    },
    
    # 3. 髌骨软化症 (Patellofemoral Pain Syndrome)
    "髌骨软化症": {
        "keywords_zh": [
            "深蹲", "全蹲", "腿举", "弓步", "跳", "蹲", "爬楼",
            "腿屈伸", "箱式深蹲", "保加利亚", "跳箱"
        ],
        "keywords_en": [
            "squat", "deep squat", "leg press", "lunge", "jump", "box jump",
            "leg extension", "bulgarian", "step up"
        ],
        "primary_muscles": ["股四头肌", "臀大肌", "臀部"],
        "severity": "absolute",
        "description": "髌骨软化症：避免膝关节屈曲超过90度的动作，膝关节压力在深蹲时达到体重的3-4倍"
    },
    
    # 4. 腰椎间盘突出 (Lumbar Disc Herniation)
    "腰椎间盘突出": {
        "keywords_zh": [
            "硬拉", "早安", "深蹲", "划船", "俯身", "罗马尼亚",
            "仰卧起坐", "转体", "弯腰", "背部伸展", "负重行走"
        ],
        "keywords_en": [
            "deadlift", "good morning", "squat", "row", "bent over", "romanian",
            "sit-up", "twist", "bend", "back extension", "farmer walk"
        ],
        "primary_muscles": ["下背部", "竖脊肌", "腰方肌"],
        "severity": "absolute",
        "description": "腰椎间盘突出：避免脊柱前屈和旋转动作，这些动作会增加椎间盘压力和剪切力"
    },
    
    # 5. 下背部疼痛 (Lower Back Pain) - 通用
    "下背部疼痛": {
        "keywords_zh": [
            "硬拉", "深蹲", "划船", "弯腰", "罗马尼亚", "早安式",
            "背部伸展", "负重行走", "农夫行走"
        ],
        "keywords_en": [
            "deadlift", "squat", "row", "bend", "romanian", "good morning",
            "back extension", "farmer walk", "loaded carry"
        ],
        "primary_muscles": ["下背部", "竖脊肌"],
        "severity": "relative",  # 相对禁忌
        "description": "下背部疼痛：避免对腰椎压力大的动作，需要根据疼痛程度调整"
    },
    
    # 6. 膝盖受伤 (Knee Injury) - 通用
    "膝盖受伤": {
        "keywords_zh": ["深蹲", "弓步", "跳", "蹲", "腿举", "腿屈伸", "腿推", "提踵"],
        "keywords_en": ["squat", "lunge", "jump", "leg press", "leg extension", "leg curl", "calf"],
        "primary_muscles": ["股四头肌", "腘绳肌", "小腿", "臀大肌"],
        "severity": "relative",
        "description": "膝盖受伤：避免深蹲、弓步、跳跃等对膝关节压力大的动作"
    },
}

# ===========================================================================
# Phase 2: 短期实施的重要损伤类型
# ===========================================================================

PHASE2_CONTRAINDICATION_RULES = {
    # 7. 前交叉韧带损伤 (ACL Injury)
    "前交叉韧带损伤": {
        "keywords_zh": [
            "深蹲", "弓步", "跳", "急停", "转向", "腿屈伸",
            "单腿", "侧向", "变向"
        ],
        "keywords_en": [
            "squat", "lunge", "jump", "pivot", "cutting", "leg extension",
            "single leg", "lateral", "agility"
        ],
        "primary_muscles": ["股四头肌", "腘绳肌", "臀大肌"],
        "severity": "absolute",
        "description": "前交叉韧带损伤：避免急停、转向和深度屈膝动作，ACL在这些动作中承受最大张力"
    },
    
    # 8. 网球肘 (Tennis Elbow)
    "网球肘": {
        "keywords_zh": [
            "反握", "腕伸", "前臂", "握力", "引体", "划船",
            "弯举", "反手"
        ],
        "keywords_en": [
            "reverse grip", "wrist extension", "forearm", "grip", "pull-up",
            "row", "curl", "supinated"
        ],
        "primary_muscles": ["前臂肌群", "肱桡肌"],
        "severity": "absolute",
        "description": "网球肘：避免腕关节伸展和前臂旋后动作，这些动作会拉伸受损的伸腕肌腱"
    },
    
    # 9. 高尔夫球肘 (Golfer's Elbow)
    "高尔夫球肘": {
        "keywords_zh": [
            "正握", "腕屈", "前臂", "弯举", "引体", "划船"
        ],
        "keywords_en": [
            "pronated grip", "wrist flexion", "forearm", "curl", "pull-up", "row"
        ],
        "primary_muscles": ["前臂肌群", "肱二头肌"],
        "severity": "absolute",
        "description": "高尔夫球肘：避免腕关节屈曲和前臂旋前动作，这些动作会拉伸受损的屈腕肌腱"
    },
    
    # 10. 颈椎病 (Cervical Spondylosis)
    "颈椎病": {
        "keywords_zh": [
            "耸肩", "颈部", "斜方肌", "头部", "倒立", "过头",
            "直立划船", "负重行走"
        ],
        "keywords_en": [
            "shrug", "neck", "trapezius", "head", "handstand", "overhead",
            "upright row", "farmer walk"
        ],
        "primary_muscles": ["上斜方肌", "颈部", "斜方肌"],
        "severity": "absolute",
        "description": "颈椎病：避免颈椎承重和过度伸展动作，这些动作会加重颈椎退化"
    },
}

# ===========================================================================
# Phase 3: 中期实施的补充损伤类型
# ===========================================================================

PHASE3_CONTRAINDICATION_RULES = {
    # 11. 跟腱炎 (Achilles Tendinitis)
    "跟腱炎": {
        "keywords_zh": [
            "提踵", "跳", "跑", "爬楼", "弓步", "深蹲", "冲刺"
        ],
        "keywords_en": [
            "calf raise", "jump", "run", "step", "lunge", "squat", "sprint"
        ],
        "primary_muscles": ["小腿", "腓肠肌", "比目鱼肌"],
        "severity": "absolute",
        "description": "跟腱炎：避免跳跃和提踵动作，这些动作会增加跟腱张力"
    },
    
    # 12. 足底筋膜炎 (Plantar Fasciitis)
    "足底筋膜炎": {
        "keywords_zh": [
            "跳", "跑", "提踵", "弓步", "爬楼", "冲刺"
        ],
        "keywords_en": [
            "jump", "run", "calf raise", "lunge", "step", "sprint"
        ],
        "primary_muscles": ["小腿"],
        "severity": "relative",
        "description": "足底筋膜炎：避免高冲击性动作，这些动作会拉伸足底筋膜"
    },
    
    # 13. 髂胫束综合征 (IT Band Syndrome)
    "髂胫束综合征": {
        "keywords_zh": [
            "跑", "跳", "侧向", "单腿", "弓步", "深蹲", "爬楼"
        ],
        "keywords_en": [
            "run", "jump", "lateral", "single leg", "lunge", "squat", "step"
        ],
        "primary_muscles": ["臀大肌", "臀中肌", "股四头肌"],
        "severity": "relative",
        "description": "髂胫束综合征：避免重复性膝关节屈伸动作，特别是跑步和侧向动作"
    },
    
    # 14. 腕管综合征 (Carpal Tunnel Syndrome)
    "腕管综合征": {
        "keywords_zh": [
            "俯卧撑", "手倒立", "腕弯举", "支撑", "握力", "前臂"
        ],
        "keywords_en": [
            "push-up", "handstand", "wrist curl", "plank", "grip", "forearm"
        ],
        "primary_muscles": ["前臂肌群"],
        "severity": "absolute",
        "description": "腕管综合征：避免腕关节过度屈曲和伸展动作，这些动作会压迫正中神经"
    },
}

# ===========================================================================
# 特殊人群禁忌症规则
# ===========================================================================

SPECIAL_POPULATION_RULES = {
    # 老年人 (65岁以上)
    "老年人骨质疏松": {
        "keywords_zh": [
            "跳", "冲击", "快速", "爆发", "转体", "扭转"
        ],
        "keywords_en": [
            "jump", "impact", "fast", "explosive", "twist", "rotation"
        ],
        "primary_muscles": [],  # 不限制特定肌群
        "severity": "caution",  # 谨慎使用
        "description": "老年人：避免高冲击性和快速旋转动作，骨质疏松增加骨折风险"
    },
    
    # 高血压患者
    "高血压": {
        "keywords_zh": [
            "硬拉", "深蹲", "倒立", "支撑", "最大", "1RM"
        ],
        "keywords_en": [
            "deadlift", "squat", "handstand", "plank", "max", "1rm"
        ],
        "primary_muscles": [],
        "severity": "caution",
        "description": "高血压：避免憋气动作和最大负荷训练，这些动作会急剧升高血压"
    },
}

# ===========================================================================
# 合并所有规则
# ===========================================================================

ALL_CONTRAINDICATION_RULES = {
    **PHASE1_CONTRAINDICATION_RULES,
    **PHASE2_CONTRAINDICATION_RULES,
    **PHASE3_CONTRAINDICATION_RULES,
    **SPECIAL_POPULATION_RULES,
}

# 导出规则统计
RULES_STATS = {
    "phase1_count": len(PHASE1_CONTRAINDICATION_RULES),
    "phase2_count": len(PHASE2_CONTRAINDICATION_RULES),
    "phase3_count": len(PHASE3_CONTRAINDICATION_RULES),
    "special_count": len(SPECIAL_POPULATION_RULES),
    "total_count": len(ALL_CONTRAINDICATION_RULES),
}
