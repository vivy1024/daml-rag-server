# DAG模板开发指南

**创建日期**: 2025-12-22

---


**版本**: v1.1.0  
**更新日期**: 2025-12-17  
**状态**: ✅ 生产就绪

---

## 📋 概述

本指南介绍如何为DAML-RAG框架开发新的DAG模板。DAG模板是三段式架构的核心组件，定义了完整的工作流程、工具链、依赖关系和执行策略。

### 什么是DAG模板？

DAG（Directed Acyclic Graph，有向无环图）模板是预定义的工作流程模板，包含：
- **工具链定义**：需要执行的MCP工具列表
- **依赖关系**：工具之间的依赖关系
- **并行策略**：哪些工具可以并行执行
- **安全约束**：必须遵守的安全规则
- **适用场景**：模板适用的用户意图

### 为什么需要DAG模板？

**三段式架构的核心**：
```
用户查询 
  ↓
【阶段1：LLM决策】LLM从DAG模板库中选择最合适的方案
  ↓
【阶段2：程序执行】程序严格按照DAG模板执行
  ↓
【阶段3：LLM综合】LLM基于真实数据进行专业分析
```

**优势**：
- ✅ **避免幻觉**：LLM不直接调用MCP，只选择模板
- ✅ **保证安全**：程序保证依赖关系和安全约束
- ✅ **性能优化**：自动并行执行、缓存优化
- ✅ **易于扩展**：新增模板无需修改LLM

---

## 🏗️ DAG模板结构

### 基本结构

```python
from typing import List, Dict, Any

class DAGTemplate:
    """DAG模板定义"""
    
    # 基本信息
    template_id: str              # 模板唯一标识（kebab-case）
    name: str                     # 模板名称（中文）
    description: str              # 模板描述
    version: str                  # 模板版本（语义化版本）
    
    # 适用场景
    applicable_intents: List[str] # 适用的用户意图列表
    example_queries: List[str]    # 示例查询
    
    # 工具链定义
    required_tools: List[str]     # 必需工具列表
    optional_tools: List[str]     # 可选工具列表
    
    # 依赖关系
    tool_dependencies: Dict[str, List[str]]  # 工具依赖关系
    
    # 执行策略
    parallel_groups: List[List[str]]         # 并行执行组
    execution_timeout: int                   # 执行超时（秒）
    
    # 预期输出
    expected_output: Dict[str, str]          # 预期输出结构
    
    # 安全约束
    safety_constraints: List[str]            # 安全约束列表
    critical_tools: List[str]                # 关键工具（失败则终止）
    
    # LLM响应配置（v1.1.0新增）
    response_hint: str                       # LLM响应提示：指导步骤10如何生成回答
    
    # 元数据
    author: str                              # 作者
    created_at: str                          # 创建时间
    updated_at: str                          # 更新时间
    tags: List[str]                          # 标签
```

### 字段说明

#### 1. 基本信息

**template_id**（必需）
- 格式：kebab-case（小写字母+连字符）
- 示例：`complete-training-plan`, `nutrition-planning`, `safety-assessment`
- 规则：全局唯一，不可重复

**name**（必需）
- 格式：中文名称
- 示例：`完整训练计划`, `营养规划`, `安全评估`

**description**（必需）
- 格式：简短描述（1-2句话）
- 示例：`为用户制定包含动作选择、训练量计算、周期化安排的完整训练计划`

**version**（必需）
- 格式：语义化版本（major.minor.patch）
- 示例：`1.0.0`, `1.2.3`

#### 2. 适用场景

**applicable_intents**（必需）
- 格式：用户意图列表
- 示例：`["制定训练计划", "增肌计划", "力量训练计划"]`
- 用途：LLM根据用户查询匹配意图

**example_queries**（可选）
- 格式：示例查询列表
- 示例：`["帮我制定一个增肌训练计划", "我想练胸肌，给我推荐动作"]`
- 用途：帮助LLM理解模板适用场景

#### 3. 工具链定义

