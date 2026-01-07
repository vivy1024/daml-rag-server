# Exercise工具实现

**版本**: v2.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本文档详细说明Exercise分类下的2个MCP工具实现，包括智能动作选择器和动作替代查找器。

**代码路径**: `daml-rag-server/src/applications/fitness/mcp_tools/exercise/`

---

## 1. intelligent_exercise_selector - 智能动作选择器

**功能说明**: 基于三层检索引擎的个性化动作推荐系统

**代码路径**: `exercise/intelligent_exercise_selector.py`

**优先级**: P0核心工具

### 输入Schema

```python
class IntelligentExerciseSelectorInput(BaseModel):
    user_id: str = Field(..., description="用户ID")
    muscle_group: str = Field(..., description="目标肌群")
    training_goal: TrainingGoal = Field(..., description="训练目标")
    difficulty_level: DifficultyLevel = Field(..., description="难度等级")
    available_equipment: List[str] = Field(..., description="可用器械列表")
    injury_history: Optional[List[str]] = Field(None, description="损伤历史")
    exercise_preferences: Optional[List[str]] = Field(None, description="运动偏好")
    disliked_exercises: Optional[List[str]] = Field(None, description="不喜欢的动作")
    session_focus: Optional[SessionFocus] = Field(None, description="训练重点")
```

### 输出Schema

```python
class IntelligentExerciseSelectorOutput(BaseModel):
    success: bool
    tool_name: str
    query_params: Dict[str, Any]
    recommendations: List[ExerciseRecommendation]  # Top 10
    reasoning: str
    safety_alerts: List[str]
    total_found: int
    execution_time_ms: float
    confidence_score: float
```

### 三层检索调用

```python
async def _query_exercises_via_three_layer(
    self,
    query_text: str,
    input_data: Dict[str, Any],
    user_profile: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """通过三层检索引擎查询动作"""
    filters = {
        "muscle_group": input_data["muscle_group"],
        "difficulty_level": input_data["difficulty_level"],
        "available_equipment": input_data["available_equipment"],
        "injury_history": input_data.get("injury_history", [])
    }
    
    result = await self.three_layer_engine.execute_three_layer_query(
        query=query_text,
        domain="fitness_exercises",
        user_id=input_data.get("user_id"),
        user_profile=user_profile,
        filters=filters,
        top_k=50,  # Layer 1召回更多候选
        safety_check=True
    )
    
    return result.final_results
```

### 评分算法

```python
def _calculate_suitability_score(
    self,
    exercise: Dict[str, Any],
    input_data: Dict[str, Any],
    user_profile: Dict[str, Any]
) -> float:
    """计算适配度评分（0-100）"""
    score = 50.0  # 基础分
    
    # 训练目标匹配 (+20)
    training_goal = input_data["training_goal"]
    if training_goal == "strength" and "推" in exercise.get("force_type", ""):
        score += 20
    elif training_goal == "hypertrophy":
        score += 15
    
    # 器械可用性 (+20)
    available = set(input_data["available_equipment"])
    required = set(exercise.get("equipment_zh", []))
    if required.issubset(available):
        score += 20
    
    # 用户偏好 (+10)
    if user_profile.get("exercise_preferences"):
        if exercise.get("movement_pattern") in user_profile["exercise_preferences"]:
            score += 10
    
    # 避免不喜欢的动作 (-30)
    if exercise["id"] in input_data.get("disliked_exercises", []):
        score -= 30
    
    return min(100.0, max(0.0, score))

def _calculate_safety_score(
    self,
    exercise: Dict[str, Any],
    input_data: Dict[str, Any],
    user_profile: Dict[str, Any]
) -> float:
    """计算安全评分（0-100）"""
    score = 100.0  # 基础分
    
    # 安全等级 (-40/-20)
    if exercise["safety_level"] == "HIGH_RISK":
        score -= 40
    elif exercise["safety_level"] == "MEDIUM_RISK":
        score -= 20
    
    # 损伤史匹配 (-10 per match)
    injury_history = set(input_data.get("injury_history", []))
    contraindications = set(exercise.get("contraindications_zh", []))
    matches = injury_history & contraindications
    score -= len(matches) * 10
    
    # 难度不匹配 (-20)
    if input_data["difficulty_level"] == "beginner":
        if "高级" in exercise.get("difficulty", ""):
            score -= 20
    
    return min(100.0, max(0.0, score))
```

