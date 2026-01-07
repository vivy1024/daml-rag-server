# DAG模板代码实现

**版本**: v1.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 📋 概述

本文档详细说明DAML-RAG系统中9个预定义DAG模板的代码实现，包括：
- 模板定义数据结构
- 任务节点配置
- 依赖关系管理
- 并行执行优化
- 模板验证机制

**核心文件**：
- `src/applications/fitness/dag_template_system.py` - DAG模板系统
- `src/applications/fitness/enhanced_dag_orchestrator.py` - DAG编排器
- `src/applications/fitness/workflow_executor.py` - 工作流程执行器

---

## 🏗️ 核心数据结构

### 1. DAGTemplate类

```python
@dataclass
class DAGTemplate:
    """DAG模板定义"""
    template_id: str                                    # 模板唯一标识
    name: str                                           # 模板名称
    description: str                                    # 模板描述
    category: TemplateCategory                          # 模板类别
    applicable_intents: List[str]                       # 适用意图列表
    required_tools: List[str]                           # 必需工具列表
    optional_tools: List[str] = field(default_factory=list)  # 可选工具列表
    tool_dependencies: Dict[str, List[str]] = field(default_factory=dict)  # 工具依赖关系
    parallel_groups: List[List[str]] = field(default_factory=list)  # 并行执行组
    expected_output: Dict[str, str] = field(default_factory=dict)  # 预期输出
    safety_constraints: List[str] = field(default_factory=list)  # 安全约束
    estimated_duration_seconds: float = 10.0            # 预估执行时长
    complexity_level: int = 1                           # 复杂度等级(1-3)
    success_rate: float = 0.95                          # 成功率
    response_hint: str = ""                             # LLM响应提示
```

### 2. TemplateCategory枚举

```python
class TemplateCategory(Enum):
    """模板类别"""
    TRAINING = "training"           # 训练相关
    NUTRITION = "nutrition"         # 营养相关
    SAFETY = "safety"              # 安全评估
    COMPREHENSIVE = "comprehensive" # 综合方案
    QUICK = "quick"                # 快速咨询
```

---

## 📦 9个预定义模板

### 模板0: 问候闲聊 (greeting)

**适用场景**: 用户问候、简单闲聊

**代码实现**:
```python
self.templates["greeting"] = DAGTemplate(
    template_id="greeting",
    name="问候闲聊",
    description="友好回应用户的问候和简单闲聊",
    category=TemplateCategory.QUICK,
    applicable_intents=[
        "你好", "早上好", "晚上好", "hi", "hello", 
        "嗨", "在吗", "闲聊", "问候"
    ],
    required_tools=[],  # 不需要调用任何工具
    optional_tools=[],
    tool_dependencies={},
    parallel_groups=[],
    expected_output={
        "greeting_response": "简短友好的问候回应"
    },
    safety_constraints=[],
    estimated_duration_seconds=1.0,
    complexity_level=1,
    response_hint="简短友好，1-2句话，不要提供训练建议"
)
```

**特点**:
- 无需调用MCP工具
- 最快响应（1秒）
- 最低复杂度

---

### 模板1: 完整训练计划 (complete_training_plan)

**适用场景**: 制定包含动作选择、训练量计算、周期化安排的完整训练计划

**必需工具**:
1. `get_user_profile` - 获取用户档案
2. `contraindications_checker` - 禁忌症检查
3. `injury_risk_assessor` - 损伤风险评估
4. `intelligent_exercise_selector` - 智能动作选择
5. `muscle_group_volume_calculator` - 肌群训练量计算
6. `professional_program_designer` - 专业计划设计

**可选工具**:
- `movement_pattern_balancer` - 动作模式平衡
- `periodized_program_designer` - 周期化设计
- `training_split_designer` - 训练分化设计

**依赖关系**:
```python
tool_dependencies={
    "get_user_profile": [],
    "contraindications_checker": ["get_user_profile"],
    "injury_risk_assessor": ["get_user_profile"],
    "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor"],
    "muscle_group_volume_calculator": ["get_user_profile"],
    "movement_pattern_balancer": ["get_user_profile"],
    "professional_program_designer": ["intelligent_exercise_selector", "muscle_group_volume_calculator"],
    "periodized_program_designer": ["professional_program_designer"],
    "training_split_designer": ["professional_program_designer"]
}
```

