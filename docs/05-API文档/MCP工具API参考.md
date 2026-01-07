# MCP工具API参考文档

**创建日期**: 2025-12-22

---


**版本**: v2.0.0
**更新日期**: 2025-12-16
**状态**: ✅ 已完成 · 15个Python MCP工具 + 用户档案MCP

---

## 📋 概述

本文档详细记录了DAML-RAG系统中16个MCP工具的API规范、输入输出格式、使用示例。这些工具分为两类：

1. **15个Python MCP工具**：集成在DAML-RAG容器内，直接查询Neo4j数据库并返回结构化JSON结果
2. **用户档案MCP**：集成部署在DAML-RAG容器内，提供用户档案管理功能

### 部署架构

```
DAML-RAG容器 (fitness_daml_rag)
├── 15个Python MCP工具（集成部署）
│   ├── 基础数据工具 (5个)
│   ├── 安全工具 (3个)
│   ├── 动作工具 (4个)
│   ├── 训练规划工具 (5个)
│   ├── 营养工具 (5个)
│   ├── 分析工具 (2个)
│   └── 辅助工具 (1个)
└── 用户档案MCP（集成部署）
    └── 用户档案管理工具 (1个)
```

### 工具分类

```
基础数据工具 (5个)
├── get_user_profile - 用户档案工具 ⭐ 用户档案MCP
├── tdee_calculator - TDEE计算器
├── assess_strength_level - 力量水平评估器
├── training_split_designer - 训练分化设计器
└── movement_pattern_balancer - 动作模式平衡器

安全工具 (3个)
├── contraindications_checker - 禁忌症检查器
├── injury_risk_assessor - 损伤风险评估器
└── safe_exercise_modifier - 安全动作修改器

动作工具 (4个)
├── intelligent_exercise_selector - 智能动作选择器
├── exercise_alternative_finder - 动作替代查找器
├── intelligent_weight_calculator - 智能重量计算器
└── exercise_similarity_finder - 动作相似度查找器

训练规划工具 (5个)
├── professional_program_designer - 专业计划设计器
├── periodized_program_designer - 周期化程序设计器
├── muscle_group_volume_calculator - 肌群训练量计算器
├── training_analytics_dashboard - 训练分析仪表板
└── evidence_based_recommender - 循证推荐器

营养工具 (5个)
├── nutrition_intake_analyzer - 营养摄入分析器
├── meal_plan_designer - 膳食计划设计器
├── exercise_nutrition_optimization - 动作营养优化器
├── muscle_recovery_nutrition - 肌肉恢复营养工具
└── nutrition_timing_optimizer - 营养时机优化器

分析工具 (2个)
├── training_analytics_dashboard - 训练分析仪表板
└── evidence_based_recommender - 循证推荐器

辅助工具 (1个)
└── assess_strength_level - 力量水平评估器
```

---

## 👤 用户档案MCP

### 1. get_user_profile - 用户档案工具

#### 功能描述
获取用户的完整档案信息，包括基本信息、健身配置、健身目标、健康状况等。此工具已集成部署在DAML-RAG容器内，提供高性能的用户档案访问。

#### 部署方式
- **当前部署**：集成在DAML-RAG容器内
- **原因**：高频调用，避免网络开销，简化部署
- **性能**：0延迟，直接内存访问

#### 方法签名
```python
async def execute(params: Dict[str, Any]) -> Dict[str, Any]
```

#### 输入参数
```python
{
    "user_id": int  # 用户ID
}
```

#### 输出格式
```python
{
    "tool": "GetUserProfile",
    "status": "success",
    "user_profile": {
        "basic_info": {
            "user_id": int,
            "name": str,
            "age": int,
            "gender": str,
            "height_cm": float,
            "weight_kg": float,
            "bmi": float
        },
        "fitness_config": {
            "fitness_level": str,           # "beginner", "intermediate", "advanced"
            "training_frequency": int,       # 每周训练天数
            "available_equipment": List[str],
            "preferred_training_time": str,
            "training_location": str
        },
        "fitness_goals": {
            "primary_goal": str,            # "增肌", "减脂", "力量", "耐力"
            "target_weight_kg": float,
            "target_body_fat_percentage": float,
            "goal_timeline_weeks": int
        },
        "health_status": {
            "known_injuries": List[str],
            "medical_conditions": List[str],
            "medications": List[str],
            "contraindications": List[str]
        },
        "preferences": {
            "favorite_exercises": List[str],
            "disliked_exercises": List[str],
            "dietary_restrictions": List[str],
            "training_style_preference": str
        }
    },
    "execution_time_ms": float
}
```

#### 使用示例
```python
user_profile_tool = GetUserProfile(backend_client)
result = await user_profile_tool.execute({
    "user_id": 123
})
```

---

## 🔧 基础数据工具

### 2. tdee_calculator - TDEE计算器

#### 功能描述
基于用户条件推荐适合的动作，融入FitnessOrchestrator DAG编排。查询Neo4j基于31字段Exercise数据，返回结构化JSON。