### 使用示例

```python
# 初始化工具
selector = IntelligentExerciseSelector(
    neo4j_client=neo4j_client,
    qdrant_client=qdrant_client,
    three_layer_engine=three_layer_engine
)

# 调用工具
result = await selector.execute({
    "user_id": "user_123",
    "muscle_group": "胸",
    "training_goal": "hypertrophy",
    "difficulty_level": "intermediate",
    "available_equipment": ["杠铃", "哑铃", "卧推凳"],
    "injury_history": ["肩部损伤"]
})

# 结果
print(f"找到 {result['total_found']} 个推荐动作")
for rec in result['recommendations'][:3]:
    print(f"- {rec['name_zh']}: 适配度{rec['suitability_score']}, 安全{rec['safety_score']}")
```

---

## 2. exercise_alternative_finder - 动作替代查找器

**功能说明**: 基于肌肉激活模式和器械可用性查找替代动作

**代码路径**: `exercise/exercise_alternative_finder.py`

**优先级**: P1建议工具

### 输入Schema

```python
class ExerciseAlternativeFinderInput(BaseModel):
    original_exercise_id: str = Field(..., description="原始动作ID")
    reason_for_alternative: str = Field(..., description="需要替代的原因")
    available_equipment: List[str] = Field(..., description="可用器械")
    user_constraints: Optional[Dict[str, Any]] = Field(None, description="用户限制")
    preserve_intensity: bool = Field(True, description="是否保持强度")
```

### 输出Schema

```python
class ExerciseAlternativeFinderOutput(BaseModel):
    success: bool
    tool_name: str
    original_exercise: Dict[str, Any]
    alternatives: List[AlternativeExercise]
    reasoning: str
    total_found: int
    execution_time_ms: float
```

### Neo4j查询替代动作

```python
async def _find_alternatives_via_neo4j(
    self,
    original_exercise_id: str,
    available_equipment: List[str]
) -> List[Dict[str, Any]]:
    """通过Neo4j查找替代动作"""
    query = """
    MATCH (original:Exercise {id: $exercise_id})
    MATCH (original)-[:TARGETS]->(muscle:Muscle)
    MATCH (alt:Exercise)-[:TARGETS]->(muscle)
    WHERE alt.id <> $exercise_id
      AND alt.equipment_zh IN $available_equipment
    
    WITH alt, COUNT(DISTINCT muscle) as shared_muscles
    ORDER BY shared_muscles DESC
    LIMIT 20
    
    RETURN alt.id as exercise_id,
           alt.name_zh,
           alt.name_en,
           alt.equipment_zh,
           alt.difficulty,
           alt.safety_level,
           shared_muscles
    """
    
    result = await self.neo4j_client.query(query, {
        "exercise_id": original_exercise_id,
        "available_equipment": available_equipment
    })
    
    return [dict(row) for row in result]
```

### 相似度计算

```python
def _calculate_similarity_score(
    self,
    original: Dict[str, Any],
    alternative: Dict[str, Any]
) -> float:
    """计算动作相似度（0-100）"""
    score = 0.0
    
    # 肌肉激活相似度 (40分)
    original_muscles = set(original.get("primary_muscles", []))
    alt_muscles = set(alternative.get("primary_muscles", []))
    if original_muscles and alt_muscles:
        muscle_overlap = len(original_muscles & alt_muscles) / len(original_muscles)
        score += muscle_overlap * 40
    
    # 动作模式相似度 (30分)
    if original.get("movement_pattern") == alternative.get("movement_pattern"):
        score += 30
    
    # 力量类型相似度 (20分)
    if original.get("force_type") == alternative.get("force_type"):
        score += 20
    
    # 难度接近度 (10分)
    difficulty_map = {"初级": 1, "中级": 2, "高级": 3}
    orig_diff = difficulty_map.get(original.get("difficulty", "中级"), 2)
    alt_diff = difficulty_map.get(alternative.get("difficulty", "中级"), 2)
    diff_score = max(0, 10 - abs(orig_diff - alt_diff) * 5)
    score += diff_score
    
    return min(100.0, score)
```

---

## 相关链接

- **基础架构**: [02-基础架构与工具注册.md](./02-基础架构与工具注册.md)
- **Training工具**: [04-Training工具实现.md](./04-Training工具实现.md)
- **Safety工具**: [05-Safety工具实现.md](./05-Safety工具实现.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