**并行执行组**:
```python
parallel_groups=[
    ["get_user_profile"],
    ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator", "movement_pattern_balancer"],
    ["intelligent_exercise_selector"],
    ["professional_program_designer"],
    ["periodized_program_designer", "training_split_designer"]
]
```

**执行流程**:
1. **Level 0**: 加载用户档案
2. **Level 1**: 并行执行安全检查和训练量计算
3. **Level 2**: 基于安全评估选择动作
4. **Level 3**: 设计专业训练计划
5. **Level 4**: 并行生成周期化和分化方案

**特点**:
- 最高复杂度（Level 3）
- 预估15秒执行时长
- 5层并行优化
- 严格安全约束

---

### 模板2: 营养规划 (nutrition_planning)

**适用场景**: 基于用户目标和训练计划制定完整的营养方案

**必需工具**:
1. `get_user_profile` - 获取用户档案
2. `tdee_calculator` - TDEE计算
3. `nutrition_intake_analyzer` - 营养摄入分析
4. `meal_plan_designer` - 膳食计划设计

**可选工具**:
- `exercise_nutrition_optimization` - 运动营养优化

**依赖关系**:
```python
tool_dependencies={
    "get_user_profile": [],
    "tdee_calculator": ["get_user_profile"],
    "nutrition_intake_analyzer": ["tdee_calculator"],
    "meal_plan_designer": ["tdee_calculator", "nutrition_intake_analyzer"],
    "exercise_nutrition_optimization": ["meal_plan_designer"]
}
```

**并行执行组**:
```python
parallel_groups=[
    ["get_user_profile"],
    ["tdee_calculator"],
    ["nutrition_intake_analyzer"],
    ["meal_plan_designer"],
    ["exercise_nutrition_optimization"]
]
```

**特点**:
- 中等复杂度（Level 2）
- 预估10秒执行时长
- 5层顺序执行（营养计算需要前置结果）

---

### 模板3: 安全评估 (safety_assessment)

**适用场景**: 全面评估用户的运动安全性，识别风险和禁忌

**必需工具**:
1. `get_user_profile` - 获取用户档案
2. `contraindications_checker` - 禁忌症检查
3. `injury_risk_assessor` - 损伤风险评估

**可选工具**:
- `safe_exercise_modifier` - 安全动作调整
- `exercise_alternative_finder` - 替代动作查找

**依赖关系**:
```python
tool_dependencies={
    "get_user_profile": [],
    "contraindications_checker": ["get_user_profile"],
    "injury_risk_assessor": ["get_user_profile"],
    "safe_exercise_modifier": ["injury_risk_assessor"],
    "exercise_alternative_finder": ["contraindications_checker"]
}
```

**并行执行组**:
```python
parallel_groups=[
    ["get_user_profile"],
    ["contraindications_checker", "injury_risk_assessor"],
    ["safe_exercise_modifier", "exercise_alternative_finder"]
]
```

**特点**:
- 中等复杂度（Level 2）
- 预估8秒执行时长
- 3层并行优化
- 严格安全约束

---

### 模板4: 动作优化 (exercise_optimization)

**适用场景**: 优化训练动作选择，提供替代方案和安全调整

**必需工具**:
1. `get_user_profile` - 获取用户档案
2. `intelligent_exercise_selector` - 智能动作选择
3. `exercise_alternative_finder` - 替代动作查找

**可选工具**:
- `contraindications_checker` - 禁忌症检查
- `safe_exercise_modifier` - 安全动作调整
- `movement_pattern_balancer` - 动作模式平衡
- `intelligent_weight_calculator` - 智能重量计算

**依赖关系**:
```python
tool_dependencies={
    "get_user_profile": [],
    "contraindications_checker": ["get_user_profile"],
    "intelligent_exercise_selector": ["get_user_profile"],
    "exercise_alternative_finder": ["intelligent_exercise_selector"],
    "safe_exercise_modifier": ["intelligent_exercise_selector"],
    "movement_pattern_balancer": ["intelligent_exercise_selector"],
    "intelligent_weight_calculator": ["intelligent_exercise_selector"]
}
```

