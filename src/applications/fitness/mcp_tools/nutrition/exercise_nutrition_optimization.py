"""
运动营养优化器 MCP工具

优化训练前后营养、推荐补剂时机、优化恢复营养

功能特性：
- 基于训练类型优化训练前后营养摄入
- 推荐补剂时机和剂量（蛋白粉、肌酸、BCAA等）
- 优化恢复营养（睡前、休息日）
- 考虑训练强度、时长、目标调整营养策略

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

class ExerciseNutritionOptimizationInput(BaseModel):
    """运动营养优化器输入"""
    user_id: str = Field(..., description="用户ID")
    
    # 训练信息
    training_type: Literal["strength", "hypertrophy", "endurance", "hiit", "mixed"] = Field(
        ..., description="训练类型"
    )
    training_duration_minutes: int = Field(
        ..., ge=15, le=180, description="训练时长（分钟）"
    )
    training_intensity: Literal["low", "moderate", "high", "very_high"] = Field(
        ..., description="训练强度"
    )
    training_time: Literal["morning", "afternoon", "evening"] = Field(
        ..., description="训练时间段"
    )
    
    # 用户基础信息
    weight_kg: float = Field(..., ge=30, le=300, description="体重（公斤）")
    fitness_goal: Literal["weight_loss", "maintenance", "muscle_gain", "recomp"] = Field(
        ..., description="健身目标"
    )
    
    # 当前营养摄入（来自TDEE计算）
    daily_protein_target: float = Field(..., ge=50, le=500, description="每日蛋白质目标（克）")
    daily_carbs_target: float = Field(..., ge=50, le=800, description="每日碳水目标（克）")
    
    # 补剂使用情况（可选）
    current_supplements: Optional[List[str]] = Field(
        None, description="当前使用的补剂"
    )


# =============================================================================
# 输出类型定义
# =============================================================================

class NutritionWindow(BaseModel):
    """营养窗口"""
    timing: str  # 训练前2小时、训练前30分钟、训练中、训练后30分钟等
    calories: float
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    food_examples: List[str]
    key_principles: List[str]


class SupplementRecommendation(BaseModel):
    """补剂推荐"""
    supplement_name: str
    dosage: str
    timing: str
    benefits: List[str]
    priority: Literal["essential", "recommended", "optional"]
    cost_effectiveness: str


class RecoveryNutrition(BaseModel):
    """恢复营养"""
    timing: str  # 睡前、休息日等
    nutrition_focus: List[str]
    food_recommendations: List[str]
    hydration_tips: List[str]


class ExerciseNutritionOptimizationOutput(BaseModel):
    """运动营养优化器输出"""
    success: bool
    tool_name: str
    user_id: str
    
    # 训练信息概览
    training_summary: Dict[str, Any]
    
    # 训练前营养窗口
    pre_workout_nutrition: List[NutritionWindow]
    
    # 训练中营养
    intra_workout_nutrition: NutritionWindow
    
    # 训练后营养窗口
    post_workout_nutrition: List[NutritionWindow]
    
    # 补剂推荐
    supplement_recommendations: List[SupplementRecommendation]
    
    # 恢复营养
    recovery_nutrition: List[RecoveryNutrition]
    
    # 水分补充策略
    hydration_strategy: Dict[str, Any]
    
    # 个性化建议
    personalized_tips: List[str]
    
    execution_time_ms: float
    confidence_score: float


# =============================================================================
# 运动营养优化器类
# =============================================================================

class ExerciseNutritionOptimization(BaseMCPTool):
    """运动营养优化器"""
    
    def get_name(self) -> str:
        return "exercise_nutrition_optimization"
    
    def get_description(self) -> str:
        return "运动营养优化器 - 优化训练前后营养、推荐补剂时机、优化恢复营养"
    
    def get_category(self) -> str:
        return "nutrition"
    
    def get_input_schema(self) -> type[BaseModel]:
        return ExerciseNutritionOptimizationInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return ExerciseNutritionOptimizationOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    def get_estimated_duration(self) -> float:
        return 600.0
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["user_profile_mcp"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行运动营养优化
        
        流程：
        1. 分析训练类型和强度
        2. 计算训练前营养窗口（2小时前、30分钟前）
        3. 计算训练中营养需求
        4. 计算训练后营养窗口（30分钟内、2小时内）
        5. 推荐补剂和时机
        6. 优化恢复营养（睡前、休息日）
        7. 制定水分补充策略
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: 生成训练概览
            training_summary = self._generate_training_summary(input_data)
            
            # Step 2: 计算训练前营养窗口
            pre_workout_nutrition = self._calculate_pre_workout_nutrition(input_data)
            
            # Step 3: 计算训练中营养
            intra_workout_nutrition = self._calculate_intra_workout_nutrition(input_data)
            
            # Step 4: 计算训练后营养窗口
            post_workout_nutrition = self._calculate_post_workout_nutrition(input_data)
            
            # Step 5: 推荐补剂
            supplement_recommendations = self._recommend_supplements(input_data)
            
            # Step 6: 优化恢复营养
            recovery_nutrition = self._optimize_recovery_nutrition(input_data)
            
            # Step 7: 制定水分补充策略
            hydration_strategy = self._create_hydration_strategy(input_data)
            
            # Step 8: 生成个性化建议
            personalized_tips = self._generate_personalized_tips(input_data)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": "exercise_nutrition_optimization",
                "user_id": input_data["user_id"],
                "training_summary": training_summary,
                "pre_workout_nutrition": [n.model_dump() for n in pre_workout_nutrition],
                "intra_workout_nutrition": intra_workout_nutrition.model_dump(),
                "post_workout_nutrition": [n.model_dump() for n in post_workout_nutrition],
                "supplement_recommendations": [s.model_dump() for s in supplement_recommendations],
                "recovery_nutrition": [r.model_dump() for r in recovery_nutrition],
                "hydration_strategy": hydration_strategy,
                "personalized_tips": personalized_tips,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 93.0
            }
            
            self.logger.info(
                f"✅ 运动营养优化完成: {input_data['training_type']}训练, "
                f"{input_data['training_duration_minutes']}分钟"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 运动营养优化失败: {e}", exc_info=True)
            raise
    
    def _generate_training_summary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成训练概览"""
        training_type_names = {
            "strength": "力量训练",
            "hypertrophy": "肌肥大训练",
            "endurance": "耐力训练",
            "hiit": "高强度间歇训练",
            "mixed": "混合训练"
        }
        
        intensity_names = {
            "low": "低强度",
            "moderate": "中等强度",
            "high": "高强度",
            "very_high": "极高强度"
        }
        
        return {
            "training_type": training_type_names.get(input_data["training_type"], "未知"),
            "duration_minutes": input_data["training_duration_minutes"],
            "intensity": intensity_names.get(input_data["training_intensity"], "未知"),
            "training_time": input_data["training_time"],
            "estimated_calories_burned": self._estimate_calories_burned(input_data),
            "nutrition_priority": self._determine_nutrition_priority(input_data)
        }
    
    def _estimate_calories_burned(self, input_data: Dict[str, Any]) -> float:
        """估算训练消耗的热量"""
        weight_kg = input_data["weight_kg"]
        duration_minutes = input_data["training_duration_minutes"]
        
        # MET值（代谢当量）
        met_values = {
            "strength": {"low": 3.5, "moderate": 5.0, "high": 6.0, "very_high": 8.0},
            "hypertrophy": {"low": 4.0, "moderate": 5.5, "high": 7.0, "very_high": 8.5},
            "endurance": {"low": 5.0, "moderate": 7.0, "high": 9.0, "very_high": 11.0},
            "hiit": {"low": 8.0, "moderate": 10.0, "high": 12.0, "very_high": 15.0},
            "mixed": {"low": 4.5, "moderate": 6.0, "high": 8.0, "very_high": 10.0}
        }
        
        training_type = input_data["training_type"]
        intensity = input_data["training_intensity"]
        met = met_values.get(training_type, {}).get(intensity, 6.0)
        
        # 热量消耗 = MET × 体重(kg) × 时间(小时)
        calories_burned = met * weight_kg * (duration_minutes / 60)
        
        return round(calories_burned, 0)
    
    def _determine_nutrition_priority(self, input_data: Dict[str, Any]) -> str:
        """确定营养优先级"""
        training_type = input_data["training_type"]
        
        if training_type in ["strength", "hypertrophy"]:
            return "蛋白质优先，适量碳水"
        elif training_type == "endurance":
            return "碳水优先，适量蛋白质"
        elif training_type == "hiit":
            return "快速碳水+蛋白质"
        else:  # mixed
            return "均衡营养"
    
    def _calculate_pre_workout_nutrition(
        self,
        input_data: Dict[str, Any]
    ) -> List[NutritionWindow]:
        """计算训练前营养窗口"""
        training_type = input_data["training_type"]
        intensity = input_data["training_intensity"]
        weight_kg = input_data["weight_kg"]
        
        windows = []
        
        # 训练前2-3小时：完整一餐
        if training_type in ["strength", "hypertrophy"]:
            # 力量训练：中等碳水+高蛋白
            carbs_2h = weight_kg * 0.8
            protein_2h = weight_kg * 0.4
            fat_2h = weight_kg * 0.2
        elif training_type == "endurance":
            # 耐力训练：高碳水+适量蛋白
            carbs_2h = weight_kg * 1.2
            protein_2h = weight_kg * 0.3
            fat_2h = weight_kg * 0.15
        else:  # hiit, mixed
            carbs_2h = weight_kg * 1.0
            protein_2h = weight_kg * 0.35
            fat_2h = weight_kg * 0.18
        
        calories_2h = carbs_2h * 4 + protein_2h * 4 + fat_2h * 9
        
        windows.append(NutritionWindow(
            timing="训练前2-3小时",
            calories=round(calories_2h, 0),
            protein_grams=round(protein_2h, 0),
            carbs_grams=round(carbs_2h, 0),
            fat_grams=round(fat_2h, 0),
            food_examples=[
                "鸡胸肉+糙米+蔬菜",
                "燕麦+香蕉+蛋白粉",
                "全麦面包+鸡蛋+牛油果"
            ],
            key_principles=[
                "完整一餐，提供持续能量",
                "避免高脂肪食物，影响消化",
                "选择中低GI碳水，稳定血糖"
            ]
        ))
        
        # 训练前30-60分钟：快速能量
        if intensity in ["high", "very_high"]:
            # 高强度训练需要更多快速碳水
            carbs_30min = weight_kg * 0.5
            protein_30min = weight_kg * 0.15
        else:
            carbs_30min = weight_kg * 0.3
            protein_30min = weight_kg * 0.1
        
        calories_30min = carbs_30min * 4 + protein_30min * 4
        
        windows.append(NutritionWindow(
            timing="训练前30-60分钟",
            calories=round(calories_30min, 0),
            protein_grams=round(protein_30min, 0),
            carbs_grams=round(carbs_30min, 0),
            fat_grams=0,
            food_examples=[
                "香蕉+少量蛋白粉",
                "白面包+蜂蜜",
                "运动饮料+BCAA",
                "能量棒"
            ],
            key_principles=[
                "快速碳水，迅速提升血糖",
                "少量蛋白质，防止分解",
                "避免脂肪和纤维，易消化",
                "如果训练前2小时已进食，可以省略"
            ]
        ))
        
        return windows
    
    def _calculate_intra_workout_nutrition(
        self,
        input_data: Dict[str, Any]
    ) -> NutritionWindow:
        """计算训练中营养"""
        duration = input_data["training_duration_minutes"]
        training_type = input_data["training_type"]
        intensity = input_data["training_intensity"]
        weight_kg = input_data["weight_kg"]
        
        # 训练时长<60分钟：通常不需要训练中补充
        if duration < 60:
            return NutritionWindow(
                timing="训练中（<60分钟）",
                calories=0,
                protein_grams=0,
                carbs_grams=0,
                fat_grams=0,
                food_examples=["清水即可"],
                key_principles=[
                    "训练时长<60分钟，通常不需要额外补充",
                    "保持水分充足即可"
                ]
            )
        
        # 训练时长>60分钟：需要补充碳水
        if training_type == "endurance":
            # 耐力训练：每小时30-60g碳水
            carbs_per_hour = 45
        elif intensity in ["high", "very_high"]:
            # 高强度训练：每小时20-30g碳水
            carbs_per_hour = 25
        else:
            carbs_per_hour = 15
        
        # 计算总碳水（基于训练时长）
        total_carbs = carbs_per_hour * (duration / 60)
        
        # BCAA或EAA（可选）
        bcaa_grams = 5 if intensity in ["high", "very_high"] else 0
        
        return NutritionWindow(
            timing=f"训练中（{duration}分钟）",
            calories=round(total_carbs * 4, 0),
            protein_grams=round(bcaa_grams, 0),
            carbs_grams=round(total_carbs, 0),
            fat_grams=0,
            food_examples=[
                "运动饮料（含电解质）",
                "能量胶",
                "BCAA粉+碳水粉",
                "稀释果汁"
            ],
            key_principles=[
                f"每小时补充{carbs_per_hour}g碳水",
                "保持血糖稳定，延缓疲劳",
                "补充电解质（钠、钾）",
                "每15-20分钟小口补水"
            ]
        )
    
    def _calculate_post_workout_nutrition(
        self,
        input_data: Dict[str, Any]
    ) -> List[NutritionWindow]:
        """计算训练后营养窗口"""
        training_type = input_data["training_type"]
        intensity = input_data["training_intensity"]
        weight_kg = input_data["weight_kg"]
        fitness_goal = input_data["fitness_goal"]
        
        windows = []
        
        # 训练后30分钟内：黄金窗口
        if training_type in ["strength", "hypertrophy"]:
            # 力量训练：高蛋白+快速碳水
            protein_30min = weight_kg * 0.4  # 0.4g/kg
            carbs_30min = weight_kg * 0.8    # 0.8g/kg
        elif training_type == "endurance":
            # 耐力训练：高碳水+适量蛋白
            protein_30min = weight_kg * 0.3
            carbs_30min = weight_kg * 1.2
        else:  # hiit, mixed
            protein_30min = weight_kg * 0.35
            carbs_30min = weight_kg * 1.0
        
        # 减脂目标：适当减少碳水
        if fitness_goal == "weight_loss":
            carbs_30min *= 0.7
        
        calories_30min = protein_30min * 4 + carbs_30min * 4
        
        windows.append(NutritionWindow(
            timing="训练后30分钟内（黄金窗口）",
            calories=round(calories_30min, 0),
            protein_grams=round(protein_30min, 0),
            carbs_grams=round(carbs_30min, 0),
            fat_grams=0,
            food_examples=[
                "乳清蛋白粉+香蕉",
                "鸡胸肉+白米饭",
                "希腊酸奶+蜂蜜+浆果",
                "蛋白粉+运动饮料"
            ],
            key_principles=[
                "快速吸收的蛋白质（乳清、鸡蛋白）",
                "高GI碳水，快速补充糖原",
                "避免脂肪，不影响吸收速度",
                "这是最重要的一餐！"
            ]
        ))
        
        # 训练后2-3小时：完整一餐
        protein_2h = weight_kg * 0.5
        carbs_2h = weight_kg * 1.0
        fat_2h = weight_kg * 0.3
        
        if fitness_goal == "weight_loss":
            carbs_2h *= 0.8
        
        calories_2h = protein_2h * 4 + carbs_2h * 4 + fat_2h * 9
        
        windows.append(NutritionWindow(
            timing="训练后2-3小时",
            calories=round(calories_2h, 0),
            protein_grams=round(protein_2h, 0),
            carbs_grams=round(carbs_2h, 0),
            fat_grams=round(fat_2h, 0),
            food_examples=[
                "牛排+红薯+蔬菜",
                "三文鱼+糙米+西兰花",
                "鸡腿肉+土豆+沙拉"
            ],
            key_principles=[
                "完整均衡的一餐",
                "优质蛋白质+复合碳水+健康脂肪",
                "支持持续恢复和肌肉生长"
            ]
        ))
        
        return windows

    
    def _recommend_supplements(
        self,
        input_data: Dict[str, Any]
    ) -> List[SupplementRecommendation]:
        """推荐补剂"""
        training_type = input_data["training_type"]
        intensity = input_data["training_intensity"]
        fitness_goal = input_data["fitness_goal"]
        current_supplements = input_data.get("current_supplements") or []  # 处理None值
        
        recommendations = []
        
        # 1. 乳清蛋白粉（Essential）
        if "whey_protein" not in current_supplements:
            recommendations.append(SupplementRecommendation(
                supplement_name="乳清蛋白粉",
                dosage="20-30g/次",
                timing="训练后30分钟内，或任何需要快速蛋白质的时候",
                benefits=[
                    "快速吸收，促进肌肉恢复",
                    "方便补充蛋白质",
                    "富含支链氨基酸（BCAA）"
                ],
                priority="essential",
                cost_effectiveness="高（性价比最高的补剂）"
            ))
        
        # 2. 肌酸（Recommended for strength/hypertrophy）
        if training_type in ["strength", "hypertrophy"] and "creatine" not in current_supplements:
            recommendations.append(SupplementRecommendation(
                supplement_name="肌酸（Creatine Monohydrate）",
                dosage="5g/天",
                timing="任何时间（训练后随餐服用更佳）",
                benefits=[
                    "增加力量和爆发力",
                    "促进肌肉生长",
                    "改善高强度训练表现",
                    "研究最充分的补剂之一"
                ],
                priority="recommended",
                cost_effectiveness="极高（便宜且有效）"
            ))
        
        # 3. BCAA/EAA（Optional for fasted training or long sessions）
        if intensity in ["high", "very_high"] and "bcaa" not in current_supplements:
            recommendations.append(SupplementRecommendation(
                supplement_name="BCAA或EAA",
                dosage="5-10g",
                timing="训练前或训练中",
                benefits=[
                    "防止肌肉分解",
                    "减少疲劳",
                    "适合空腹训练或长时间训练"
                ],
                priority="optional",
                cost_effectiveness="中（如果饮食蛋白质充足，可以不用）"
            ))
        
        # 4. 咖啡因（Recommended for energy）
        if intensity in ["high", "very_high"] and "caffeine" not in current_supplements:
            recommendations.append(SupplementRecommendation(
                supplement_name="咖啡因",
                dosage="3-6mg/kg体重（约200-400mg）",
                timing="训练前30-60分钟",
                benefits=[
                    "提升专注力和警觉性",
                    "增加力量和耐力",
                    "减少疲劳感",
                    "促进脂肪燃烧"
                ],
                priority="recommended",
                cost_effectiveness="极高（咖啡或咖啡因片都可以）"
            ))
        
        # 5. 欧米伽3鱼油（Recommended for recovery）
        if "omega3" not in current_supplements:
            recommendations.append(SupplementRecommendation(
                supplement_name="欧米伽3鱼油",
                dosage="EPA+DHA 1-2g/天",
                timing="随餐服用",
                benefits=[
                    "抗炎作用，减少肌肉酸痛",
                    "改善心血管健康",
                    "支持关节健康",
                    "促进恢复"
                ],
                priority="recommended",
                cost_effectiveness="高"
            ))
        
        # 6. 维生素D（Essential for most people）
        if "vitamin_d" not in current_supplements:
            recommendations.append(SupplementRecommendation(
                supplement_name="维生素D3",
                dosage="2000-4000 IU/天",
                timing="随含脂肪的餐食服用",
                benefits=[
                    "支持骨骼健康",
                    "提升睾酮水平",
                    "增强免疫功能",
                    "改善肌肉功能",
                    "大多数人都缺乏"
                ],
                priority="essential",
                cost_effectiveness="极高"
            ))
        
        # 7. 镁（Recommended for sleep and recovery）
        if intensity in ["high", "very_high"] and "magnesium" not in current_supplements:
            recommendations.append(SupplementRecommendation(
                supplement_name="镁（Magnesium）",
                dosage="200-400mg/天",
                timing="睡前服用",
                benefits=[
                    "改善睡眠质量",
                    "防止肌肉痉挛",
                    "支持能量代谢",
                    "减少压力"
                ],
                priority="recommended",
                cost_effectiveness="高"
            ))
        
        # 8. 瓜氨酸或精氨酸（Optional for pump）
        if training_type in ["strength", "hypertrophy"] and intensity in ["high", "very_high"]:
            recommendations.append(SupplementRecommendation(
                supplement_name="瓜氨酸（Citrulline）",
                dosage="6-8g",
                timing="训练前30-60分钟",
                benefits=[
                    "增加一氧化氮产生",
                    "改善血流和肌肉泵感",
                    "减少疲劳",
                    "提升训练表现"
                ],
                priority="optional",
                cost_effectiveness="中"
            ))
        
        # 9. β-丙氨酸（Optional for endurance）
        if training_type in ["endurance", "hiit"] and intensity in ["high", "very_high"]:
            recommendations.append(SupplementRecommendation(
                supplement_name="β-丙氨酸（Beta-Alanine）",
                dosage="3-6g/天",
                timing="分次服用（减少刺痛感）",
                benefits=[
                    "缓冲乳酸堆积",
                    "延缓肌肉疲劳",
                    "提升高强度耐力",
                    "适合HIIT和耐力训练"
                ],
                priority="optional",
                cost_effectiveness="中"
            ))
        
        # 10. 多种维生素（Optional as insurance）
        if "multivitamin" not in current_supplements:
            recommendations.append(SupplementRecommendation(
                supplement_name="多种维生素",
                dosage="按产品说明",
                timing="随餐服用",
                benefits=[
                    "作为营养保险",
                    "填补饮食缺口",
                    "支持整体健康"
                ],
                priority="optional",
                cost_effectiveness="中（优先从食物获取）"
            ))
        
        return recommendations
    
    def _optimize_recovery_nutrition(
        self,
        input_data: Dict[str, Any]
    ) -> List[RecoveryNutrition]:
        """优化恢复营养"""
        weight_kg = input_data["weight_kg"]
        training_type = input_data["training_type"]
        
        recovery_plans = []
        
        # 1. 睡前营养
        protein_before_bed = weight_kg * 0.4  # 0.4g/kg
        
        recovery_plans.append(RecoveryNutrition(
            timing="睡前30-60分钟",
            nutrition_focus=[
                f"缓释蛋白质：{protein_before_bed:.0f}g（酪蛋白或食物蛋白）",
                "避免大量碳水，影响睡眠",
                "可以少量健康脂肪"
            ],
            food_recommendations=[
                "希腊酸奶（富含酪蛋白）",
                "干酪（Cottage Cheese）",
                "酪蛋白蛋白粉",
                "少量坚果",
                "鸡蛋"
            ],
            hydration_tips=[
                "避免睡前大量饮水，影响睡眠",
                "如果口渴，小口补水"
            ]
        ))
        
        # 2. 休息日营养
        recovery_plans.append(RecoveryNutrition(
            timing="休息日全天",
            nutrition_focus=[
                "保持高蛋白摄入（支持恢复）",
                "适当减少碳水（10-20%）",
                "增加健康脂肪和蔬菜",
                "关注抗炎食物"
            ],
            food_recommendations=[
                "深海鱼（三文鱼、沙丁鱼）- 欧米伽3",
                "浆果类（蓝莓、草莓）- 抗氧化",
                "姜黄、生姜 - 抗炎",
                "深绿色蔬菜 - 镁和维生素K",
                "坚果和种子 - 健康脂肪"
            ],
            hydration_tips=[
                "保持充足水分（2-3升）",
                "可以喝绿茶（抗氧化）"
            ]
        ))
        
        # 3. 高强度训练后的额外恢复
        if input_data["training_intensity"] in ["high", "very_high"]:
            recovery_plans.append(RecoveryNutrition(
                timing="高强度训练后24-48小时",
                nutrition_focus=[
                    "增加抗氧化剂摄入",
                    "补充电解质（钠、钾、镁）",
                    "充足蛋白质（每餐30-40g）",
                    "适量碳水补充糖原"
                ],
                food_recommendations=[
                    "樱桃汁（减少肌肉酸痛）",
                    "姜黄拿铁（抗炎）",
                    "香蕉（钾）",
                    "菠菜（镁）",
                    "椰子水（电解质）"
                ],
                hydration_tips=[
                    "增加水分摄入（3-4升）",
                    "监测尿液颜色（淡黄色为佳）"
                ]
            ))
        
        return recovery_plans
    
    def _create_hydration_strategy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """制定水分补充策略"""
        weight_kg = input_data["weight_kg"]
        duration = input_data["training_duration_minutes"]
        intensity = input_data["training_intensity"]
        
        # 基础水分需求：30-40ml/kg体重
        daily_water_ml = weight_kg * 35
        
        # 训练中水分需求：根据时长和强度
        if intensity in ["high", "very_high"]:
            water_per_hour = 800  # ml/小时
        else:
            water_per_hour = 500
        
        training_water_ml = water_per_hour * (duration / 60)
        
        # 总水分需求
        total_water_ml = daily_water_ml + training_water_ml
        
        return {
            "daily_baseline": f"{daily_water_ml:.0f}ml（{daily_water_ml/1000:.1f}升）",
            "training_additional": f"{training_water_ml:.0f}ml",
            "total_daily": f"{total_water_ml:.0f}ml（{total_water_ml/1000:.1f}升）",
            "timing_strategy": {
                "wake_up": "起床后：500ml（补充夜间流失）",
                "pre_workout": "训练前2小时：500ml",
                "pre_workout_30min": "训练前30分钟：200-300ml",
                "during_workout": f"训练中：每15-20分钟{water_per_hour/4:.0f}ml",
                "post_workout": "训练后：立即补充500ml",
                "throughout_day": "全天：小口频繁补水"
            },
            "electrolyte_needs": {
                "when_needed": "训练时长>60分钟，或高强度训练，或大量出汗",
                "sodium": "500-700mg/小时",
                "potassium": "200-300mg/小时",
                "sources": ["运动饮料", "椰子水", "电解质片", "盐+水"]
            },
            "hydration_monitoring": [
                "尿液颜色：淡黄色为佳",
                "体重变化：训练前后体重差异反映水分流失",
                "口渴感：不要等到口渴才喝水",
                "皮肤弹性：捏起皮肤快速恢复表示水分充足"
            ]
        }
    
    def _generate_personalized_tips(self, input_data: Dict[str, Any]) -> List[str]:
        """生成个性化建议"""
        tips = []
        
        training_type = input_data["training_type"]
        intensity = input_data["training_intensity"]
        training_time = input_data["training_time"]
        fitness_goal = input_data["fitness_goal"]
        
        # 基于训练类型的建议
        if training_type in ["strength", "hypertrophy"]:
            tips.extend([
                "💪 力量训练：训练后30分钟内的蛋白质+碳水最关键",
                "🥩 每餐至少30g蛋白质，促进肌肉蛋白合成",
                "⚡ 考虑补充肌酸，研究证明有效提升力量"
            ])
        elif training_type == "endurance":
            tips.extend([
                "🏃 耐力训练：碳水是关键，训练前后充足补充",
                "🍌 训练中每小时30-60g碳水，保持血糖稳定",
                "💧 电解质很重要，尤其是长时间训练"
            ])
        elif training_type == "hiit":
            tips.extend([
                "🔥 HIIT训练：训练后快速碳水+蛋白质，恢复糖原",
                "⚡ 训练前咖啡因可以提升表现",
                "😴 HIIT对神经系统压力大，确保充足睡眠"
            ])
        
        # 基于训练时间的建议
        if training_time == "morning":
            tips.extend([
                "🌅 早晨训练：起床后先喝水，训练前吃点快速碳水",
                "☕ 可以空腹有氧，但力量训练建议先吃点东西"
            ])
        elif training_time == "evening":
            tips.extend([
                "🌙 晚间训练：训练后不要吃太多，影响睡眠",
                "😴 睡前补充酪蛋白，支持夜间恢复"
            ])
        
        # 基于健身目标的建议
        if fitness_goal == "weight_loss":
            tips.extend([
                "🔥 减脂期：保持高蛋白，保护肌肉量",
                "⚖️ 训练后碳水可以适当减少，但不要完全不吃"
            ])
        elif fitness_goal == "muscle_gain":
            tips.extend([
                "💪 增肌期：训练后碳水要充足，促进胰岛素分泌",
                "🍽️ 每天5-6餐，保持持续的营养供应"
            ])
        
        # 基于训练强度的建议
        if intensity in ["high", "very_high"]:
            tips.extend([
                "⚡ 高强度训练：恢复更重要，睡眠至少7-9小时",
                "🧘 考虑增加休息日，避免过度训练",
                "💊 补充欧米伽3和镁，帮助恢复和睡眠"
            ])
        
        # 通用建议
        tips.extend([
            "📊 前2周记录饮食和训练，了解自己的需求",
            "🔄 根据体重和表现调整营养策略",
            "🎯 80/20原则：80%时间严格执行，20%时间灵活",
            "💤 睡眠和营养同样重要，确保7-9小时睡眠",
            "📱 使用App追踪水分摄入，确保充足"
        ])
        
        return tips