#### 方法签名
```python
async def execute(params: Dict[str, Any]) -> Dict[str, Any]
```

#### 输入参数
```python
{
    "muscle_group": str,              # 目标肌群 (如 "胸", "背", "腿")
    "available_equipment": List[str], # 可用器械列表 (如 ["哑铃", "杠铃"])
    "difficulty_level": str,          # 难度等级 ("beginner", "intermediate", "advanced")
    "training_goal": str,             # 训练目标 ("strength", "hypertrophy", "endurance", "general_fitness")
    "injury_history": List[str],      # 损伤史列表 (可选)
    "top_k": int                      # 返回数量 (可选，默认20)
}
```

#### 输出格式
```python
{
    "tool": "IntelligentExerciseSelector",
    "status": "success",
    "exercises": [
        {
            "exercise_id": str,
            "name_zh": str,
            "name_en": str,
            "primary_muscle_zh": str,
            "secondary_muscles_zh": List[str],
            "equipment_needed": List[str],
            "difficulty_level": str,
            "movement_pattern": str,
            "force_type": str,
            "mechanics": str,
            "safety_score": float,
            "instructions_zh": str (可选),
            "common_mistakes_zh": List[str] (可选),
            "safety_warnings_zh": List[str] (可选),
            "contraindications_zh": List[str] (可选),
            "progression_options": List[str] (可选)
        }
    ],
    "reasoning": str,
    "safety_alerts": List[str],
    "total_count": int,
    "execution_time_ms": float
}
```

#### 使用示例
```python
selector = IntelligentExerciseSelector(neo4j_client)
result = await selector.execute({
    "muscle_group": "胸",
    "available_equipment": ["哑铃", "杠铃"],
    "difficulty_level": "intermediate",
    "training_goal": "hypertrophy",
    "injury_history": []
})
```

---

### 2. exercise_similarity_finder - 动作相似度查找器

#### 功能描述
基于功能相似性查找替代动作，支持多种相似度类型：肌群目标、动作模式、器械、生物力学。

#### 方法签名
```python
async def execute(params: Dict[str, Any]) -> Dict[str, Any]
```

#### 输入参数
```python
{
    "exercise_id": str,              # 源动作ID
    "similarity_type": str,          # 相似度类型 ("muscle_target", "movement_pattern", "equipment", "biomechanics")
    "top_k": int,                    # 返回相似动作数量 (可选，默认5)
    "min_score": float               # 最小相似度阈值 (可选，默认0.5)
}
```

#### 输出格式
```python
{
    "tool": "ExerciseSimilarityFinder",
    "status": "success",
    "source_exercise": {
        "exercise_id": str,
        "name_zh": str,
        "name_en": str,
        "primary_muscle_zh": str,
        "movement_pattern_zh": str,
        "equipment_zh": List[str],
        "mechanics_zh": str,
        "force_type_zh": str
    },
    "similar_exercises": [
        {
            "exercise_id": str,
            "name_zh": str,
            "name_en": str,
            "similarity_score": float,
            "similarity_type": str,
            "match_factors": List[str],
            "differences": List[str],
            "switch_guidance": str,
            "equipment_needed": List[str],
            "difficulty_level": str
        }
    ],
    "similarity_analysis": {
        "similarity_type": str,
        "total_candidates": int,
        "qualified_count": int,
        "average_similarity": float,
        "max_similarity": float,
        "min_similarity": float
    },
    "switch_guidance": str,
    "execution_time_ms": float
}
```

#### 使用示例
```python
finder = ExerciseSimilarityFinder(neo4j_client)
result = await finder.execute({
    "exercise_id": "ex_001",
    "similarity_type": "muscle_target",
    "top_k": 5
})
```

---

### 3. safe_exercise_modifier - 安全动作修改器

#### 功能描述
根据损伤类型调整动作，提供安全的替代方案。基于InjuryType数据调整Exercise参数。

#### 方法签名
```python
async def execute(params: Dict[str, Any]) -> Dict[str, Any]
```

#### 输入参数
```python
{
    "exercise_id": str,                  # 原动作ID
    "injury_type": str,                  # 损伤类型 (如 "肩部损伤", "腰部损伤")
    "user_limitations": Dict[str, Any],  # 用户限制 (可选)
    "modification_preference": str       # 修改偏好 ("safe_only", "moderate", "adaptive")
}
```

