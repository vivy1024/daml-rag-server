# Safety工具实现

**版本**: v2.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本文档详细说明Safety分类下的3个MCP工具实现，负责运动安全检查、损伤风险评估和动作修改建议。

**代码路径**: `daml-rag-server/src/applications/fitness/mcp_tools/safety/`

---

## 1. contraindications_checker - 禁忌症检查器

**功能说明**: 基于用户档案和Neo4j CONTRAINDICATED_FOR关系的医学安全检查

**代码路径**: `safety/contraindications_checker.py`

**优先级**: P0核心工具

### 输入Schema

```python
class ContraindicationsCheckerInput(BaseModel):
    user_id: str = Field(..., description="用户ID")
    exercise_ids: List[str] = Field(..., description="要检查的动作ID列表")
    health_conditions: Optional[List[str]] = Field(None, description="额外健康状况")
    include_recommendations: bool = Field(True, description="是否包含安全建议")
    strict_mode: bool = Field(False, description="严格模式：更保守的安全阈值")
```

### 输出Schema

```python
class ContraindicationsCheckerOutput(BaseModel):
    success: bool
    tool_name: str
    user_id: str
    checked_exercises: int
    exercises_with_contraindications: int
    high_risk_exercises: int
    exercise_results: List[ExerciseContraindicationStatus]
    overall_assessment: OverallAssessment
    medical_guidance: str
    execution_time_ms: float
    confidence_score: int
```

### Neo4j禁忌症查询

```python
async def _get_exercise_contraindications(
    self,
    exercise_id: str,
    health_conditions: List[str]
) -> List[Dict[str, Any]]:
    """获取动作的禁忌症（基于CONTRAINDICATED_FOR关系）"""
    query = """
    MATCH (e:Exercise {id: $exercise_id})
    OPTIONAL MATCH (e)-[r:CONTRAINDICATED_FOR]->(injury:InjuryType)
    WHERE injury.name_zh IN $health_conditions
       OR injury.name_en IN $health_conditions
       OR injury.category_zh IN $health_conditions
    
    RETURN
      injury.name_zh as injury_name_zh,
      injury.name_en as injury_name_en,
      injury.category_zh as category_zh,
      r.risk_level as risk_level,
      r.severity as severity,  # absolute/relative/caution
      r.reason as reason,
      r.severity_score as severity_score,
      injury.affected_body_parts as body_parts,
      injury.medical_source as medical_source
    ORDER BY r.severity_score DESC
    """
    
    result = await self.neo4j_client.query(query, {
        "exercise_id": exercise_id,
        "health_conditions": health_conditions
    })
    
    contraindications = []
    for row in result:
        if row.get("injury_name_zh") is None:
            continue
        
        contraindications.append({
            "exercise_id": exercise_id,
            "contraindication_type": row.get("category_zh") or "Unknown",
            "risk_level": self._map_risk_level(row.get("risk_level")),
            "severity": row.get("severity", "relative"),
            "reason": row.get("reason") or "基于医学指导",
            "severity_score": int(row.get("severity_score") or 5),
            "body_part_affected": ", ".join(row.get("body_parts", [])),
            "medical_source": row.get("medical_source")
        })
    
    return contraindications
```

### 严重程度分级处理

