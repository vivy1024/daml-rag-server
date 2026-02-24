"""
TDEE计算器 MCP工具

基于Mifflin-St Jeor公式计算每日总能量消耗（TDEE）
参考TypeScript的tdee-calculator实现

功能特性：
- 使用Mifflin-St Jeor公式计算基础代谢率（BMR）
- 基于活动水平计算TDEE（训练频率、强度、日常活动）
- 基于用户目标调整热量（增肌+300-500，减脂-300-500）
- 计算三大营养素比例（蛋白质、碳水化合物、脂肪）
- 处理特殊饮食需求（高蛋白、低碳水、生酮等）

作者: BUILD_BODY Team
版本: v1.0.0
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import logging

from ...mcp_tools.base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


# =============================================================================
# 输入Schema定义
# =============================================================================

class TDEECalculatorInput(BaseModel):
    """TDEE计算器输入"""
    user_id: str = Field(..., description="用户ID，用于获取用户档案")
    
    # 基础信息（如果用户档案中没有，则必须提供）
    age: Optional[int] = Field(None, ge=10, le=120, description="年龄（岁）")
    gender: Optional[Literal["male", "female"]] = Field(None, description="性别")
    weight_kg: Optional[float] = Field(None, ge=30, le=300, description="体重（公斤）")
    height_cm: Optional[float] = Field(None, ge=100, le=250, description="身高（厘米）")
    
    # 活动水平
    training_frequency_per_week: int = Field(
        ..., ge=0, le=7, description="每星期训练频率"
    )
    training_intensity: Literal["low", "moderate", "high"] = Field(
        ..., description="训练强度"
    )
    daily_activity_level: Literal["sedentary", "lightly_active", "moderately_active", "very_active", "extremely_active"] = Field(
        ..., description="日常活动水平"
    )
    
    # 目标
    fitness_goal: Literal["fat_loss", "maintenance", "hypertrophy", "recomp"] = Field(
        ..., description="健身目标"
    )
    
    # 特殊饮食需求（可选）
    dietary_preference: Optional[Literal["balanced", "high_protein", "low_carb", "keto", "vegetarian", "vegan"]] = Field(
        None, description="饮食偏好"
    )


# =============================================================================
# 输出类型定义
# =============================================================================

class BMRCalculation(BaseModel):
    """基础代谢率计算"""
    bmr: float
    formula: str
    calculation_details: str


class ActivityMultiplier(BaseModel):
    """活动系数"""
    multiplier: float
    training_contribution: float
    daily_activity_contribution: float
    reasoning: str


class CalorieTarget(BaseModel):
    """热量目标"""
    tdee: float
    target_calories: float
    adjustment: int
    reasoning: str


class MacronutrientDistribution(BaseModel):
    """三大营养素分配"""
    protein_grams: float
    protein_calories: float
    protein_percentage: float
    
    carbs_grams: float
    carbs_calories: float
    carbs_percentage: float
    
    fat_grams: float
    fat_calories: float
    fat_percentage: float
    
    reasoning: str


class MealTiming(BaseModel):
    """进餐时机建议"""
    meals_per_day: int
    calories_per_meal: float
    pre_workout_calories: float
    post_workout_calories: float
    recommendations: List[str]


class TDEECalculatorOutput(BaseModel):
    """TDEE计算器输出"""
    success: bool
    tool_name: str
    user_id: str
    
    # 基础信息
    user_info: Dict[str, Any]
    
    # BMR计算
    bmr_calculation: BMRCalculation
    
    # 活动系数
    activity_multiplier: ActivityMultiplier
    
    # 热量目标
    calorie_target: CalorieTarget
    
    # 三大营养素分配
    macronutrient_distribution: MacronutrientDistribution
    
    # 进餐时机建议
    meal_timing: MealTiming
    
    # 额外建议
    additional_recommendations: List[str]
    
    execution_time_ms: float
    confidence_score: float


# =============================================================================
# TDEE计算器类
# =============================================================================

class TDEECalculator(BaseMCPTool):
    """TDEE计算器"""
    
    def get_name(self) -> str:
        return "tdee_calculator"
    
    def get_description(self) -> str:
        return "TDEE计算器 - 基于Mifflin-St Jeor公式的个性化热量和营养素计算"
    
    def get_category(self) -> str:
        return "nutrition"
    
    def get_input_schema(self) -> type[BaseModel]:
        return TDEECalculatorInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return TDEECalculatorOutput
    
    def get_complexity(self) -> str:
        return "medium"
    
    def get_estimated_duration(self) -> float:
        return 800.0
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["user_profile_mcp"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行TDEE计算
        
        流程：
        1. 获取用户档案（年龄、性别、体重、身高）
        2. 使用Mifflin-St Jeor公式计算BMR
        3. 计算活动系数（训练频率、强度、日常活动）
        4. 计算TDEE
        5. 基于用户目标调整热量
        6. 计算三大营养素比例
        7. 生成进餐时机建议
        8. 处理特殊饮食需求
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: 获取用户档案（优先从 input_data 获取，DAG 编排器注入）
            user_profile = input_data.get("user_profile") or await self._get_user_profile(input_data.get("user_id"))
            
            # 合并用户档案和输入数据
            user_info = self._merge_user_info(input_data, user_profile)
            
            # 验证必需信息
            self._validate_user_info(user_info)
            
            # Step 2: 计算BMR（Mifflin-St Jeor公式）
            bmr_calculation = self._calculate_bmr(user_info)
            
            # Step 3: 计算活动系数
            activity_multiplier = self._calculate_activity_multiplier(
                input_data["training_frequency_per_week"],
                input_data["training_intensity"],
                input_data["daily_activity_level"]
            )
            
            # Step 4: 计算TDEE
            tdee = bmr_calculation.bmr * activity_multiplier.multiplier
            
            # Step 5: 基于用户目标调整热量
            calorie_target = self._calculate_calorie_target(
                tdee,
                input_data["fitness_goal"]
            )
            
            # Step 6: 计算三大营养素比例
            macronutrient_distribution = self._calculate_macronutrient_distribution(
                calorie_target.target_calories,
                user_info["weight_kg"],
                input_data["fitness_goal"],
                input_data.get("dietary_preference", "balanced")
            )
            
            # Step 7: 生成进餐时机建议
            meal_timing = self._generate_meal_timing(
                calorie_target.target_calories,
                input_data["training_frequency_per_week"]
            )
            
            # Step 8: 生成额外建议
            additional_recommendations = self._generate_additional_recommendations(
                input_data,
                user_info,
                calorie_target,
                macronutrient_distribution
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": "tdee_calculator",
                "user_id": input_data["user_id"],
                "user_info": user_info,
                "bmr_calculation": bmr_calculation.model_dump(),
                "activity_multiplier": activity_multiplier.model_dump(),
                "calorie_target": calorie_target.model_dump(),
                "macronutrient_distribution": macronutrient_distribution.model_dump(),
                "meal_timing": meal_timing.model_dump(),
                "additional_recommendations": additional_recommendations,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 92.0
            }
            
            self.logger.info(
                f"✅ TDEE计算完成: TDEE={tdee:.0f}卡, "
                f"目标={calorie_target.target_calories:.0f}卡"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ TDEE计算失败: {e}", exc_info=True)
            raise
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案（从 input_data 中注入的 user_profile 或空字典）"""
        # Agent 模式下 user_profile 由 tool_node 注入到 input_data
        # DAG 模式下由工作流预加载
        return {}

    def _merge_user_info(
        self,
        input_data: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并用户档案和输入数据"""
        # 优先使用输入数据，其次使用用户档案
        # Agent 模式下 user_profile 可能在 input_data 中
        profile = input_data.get("user_profile", user_profile) or {}
        basic_info = profile.get("basic_info", {})

        return {
            "age": input_data.get("age") or basic_info.get("age"),
            "gender": input_data.get("gender") or basic_info.get("gender"),
            # 兼容 weight/weight_kg 和 height/height_cm 两种字段名
            "weight_kg": input_data.get("weight_kg") or basic_info.get("weight_kg") or basic_info.get("weight"),
            "height_cm": input_data.get("height_cm") or basic_info.get("height_cm") or basic_info.get("height"),
        }
    
    def _validate_user_info(self, user_info: Dict[str, Any]) -> None:
        """验证必需信息"""
        required_fields = ["age", "gender", "weight_kg", "height_cm"]
        missing_fields = [f for f in required_fields if not user_info.get(f)]
        
        if missing_fields:
            raise ValueError(
                f"缺少必需信息: {', '.join(missing_fields)}。"
                f"请在输入中提供或确保用户档案包含这些信息。"
            )
    
    def _calculate_bmr(self, user_info: Dict[str, Any]) -> BMRCalculation:
        """
        使用Mifflin-St Jeor公式计算BMR
        
        男性: BMR = 10 × 体重(kg) + 6.25 × 身高(cm) - 5 × 年龄(岁) + 5
        女性: BMR = 10 × 体重(kg) + 6.25 × 身高(cm) - 5 × 年龄(岁) - 161
        """
        weight_kg = user_info["weight_kg"]
        height_cm = user_info["height_cm"]
        age = user_info["age"]
        gender = user_info["gender"]
        
        # 计算BMR
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age
        
        if gender == "male":
            bmr += 5
            gender_adjustment = "+5"
        else:  # female
            bmr -= 161
            gender_adjustment = "-161"
        
        calculation_details = (
            f"10 × {weight_kg}kg + 6.25 × {height_cm}cm - 5 × {age}岁 {gender_adjustment} "
            f"= {bmr:.0f}卡/天"
        )
        
        return BMRCalculation(
            bmr=round(bmr, 1),
            formula="Mifflin-St Jeor公式",
            calculation_details=calculation_details
        )
    
    def _calculate_activity_multiplier(
        self,
        training_frequency: int,
        training_intensity: str,
        daily_activity_level: str
    ) -> ActivityMultiplier:
        """
        计算活动系数
        
        活动系数 = 日常活动系数 + 训练贡献系数
        """
        # 日常活动系数（基础）
        daily_activity_multipliers = {
            "sedentary": 1.2,           # 久坐（办公室工作）
            "lightly_active": 1.375,    # 轻度活动（每星期1-3天轻度运动）
            "moderately_active": 1.55,  # 中度活动（每星期3-5天中度运动）
            "very_active": 1.725,       # 高度活动（每星期6-7天高强度运动）
            "extremely_active": 1.9     # 极度活动（每天多次高强度运动）
        }
        
        daily_multiplier = daily_activity_multipliers.get(daily_activity_level, 1.55)
        
        # 训练贡献系数
        # 基于训练频率和强度计算额外的能量消耗
        intensity_factors = {
            "low": 0.02,      # 低强度：每次训练增加2%
            "moderate": 0.04, # 中强度：每次训练增加4%
            "high": 0.06      # 高强度：每次训练增加6%
        }
        
        intensity_factor = intensity_factors.get(training_intensity, 0.04)
        training_contribution = training_frequency * intensity_factor
        
        # 总活动系数
        total_multiplier = daily_multiplier + training_contribution
        
        reasoning = (
            f"日常活动系数（{daily_activity_level}）: {daily_multiplier:.2f}；"
            f"训练贡献（{training_frequency}次/周 × {training_intensity}强度）: "
            f"+{training_contribution:.2f}；"
            f"总系数: {total_multiplier:.2f}"
        )
        
        return ActivityMultiplier(
            multiplier=round(total_multiplier, 2),
            training_contribution=round(training_contribution, 2),
            daily_activity_contribution=round(daily_multiplier, 2),
            reasoning=reasoning
        )
    
    def _calculate_calorie_target(
        self,
        tdee: float,
        fitness_goal: str
    ) -> CalorieTarget:
        """
        基于用户目标调整热量
        
        - 减脂: TDEE - 300-500卡
        - 维持: TDEE
        - 增肌: TDEE + 300-500卡
        - 重组成: TDEE（或略低）
        """
        adjustments = {
            "fat_loss": -400,         # 减脂：-400卡
            "maintenance": 0,         # 维持：0卡
            "hypertrophy": 400,       # 增肌：+400卡
            "recomp": -100            # 重组成：-100卡（轻微赤字）
        }

        adjustment = adjustments.get(fitness_goal, 0)
        target_calories = tdee + adjustment

        goal_descriptions = {
            "fat_loss": "减脂目标，创造热量赤字",
            "maintenance": "维持体重，保持热量平衡",
            "hypertrophy": "增肌目标，创造热量盈余",
            "recomp": "身体重组成，轻微热量赤字配合力量训练"
        }
        
        reasoning = (
            f"TDEE: {tdee:.0f}卡/天；"
            f"{goal_descriptions.get(fitness_goal, '')}；"
            f"调整: {adjustment:+d}卡；"
            f"目标热量: {target_calories:.0f}卡/天"
        )
        
        return CalorieTarget(
            tdee=round(tdee, 1),
            target_calories=round(target_calories, 1),
            adjustment=adjustment,
            reasoning=reasoning
        )
    
    def _calculate_macronutrient_distribution(
        self,
        target_calories: float,
        weight_kg: float,
        fitness_goal: str,
        dietary_preference: str
    ) -> MacronutrientDistribution:
        """
        计算三大营养素比例
        
        蛋白质: 4卡/克
        碳水化合物: 4卡/克
        脂肪: 9卡/克
        """
        # 基于目标和饮食偏好确定营养素比例
        if dietary_preference == "high_protein":
            protein_ratio = 0.35
            carbs_ratio = 0.35
            fat_ratio = 0.30
        elif dietary_preference == "low_carb":
            protein_ratio = 0.30
            carbs_ratio = 0.25
            fat_ratio = 0.45
        elif dietary_preference == "keto":
            protein_ratio = 0.25
            carbs_ratio = 0.05
            fat_ratio = 0.70
        elif dietary_preference in ["vegetarian", "vegan"]:
            protein_ratio = 0.25
            carbs_ratio = 0.50
            fat_ratio = 0.25
        else:  # balanced
            if fitness_goal == "hypertrophy":
                protein_ratio = 0.30
                carbs_ratio = 0.45
                fat_ratio = 0.25
            elif fitness_goal == "fat_loss":
                protein_ratio = 0.35
                carbs_ratio = 0.35
                fat_ratio = 0.30
            else:  # maintenance, recomp
                protein_ratio = 0.30
                carbs_ratio = 0.40
                fat_ratio = 0.30
        
        # 计算蛋白质（也可以基于体重：1.6-2.2g/kg）
        protein_grams_by_weight = weight_kg * 2.0  # 2g/kg体重
        protein_calories_by_ratio = target_calories * protein_ratio
        protein_grams_by_ratio = protein_calories_by_ratio / 4
        
        # 使用两种方法的平均值
        protein_grams = (protein_grams_by_weight + protein_grams_by_ratio) / 2
        protein_calories = protein_grams * 4
        
        # 计算脂肪
        fat_calories = target_calories * fat_ratio
        fat_grams = fat_calories / 9
        
        # 计算碳水（剩余热量）
        carbs_calories = target_calories - protein_calories - fat_calories
        carbs_grams = carbs_calories / 4
        
        # 计算百分比
        protein_percentage = (protein_calories / target_calories) * 100
        carbs_percentage = (carbs_calories / target_calories) * 100
        fat_percentage = (fat_calories / target_calories) * 100
        
        reasoning = (
            f"基于{fitness_goal}目标和{dietary_preference}饮食偏好；"
            f"蛋白质: {protein_percentage:.0f}%，"
            f"碳水: {carbs_percentage:.0f}%，"
            f"脂肪: {fat_percentage:.0f}%"
        )
        
        return MacronutrientDistribution(
            protein_grams=round(protein_grams, 1),
            protein_calories=round(protein_calories, 1),
            protein_percentage=round(protein_percentage, 1),
            carbs_grams=round(carbs_grams, 1),
            carbs_calories=round(carbs_calories, 1),
            carbs_percentage=round(carbs_percentage, 1),
            fat_grams=round(fat_grams, 1),
            fat_calories=round(fat_calories, 1),
            fat_percentage=round(fat_percentage, 1),
            reasoning=reasoning
        )
    
    def _generate_meal_timing(
        self,
        target_calories: float,
        training_frequency: int
    ) -> MealTiming:
        """生成进餐时机建议"""
        # 基于总热量确定进餐次数
        if target_calories < 1800:
            meals_per_day = 3
        elif target_calories < 2500:
            meals_per_day = 4
        else:
            meals_per_day = 5
        
        calories_per_meal = target_calories / meals_per_day
        
        # 训练前后热量分配
        if training_frequency > 0:
            pre_workout_calories = target_calories * 0.25  # 训练前25%
            post_workout_calories = target_calories * 0.30  # 训练后30%
        else:
            pre_workout_calories = 0
            post_workout_calories = 0
        
        recommendations = [
            f"建议每天{meals_per_day}餐，每餐约{calories_per_meal:.0f}卡",
            "早餐应包含充足蛋白质和碳水，启动代谢"
        ]
        
        if training_frequency > 0:
            recommendations.extend([
                f"训练前1-2小时：{pre_workout_calories:.0f}卡（碳水为主，适量蛋白质）",
                f"训练后30分钟内：{post_workout_calories:.0f}卡（快速碳水+蛋白质）",
                "训练日可适当增加碳水摄入，休息日可减少"
            ])
        
        recommendations.append("睡前避免大量碳水，可摄入缓释蛋白质（如酪蛋白）")
        
        return MealTiming(
            meals_per_day=meals_per_day,
            calories_per_meal=round(calories_per_meal, 1),
            pre_workout_calories=round(pre_workout_calories, 1),
            post_workout_calories=round(post_workout_calories, 1),
            recommendations=recommendations
        )
    
    def _generate_additional_recommendations(
        self,
        input_data: Dict[str, Any],
        user_info: Dict[str, Any],
        calorie_target: CalorieTarget,
        macronutrient_distribution: MacronutrientDistribution
    ) -> List[str]:
        """生成额外建议"""
        recommendations = []
        
        # 基于目标的建议
        fitness_goal = input_data["fitness_goal"]
        if fitness_goal == "fat_loss":
            recommendations.extend([
                "减脂期间保持高蛋白摄入，保护肌肉量",
                "优先选择高纤维、低GI碳水（燕麦、糙米、红薯）",
                "每星期称重1-2次，根据体重变化调整热量（目标：每星期减重0.5-1kg）"
            ])
        elif fitness_goal == "hypertrophy":
            recommendations.extend([
                "增肌期间确保热量盈余，配合力量训练",
                "训练后及时补充碳水和蛋白质，促进恢复",
                "每星期称重，目标：每星期增重0.25-0.5kg（避免过快增重导致脂肪堆积）"
            ])
        elif fitness_goal == "recomp":
            recommendations.extend([
                "身体重组成需要耐心，配合力量训练和充足蛋白质",
                "关注身体成分变化（体脂率、肌肉量），而非单纯体重",
                "保持训练强度，确保渐进超负荷"
            ])
        
        # 基于饮食偏好的建议
        dietary_preference = input_data.get("dietary_preference", "balanced")
        if dietary_preference == "keto":
            recommendations.append("生酮饮食：注意电解质补充（钠、钾、镁），多喝水")
        elif dietary_preference in ["vegetarian", "vegan"]:
            recommendations.append("素食者：注意补充维生素B12、铁、锌、omega-3")
        
        # 通用建议
        recommendations.extend([
            "保持充足水分摄入（每天至少2-3升）",
            "定期评估进展，每2-4周根据反馈调整热量和营养素比例",
            "优先选择天然、未加工食物，避免过多加工食品"
        ])
        
        # 基于蛋白质摄入的建议
        protein_per_kg = macronutrient_distribution.protein_grams / user_info["weight_kg"]
        if protein_per_kg < 1.6:
            recommendations.append(
                f"⚠️ 当前蛋白质摄入（{protein_per_kg:.1f}g/kg）偏低，"
                f"建议增加至1.6-2.2g/kg以支持肌肉恢复和生长"
            )
        
        return recommendations