#### 输出格式
```python
{
    "tool": "SafeExerciseModifier",
    "status": "success",
    "original_exercise": {
        "exercise_id": str,
        "name_zh": str,
        "name_en": str,
        "primary_muscle_zh": str,
        "movement_pattern_zh": str,
        "contraindications_zh": List[str],
        "safety_warning_signs_zh": List[str]
    },
    "modifications": [
        {
            "original_exercise_id": str,
            "original_name_zh": str,
            "modified_exercise_id": str (可选),
            "modified_name_zh": str,
            "modification_type": str,      # "alternative", "modified_version", "avoid"
            "safety_score_before": float,
            "safety_score_after": float,
            "modifications_applied": List[str],
            "contraindications_avoided": List[str],
            "safety_enhancements": List[str],
            "instructions_zh": str,
            "warnings": List[str]
        }
    ],
    "medical_guidance": str,
    "contraindications_analysis": {
        "has_contraindications": bool,
        "risk_level": str,
        "contraindications_count": int,
        "max_severity": int,
        "contraindications_details": List[Dict],
        "warnings": List[str]
    },
    "safety_recommendations": List[str],
    "execution_time_ms": float
}
```

---

## 🏗️ Phase 2: 训练规划工具

### 4. periodized_program_designer - 周期化程序设计器

#### 功能描述
基于PeriodizationModel设计完整周期化训练计划。查询Neo4j获取5种PeriodizationModel和TrainingPhase数据。

#### 输入参数
```python
{
    "user_level": str,                   # 用户水平 ("beginner", "intermediate", "advanced")
    "training_goal": str,                # 训练目标 ("strength", "hypertrophy", "endurance", "general_fitness")
    "training_days_per_week": int,       # 每周训练天数 (2-7)
    "available_equipment": List[str],    # 可用器械列表
    "injury_history": List[str],         # 损伤史列表 (可选)
    "program_duration_weeks": int        # 计划持续周数 (可选，默认12)
}
```

#### 输出格式
```python
{
    "tool": "PeriodizedProgramDesigner",
    "status": "success",
    "program": {
        "program_id": str,
        "user_id": str,
        "training_goal": str,
        "user_level": str,
        "model_type": str,               # "linear", "undulating", "block", "conjugate", "reverse"
        "total_weeks": int,
        "phases": [
            {
                "phase_id": str,
                "phase_name_zh": str,
                "duration_weeks": int,
                "focus_area": str,
                "intensity_range": [float, float],    # [min, max] %1RM
                "volume_range": [int, int],           # [min, max] 组
                "reps_range": [int, int],             # [min, max] 次
                "rpe_target": str,
                "objectives": List[str],
                "phase_type": str
            }
        ],
        "weekly_structure": Dict[int, Dict[str, Any]],
        "progression_logic": List[str],
        "equipment_considerations": List[str],
        "injury_adaptations": List[str]
    },
    "model_selection_rationale": str,
    "scientific_basis": List[str],
    "progression_tracking": {
        "weekly_assessments": List[Dict],
        "phase_transition_criteria": Dict[str, List[str]]
    },
    "equipment_adaptations": List[str],
    "execution_time_ms": float
}
```

---

### 5. muscle_group_volume_calculator - 肌群训练量计算器

#### 功能描述
基于Muscle节点信息计算训练量，使用MEV/MAV/MRV科学训练容量理论。

#### 输入参数
```python
{
    "muscle_group": str,                 # 目标肌群 (如 "胸", "背", "股四头肌")
    "training_frequency": str,           # 每周训练频率 (如 "2-3次", "1-2次")
    "training_goal": str,                # 训练目标 ("strength", "hypertrophy", "endurance")
    "user_level": str,                   # 用户水平 ("beginner", "intermediate", "advanced")
    "injury_status": str                 # 损伤状态 ("healthy", "recovering", "limited")
}
```

#### 输出格式
```python
{
    "tool": "MuscleGroupVolumeCalculator",
    "status": "success",
    "muscle_info": {
        "muscle_id": str,
        "name_zh": str,
        "name_en": str,
        "recovery_time_hours": int,
        "training_frequency": str,
        "fiber_type_distribution": Dict,
        "mev": int,
        "mav": int,
        "mrv": int
    },
    "volume_recommendations": {
        "muscle_group": str,
        "muscle_id": str,
        "recovery_time_hours": int,
        "training_frequency": str,
        "mev_range": [int, int],
        "mav_range": [int, int],
        "mrv_range": [int, int],
        "recommended_sets": int,
        "recommended_reps_range": [int, int],
        "recommended_exercises": List[Dict],
        "safety_considerations": List[str],
        "progression_guidelines": List[str]
    },
    "scientific_basis": List[str],
    "personalization_factors": {
        "muscle_characteristics": Dict,
        "training_variables": Dict,
        "adaptation_timeline": Dict
    },
    "execution_time_ms": float
}
```

---

### 6. movement_pattern_balancer - 动作模式平衡器

#### 功能描述
确保动作模式平衡，分析肌群协同关系。基于Muscle.synergy_partners和movement_patterns。

#### 输入参数
```python
{
    "current_program": List[str],        # 当前计划的动作ID列表
    "target_muscle_groups": List[str]    # 目标肌群列表
}
```

#### 输出格式
```python
{
    "tool": "MovementPatternBalancer",
    "status": "success",
    "balance_analysis": {
        "balanced_score": float,
        "imbalanced_patterns": List[str],
        "synergy_coverage": Dict[str, List[str]],
        "antagonist_balance": Dict[str, str],
        "adjustment_suggestions": List[str]
    },
    "program_adjustments": List[str],
    "execution_time_ms": float
}
```

