# Training工具实现

**版本**: v2.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本文档详细说明Training分类下的8个MCP工具实现，涵盖重量计算、容量管理、计划设计等核心训练功能。

**代码路径**: `daml-rag-server/src/applications/fitness/mcp_tools/training/`

---

## 1. intelligent_weight_calculator - 智能重量计算器

**功能说明**: 基于用户1RM、训练目标和RPE智能计算训练重量

**代码路径**: `training/intelligent_weight_calculator.py`

**优先级**: P1建议工具

### 输入Schema

```python
class IntelligentWeightCalculatorInput(BaseModel):
    user_id: str = Field(..., description="用户ID")
    exercise_id: str = Field(..., description="动作ID")
    training_goal: TrainingGoal = Field(..., description="训练目标")
    reps_target: int = Field(..., description="目标重复次数", ge=1, le=30)
    rpe_target: float = Field(..., description="目标RPE (1-10)", ge=1, le=10)
    user_level: Optional[UserLevel] = Field(UserLevel.INTERMEDIATE, description="用户水平")
```

### 输出Schema

```python
class IntelligentWeightCalculatorOutput(BaseModel):
    success: bool
    tool_name: str
    calculation: WeightCalculation
    adjustments: WeightAdjustments
    safety_considerations: List[str]
    progression_guidelines: List[str]
    execution_time_ms: float
    confidence_score: Optional[float] = None
```

### 重量计算逻辑

```python
def _calculate_recommended_weight(
    self,
    base_1rm: float,
    reps_target: int,
    rpe_target: float,
    adjustments: Dict[str, float],
    training_goal: str
) -> Dict[str, Any]:
    """计算推荐重量"""
    # 使用RPE表和反推公式
    rpe_percentage = self._get_rpe_percentage(rpe_target)
    
    # 根据目标重复次数调整
    reps_adjustment = self._get_reps_adjustment(reps_target, training_goal)
    
    # 计算推荐1RM
    adjusted_1rm = base_1rm * adjustments["total_adjustment"]
    
    # 计算推荐重量
    recommended_weight = adjusted_1rm * rpe_percentage * reps_adjustment
    
    # 重量范围（±5%）
    weight_range = (
        round(recommended_weight * 0.95, 1),
        round(recommended_weight * 1.05, 1)
    )
    
    return {
        "recommended_weight": round(recommended_weight, 1),
        "weight_range": weight_range,
        "reps_1rm_estimate": round(adjusted_1rm, 1),
        "percentage_of_1rm": round(rpe_percentage * 100, 1),
        "rpe_correlation": rpe_target
    }

def _get_rpe_percentage(self, rpe: float) -> float:
    """获取RPE百分比"""
    rpe_table = {
        10.0: 1.0,
        9.5: 0.975,
        9.0: 0.95,
        8.5: 0.925,
        8.0: 0.90,
        7.5: 0.875,
        7.0: 0.85,
        6.5: 0.825,
        6.0: 0.80
    }
    rounded_rpe = round(rpe * 2) / 2
    return rpe_table.get(rounded_rpe, 0.85)
```

### 训练目标调整

```python
def _calculate_adjustments(
    self, user_level: str, training_goal: str, rpe_target: float
) -> Dict[str, float]:
    """计算调整因子（基于力量标准的百分比）"""
    # 水平调整
    level_adjustments = {
        "beginner": 0.7,
        "intermediate": 1.0,
        "advanced": 1.3
    }
    level_adjustment = level_adjustments.get(user_level, 1.0)
    
    # 目标调整（基于力量标准的百分比）
    goal_adjustments = {
        "strength": 0.90,      # 力量训练：85-95%，中位数90%
        "hypertrophy": 0.70,   # 增肌训练：60-80%，中位数70%
        "endurance": 0.50,     # 耐力训练：40-60%，中位数50%
        "general_fitness": 0.70  # 一般健身：65-75%，中位数70%
    }
    goal_adjustment = goal_adjustments.get(training_goal, 0.70)
    
    # 疲劳调整（RPE影响）
    fatigue_adjustment = max(0.5, 1 - (rpe_target - 6) * 0.1)
    
    # 总调整因子
    total_adjustment = level_adjustment * goal_adjustment * fatigue_adjustment
    
    return {
        "level_adjustment": level_adjustment,
        "goal_adjustment": goal_adjustment,
        "fatigue_adjustment": fatigue_adjustment,
        "total_adjustment": total_adjustment
    }
```

