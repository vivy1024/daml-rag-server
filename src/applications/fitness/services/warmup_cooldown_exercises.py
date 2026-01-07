"""
热身和放松动作配置模块

基于运动学教授和专业教练的视角，从1790个动作中精选热身和放松动作。
采用硬编码方式确保动作选择的专业性和安全性。

设计原则：
1. 热身动作：提升体温、激活目标肌群、增加关节活动度、预防损伤
2. 放松动作：降低心率、拉伸肌肉、促进恢复、减少延迟性肌肉酸痛

科学依据：
- ACSM建议：热身5-10分钟，包含轻度有氧和动态拉伸
- NSCA建议：放松5-10分钟，包含静态拉伸和呼吸练习

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2026-01-06
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class TrainingFocus(str, Enum):
    """训练重点分类"""
    UPPER_BODY = "upper_body"      # 上肢
    LOWER_BODY = "lower_body"      # 下肢
    PUSH = "push"                  # 推类
    PULL = "pull"                  # 拉类
    LEGS = "legs"                  # 腿部
    FULL_BODY = "full_body"        # 全身
    CORE = "core"                  # 核心
    CHEST = "chest"                # 胸部
    BACK = "back"                  # 背部
    SHOULDERS = "shoulders"        # 肩部


@dataclass
class WarmupExercise:
    """热身动作配置"""
    exercise_id: int
    name_zh: str
    duration_seconds: int  # 持续时间（秒）
    sets: int = 1
    reps: Optional[int] = None  # 如果是次数型动作
    notes: str = ""


@dataclass
class CooldownExercise:
    """放松动作配置"""
    exercise_id: int
    name_zh: str
    duration_seconds: int  # 持续时间（秒）
    sets: int = 1
    notes: str = ""


# =============================================================================
# 通用热身动作（适用于所有训练）
# =============================================================================

GENERAL_WARMUP_CARDIO: List[WarmupExercise] = [
    # 轻度有氧 - 提升体温和心率
    WarmupExercise(1201, "跑步机步行", 120, notes="中等速度，逐渐加快"),
    WarmupExercise(1199, "跑步机慢跑", 180, notes="轻松配速，不要气喘"),
    WarmupExercise(1569, "动感单车", 180, notes="低阻力，中等转速"),
    WarmupExercise(1696, "椭圆机", 180, notes="低阻力，全身协调"),
    WarmupExercise(1597, "跳绳", 60, notes="基础跳法，保持节奏"),
    WarmupExercise(1102, "有氧开合跳", 60, sets=2, reps=20, notes="动态热身首选"),
]

GENERAL_WARMUP_DYNAMIC: List[WarmupExercise] = [
    # 动态拉伸 - 增加关节活动度
    WarmupExercise(1594, "尺蠖爬行", 60, sets=2, reps=5, notes="全身动态热身"),
    WarmupExercise(1251, "交替环绕", 30, sets=1, reps=10, notes="髋关节活动"),
    WarmupExercise(1463, "站立八字髋关节活动", 30, sets=1, reps=10, notes="髋关节灵活性"),
    WarmupExercise(1600, "脚踝画圈", 30, sets=1, reps=10, notes="踝关节活动"),
    WarmupExercise(1358, "站立颈部绕圈", 20, sets=1, reps=5, notes="颈部放松"),
]


# =============================================================================
# 上肢热身动作
# =============================================================================

UPPER_BODY_WARMUP: List[WarmupExercise] = [
    # 肩部激活
    WarmupExercise(1288, "站姿侧平举", 30, sets=2, reps=10, notes="轻重量或无重量"),
    WarmupExercise(1280, "站立肩部屈曲活动性", 30, sets=1, reps=10, notes="肩关节活动"),
    WarmupExercise(1283, "肩外旋/肩内旋", 30, sets=1, reps=10, notes="肩袖激活"),
    WarmupExercise(1598, "墙上天使", 30, sets=2, reps=10, notes="肩胛骨活动"),
    WarmupExercise(1221, "肩胛稳定圈", 30, sets=1, reps=10, notes="肩胛骨稳定"),
    # 胸背激活
    WarmupExercise(1298, "肩胛收缩", 30, sets=2, reps=10, notes="背部激活"),
    WarmupExercise(1299, "肩胛前伸", 30, sets=2, reps=10, notes="前锯肌激活"),
    WarmupExercise(1295, "前锯肌激活平板支撑", 30, sets=1, notes="核心+前锯肌"),
    # 手臂激活
    WarmupExercise(1228, "手腕伸肌松动", 20, sets=1, reps=10, notes="前臂热身"),
]

CHEST_WARMUP: List[WarmupExercise] = [
    WarmupExercise(1598, "墙上天使", 30, sets=2, reps=10, notes="胸椎活动"),
    WarmupExercise(1295, "前锯肌激活平板支撑", 30, sets=2, notes="前锯肌激活"),
    WarmupExercise(1291, "前锯肌激活：反手直拳", 30, sets=2, reps=10, notes="肩胛稳定"),
    WarmupExercise(1219, "卧推起杠（主动）", 20, sets=2, reps=5, notes="卧推动作模式激活"),
]

BACK_WARMUP: List[WarmupExercise] = [
    WarmupExercise(1298, "肩胛收缩", 30, sets=2, reps=15, notes="背部激活首选"),
    WarmupExercise(1250, "俯卧T字抬臂", 30, sets=2, reps=10, notes="中背激活"),
    WarmupExercise(1301, "肩胛下压", 30, sets=2, reps=10, notes="下斜方肌激活"),
    WarmupExercise(1417, "地面泡沫轴背阔肌活动", 30, sets=1, notes="背阔肌松动"),
]

SHOULDER_WARMUP: List[WarmupExercise] = [
    WarmupExercise(1306, "肩袖外旋 1", 30, sets=2, reps=10, notes="肩袖激活"),
    WarmupExercise(1305, "肩袖外旋 2", 30, sets=2, reps=10, notes="肩袖激活变体"),
    WarmupExercise(1285, "弹力带肩部Y举", 30, sets=2, reps=10, notes="三角肌激活"),
    WarmupExercise(1286, "俯卧撑姿势：肩部时钟", 30, sets=1, reps=5, notes="肩关节稳定"),
]


# =============================================================================
# 下肢热身动作
# =============================================================================

LOWER_BODY_WARMUP: List[WarmupExercise] = [
    # 髋关节激活
    WarmupExercise(1463, "站立八字髋关节活动", 30, sets=1, reps=10, notes="髋关节灵活性"),
    WarmupExercise(1471, "开髋动作", 30, sets=1, reps=10, notes="髋关节打开"),
    WarmupExercise(1357, "站立动态臀部拉伸（抱膝）", 30, sets=1, reps=10, notes="臀部激活"),
    # 臀部激活
    WarmupExercise(1411, "贝壳式 1 侧卧", 30, sets=2, reps=15, notes="臀中肌激活"),
    WarmupExercise(1469, "弹力带臀桥", 30, sets=2, reps=10, notes="臀大肌激活"),
    WarmupExercise(1317, "弹力带臀部后踢（保持）", 20, sets=2, reps=10, notes="臀部激活"),
    # 腿部激活
    WarmupExercise(1483, "站立迷你阻力带髋屈", 30, sets=2, reps=10, notes="髋屈肌激活"),
    WarmupExercise(1596, "靠墙静蹲", 30, sets=2, notes="股四头肌激活"),
    # 踝关节
    WarmupExercise(1600, "脚踝画圈", 20, sets=1, reps=10, notes="踝关节活动"),
    WarmupExercise(1380, "靠墙踝背屈", 20, sets=2, reps=10, notes="踝关节灵活性"),
]

LEGS_WARMUP: List[WarmupExercise] = [
    # 动态拉伸
    WarmupExercise(1475, "站立交替动态内收肌拉伸", 30, sets=1, reps=10, notes="内收肌激活"),
    WarmupExercise(1337, "站立双侧动态大腿后侧拉伸", 30, sets=1, reps=10, notes="腘绳肌激活"),
    WarmupExercise(1479, "髋屈肌拉伸：跪姿弓步 1", 30, sets=1, reps=5, notes="髋屈肌拉伸"),
    # 激活动作
    WarmupExercise(1411, "贝壳式 1 侧卧", 30, sets=2, reps=15, notes="臀中肌激活"),
    WarmupExercise(1469, "弹力带臀桥", 30, sets=2, reps=10, notes="臀大肌激活"),
    WarmupExercise(1596, "靠墙静蹲", 30, sets=2, notes="股四头肌激活"),
    # 小腿
    WarmupExercise(1451, "提踵 1A 双腿 离心 地面", 20, sets=2, reps=10, notes="小腿激活"),
]


# =============================================================================
# 核心热身动作
# =============================================================================

CORE_WARMUP: List[WarmupExercise] = [
    WarmupExercise(204, "前臂平板支撑", 30, sets=2, notes="核心激活基础"),
    WarmupExercise(1395, "核心稳定 1：四点支撑对侧抬肢", 30, sets=2, reps=10, notes="核心稳定"),
    WarmupExercise(1392, "核心稳定 2：对侧触肩（四点支撑位）", 30, sets=2, reps=10, notes="抗旋转"),
    WarmupExercise(1386, "同侧死虫式", 30, sets=2, reps=10, notes="腹部激活"),
    WarmupExercise(1387, "交叉对侧死虫式", 30, sets=2, reps=10, notes="核心协调"),
    WarmupExercise(326, "侧平板支撑（手撑）", 20, sets=2, notes="侧链激活"),
]


# =============================================================================
# 放松动作配置 - 静态拉伸
# =============================================================================

GENERAL_COOLDOWN: List[CooldownExercise] = [
    # 全身放松
    CooldownExercise(617, "儿童式（双臂前伸）", 60, notes="全身放松首选"),
    CooldownExercise(619, "儿童式（双臂贴身）", 60, notes="背部放松"),
    CooldownExercise(1319, "祈祷式拉伸 1", 60, notes="背部和肩部放松"),
    CooldownExercise(629, "尸体式", 120, notes="最终放松，调整呼吸"),
]

UPPER_BODY_COOLDOWN: List[CooldownExercise] = [
    # 胸部拉伸
    CooldownExercise(127, "胸肌拉伸（变体一）", 30, notes="胸大肌拉伸"),
    CooldownExercise(125, "胸肌拉伸（变体三）", 30, notes="胸小肌拉伸"),
    # 背部拉伸
    CooldownExercise(144, "背阔肌拉伸（变式一）", 30, notes="背阔肌拉伸"),
    CooldownExercise(143, "背阔肌拉伸 — 变体二", 30, notes="背阔肌深度拉伸"),
    CooldownExercise(617, "儿童式（双臂前伸）", 45, notes="背部整体放松"),
    # 肩部拉伸
    CooldownExercise(141, "肩部拉伸 — 变体一", 30, notes="三角肌前束拉伸"),
    CooldownExercise(138, "肩部拉伸（变体四）", 30, notes="三角肌后束拉伸"),
    CooldownExercise(1287, "肩部外展拉伸", 30, notes="肩关节放松"),
    # 手臂拉伸
    CooldownExercise(137, "肱三头肌拉伸（变体一）", 30, notes="三头肌拉伸"),
    CooldownExercise(123, "二头肌拉伸（变体一）", 30, notes="二头肌拉伸"),
    # 斜方肌拉伸
    CooldownExercise(134, "斜方肌拉伸（变式一）", 30, notes="上斜方肌拉伸"),
    CooldownExercise(1231, "坐姿上斜方肌和冈上肌拉伸", 30, notes="肩颈放松"),
]


CHEST_COOLDOWN: List[CooldownExercise] = [
    CooldownExercise(127, "胸肌拉伸（变体一）", 45, notes="胸大肌主要拉伸"),
    CooldownExercise(126, "胸部拉伸（变式二）", 30, notes="胸肌深度拉伸"),
    CooldownExercise(141, "肩部拉伸 — 变体一", 30, notes="三角肌前束拉伸"),
    CooldownExercise(137, "肱三头肌拉伸（变体一）", 30, notes="三头肌拉伸"),
    CooldownExercise(683, "辅助鱼式", 45, notes="胸椎伸展"),
]

BACK_COOLDOWN: List[CooldownExercise] = [
    CooldownExercise(617, "儿童式（双臂前伸）", 60, notes="背阔肌拉伸"),
    CooldownExercise(144, "背阔肌拉伸（变式一）", 45, notes="背阔肌深度拉伸"),
    CooldownExercise(168, "斜方肌/中背拉伸（变体一）", 30, notes="中背放松"),
    CooldownExercise(123, "二头肌拉伸（变体一）", 30, notes="二头肌拉伸"),
    CooldownExercise(625, "猫式", 30, notes="脊柱灵活性"),
]

SHOULDER_COOLDOWN: List[CooldownExercise] = [
    CooldownExercise(141, "肩部拉伸 — 变体一", 45, notes="三角肌前束拉伸"),
    CooldownExercise(139, "肩部拉伸 — 变体三", 30, notes="三角肌中束拉伸"),
    CooldownExercise(138, "肩部拉伸（变体四）", 30, notes="三角肌后束拉伸"),
    CooldownExercise(134, "斜方肌拉伸（变式一）", 30, notes="上斜方肌拉伸"),
    CooldownExercise(1303, "侧卧肩袖外旋拉伸", 30, notes="肩袖放松"),
    CooldownExercise(660, "小狗式", 45, notes="肩部深度拉伸"),
]

LOWER_BODY_COOLDOWN: List[CooldownExercise] = [
    # 股四头肌拉伸
    CooldownExercise(131, "大腿前侧拉伸（变体一）", 30, notes="股四头肌拉伸"),
    CooldownExercise(1212, "跪姿股四头肌拉伸", 45, notes="股四头肌深度拉伸"),
    # 腘绳肌拉伸
    CooldownExercise(148, "腿后侧拉伸（变体一）", 30, notes="腘绳肌拉伸"),
    CooldownExercise(1329, "仰卧大腿后侧静态拉伸", 45, notes="腘绳肌深度拉伸"),
    # 臀部拉伸
    CooldownExercise(151, "臀部拉伸（变体一）", 30, notes="臀大肌拉伸"),
    CooldownExercise(665, "仰卧鸽式", 45, notes="臀部深度拉伸"),
    CooldownExercise(658, "鸽子式", 60, notes="髋关节放松"),
    # 内收肌拉伸
    CooldownExercise(1470, "坐姿双侧内收肌静态拉伸", 30, notes="内收肌拉伸"),
    # 小腿拉伸
    CooldownExercise(158, "小腿拉伸（变体一）", 30, notes="腓肠肌拉伸"),
    CooldownExercise(1262, "比目鱼肌拉伸", 30, notes="比目鱼肌拉伸"),
    # 髋屈肌拉伸
    CooldownExercise(1479, "髋屈肌拉伸：跪姿弓步 1", 45, notes="髋屈肌放松"),
]

LEGS_COOLDOWN: List[CooldownExercise] = [
    # 股四头肌
    CooldownExercise(131, "大腿前侧拉伸（变体一）", 45, notes="股四头肌拉伸"),
    CooldownExercise(630, "新月式", 45, notes="髋屈肌+股四头肌"),
    # 腘绳肌
    CooldownExercise(148, "腿后侧拉伸（变体一）", 45, notes="腘绳肌拉伸"),
    CooldownExercise(648, "半猴式", 45, notes="腘绳肌深度拉伸"),
    CooldownExercise(663, "金字塔式", 45, notes="腿后侧整体拉伸"),
    # 臀部
    CooldownExercise(658, "鸽子式", 60, notes="臀部深度放松"),
    CooldownExercise(650, "快乐婴儿式", 45, notes="髋关节放松"),
    # 内收肌
    CooldownExercise(1570, "自重蝴蝶式拉伸", 45, notes="内收肌拉伸"),
    # 小腿
    CooldownExercise(636, "下犬式：脚尖到脚跟", 30, notes="小腿动态拉伸"),
    CooldownExercise(158, "小腿拉伸（变体一）", 30, notes="腓肠肌拉伸"),
]

CORE_COOLDOWN: List[CooldownExercise] = [
    CooldownExercise(162, "腹肌拉伸（变体一）", 30, notes="腹直肌拉伸"),
    CooldownExercise(861, "眼镜蛇式", 45, notes="腹部深度拉伸"),
    CooldownExercise(682, "仰卧扭转", 45, notes="腹斜肌+脊柱旋转"),
    CooldownExercise(166, "下背部拉伸（变体一）", 30, notes="下背部放松"),
    CooldownExercise(1400, "仰卧双膝抱胸", 30, notes="下背部放松"),
    CooldownExercise(617, "儿童式（双臂前伸）", 60, notes="整体放松"),
]


# =============================================================================
# 热身放松动作选择器
# =============================================================================

class WarmupCooldownSelector:
    """
    热身放松动作选择器
    
    根据训练重点自动选择合适的热身和放松动作
    """
    
    # 训练重点到热身动作的映射
    WARMUP_MAPPING: Dict[TrainingFocus, List[WarmupExercise]] = {
        TrainingFocus.UPPER_BODY: UPPER_BODY_WARMUP,
        TrainingFocus.LOWER_BODY: LOWER_BODY_WARMUP,
        TrainingFocus.PUSH: CHEST_WARMUP + SHOULDER_WARMUP[:2],
        TrainingFocus.PULL: BACK_WARMUP,
        TrainingFocus.LEGS: LEGS_WARMUP,
        TrainingFocus.FULL_BODY: UPPER_BODY_WARMUP[:4] + LOWER_BODY_WARMUP[:4],
        TrainingFocus.CORE: CORE_WARMUP,
        TrainingFocus.CHEST: CHEST_WARMUP,
        TrainingFocus.BACK: BACK_WARMUP,
        TrainingFocus.SHOULDERS: SHOULDER_WARMUP,
    }
    
    # 训练重点到放松动作的映射
    COOLDOWN_MAPPING: Dict[TrainingFocus, List[CooldownExercise]] = {
        TrainingFocus.UPPER_BODY: UPPER_BODY_COOLDOWN,
        TrainingFocus.LOWER_BODY: LOWER_BODY_COOLDOWN,
        TrainingFocus.PUSH: CHEST_COOLDOWN,
        TrainingFocus.PULL: BACK_COOLDOWN,
        TrainingFocus.LEGS: LEGS_COOLDOWN,
        TrainingFocus.FULL_BODY: UPPER_BODY_COOLDOWN[:4] + LOWER_BODY_COOLDOWN[:4],
        TrainingFocus.CORE: CORE_COOLDOWN,
        TrainingFocus.CHEST: CHEST_COOLDOWN,
        TrainingFocus.BACK: BACK_COOLDOWN,
        TrainingFocus.SHOULDERS: SHOULDER_COOLDOWN,
    }
    
    @classmethod
    def get_warmup_exercises(
        cls,
        training_focus: TrainingFocus,
        duration_minutes: int = 10,
        include_cardio: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取热身动作列表
        
        Args:
            training_focus: 训练重点
            duration_minutes: 热身时长（分钟）
            include_cardio: 是否包含有氧热身
        
        Returns:
            热身动作列表，每个动作包含完整信息
        """
        exercises = []
        total_duration = 0
        target_duration = duration_minutes * 60  # 转换为秒
        
        # 1. 添加有氧热身（如果需要）
        if include_cardio:
            cardio = GENERAL_WARMUP_CARDIO[0]  # 默认选择跑步机步行
            exercises.append(cls._format_warmup_exercise(cardio, "有氧热身"))
            total_duration += cardio.duration_seconds
        
        # 2. 添加动态拉伸
        for ex in GENERAL_WARMUP_DYNAMIC[:3]:
            if total_duration >= target_duration:
                break
            exercises.append(cls._format_warmup_exercise(ex, "动态拉伸"))
            total_duration += ex.duration_seconds
        
        # 3. 添加针对性热身
        specific_warmup = cls.WARMUP_MAPPING.get(training_focus, UPPER_BODY_WARMUP)
        for ex in specific_warmup:
            if total_duration >= target_duration:
                break
            exercises.append(cls._format_warmup_exercise(ex, "针对性激活"))
            total_duration += ex.duration_seconds
        
        return exercises
    
    @classmethod
    def get_cooldown_exercises(
        cls,
        training_focus: TrainingFocus,
        duration_minutes: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取放松动作列表
        
        Args:
            training_focus: 训练重点
            duration_minutes: 放松时长（分钟）
        
        Returns:
            放松动作列表，每个动作包含完整信息
        """
        exercises = []
        total_duration = 0
        target_duration = duration_minutes * 60  # 转换为秒
        
        # 1. 添加针对性放松
        specific_cooldown = cls.COOLDOWN_MAPPING.get(training_focus, UPPER_BODY_COOLDOWN)
        for ex in specific_cooldown:
            if total_duration >= target_duration * 0.7:  # 70%时间用于针对性拉伸
                break
            exercises.append(cls._format_cooldown_exercise(ex, "针对性拉伸"))
            total_duration += ex.duration_seconds
        
        # 2. 添加通用放松
        for ex in GENERAL_COOLDOWN:
            if total_duration >= target_duration:
                break
            exercises.append(cls._format_cooldown_exercise(ex, "全身放松"))
            total_duration += ex.duration_seconds
        
        return exercises
    
    @classmethod
    def _format_warmup_exercise(
        cls,
        exercise: WarmupExercise,
        category: str
    ) -> Dict[str, Any]:
        """格式化热身动作为字典"""
        result = {
            "exercise_id": str(exercise.exercise_id),
            "name_zh": exercise.name_zh,
            "category": category,
            "type": "warmup",
            "duration_seconds": exercise.duration_seconds,
            "sets": exercise.sets,
            "notes": exercise.notes,
        }
        if exercise.reps:
            result["reps"] = exercise.reps
        return result
    
    @classmethod
    def _format_cooldown_exercise(
        cls,
        exercise: CooldownExercise,
        category: str
    ) -> Dict[str, Any]:
        """格式化放松动作为字典"""
        return {
            "exercise_id": str(exercise.exercise_id),
            "name_zh": exercise.name_zh,
            "category": category,
            "type": "cooldown",
            "duration_seconds": exercise.duration_seconds,
            "sets": exercise.sets,
            "notes": exercise.notes,
        }
    
    @classmethod
    def determine_training_focus(
        cls,
        target_muscles: List[str],
        training_split: str
    ) -> TrainingFocus:
        """
        根据目标肌群和训练分化确定训练重点
        
        Args:
            target_muscles: 目标肌群列表
            training_split: 训练分化类型
        
        Returns:
            训练重点枚举
        """
        # 根据训练分化快速判断
        split_mapping = {
            "push_pull_legs": {
                "push": TrainingFocus.PUSH,
                "pull": TrainingFocus.PULL,
                "legs": TrainingFocus.LEGS,
            },
            "upper_lower": {
                "upper": TrainingFocus.UPPER_BODY,
                "lower": TrainingFocus.LOWER_BODY,
            },
            "full_body": TrainingFocus.FULL_BODY,
            "bro_split": TrainingFocus.FULL_BODY,
        }
        
        # 根据目标肌群判断
        upper_muscles = {"胸大肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌", "斜方肌"}
        lower_muscles = {"股四头肌", "腘绳肌", "臀大肌", "小腿肌群", "臀中肌"}
        core_muscles = {"腹直肌", "腹斜肌", "下背部", "核心"}
        
        target_set = set(target_muscles)
        
        # 检查是否主要是上肢
        if target_set & upper_muscles and not (target_set & lower_muscles):
            if "胸大肌" in target_set:
                return TrainingFocus.CHEST
            elif "背阔肌" in target_set:
                return TrainingFocus.BACK
            elif "三角肌" in target_set:
                return TrainingFocus.SHOULDERS
            return TrainingFocus.UPPER_BODY
        
        # 检查是否主要是下肢
        if target_set & lower_muscles and not (target_set & upper_muscles):
            return TrainingFocus.LOWER_BODY
        
        # 检查是否主要是核心
        if target_set & core_muscles and len(target_set & core_muscles) >= len(target_set) / 2:
            return TrainingFocus.CORE
        
        # 默认全身
        return TrainingFocus.FULL_BODY