**并行执行组**:
```python
parallel_groups=[
    ["get_user_profile"],
    ["contraindications_checker", "intelligent_exercise_selector"],
    ["exercise_alternative_finder", "safe_exercise_modifier", "movement_pattern_balancer"],
    ["intelligent_weight_calculator"]
]
```

**特点**:
- 低复杂度（Level 1）
- 预估6秒执行时长
- 4层并行优化

---

### 模板5: 综合健身方案 (comprehensive_fitness)

**适用场景**: 包含训练、营养、安全的完整健身解决方案

**必需工具**:
1. `get_user_profile` - 获取用户档案
2. `contraindications_checker` - 禁忌症检查
3. `injury_risk_assessor` - 损伤风险评估
4. `intelligent_exercise_selector` - 智能动作选择
5. `muscle_group_volume_calculator` - 肌群训练量计算
6. `professional_program_designer` - 专业计划设计
7. `tdee_calculator` - TDEE计算
8. `meal_plan_designer` - 膳食计划设计

**可选工具**:
- `periodized_program_designer` - 周期化设计
- `training_split_designer` - 训练分化设计
- `exercise_nutrition_optimization` - 运动营养优化

**并行执行组**:
```python
parallel_groups=[
    ["get_user_profile"],
    ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator", "tdee_calculator"],
    ["intelligent_exercise_selector"],
    ["professional_program_designer"],
    ["meal_plan_designer", "periodized_program_designer", "training_split_designer"],
    ["exercise_nutrition_optimization"]
]
```

**特点**:
- 最高复杂度（Level 3）
- 预估20秒执行时长
- 6层并行优化
- 训练和营养协调

---

### 模板6: 快速咨询 (quick_consultation)

**适用场景**: 快速回答简单的健身问题

**必需工具**:
1. `get_user_profile` - 获取用户档案

**依赖关系**:
```python
tool_dependencies={
    "get_user_profile": []
}
```

**特点**:
- 最低复杂度（Level 1）
- 预估2秒执行时长
- 单工具执行

---

### 模板7: 进展分析 (progress_analysis)

**适用场景**: 分析用户训练进展，提供优化建议

**必需工具**:
1. `get_user_profile` - 获取用户档案
2. `muscle_group_volume_calculator` - 肌群训练量计算

**可选工具**:
- `periodized_program_designer` - 周期化设计

**依赖关系**:
```python
tool_dependencies={
    "get_user_profile": [],
    "muscle_group_volume_calculator": ["get_user_profile"],
    "periodized_program_designer": ["muscle_group_volume_calculator"]
}
```

**并行执行组**:
```python
parallel_groups=[
    ["get_user_profile"],
    ["muscle_group_volume_calculator"],
    ["periodized_program_designer"]
]
```

**特点**:
- 中等复杂度（Level 2）
- 预估8秒执行时长
- 数据驱动分析

---

### 模板8: 康复训练 (rehabilitation_training)

**适用场景**: 为有伤病史的用户制定安全的康复训练计划

**必需工具**:
1. `get_user_profile` - 获取用户档案
2. `contraindications_checker` - 禁忌症检查
3. `injury_risk_assessor` - 损伤风险评估
4. `safe_exercise_modifier` - 安全动作调整

**可选工具**:
- `exercise_alternative_finder` - 替代动作查找
- `intelligent_exercise_selector` - 智能动作选择
- `movement_pattern_balancer` - 动作模式平衡

**依赖关系**:
```python
tool_dependencies={
    "get_user_profile": [],
    "contraindications_checker": ["get_user_profile"],
    "injury_risk_assessor": ["get_user_profile"],
    "safe_exercise_modifier": ["injury_risk_assessor"],
    "exercise_alternative_finder": ["contraindications_checker"],
    "intelligent_exercise_selector": ["safe_exercise_modifier"],
    "movement_pattern_balancer": ["intelligent_exercise_selector"]
}
```