---

## 🛡️ Phase 3: 安全与康复工具

### 7. injury_risk_assessor - 损伤风险评估器

#### 功能描述
基于真实动作数据评估损伤风险，使用Exercise.safety_level和safety_warning_signs。

#### 输入参数
```python
{
    "exercise_id": str,                  # 动作ID
    "user_profile": {                    # 用户档案
        "experience_level": str,         # ("beginner", "intermediate", "advanced")
        "known_injuries": List[str],     # 已知损伤列表
        "movement_quality": str          # 动作质量 ("good", "fair", "poor")
    }
}
```

#### 输出格式
```python
{
    "tool": "InjuryRiskAssessor",
    "status": "success",
    "exercise": {
        "name_zh": str,
        "difficulty_level": str,
        "safety_level": str
    },
    "risk_assessment": {
        "risk_level": str,               # "low", "moderate", "high", "very_high"
        "risk_score": float,
        "risk_factors": List[str],
        "protective_factors": List[str],
        "modification_suggestions": List[str],
        "monitoring_guidance": List[str]
    },
    "execution_time_ms": float
}
```

---

### 8. contraindications_checker - 禁忌症检查器

#### 功能描述
检查动作禁忌，基于CONTRAINDICATED_FOR关系检查兼容性。

#### 输入参数
```python
{
    "user_conditions": List[str],        # 用户条件/损伤类型ID列表
    "proposed_exercises": List[str]      # 拟议动作ID列表
}
```

#### 输出格式
```python
{
    "tool": "ContraindicationsChecker",
    "status": "success",
    "compatibility_matrix": {
        str: {                           # exercise_id
            str: str                     # condition: "compatible" | "caution" | "monitor" | "contraindicated"
        }
    },
    "program_modifications": List[str],
    "medical_clearance_required": bool,
    "execution_time_ms": float
}
```

---

## 🍎 Phase 4: 营养整合工具

### 9. exercise_nutrition_optimization - 动作营养优化器

#### 功能描述
根据训练计划优化营养，基于Exercise.key_nutrients和recommended_foods。

#### 输入参数
```python
{
    "exercise_program": List[str],       # 训练计划的动作ID列表
    "training_schedule": Dict[str, Any]  # 训练时间表 (可选)
}
```

#### 输出格式
```python
{
    "tool": "ExerciseNutritionOptimizer",
    "status": "success",
    "exercise_nutrition_mapping": {
        str: {                          # exercise_id
            "exercise_name": str,
            "key_nutrients": List[str],
            "recommended_foods": List[str]
        }
    },
    "meal_timing_strategy": {
        "pre_workout": str,
        "during_workout": str,
        "post_workout": str,
        "general": str
    },
    "nutrition_summary": {
        "total_key_nutrients": List[str],
        "focus_nutrients": List[str],
        "dietary_emphasis": List[str]
    },
    "execution_time_ms": float
}
```

---

### 10. muscle_recovery_nutrition - 肌肉恢复营养工具

#### 功能描述
基于Muscle恢复时间制定营养计划，使用Muscle-Nutrient关系。

#### 输入参数
```python
{
    "target_muscles": List[str],         # 目标肌群列表
    "training_frequency": str,           # 训练频率
    "training_intensity": str            # 训练强度 ("low", "moderate", "high")
}
```

#### 输出格式
```python
{
    "tool": "MuscleRecoveryNutrition",
    "status": "success",
    "recovery_plan": {
        str: {                          # muscle_name
            "recovery_time_hours": int,
            "key_nutrients": List[str],
            "supplementation_suggestions": List[str]
        }
    },
    "meal_timing": {
        "immediate_post_workout": str,
        "within_2_hours": str,
        "throughout_day": str,
        "before_bed": str
    },
    "nutritional_priorities": List[str],
    "execution_time_ms": float
}
```

---

## 📊 Phase 5: 数据洞察工具

### 11. training_analytics_dashboard - 训练分析仪表板

#### 功能描述
综合训练数据分析，提供进度指标和改进建议。

#### 输入参数
```python
{
    "exercise_history": List[Dict],      # 训练历史记录
    "user_goals": List[str],             # 用户目标
    "current_level": str                 # 当前水平 ("beginner", "intermediate", "advanced")
}
```

#### 输出格式
```python
{
    "tool": "TrainingAnalyticsDashboard",
    "status": "success",
    "progress_metrics": {
        "training_consistency": float,
        "volume_progression": float,
        "goal_alignment": float,
        "overall_progress": float
    },
    "improvement_recommendations": List[str],
    "risk_alerts": List[str],
    "analytics_summary": {
        "total_sessions": int,
        "training_frequency": float,
        "volume_trend": str,
        "goal_alignment": float,
        "consistency_score": float
    },
    "execution_time_ms": float
}
```

---

### 12. evidence_based_recommender - 循证推荐器