**required_tools**（必需）
- 格式：MCP工具名称列表
- 示例：`["get_user_profile", "contraindications_checker", "intelligent_exercise_selector"]`
- 规则：必须执行的工具

**optional_tools**（可选）
- 格式：MCP工具名称列表
- 示例：`["movement_pattern_balancer", "periodized_program_designer"]`
- 规则：可选执行的工具

#### 4. 依赖关系

**tool_dependencies**（必需）
- 格式：`{工具名: [依赖的工具列表]}`
- 示例：
```python
{
    "get_user_profile": [],  # 无依赖
    "contraindications_checker": ["get_user_profile"],  # 依赖用户档案
    "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor"]
}
```
- 规则：
  - 无依赖的工具：空列表 `[]`
  - 不能有循环依赖
  - 依赖的工具必须在 `required_tools` 或 `optional_tools` 中

#### 5. 执行策略

**parallel_groups**（可选）
- 格式：`[[工具1, 工具2], [工具3], ...]`
- 示例：
```python
[
    ["get_user_profile"],  # Level 0
    ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator"],  # Level 1（并行）
    ["intelligent_exercise_selector"],  # Level 2
    ["professional_program_designer"]  # Level 3
]
```
- 规则：
  - 同一组内的工具并行执行
  - 不同组按顺序执行
  - 如果不指定，系统自动根据依赖关系生成

**execution_timeout**（可选）
- 格式：整数（秒）
- 示例：`300`（5分钟）
- 默认：`180`（3分钟）

#### 6. 预期输出

**expected_output**（必需）
- 格式：`{输出字段: 数据类型}`
- 示例：
```python
{
    "user_profile": "Dict",
    "contraindications": "List[Exercise]",
    "recommended_exercises": "List[Exercise]",
    "training_program": "TrainingProgram"
}
```
- 用途：验证执行结果的完整性

#### 7. 安全约束

**safety_constraints**（必需）
- 格式：安全约束描述列表
- 示例：
```python
[
    "必须执行contraindications_checker",
    "必须执行injury_risk_assessor",
    "禁忌动作必须从推荐中排除"
]
```

**critical_tools**（必需）
- 格式：关键工具名称列表
- 示例：`["contraindications_checker", "injury_risk_assessor"]`
- 规则：这些工具失败时，整个DAG执行终止

#### 8. LLM响应配置（v1.1.0新增）

**response_hint**（必需）
- 格式：字符串，描述LLM应该如何生成回答
- 用途：指导步骤10的LLM生成符合场景的回答（风格、长度、内容约束）
- 示例：
```python
# greeting模板
response_hint = "简短友好，1-2句话，不要提供训练建议"

# complete_training_plan模板
response_hint = "详细专业，提供完整的训练计划，包含动作选择、组数次数、训练量分配、周期化安排，字数300-500字"

# quick_consultation模板
response_hint = "简洁明了，直接回答用户问题，提供实用建议，2-3段话，字数100-200字"
```

**配置要素**：
1. **响应风格**：简短友好、详细专业、简洁实用、数据驱动等
2. **响应长度**：1-2句话、2-3段话、字数范围（如100-200字）
3. **内容约束**：包含什么、不包含什么（如"不要提供训练建议"）
4. **专业程度**：友好、专业、严谨、谨慎等

**设计原则**：
- ✅ 明确具体：清楚说明风格、长度、内容要求
- ✅ 场景匹配：response_hint要与模板的适用场景匹配
- ✅ 用户友好：考虑用户期望的回答方式
- ❌ 避免模糊：不要使用"适当"、"合理"等模糊词汇

---

## 📝 开发流程

### 步骤1：需求分析

**确定模板目标**：
- 这个模板要解决什么问题？
- 适用于哪些用户场景？
- 需要哪些MCP工具？

**示例**：
```
目标：为用户制定完整的增肌训练计划
场景：用户询问"帮我制定增肌计划"、"我想练胸肌"
工具：用户档案、禁忌检查、动作选择、训练量计算、计划设计
```

