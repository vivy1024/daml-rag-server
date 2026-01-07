"""
膳食营养指导器 MCP工具

基于TDEE计算结果提供营养指导和食物推荐

功能特性：
- 基于TDEE设计每日营养分配方案
- 分配三大营养素到各餐（告诉用户每餐吃多少）
- 基于微量元素和维生素推荐食物类别
- 不强制具体食物和份量，给用户灵活选择空间
- 考虑用户实际情况（周边食材、做饭能力、预算等）

作者: BUILD_BODY Team
版本: v2.0.0
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import logging

from ...mcp_tools.base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


# =============================================================================
# 输入Schema定义
# =============================================================================

class MealPlanDesignerInput(BaseModel):
    """膳食营养指导器输入"""
    user_id: str = Field(..., description="用户ID")
    
    # 营养目标（来自TDEE计算）
    target_calories: float = Field(..., ge=1000, le=5000, description="目标热量（卡）")
    target_protein_grams: float = Field(..., ge=50, le=500, description="目标蛋白质（克）")
    target_carbs_grams: float = Field(..., ge=50, le=800, description="目标碳水（克）")
    target_fat_grams: float = Field(..., ge=30, le=200, description="目标脂肪（克）")
    
    # 饮食偏好
    dietary_preference: Literal["balanced", "high_protein", "low_carb", "keto", "vegetarian", "vegan"] = Field(
        default="balanced", description="饮食偏好"
    )
    
    # 进餐偏好
    meals_per_day: int = Field(default=4, ge=3, le=6, description="每天进餐次数")
    
    # 训练相关
    training_days_per_week: int = Field(default=0, ge=0, le=7, description="每周训练天数")
    
    # 健身目标
    fitness_goal: Literal["weight_loss", "maintenance", "muscle_gain", "recomp"] = Field(
        default="maintenance", description="健身目标"
    )



# =============================================================================
# 输出类型定义
# =============================================================================

class MealNutritionTarget(BaseModel):
    """单餐营养目标"""
    meal_type: str
    meal_time: str
    target_calories: float
    target_protein: float
    target_carbs: float
    target_fat: float
    nutrition_tips: List[str]


class FoodRecommendation(BaseModel):
    """食物推荐"""
    category: str  # 蛋白质、碳水、蔬菜、水果、健康脂肪
    recommended_foods: List[str]
    nutrition_benefits: List[str]  # 营养益处（富含锌镁、欧米伽3、维生素E/C等）
    selection_tips: List[str]  # 选择建议


class DayNutritionPlan(BaseModel):
    """单日营养计划"""
    day_type: Literal["training", "rest"]
    meals: List[MealNutritionTarget]
    daily_totals: Dict[str, float]
    key_nutrients_focus: List[str]  # 当天重点关注的营养素
    hydration_target: str  # 水分摄入目标


class MealPlanDesignerOutput(BaseModel):
    """膳食营养指导器输出"""
    success: bool
    tool_name: str
    user_id: str
    
    # 营养计划概览
    plan_summary: Dict[str, Any]
    
    # 训练日营养方案
    training_day_plan: DayNutritionPlan
    
    # 休息日营养方案
    rest_day_plan: DayNutritionPlan
    
    # 食物推荐（按类别）
    food_recommendations: List[FoodRecommendation]
    
    # 微量元素和维生素指导
    micronutrient_guidance: Dict[str, Any]
    
    # 实用建议
    practical_tips: List[str]
    
    # 灵活调整建议
    flexibility_tips: List[str]
    
    execution_time_ms: float
    confidence_score: float



# =============================================================================
# 膳食营养指导器类
# =============================================================================

class MealPlanDesigner(BaseMCPTool):
    """膳食营养指导器"""
    
    def get_name(self) -> str:
        return "meal_plan_designer"
    
    def get_description(self) -> str:
        return "膳食营养指导器 - 提供营养分配方案和食物推荐，不强制具体食物计划"
    
    def get_category(self) -> str:
        return "nutrition"
    
    def get_input_schema(self) -> type[BaseModel]:
        return MealPlanDesignerInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return MealPlanDesignerOutput
    
    def get_complexity(self) -> str:
        return "medium"
    
    def get_estimated_duration(self) -> float:
        return 500.0
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["user_profile_mcp"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行膳食营养指导
        
        流程：
        1. 计算每餐营养分配（告诉用户每餐吃多少）
        2. 生成训练日和休息日方案
        3. 基于微量元素推荐食物类别
        4. 提供灵活的实用建议
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: 计算每餐营养分配
            training_day_plan = self._create_training_day_plan(input_data)
            rest_day_plan = self._create_rest_day_plan(input_data)
            
            # Step 2: 生成食物推荐（基于营养益处）
            food_recommendations = self._generate_food_recommendations(input_data)
            
            # Step 3: 生成微量元素指导
            micronutrient_guidance = self._generate_micronutrient_guidance(input_data)
            
            # Step 4: 生成实用建议
            practical_tips = self._generate_practical_tips(input_data)
            
            # Step 5: 生成灵活调整建议
            flexibility_tips = self._generate_flexibility_tips(input_data)
            
            # 计划概览
            plan_summary = self._generate_plan_summary(input_data)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": "meal_plan_designer",
                "user_id": input_data["user_id"],
                "plan_summary": plan_summary,
                "training_day_plan": training_day_plan.model_dump(),
                "rest_day_plan": rest_day_plan.model_dump(),
                "food_recommendations": [r.model_dump() for r in food_recommendations],
                "micronutrient_guidance": micronutrient_guidance,
                "practical_tips": practical_tips,
                "flexibility_tips": flexibility_tips,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 95.0
            }
            
            self.logger.info(
                f"✅ 膳食营养指导完成: 目标{input_data['target_calories']:.0f}卡/天"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 膳食营养指导失败: {e}", exc_info=True)
            raise

    
    def _create_training_day_plan(self, input_data: Dict[str, Any]) -> DayNutritionPlan:
        """创建训练日营养方案"""
        meals_per_day = input_data["meals_per_day"]
        target_calories = input_data["target_calories"]
        target_protein = input_data["target_protein_grams"]
        target_carbs = input_data["target_carbs_grams"]
        target_fat = input_data["target_fat_grams"]
        
        # 训练日餐次分配（包含训练前后）
        if meals_per_day == 3:
            distribution = {
                "breakfast": (0.25, "07:00"),
                "lunch": (0.30, "12:00"),
                "pre_workout": (0.15, "16:00"),
                "post_workout": (0.20, "18:30"),
                "dinner": (0.10, "20:00")
            }
        elif meals_per_day == 4:
            distribution = {
                "breakfast": (0.20, "07:00"),
                "lunch": (0.25, "12:00"),
                "pre_workout": (0.15, "16:00"),
                "post_workout": (0.20, "18:30"),
                "dinner": (0.20, "20:00")
            }
        else:  # 5-6餐
            distribution = {
                "breakfast": (0.18, "07:00"),
                "morning_snack": (0.10, "10:00"),
                "lunch": (0.22, "12:00"),
                "pre_workout": (0.15, "16:00"),
                "post_workout": (0.20, "18:30"),
                "dinner": (0.15, "20:00")
            }
        
        meals = []
        for meal_type, (ratio, meal_time) in distribution.items():
            # 训练前后调整碳水比例
            if meal_type == "pre_workout":
                # 训练前：碳水为主，少量蛋白质
                meal_protein = target_protein * ratio * 0.6
                meal_carbs = target_carbs * ratio * 1.4
                meal_fat = target_fat * ratio * 0.5
                tips = [
                    "训练前1-2小时进食",
                    f"重点：快速碳水{meal_carbs:.0f}g（香蕉、燕麦、面包）",
                    f"适量蛋白质{meal_protein:.0f}g",
                    "避免高脂肪食物，影响消化"
                ]
            elif meal_type == "post_workout":
                # 训练后：快速碳水+蛋白质
                meal_protein = target_protein * ratio * 1.2
                meal_carbs = target_carbs * ratio * 1.3
                meal_fat = target_fat * ratio * 0.6
                tips = [
                    "训练后30分钟内进食",
                    f"重点：快速碳水{meal_carbs:.0f}g + 蛋白质{meal_protein:.0f}g",
                    "促进肌肉恢复和糖原补充",
                    "可以喝蛋白粉+香蕉"
                ]
            else:
                meal_protein = target_protein * ratio
                meal_carbs = target_carbs * ratio
                meal_fat = target_fat * ratio
                tips = [f"均衡摄入三大营养素"]
            
            meal_calories = meal_protein * 4 + meal_carbs * 4 + meal_fat * 9
            
            meals.append(MealNutritionTarget(
                meal_type=meal_type,
                meal_time=meal_time,
                target_calories=round(meal_calories, 0),
                target_protein=round(meal_protein, 0),
                target_carbs=round(meal_carbs, 0),
                target_fat=round(meal_fat, 0),
                nutrition_tips=tips
            ))
        
        return DayNutritionPlan(
            day_type="training",
            meals=meals,
            daily_totals={
                "calories": target_calories,
                "protein": target_protein,
                "carbs": target_carbs,
                "fat": target_fat
            },
            key_nutrients_focus=[
                "训练前：快速碳水（香蕉、燕麦、白米饭）",
                "训练后：蛋白质+碳水（鸡胸肉+米饭、蛋白粉+香蕉）",
                "全天：充足蛋白质支持肌肉恢复"
            ],
            hydration_target="训练日至少3-4升水，训练中每15分钟补水200ml"
        )

    
    def _create_rest_day_plan(self, input_data: Dict[str, Any]) -> DayNutritionPlan:
        """创建休息日营养方案"""
        meals_per_day = input_data["meals_per_day"]
        target_calories = input_data["target_calories"] * 0.9  # 休息日略减10%
        target_protein = input_data["target_protein_grams"]  # 蛋白质保持
        target_carbs = input_data["target_carbs_grams"] * 0.8  # 碳水减少20%
        target_fat = input_data["target_fat_grams"] * 1.1  # 脂肪略增
        
        # 休息日餐次分配（无训练前后）
        if meals_per_day == 3:
            distribution = {
                "breakfast": (0.30, "07:00"),
                "lunch": (0.40, "12:00"),
                "dinner": (0.30, "19:00")
            }
        elif meals_per_day == 4:
            distribution = {
                "breakfast": (0.25, "07:00"),
                "lunch": (0.30, "12:00"),
                "snack": (0.15, "15:00"),
                "dinner": (0.30, "19:00")
            }
        else:  # 5-6餐
            distribution = {
                "breakfast": (0.20, "07:00"),
                "morning_snack": (0.10, "10:00"),
                "lunch": (0.30, "12:00"),
                "afternoon_snack": (0.10, "15:00"),
                "dinner": (0.30, "19:00")
            }
        
        meals = []
        for meal_type, (ratio, meal_time) in distribution.items():
            meal_protein = target_protein * ratio
            meal_carbs = target_carbs * ratio
            meal_fat = target_fat * ratio
            meal_calories = meal_protein * 4 + meal_carbs * 4 + meal_fat * 9
            
            tips = [
                f"目标：{meal_calories:.0f}卡",
                f"蛋白质{meal_protein:.0f}g，碳水{meal_carbs:.0f}g，脂肪{meal_fat:.0f}g"
            ]
            
            meals.append(MealNutritionTarget(
                meal_type=meal_type,
                meal_time=meal_time,
                target_calories=round(meal_calories, 0),
                target_protein=round(meal_protein, 0),
                target_carbs=round(meal_carbs, 0),
                target_fat=round(meal_fat, 0),
                nutrition_tips=tips
            ))
        
        return DayNutritionPlan(
            day_type="rest",
            meals=meals,
            daily_totals={
                "calories": round(target_calories, 0),
                "protein": round(target_protein, 0),
                "carbs": round(target_carbs, 0),
                "fat": round(target_fat, 0)
            },
            key_nutrients_focus=[
                "保持高蛋白摄入支持恢复",
                "适当减少碳水摄入",
                "增加健康脂肪（坚果、牛油果、橄榄油）"
            ],
            hydration_target="休息日至少2-3升水"
        )

    
    def _generate_food_recommendations(self, input_data: Dict[str, Any]) -> List[FoodRecommendation]:
        """生成食物推荐（基于营养益处）"""
        dietary_preference = input_data.get("dietary_preference", "balanced")
        fitness_goal = input_data.get("fitness_goal", "maintenance")
        
        recommendations = []
        
        # 1. 蛋白质来源
        if dietary_preference in ["vegetarian", "vegan"]:
            protein_foods = ["豆腐", "豆浆", "扁豆", "鹰嘴豆", "藜麦", "坚果", "种子"]
            protein_benefits = [
                "植物蛋白：富含纤维，易消化",
                "豆类：含铁、锌、镁等矿物质",
                "坚果：富含欧米伽3脂肪酸和维生素E"
            ]
        else:
            protein_foods = ["鸡胸肉", "鱼肉（三文鱼、鳕鱼）", "鸡蛋", "瘦牛肉", "希腊酸奶", "豆腐"]
            protein_benefits = [
                "鱼肉：富含欧米伽3（EPA/DHA），抗炎作用",
                "鸡蛋：完整蛋白质，含胆碱和维生素B12",
                "瘦牛肉：富含铁、锌、肌酸，支持力量训练"
            ]
        
        recommendations.append(FoodRecommendation(
            category="优质蛋白质",
            recommended_foods=protein_foods,
            nutrition_benefits=protein_benefits,
            selection_tips=[
                "每餐至少一份蛋白质（手掌大小）",
                "多样化蛋白质来源，获取不同氨基酸",
                "训练后优先快速吸收的蛋白质（乳清、鸡蛋白）"
            ]
        ))
        
        # 2. 碳水化合物来源
        if fitness_goal == "weight_loss":
            carb_foods = ["燕麦", "糙米", "红薯", "全麦面包", "藜麦", "蔬菜"]
            carb_tips = ["优先低GI碳水，稳定血糖", "训练前后可以吃快速碳水"]
        else:
            carb_foods = ["燕麦", "糙米", "白米饭", "红薯", "土豆", "香蕉", "全麦面包"]
            carb_tips = ["训练前后：快速碳水（白米、香蕉）", "其他时间：慢速碳水（燕麦、糙米）"]
        
        recommendations.append(FoodRecommendation(
            category="优质碳水化合物",
            recommended_foods=carb_foods,
            nutrition_benefits=[
                "燕麦：富含β-葡聚糖，降低胆固醇",
                "红薯：富含维生素A、C和钾",
                "香蕉：富含钾和镁，防止肌肉痉挛"
            ],
            selection_tips=carb_tips
        ))
        
        # 3. 健康脂肪来源
        fat_foods = ["牛油果", "坚果（杏仁、核桃）", "橄榄油", "亚麻籽", "奇亚籽", "深海鱼"]
        recommendations.append(FoodRecommendation(
            category="健康脂肪",
            recommended_foods=fat_foods,
            nutrition_benefits=[
                "牛油果：富含单不饱和脂肪酸和钾",
                "核桃：富含欧米伽3（ALA），抗炎",
                "橄榄油：富含多酚，心血管健康",
                "深海鱼：EPA/DHA，减少肌肉酸痛"
            ],
            selection_tips=[
                "每天一小把坚果（30g）",
                "烹饪用橄榄油或椰子油",
                "每周2-3次深海鱼"
            ]
        ))
        
        # 4. 蔬菜水果
        recommendations.append(FoodRecommendation(
            category="蔬菜和水果",
            recommended_foods=[
                "深绿色蔬菜（菠菜、西兰花）",
                "十字花科（西兰花、花椰菜）",
                "浆果类（蓝莓、草莓）",
                "柑橘类（橙子、柚子）"
            ],
            nutrition_benefits=[
                "菠菜：富含铁、镁、叶酸",
                "西兰花：富含维生素C、K和硫化物",
                "蓝莓：富含抗氧化剂，减少运动氧化应激",
                "柑橘：富含维生素C，增强免疫力"
            ],
            selection_tips=[
                "每天至少5种不同颜色的蔬菜水果",
                "训练后吃浆果类，抗氧化",
                "深绿色蔬菜每天至少一份"
            ]
        ))
        
        return recommendations

    
    def _generate_micronutrient_guidance(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成微量元素和维生素指导"""
        fitness_goal = input_data.get("fitness_goal", "maintenance")
        
        guidance = {
            "key_micronutrients": [
                {
                    "name": "锌（Zinc）",
                    "importance": "支持睾酮生成、免疫功能、蛋白质合成",
                    "food_sources": ["牡蛎", "牛肉", "南瓜籽", "腰果"],
                    "daily_target": "男性11mg，女性8mg"
                },
                {
                    "name": "镁（Magnesium）",
                    "importance": "肌肉收缩、能量代谢、防止肌肉痉挛",
                    "food_sources": ["菠菜", "杏仁", "黑巧克力", "香蕉"],
                    "daily_target": "男性400mg，女性310mg"
                },
                {
                    "name": "维生素D",
                    "importance": "钙吸收、骨骼健康、睾酮水平、免疫功能",
                    "food_sources": ["深海鱼", "蛋黄", "强化牛奶", "晒太阳"],
                    "daily_target": "600-800 IU（建议补充剂）"
                },
                {
                    "name": "维生素C",
                    "importance": "抗氧化、胶原蛋白合成、免疫功能",
                    "food_sources": ["柑橘类", "西兰花", "草莓", "青椒"],
                    "daily_target": "75-90mg"
                },
                {
                    "name": "维生素E",
                    "importance": "抗氧化、减少运动氧化应激",
                    "food_sources": ["坚果", "种子", "菠菜", "牛油果"],
                    "daily_target": "15mg"
                },
                {
                    "name": "欧米伽3（Omega-3）",
                    "importance": "抗炎、心血管健康、减少肌肉酸痛",
                    "food_sources": ["深海鱼（三文鱼、沙丁鱼）", "亚麻籽", "核桃", "奇亚籽"],
                    "daily_target": "EPA+DHA 250-500mg"
                },
                {
                    "name": "铁（Iron）",
                    "importance": "氧气运输、能量代谢、防止疲劳",
                    "food_sources": ["红肉", "菠菜", "扁豆", "强化谷物"],
                    "daily_target": "男性8mg，女性18mg"
                }
            ],
            "supplementation_advice": [
                "维生素D：大多数人需要补充（尤其冬季）",
                "欧米伽3：如果不常吃鱼，建议补充鱼油",
                "镁：训练强度大时可考虑补充",
                "多种维生素：作为保险，但优先从食物获取"
            ],
            "timing_tips": [
                "维生素D：随含脂肪的餐食服用",
                "铁：空腹或随维生素C服用，吸收更好",
                "镁：睡前服用，帮助放松和睡眠",
                "欧米伽3：随餐服用，减少鱼腥味"
            ]
        }
        
        return guidance
    
    def _generate_practical_tips(self, input_data: Dict[str, Any]) -> List[str]:
        """生成实用建议"""
        return [
            "🍽️ 不需要精确称重：用手掌估算份量（蛋白质=手掌大小，碳水=拳头大小）",
            "🛒 根据周边食材灵活选择：超市有什么买什么，不必强求特定食物",
            "💰 考虑性价比：鸡蛋、鸡胸肉、豆腐都是便宜的优质蛋白质",
            "👨‍🍳 不会做饭？简单烹饪即可：水煮、清蒸、烤箱都很简单",
            "🥡 外食也可以：选择烤鸡、鱼、沙拉，避免油炸和重口味",
            "📦 Meal Prep：周末准备3-4天的蛋白质和碳水，省时省力",
            "🔄 80/20原则：80%时间吃健康食物，20%时间可以灵活",
            "📱 用App记录：前2周记录饮食，了解食物热量，之后凭感觉即可",
            "💧 水分充足：口渴就喝，尿液淡黄色为佳",
            "😴 睡前避免大餐：睡前2-3小时完成最后一餐"
        ]
    
    def _generate_flexibility_tips(self, input_data: Dict[str, Any]) -> List[str]:
        """生成灵活调整建议"""
        return [
            "📊 每周称重1-2次，根据体重变化调整热量（±200卡）",
            "🎯 如果体重不变：增肌加200卡，减脂减200卡",
            "🍕 偶尔聚餐没关系：第二天恢复正常饮食即可",
            "🏃 训练强度大时：适当增加碳水摄入",
            "😴 睡眠不足时：增加碳水，减少训练强度",
            "🤒 生病时：保持蛋白质，增加维生素C和水分",
            "✈️ 出差旅行：优先保证蛋白质摄入，其他灵活调整",
            "💪 平台期：尝试调整碳水和脂肪比例，保持蛋白质",
            "🔥 减脂停滞：尝试Refeed Day（高碳水日）重启代谢",
            "📈 持续进步：每4-6周重新评估，调整营养方案"
        ]
    
    def _generate_plan_summary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成计划概览"""
        return {
            "approach": "营养指导模式",
            "philosophy": "告诉你吃多少，不强制吃什么",
            "flexibility": "根据周边食材、预算、做饭能力灵活选择",
            "target_nutrition": {
                "calories": input_data["target_calories"],
                "protein": input_data["target_protein_grams"],
                "carbs": input_data["target_carbs_grams"],
                "fat": input_data["target_fat_grams"]
            },
            "meals_per_day": input_data["meals_per_day"],
            "training_days_per_week": input_data.get("training_days_per_week", 0),
            "key_principles": [
                "每餐明确营养目标（多少卡、多少蛋白质）",
                "基于营养益处推荐食物类别",
                "不强制具体食物和份量",
                "考虑实际情况（食材、预算、能力）",
                "80/20原则：大部分时间健康，偶尔灵活"
            ]
        }