---

## 2. muscle_group_volume_calculator - 肌群容量计算器

**功能说明**: 计算每周肌群训练容量，确保训练量适宜

**代码路径**: `training/muscle_group_volume_calculator.py`

**优先级**: P0核心工具

### 输入Schema

```python
class MuscleGroupVolumeCalculatorInput(BaseModel):
    user_id: str = Field(..., description="用户ID")
    training_plan: List[Dict[str, Any]] = Field(..., description="训练计划")
    target_muscle_groups: Optional[List[str]] = Field(None, description="目标肌群")
```

### 容量计算

```python
def _calculate_volume_per_muscle(
    self,
    training_plan: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """计算每个肌群的训练容量"""
    muscle_volumes = {}
    
    for session in training_plan:
        for exercise in session.get("exercises", []):
            # 获取动作激活的肌群
            muscles = exercise.get("primary_muscles", []) + exercise.get("secondary_muscles", [])
            sets = exercise.get("sets", 3)
            reps = exercise.get("reps", 10)
            
            for muscle in muscles:
                if muscle not in muscle_volumes:
                    muscle_volumes[muscle] = {
                        "total_sets": 0,
                        "total_reps": 0,
                        "exercises": []
                    }
                
                muscle_volumes[muscle]["total_sets"] += sets
                muscle_volumes[muscle]["total_reps"] += sets * reps
                muscle_volumes[muscle]["exercises"].append(exercise["name"])
    
    return muscle_volumes
```

---

## 3. professional_program_designer - 专业计划设计器

**功能说明**: 基于用户目标和水平设计完整训练计划

**代码路径**: `training/professional_program_designer.py`

**优先级**: P1建议工具

### 计划生成流程

```python
async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行专业计划设计"""
    # 1. 分析用户档案
    user_profile = await self._analyze_user_profile(input_data["user_id"])
    
    # 2. 确定训练分化
    split_type = self._determine_training_split(
        user_profile,
        input_data["training_goal"],
        input_data["days_per_week"]
    )
    
    # 3. 选择动作
    exercises = await self._select_exercises_for_split(
        split_type,
        user_profile,
        input_data
    )
    
    # 4. 计算训练参数
    program = self._calculate_training_parameters(
        exercises,
        user_profile,
        input_data["training_goal"]
    )
    
    # 5. 添加周期化
    periodized_program = self._add_periodization(
        program,
        input_data.get("program_duration_weeks", 12)
    )
    
    return {
        "success": True,
        "program": periodized_program,
        "split_type": split_type,
        "reasoning": self._generate_program_reasoning(periodized_program)
    }
```

---

## 4. movement_pattern_balancer - 动作模式平衡器

**功能说明**: 确保训练计划中动作模式的平衡

**代码路径**: `training/movement_pattern_balancer.py`

**优先级**: P1建议工具

### 动作模式分析

```python
def _analyze_movement_patterns(
    self,
    exercises: List[Dict[str, Any]]
) -> Dict[str, int]:
    """分析动作模式分布"""
    pattern_counts = {
        "推": 0,
        "拉": 0,
        "蹲": 0,
        "髋铰链": 0,
        "核心": 0,
        "单侧": 0
    }
    
    for exercise in exercises:
        pattern = exercise.get("movement_pattern_zh", "")
        if pattern in pattern_counts:
            pattern_counts[pattern] += 1
    
    return pattern_counts

def _check_balance(
    self,
    pattern_counts: Dict[str, int]
) -> Dict[str, Any]:
    """检查动作模式平衡"""
    total = sum(pattern_counts.values())
    if total == 0:
        return {"balanced": False, "issues": ["没有动作"]}
    
    issues = []
    
    # 推拉比例应接近1:1
    push_count = pattern_counts.get("推", 0)
    pull_count = pattern_counts.get("拉", 0)
    if push_count > 0 and pull_count > 0:
        ratio = push_count / pull_count
        if ratio > 1.5 or ratio < 0.67:
            issues.append(f"推拉比例失衡: {push_count}:{pull_count}")
    
    # 下肢动作应占30-40%
    lower_body = pattern_counts.get("蹲", 0) + pattern_counts.get("髋铰链", 0)
    lower_percentage = (lower_body / total) * 100
    if lower_percentage < 25 or lower_percentage > 45:
        issues.append(f"下肢动作比例不当: {lower_percentage:.1f}%")
    
    return {
        "balanced": len(issues) == 0,
        "issues": issues,
        "pattern_distribution": pattern_counts
    }
```