#### 功能描述
基于证据等级推荐，权衡科学严谨性和实用性。使用Muscle.evidence_level和reliability_score。

#### 输入参数
```python
{
    "query": str,                        # 查询内容
    "preference": str                    # 偏好 ("scientific_rigor", "practical_effectiveness", "balanced")
}
```

#### 输出格式
```python
{
    "tool": "EvidenceBasedRecommender",
    "status": "success",
    "recommendations": [
        {
            "type": str,
            "name": str,
            "evidence_level": int,
            "reliability_score": float,
            "scientific_support": str,
            "practical_applicability": str,
            "weight": float
        }
    ],
    "evidence_summary": {
        "high_evidence": int,
        "medium_evidence": int,
        "low_evidence": int,
        "overall_quality": str
    },
    "practical_notes": List[str],
    "research_limitations": List[str],
    "execution_time_ms": float
}
```

---

## 💡 最佳实践

### 1. 错误处理

#### 1.1 标准错误格式
所有工具都返回标准化的错误格式：
```python
{
    "tool": "ToolName",
    "status": "error",
    "error": str,                        # 错误信息
    "error_code": str,                   # 错误代码
    "execution_time_ms": float
}
```

#### 1.2 错误处理示例
```python
async def safe_tool_call(tool, params):
    """安全的工具调用，包含错误处理"""
    try:
        result = await tool.execute(params)
        
        if result["status"] == "error":
            logger.error(f"工具执行失败: {result['error']}")
            
            # 根据错误类型采取不同策略
            if "not found" in result["error"].lower():
                # 数据未找到，使用默认值
                return get_default_result()
            elif "timeout" in result["error"].lower():
                # 超时，重试一次
                logger.info("超时，重试中...")
                return await tool.execute(params)
            else:
                # 其他错误，返回错误信息
                return result
        
        return result
        
    except Exception as e:
        logger.exception(f"工具调用异常: {e}")
        return {
            "tool": tool.__class__.__name__,
            "status": "error",
            "error": str(e),
            "error_code": "EXCEPTION",
            "execution_time_ms": 0
        }
```

#### 1.3 常见错误类型

| 错误代码 | 说明 | 处理建议 |
|---------|------|---------|
| `INVALID_PARAMS` | 参数验证失败 | 检查输入参数格式和类型 |
| `NOT_FOUND` | 数据未找到 | 使用默认值或提示用户 |
| `DATABASE_ERROR` | 数据库查询失败 | 重试或使用缓存数据 |
| `TIMEOUT` | 执行超时 | 重试或降低查询复杂度 |
| `PERMISSION_DENIED` | 权限不足 | 检查用户权限 |
| `RATE_LIMIT` | 请求频率过高 | 实现限流和重试机制 |

#### 1.4 错误恢复策略
```python
class ErrorRecoveryStrategy:
    """错误恢复策略"""
    
    @staticmethod
    async def retry_with_backoff(tool, params, max_retries=3):
        """指数退避重试"""
        for attempt in range(max_retries):
            try:
                result = await tool.execute(params)
                if result["status"] == "success":
                    return result
                
                # 等待时间：2^attempt 秒
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return {"status": "error", "error": "Max retries exceeded"}
    
    @staticmethod
    async def fallback_to_cache(tool, params, cache_client):
        """降级到缓存"""
        try:
            result = await tool.execute(params)
            if result["status"] == "success":
                # 成功，更新缓存
                await cache_client.set(params, result)
                return result
        except Exception:
            pass
        
        # 失败，使用缓存
        cached = await cache_client.get(params)
        if cached:
            logger.warning("使用缓存数据")
            return cached
        
        return {"status": "error", "error": "No cache available"}
```

---

### 2. 性能优化

#### 2.1 参数优化
```python
# ✅ 好的做法：限制返回数量
result = await selector.execute({
    "muscle_group": "胸",
    "top_k": 10,              # 只返回前10个结果
    "min_score": 0.7          # 过滤低质量结果
})

# ❌ 不好的做法：返回所有结果
result = await selector.execute({
    "muscle_group": "胸"
    # 可能返回数百个结果，影响性能
})
```

#### 2.2 缓存策略
```python
class CachedToolWrapper:
    """带缓存的工具包装器"""
    
    def __init__(self, tool, cache_client, ttl=3600):
        self.tool = tool
        self.cache_client = cache_client
        self.ttl = ttl
    
    async def execute(self, params):
        # 生成缓存键
        cache_key = self._generate_cache_key(params)
        
        # 检查缓存
        cached = await self.cache_client.get(cache_key)
        if cached:
            logger.info(f"缓存命中: {cache_key}")
            return cached
        
        # 执行工具
        result = await self.tool.execute(params)
        
        # 存入缓存
        if result["status"] == "success":
            await self.cache_client.set(
                cache_key, 
                result, 
                ttl=self.ttl
            )
        
        return result
    
    def _generate_cache_key(self, params):
        """生成缓存键"""
        import hashlib
        import json
        
        # 排序参数以确保一致性
        sorted_params = json.dumps(params, sort_keys=True)
        hash_value = hashlib.md5(sorted_params.encode()).hexdigest()
        
        return f"{self.tool.__class__.__name__}:{hash_value}"
```