```python
def _generate_exercise_recommendations(
    self,
    exercise_info: Dict[str, Any],
    contraindications: List[Dict[str, Any]],
    risk_assessment: Dict[str, Any],
    health_conditions: List[str]
) -> Dict[str, Any]:
    """生成动作建议（基于severity字段）"""
    has_absolute = any(c.get("severity") == "absolute" for c in contraindications)
    has_relative = any(c.get("severity") == "relative" for c in contraindications)
    has_caution = any(c.get("severity") == "caution" for c in contraindications)
    
    # 绝对禁忌：完全不能执行
    can_perform = not has_absolute
    
    recommendations = {
        "can_perform": can_perform,
        "modifications": [],
        "alternatives": [],
        "precautions": [],
        "medical_consultation_needed": has_absolute or risk_assessment["max_level"] in ["HIGH", "CRITICAL"]
    }
    
    # 绝对禁忌的建议
    if has_absolute:
        absolute_injuries = [c.get("contraindication_type") for c in contraindications if c.get("severity") == "absolute"]
        recommendations["precautions"].append(
            f"⛔ 绝对禁忌：由于{', '.join(absolute_injuries)}，必须完全避免此动作"
        )
        recommendations["alternatives"].append("寻找完全不涉及受伤部位的替代动作")
        recommendations["alternatives"].append("咨询医疗专业人员获取个性化建议")
        return recommendations
    
    # 相对禁忌的建议
    if has_relative:
        relative_injuries = [c.get("contraindication_type") for c in contraindications if c.get("severity") == "relative"]
        recommendations["precautions"].append(
            f"⚠️ 相对禁忌：由于{', '.join(relative_injuries)}，需要在专业指导下谨慎进行"
        )
        recommendations["modifications"].extend([
            "大幅降低训练重量（50%以下）",
            "减少动作幅度至无痛范围",
            "延长休息时间，密切监控身体反应"
        ])
        recommendations["precautions"].append("如有任何疼痛或不适，立即停止")
    
    # 谨慎使用的建议
    if has_caution:
        caution_reasons = [c.get("reason") for c in contraindications if c.get("severity") == "caution"]
        recommendations["precautions"].append(
            f"💡 谨慎使用：{caution_reasons[0] if caution_reasons else '需要特别注意'}"
        )
        recommendations["modifications"].extend([
            "适当降低训练强度",
            "充分热身和拉伸",
            "注意动作质量和控制"
        ])
    
    return recommendations
```

### 风险评估

```python
def _assess_risk_level(
    self,
    contraindications: List[Dict[str, Any]],
    strict_mode: bool
) -> Dict[str, Any]:
    """评估风险等级"""
    if not contraindications:
        return {"total_score": 0, "max_level": "LOW", "level": "LOW"}
    
    severity_scores = [c["severity_score"] for c in contraindications]
    max_score = max(severity_scores)
    total_score = sum(severity_scores)
    
    # 确定最大风险等级
    if max_score >= 8:
        max_level = "CRITICAL"
    elif max_score >= 6:
        max_level = "HIGH"
    elif max_score >= 4:
        max_level = "MODERATE"
    else:
        max_level = "LOW"
    
    # 严格模式下调整风险等级
    if strict_mode and max_level != "LOW":
        levels = ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        current_index = levels.index(max_level)
        if current_index < len(levels) - 1:
            max_level = levels[current_index + 1]
    
    return {
        "total_score": total_score,
        "max_level": max_level,
        "level": max_level
    }
```

---

## 2. injury_risk_assessor - 损伤风险评估器

**功能说明**: 评估动作的损伤风险，考虑用户历史和动作特性

**代码路径**: `safety/injury_risk_assessor.py`

**优先级**: P0核心工具

### 风险因素分析

```python
def _analyze_risk_factors(
    self,
    exercise: Dict[str, Any],
    user_profile: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """分析损伤风险因素"""
    risk_factors = []
    
    # 1. 动作复杂度风险
    if exercise.get("difficulty") == "高级":
        risk_factors.append({
            "factor": "动作复杂度高",
            "severity": "MEDIUM",
            "score": 3,
            "mitigation": "建议在教练指导下进行"
        })
    
    # 2. 负重风险
    if "杠铃" in exercise.get("equipment_zh", []):
        risk_factors.append({
            "factor": "大重量负重",
            "severity": "MEDIUM",
            "score": 3,
            "mitigation": "确保有保护员，使用安全架"
        })
    
    # 3. 关节应力风险
    if "肩" in exercise.get("primary_muscles", []):
        if user_profile.get("injury_history") and "肩部损伤" in user_profile["injury_history"]:
            risk_factors.append({
                "factor": "肩关节应力",
                "severity": "HIGH",
                "score": 5,
                "mitigation": "降低重量，控制动作幅度"
            })
    
    # 4. 脊柱负荷风险
    if exercise.get("movement_pattern_zh") == "髋铰链":
        risk_factors.append({
            "factor": "脊柱负荷",
            "severity": "MEDIUM",
            "score": 4,
            "mitigation": "保持脊柱中立位，核心收紧"
        })
    
    return risk_factors
```

