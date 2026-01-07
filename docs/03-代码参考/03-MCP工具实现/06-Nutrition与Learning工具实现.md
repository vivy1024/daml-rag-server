# Nutrition与Learning工具实现

**版本**: v2.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本文档详细说明Nutrition分类下的4个工具和Learning分类下的1个工具实现。

**代码路径**: 
- Nutrition: `daml-rag-server/src/applications/fitness/mcp_tools/nutrition/`
- Learning: `daml-rag-server/src/applications/fitness/mcp_tools/`

---

## Nutrition工具（4个）

### 1. tdee_calculator - TDEE计算器

**功能说明**: 计算每日总能量消耗（TDEE）和营养素需求

**代码路径**: `nutrition/tdee_calculator.py`

**优先级**: P0核心工具

#### 输入Schema

```python
class TDEECalculatorInput(BaseModel):
    user_id: str = Field(..., description="用户ID")
    age: int = Field(..., description="年龄", ge=10, le=100)
    gender: str = Field(..., description="性别", pattern="^(male|female)$")
    weight_kg: float = Field(..., description="体重(kg)", gt=0)
    height_cm: float = Field(..., description="身高(cm)", gt=0)
    activity_level: str = Field(..., description="活动水平")
    training_goal: Optional[str] = Field(None, description="训练目标")
```

#### TDEE计算公式

```python
def _calculate_bmr(
    self,
    age: int,
    gender: str,
    weight_kg: float,
    height_cm: float
) -> float:
    """计算基础代谢率（BMR）- Mifflin-St Jeor公式"""
    if gender == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    
    return bmr

def _calculate_tdee(
    self,
    bmr: float,
    activity_level: str
) -> float:
    """计算TDEE"""
    activity_multipliers = {
        "sedentary": 1.2,        # 久坐
        "lightly_active": 1.375, # 轻度活动
        "moderately_active": 1.55, # 中度活动
        "very_active": 1.725,    # 高度活动
        "extremely_active": 1.9  # 极度活动
    }
    
    multiplier = activity_multipliers.get(activity_level, 1.55)
    return bmr * multiplier

def _calculate_macros(
    self,
    tdee: float,
    training_goal: str,
    weight_kg: float
) -> Dict[str, float]:
    """计算营养素需求"""
    if training_goal == "muscle_gain":
        # 增肌：蛋白质2g/kg，脂肪25%，剩余碳水
        protein_g = weight_kg * 2.0
        fat_g = (tdee * 0.25) / 9
        carbs_g = (tdee - protein_g * 4 - fat_g * 9) / 4
    elif training_goal == "fat_loss":
        # 减脂：蛋白质2.2g/kg，脂肪20%，剩余碳水
        protein_g = weight_kg * 2.2
        fat_g = (tdee * 0.20) / 9
        carbs_g = (tdee - protein_g * 4 - fat_g * 9) / 4
    else:
        # 维持：蛋白质1.6g/kg，脂肪30%，剩余碳水
        protein_g = weight_kg * 1.6
        fat_g = (tdee * 0.30) / 9
        carbs_g = (tdee - protein_g * 4 - fat_g * 9) / 4
    
    return {
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carbs_g, 1),
        "fat_g": round(fat_g, 1)
    }
```

---

### 2. nutrition_intake_analyzer - 营养摄入分析器

**功能说明**: 分析用户饮食记录，评估营养摄入是否达标

**代码路径**: `nutrition/nutrition_intake_analyzer.py`

**优先级**: P1建议工具

#### 营养分析

```python
def _analyze_intake(
    self,
    daily_intake: Dict[str, float],
    target_intake: Dict[str, float]
) -> Dict[str, Any]:
    """分析营养摄入"""
    analysis = {}
    
    for nutrient in ["protein_g", "carbs_g", "fat_g", "calories"]:
        actual = daily_intake.get(nutrient, 0)
        target = target_intake.get(nutrient, 0)
        
        if target > 0:
            percentage = (actual / target) * 100
            deviation = actual - target
            
            if percentage >= 90 and percentage <= 110:
                status = "optimal"
            elif percentage >= 80 and percentage <= 120:
                status = "acceptable"
            elif percentage < 80:
                status = "insufficient"
            else:
                status = "excessive"
            
            analysis[nutrient] = {
                "actual": actual,
                "target": target,
                "percentage": round(percentage, 1),
                "deviation": round(deviation, 1),
                "status": status
            }
    
    return analysis
```