#### 2.3 批量处理
```python
async def batch_process_exercises(exercise_ids, tool):
    """批量处理动作"""
    # ✅ 好的做法：并发处理
    tasks = [
        tool.execute({"exercise_id": ex_id})
        for ex_id in exercise_ids
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理结果
    successful = []
    failed = []
    for result in results:
        if isinstance(result, Exception):
            failed.append(str(result))
        elif result["status"] == "success":
            successful.append(result)
        else:
            failed.append(result["error"])
    
    return {
        "successful": successful,
        "failed": failed,
        "success_rate": len(successful) / len(exercise_ids)
    }
```

#### 2.4 数据库查询优化
```python
# ✅ 好的做法：使用索引字段查询
result = await neo4j_client.query("""
    MATCH (e:Exercise)
    WHERE e.primary_muscle_zh = $muscle
    AND e.difficulty_level = $difficulty
    RETURN e
    LIMIT 20
""", muscle="胸大肌", difficulty="intermediate")

# ❌ 不好的做法：全表扫描
result = await neo4j_client.query("""
    MATCH (e:Exercise)
    WHERE e.name_zh CONTAINS $keyword
    RETURN e
""", keyword="卧推")  # 可能扫描所有Exercise节点
```

#### 2.5 性能监控
```python
class PerformanceMonitor:
    """性能监控"""
    
    def __init__(self):
        self.metrics = {}
    
    async def monitor_tool(self, tool, params):
        """监控工具执行"""
        import time
        
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            result = await tool.execute(params)
            
            elapsed_time = time.time() - start_time
            memory_used = self._get_memory_usage() - start_memory
            
            # 记录指标
            tool_name = tool.__class__.__name__
            if tool_name not in self.metrics:
                self.metrics[tool_name] = {
                    "calls": 0,
                    "total_time": 0,
                    "total_memory": 0,
                    "errors": 0
                }
            
            self.metrics[tool_name]["calls"] += 1
            self.metrics[tool_name]["total_time"] += elapsed_time
            self.metrics[tool_name]["total_memory"] += memory_used
            
            if result["status"] == "error":
                self.metrics[tool_name]["errors"] += 1
            
            # 性能告警
            if elapsed_time > 1.0:  # 超过1秒
                logger.warning(
                    f"工具执行缓慢: {tool_name} "
                    f"耗时 {elapsed_time:.2f}s"
                )
            
            return result
            
        except Exception as e:
            self.metrics[tool_name]["errors"] += 1
            raise
    
    def _get_memory_usage(self):
        """获取内存使用量"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
    
    def get_report(self):
        """生成性能报告"""
        report = []
        for tool_name, metrics in self.metrics.items():
            avg_time = metrics["total_time"] / metrics["calls"]
            avg_memory = metrics["total_memory"] / metrics["calls"]
            error_rate = metrics["errors"] / metrics["calls"]
            
            report.append({
                "tool": tool_name,
                "calls": metrics["calls"],
                "avg_time_ms": avg_time * 1000,
                "avg_memory_mb": avg_memory,
                "error_rate": error_rate
            })
        
        return sorted(report, key=lambda x: x["avg_time_ms"], reverse=True)
```

---

### 3. 安全考虑

#### 3.1 输入验证
```python
from pydantic import BaseModel, validator, Field
from typing import List, Optional

class ExerciseSelectorParams(BaseModel):
    """动作选择器参数验证"""
    
    muscle_group: str = Field(..., min_length=1, max_length=50)
    available_equipment: List[str] = Field(default_factory=list)
    difficulty_level: str = Field(..., regex="^(beginner|intermediate|advanced)$")
    training_goal: str = Field(..., regex="^(strength|hypertrophy|endurance|general_fitness)$")
    injury_history: Optional[List[str]] = Field(default_factory=list)
    top_k: int = Field(default=20, ge=1, le=100)
    
    @validator("available_equipment")
    def validate_equipment(cls, v):
        """验证器械列表"""
        allowed_equipment = [
            "哑铃", "杠铃", "固定器械", "自由重量",
            "弹力带", "壶铃", "TRX", "自重"
        ]
        for equipment in v:
            if equipment not in allowed_equipment:
                raise ValueError(f"不支持的器械: {equipment}")
        return v
    
    @validator("injury_history")
    def validate_injuries(cls, v):
        """验证损伤列表"""
        if len(v) > 10:
            raise ValueError("损伤列表过长")
        return v

# 使用示例
try:
    params = ExerciseSelectorParams(
        muscle_group="胸",
        available_equipment=["哑铃", "杠铃"],
        difficulty_level="intermediate",
        training_goal="hypertrophy"
    )
    result = await selector.execute(params.dict())
except ValidationError as e:
    logger.error(f"参数验证失败: {e}")
```