**并行执行组**:
```python
parallel_groups=[
    ["get_user_profile"],
    ["contraindications_checker", "injury_risk_assessor"],
    ["safe_exercise_modifier"],
    ["exercise_alternative_finder", "intelligent_exercise_selector"],
    ["movement_pattern_balancer"]
]
```

**特点**:
- 最高复杂度（Level 3）
- 预估12秒执行时长
- 5层执行
- 严格安全约束

---

## 🔧 模板管理器实现

### DAGTemplateManager类

```python
class DAGTemplateManager:
    """DAG模板管理器"""
    
    def __init__(self):
        self.templates: Dict[str, DAGTemplate] = {}
        self._initialize_templates()
        self._validate_all_templates()
    
    def get_template(self, template_id: str) -> Optional[DAGTemplate]:
        """获取指定模板"""
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> List[DAGTemplate]:
        """获取所有模板"""
        return list(self.templates.values())
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[DAGTemplate]:
        """按类别获取模板"""
        return [t for t in self.templates.values() if t.category == category]
```

### 模板验证

```python
def validate(self) -> bool:
    """验证模板完整性"""
    # 检查必需字段
    if not self.template_id or not self.name:
        logger.error(f"模板缺少必需字段: template_id或name")
        return False
    
    # 检查工具列表（greeting模板允许为空）
    if not self.required_tools and self.template_id != "greeting":
        logger.error(f"模板 {self.template_id} 缺少必需工具")
        return False
    
    # 检查依赖关系中的工具是否在工具列表中
    all_tools = set(self.required_tools + self.optional_tools)
    for tool, deps in self.tool_dependencies.items():
        if tool not in all_tools:
            logger.error(f"模板 {self.template_id} 依赖关系中的工具 {tool} 不在工具列表中")
            return False
        for dep in deps:
            if dep not in all_tools:
                logger.error(f"模板 {self.template_id} 工具 {tool} 的依赖 {dep} 不在工具列表中")
                return False
    
    # 检查并行组中的工具是否在工具列表中
    for group in self.parallel_groups:
        for tool in group:
            if tool not in all_tools:
                logger.error(f"模板 {self.template_id} 并行组中的工具 {tool} 不在工具列表中")
                return False
    
    return True
```

---

## 🚀 模板执行流程

### 1. 从模板构建DAG任务

```python
async def _build_dag_tasks_from_template(
    self,
    template: DAGTemplate,
    user_profile: Dict[str, Any],
    session_context: Dict[str, Any] = None
) -> List[DAGTask]:
    """从模板构建DAG任务列表"""
    tasks = []

    # 添加必需工具
    for tool_name in template.required_tools:
        # 将模板中的工具名（kebab-case）转换为注册表中的格式
        registry_tool_name = tool_name.replace('-', '_')
        
        if registry_tool_name in self.tool_metadata_registry:
            metadata = self.tool_metadata_registry[registry_tool_name]
            params = self._build_tool_params(registry_tool_name, user_profile, session_context)

            task = DAGTask(
                tool_name=registry_tool_name,
                tool_metadata=metadata,
                params=params,
                dependencies=[dep.replace('-', '_') for dep in template.tool_dependencies.get(tool_name, [])],
                priority=metadata.priority
            )
            tasks.append(task)

    # 根据模板复杂度和用户档案选择可选工具
    selected_optional_tools = self._select_optional_tools_from_template(
        template,
        user_profile
    )

    for tool_name in selected_optional_tools:
        registry_tool_name = tool_name.replace('-', '_')
        
        if registry_tool_name in self.tool_metadata_registry:
            metadata = self.tool_metadata_registry[registry_tool_name]
            params = self._build_tool_params(registry_tool_name, user_profile, session_context)

            task = DAGTask(
                tool_name=registry_tool_name,
                tool_metadata=metadata,
                params=params,
                dependencies=[dep.replace('-', '_') for dep in template.tool_dependencies.get(tool_name, [])],
                priority=TaskPriority.LOW
            )
            tasks.append(task)

    return tasks
```

### 2. 可选工具智能选择