---

### 3. meal_plan_designer - 膳食计划设计器

**功能说明**: 基于TDEE和营养目标设计每日膳食计划

**代码路径**: `nutrition/meal_plan_designer.py`

**优先级**: P1建议工具

#### 膳食分配

```python
def _distribute_meals(
    self,
    daily_macros: Dict[str, float],
    meals_per_day: int,
    training_time: Optional[str] = None
) -> List[Dict[str, Any]]:
    """分配每餐营养素"""
    meals = []
    
    # 基础分配比例
    if meals_per_day == 3:
        ratios = [0.30, 0.40, 0.30]  # 早中晚
    elif meals_per_day == 4:
        ratios = [0.25, 0.30, 0.25, 0.20]  # 早中晚加餐
    else:
        ratios = [1.0 / meals_per_day] * meals_per_day
    
    # 如果有训练时间，调整训练前后餐比例
    if training_time:
        ratios = self._adjust_for_training(ratios, training_time)
    
    for i, ratio in enumerate(ratios):
        meal = {
            "meal_number": i + 1,
            "protein_g": round(daily_macros["protein_g"] * ratio, 1),
            "carbs_g": round(daily_macros["carbs_g"] * ratio, 1),
            "fat_g": round(daily_macros["fat_g"] * ratio, 1)
        }
        meals.append(meal)
    
    return meals
```

---

### 4. exercise_nutrition_optimization - 运动营养优化

**功能说明**: 优化训练前后的营养摄入时机和比例

**代码路径**: `nutrition/exercise_nutrition_optimization.py`

**优先级**: P1建议工具

#### 训练窗口营养

```python
def _calculate_pre_workout_nutrition(
    self,
    training_duration_min: int,
    training_intensity: str
) -> Dict[str, Any]:
    """计算训练前营养"""
    if training_intensity == "high":
        carbs_g = 30 + (training_duration_min / 60) * 20
        protein_g = 20
    elif training_intensity == "moderate":
        carbs_g = 20 + (training_duration_min / 60) * 15
        protein_g = 15
    else:
        carbs_g = 15
        protein_g = 10
    
    return {
        "timing": "训练前1-2小时",
        "carbs_g": round(carbs_g, 1),
        "protein_g": round(protein_g, 1),
        "fat_g": 5.0,
        "examples": ["香蕉+蛋白粉", "燕麦+鸡蛋"]
    }

def _calculate_post_workout_nutrition(
    self,
    training_type: str,
    body_weight_kg: float
) -> Dict[str, Any]:
    """计算训练后营养"""
    if training_type == "strength":
        protein_g = body_weight_kg * 0.4
        carbs_g = body_weight_kg * 0.8
    else:  # hypertrophy or endurance
        protein_g = body_weight_kg * 0.3
        carbs_g = body_weight_kg * 1.0
    
    return {
        "timing": "训练后30分钟内",
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carbs_g, 1),
        "fat_g": 10.0,
        "examples": ["鸡胸肉+米饭", "蛋白粉+香蕉"]
    }
```

---

## Learning工具（1个）

### find_similar_training_cases - 相似案例查找

**功能说明**: 基于质量评分和用户特征推荐相似的训练案例

**代码路径**: `mcp_tools/find_similar_training_cases.py`

**优先级**: P2扩展工具

#### 输入Schema

```python
class FindSimilarTrainingCasesInput(BaseModel):
    query: str = Field(..., description="用户查询")
    user_profile: Dict[str, Any] = Field(..., description="用户档案")
    training_goal: Optional[str] = Field(None, description="训练目标")
    min_quality_score: float = Field(4.0, description="最低质量评分")
    training_effect_filter: Optional[str] = Field(None, description="训练效果过滤")
    top_k: int = Field(5, description="返回案例数量")
```

#### Few-Shot检索

