"""
训练目标推荐服务

基于用户类型和训练目标提供个性化推荐
支持中国本地化扩展目标 - Requirements 3.1, 3.2, 3.3, 3.4

功能特性：
- 体态矫正推荐久坐人群动作 - Requirements 3.2, 3.4
- 大学生增肌推荐经济饮食方案 - Requirements 3.4
- 减脂塑形推荐高次数、短休息训练方案 - Requirements 3.1
- 功能性训练推荐运动表现提升动作 - Requirements 3.3

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-26
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class UserType(str, Enum):
    """用户类型枚举"""
    STUDENT = "student"          # 大学生
    WORKER = "worker"            # 上班族
    ATHLETE = "athlete"          # 运动员
    SENIOR = "senior"            # 中老年
    OTHER = "other"              # 其他


class TrainingGoalRecommender:
    """
    训练目标推荐服务
    
    根据用户类型和训练目标提供个性化推荐
    Requirements: 3.1, 3.2, 3.3, 3.4
    """
    
    # 体态矫正推荐动作（久坐人群） - Requirements 3.2, 3.4
    POSTURE_CORRECTION_EXERCISES = {
        "sedentary": {
            "description": "久坐人群体态矫正动作",
            "exercises": [
                {
                    "name_zh": "面拉",
                    "name_en": "Face Pull",
                    "target": "改善圆肩",
                    "sets": 3,
                    "reps": "15-20",
                    "notes": "注重肩胛骨后缩"
                },
                {
                    "name_zh": "猫牛式",
                    "name_en": "Cat-Cow Stretch",
                    "target": "改善脊柱灵活性",
                    "sets": 3,
                    "reps": "10-15",
                    "notes": "缓慢控制，配合呼吸"
                },
                {
                    "name_zh": "髋屈肌拉伸",
                    "name_en": "Hip Flexor Stretch",
                    "target": "改善骨盆前倾",
                    "sets": 2,
                    "reps": "30秒/侧",
                    "notes": "保持核心收紧"
                },
                {
                    "name_zh": "死虫式",
                    "name_en": "Dead Bug",
                    "target": "核心稳定性",
                    "sets": 3,
                    "reps": "10-12/侧",
                    "notes": "保持腰部贴地"
                },
                {
                    "name_zh": "Y-T-W-L举",
                    "name_en": "Y-T-W-L Raises",
                    "target": "肩胛稳定性",
                    "sets": 2,
                    "reps": "8-10/动作",
                    "notes": "轻重量，注重控制"
                },
                {
                    "name_zh": "臀桥",
                    "name_en": "Glute Bridge",
                    "target": "激活臀肌，改善骨盆前倾",
                    "sets": 3,
                    "reps": "12-15",
                    "notes": "顶峰收缩2秒"
                }
            ],
            "common_issues": [
                "圆肩驼背",
                "骨盆前倾",
                "颈前伸",
                "腰椎过度前凸"
            ],
            "training_tips": [
                "每天进行2-3次短时间拉伸",
                "工作时每小时起身活动5分钟",
                "加强背部和臀部肌群训练",
                "减少胸部和髋屈肌的过度训练"
            ]
        }
    }
    
    # 大学生经济饮食方案 - Requirements 3.4
    STUDENT_NUTRITION_PLANS = {
        "hypertrophy": {
            "description": "大学生增肌经济饮食方案",
            "daily_protein_target": "1.6-2.0g/kg体重",
            "budget_friendly_foods": [
                {
                    "name": "鸡蛋",
                    "protein_per_100g": "13g",
                    "cost_rating": "低",
                    "tips": "食堂鸡蛋性价比最高"
                },
                {
                    "name": "鸡胸肉",
                    "protein_per_100g": "31g",
                    "cost_rating": "中",
                    "tips": "批量购买冷冻鸡胸更划算"
                },
                {
                    "name": "豆腐/豆制品",
                    "protein_per_100g": "8-15g",
                    "cost_rating": "低",
                    "tips": "食堂豆腐菜品是优质蛋白来源"
                },
                {
                    "name": "牛奶/酸奶",
                    "protein_per_100g": "3-4g",
                    "cost_rating": "中",
                    "tips": "选择纯牛奶或无糖酸奶"
                },
                {
                    "name": "花生酱",
                    "protein_per_100g": "25g",
                    "cost_rating": "中",
                    "tips": "搭配全麦面包作为加餐"
                },
                {
                    "name": "燕麦",
                    "protein_per_100g": "13g",
                    "cost_rating": "低",
                    "tips": "早餐首选，提供优质碳水"
                }
            ],
            "meal_timing": {
                "breakfast": "燕麦+鸡蛋+牛奶",
                "lunch": "米饭+鸡胸肉/豆腐+蔬菜",
                "dinner": "米饭+瘦肉+蔬菜",
                "pre_workout": "香蕉+花生酱面包",
                "post_workout": "牛奶+鸡蛋"
            },
            "budget_tips": [
                "优先选择食堂，性价比最高",
                "批量购买蛋白质来源（鸡蛋、鸡胸肉）",
                "自制蛋白奶昔比购买蛋白粉更经济",
                "利用学校健身房免费资源"
            ]
        },
        "fat_loss": {
            "description": "大学生减脂经济饮食方案",
            "daily_calorie_deficit": "300-500kcal",
            "budget_friendly_foods": [
                {
                    "name": "鸡蛋",
                    "calories_per_100g": "155kcal",
                    "cost_rating": "低",
                    "tips": "高蛋白低碳水，饱腹感强"
                },
                {
                    "name": "鸡胸肉",
                    "calories_per_100g": "165kcal",
                    "cost_rating": "中",
                    "tips": "去皮，减少脂肪摄入"
                },
                {
                    "name": "蔬菜",
                    "calories_per_100g": "20-50kcal",
                    "cost_rating": "低",
                    "tips": "食堂蔬菜无限量，增加饱腹感"
                },
                {
                    "name": "黄瓜/西红柿",
                    "calories_per_100g": "15-20kcal",
                    "cost_rating": "低",
                    "tips": "作为零食替代品"
                }
            ],
            "meal_timing": {
                "breakfast": "鸡蛋+全麦面包+蔬菜",
                "lunch": "少量米饭+大量蔬菜+瘦肉",
                "dinner": "蔬菜沙拉+鸡胸肉",
                "snacks": "黄瓜/西红柿/无糖酸奶"
            },
            "budget_tips": [
                "减少外卖和零食支出",
                "多吃食堂蔬菜，控制主食量",
                "自带水杯，减少饮料消费",
                "利用学校操场进行有氧运动"
            ]
        }
    }
    
    # 减脂塑形训练方案 - Requirements 3.1
    FAT_LOSS_TRAINING_PARAMS = {
        "description": "减脂塑形训练参数",
        "rep_range": "12-20",
        "rest_period": "30-45秒",
        "training_density": "高",
        "recommended_methods": [
            {
                "name": "超级组",
                "description": "两个动作连续进行，无休息",
                "benefit": "提高训练密度，增加热量消耗"
            },
            {
                "name": "循环训练",
                "description": "多个动作循环进行",
                "benefit": "保持心率，提高代谢"
            },
            {
                "name": "HIIT",
                "description": "高强度间歇训练",
                "benefit": "短时间高效燃脂"
            }
        ],
        "cardio_recommendations": [
            "力量训练后进行20-30分钟低强度有氧",
            "每周2-3次HIIT训练",
            "日常增加步行量（目标10000步/天）"
        ]
    }
    
    # 功能性训练方案 - Requirements 3.3
    FUNCTIONAL_TRAINING_PARAMS = {
        "description": "功能性训练参数",
        "rep_range": "8-15",
        "rest_period": "60-90秒",
        "focus_areas": [
            "多关节复合动作",
            "核心稳定性",
            "平衡与协调",
            "爆发力"
        ],
        "recommended_exercises": [
            {
                "name_zh": "壶铃摆荡",
                "name_en": "Kettlebell Swing",
                "benefit": "髋关节爆发力，核心稳定"
            },
            {
                "name_zh": "土耳其起立",
                "name_en": "Turkish Get-Up",
                "benefit": "全身协调，肩部稳定"
            },
            {
                "name_zh": "农夫行走",
                "name_en": "Farmer's Walk",
                "benefit": "核心稳定，握力，整体力量"
            },
            {
                "name_zh": "药球抛掷",
                "name_en": "Medicine Ball Throw",
                "benefit": "上肢爆发力，核心传导"
            },
            {
                "name_zh": "单腿硬拉",
                "name_en": "Single-Leg Deadlift",
                "benefit": "平衡，髋关节稳定"
            }
        ],
        "sport_specific_tips": [
            "根据运动项目选择针对性动作",
            "注重动作质量而非重量",
            "包含多平面运动模式",
            "定期进行运动能力测试"
        ]
    }
    
    def get_posture_correction_recommendations(
        self,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取体态矫正推荐
        
        针对久坐人群提供体态矫正动作和建议
        Requirements: 3.2, 3.4
        
        Args:
            user_profile: 用户档案
            
        Returns:
            体态矫正推荐
        """
        user_type = user_profile.get("user_type", "other")
        occupation = user_profile.get("occupation", "")
        
        # 判断是否为久坐人群
        is_sedentary = (
            user_type in ["student", "worker"] or
            "办公" in occupation or
            "程序" in occupation or
            "设计" in occupation or
            "文员" in occupation
        )
        
        recommendations = self.POSTURE_CORRECTION_EXERCISES["sedentary"].copy()
        
        if is_sedentary:
            recommendations["priority"] = "high"
            recommendations["message"] = (
                "检测到您可能是久坐人群，体态矫正对您尤为重要。"
                "建议每天进行以下动作，改善圆肩驼背和骨盆前倾问题。"
            )
        else:
            recommendations["priority"] = "medium"
            recommendations["message"] = (
                "体态矫正有助于提高训练效果和预防损伤。"
                "建议将以下动作纳入热身或放松环节。"
            )
        
        logger.info(
            f"📊 体态矫正推荐: user_type={user_type}, "
            f"is_sedentary={is_sedentary}, "
            f"exercises_count={len(recommendations['exercises'])}"
        )
        
        return recommendations
    
    def get_student_nutrition_plan(
        self,
        training_goal: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取大学生营养方案
        
        针对大学生提供经济实惠的饮食建议
        Requirements: 3.4
        
        Args:
            training_goal: 训练目标
            user_profile: 用户档案
            
        Returns:
            营养方案
        """
        user_type = user_profile.get("user_type", "other")
        campus_name = user_profile.get("campus_name", "")
        
        # 确定营养方案类型
        if training_goal in ["hypertrophy", "strength"]:
            plan_type = "hypertrophy"
        elif training_goal in ["fat_loss", "weight_loss"]:
            plan_type = "fat_loss"
        else:
            plan_type = "hypertrophy"  # 默认增肌方案
        
        plan = self.STUDENT_NUTRITION_PLANS.get(plan_type, {}).copy()
        
        if user_type == "student":
            plan["is_student_optimized"] = True
            plan["message"] = (
                f"为您定制的大学生{plan.get('description', '饮食方案')}。"
                "充分利用食堂资源，在有限预算内实现营养目标。"
            )
            if campus_name:
                plan["message"] += f"\n学校：{campus_name}"
        else:
            plan["is_student_optimized"] = False
            plan["message"] = (
                "以下是经济实惠的饮食建议，"
                "适合预算有限但追求健康的用户。"
            )
        
        logger.info(
            f"📊 营养方案推荐: user_type={user_type}, "
            f"training_goal={training_goal}, "
            f"plan_type={plan_type}"
        )
        
        return plan
    
    def get_fat_loss_training_params(self) -> Dict[str, Any]:
        """
        获取减脂塑形训练参数
        
        Requirements: 3.1
        
        Returns:
            减脂训练参数
        """
        return self.FAT_LOSS_TRAINING_PARAMS.copy()
    
    def get_functional_training_params(self) -> Dict[str, Any]:
        """
        获取功能性训练参数
        
        Requirements: 3.3
        
        Returns:
            功能性训练参数
        """
        return self.FUNCTIONAL_TRAINING_PARAMS.copy()
    
    def get_goal_specific_recommendations(
        self,
        training_goal: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取目标相关推荐
        
        根据训练目标和用户类型提供综合推荐
        Requirements: 3.1, 3.2, 3.3, 3.4
        
        Args:
            training_goal: 训练目标
            user_profile: 用户档案
            
        Returns:
            综合推荐
        """
        recommendations = {
            "training_goal": training_goal,
            "user_type": user_profile.get("user_type", "other"),
            "training_params": {},
            "nutrition_plan": None,
            "additional_recommendations": []
        }
        
        # 根据训练目标提供推荐
        if training_goal == "fat_loss":
            recommendations["training_params"] = self.get_fat_loss_training_params()
            recommendations["additional_recommendations"].extend([
                "保持高训练密度，控制休息时间在45秒内",
                "配合有氧训练和饮食控制，创造热量缺口",
                "优先选择复合动作，提高热量消耗"
            ])
            
        elif training_goal == "posture_correction":
            recommendations["posture_exercises"] = self.get_posture_correction_recommendations(
                user_profile
            )
            recommendations["additional_recommendations"].extend([
                "注重动作控制和肌肉激活，避免代偿",
                "加强核心稳定性训练和拉伸放松",
                "每天进行2-3次短时间拉伸"
            ])
            
        elif training_goal == "functional":
            recommendations["training_params"] = self.get_functional_training_params()
            recommendations["additional_recommendations"].extend([
                "注重多关节复合动作和动态稳定性",
                "包含平衡、协调和爆发力训练元素",
                "根据运动项目选择针对性动作"
            ])
        
        # 大学生用户提供营养方案
        if user_profile.get("user_type") == "student":
            recommendations["nutrition_plan"] = self.get_student_nutrition_plan(
                training_goal, user_profile
            )
        
        logger.info(
            f"📊 目标推荐生成: training_goal={training_goal}, "
            f"user_type={recommendations['user_type']}, "
            f"has_nutrition_plan={recommendations['nutrition_plan'] is not None}"
        )
        
        return recommendations


# 单例模式
_training_goal_recommender: Optional[TrainingGoalRecommender] = None


def get_training_goal_recommender() -> TrainingGoalRecommender:
    """获取训练目标推荐服务单例"""
    global _training_goal_recommender
    if _training_goal_recommender is None:
        _training_goal_recommender = TrainingGoalRecommender()
    return _training_goal_recommender