---

## 5-8. 其他Training工具

### 5. periodized_program_designer - 周期化计划设计器
**代码路径**: `training/periodized_program_designer.py`  
**优先级**: P2扩展工具  
**功能**: 设计包含准备期、积累期、强化期的周期化训练计划

### 6. training_split_designer - 训练分化设计器
**代码路径**: `training/training_split_designer.py`  
**优先级**: P2扩展工具  
**功能**: 根据训练频率设计最优训练分化（全身/上下肢/推拉腿等）

### 7. record_training_feedback - 训练反馈记录
**代码路径**: `training/record_training_feedback.py`
**优先级**: P1建议工具
**功能**: 记录训练反馈，用于Few-Shot学习和质量评分

### 输入Schema

```python
class TrainingRecord(BaseModel):
    """单条训练记录"""
    exercise_name: str = Field(..., description="动作名称")
    sets: int = Field(..., ge=1, description="组数")
    reps: int = Field(..., ge=1, description="次数")
    weight: float = Field(..., ge=0, description="重量（kg）")
    notes: Optional[str] = Field(None, description="备注")


class RecordTrainingFeedbackInput(BaseModel):
    """训练反馈记录输入"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="训练会话ID")
    fatigue_level: int = Field(..., ge=1, le=10, description="疲劳程度（1-10分）")
    subjective_feeling: str = Field(..., description="主观感受（文本描述）")
    training_records: List[TrainingRecord] = Field(..., min_length=1, description="训练记录列表")
    date: Optional[str] = Field(None, description="日期（ISO 8601格式，默认今天）")
```

### 输出Schema

```python
class RecordTrainingFeedbackOutput(BaseModel):
    """训练反馈记录输出"""
    success: bool = Field(..., description="是否成功")
    tool_name: str = Field(..., description="工具名称")
    data: Dict[str, Any] = Field(..., description="反馈记录数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
```

### 功能特点

1. **简单存储**: 只负责存储反馈数据，不进行自动评估
2. **前端驱动**: 数据由前端训练记录界面收集
3. **历史追踪**: 支持查询历史反馈记录

### 数据流向

```python
async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行训练反馈记录"""
    user_id = input_data["user_id"]
    session_id = input_data["session_id"]
    fatigue_level = input_data["fatigue_level"]
    subjective_feeling = input_data["subjective_feeling"]
    training_records = input_data["training_records"]
    date = input_data.get("date") or datetime.now().isoformat()

    # 构建反馈记录
    feedback_record = {
        "session_id": session_id,
        "date": date,
        "fatigue_level": fatigue_level,
        "subjective_feeling": subjective_feeling,
        "training_records": training_records,
        "created_at": datetime.now().isoformat()
    }

    # 注意：实际存储需要通过MCP客户端调用 update_user_profile
    # 这里先返回成功，实际存储逻辑由MCPToolManager处理

    return {
        "success": True,
        "tool_name": self.get_name(),
        "data": {
            "feedback_record": feedback_record,
            "user_id": user_id,
            "message": "训练反馈记录成功"
        }
    }
```

---

## 8. safe_exercise_modifier - 安全动作修改器
**代码路径**: `training/safe_exercise_modifier.py`  
**优先级**: P1建议工具  
**功能**: 根据用户限制修改动作参数（重量、幅度、速度）

---

## 相关链接

- **基础架构**: [02-基础架构与工具注册.md](./02-基础架构与工具注册.md)
- **Exercise工具**: [03-Exercise工具实现.md](./03-Exercise工具实现.md)
- **Safety工具**: [05-Safety工具实现.md](./05-Safety工具实现.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