### 步骤2：设计工具链

**列出所有需要的工具**：
```python
required_tools = [
    "get_user_profile",           # 获取用户档案
    "contraindications_checker",  # 禁忌动作检查
    "injury_risk_assessor",       # 损伤风险评估
    "intelligent_exercise_selector",  # 智能动作选择
    "muscle_group_volume_calculator",  # 肌肉训练量计算
    "professional_program_designer"    # 专业计划设计
]

optional_tools = [
    "movement_pattern_balancer",   # 动作模式平衡
    "periodized_program_designer"  # 周期化设计
]
```

### 步骤3：定义依赖关系

**绘制依赖图**：
```
get_user_profile (Level 0)
    ↓
    ├─→ contraindications_checker (Level 1)
    ├─→ injury_risk_assessor (Level 1)
    └─→ muscle_group_volume_calculator (Level 1)
         ↓
         ├─→ intelligent_exercise_selector (Level 2)
         │    ↓
         └────→ professional_program_designer (Level 3)
```

**转换为代码**：
```python
tool_dependencies = {
    "get_user_profile": [],
    "contraindications_checker": ["get_user_profile"],
    "injury_risk_assessor": ["get_user_profile"],
    "muscle_group_volume_calculator": ["get_user_profile"],
    "intelligent_exercise_selector": [
        "contraindications_checker",
        "injury_risk_assessor"
    ],
    "professional_program_designer": [
        "intelligent_exercise_selector",
        "muscle_group_volume_calculator"
    ]
}
```

### 步骤4：优化并行执行

**识别可并行的工具**：
- Level 1的三个工具都只依赖 `get_user_profile`
- 它们之间没有依赖关系
- 可以并行执行

**定义并行组**：
```python
parallel_groups = [
    ["get_user_profile"],  # Level 0
    [
        "contraindications_checker",
        "injury_risk_assessor",
        "muscle_group_volume_calculator"
    ],  # Level 1（并行）
    ["intelligent_exercise_selector"],  # Level 2
    ["professional_program_designer"]   # Level 3
]
```

### 步骤5：定义安全约束

**识别关键工具**：
- `contraindications_checker`：必须执行，失败则终止
- `injury_risk_assessor`：必须执行，失败则终止

**定义约束**：
```python
safety_constraints = [
    "必须执行contraindications_checker",
    "必须执行injury_risk_assessor",
    "禁忌动作必须从推荐中排除",
    "训练量必须符合用户恢复能力"
]

critical_tools = [
    "contraindications_checker",
    "injury_risk_assessor"
]
```

### 步骤6：编写模板代码

**创建模板文件**：`src/applications/fitness/templates/complete_training_plan.py`

