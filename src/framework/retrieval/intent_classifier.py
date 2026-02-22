# -*- coding: utf-8 -*-
"""
查询意图分类器（规则引擎版）

根据查询文本的模式和关键词，将查询分为三类：
- structured: 可直接用 Neo4j Cypher 回答（动作-肌肉、器械、营养成分等）
- semantic: 需要语义理解的开放性问题 → Hybrid Search
- hybrid: 两路都走，融合结果

设计原则：纯规则+正则，零 LLM 调用，零延迟开销。

版本: v1.0.0
作者: 薛小川
日期: 2026-02-17
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """查询意图类型"""
    STRUCTURED = "structured"  # Neo4j Cypher 直查
    SEMANTIC = "semantic"      # Hybrid Search（BM25 + 向量 + RRF）
    HYBRID = "hybrid"          # 两路融合


class StructuredQueryType(Enum):
    """结构化查询子类型（对应 Cypher 模板）"""
    EXERCISE_MUSCLES = "exercise_muscles"       # 动作→肌肉
    MUSCLE_EXERCISES = "muscle_exercises"       # 肌肉→动作
    EXERCISE_EQUIPMENT = "exercise_equipment"   # 动作→器械
    EXERCISE_DETAILS = "exercise_details"       # 动作详情
    MUSCLE_CAPACITY = "muscle_capacity"         # 肌肉训练容量
    EXERCISE_BY_EQUIPMENT = "exercise_by_equipment"  # 器械→动作
    SAFETY_CONTRAINDICATIONS = "safety_contraindications"  # 安全禁忌查询
    POSTURAL_EXERCISES = "postural_exercises"              # 体态矫正动作查询
    STRENGTH_STANDARDS = "strength_standards"              # 力量标准查询
    EXERCISE_BY_LEVEL = "exercise_by_level"                # 按难度级别查询
    EXERCISE_BY_FORCE = "exercise_by_force"                # 按力类型分类
    EXERCISE_BY_MECHANIC = "exercise_by_mechanic"          # 按运动学机制分类
    # ─── v1.1.0 新增 6 种 ───
    SUPPLEMENT_ADVICE = "supplement_advice"                # 补剂咨询
    TRAINING_FREQUENCY = "training_frequency"              # 训练频率
    TRAINING_SPLIT = "training_split"                      # 训练分化
    EXERCISE_SUBSTITUTION = "exercise_substitution"        # 动作替代
    WARMUP_STRETCHING = "warmup_stretching"                # 热身拉伸
    NUTRITION_MACRO = "nutrition_macro"                    # 营养宏量


@dataclass
class IntentResult:
    """意图分类结果"""
    intent: QueryIntent
    confidence: float  # 0.0 ~ 1.0
    structured_type: Optional[StructuredQueryType] = None
    extracted_entity: Optional[str] = None  # 提取的实体（动作名/肌肉名等）
    reason: str = ""


# ─── 实体词典 ─────────────────────────────────────

# 常见动作名（用于实体提取）
EXERCISE_KEYWORDS = [
    "深蹲", "硬拉", "卧推", "引体向上", "划船", "推举", "弯举",
    "飞鸟", "臂屈伸", "腿举", "腿弯举", "腿屈伸", "小腿提踵",
    "罗马尼亚硬拉", "相扑硬拉", "前蹲", "颈前深蹲", "保加利亚分腿蹲",
    "俯卧撑", "双杠臂屈伸", "面拉", "侧平举", "前平举",
    "杠铃弯举", "哑铃弯举", "锤式弯举", "绳索下压",
    "高位下拉", "坐姿划船", "T杠划船", "杠铃划船",
    "上斜卧推", "下斜卧推", "哑铃卧推", "杠铃卧推",
    "肩推", "哑铃推举", "杠铃推举", "阿诺德推举",
    "山羊挺身", "仰卧起坐", "平板支撑", "卷腹",
    "箭步蹲", "臀桥", "臀推", "早安式体前屈",
]

# 常见肌肉名
MUSCLE_KEYWORDS = [
    "胸肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌",
    "股四头肌", "腘绳肌", "臀大肌", "小腿", "腓肠肌", "比目鱼肌",
    "斜方肌", "竖脊肌", "腹直肌", "腹外斜肌", "腹内斜肌",
    "前臂", "菱形肌", "大圆肌", "小圆肌", "冈下肌",
    "胸大肌", "胸小肌", "三角肌前束", "三角肌中束", "三角肌后束",
    "臀中肌", "臀小肌", "髂腰肌", "内收肌",
    "胸", "背", "肩", "手臂", "腿", "臀", "核心", "腹肌",
]

# 常见器械名
EQUIPMENT_KEYWORDS = [
    "杠铃", "哑铃", "绳索", "龙门架", "史密斯机",
    "弹力带", "壶铃", "TRX", "瑜伽垫", "泡沫轴",
    "腿举机", "坐姿推胸机", "高位下拉机", "蝴蝶机",
    "罗马椅", "卧推架", "深蹲架", "引体向上杆",
    "自重", "徒手",
]

# 安全禁忌相关关键词（损伤/疾病名）
INJURY_KEYWORDS = [
    "腰椎间盘突出", "膝盖损伤", "肩袖损伤", "高血压", "心脏病", "骨质疏松",
    "下背部疼痛", "前交叉韧带", "膝盖受伤", "髌骨软化", "髂胫束",
    "肩峰撞击", "肩部受伤", "腕管综合征", "腕部受伤",
    "跟腱炎", "足底筋膜炎", "踝关节扭伤", "颈椎病", "颈部受伤",
    "网球肘", "高尔夫球肘", "髋关节撞击", "髋滑囊炎", "髋部受伤",
    "腰部损伤", "膝盖", "肩部", "手腕", "脚踝", "颈部", "肘部", "髋部",
    # 口语化表达
    "腰突", "腰间盘", "腰痛", "腰疼", "腰不好",
    "膝盖疼", "膝盖痛", "膝盖不好", "膝关节",
    "肩膀疼", "肩膀痛", "肩痛", "肩伤",
    "脖子疼", "脖子痛", "颈椎",
    "手腕疼", "手腕痛", "鼠标手",
    "脚踝扭伤", "崴脚", "崴了脚",
    "跟腱", "足底", "脚底疼",
    "肘疼", "肘痛",
    "髋关节疼", "髋关节痛",
]

# 体态问题关键词
POSTURAL_KEYWORDS = [
    "圆肩", "驼背", "骨盆前倾", "骨盆后倾", "头前伸", "脊柱侧弯",
    "膝内扣", "膝超伸", "扁平足", "高弓足", "胸椎后凸", "腰椎前凸",
    "膝内翻", "膝外翻", "X型腿", "O型腿",
]

# 力量标准相关关键词
STRENGTH_STANDARD_KEYWORDS = [
    "力量标准", "力量水平", "什么水平", "多少算", "strength standard",
    "多少公斤", "多重算", "能推多少", "能蹲多少", "能拉多少",
]

# 健身水平关键词
FITNESS_LEVEL_KEYWORDS = [
    "新手", "初学者", "入门", "初级", "中级", "高级", "进阶", "专家",
    "beginner", "novice", "intermediate", "advanced", "expert",
    "适合新手", "新手动作", "初学者动作", "高级动作", "进阶动作",
]

# 力类型关键词
FORCE_TYPE_KEYWORDS = [
    "推", "拉", "push", "pull", "pressing", "pulling",
    "推类", "拉类", "推举", "推的动作", "拉的动作",
    "推力", "拉力", "水平推", "垂直推", "水平拉", "垂直拉",
]

# 运动学机制关键词
MECHANIC_TYPE_KEYWORDS = [
    "复合", "孤立", "compound", "isolation", "multi-joint", "single-joint",
    "复合动作", "孤立动作", "多关节", "单关节", "复合训练", "孤立训练",
]

# ─── v1.1.0 新增关键词词典 ─────────────────────────────

# 补剂关键词
SUPPLEMENT_KEYWORDS = [
    "蛋白粉", "肌酸", "BCAA", "支链氨基酸", "谷氨酰胺", "左旋肉碱",
    "氮泵", "增肌粉", "鱼油", "维生素D", "ZMA", "咖啡因",
    "补剂", "营养补充剂", "运动补剂", "蛋白质粉", "乳清蛋白",
    "酪蛋白", "植物蛋白粉", "增重粉", "pre-workout",
]

# 训练频率关键词
TRAINING_FREQUENCY_KEYWORDS = [
    "频率", "几次", "多久练一次", "休息几天", "恢复时间",
    "一周几练", "每周几次", "隔几天", "连续练", "休息日",
    "练几天", "训练频率", "训练天数",
]

# 训练分化关键词
TRAINING_SPLIT_KEYWORDS = [
    "分化", "分化训练", "推拉腿", "PPL", "上下肢分化",
    "胸背腿", "五天分化", "四天分化", "三天分化", "全身训练",
    "bro split", "训练安排", "训练计划", "周计划", "训练日",
    "怎么安排", "怎么分配",
]

# 动作替代关键词
SUBSTITUTION_KEYWORDS = [
    "替代", "替换", "代替", "没有", "不用", "换成",
    "替代动作", "替代方案", "类似动作", "相似动作",
    "用什么代替", "怎么替代", "可以换成",
]

# 热身拉伸关键词
WARMUP_STRETCHING_KEYWORDS = [
    "热身", "拉伸", "放松", "泡沫轴", "筋膜放松",
    "动态拉伸", "静态拉伸", "激活", "预热", "冷身",
    "训练前", "训练后", "练前", "练后", "warm up", "cool down",
    "肌肉放松", "关节活动",
]

# 营养宏量关键词
NUTRITION_KEYWORDS = [
    "蛋白质", "碳水", "碳水化合物", "脂肪", "热量", "卡路里",
    "摄入量", "宏量营养素", "macro", "TDEE", "基础代谢",
    "增肌饮食", "减脂饮食", "饮食计划", "营养", "膳食",
    "吃多少", "怎么吃", "饮食安排",
]


# ─── 结构化查询模式 ─────────────────────────────────

# 模式：动作 → 肌肉（"深蹲练哪些肌肉"、"卧推锻炼什么部位"）
EXERCISE_MUSCLE_PATTERNS = [
    r"(.+?)(?:练|锻炼|训练|刺激|激活|用到)(?:哪些?|什么|哪个|啥)(?:肌肉|肌群|部位|肌)",
    r"(.+?)(?:主要|主动|目标)(?:肌肉|肌群|部位)",
    r"(.+?)(?:能|可以)(?:练到|锻炼到|刺激到)(?:哪些?|什么)?(?:肌肉|肌群|部位)?",
    r"做(.+?)(?:时|的时候)(?:用到|练到|刺激)(?:哪些?|什么)(?:肌肉|肌群)?",
]

# 模式：肌肉 → 动作（"练胸肌的动作"、"怎么练背"）
MUSCLE_EXERCISE_PATTERNS = [
    r"(?:练|锻炼|训练|强化)(.+?)(?:的|用什么|有哪些?)(?:动作|方法|训练|运动|方式)",
    r"(.+?)(?:怎么练|如何练|如何锻炼|怎么锻炼|怎样练)",
    r"(?:哪些?|什么|啥)(?:动作|训练|运动)(?:练|锻炼|针对)(.+)",
    r"(?:针对|锻炼|训练)(.+?)(?:的|最好的|推荐的?)(?:动作|训练|运动)",
]

# 模式：动作 → 器械（"深蹲需要什么器械"）
EXERCISE_EQUIPMENT_PATTERNS = [
    r"(.+?)(?:需要|用|使用)(?:什么|哪些?|啥)(?:器械|器材|设备|工具)",
    r"做(.+?)(?:需要|用)(?:什么|哪些?)(?:器械|器材)?",
]

# 模式：器械 → 动作（"哑铃能做什么动作"）
EQUIPMENT_EXERCISE_PATTERNS = [
    r"(?:用)?(.+?)(?:能做|可以做|能练|可以练)(?:什么|哪些?)(?:动作|训练|运动)?",
    r"(.+?)(?:的|相关)(?:动作|训练|运动|练法)",
]

# 模式：动作详情（"深蹲怎么做"、"硬拉的正确姿势"）
EXERCISE_DETAIL_PATTERNS = [
    r"(.+?)(?:怎么做|怎样做|如何做|正确做法|正确姿势|动作要领|技术要点)",
    r"(.+?)(?:的)(?:正确|标准)(?:姿势|做法|动作|形式)",
]

# 模式：肌肉训练容量（"胸肌的训练量"、"背的MEV"）
MUSCLE_CAPACITY_PATTERNS = [
    r"(.+?)(?:的)?(?:训练量|训练容量|最大可恢复量|最小有效量|最大适应量)",
    r"(.+?)(?:的)?(?:MEV|MAV|MRV)",
]

# 模式：安全禁忌（"腰椎间盘突出不能做什么"、"膝盖损伤的禁忌动作"）
# 也覆盖带伤训练场景（"腰突能做什么训练"、"膝盖不好怎么练腿"）
SAFETY_CONTRAINDICATION_PATTERNS = [
    r"(.+?)(?:不能做|不适合做|禁忌|不可以做)(?:什么|哪些?)?(?:动作|运动|训练)?",
    r"(.+?)(?:的)?(?:禁忌|禁忌症|禁忌动作|危险动作|不宜做的动作)",
    r"(?:有|患有|得了)(.+?)(?:能|可以|适合)(?:做|练)(?:什么|哪些?)?",
    r"(.+?)(?:患者|人群)(?:不能|不适合|应该避免)(?:做|练)?(?:什么|哪些?)?(?:动作|运动)?",
    # 带伤训练场景
    r"(.+?)(?:适合做|适合练|可以做|可以练|能做|能练)(?:什么|哪些?)?(?:动作|运动|训练)?",
    r"(.+?)(?:不好|受伤|有伤)(?:怎么练|怎么训练|能练|还能练)",
    r"(.+?)(?:患者|的人)(?:的)?(?:安全训练|安全动作|推荐动作|适合的动作)",
    r"(.+?)(?:能|可以|适合)(?:做|练)(.+?)(?:吗|么|不)",
]

# 模式：体态矫正（"圆肩怎么矫正"、"骨盆前倾做什么动作"）
POSTURAL_EXERCISE_PATTERNS = [
    r"(.+?)(?:怎么矫正|如何矫正|怎么改善|如何改善|怎么纠正|如何纠正|怎么缓解)",
    r"(.+?)(?:矫正|改善|纠正|缓解)(?:动作|训练|方法|运动)",
    r"(?:矫正|改善|纠正|缓解)(.+?)(?:的|用什么)?(?:动作|训练|方法|运动)",
    r"(.+?)(?:做什么|练什么)(?:动作|运动)?(?:好|可以改善)?",
]

# 模式：力量标准（"深蹲多少公斤算中级"、"卧推力量标准"）
STRENGTH_STANDARD_PATTERNS = [
    r"(.+?)(?:的)?(?:力量标准|力量水平|什么水平)",
    r"(.+?)(?:多少|多重)(?:公斤|kg|KG)?(?:算|是)(?:什么水平|初级|中级|高级|精英)?",
    r"(.+?)(?:能|应该)(?:推|蹲|拉|举)(?:多少|多重)",
]

# 模式：健身水平（"适合新手的动作"、"初学者能做什么"）
FITNESS_LEVEL_PATTERNS = [
    re.compile(r"(适合|推荐给?)(新手|初学者|初级|中级|高级|进阶)", re.IGNORECASE),
    re.compile(r"(新手|初学者|初级|中级|高级|进阶)(适合|能做|可以做|推荐)的?(动作|训练|运动)", re.IGNORECASE),
    re.compile(r"(beginner|novice|intermediate|advanced|expert)\s*(exercise|workout|movement)", re.IGNORECASE),
]

# 模式：力类型（"推类动作"、"拉的训练"）
FORCE_TYPE_PATTERNS = [
    re.compile(r"(推|拉)(类|的|力)?(动作|训练|运动)", re.IGNORECASE),
    re.compile(r"(push|pull)(ing)?\s*(exercise|movement|workout)", re.IGNORECASE),
    re.compile(r"(水平|垂直)(推|拉)", re.IGNORECASE),
]

# 模式：运动学机制（"复合动作"、"孤立训练"）
MECHANIC_TYPE_PATTERNS = [
    re.compile(r"(复合|孤立)(动作|训练|运动)", re.IGNORECASE),
    re.compile(r"(compound|isolation)\s*(exercise|movement|workout)", re.IGNORECASE),
    re.compile(r"(多|单)关节(动作|训练)?", re.IGNORECASE),
]

# ─── v1.1.0 新增 6 种模式 ─────────────────────────────

# 模式：补剂咨询（"蛋白粉怎么选"、"肌酸什么时候吃"、"需要吃补剂吗"）
SUPPLEMENT_PATTERNS = [
    re.compile(r"(.+?)(?:怎么选|怎么吃|什么时候吃|吃多少|有用吗|有必要吃|需要吃)", re.IGNORECASE),
    re.compile(r"(?:推荐|选择|购买)(?:什么|哪种|哪个)(.+?)(?:好|合适)?", re.IGNORECASE),
    re.compile(r"(.+?)(?:和|与|跟)(.+?)(?:区别|差别|哪个好|怎么选)", re.IGNORECASE),
    re.compile(r"(.+?)(?:的)?(?:作用|功效|效果|副作用|用法|用量)", re.IGNORECASE),
]

# 模式：训练频率（"胸肌多久练一次"、"一周练几次"）
TRAINING_FREQUENCY_PATTERNS = [
    re.compile(r"(.+?)(?:多久|多长时间|几天)(?:练|训练)一次", re.IGNORECASE),
    re.compile(r"一周(?:练|训练)几(?:次|天)", re.IGNORECASE),
    re.compile(r"(.+?)(?:的)?(?:训练频率|恢复时间|休息时间)", re.IGNORECASE),
    re.compile(r"(?:每周|一周)(?:练|训练)(.+?)几次", re.IGNORECASE),
    re.compile(r"(.+?)(?:需要|应该)(?:休息|恢复)(?:几天|多久)", re.IGNORECASE),
]

# 模式：训练分化（"推拉腿怎么安排"、"五天分化计划"）
TRAINING_SPLIT_PATTERNS = [
    re.compile(r"(推拉腿|PPL|上下肢|胸背腿|全身)(?:分化|训练|计划|怎么安排|怎么练)", re.IGNORECASE),
    re.compile(r"(三天|四天|五天|六天|[3-6]天)(?:分化|训练|计划|安排)", re.IGNORECASE),
    re.compile(r"(?:训练|健身)(?:怎么|如何)(?:分化|安排|分配|规划)", re.IGNORECASE),
    re.compile(r"(?:制定|设计|安排)(?:一个|一份)?(?:训练|健身)(?:计划|方案)", re.IGNORECASE),
]

# 模式：动作替代（"没有杠铃怎么练深蹲"、"引体向上的替代动作"）
EXERCISE_SUBSTITUTION_PATTERNS = [
    re.compile(r"(?:没有|不用|不想用)(.+?)(?:怎么|如何|用什么)(?:练|做|替代)(.+?)", re.IGNORECASE),
    re.compile(r"(.+?)(?:的)?(?:替代|替换|代替)(?:动作|方案|方法)", re.IGNORECASE),
    re.compile(r"(?:用什么|什么动作)(?:替代|代替|替换)(.+)", re.IGNORECASE),
    re.compile(r"(.+?)(?:可以|能)(?:用|换成)(.+?)(?:替代|代替|替换)?", re.IGNORECASE),
]

# 模式：热身拉伸（"深蹲前怎么热身"、"训练后怎么拉伸"）
WARMUP_STRETCHING_PATTERNS = [
    re.compile(r"(.+?)(?:前|之前)(?:怎么|如何)?(?:热身|拉伸|激活|预热)", re.IGNORECASE),
    re.compile(r"(.+?)(?:后|之后)(?:怎么|如何)?(?:拉伸|放松|冷身|恢复)", re.IGNORECASE),
    re.compile(r"(?:怎么|如何)(?:热身|拉伸|放松|激活)(.+?)", re.IGNORECASE),
    re.compile(r"(.+?)(?:的)?(?:热身|拉伸|放松|激活)(?:动作|方法|方式)", re.IGNORECASE),
]

# 模式：营养宏量（"增肌期蛋白质摄入量"、"减脂碳水怎么安排"）
NUTRITION_MACRO_PATTERNS = [
    re.compile(r"(增肌|减脂|维持)(?:期)?(?:的)?(.+?)(?:摄入量|吃多少|怎么安排|怎么吃)", re.IGNORECASE),
    re.compile(r"(.+?)(?:的)?(?:摄入量|需求量|推荐量|每日摄入)", re.IGNORECASE),
    re.compile(r"(?:每天|一天)(?:需要|应该)?(?:吃|摄入)(?:多少)(.+)", re.IGNORECASE),
    re.compile(r"(?:怎么|如何)(?:计算|安排)(.+?)(?:摄入|饮食|营养)", re.IGNORECASE),
    re.compile(r"(TDEE|基础代谢|热量缺口|热量盈余)(?:怎么算|是多少|怎么计算)", re.IGNORECASE),
]


def classify_intent(query: str) -> IntentResult:
    """
    分类查询意图

    Args:
        query: 用户查询文本

    Returns:
        IntentResult: 分类结果
    """
    query_clean = query.strip()

    # 1. 尝试匹配结构化模式
    structured_result = _match_structured_patterns(query_clean)
    if structured_result and structured_result.confidence >= 0.7:
        logger.info(
            f"🎯 意图分类: STRUCTURED ({structured_result.structured_type.value}), "
            f"实体='{structured_result.extracted_entity}', "
            f"置信度={structured_result.confidence:.2f}"
        )
        return structured_result

    # 2. 检查是否包含结构化实体但模式不明确 → hybrid
    has_exercise = any(kw in query_clean for kw in EXERCISE_KEYWORDS)
    has_muscle = any(kw in query_clean for kw in MUSCLE_KEYWORDS)
    has_equipment = any(kw in query_clean for kw in EQUIPMENT_KEYWORDS)
    has_injury = any(kw in query_clean for kw in INJURY_KEYWORDS)
    has_postural = any(kw in query_clean for kw in POSTURAL_KEYWORDS)
    has_force = any(k in query_clean for k in FORCE_TYPE_KEYWORDS[:6])
    has_mechanic = any(k in query_clean for k in MECHANIC_TYPE_KEYWORDS[:6])
    has_supplement = any(kw in query_clean for kw in SUPPLEMENT_KEYWORDS)
    has_nutrition = any(kw in query_clean for kw in NUTRITION_KEYWORDS)

    if (has_exercise or has_muscle or has_equipment or has_injury
            or has_postural or has_supplement or has_nutrition) and len(query_clean) > 10:
        # 有实体但查询较长/复杂 → hybrid
        entity = _extract_first_entity(query_clean)
        logger.info(
            f"🎯 意图分类: HYBRID, 实体='{entity}', "
            f"原因='含结构化实体但查询复杂'"
        )
        return IntentResult(
            intent=QueryIntent.HYBRID,
            confidence=0.6,
            extracted_entity=entity,
            reason="含结构化实体但查询复杂，两路融合"
        )

    # 3. 默认 → semantic
    logger.info(f"🎯 意图分类: SEMANTIC, 原因='无结构化模式匹配'")
    return IntentResult(
        intent=QueryIntent.SEMANTIC,
        confidence=0.8,
        reason="语义查询，使用混合检索"
    )


def _match_structured_patterns(query: str) -> Optional[IntentResult]:
    """尝试匹配结构化查询模式"""

    # 动作 → 肌肉
    for pattern in EXERCISE_MUSCLE_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_exercise(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.9,
                    structured_type=StructuredQueryType.EXERCISE_MUSCLES,
                    extracted_entity=entity,
                    reason=f"动作→肌肉查询: {entity}"
                )

    # 肌肉 → 动作
    for pattern in MUSCLE_EXERCISE_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_muscle(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.9,
                    structured_type=StructuredQueryType.MUSCLE_EXERCISES,
                    extracted_entity=entity,
                    reason=f"肌肉→动作查询: {entity}"
                )

    # 动作 → 器械
    for pattern in EXERCISE_EQUIPMENT_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_exercise(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.EXERCISE_EQUIPMENT,
                    extracted_entity=entity,
                    reason=f"动作→器械查询: {entity}"
                )

    # 器械 → 动作
    for pattern in EQUIPMENT_EXERCISE_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_equipment(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.EXERCISE_BY_EQUIPMENT,
                    extracted_entity=entity,
                    reason=f"器械→动作查询: {entity}"
                )

    # 动作详情
    for pattern in EXERCISE_DETAIL_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_exercise(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.8,
                    structured_type=StructuredQueryType.EXERCISE_DETAILS,
                    extracted_entity=entity,
                    reason=f"动作详情查询: {entity}"
                )

    # 肌肉训练容量
    for pattern in MUSCLE_CAPACITY_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_muscle(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.MUSCLE_CAPACITY,
                    extracted_entity=entity,
                    reason=f"肌肉训练容量查询: {entity}"
                )

    # 安全禁忌查询
    for pattern in SAFETY_CONTRAINDICATION_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            # 清理实体：去掉尾部标点、助词、前缀
            entity = re.sub(r'[，,。.、的了]$', '', entity)
            entity = re.sub(r'^(?:我有|我的|我)', '', entity)
            entity = entity.strip()
            if _is_valid_injury(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.9,
                    structured_type=StructuredQueryType.SAFETY_CONTRAINDICATIONS,
                    extracted_entity=entity,
                    reason=f"安全禁忌查询: {entity}"
                )

    # 体态矫正动作查询
    for pattern in POSTURAL_EXERCISE_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_postural(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.9,
                    structured_type=StructuredQueryType.POSTURAL_EXERCISES,
                    extracted_entity=entity,
                    reason=f"体态矫正查询: {entity}"
                )

    # 力量标准查询
    for pattern in STRENGTH_STANDARD_PATTERNS:
        m = re.search(pattern, query)
        if m:
            entity = m.group(1).strip()
            if _is_valid_exercise(entity) or _is_valid_strength_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.STRENGTH_STANDARDS,
                    extracted_entity=entity,
                    reason=f"力量标准查询: {entity}"
                )

    # 健身水平查询（"适合新手的动作"、"初学者能做什么"）
    for pattern in FITNESS_LEVEL_PATTERNS:
        m = pattern.search(query)
        if m:
            # 尝试所有捕获组，找到有效的水平关键词
            entity = None
            for gi in range(1, (m.lastindex or 0) + 1):
                candidate = m.group(gi).strip() if m.group(gi) else ""
                if _is_valid_level_query(candidate):
                    entity = candidate
                    break
            if entity is None:
                entity = m.group(0).strip()
            if _is_valid_level_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.EXERCISE_BY_LEVEL,
                    extracted_entity=entity,
                    reason=f"健身水平查询: {entity}"
                )

    # 力类型查询（"推类动作"、"拉的训练"）
    for pattern in FORCE_TYPE_PATTERNS:
        m = pattern.search(query)
        if m:
            entity = m.group(1) if m.lastindex >= 1 else m.group(0)
            entity = entity.strip()
            if _is_valid_force_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.EXERCISE_BY_FORCE,
                    extracted_entity=entity,
                    reason=f"力类型查询: {entity}"
                )

    # 运动学机制查询（"复合动作"、"孤立训练"）
    for pattern in MECHANIC_TYPE_PATTERNS:
        m = pattern.search(query)
        if m:
            entity = m.group(1) if m.lastindex >= 1 else m.group(0)
            entity = entity.strip()
            if _is_valid_mechanic_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.EXERCISE_BY_MECHANIC,
                    extracted_entity=entity,
                    reason=f"运动学机制查询: {entity}"
                )

    # ─── v1.1.0 新增 6 种模式匹配 ───

    # 补剂咨询（"蛋白粉怎么选"、"肌酸什么时候吃"）
    for pattern in SUPPLEMENT_PATTERNS:
        m = pattern.search(query)
        if m:
            entity = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            entity = entity.strip()
            if _is_valid_supplement(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.SUPPLEMENT_ADVICE,
                    extracted_entity=entity,
                    reason=f"补剂咨询: {entity}"
                )

    # 训练频率（"胸肌多久练一次"、"一周练几次"）
    for pattern in TRAINING_FREQUENCY_PATTERNS:
        m = pattern.search(query)
        if m:
            entity = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            entity = entity.strip() if entity else "通用"
            if _is_valid_frequency_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.80,
                    structured_type=StructuredQueryType.TRAINING_FREQUENCY,
                    extracted_entity=entity,
                    reason=f"训练频率查询: {entity}"
                )

    # 训练分化（"推拉腿怎么安排"、"五天分化计划"）
    for pattern in TRAINING_SPLIT_PATTERNS:
        m = pattern.search(query)
        if m:
            entity = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            entity = entity.strip() if entity else "通用"
            if _is_valid_split_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.80,
                    structured_type=StructuredQueryType.TRAINING_SPLIT,
                    extracted_entity=entity,
                    reason=f"训练分化查询: {entity}"
                )

    # 动作替代（"没有杠铃怎么练深蹲"、"引体向上的替代动作"）
    for pattern in EXERCISE_SUBSTITUTION_PATTERNS:
        m = pattern.search(query)
        if m:
            entity = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            entity = entity.strip()
            if _is_valid_substitution_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.85,
                    structured_type=StructuredQueryType.EXERCISE_SUBSTITUTION,
                    extracted_entity=entity,
                    reason=f"动作替代查询: {entity}"
                )

    # 热身拉伸（"深蹲前怎么热身"、"训练后怎么拉伸"）
    for pattern in WARMUP_STRETCHING_PATTERNS:
        m = pattern.search(query)
        if m:
            entity = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            entity = entity.strip()
            if _is_valid_warmup_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.80,
                    structured_type=StructuredQueryType.WARMUP_STRETCHING,
                    extracted_entity=entity,
                    reason=f"热身拉伸查询: {entity}"
                )

    # 营养宏量（"增肌期蛋白质摄入量"、"减脂碳水怎么安排"）
    for pattern in NUTRITION_MACRO_PATTERNS:
        m = pattern.search(query)
        if m:
            entity = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            entity = entity.strip()
            if _is_valid_nutrition_query(entity):
                return IntentResult(
                    intent=QueryIntent.STRUCTURED,
                    confidence=0.80,
                    structured_type=StructuredQueryType.NUTRITION_MACRO,
                    extracted_entity=entity,
                    reason=f"营养宏量查询: {entity}"
                )

    return None


def _is_valid_exercise(entity: str) -> bool:
    """检查是否是有效的动作名"""
    if not entity or len(entity) > 15:
        return False
    return any(kw in entity for kw in EXERCISE_KEYWORDS)


def _is_valid_muscle(entity: str) -> bool:
    """检查是否是有效的肌肉名"""
    if not entity or len(entity) > 10:
        return False
    return any(kw in entity for kw in MUSCLE_KEYWORDS)


def _is_valid_equipment(entity: str) -> bool:
    """检查是否是有效的器械名"""
    if not entity or len(entity) > 10:
        return False
    return any(kw in entity for kw in EQUIPMENT_KEYWORDS)


def _is_valid_injury(entity: str) -> bool:
    """检查是否是有效的损伤/疾病名"""
    if not entity or len(entity) > 15:
        return False
    return any(kw in entity for kw in INJURY_KEYWORDS)


def _is_valid_postural(entity: str) -> bool:
    """检查是否是有效的体态问题名"""
    if not entity or len(entity) > 15:
        return False
    return any(kw in entity for kw in POSTURAL_KEYWORDS)


def _is_valid_strength_query(entity: str) -> bool:
    """检查是否是有效的力量标准查询实体"""
    if not entity or len(entity) > 15:
        return False
    return any(kw in entity for kw in STRENGTH_STANDARD_KEYWORDS)


def _is_valid_level_query(keyword: str) -> bool:
    """检查是否是有效的健身水平查询"""
    return any(k in keyword for k in ["新手", "初学", "初级", "中级", "高级", "进阶", "beginner", "intermediate", "advanced"])


def _is_valid_force_query(keyword: str) -> bool:
    """检查是否是有效的力类型查询"""
    return any(k in keyword for k in ["推", "拉", "push", "pull"])


def _is_valid_mechanic_query(keyword: str) -> bool:
    """检查是否是有效的运动学机制查询"""
    return any(k in keyword for k in ["复合", "孤立", "compound", "isolation", "多关节", "单关节"])


def _is_valid_supplement(entity: str) -> bool:
    """检查是否是有效的补剂名"""
    if not entity or len(entity) > 15:
        return False
    return any(kw in entity for kw in SUPPLEMENT_KEYWORDS)


def _is_valid_frequency_query(entity: str) -> bool:
    """检查是否是有效的训练频率查询"""
    if not entity:
        return False
    # 包含肌肉名或训练频率关键词
    return (any(kw in entity for kw in MUSCLE_KEYWORDS)
            or any(kw in entity for kw in TRAINING_FREQUENCY_KEYWORDS)
            or entity == "通用")


def _is_valid_split_query(entity: str) -> bool:
    """检查是否是有效的训练分化查询"""
    if not entity:
        return False
    return any(kw in entity for kw in TRAINING_SPLIT_KEYWORDS + [
        "推拉腿", "PPL", "上下肢", "胸背腿", "全身",
        "三天", "四天", "五天", "六天", "3天", "4天", "5天", "6天",
        "训练", "健身",
    ])


def _is_valid_substitution_query(entity: str) -> bool:
    """检查是否是有效的动作替代查询"""
    if not entity or len(entity) > 20:
        return False
    return (any(kw in entity for kw in EXERCISE_KEYWORDS)
            or any(kw in entity for kw in EQUIPMENT_KEYWORDS)
            or any(kw in entity for kw in SUBSTITUTION_KEYWORDS))


def _is_valid_warmup_query(entity: str) -> bool:
    """检查是否是有效的热身拉伸查询"""
    if not entity or len(entity) > 15:
        return False
    return (any(kw in entity for kw in EXERCISE_KEYWORDS)
            or any(kw in entity for kw in MUSCLE_KEYWORDS)
            or any(kw in entity for kw in WARMUP_STRETCHING_KEYWORDS)
            or entity in ["训练", "健身", "运动", "力量训练", "有氧"])


def _is_valid_nutrition_query(entity: str) -> bool:
    """检查是否是有效的营养宏量查询"""
    if not entity or len(entity) > 15:
        return False
    return (any(kw in entity for kw in NUTRITION_KEYWORDS)
            or entity in ["增肌", "减脂", "维持", "TDEE", "基础代谢"])


def _extract_first_entity(query: str) -> Optional[str]:
    """从查询中提取第一个匹配的实体"""
    for kw in EXERCISE_KEYWORDS:
        if kw in query:
            return kw
    for kw in MUSCLE_KEYWORDS:
        if kw in query:
            return kw
    for kw in EQUIPMENT_KEYWORDS:
        if kw in query:
            return kw
    for kw in INJURY_KEYWORDS:
        if kw in query:
            return kw
    for kw in POSTURAL_KEYWORDS:
        if kw in query:
            return kw
    for kw in FITNESS_LEVEL_KEYWORDS:
        if kw in query:
            return kw
    for kw in FORCE_TYPE_KEYWORDS:
        if kw in query:
            return kw
    for kw in MECHANIC_TYPE_KEYWORDS:
        if kw in query:
            return kw
    for kw in SUPPLEMENT_KEYWORDS:
        if kw in query:
            return kw
    for kw in NUTRITION_KEYWORDS:
        if kw in query:
            return kw
    return None
