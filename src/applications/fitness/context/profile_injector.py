# -*- coding: utf-8 -*-
"""
用户档案注入模块

自动将用户档案信息注入到对话上下文中。

Requirements: 8.5

版本: v1.0.0
日期: 2025-12-31
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProfileInjectionConfig:
    """档案注入配置"""
    # 注入的字段
    include_basic_info: bool = True      # 基础信息（年龄、性别、身高、体重）
    include_fitness_level: bool = True   # 健身水平
    include_goals: bool = True           # 健身目标
    include_injuries: bool = True        # 伤病信息
    include_preferences: bool = True     # 偏好设置
    include_training_history: bool = False  # 训练历史（较长，默认不包含）
    include_nutrition: bool = True       # 营养档案（TDEE/BMR/宏量）
    include_strength: bool = True        # 力量数据（1RM等）
    include_ffmi: bool = True            # FFMI评估
    include_training_prefs: bool = True  # 训练偏好（器械/分化/位置）
    include_body_composition: bool = True  # 体成分（体脂率/BMI）

    # 格式配置
    max_profile_tokens: int = 500        # 档案最大Token数
    format_style: str = "concise"        # 格式风格：concise/detailed


class ProfileInjector:
    """
    用户档案注入器
    
    职责：
    1. 从用户档案中提取关键信息
    2. 格式化为适合LLM理解的文本
    3. 自动注入到对话上下文
    
    Requirements: 8.5
    """
    
    def __init__(
        self,
        config: Optional[ProfileInjectionConfig] = None,
    ):
        """
        初始化档案注入器
        
        Args:
            config: 注入配置
        """
        self.config = config or ProfileInjectionConfig()
        
        logger.info(
            f"ProfileInjector initialized: "
            f"style={self.config.format_style}"
        )
    
    def extract_key_profile(
        self,
        user_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        从用户档案中提取关键信息
        
        Args:
            user_profile: 完整用户档案
            
        Returns:
            提取的关键信息
            
        Requirements: 8.5
        """
        if not user_profile:
            return {}
        
        extracted = {}
        
        # 基础信息
        if self.config.include_basic_info:
            basic_info = user_profile.get("basic_info", {})
            extracted["basic_info"] = {
                "age": basic_info.get("age"),
                "gender": basic_info.get("gender"),
                "height": basic_info.get("height"),
                "weight": basic_info.get("weight"),
                "body_type": basic_info.get("body_type"),
            }
        
        # 健身水平
        if self.config.include_fitness_level:
            fitness_config = user_profile.get("fitness_config", {})
            extracted["fitness_level"] = {
                "level": fitness_config.get("fitness_level"),
                "training_days": fitness_config.get("training_days_per_week"),
                "session_duration": fitness_config.get("training_duration_per_session"),
            }
        
        # 健身目标
        if self.config.include_goals:
            fitness_goals = user_profile.get("fitness_goals", {})
            extracted["goals"] = {
                "primary_goal": fitness_goals.get("primary_goal"),
                "target_weight": fitness_goals.get("target_weight"),
            }
        
        # 伤病信息
        if self.config.include_injuries:
            health_profile = user_profile.get("health_status", {})
            injury_history = health_profile.get("injury_history", [])
            chronic_diseases = health_profile.get("chronic_diseases", [])
            medications = health_profile.get("medications", [])
            other_notes = health_profile.get("other_notes", "")

            if injury_history or chronic_diseases or medications or other_notes:
                extracted["health"] = {
                    "injury_history": injury_history,
                    "chronic_diseases": chronic_diseases,
                    "medications": medications,
                    "other_notes": other_notes,
                }
        
        # 偏好设置
        if self.config.include_preferences:
            training_system = user_profile.get("training_system", {})
            extracted["preferences"] = {
                "preferred_time": training_system.get("preferred_training_time"),
                "user_type": training_system.get("user_type"),
            }
        
        # 训练历史（可选）
        if self.config.include_training_history:
            training_system = user_profile.get("training_system", {})
            extracted["training_history"] = {
                "consecutive_weeks": training_system.get("consecutive_training_weeks"),
                "volume_multiplier": training_system.get("personal_volume_multiplier"),
            }

        # 营养档案
        if self.config.include_nutrition:
            nutrition = user_profile.get("nutrition_profile", {})
            auto_calc = nutrition.get("auto_calculated", {})
            user_settings = nutrition.get("user_settings", {})
            if auto_calc or user_settings:
                extracted["nutrition"] = {
                    "tdee": auto_calc.get("tdee"),
                    "bmr": auto_calc.get("bmr"),
                    "target_calories": auto_calc.get("target_calories"),
                    "macros": auto_calc.get("macros", {}),
                    "dietary_preferences": user_settings.get("dietary_preferences", []),
                    "allergies": user_settings.get("allergies", []),
                }

        # 力量数据
        if self.config.include_strength:
            strength = user_profile.get("strength_data", {})
            exercises = strength.get("exercises", {})
            if exercises:
                extracted["strength"] = {
                    "exercises": {k: {"estimated_1rm": v.get("estimated_1rm")} for k, v in exercises.items() if v.get("estimated_1rm")},
                }

        # FFMI评估
        if self.config.include_ffmi:
            ffmi = user_profile.get("ffmi_assessment", {})
            if ffmi.get("ffmi"):
                extracted["ffmi"] = {
                    "ffmi": ffmi.get("ffmi"),
                    "normalized_ffmi": ffmi.get("normalized_ffmi"),
                    "assessment": ffmi.get("assessment"),
                    "natural_potential": ffmi.get("natural_potential"),
                }

        # 训练偏好
        if self.config.include_training_prefs:
            training_prefs = user_profile.get("training_preferences", {})
            if training_prefs:
                extracted["training_prefs"] = {
                    "training_split": training_prefs.get("training_split"),
                    "training_location": training_prefs.get("training_location"),
                    "available_equipment": training_prefs.get("available_equipment", []),
                    "exercise_preferences": training_prefs.get("exercise_preferences", []),
                    "disliked_exercises": training_prefs.get("disliked_exercises", []),
                }

        # 体成分
        if self.config.include_body_composition:
            basic_info = user_profile.get("basic_info", {})
            body_fat = basic_info.get("body_fat_percentage")
            bmi = basic_info.get("bmi")
            if body_fat or bmi:
                extracted["body_composition"] = {
                    "body_fat_percentage": body_fat,
                    "bmi": bmi,
                }
        
        return extracted
    
    def format_profile_for_context(
        self,
        user_profile: Dict[str, Any],
        style: Optional[str] = None,
    ) -> str:
        """
        将用户档案格式化为上下文文本
        
        Args:
            user_profile: 用户档案
            style: 格式风格（可选，默认使用配置）
            
        Returns:
            格式化的档案文本
            
        Requirements: 8.5
        """
        if not user_profile:
            return ""
        
        style = style or self.config.format_style
        
        # 提取关键信息
        extracted = self.extract_key_profile(user_profile)
        
        if style == "concise":
            return self._format_concise(extracted)
        else:
            return self._format_detailed(extracted)
    
    def _format_concise(self, profile: Dict[str, Any]) -> str:
        """简洁格式"""
        parts = []
        
        # 基础信息
        basic = profile.get("basic_info", {})
        if basic:
            info_parts = []
            if basic.get("age"):
                info_parts.append(f"{basic['age']}岁")
            if basic.get("gender"):
                gender_map = {"male": "男", "female": "女"}
                info_parts.append(gender_map.get(basic["gender"], basic["gender"]))
            if basic.get("height"):
                info_parts.append(f"{basic['height']}cm")
            if basic.get("weight"):
                info_parts.append(f"{basic['weight']}kg")
            if info_parts:
                parts.append(f"基础信息: {', '.join(info_parts)}")
        
        # 健身水平
        fitness = profile.get("fitness_level", {})
        if fitness.get("level"):
            level_map = {
                "beginner": "初学者",
                "intermediate": "中级",
                "advanced": "高级",
            }
            level = level_map.get(fitness["level"], fitness["level"])
            days = fitness.get("training_days", "")
            if days:
                parts.append(f"健身水平: {level}, 每星期{days}天")
            else:
                parts.append(f"健身水平: {level}")
        
        # 健身目标
        goals = profile.get("goals", {})
        if goals.get("primary_goal"):
            goal_map = {
                "hypertrophy": "增肌",
                "fat_loss": "减脂",
                "strength": "力量提升",
                "endurance": "耐力提升",
                "general_fitness": "综合健身",
                "body_shaping": "塑形",
                "flexibility": "柔韧性",
            }
            goal = goal_map.get(goals["primary_goal"], goals["primary_goal"])
            parts.append(f"目标: {goal}")
        
        # 健康信息
        health = profile.get("health", {})
        injury_history = health.get("injury_history", [])
        chronic_diseases = health.get("chronic_diseases", [])
        medications = health.get("medications", [])
        health_notes = []
        if injury_history:
            health_notes.append(f"伤病: {', '.join(injury_history[:3])}")
        if chronic_diseases:
            health_notes.append(f"慢性病: {', '.join(chronic_diseases[:2])}")
        if medications:
            health_notes.append(f"用药: {', '.join(medications[:2])}")
        if health_notes:
            parts.append(f"注意事项: {'; '.join(health_notes)}")

        # 偏好
        prefs = profile.get("preferences", {})
        if prefs.get("user_type"):
            type_map = {"student": "学生", "worker": "上班族", "other": "其他"}
            parts.append(f"用户类型: {type_map.get(prefs['user_type'], prefs['user_type'])}")

        # 营养摘要
        nutrition = profile.get("nutrition", {})
        if nutrition.get("tdee"):
            parts.append(f"TDEE: {nutrition['tdee']}kcal")
        if nutrition.get("target_calories"):
            parts.append(f"目标热量: {nutrition['target_calories']}kcal")

        # 体成分
        body_comp = profile.get("body_composition", {})
        if body_comp.get("body_fat_percentage"):
            parts.append(f"体脂: {body_comp['body_fat_percentage']}%")

        # FFMI
        ffmi = profile.get("ffmi", {})
        if ffmi.get("ffmi"):
            parts.append(f"FFMI: {ffmi['ffmi']}")

        # 力量摘要
        strength = profile.get("strength", {})
        exercises = strength.get("exercises", {})
        if exercises:
            top_lifts = [f"{k}: {v['estimated_1rm']}kg" for k, v in list(exercises.items())[:3]]
            parts.append(f"1RM: {', '.join(top_lifts)}")

        # 训练偏好摘要
        tp = profile.get("training_prefs", {})
        if tp.get("training_split"):
            parts.append(f"分化: {tp['training_split']}")
        if tp.get("available_equipment"):
            parts.append(f"器械: {', '.join(tp['available_equipment'][:4])}")
        
        return "; ".join(parts) if parts else "用户档案未完善"
    
    def _format_detailed(self, profile: Dict[str, Any]) -> str:
        """详细格式"""
        lines = ["【用户档案】"]
        
        # 基础信息
        basic = profile.get("basic_info", {})
        if basic:
            lines.append("\n基础信息:")
            if basic.get("age"):
                lines.append(f"  - 年龄: {basic['age']}岁")
            if basic.get("gender"):
                gender_map = {"male": "男性", "female": "女性"}
                lines.append(f"  - 性别: {gender_map.get(basic['gender'], basic['gender'])}")
            if basic.get("height"):
                lines.append(f"  - 身高: {basic['height']}cm")
            if basic.get("weight"):
                lines.append(f"  - 体重: {basic['weight']}kg")
            if basic.get("body_type"):
                lines.append(f"  - 体型: {basic['body_type']}")
        
        # 健身水平
        fitness = profile.get("fitness_level", {})
        if fitness:
            lines.append("\n健身水平:")
            if fitness.get("level"):
                level_map = {
                    "beginner": "初学者",
                    "intermediate": "中级训练者",
                    "advanced": "高级训练者",
                }
                lines.append(f"  - 等级: {level_map.get(fitness['level'], fitness['level'])}")
            if fitness.get("training_days"):
                lines.append(f"  - 训练频率: 每星期{fitness['training_days']}天")
            if fitness.get("session_duration"):
                lines.append(f"  - 单次时长: {fitness['session_duration']}分钟")
        
        # 健身目标
        goals = profile.get("goals", {})
        if goals:
            lines.append("\n健身目标:")
            if goals.get("primary_goal"):
                goal_map = {
                    "hypertrophy": "增肌",
                    "fat_loss": "减脂",
                    "strength": "力量提升",
                    "endurance": "耐力提升",
                    "general_fitness": "综合健身",
                    "body_shaping": "塑形",
                    "flexibility": "柔韧性提升",
                }
                lines.append(f"  - 主要目标: {goal_map.get(goals['primary_goal'], goals['primary_goal'])}")
            if goals.get("target_weight"):
                lines.append(f"  - 目标体重: {goals['target_weight']}kg")
        
        # 健康信息
        health = profile.get("health", {})
        if health:
            injury_history = health.get("injury_history", [])
            chronic_diseases = health.get("chronic_diseases", [])
            medications = health.get("medications", [])
            other_notes = health.get("other_notes", "")
            if injury_history or chronic_diseases or medications or other_notes:
                lines.append("\n健康注意事项:")
                for injury in injury_history[:5]:
                    lines.append(f"  - ⚠️ 伤病: {injury}")
                for disease in chronic_diseases[:3]:
                    lines.append(f"  - 🏥 慢性病: {disease}")
                for med in medications[:3]:
                    lines.append(f"  - 💊 用药: {med}")
                if other_notes:
                    lines.append(f"  - 📝 备注: {other_notes}")
        
        # 偏好设置
        prefs = profile.get("preferences", {})
        if prefs:
            lines.append("\n偏好设置:")
            if prefs.get("user_type"):
                type_map = {"student": "大学生", "worker": "上班族", "other": "其他"}
                lines.append(f"  - 用户类型: {type_map.get(prefs['user_type'], prefs['user_type'])}")
            if prefs.get("preferred_time"):
                lines.append(f"  - 偏好时间: {prefs['preferred_time']}")

        # 体成分
        body_comp = profile.get("body_composition", {})
        if body_comp:
            has_data = body_comp.get("body_fat_percentage") or body_comp.get("bmi")
            if has_data:
                lines.append("\n体成分:")
                if body_comp.get("body_fat_percentage"):
                    lines.append(f"  - 体脂率: {body_comp['body_fat_percentage']}%")
                if body_comp.get("bmi"):
                    lines.append(f"  - BMI: {body_comp['bmi']}")

        # FFMI评估
        ffmi = profile.get("ffmi", {})
        if ffmi.get("ffmi"):
            lines.append("\nFFMI评估:")
            lines.append(f"  - FFMI: {ffmi['ffmi']}")
            if ffmi.get("normalized_ffmi"):
                lines.append(f"  - 标准化FFMI: {ffmi['normalized_ffmi']}")
            if ffmi.get("assessment"):
                lines.append(f"  - 评级: {ffmi['assessment']}")
            if ffmi.get("natural_potential"):
                lines.append(f"  - 自然潜力: {ffmi['natural_potential']}")

        # 营养档案
        nutrition = profile.get("nutrition", {})
        if nutrition:
            has_data = nutrition.get("tdee") or nutrition.get("dietary_preferences")
            if has_data:
                lines.append("\n营养档案:")
                if nutrition.get("tdee"):
                    lines.append(f"  - TDEE: {nutrition['tdee']}kcal")
                if nutrition.get("bmr"):
                    lines.append(f"  - BMR: {nutrition['bmr']}kcal")
                if nutrition.get("target_calories"):
                    lines.append(f"  - 目标热量: {nutrition['target_calories']}kcal")
                macros = nutrition.get("macros", {})
                if macros:
                    lines.append(f"  - 宏量: 蛋白{macros.get('protein_g', '?')}g / 碳水{macros.get('carbs_g', '?')}g / 脂肪{macros.get('fat_g', '?')}g")
                if nutrition.get("dietary_preferences"):
                    lines.append(f"  - 饮食偏好: {', '.join(nutrition['dietary_preferences'])}")
                if nutrition.get("allergies"):
                    lines.append(f"  - 过敏: {', '.join(nutrition['allergies'])}")

        # 力量数据
        strength = profile.get("strength", {})
        exercises = strength.get("exercises", {})
        if exercises:
            lines.append("\n力量水平 (估算1RM):")
            for name, data in list(exercises.items())[:5]:
                lines.append(f"  - {name}: {data['estimated_1rm']}kg")

        # 训练偏好
        tp = profile.get("training_prefs", {})
        if tp:
            has_data = tp.get("training_split") or tp.get("available_equipment")
            if has_data:
                lines.append("\n训练偏好:")
                if tp.get("training_split"):
                    lines.append(f"  - 训练分化: {tp['training_split']}")
                if tp.get("training_location"):
                    lines.append(f"  - 训练地点: {tp['training_location']}")
                if tp.get("available_equipment"):
                    lines.append(f"  - 可用器械: {', '.join(tp['available_equipment'][:6])}")
                if tp.get("exercise_preferences"):
                    lines.append(f"  - 偏好动作类型: {', '.join(tp['exercise_preferences'][:4])}")
                if tp.get("disliked_exercises"):
                    lines.append(f"  - 不喜欢的动作: {', '.join(tp['disliked_exercises'][:4])}")
        
        return "\n".join(lines)
    
    def build_system_prompt_with_profile(
        self,
        base_prompt: str,
        user_profile: Dict[str, Any],
    ) -> str:
        """
        构建包含用户档案的系统提示词
        
        Args:
            base_prompt: 基础系统提示词
            user_profile: 用户档案
            
        Returns:
            包含档案的完整提示词
        """
        profile_text = self.format_profile_for_context(user_profile)
        
        if not profile_text:
            return base_prompt
        
        return f"""{base_prompt}

{profile_text}

请根据用户的个人情况提供个性化的建议。"""
    
    def calculate_profile_utilization(
        self,
        user_profile: Dict[str, Any],
        response: str,
    ) -> float:
        """
        计算档案利用率
        
        检查响应中是否引用了用户档案信息
        
        Args:
            user_profile: 用户档案
            response: 系统响应
            
        Returns:
            利用率（0-100%）
        """
        if not user_profile or not response:
            return 0.0
        
        # 提取关键信息
        extracted = self.extract_key_profile(user_profile)
        
        # 检查各类信息是否被引用
        utilized_count = 0
        total_count = 0
        
        # 检查基础信息
        basic = extracted.get("basic_info", {})
        if basic:
            total_count += 1
            if any(str(v) in response for v in basic.values() if v):
                utilized_count += 1
        
        # 检查健身水平
        fitness = extracted.get("fitness_level", {})
        if fitness.get("level"):
            total_count += 1
            level_keywords = {
                "beginner": ["初学", "新手", "入门"],
                "intermediate": ["中级", "进阶"],
                "advanced": ["高级", "资深"],
            }
            level = fitness["level"]
            if any(kw in response for kw in level_keywords.get(level, [])):
                utilized_count += 1
        
        # 检查目标
        goals = extracted.get("goals", {})
        if goals.get("primary_goal"):
            total_count += 1
            goal_keywords = {
                "hypertrophy": ["增肌", "肌肉"],
                "fat_loss": ["减脂", "减肥", "燃脂"],
                "strength": ["力量", "强壮"],
            }
            goal = goals["primary_goal"]
            if any(kw in response for kw in goal_keywords.get(goal, [])):
                utilized_count += 1
        
        # 检查伤病
        health = extracted.get("health", {})
        injury_history = health.get("injury_history", [])
        if injury_history:
            total_count += 1
            if any(injury in response for injury in injury_history):
                utilized_count += 1
        
        if total_count == 0:
            return 0.0
        
        return (utilized_count / total_count) * 100