```python
"""
完整训练计划DAG模板
"""

from typing import List, Dict, Any
from ..dag_template_manager import DAGTemplate

# 模板定义
COMPLETE_TRAINING_PLAN_TEMPLATE = DAGTemplate(
    # 基本信息
    template_id="complete-training-plan",
    name="完整训练计划",
    description="为用户制定包含动作选择、训练量计算、周期化安排的完整训练计划",
    version="1.0.0",
    
    # 适用场景
    applicable_intents=[
        "制定训练计划",
        "增肌计划",
        "力量训练计划",
        "训练方案设计"
    ],
    example_queries=[
        "帮我制定一个增肌训练计划",
        "我想练胸肌，给我推荐动作和计划",
        "制定一个4天的力量训练方案"
    ],
    
    # 工具链定义
    required_tools=[
        "get_user_profile",
        "contraindications_checker",
        "injury_risk_assessor",
        "intelligent_exercise_selector",
        "muscle_group_volume_calculator",
        "professional_program_designer"
    ],
    optional_tools=[
        "movement_pattern_balancer",
        "periodized_program_designer",
        "training_split_designer"
    ],
    
    # 依赖关系
    tool_dependencies={
        "get_user_profile": [],
        "contraindications_checker": ["get_user_profile"],
        "injury_risk_assessor": ["get_user_profile"],
        "muscle_group_volume_calculator": ["get_user_profile"],
        "intelligent_exercise_selector": [
            "contraindications_checker",
            "injury_risk_assessor"
        ],
        "professional_program_designer": [
            "intelligent_exercise_selector",
            "muscle_group_volume_calculator"
        ]
    },
    
    # 执行策略
    parallel_groups=[
        ["get_user_profile"],
        [
            "contraindications_checker",
            "injury_risk_assessor",
            "muscle_group_volume_calculator"
        ],
        ["intelligent_exercise_selector"],
        ["professional_program_designer"]
    ],
    execution_timeout=300,
    
    # 预期输出
    expected_output={
        "user_profile": "Dict",
        "contraindications": "List[Exercise]",
        "injury_risks": "Dict",
        "recommended_exercises": "List[Exercise]",
        "volume_recommendations": "Dict[str, VolumeRange]",
        "training_program": "TrainingProgram"
    },
    
    # 安全约束
    safety_constraints=[
        "必须执行contraindications_checker",
        "必须执行injury_risk_assessor",
        "禁忌动作必须从推荐中排除",
        "训练量必须符合用户恢复能力"
    ],
    critical_tools=[
        "contraindications_checker",
        "injury_risk_assessor"
    ],
    
    # 元数据
    author="BUILD_BODY Team",
    created_at="2025-12-12",
    updated_at="2025-12-12",
    tags=["training", "program-design", "muscle-building"]
)
```

### 步骤7：注册模板

**在模板管理器中注册**：`src/applications/fitness/dag_template_manager.py`

```python
from .templates.complete_training_plan import COMPLETE_TRAINING_PLAN_TEMPLATE

class DAGTemplateManager:
    def __init__(self):
        self.templates = {
            "complete-training-plan": COMPLETE_TRAINING_PLAN_TEMPLATE,
            # 其他模板...
        }
```

### 步骤8：测试模板

**编写单元测试**：`tests/test_complete_training_plan_template.py`

```python
import pytest
from src.applications.fitness.dag_template_manager import DAGTemplateManager

def test_complete_training_plan_template():
    """测试完整训练计划模板"""
    manager = DAGTemplateManager()
    template = manager.get_template("complete-training-plan")
    
    # 验证基本信息
    assert template.template_id == "complete-training-plan"
    assert template.name == "完整训练计划"
    
    # 验证工具链
    assert "get_user_profile" in template.required_tools
    assert "contraindications_checker" in template.required_tools
    
    # 验证依赖关系
    assert template.tool_dependencies["get_user_profile"] == []
    assert "get_user_profile" in template.tool_dependencies["contraindications_checker"]
    
    # 验证无循环依赖
    assert manager.validate_template(template) == True
    
    # 验证并行组
    assert len(template.parallel_groups) == 4
    assert len(template.parallel_groups[1]) == 3  # Level 1有3个并行工具
```

**运行测试**：
```bash
docker-compose exec fitness_daml_rag pytest tests/test_complete_training_plan_template.py -v
```

---

## 📚 完整示例：Greeting模板

### 场景说明

**目标**：友好回应用户的问候和简单闲聊  
**特点**：不需要调用任何MCP工具，快速响应  
**适用场景**：用户输入"你好"、"早上好"、"hi"等问候语

### 模板定义

```python
DAGTemplate(
    template_id="greeting",
    name="问候闲聊",
    description="友好回应用户的问候和简单闲聊",
    category=TemplateCategory.QUICK,
    
    # 适用意图
    applicable_intents=[
        "你好",
        "早上好",
        "晚上好",
        "hi",
        "hello",
        "嗨",
        "在吗",
        "闲聊",
        "问候"
    ],
    
    # 工具链（不需要任何工具）
    required_tools=[],
    optional_tools=[],
    
    # 依赖关系（无）
    tool_dependencies={},
    
    # 并行组（无）
    parallel_groups=[],
    
    # 预期输出
    expected_output={
        "greeting_response": "简短友好的问候回应"
    },
    
    # 安全约束（无）
    safety_constraints=[],
    
    # 执行参数
    estimated_duration_seconds=1.0,
    complexity_level=1,
    
    # LLM响应配置
    response_hint="简短友好，1-2句话，不要提供训练建议"
)
```

