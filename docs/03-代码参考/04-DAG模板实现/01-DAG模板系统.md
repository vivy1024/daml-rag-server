# 核心组件：DAG模板系统代码参考

**版本**: v1.1.0  
**创建日期**: 2025-12-17  
**更新日期**: 2025-12-17  
**状态**: ✅ 已完成

---

## 概述

DAG模板系统管理预定义的工作流程模板，供LLM决策引擎选择使用。

### 文件位置

- **主文件**: `src/applications/fitness/dag_template_system.py`
- **模板定义**: `src/applications/fitness/intent_templates.py`

### 核心类：DAGTemplateManager

```python
class DAGTemplateManager:
    """
    DAG模板管理器
    
    职责：
    - 管理预定义的DAG模板
    - 提供模板查找和验证
    - 支持动态添加新模板
    """
    
    def __init__(self):
        self.templates: Dict[str, DAGTemplate] = {}
        self._load_default_templates()
    
    def register_template(self, template: DAGTemplate):
        """注册DAG模板"""
        self.templates[template.template_id] = template
        logger.info(f"注册DAG模板: {template.template_id}")
    
    def get_template(self, template_id: str) -> Optional[DAGTemplate]:
        """获取DAG模板"""
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> List[DAGTemplate]:
        """获取所有模板"""
        return list(self.templates.values())
```

### DAG模板数据结构

```python
@dataclass
class DAGTemplate:
    """DAG模板"""
    template_id: str                        # 模板ID
    name: str                               # 模板名称
    description: str                        # 模板描述
    category: TemplateCategory              # 模板类别
    applicable_intents: List[str]           # 适用意图
    required_tools: List[str]               # 必需工具
    optional_tools: List[str]               # 可选工具
    tool_dependencies: Dict[str, List[str]] # 工具依赖关系
    parallel_groups: List[List[str]]        # 并行执行组
    expected_output: Dict[str, str]         # 预期输出
    safety_constraints: List[str]           # 安全约束
    estimated_duration_seconds: float       # 预估执行时间（秒）
    complexity_level: int                   # 复杂度等级（1-3）
    success_rate: float                     # 成功率
    response_hint: str                      # LLM响应提示（v1.1.0新增）
```

### 模板类别枚举

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

## 预定义模板

### 0. 问候闲聊模板（v1.1.0新增）

```python
DAGTemplate(
    template_id="greeting",
    name="问候闲聊",
    description="友好回应用户的问候和简单闲聊",
    category=TemplateCategory.QUICK,
    applicable_intents=[
        "你好", "早上好", "晚上好", "hi", "hello", "嗨", "在吗", "闲聊", "问候"
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

**特点**：
- ✅ 无工具调用：`required_tools=[]`
- ✅ 极快响应：1秒内完成
- ✅ 简短友好：1-2句话的问候回应
- ✅ 明确约束：不提供训练建议

### 1. 完整训练计划模板

```python
COMPLETE_TRAINING_PLAN = DAGTemplate(
    template_id="complete_training_plan",
    name="完整训练计划",
    description="制定个性化的训练计划",
    applicable_scenarios=["制定训练计划", "增肌计划", "力量训练"],
    required_tools=[
        "get_user_profile",
        "contraindications_checker",
        "injury_risk_assessor",
        "intelligent_exercise_selector",
        "muscle_group_volume_calculator",
        "professional_program_designer"
    ],
    tool_dependencies={
        "get_user_profile": [],
        "contraindications_checker": ["get_user_profile"],
        "injury_risk_assessor": ["get_user_profile"],
        "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor"],
        "muscle_group_volume_calculator": ["get_user_profile"],
        "professional_program_designer": ["intelligent_exercise_selector", "muscle_group_volume_calculator"]
    },
    estimated_duration=3.5
)
```

### 2. 营养规划模板

```python
NUTRITION_PLANNING = DAGTemplate(
    template_id="nutrition_planning",
    name="营养规划",
    description="制定营养和膳食计划",
    applicable_scenarios=["饮食建议", "营养搭配", "餐食计划"],
    required_tools=[
        "get_user_profile",
        "tdee_calculator",
        "nutrition_intake_analyzer",
        "meal_plan_designer"
    ],
    tool_dependencies={
        "get_user_profile": [],
        "tdee_calculator": ["get_user_profile"],
        "nutrition_intake_analyzer": ["tdee_calculator"],
        "meal_plan_designer": ["nutrition_intake_analyzer"]
    },
    estimated_duration=2.0
)
```

### 3. 动作优化模板

```python
EXERCISE_OPTIMIZATION = DAGTemplate(
    template_id="exercise_optimization",
    name="动作优化",
    description="选择和优化训练动作",
    applicable_scenarios=["动作选择", "替代动作", "动作修正"],
    required_tools=[
        "get_user_profile",
        "contraindications_checker",
        "intelligent_exercise_selector",
        "exercise_alternative_finder"
    ],
    tool_dependencies={
        "get_user_profile": [],
        "contraindications_checker": ["get_user_profile"],
        "intelligent_exercise_selector": ["contraindications_checker"],
        "exercise_alternative_finder": ["intelligent_exercise_selector"]
    },
    estimated_duration=1.5
)
```

---

## 相关文档

- **LLM决策引擎**: [08-步骤6.5-LLM选择DAG方案.md](./07-步骤6.5-LLM选择DAG方案.md)
- **DAG编排器**: [09-步骤7-DAG编排器.md](./08-步骤7-DAG编排器.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-17