```python
def _select_optional_tools_from_template(
    self,
    template: DAGTemplate,
    user_profile: Dict[str, Any]
) -> List[str]:
    """从模板中选择可选工具"""
    selected_tools = []
    
    # 根据模板复杂度决定选择多少可选工具
    if template.complexity_level == 3:
        # 复杂模板：选择所有可选工具
        selected_tools = template.optional_tools.copy()
    elif template.complexity_level == 2:
        # 中等模板：选择前一半可选工具
        selected_tools = template.optional_tools[:len(template.optional_tools)//2 + 1]
    else:
        # 简单模板：选择1-2个可选工具
        selected_tools = template.optional_tools[:2]
    
    # 根据用户档案特征调整
    fitness_level = user_profile.get("fitness_level", "beginner")
    fitness_goals = user_profile.get("fitness_goals", [])
    
    # 初学者：添加安全相关工具
    if fitness_level == "beginner":
        if "safe_exercise_modifier" in template.optional_tools and "safe_exercise_modifier" not in selected_tools:
            selected_tools.append("safe_exercise_modifier")
    
    # 增肌目标：添加营养相关工具
    if "增肌" in fitness_goals or "muscle_gain" in fitness_goals:
        if "exercise_nutrition_optimization" in template.optional_tools and "exercise_nutrition_optimization" not in selected_tools:
            selected_tools.append("exercise_nutrition_optimization")
    
    return selected_tools
```

### 3. 基于模板的拓扑排序

```python
def _build_levels_from_parallel_groups(
    self,
    tasks: List[DAGTask],
    parallel_groups: List[List[str]]
) -> List[ExecutionLevel]:
    """从模板的并行组构建执行层级"""
    levels = []
    task_map = {task.tool_name: task for task in tasks}
    
    for level_num, group in enumerate(parallel_groups):
        level_tasks = []
        
        for tool_name in group:
            # 转换工具名格式
            registry_tool_name = tool_name.replace('-', '_')
            if registry_tool_name in task_map:
                task = task_map[registry_tool_name]
                task.level = level_num
                level_tasks.append(task)
        
        if level_tasks:
            level = ExecutionLevel(
                level=level_num,
                tasks=level_tasks,
                estimated_duration=max(task.tool_metadata.execution_time for task in level_tasks),
                can_parallel=all(task.tool_metadata.parallel_safe for task in level_tasks)
            )
            levels.append(level)
    
    return levels
```

---

## 📊 模板统计信息

### 获取统计数据

```python
def get_template_statistics(self) -> Dict[str, Any]:
    """获取模板统计信息"""
    stats = {
        "total_templates": len(self.templates),
        "by_category": {},
        "by_complexity": {1: 0, 2: 0, 3: 0},
        "average_duration": 0.0,
        "total_tools": set()
    }
    
    total_duration = 0.0
    for template in self.templates.values():
        # 按类别统计
        category = template.category.value
        if category not in stats["by_category"]:
            stats["by_category"][category] = 0
        stats["by_category"][category] += 1
        
        # 按复杂度统计
        stats["by_complexity"][template.complexity_level] += 1
        
        # 累计时长
        total_duration += template.estimated_duration_seconds
        
        # 收集所有工具
        stats["total_tools"].update(template.required_tools)
        stats["total_tools"].update(template.optional_tools)
    
    stats["average_duration"] = total_duration / len(self.templates)
    stats["total_tools"] = len(stats["total_tools"])
    
    return stats
```

**统计结果示例**:
```json
{
  "total_templates": 9,
  "by_category": {
    "quick": 2,
    "training": 3,
    "nutrition": 1,
    "safety": 2,
    "comprehensive": 1
  },
  "by_complexity": {
    "1": 3,
    "2": 3,
    "3": 3
  },
  "average_duration": 9.1,
  "total_tools": 17
}
```

---

## 🔍 模板搜索

### 按关键词搜索

```python
def search_templates(self, query: str) -> List[DAGTemplate]:
    """搜索模板"""
    query_lower = query.lower()
    matching_templates = []
    
    for template in self.templates.values():
        # 检查名称
        if query_lower in template.name.lower():
            matching_templates.append(template)
            continue
        
        # 检查描述
        if query_lower in template.description.lower():
            matching_templates.append(template)
            continue
        
        # 检查适用意图
        for intent in template.applicable_intents:
            if query_lower in intent.lower():
                matching_templates.append(template)
                break
    
    return matching_templates
```