### 设计要点

1. **无工具调用**：`required_tools=[]`，不需要调用任何MCP工具
2. **快速响应**：`estimated_duration_seconds=1.0`，极快的响应速度
3. **简单场景**：`complexity_level=1`，最简单的模板
4. **明确约束**：`response_hint`明确指出"不要提供训练建议"

### 使用场景

**用户输入**：
```
用户: 你好
用户: 早上好，今天天气不错
用户: hi，在吗？
```

**系统响应**：
```
系统: 你好！很高兴为你服务，有什么健身问题我可以帮你解答吗？
系统: 早上好！今天是训练的好日子，需要我帮你制定训练计划吗？
系统: 在的！我是你的AI健身教练，随时为你提供专业的健身指导。
```

### 与其他模板的对比

| 特性 | greeting模板 | quick_consultation模板 | complete_training_plan模板 |
|------|-------------|----------------------|--------------------------|
| 工具数量 | 0个 | 1个 | 6个+ |
| 响应时间 | 1秒 | 2秒 | 15秒 |
| 响应长度 | 1-2句话 | 100-200字 | 300-500字 |
| 适用场景 | 问候闲聊 | 简单咨询 | 完整计划 |

---

## 🎯 最佳实践

### 1. 模板设计原则

**单一职责**：
- ✅ 每个模板专注于一个核心场景
- ❌ 不要创建"万能模板"

**清晰依赖**：
- ✅ 依赖关系清晰明确
- ❌ 避免复杂的依赖网络

**安全优先**：
- ✅ 安全工具优先执行
- ✅ 关键工具失败则终止

**性能优化**：
- ✅ 最大化并行执行
- ✅ 合理设置超时时间

### 2. 工具选择建议

**必需工具**：
- 用户档案相关：`get_user_profile`
- 安全检查相关：`contraindications_checker`, `injury_risk_assessor`
- 核心功能相关：根据模板目标选择

**可选工具**：
- 增强功能：`movement_pattern_balancer`, `periodized_program_designer`
- 高级分析：`training_split_designer`, `recovery_optimizer`

### 3. 依赖关系设计

**避免循环依赖**：
```python
# ❌ 错误：循环依赖
{
    "tool_a": ["tool_b"],
    "tool_b": ["tool_a"]
}

# ✅ 正确：单向依赖
{
    "tool_a": [],
    "tool_b": ["tool_a"]
}
```

**最小化依赖**：
```python
# ❌ 不好：过度依赖
{
    "tool_c": ["tool_a", "tool_b", "tool_d", "tool_e"]
}

# ✅ 更好：只依赖必需的
{
    "tool_c": ["tool_a", "tool_b"]
}
```

### 4. 并行优化策略

**识别并行机会**：
- 同一层级的工具
- 无数据依赖的工具
- 独立的计算任务

**示例**：
```python
# Level 1：这三个工具都只依赖用户档案，可以并行
parallel_groups = [
    ["get_user_profile"],
    [
        "contraindications_checker",  # 并行
        "injury_risk_assessor",       # 并行
        "muscle_group_volume_calculator"  # 并行
    ]
]
```

### 5. 安全约束设计

**关键工具识别**：
- 安全检查工具：必须成功
- 数据验证工具：必须成功
- 核心功能工具：根据场景决定

**约束描述**：
- 清晰明确
- 可验证
- 可追溯

---

## 📚 示例模板

### 示例1：营养规划模板

