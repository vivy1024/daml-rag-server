"""
营养摄入分析器 MCP工具

分析用户当前饮食摄入，对比目标营养需求，识别营养缺口

功能特性：
- 分析用户当前饮食记录（食物、份量、营养素）
- 对比目标营养需求（基于TDEE计算结果）
- 识别营养缺口（蛋白质、碳水、脂肪、微量营养素）
- 提供改善建议（增加/减少特定食物）
- 评估饮食质量（营养密度、食物多样性）

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

class FoodIntake(BaseModel):
    """单个食物摄入记录"""
    food_name: str = Field(..., description="食物名称")
    portion_size: float = Field(..., ge=0, description="份量（克）")
    meal_type: Optional[Literal["breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"]] = Field(
        None, description="餐次类型"
    )


class NutritionIntakeAnalyzerInput(BaseModel):
    """营养摄入分析器输入"""
    user_id: str = Field(..., description="用户ID")
    
    # 当前饮食记录（允许空列表，工具会返回默认响应）
    daily_food_intake: List[FoodIntake] = Field(
        default_factory=list, description="当天食物摄入记录"
    )
    
    # 目标营养需求（可选，如果不提供则从TDEE计算）
    target_calories: Optional[float] = Field(None, ge=0, description="目标热量（卡）")
    target_protein_grams: Optional[float] = Field(None, ge=0, description="目标蛋白质（克）")
    target_carbs_grams: Optional[float] = Field(None, ge=0, description="目标碳水（克）")
    target_fat_grams: Optional[float] = Field(None, ge=0, description="目标脂肪（克）")
    
    # 分析选项
    include_micronutrients: bool = Field(
        default=False, description="是否包含微量营养素分析"
    )
    fitness_goal: Optional[Literal["fat_loss", "maintenance", "hypertrophy", "recomp"]] = Field(
        None, description="健身目标（用于生成建议）"
    )


# =============================================================================
# 输出类型定义
# =============================================================================


class MacronutrientIntake(BaseModel):
    """宏量营养素摄入"""
    calories: float
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    fiber_grams: float


class MacronutrientTarget(BaseModel):
    """宏量营养素目标"""
    calories: float
    protein_grams: float
    carbs_grams: float
    fat_grams: float


class MacronutrientGap(BaseModel):
    """宏量营养素缺口"""
    calories_gap: float
    calories_gap_percentage: float
    protein_gap: float
    protein_gap_percentage: float
    carbs_gap: float
    carbs_gap_percentage: float
    fat_gap: float
    fat_gap_percentage: float
    
    overall_status: Literal["deficit", "balanced", "surplus"]
    reasoning: str


class MicronutrientAnalysis(BaseModel):
    """微量营养素分析"""
    vitamin_a_mcg: float
    vitamin_c_mg: float
    vitamin_d_mcg: float
    calcium_mg: float
    iron_mg: float
    zinc_mg: float
    
    deficiencies: List[str]
    recommendations: List[str]


class DietQualityScore(BaseModel):
    """饮食质量评分"""
    overall_score: float  # 0-100
    nutrient_density_score: float  # 营养密度
    food_variety_score: float  # 食物多样性
    meal_timing_score: float  # 进餐时机
    
    strengths: List[str]
    weaknesses: List[str]


class ImprovementSuggestion(BaseModel):
    """改善建议"""
    category: Literal["increase", "decrease", "replace", "timing"]
    priority: Literal["high", "medium", "low"]
    suggestion: str
    reasoning: str
    example_foods: List[str]


class NutritionIntakeAnalyzerOutput(BaseModel):
    """营养摄入分析器输出"""
    success: bool
    tool_name: str
    user_id: str
    
    # 当前摄入
    current_intake: MacronutrientIntake
    
    # 目标需求
    target_needs: MacronutrientTarget
    
    # 营养缺口
    nutrient_gap: MacronutrientGap
    
    # 微量营养素分析（可选）
    micronutrient_analysis: Optional[MicronutrientAnalysis]
    
    # 饮食质量评分
    diet_quality_score: DietQualityScore
    
    # 改善建议
    improvement_suggestions: List[ImprovementSuggestion]
    
    # 食物摄入详情
    food_intake_details: List[Dict[str, Any]]
    
    execution_time_ms: float
    confidence_score: float


# =============================================================================
# 营养摄入分析器类
# =============================================================================


class NutritionIntakeAnalyzer(BaseMCPTool):
    """营养摄入分析器"""
    
    def get_name(self) -> str:
        return "nutrition_intake_analyzer"
    
    def get_description(self) -> str:
        return "营养摄入分析器 - 分析当前饮食，对比目标需求，识别营养缺口"
    
    def get_category(self) -> str:
        return "nutrition"
    
    def get_input_schema(self) -> type[BaseModel]:
        return NutritionIntakeAnalyzerInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return NutritionIntakeAnalyzerOutput
    
    def get_complexity(self) -> str:
        return "medium"
    
    def get_estimated_duration(self) -> float:
        return 1000.0
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["neo4j", "user_profile_mcp"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行营养摄入分析
        
        流程：
        1. 查询食物营养数据（Neo4j）
        2. 计算当前摄入（总热量、三大营养素）
        3. 获取目标营养需求（输入或TDEE计算）
        4. 计算营养缺口
        5. 分析微量营养素（可选）
        6. 评估饮食质量
        7. 生成改善建议
        """
        import time
        start_time = time.time()
        
        try:
            # 处理空列表情况 - 返回默认响应
            if not input_data.get("daily_food_intake"):
                execution_time_ms = (time.time() - start_time) * 1000
                
                # 获取目标营养需求
                target_needs = await self._get_target_needs(input_data)
                
                return {
                    "success": True,
                    "tool_name": "nutrition_intake_analyzer",
                    "user_id": input_data["user_id"],
                    "current_intake": MacronutrientIntake(
                        calories=0, protein_grams=0, carbs_grams=0, fat_grams=0, fiber_grams=0
                    ).model_dump(),
                    "target_needs": target_needs.model_dump(),
                    "nutrient_gap": MacronutrientGap(
                        calories_gap=-target_needs.calories,
                        calories_gap_percentage=-100.0,
                        protein_gap=-target_needs.protein_grams,
                        protein_gap_percentage=-100.0,
                        carbs_gap=-target_needs.carbs_grams,
                        carbs_gap_percentage=-100.0,
                        fat_gap=-target_needs.fat_grams,
                        fat_gap_percentage=-100.0,
                        overall_status="deficit",
                        reasoning="未提供饮食记录，无法分析当前摄入"
                    ).model_dump(),
                    "micronutrient_analysis": None,
                    "diet_quality_score": DietQualityScore(
                        overall_score=0,
                        nutrient_density_score=0,
                        food_variety_score=0,
                        meal_timing_score=0,
                        strengths=[],
                        weaknesses=["未提供饮食记录"]
                    ).model_dump(),
                    "improvement_suggestions": [
                        ImprovementSuggestion(
                            category="increase",
                            priority="high",
                            suggestion="请记录您的饮食摄入以获得准确分析",
                            reasoning="没有饮食记录无法进行营养分析",
                            example_foods=[]
                        ).model_dump()
                    ],
                    "food_intake_details": [],
                    "execution_time_ms": execution_time_ms,
                    "confidence_score": 0.0
                }
            
            # Step 1: 查询食物营养数据
            food_intake_details = await self._query_food_nutrition_data(
                input_data["daily_food_intake"]
            )
            
            # Step 2: 计算当前摄入
            current_intake = self._calculate_current_intake(food_intake_details)
            
            # Step 3: 获取目标营养需求
            target_needs = await self._get_target_needs(input_data)
            
            # Step 4: 计算营养缺口
            nutrient_gap = self._calculate_nutrient_gap(
                current_intake,
                target_needs
            )
            
            # Step 5: 分析微量营养素（可选）
            micronutrient_analysis = None
            if input_data.get("include_micronutrients", False):
                micronutrient_analysis = self._analyze_micronutrients(
                    food_intake_details
                )
            
            # Step 6: 评估饮食质量
            diet_quality_score = self._evaluate_diet_quality(
                food_intake_details,
                current_intake,
                target_needs,
                input_data["daily_food_intake"]
            )
            
            # Step 7: 生成改善建议
            improvement_suggestions = self._generate_improvement_suggestions(
                nutrient_gap,
                diet_quality_score,
                input_data.get("fitness_goal"),
                food_intake_details
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": "nutrition_intake_analyzer",
                "user_id": input_data["user_id"],
                "current_intake": current_intake.model_dump(),
                "target_needs": target_needs.model_dump(),
                "nutrient_gap": nutrient_gap.model_dump(),
                "micronutrient_analysis": micronutrient_analysis.model_dump() if micronutrient_analysis else None,
                "diet_quality_score": diet_quality_score.model_dump(),
                "improvement_suggestions": [s.model_dump() for s in improvement_suggestions],
                "food_intake_details": food_intake_details,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 88.0
            }
            
            self.logger.info(
                f"✅ 营养摄入分析完成: 当前{current_intake.calories:.0f}卡, "
                f"目标{target_needs.calories:.0f}卡, "
                f"缺口{nutrient_gap.calories_gap:+.0f}卡"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 营养摄入分析失败: {e}", exc_info=True)
            raise

    
    async def _query_food_nutrition_data(
        self,
        food_intake_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        查询食物营养数据
        
        从Neo4j查询每个食物的营养信息
        """
        food_details = []
        
        for intake in food_intake_list:
            food_name = intake["food_name"]
            portion_size = intake["portion_size"]
            
            # 查询Neo4j获取食物营养数据
            query = """
            MATCH (f:Food {name: $food_name})-[r:CONTAINS_NUTRIENT]->(n:Nutrient)
            RETURN f.name as food_name,
                   f.category as category,
                   f.edible_part as edible_part,
                   n.name as nutrient_name,
                   r.amount as amount,
                   n.unit as unit
            """
            
            try:
                result = await self.neo4j_client.execute_query(
                    query,
                    {"food_name": food_name}
                )
                
                if not result:
                    self.logger.warning(f"⚠️ 未找到食物: {food_name}")
                    continue
                
                # 解析营养数据
                nutrients = {}
                food_category = None
                edible_part = 100  # 默认可食部分100%
                
                for record in result:
                    if food_category is None:
                        food_category = record.get("category", "未知")
                        edible_part_value = record.get("edible_part")
                        # 处理None值，默认为100
                        edible_part = edible_part_value if edible_part_value is not None else 100
                    
                    nutrient_name = record["nutrient_name"]
                    amount = record["amount"]
                    unit = record.get("unit", "")
                    
                    nutrients[nutrient_name] = {
                        "amount": amount,
                        "unit": unit
                    }
                
                # 计算实际摄入（考虑份量和可食部分）
                actual_portion = portion_size * (edible_part / 100)
                scaling_factor = actual_portion / 100  # 营养数据通常是每100g
                
                food_detail = {
                    "food_name": food_name,
                    "portion_size": portion_size,
                    "actual_portion": actual_portion,
                    "category": food_category,
                    "meal_type": intake.get("meal_type"),
                    "nutrients": nutrients,
                    "scaling_factor": scaling_factor,
                    # 提取关键营养素
                    "calories": nutrients.get("能量", {}).get("amount", 0) * scaling_factor,
                    "protein": nutrients.get("蛋白质", {}).get("amount", 0) * scaling_factor,
                    "carbs": nutrients.get("碳水化合物", {}).get("amount", 0) * scaling_factor,
                    "fat": nutrients.get("脂肪", {}).get("amount", 0) * scaling_factor,
                    "fiber": nutrients.get("膳食纤维", {}).get("amount", 0) * scaling_factor
                }
                
                food_details.append(food_detail)
                
            except Exception as e:
                self.logger.error(f"❌ 查询食物 {food_name} 失败: {e}")
                continue
        
        return food_details
    
    def _calculate_current_intake(
        self,
        food_intake_details: List[Dict[str, Any]]
    ) -> MacronutrientIntake:
        """计算当前摄入"""
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_fiber = 0.0
        
        for food in food_intake_details:
            total_calories += food.get("calories", 0)
            total_protein += food.get("protein", 0)
            total_carbs += food.get("carbs", 0)
            total_fat += food.get("fat", 0)
            total_fiber += food.get("fiber", 0)
        
        return MacronutrientIntake(
            calories=round(total_calories, 1),
            protein_grams=round(total_protein, 1),
            carbs_grams=round(total_carbs, 1),
            fat_grams=round(total_fat, 1),
            fiber_grams=round(total_fiber, 1)
        )

    
    async def _get_target_needs(
        self,
        input_data: Dict[str, Any]
    ) -> MacronutrientTarget:
        """
        获取目标营养需求
        
        优先使用输入数据，否则从用户档案或TDEE计算获取
        """
        # 如果输入中提供了目标值，直接使用
        if input_data.get("target_calories"):
            return MacronutrientTarget(
                calories=input_data["target_calories"],
                protein_grams=input_data.get("target_protein_grams", 0),
                carbs_grams=input_data.get("target_carbs_grams", 0),
                fat_grams=input_data.get("target_fat_grams", 0)
            )
        
        # 否则，使用默认值（基于一般建议）
        # TODO: 可以调用TDEE计算器获取更准确的目标
        user_id = input_data["user_id"]
        self.logger.warning(
            f"⚠️ 未提供目标营养需求，使用默认值（用户: {user_id}）"
        )
        
        # 默认目标（假设70kg成年人，中等活动水平）
        return MacronutrientTarget(
            calories=2200.0,
            protein_grams=150.0,  # ~2g/kg
            carbs_grams=250.0,
            fat_grams=70.0
        )
    
    def _calculate_nutrient_gap(
        self,
        current_intake: MacronutrientIntake,
        target_needs: MacronutrientTarget
    ) -> MacronutrientGap:
        """计算营养缺口"""
        # 计算绝对缺口
        calories_gap = current_intake.calories - target_needs.calories
        protein_gap = current_intake.protein_grams - target_needs.protein_grams
        carbs_gap = current_intake.carbs_grams - target_needs.carbs_grams
        fat_gap = current_intake.fat_grams - target_needs.fat_grams
        
        # 计算百分比缺口
        calories_gap_pct = (calories_gap / target_needs.calories * 100) if target_needs.calories > 0 else 0
        protein_gap_pct = (protein_gap / target_needs.protein_grams * 100) if target_needs.protein_grams > 0 else 0
        carbs_gap_pct = (carbs_gap / target_needs.carbs_grams * 100) if target_needs.carbs_grams > 0 else 0
        fat_gap_pct = (fat_gap / target_needs.fat_grams * 100) if target_needs.fat_grams > 0 else 0
        
        # 判断整体状态
        if abs(calories_gap_pct) <= 5:
            overall_status = "balanced"
            status_desc = "热量摄入基本平衡"
        elif calories_gap_pct < -5:
            overall_status = "deficit"
            status_desc = f"热量摄入不足{abs(calories_gap):.0f}卡（{abs(calories_gap_pct):.1f}%）"
        else:
            overall_status = "surplus"
            status_desc = f"热量摄入过剩{calories_gap:.0f}卡（{calories_gap_pct:.1f}%）"
        
        # 生成推理说明
        reasoning_parts = [status_desc]
        
        if abs(protein_gap_pct) > 10:
            if protein_gap < 0:
                reasoning_parts.append(f"蛋白质不足{abs(protein_gap):.0f}g")
            else:
                reasoning_parts.append(f"蛋白质过量{protein_gap:.0f}g")
        
        if abs(carbs_gap_pct) > 10:
            if carbs_gap < 0:
                reasoning_parts.append(f"碳水不足{abs(carbs_gap):.0f}g")
            else:
                reasoning_parts.append(f"碳水过量{carbs_gap:.0f}g")
        
        if abs(fat_gap_pct) > 10:
            if fat_gap < 0:
                reasoning_parts.append(f"脂肪不足{abs(fat_gap):.0f}g")
            else:
                reasoning_parts.append(f"脂肪过量{fat_gap:.0f}g")
        
        reasoning = "；".join(reasoning_parts)
        
        return MacronutrientGap(
            calories_gap=round(calories_gap, 1),
            calories_gap_percentage=round(calories_gap_pct, 1),
            protein_gap=round(protein_gap, 1),
            protein_gap_percentage=round(protein_gap_pct, 1),
            carbs_gap=round(carbs_gap, 1),
            carbs_gap_percentage=round(carbs_gap_pct, 1),
            fat_gap=round(fat_gap, 1),
            fat_gap_percentage=round(fat_gap_pct, 1),
            overall_status=overall_status,
            reasoning=reasoning
        )

    
    def _analyze_micronutrients(
        self,
        food_intake_details: List[Dict[str, Any]]
    ) -> MicronutrientAnalysis:
        """分析微量营养素"""
        # 汇总微量营养素
        total_vitamin_a = 0.0
        total_vitamin_c = 0.0
        total_vitamin_d = 0.0
        total_calcium = 0.0
        total_iron = 0.0
        total_zinc = 0.0
        
        for food in food_intake_details:
            nutrients = food.get("nutrients", {})
            scaling_factor = food.get("scaling_factor", 1.0)
            
            total_vitamin_a += nutrients.get("维生素A", {}).get("amount", 0) * scaling_factor
            total_vitamin_c += nutrients.get("维生素C", {}).get("amount", 0) * scaling_factor
            total_vitamin_d += nutrients.get("维生素D", {}).get("amount", 0) * scaling_factor
            total_calcium += nutrients.get("钙", {}).get("amount", 0) * scaling_factor
            total_iron += nutrients.get("铁", {}).get("amount", 0) * scaling_factor
            total_zinc += nutrients.get("锌", {}).get("amount", 0) * scaling_factor
        
        # 推荐摄入量（RDA）
        rda = {
            "vitamin_a": 800,  # mcg
            "vitamin_c": 100,  # mg
            "vitamin_d": 15,   # mcg
            "calcium": 1000,   # mg
            "iron": 15,        # mg
            "zinc": 12         # mg
        }
        
        # 识别缺乏
        deficiencies = []
        recommendations = []
        
        if total_vitamin_a < rda["vitamin_a"] * 0.7:
            deficiencies.append("维生素A")
            recommendations.append("增加胡萝卜、南瓜、菠菜等富含维生素A的食物")
        
        if total_vitamin_c < rda["vitamin_c"] * 0.7:
            deficiencies.append("维生素C")
            recommendations.append("增加柑橘类水果、西红柿、青椒等富含维生素C的食物")
        
        if total_vitamin_d < rda["vitamin_d"] * 0.7:
            deficiencies.append("维生素D")
            recommendations.append("增加鱼类、蛋黄摄入，或考虑补充剂；多晒太阳")
        
        if total_calcium < rda["calcium"] * 0.7:
            deficiencies.append("钙")
            recommendations.append("增加奶制品、豆制品、绿叶蔬菜摄入")
        
        if total_iron < rda["iron"] * 0.7:
            deficiencies.append("铁")
            recommendations.append("增加红肉、动物肝脏、豆类摄入")
        
        if total_zinc < rda["zinc"] * 0.7:
            deficiencies.append("锌")
            recommendations.append("增加海鲜、坚果、全谷物摄入")
        
        if not deficiencies:
            recommendations.append("微量营养素摄入充足，继续保持")
        
        return MicronutrientAnalysis(
            vitamin_a_mcg=round(total_vitamin_a, 1),
            vitamin_c_mg=round(total_vitamin_c, 1),
            vitamin_d_mcg=round(total_vitamin_d, 1),
            calcium_mg=round(total_calcium, 1),
            iron_mg=round(total_iron, 1),
            zinc_mg=round(total_zinc, 1),
            deficiencies=deficiencies,
            recommendations=recommendations
        )
    
    def _evaluate_diet_quality(
        self,
        food_intake_details: List[Dict[str, Any]],
        current_intake: MacronutrientIntake,
        target_needs: MacronutrientTarget,
        food_intake_list: List[Dict[str, Any]]
    ) -> DietQualityScore:
        """评估饮食质量"""
        # 1. 营养密度评分（0-100）
        # 基于蛋白质和纤维含量相对于热量的比例
        if current_intake.calories > 0:
            protein_density = (current_intake.protein_grams * 4 / current_intake.calories) * 100
            fiber_density = current_intake.fiber_grams / (current_intake.calories / 1000)
            
            # 蛋白质密度评分（目标15-30%）
            if 15 <= protein_density <= 30:
                protein_score = 100
            elif protein_density < 15:
                protein_score = max(0, protein_density / 15 * 100)
            else:
                protein_score = max(0, 100 - (protein_density - 30) * 2)
            
            # 纤维密度评分（目标>14g/1000卡）
            fiber_score = min(100, fiber_density / 14 * 100)
            
            nutrient_density_score = (protein_score + fiber_score) / 2
        else:
            nutrient_density_score = 0
        
        # 2. 食物多样性评分（0-100）
        unique_foods = len(set(f["food_name"] for f in food_intake_details))
        food_categories = set(f.get("category", "未知") for f in food_intake_details)
        
        # 理想：每天至少15种不同食物，5个食物类别
        variety_score = min(100, (unique_foods / 15 * 50) + (len(food_categories) / 5 * 50))
        
        # 3. 进餐时机评分（0-100）
        meal_types = [f.get("meal_type") for f in food_intake_list if f.get("meal_type")]
        has_breakfast = "breakfast" in meal_types
        has_lunch = "lunch" in meal_types
        has_dinner = "dinner" in meal_types
        meal_count = len([m for m in meal_types if m in ["breakfast", "lunch", "dinner", "snack"]])
        
        timing_score = 0
        if has_breakfast:
            timing_score += 30
        if has_lunch:
            timing_score += 30
        if has_dinner:
            timing_score += 30
        if meal_count >= 4:
            timing_score += 10  # 奖励多餐
        
        # 4. 综合评分
        overall_score = (
            nutrient_density_score * 0.4 +
            variety_score * 0.3 +
            timing_score * 0.3
        )
        
        # 5. 识别优势和劣势
        strengths = []
        weaknesses = []
        
        if nutrient_density_score >= 70:
            strengths.append("营养密度高，食物质量好")
        elif nutrient_density_score < 50:
            weaknesses.append("营养密度偏低，建议增加高蛋白、高纤维食物")
        
        if variety_score >= 70:
            strengths.append("食物种类丰富，营养均衡")
        elif variety_score < 50:
            weaknesses.append("食物种类单一，建议增加食物多样性")
        
        if timing_score >= 70:
            strengths.append("进餐时机合理，有利于代谢")
        elif timing_score < 50:
            weaknesses.append("进餐时机不规律，建议规律进餐")
        
        if current_intake.fiber_grams >= 25:
            strengths.append("膳食纤维摄入充足")
        elif current_intake.fiber_grams < 15:
            weaknesses.append("膳食纤维不足，建议增加蔬菜、水果、全谷物")
        
        return DietQualityScore(
            overall_score=round(overall_score, 1),
            nutrient_density_score=round(nutrient_density_score, 1),
            food_variety_score=round(variety_score, 1),
            meal_timing_score=round(timing_score, 1),
            strengths=strengths,
            weaknesses=weaknesses
        )

    
    def _generate_improvement_suggestions(
        self,
        nutrient_gap: MacronutrientGap,
        diet_quality_score: DietQualityScore,
        fitness_goal: Optional[str],
        food_intake_details: List[Dict[str, Any]]
    ) -> List[ImprovementSuggestion]:
        """生成改善建议"""
        suggestions = []
        
        # 1. 基于营养缺口的建议
        # 蛋白质缺口
        if nutrient_gap.protein_gap < -10:
            suggestions.append(ImprovementSuggestion(
                category="increase",
                priority="high",
                suggestion=f"增加蛋白质摄入{abs(nutrient_gap.protein_gap):.0f}克",
                reasoning="当前蛋白质摄入不足，影响肌肉恢复和生长",
                example_foods=["鸡胸肉", "鱼肉", "鸡蛋", "希腊酸奶", "豆腐", "蛋白粉"]
            ))
        elif nutrient_gap.protein_gap > 20:
            suggestions.append(ImprovementSuggestion(
                category="decrease",
                priority="low",
                suggestion=f"适当减少蛋白质摄入{nutrient_gap.protein_gap:.0f}克",
                reasoning="蛋白质摄入过量，可能增加肾脏负担",
                example_foods=[]
            ))
        
        # 碳水化合物缺口
        if nutrient_gap.carbs_gap < -20:
            suggestions.append(ImprovementSuggestion(
                category="increase",
                priority="medium",
                suggestion=f"增加碳水化合物摄入{abs(nutrient_gap.carbs_gap):.0f}克",
                reasoning="碳水不足可能影响训练表现和恢复",
                example_foods=["燕麦", "糙米", "红薯", "全麦面包", "香蕉", "土豆"]
            ))
        elif nutrient_gap.carbs_gap > 30:
            suggestions.append(ImprovementSuggestion(
                category="decrease",
                priority="medium",
                suggestion=f"适当减少碳水化合物摄入{nutrient_gap.carbs_gap:.0f}克",
                reasoning="碳水过量可能导致脂肪堆积",
                example_foods=[]
            ))
        
        # 脂肪缺口
        if nutrient_gap.fat_gap < -10:
            suggestions.append(ImprovementSuggestion(
                category="increase",
                priority="medium",
                suggestion=f"增加健康脂肪摄入{abs(nutrient_gap.fat_gap):.0f}克",
                reasoning="脂肪不足影响激素合成和维生素吸收",
                example_foods=["牛油果", "坚果", "橄榄油", "三文鱼", "亚麻籽"]
            ))
        elif nutrient_gap.fat_gap > 15:
            suggestions.append(ImprovementSuggestion(
                category="decrease",
                priority="medium",
                suggestion=f"适当减少脂肪摄入{nutrient_gap.fat_gap:.0f}克",
                reasoning="脂肪摄入过量，热量密度高",
                example_foods=[]
            ))
        
        # 2. 基于饮食质量的建议
        if diet_quality_score.food_variety_score < 60:
            suggestions.append(ImprovementSuggestion(
                category="increase",
                priority="high",
                suggestion="增加食物种类多样性",
                reasoning="食物种类单一，可能导致营养不均衡",
                example_foods=["不同颜色的蔬菜", "多种水果", "不同蛋白质来源", "全谷物"]
            ))
        
        if diet_quality_score.nutrient_density_score < 60:
            suggestions.append(ImprovementSuggestion(
                category="replace",
                priority="high",
                suggestion="用营养密度高的食物替代加工食品",
                reasoning="提高食物质量，获得更多营养素",
                example_foods=["用全麦面包替代白面包", "用糙米替代白米", "用新鲜水果替代果汁"]
            ))
        
        # 3. 基于健身目标的建议
        if fitness_goal == "hypertrophy":
            if nutrient_gap.overall_status == "deficit":
                suggestions.append(ImprovementSuggestion(
                    category="increase",
                    priority="high",
                    suggestion="增加总热量摄入以支持增肌",
                    reasoning="增肌需要热量盈余",
                    example_foods=["增加餐次", "添加健康零食", "增加碳水和蛋白质"]
                ))
        elif fitness_goal == "fat_loss":
            if nutrient_gap.overall_status == "surplus":
                suggestions.append(ImprovementSuggestion(
                    category="decrease",
                    priority="high",
                    suggestion="适当减少总热量摄入以支持减脂",
                    reasoning="减脂需要热量赤字",
                    example_foods=[]
                ))
            # 减脂期间保持高蛋白
            if nutrient_gap.protein_gap_percentage < -5:
                suggestions.append(ImprovementSuggestion(
                    category="increase",
                    priority="high",
                    suggestion="减脂期间保持高蛋白摄入",
                    reasoning="高蛋白有助于保护肌肉量，增加饱腹感",
                    example_foods=["瘦肉", "鱼", "蛋白粉", "低脂奶制品"]
                ))
        
        # 4. 进餐时机建议
        if diet_quality_score.meal_timing_score < 60:
            suggestions.append(ImprovementSuggestion(
                category="timing",
                priority="medium",
                suggestion="优化进餐时机和频率",
                reasoning="规律进餐有助于稳定血糖和代谢",
                example_foods=["早餐必吃", "每3-4小时进餐一次", "训练前后及时补充"]
            ))
        
        # 5. 膳食纤维建议
        current_fiber = sum(f.get("fiber", 0) for f in food_intake_details)
        if current_fiber < 20:
            suggestions.append(ImprovementSuggestion(
                category="increase",
                priority="medium",
                suggestion=f"增加膳食纤维摄入（当前{current_fiber:.0f}g，建议25-30g）",
                reasoning="膳食纤维有助于消化健康和饱腹感",
                example_foods=["蔬菜", "水果", "全谷物", "豆类", "坚果"]
            ))
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda x: priority_order[x.priority])
        
        return suggestions