---

## 3. safe_exercise_modifier - 安全动作修改器

**功能说明**: 根据用户限制修改动作参数，提供安全的训练方案

**代码路径**: `safety/safe_exercise_modifier.py`

**优先级**: P1建议工具

### 动作修改策略

```python
def _generate_modifications(
    self,
    exercise: Dict[str, Any],
    user_constraints: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """生成动作修改建议"""
    modifications = []
    
    # 1. 重量修改
    if user_constraints.get("reduce_load"):
        modifications.append({
            "type": "weight",
            "modification": "降低训练重量至60-70%",
            "reason": "减少关节压力",
            "implementation": "使用较轻的哑铃或减少杠铃片"
        })
    
    # 2. 幅度修改
    if user_constraints.get("limited_range"):
        affected_joint = user_constraints.get("affected_joint", "关节")
        modifications.append({
            "type": "range_of_motion",
            "modification": f"限制{affected_joint}活动幅度",
            "reason": "避免疼痛区域",
            "implementation": f"在无痛范围内进行，避免{affected_joint}过度伸展或屈曲"
        })
    
    # 3. 速度修改
    if user_constraints.get("control_speed"):
        modifications.append({
            "type": "tempo",
            "modification": "降低动作速度，增加控制",
            "reason": "提高动作质量，减少冲击",
            "implementation": "采用3-1-3节奏（3秒下降，1秒停顿，3秒上升）"
        })
    
    # 4. 器械替换
    if user_constraints.get("equipment_limitation"):
        modifications.append({
            "type": "equipment",
            "modification": "使用更安全的器械变式",
            "reason": "降低技术要求和风险",
            "implementation": "用史密斯机替代自由杠铃，或用固定器械替代自由重量"
        })
    
    return modifications
```

---

## 4. postural_assessor - 体态评估工具

**功能说明**: 评估用户体态问题，推荐矫正动作并警告加重动作

**代码路径**: `safety/postural_assessor.py`

**优先级**: P1建议工具

**Requirements**: 20.5, 20.6

### 输入Schema

```python
class PosturalAssessorInput(BaseModel):
    """体态评估工具输入Schema"""
    user_id: str = Field(..., description="用户ID，用于获取体态问题")
    postural_issues: Optional[List[str]] = Field(
        None,
        description="体态问题列表（中文），如果不提供则从用户档案读取"
    )
    include_exercises: bool = Field(
        True,
        description="是否包含矫正和加重动作列表"
    )
    max_exercises_per_issue: int = Field(
        5,
        description="每个体态问题返回的最大动作数量"
    )
```

### 输出Schema

```python
class PosturalAssessorOutput(BaseModel):
    """体态评估工具输出Schema"""
    success: bool
    tool_name: str
    user_id: str
    assessment_date: str

    # 评估结果
    total_issues: int
    issues_assessed: List[PosturalIssueAssessment]

    # 总体建议
    overall_recommendations: List[str]
    priority_issues: List[str]

    # 元数据
    execution_time_ms: float
    data_source: str


class PosturalIssueAssessment(BaseModel):
    """单个体态问题评估"""
    issue_name: str
    issue_name_zh: str
    category: str
    description: str

    # 相关肌肉
    related_muscles: List[RelatedMuscle]

    # 矫正动作
    corrective_exercises: List[CorrectiveExercise]
    corrective_count: int

    # 加重动作
    aggravating_exercises: List[AggravatingExercise]
    aggravating_count: int

    # 建议
    recommendations: List[str]
```