#### 3.2 权限控制
```python
class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    async def check_tool_permission(user_id: int, tool_name: str) -> bool:
        """检查工具使用权限"""
        # 检查用户会员等级
        user = await get_user(user_id)
        
        # 高级工具需要会员权限
        premium_tools = [
            "periodized_program_designer",
            "evidence_based_recommender",
            "training_analytics_dashboard"
        ]
        
        if tool_name in premium_tools and not user.is_premium:
            return False
        
        return True
    
    @staticmethod
    async def check_rate_limit(user_id: int, tool_name: str) -> bool:
        """检查请求频率限制"""
        # 免费用户：每小时10次
        # 会员用户：每小时100次
        user = await get_user(user_id)
        limit = 100 if user.is_premium else 10
        
        # 检查Redis计数器
        key = f"rate_limit:{user_id}:{tool_name}"
        count = await redis_client.incr(key)
        
        if count == 1:
            await redis_client.expire(key, 3600)  # 1小时过期
        
        return count <= limit
```

#### 3.3 数据脱敏
```python
def sanitize_user_data(user_profile: dict) -> dict:
    """脱敏用户数据"""
    sensitive_fields = [
        "phone", "email", "id_card", 
        "medical_records", "payment_info"
    ]
    
    sanitized = user_profile.copy()
    for field in sensitive_fields:
        if field in sanitized:
            # 移除敏感字段
            del sanitized[field]
    
    # 脱敏姓名
    if "name" in sanitized:
        name = sanitized["name"]
        if len(name) > 1:
            sanitized["name"] = name[0] + "*" * (len(name) - 1)
    
    return sanitized
```

---

### 4. 集成建议

#### 4.1 直接调用
```python
# 单个工具调用
tool = IntelligentExerciseSelector(neo4j_client)
result = await tool.execute({
    "muscle_group": "胸",
    "available_equipment": ["哑铃", "杠铃"],
    "difficulty_level": "intermediate",
    "training_goal": "hypertrophy"
})
```

#### 4.2 DAG编排集成
```python
# 集成到工作流
orchestrator = FitnessDAGOrchestrator()

# 注册工具为DAG节点
orchestrator.register_task(
    task_id="select_exercises",
    task_func=selector.execute,
    dependencies=["load_user_profile"]
)

orchestrator.register_task(
    task_id="check_contraindications",
    task_func=contraindications_checker.execute,
    dependencies=["select_exercises"]
)

# 执行DAG
result = await orchestrator.execute_fitness_template(
    template_id="complete_training_plan",
    user_profile=user_profile
)
```

#### 4.3 批量处理
```python
# 并发处理多个工具
async def process_training_plan(user_profile):
    """处理训练计划"""
    
    # 并发执行多个工具
    tasks = {
        "exercises": selector.execute({
            "muscle_group": "胸",
            "user_profile": user_profile
        }),
        "volume": volume_calculator.execute({
            "muscle_group": "胸大肌",
            "training_frequency": "2-3次",
            "training_goal": "hypertrophy"
        }),
        "nutrition": nutrition_optimizer.execute({
            "exercise_program": ["ex_001", "ex_002"],
            "training_schedule": {}
        })
    }
    
    # 等待所有任务完成
    results = await asyncio.gather(
        *tasks.values(),
        return_exceptions=True
    )
    
    # 组合结果
    return {
        key: result
        for key, result in zip(tasks.keys(), results)
        if not isinstance(result, Exception)
    }
```

#### 4.4 流式处理
```python
async def stream_training_plan(user_profile):
    """流式生成训练计划"""
    
    # 步骤1：选择动作
    yield {"step": "selecting_exercises", "progress": 0.2}
    exercises = await selector.execute({...})
    
    # 步骤2：检查禁忌症
    yield {"step": "checking_safety", "progress": 0.4}
    safety = await contraindications_checker.execute({...})
    
    # 步骤3：计算训练量
    yield {"step": "calculating_volume", "progress": 0.6}
    volume = await volume_calculator.execute({...})
    
    # 步骤4：优化营养
    yield {"step": "optimizing_nutrition", "progress": 0.8}
    nutrition = await nutrition_optimizer.execute({...})
    
    # 步骤5：生成计划
    yield {
        "step": "complete",
        "progress": 1.0,
        "result": {
            "exercises": exercises,
            "safety": safety,
            "volume": volume,
            "nutrition": nutrition
        }
    }
```

---

---

## 📊 15个Python MCP工具完整列表

### 基础数据工具 (5个)

| 工具名称 | 功能描述 | 主要输入 | 主要输出 |
|---------|---------|---------|---------|
| **tdee_calculator** | TDEE计算器 | 年龄、性别、体重、身高、活动水平 | TDEE、BMR、热量建议 |
| **assess_strength_level** | 力量水平评估器 | 用户档案、1RM数据 | 力量等级、进步建议 |
| **training_split_designer** | 训练分化设计器 | 训练频率、目标、经验水平 | 训练分化方案 |
| **movement_pattern_balancer** | 动作模式平衡器 | 当前计划、目标肌群 | 平衡分析、调整建议 |
| **get_user_profile** | 用户档案工具 | 用户ID | 完整用户档案 |