```python
async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行相似案例查找"""
    # 1. 使用Few-Shot检索器查找相似案例
    if self.few_shot_retriever:
        similar_examples, retrieval_stats = await self.few_shot_retriever.retrieve_with_quality_filter(
            query=input_data["query"],
            user_id=input_data["user_profile"].get("user_id"),
            query_complexity=None,
            top_k=input_data["top_k"] * 2
        )
    else:
        # 降级：直接从后端API搜索
        similar_examples = await self._fallback_search(
            query=input_data["query"],
            user_profile=input_data["user_profile"],
            top_k=input_data["top_k"] * 2
        )
    
    # 2. 应用额外过滤条件
    filtered_cases = self._apply_filters(
        examples=similar_examples,
        min_quality_score=input_data["min_quality_score"],
        training_effect_filter=input_data.get("training_effect_filter"),
        training_goal=input_data.get("training_goal"),
        user_profile=input_data["user_profile"]
    )
    
    # 3. 格式化结果
    formatted_cases = self._format_cases(filtered_cases[:input_data["top_k"]])
    
    return {
        "success": True,
        "similar_cases": formatted_cases,
        "total_found": len(formatted_cases),
        "recommendation": self._generate_recommendation(filtered_cases, input_data["query"])
    }
```

#### 过滤逻辑

```python
def _apply_filters(
    self,
    examples: List[Any],
    min_quality_score: float,
    training_effect_filter: Optional[str],
    training_goal: Optional[str],
    user_profile: Dict[str, Any]
) -> List[Any]:
    """应用额外的过滤条件"""
    filtered = []
    
    for example in examples:
        # 1. 质量评分过滤
        if example.quality_score < min_quality_score:
            continue
        
        # 2. 训练效果过滤
        if training_effect_filter:
            if not example.training_effect:
                continue
            if example.training_effect not in [training_effect_filter, "excellent"]:
                continue
        
        # 3. 训练目标匹配
        if training_goal:
            case_goal = example.metadata.get("training_goal")
            if case_goal and case_goal != training_goal:
                if example.quality_score < 4.5:
                    continue
        
        filtered.append(example)
    
    return filtered
```

---

## 使用示例

```python
# 1. TDEE计算
tdee_calc = TDEECalculator(neo4j_client, qdrant_client, three_layer_engine)
tdee_result = await tdee_calc.execute({
    "user_id": "user_123",
    "age": 30,
    "gender": "male",
    "weight_kg": 75.0,
    "height_cm": 175.0,
    "activity_level": "moderately_active",
    "training_goal": "muscle_gain"
})

# 2. 营养摄入分析
analyzer = NutritionIntakeAnalyzer(neo4j_client, qdrant_client, three_layer_engine)
analysis_result = await analyzer.execute({
    "user_id": "user_123",
    "daily_intake": {
        "protein_g": 150,
        "carbs_g": 300,
        "fat_g": 60,
        "calories": 2400
    }
})

# 3. 相似案例查找
finder = FindSimilarTrainingCasesTool(backend_client, vector_store)
cases_result = await finder.execute({
    "query": "增肌训练计划",
    "user_profile": {"user_id": "user_123", "training_level": "intermediate"},
    "training_goal": "hypertrophy",
    "min_quality_score": 4.0,
    "top_k": 5
})
```

---

## 工具总结

### 按优先级分类

**P0核心工具（5个）**:
1. intelligent_exercise_selector
2. contraindications_checker
3. injury_risk_assessor
4. muscle_group_volume_calculator
5. tdee_calculator

**P1建议工具（9个）**:
6. professional_program_designer
7. exercise_alternative_finder
8. movement_pattern_balancer
9. intelligent_weight_calculator
10. safe_exercise_modifier
11. nutrition_intake_analyzer
12. meal_plan_designer
13. exercise_nutrition_optimization
14. record_training_feedback

**P2扩展工具（3个）**:
15. periodized_program_designer
16. training_split_designer
17. find_similar_training_cases

---

## 相关链接

- **基础架构**: [02-基础架构与工具注册.md](./02-基础架构与工具注册.md)
- **MCP工具架构**: [../../02-核心架构/03-编排层/03-MCP工具架构.md](../../02-核心架构/03-编排层/03-MCP工具架构.md)
- **MCP工具开发指南**: [../../04-开发指南/01-快速上手/02-MCP工具开发指南.md](../../04-开发指南/01-快速上手/02-MCP工具开发指南.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