### Neo4j关系查询

```python
async def _get_corrective_exercises(
    self, issue_name: str, max_count: int
) -> List[CorrectiveExercise]:
    """获取矫正动作"""
    query = """
    MATCH (e:Exercise)-[:CORRECTS]->(p:PosturalIssue {name: $issue_name})
    RETURN e.id as exercise_id,
           e.name as name,
           e.name_zh as name_zh,
           e.category as category,
           e.difficulty_zh as difficulty,
           e.description as description
    ORDER BY e.difficulty_zh
    LIMIT $max_count
    """
    results = self.neo4j_client.execute_query(
        query,
        {"issue_name": issue_name, "max_count": max_count}
    )
    # ...


async def _get_aggravating_exercises(
    self, issue_name: str, max_count: int
) -> List[AggravatingExercise]:
    """获取加重动作"""
    query = """
    MATCH (e:Exercise)-[:AGGRAVATES]->(p:PosturalIssue {name: $issue_name})
    RETURN e.id as exercise_id,
           e.name as name,
           e.name_zh as name_zh,
           e.category as category,
           e.safety_level as risk_level
    LIMIT $max_count
    """
    # ...
```

### 功能特性

1. **识别体态问题**: 从用户档案读取或直接输入体态问题
2. **推荐矫正动作**: 基于CORRECTS关系查询矫正动作
3. **警告加重动作**: 基于AGGRAVATES关系查询加重动作
4. **提供相关肌肉信息**: 基于RELATED_TO关系展示相关肌肉
5. **生成针对性建议**: 根据评估结果生成个性化建议

### 使用示例

```python
# 体态评估
assessor = PosturalAssessor(neo4j_client, qdrant_client, three_layer_engine)
result = await assessor.execute({
    "user_id": "user_123",
    "postural_issues": ["圆肩", "骨盆前倾"],
    "include_exercises": True,
    "max_exercises_per_issue": 5
})

# 返回结果示例
{
    "success": True,
    "tool_name": "postural_assessor",
    "user_id": "user_123",
    "total_issues": 2,
    "issues_assessed": [
        {
            "issue_name_zh": "圆肩",
            "category": "upper_body",
            "corrective_exercises": [...],
            "aggravating_exercises": [...],
            "recommendations": [
                "建议每星期进行2-3次矫正训练",
                "加强上背部肌肉训练，拉伸胸部肌肉"
            ]
        }
    ],
    "overall_recommendations": [
        "检测到2个体态问题，建议制定系统的矫正训练计划",
        "矫正训练应循序渐进，避免急于求成"
    ]
}
```

---

## 使用示例

```python
# 1. 禁忌症检查
checker = ContraindicationsChecker(neo4j_client, qdrant_client, three_layer_engine)
result = await checker.execute({
    "user_id": "user_123",
    "exercise_ids": ["squat_001", "deadlift_001"],
    "health_conditions": ["腰椎间盘突出", "膝关节炎"],
    "strict_mode": True
})

# 2. 损伤风险评估
assessor = InjuryRiskAssessor(neo4j_client, qdrant_client, three_layer_engine)
risk_result = await assessor.execute({
    "user_id": "user_123",
    "exercise_id": "overhead_press_001"
})

# 3. 安全动作修改
modifier = SafeExerciseModifier(neo4j_client, qdrant_client, three_layer_engine)
mod_result = await modifier.execute({
    "exercise_id": "squat_001",
    "user_constraints": {
        "reduce_load": True,
        "limited_range": True,
        "affected_joint": "膝关节"
    }
})
```

---

## 相关链接

- **基础架构**: [02-基础架构与工具注册.md](./02-基础架构与工具注册.md)
- **Exercise工具**: [03-Exercise工具实现.md](./03-Exercise工具实现.md)
- **Nutrition工具**: [06-Nutrition工具实现.md](./06-Nutrition工具实现.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
