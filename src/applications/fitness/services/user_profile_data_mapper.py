# -*- coding: utf-8 -*-
"""
用户档案数据映射服务

将用户档案中的选项映射到Neo4j节点名称（中英文转换）

版本: v2.0.0
日期: 2026-01-05
更新: 统一化后简化映射，前端选项与Neo4j节点完全一致

变更说明:
- v2.0.0: 统一化后简化映射
  - 删除复杂的多对多映射字典
  - 改为简单的中英文名称对照
  - 前端选项与Neo4j节点name_zh完全一致
  - 保留验证功能和关节-伤病关联
"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass


@dataclass
class MappingResult:
    """映射结果"""
    user_value: str
    neo4j_values: List[str]
    confidence: float  # 0.0 - 1.0


class UserProfileDataMapper:
    """用户档案数据映射器"""
    
    # ==================== 伤病映射 ====================
    # 统一后的伤病选项（前端选项与Neo4j节点name_zh完全一致，不再需要复杂映射）
    # 更新日期: 2026-01-05 (统一化后简化映射)
    #
    # 前端选项 (ALL_INJURY_OPTIONS) -> Neo4j InjuryType.name_zh (直接对应)
    # 用户直接选择具体伤病（如"下背部疼痛"而非"腰部损伤"）
    
    # 伤病中英文对照（用于查询）
    INJURY_NAME_MAPPING: Dict[str, str] = {
        "下背部疼痛": "lower_back_pain",
        "腰椎间盘突出": "herniated_disc",
        "前交叉韧带损伤": "acl_injury",
        "膝盖受伤": "knee_injury",
        "髌骨软化症": "chondromalacia_patellae",
        "髂胫束综合征": "itbs",
        "肩峰撞击": "shoulder_impingement",
        "肩袖损伤": "rotator_cuff_injury",
        "肩部受伤": "shoulder_injury",
        "腕管综合征": "carpal_tunnel",
        "腕部受伤": "wrist_injury",
        "跟腱炎": "achilles_tendinitis",
        "足底筋膜炎": "plantar_fasciitis",
        "踝关节扭伤": "ankle_sprain",
        "颈椎病": "cervical_spondylosis",
        "颈部受伤": "neck_injury",
        "网球肘": "tennis_elbow",
        "高尔夫球肘": "golfers_elbow",
        "髋关节撞击": "hip_impingement",
        "髋滑囊炎": "hip_bursitis",
        "髋部受伤": "hip_injury",
    }
    
    # 反向映射: Neo4j InjuryType.name -> 中文名称
    INJURY_NAME_REVERSE_MAPPING: Dict[str, str] = {
        "lower_back_pain": "下背部疼痛",
        "herniated_disc": "腰椎间盘突出",
        "acl_injury": "前交叉韧带损伤",
        "knee_injury": "膝盖受伤",
        "chondromalacia_patellae": "髌骨软化症",
        "itbs": "髂胫束综合征",
        "shoulder_impingement": "肩峰撞击",
        "rotator_cuff_injury": "肩袖损伤",
        "shoulder_injury": "肩部受伤",
        "carpal_tunnel": "腕管综合征",
        "wrist_injury": "腕部受伤",
        "achilles_tendinitis": "跟腱炎",
        "plantar_fasciitis": "足底筋膜炎",
        "ankle_sprain": "踝关节扭伤",
        "cervical_spondylosis": "颈椎病",
        "neck_injury": "颈部受伤",
        "tennis_elbow": "网球肘",
        "golfers_elbow": "高尔夫球肘",
        "hip_impingement": "髋关节撞击",
        "hip_bursitis": "髋滑囊炎",
        "hip_injury": "髋部受伤",
    }
    
    # 伤病分类映射（用于前端分组显示）
    INJURY_CATEGORY_MAPPING: Dict[str, List[str]] = {
        "腰部损伤": ["下背部疼痛", "腰椎间盘突出"],
        "膝盖损伤": ["前交叉韧带损伤", "膝盖受伤", "髌骨软化症", "髂胫束综合征"],
        "肩部损伤": ["肩峰撞击", "肩袖损伤", "肩部受伤"],
        "手腕损伤": ["腕管综合征", "腕部受伤"],
        "脚踝损伤": ["跟腱炎", "足底筋膜炎", "踝关节扭伤"],
        "颈部损伤": ["颈椎病", "颈部受伤"],
        "肘部损伤": ["网球肘", "高尔夫球肘"],
        "髋部损伤": ["髋关节撞击", "髋滑囊炎", "髋部受伤"],
    }
    
    # ==================== 关节-伤病映射 ====================
    # Neo4j Joint.name_zh -> 伤病分类
    # 用于禁忌症检查：如果用户有某关节的伤病，应该避免涉及该关节的动作
    JOINT_TO_INJURY_CATEGORY_MAPPING: Dict[str, str] = {
        "肩关节": "肩部损伤",
        "肘关节": "肘部损伤",
        "腕关节": "手腕损伤",
        "髋关节": "髋部损伤",
        "膝关节": "膝盖损伤",
        "踝关节": "脚踝损伤",
        "脊柱": "腰部损伤",
        "颈椎": "颈部损伤",
        "核心": "腰部损伤",  # 核心问题通常与腰部相关
    }
    
    # ==================== 器械映射 ====================
    # 统一后的器械选项（前端选项与Neo4j节点完全一致，不再需要复杂映射）
    # 更新日期: 2026-01-05 (统一化后简化映射)
    #
    # 前端选项 (EQUIPMENT_OPTIONS) -> Neo4j Equipment.name_zh (直接对应)
    # 16个器械 + 5个训练类型分类 = 21个节点
    
    # 器械中英文对照（用于查询）
    EQUIPMENT_NAME_MAPPING: Dict[str, str] = {
        "杠铃": "barbell",
        "杠铃片": "weight_plate",
        "哑铃": "dumbbell",
        "固定器械": "machine",
        "自由重量架": "free_weight_rack",
        "史密斯架": "smith_machine",
        "龙门架": "cable_machine",
        "弹力带": "resistance_band",
        "壶铃": "kettlebell",
        "TRX": "trx",
        "药球": "medicine_ball",
        "波速球": "bosu_ball",
        "健身球": "stability_ball",
        "跳箱": "plyo_box",
        "战绳": "battle_rope",
        "徒手": "bodyweight",
        # 训练类型分类
        "恢复": "recovery",
        "拉伸": "stretching",
        "有氧训练": "cardio",
        "瑜伽": "yoga",
        "Vitruvian": "vitruvian",
    }
    
    # 反向映射: Neo4j Equipment.name -> 中文名称
    EQUIPMENT_NAME_REVERSE_MAPPING: Dict[str, str] = {
        "barbell": "杠铃",
        "weight_plate": "杠铃片",
        "dumbbell": "哑铃",
        "machine": "固定器械",
        "free_weight_rack": "自由重量架",
        "smith_machine": "史密斯架",
        "cable_machine": "龙门架",
        "resistance_band": "弹力带",
        "kettlebell": "壶铃",
        "trx": "TRX",
        "medicine_ball": "药球",
        "bosu_ball": "波速球",
        "stability_ball": "健身球",
        "plyo_box": "跳箱",
        "battle_rope": "战绳",
        "bodyweight": "徒手",
        # 训练类型分类
        "recovery": "恢复",
        "stretching": "拉伸",
        "cardio": "有氧训练",
        "yoga": "瑜伽",
        "vitruvian": "Vitruvian",
    }
    
    # 训练类型分类（非器械，用于动作分类）
    TRAINING_TYPE_CATEGORIES: Set[str] = {"恢复", "拉伸", "有氧训练", "瑜伽"}
    
    # ==================== 训练目标映射 ====================
    # 统一后的训练目标（前端选项与Neo4j节点完全一致，不再需要映射）
    # Neo4j TrainingGoal节点现在使用统一的name和name_zh
    # 
    # 前端选项 (FITNESS_GOALS_OPTIONS) -> Neo4j TrainingGoal.name_zh (直接对应)
    # - 增肌 -> hypertrophy (增肌)
    # - 减脂 -> fat_loss (减脂)
    # - 增强力量 -> strength (增强力量)
    # - 提高耐力 -> endurance (提高耐力)
    # - 塑形 -> body_shaping (塑形)
    # - 功能性训练 -> functional (功能性训练)
    # - 运动表现 -> athletic_performance (运动表现)
    # - 康复训练 -> rehabilitation (康复训练)
    #
    # 更新日期: 2026-01-05 (统一化后不再需要映射字典)
    
    # 训练目标中英文对照（用于查询）
    GOAL_NAME_MAPPING: Dict[str, str] = {
        "增肌": "hypertrophy",
        "减脂": "fat_loss",
        "增强力量": "strength",
        "提高耐力": "endurance",
        "塑形": "body_shaping",
        "功能性训练": "functional",
        "运动表现": "athletic_performance",
        "康复训练": "rehabilitation",
    }
    
    # ==================== 体态问题映射 ====================
    # 统一后的体态问题选项（前端选项与Neo4j节点完全一致）
    # 更新日期: 2026-01-05 (新增体态矫正功能)
    #
    # 前端选项 (POSTURAL_ISSUES_OPTIONS) -> Neo4j PosturalIssue.name_zh (直接对应)
    # 12种常见体态问题
    
    # 体态问题中英文对照（用于查询）
    POSTURAL_ISSUE_NAME_MAPPING: Dict[str, str] = {
        "圆肩": "rounded_shoulders",
        "头前伸": "forward_head",
        "胸椎后凸过度(驼背)": "excessive_thoracic_kyphosis",
        "胸椎后凸不足(平背)": "flat_back",
        "骨盆前倾": "anterior_pelvic_tilt",
        "骨盆后倾": "posterior_pelvic_tilt",
        "腰椎前凸过度": "excessive_lumbar_lordosis",
        "脊柱侧弯": "scoliosis",
        "膝内翻(O型腿)": "genu_varum",
        "膝外翻(X型腿)": "genu_valgum",
        "扁平足": "flat_feet",
        "高弓足": "high_arches",
    }
    
    # 反向映射: Neo4j PosturalIssue.name -> 中文名称
    POSTURAL_ISSUE_NAME_REVERSE_MAPPING: Dict[str, str] = {
        "rounded_shoulders": "圆肩",
        "forward_head": "头前伸",
        "excessive_thoracic_kyphosis": "胸椎后凸过度(驼背)",
        "flat_back": "胸椎后凸不足(平背)",
        "anterior_pelvic_tilt": "骨盆前倾",
        "posterior_pelvic_tilt": "骨盆后倾",
        "excessive_lumbar_lordosis": "腰椎前凸过度",
        "scoliosis": "脊柱侧弯",
        "genu_varum": "膝内翻(O型腿)",
        "genu_valgum": "膝外翻(X型腿)",
        "flat_feet": "扁平足",
        "high_arches": "高弓足",
    }
    
    # 体态问题分类（用于前端分组显示）
    POSTURAL_ISSUE_CATEGORY_MAPPING: Dict[str, List[str]] = {
        "上半身": ["圆肩", "头前伸", "胸椎后凸过度(驼背)", "胸椎后凸不足(平背)"],
        "骨盆和腰椎": ["骨盆前倾", "骨盆后倾", "腰椎前凸过度", "脊柱侧弯"],
        "下肢": ["膝内翻(O型腿)", "膝外翻(X型腿)"],
        "足部": ["扁平足", "高弓足"],
    }
    
    # 反向映射: Neo4j TrainingGoal.name -> 中文名称
    GOAL_NAME_REVERSE_MAPPING: Dict[str, str] = {
        "hypertrophy": "增肌",
        "fat_loss": "减脂",
        "strength": "增强力量",
        "endurance": "提高耐力",
        "body_shaping": "塑形",
        "functional": "功能性训练",
        "athletic_performance": "运动表现",
        "rehabilitation": "康复训练",
    }
    
    # ==================== 训练水平映射 ====================
    # 用户档案 fitness_level -> Neo4j TrainingLevel.name
    LEVEL_MAPPING: Dict[str, str] = {
        "novice": "novice",
        "beginner": "beginner",
        "intermediate": "intermediate",
        "advanced": "advanced",
    }
    
    # ==================== 映射方法 ====================
    
    @classmethod
    def map_injuries_to_neo4j(cls, user_injuries: List[str]) -> List[str]:
        """
        将用户档案中的伤病选项映射到Neo4j InjuryType节点名称
        
        统一化后，前端选项与Neo4j节点name_zh完全一致，
        此方法返回对应的英文name用于查询
        
        Args:
            user_injuries: 用户档案中的伤病列表（中文，具体伤病名称）
            
        Returns:
            Neo4j InjuryType节点的name列表（英文）
        """
        if not user_injuries or user_injuries == ["无"]:
            return []
        
        neo4j_injuries = []
        for injury in user_injuries:
            if injury in cls.INJURY_NAME_MAPPING:
                neo4j_injuries.append(cls.INJURY_NAME_MAPPING[injury])
        
        return neo4j_injuries
    
    @classmethod
    def map_injury_from_neo4j(cls, neo4j_injury: str) -> Optional[str]:
        """
        将Neo4j InjuryType节点名称映射回用户档案选项（中文）
        
        Args:
            neo4j_injury: Neo4j InjuryType节点的name（英文）
            
        Returns:
            用户档案中的伤病选项（中文）
        """
        return cls.INJURY_NAME_REVERSE_MAPPING.get(neo4j_injury)
    
    @classmethod
    def get_injury_category(cls, injury_name_zh: str) -> Optional[str]:
        """
        获取伤病所属的分类
        
        Args:
            injury_name_zh: 伤病中文名称
            
        Returns:
            伤病分类（如"腰部损伤"）
        """
        for category, injuries in cls.INJURY_CATEGORY_MAPPING.items():
            if injury_name_zh in injuries:
                return category
        return None
    
    @classmethod
    def get_injuries_by_category(cls, category: str) -> List[str]:
        """
        获取某分类下的所有伤病
        
        Args:
            category: 伤病分类（如"腰部损伤"）
            
        Returns:
            该分类下的所有伤病中文名称列表
        """
        return cls.INJURY_CATEGORY_MAPPING.get(category, [])
    
    @classmethod
    def map_joint_to_injury_category(cls, joint_name: str) -> Optional[str]:
        """
        将关节名称映射到伤病分类
        
        Args:
            joint_name: Neo4j Joint节点的name_zh
            
        Returns:
            伤病分类（如"腰部损伤"）
        """
        return cls.JOINT_TO_INJURY_CATEGORY_MAPPING.get(joint_name)
    
    @classmethod
    def get_injuries_for_joint(cls, joint_name: str) -> List[str]:
        """
        获取与特定关节相关的所有具体伤病
        
        用于禁忌症检查：如果用户有某关节的伤病，应该避免涉及该关节的动作
        
        Args:
            joint_name: 关节名称
            
        Returns:
            相关的具体伤病中文名称列表
        """
        category = cls.JOINT_TO_INJURY_CATEGORY_MAPPING.get(joint_name)
        if not category:
            return []
        
        return cls.INJURY_CATEGORY_MAPPING.get(category, [])
    
    @classmethod
    def map_equipment_to_neo4j(cls, user_equipment: List[str]) -> List[str]:
        """
        将用户档案中的器械选项映射到Neo4j Equipment节点名称
        
        统一化后，前端选项与Neo4j节点name_zh完全一致，
        此方法返回对应的英文name用于查询
        
        Args:
            user_equipment: 用户档案中的器械列表（中文）
            
        Returns:
            Neo4j Equipment节点的name列表（英文）
        """
        if not user_equipment:
            return []
        
        neo4j_equipment = []
        for equip in user_equipment:
            if equip in cls.EQUIPMENT_NAME_MAPPING:
                neo4j_equipment.append(cls.EQUIPMENT_NAME_MAPPING[equip])
        
        return neo4j_equipment
    
    @classmethod
    def map_equipment_from_neo4j(cls, neo4j_equipment: str) -> Optional[str]:
        """
        将Neo4j Equipment节点名称映射回用户档案选项（中文）
        
        Args:
            neo4j_equipment: Neo4j Equipment节点的name（英文）
            
        Returns:
            用户档案中的器械选项（中文）
        """
        return cls.EQUIPMENT_NAME_REVERSE_MAPPING.get(neo4j_equipment)
    
    @classmethod
    def is_training_type_category(cls, equipment_name: str) -> bool:
        """
        检查是否为训练类型分类（非器械）
        
        Args:
            equipment_name: Equipment节点名称
            
        Returns:
            是否为训练类型分类
        """
        return equipment_name in cls.TRAINING_TYPE_CATEGORIES
    
    @classmethod
    def map_goals_to_neo4j(cls, user_goals: List[str]) -> List[str]:
        """
        将用户档案中的训练目标映射到Neo4j TrainingGoal节点名称
        
        统一化后，前端选项与Neo4j节点name_zh完全一致，
        此方法返回对应的英文name用于查询
        
        Args:
            user_goals: 用户档案中的目标列表（中文）
            
        Returns:
            Neo4j TrainingGoal节点的name列表（英文）
        """
        if not user_goals:
            return []
        
        neo4j_goals = []
        for goal in user_goals:
            if goal in cls.GOAL_NAME_MAPPING:
                neo4j_goals.append(cls.GOAL_NAME_MAPPING[goal])
        
        return neo4j_goals
    
    @classmethod
    def map_goal_from_neo4j(cls, neo4j_goal: str) -> Optional[str]:
        """
        将Neo4j TrainingGoal节点名称映射回用户档案选项（中文）
        
        Args:
            neo4j_goal: Neo4j TrainingGoal节点的name（英文）
            
        Returns:
            用户档案中的目标选项（中文）
        """
        return cls.GOAL_NAME_REVERSE_MAPPING.get(neo4j_goal)
    
    @classmethod
    def map_level_to_neo4j(cls, user_level: str) -> str:
        """
        将用户档案中的训练水平映射到Neo4j TrainingLevel节点
        
        Args:
            user_level: 用户档案中的训练水平
            
        Returns:
            Neo4j TrainingLevel节点的name
        """
        return cls.LEVEL_MAPPING.get(user_level, user_level)
    
    @classmethod
    def get_contraindicated_injuries_for_joint(cls, joint_name: str) -> List[str]:
        """
        获取与特定关节相关的所有伤病类型（英文name）
        
        用于禁忌症检查：如果用户有某关节的伤病，应该避免涉及该关节的动作
        
        Args:
            joint_name: 关节名称
            
        Returns:
            相关的InjuryType英文name列表
        """
        injuries_zh = cls.get_injuries_for_joint(joint_name)
        return [cls.INJURY_NAME_MAPPING[i] for i in injuries_zh if i in cls.INJURY_NAME_MAPPING]
    
    @classmethod
    def validate_user_profile_data(cls, user_profile: dict) -> Dict[str, List[str]]:
        """
        验证用户档案数据，返回无法映射的选项
        
        Args:
            user_profile: 用户档案字典
            
        Returns:
            无法映射的选项，按字段分组
        """
        unmapped = {}
        
        # 检查伤病
        injuries = user_profile.get("health_status", {}).get("injury_history", [])
        unmapped_injuries = [i for i in injuries if i not in cls.INJURY_NAME_MAPPING and i not in ["无", "其他"]]
        if unmapped_injuries:
            unmapped["injury_history"] = unmapped_injuries
        
        # 检查器械
        equipment = user_profile.get("training_preferences", {}).get("available_equipment", [])
        unmapped_equipment = [e for e in equipment if e not in cls.EQUIPMENT_NAME_MAPPING]
        if unmapped_equipment:
            unmapped["available_equipment"] = unmapped_equipment
        
        # 检查目标
        goals = user_profile.get("fitness_goals", {}).get("primary_goals", [])
        unmapped_goals = [g for g in goals if g not in cls.GOAL_NAME_MAPPING]
        if unmapped_goals:
            unmapped["primary_goals"] = unmapped_goals
        
        # 检查体态问题
        postural_issues = user_profile.get("health_status", {}).get("postural_issues", [])
        unmapped_postural = [p for p in postural_issues if p not in cls.POSTURAL_ISSUE_NAME_MAPPING and p not in ["无"]]
        if unmapped_postural:
            unmapped["postural_issues"] = unmapped_postural
        
        return unmapped
    
    @classmethod
    def map_postural_issues_to_neo4j(cls, user_postural_issues: List[str]) -> List[str]:
        """
        将用户档案中的体态问题选项映射到Neo4j PosturalIssue节点名称
        
        统一化后，前端选项与Neo4j节点name_zh完全一致，
        此方法返回对应的英文name用于查询
        
        Args:
            user_postural_issues: 用户档案中的体态问题列表（中文）
            
        Returns:
            Neo4j PosturalIssue节点的name列表（英文）
        """
        if not user_postural_issues or user_postural_issues == ["无"]:
            return []
        
        neo4j_postural_issues = []
        for issue in user_postural_issues:
            if issue in cls.POSTURAL_ISSUE_NAME_MAPPING:
                neo4j_postural_issues.append(cls.POSTURAL_ISSUE_NAME_MAPPING[issue])
        
        return neo4j_postural_issues
    
    @classmethod
    def map_postural_issue_from_neo4j(cls, neo4j_postural_issue: str) -> Optional[str]:
        """
        将Neo4j PosturalIssue节点名称映射回用户档案选项（中文）
        
        Args:
            neo4j_postural_issue: Neo4j PosturalIssue节点的name（英文）
            
        Returns:
            用户档案中的体态问题选项（中文）
        """
        return cls.POSTURAL_ISSUE_NAME_REVERSE_MAPPING.get(neo4j_postural_issue)


# 便捷函数
def map_user_injuries(injuries: List[str]) -> List[str]:
    """便捷函数：映射用户伤病到Neo4j（返回英文name）"""
    return UserProfileDataMapper.map_injuries_to_neo4j(injuries)


def map_user_equipment(equipment: List[str]) -> List[str]:
    """便捷函数：映射用户器械到Neo4j（返回英文name）"""
    return UserProfileDataMapper.map_equipment_to_neo4j(equipment)


def map_user_goals(goals: List[str]) -> List[str]:
    """便捷函数：映射用户目标到Neo4j（返回英文name）"""
    return UserProfileDataMapper.map_goals_to_neo4j(goals)


def map_user_postural_issues(postural_issues: List[str]) -> List[str]:
    """便捷函数：映射用户体态问题到Neo4j（返回英文name）"""
    return UserProfileDataMapper.map_postural_issues_to_neo4j(postural_issues)