```python
NUTRITION_PLANNING_TEMPLATE = DAGTemplate(
    template_id="nutrition-planning",
    name="营养规划",
    description="为用户制定个性化的营养计划，包含TDEE计算、营养分析、餐食设计",
    version="1.0.0",
    
    applicable_intents=[
        "营养规划",
        "饮食建议",
        "餐食计划",
        "营养搭配"
    ],
    
    required_tools=[
        "get_user_profile",
        "tdee_calculator",
        "nutrition_analyzer",
        "meal_plan_designer"
    ],
    
    tool_dependencies={
        "get_user_profile": [],
        "tdee_calculator": ["get_user_profile"],
        "nutrition_analyzer": ["tdee_calculator"],
        "meal_plan_designer": ["nutrition_analyzer"]
    },
    
    parallel_groups=[
        ["get_user_profile"],
        ["tdee_calculator"],
        ["nutrition_analyzer"],
        ["meal_plan_designer"]
    ],
    
    safety_constraints=[
        "必须考虑用户过敏信息",
        "必须符合用户饮食偏好",
        "热量摄入必须合理"
    ],
    
    critical_tools=["tdee_calculator"]
)
```

### 示例2：安全评估模板

```python
SAFETY_ASSESSMENT_TEMPLATE = DAGTemplate(
    template_id="safety-assessment",
    name="安全评估",
    description="评估用户的训练安全性，识别禁忌动作和风险因素",
    version="1.0.0",
    
    applicable_intents=[
        "安全评估",
        "禁忌动作",
        "风险评估",
        "安全检查"
    ],
    
    required_tools=[
        "get_user_profile",
        "contraindications_checker",
        "injury_risk_assessor",
        "safety_recommendation_generator"
    ],
    
    tool_dependencies={
        "get_user_profile": [],
        "contraindications_checker": ["get_user_profile"],
        "injury_risk_assessor": ["get_user_profile"],
        "safety_recommendation_generator": [
            "contraindications_checker",
            "injury_risk_assessor"
        ]
    },
    
    parallel_groups=[
        ["get_user_profile"],
        ["contraindications_checker", "injury_risk_assessor"],
        ["safety_recommendation_generator"]
    ],
    
    safety_constraints=[
        "必须执行contraindications_checker",
        "必须执行injury_risk_assessor",
        "所有禁忌动作必须明确标注"
    ],
    
    critical_tools=[
        "contraindications_checker",
        "injury_risk_assessor"
    ]
)
```

---

## 🔧 调试和优化

### 调试工具

**DAG可视化**：
```python
from src.applications.fitness.dag_visualizer import DAGVisualizer

visualizer = DAGVisualizer()
mermaid_diagram = visualizer.visualize_dag_structure(template)
print(mermaid_diagram)
```

**执行日志**：
```python
from src.applications.fitness.three_stage_orchestrator import ThreeStageOrchestrator

orchestrator = ThreeStageOrchestrator(debug_mode=True)
result = await orchestrator.execute(user_query, user_profile)
```

### 性能优化

**监控性能**：
```python
from src.applications.fitness.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()
report = monitor.generate_report()
print(f"平均执行时间: {report['avg_execution_time']}ms")
print(f"并行度: {report['parallelism_factor']}")
```

**优化建议**：
- 增加并行执行的工具数量
- 减少不必要的依赖
- 使用缓存减少重复计算
- 合理设置超时时间

---

## 📖 参考资料

**相关文档**：
- <!-- [完整工作流程](../../02-核心架构/01-系统架构/02-完整工作流程.md) (文档不存在) -->
- <!-- [DAG模板系统参考](../03-代码参考/26-DAG模板系统参考.md) (文档不存在) -->
- <!-- [三段式编排器参考](../03-代码参考/29-三段式编排器参考.md) (文档不存在) -->

**代码示例**：
- [DAG模板管理器](../../src/applications/fitness/dag_template_manager.py)
- [示例模板](../../src/applications/fitness/templates/)
- [测试用例](../../tests/test_dag_template_manager.py)

---

**维护者**: BUILD_BODY Team  
**最后更新**: 2025-12-12