---

## ✅ 依赖关系验证

### 循环依赖检测

```python
def validate_template_dependencies(self, template_id: str) -> Dict[str, Any]:
    """验证模板的依赖关系"""
    template = self.get_template(template_id)
    if not template:
        return {"valid": False, "error": "模板不存在"}
    
    all_tools = set(template.required_tools + template.optional_tools)
    issues = []
    
    # 检查循环依赖
    def has_cycle(tool: str, visited: Set[str], rec_stack: Set[str]) -> bool:
        visited.add(tool)
        rec_stack.add(tool)
        
        for dep in template.tool_dependencies.get(tool, []):
            if dep not in visited:
                if has_cycle(dep, visited, rec_stack):
                    return True
            elif dep in rec_stack:
                return True
        
        rec_stack.remove(tool)
        return False
    
    for tool in all_tools:
        if has_cycle(tool, set(), set()):
            issues.append(f"检测到循环依赖: {tool}")
    
    # 检查依赖完整性
    for tool, deps in template.tool_dependencies.items():
        for dep in deps:
            if dep not in all_tools:
                issues.append(f"工具 {tool} 的依赖 {dep} 不在工具列表中")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "total_tools": len(all_tools),
        "total_dependencies": sum(len(deps) for deps in template.tool_dependencies.values())
    }
```

---

## 📤 模板导出

### 导出为JSON

```python
def export_templates(self, filepath: str):
    """导出模板到JSON文件"""
    templates_data = {
        template_id: template.to_dict()
        for template_id, template in self.templates.items()
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(templates_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 导出 {len(self.templates)} 个模板到 {filepath}")
```

---

## 🎯 使用示例

### 基本使用

```python
# 初始化模板管理器
manager = DAGTemplateManager()

# 获取所有模板
all_templates = manager.get_all_templates()
print(f"总共 {len(all_templates)} 个模板")

# 获取特定模板
template = manager.get_template("complete_training_plan")
if template:
    print(f"模板: {template.name}")
    print(f"描述: {template.description}")
    print(f"必需工具: {len(template.required_tools)}")
    print(f"可选工具: {len(template.optional_tools)}")

# 按类别获取模板
training_templates = manager.get_templates_by_category(TemplateCategory.TRAINING)
print(f"训练类模板: {len(training_templates)}个")

# 搜索模板
results = manager.search_templates("营养")
print(f"搜索结果: {len(results)}个")

# 获取统计信息
stats = manager.get_template_statistics()
print(f"模板统计: {stats}")

# 验证依赖关系
validation = manager.validate_template_dependencies("complete_training_plan")
print(f"依赖验证: {'✅ 通过' if validation['valid'] else '❌ 失败'}")
```

### 在编排器中使用

```python
# 基于模板执行DAG
execution_result = await orchestrator.execute_template(
    template_id="complete_training_plan",
    user_profile=user_profile,
    session_context={"session_id": session_id},
    cached_results={}
)

print(f"执行结果: {'成功' if execution_result.success else '失败'}")
print(f"总耗时: {execution_result.total_time:.2f}秒")
print(f"完成任务: {execution_result.tasks_completed}个")
```

---

## 📝 总结

### 核心特性

1. **9个预定义模板**: 覆盖问候、训练、营养、安全、康复等场景
2. **智能依赖管理**: 自动解析工具依赖关系，支持循环依赖检测
3. **并行执行优化**: 预定义并行执行组，最大化执行效率
4. **可选工具智能选择**: 根据复杂度和用户档案动态选择可选工具
5. **完整性验证**: 模板加载时自动验证完整性和一致性

### 性能优化

- **并行执行**: 最多6层并行优化（综合健身方案）
- **预估时长**: 1-20秒（根据模板复杂度）
- **工具复用**: 17个MCP工具灵活组合
- **缓存支持**: 支持工具结果缓存

### 扩展性

- **新增模板**: 在`_initialize_templates()`中添加新模板定义
- **修改依赖**: 更新`tool_dependencies`字典
- **调整并行**: 修改`parallel_groups`列表
- **自定义验证**: 扩展`validate()`方法

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