### 安全工具 (3个)

| 工具名称 | 功能描述 | 主要输入 | 主要输出 |
|---------|---------|---------|---------|
| **contraindications_checker** | 禁忌症检查器 | 用户条件、拟议动作 | 兼容性矩阵、修改建议 |
| **injury_risk_assessor** | 损伤风险评估器 | 动作ID、用户档案 | 风险等级、监控指导 |
| **safe_exercise_modifier** | 安全动作修改器 | 动作ID、损伤类型 | 安全替代方案 |

### 动作工具 (4个)

| 工具名称 | 功能描述 | 主要输入 | 主要输出 |
|---------|---------|---------|---------|
| **intelligent_exercise_selector** | 智能动作选择器 | 肌群、器械、难度、目标 | 推荐动作列表 |
| **exercise_alternative_finder** | 动作替代查找器 | 动作ID、替代原因 | 替代动作列表 |
| **intelligent_weight_calculator** | 智能重量计算器 | 动作ID、用户水平、目标 | 推荐重量、组数、次数 |
| **exercise_similarity_finder** | 动作相似度查找器 | 动作ID、相似度类型 | 相似动作列表 |

### 训练规划工具 (5个)

| 工具名称 | 功能描述 | 主要输入 | 主要输出 |
|---------|---------|---------|---------|
| **professional_program_designer** | 专业计划设计器 | 用户档案、目标、周期 | 完整训练计划 |
| **periodized_program_designer** | 周期化程序设计器 | 用户水平、目标、周数 | 周期化计划 |
| **muscle_group_volume_calculator** | 肌群训练量计算器 | 肌群、频率、目标 | 训练量建议 |
| **training_analytics_dashboard** | 训练分析仪表板 | 训练历史、目标 | 进度指标、改进建议 |
| **evidence_based_recommender** | 循证推荐器 | 查询、偏好 | 循证推荐列表 |

### 营养工具 (5个)

| 工具名称 | 功能描述 | 主要输入 | 主要输出 |
|---------|---------|---------|---------|
| **nutrition_intake_analyzer** | 营养摄入分析器 | 饮食记录、目标 | 营养分析、建议 |
| **meal_plan_designer** | 膳食计划设计器 | TDEE、目标、偏好 | 膳食计划 |
| **exercise_nutrition_optimization** | 动作营养优化器 | 训练计划、时间表 | 营养时机策略 |
| **muscle_recovery_nutrition** | 肌肉恢复营养工具 | 目标肌群、训练强度 | 恢复营养计划 |
| **nutrition_timing_optimizer** | 营养时机优化器 | 训练时间、目标 | 营养时机建议 |

---

## 🔄 MCP工具部署说明

### 集成部署架构

所有16个MCP工具（15个Python工具 + 1个用户档案工具）都集成部署在DAML-RAG容器内：

```
Docker容器: fitness_daml_rag
├── DAML-RAG服务 (端口8001)
├── 15个Python MCP工具
│   └── 直接调用Neo4j/Qdrant/MySQL
└── 用户档案MCP
    └── 直接调用Laravel后端API
```

### 部署优势

1. **性能优化**
   - ✅ 无网络开销
   - ✅ 直接内存访问
   - ✅ 响应时间<50ms

2. **简化部署**
   - ✅ 单容器部署
   - ✅ 统一管理
   - ✅ 降低运维复杂度

3. **资源优化**
   - ✅ 节省容器资源
   - ✅ 共享数据库连接池
   - ✅ 统一缓存管理

### 调用方式

```python
# 方式1：通过DAG编排器调用
orchestrator = FitnessDAGOrchestrator()
result = await orchestrator.execute_fitness_template(
    template_id="complete_training_plan",
    user_profile=user_profile
)

# 方式2：直接调用工具
tool = IntelligentExerciseSelector(neo4j_client)
result = await tool.execute({
    "muscle_group": "胸",
    "available_equipment": ["哑铃", "杠铃"],
    "difficulty_level": "intermediate"
})

# 方式3：通过MCP客户端调用
mcp_client = MCPClientPool()
result = await mcp_client.call_tool(
    server_name="fitness_tools",
    tool_name="intelligent_exercise_selector",
    arguments={...}
)
```

---

## 📝 维护者

**维护者**: 薛小川
**创建日期**: 2025-12-01
**更新日期**: 2025-12-16
**版本**: v2.0.0
**状态**: ✅ 已完成 · 15个Python MCP工具 + 用户档案MCP

**变更记录**:
- v2.0.0 (2025-12-16): 添加15个Python MCP工具和用户档案MCP的完整说明
- v1.0.0 (2025-12-01): 初始版本，12个MCP工具
