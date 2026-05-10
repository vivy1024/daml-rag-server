# 04-DAG模板实现

> ⛔ **DEPRECATED (v3.0)**
>
> 本文档描述的 DAG 模板系统已在 v3.0 中**完全删除**。
> 编排职责已上移至 **YuzhenFork Agent Loop**（Skills-first Agent）。
> 删除的代码：`dag_template_system.py`, `enhanced_dag_orchestrator.py`, `workflow_executor.py`
>
> 本文档仅保留供历史参考，不再维护。
> 新架构参考：`.kiro/specs/skills-first-agent-v2/`

**版本**: v1.0.0 → ~~已废弃~~
**创建日期**: 2025-12-22
**状态**: ⛔ DEPRECATED — v3.0 已删除

---

## 模块说明

本模块包含所有DAG（有向无环图）模板的详细代码实现文档。DAG模板是DAML-RAG工作流程编排的核心，定义了MCP工具的调用顺序和依赖关系。

### DAG模板架构

**设计理念**
- **声明式定义**：通过YAML配置定义任务节点和依赖关系
- **可复用性**：模板可以被多个场景复用
- **可扩展性**：支持自定义新模板

**执行流程**
1. LLM从模板库选择合适的DAG方案（步骤6.5）
2. DAG编排器加载并执行选中的模板（步骤7）
3. 按依赖关系顺序调用MCP工具
4. 汇总所有工具结果（步骤9）

---

## 文档列表

### DAG模板系统

1. [01-DAG模板系统.md](./01-DAG模板系统.md) - DAG模板系统的设计和实现
2. [02-三段式编排器.md](./02-三段式编排器.md) - 三段式编排器的核心逻辑

### DAG模板代码实现

3. [03-DAG模板代码实现.md](./03-DAG模板代码实现.md) - 所有DAG模板的详细代码实现
4. [04-CacheManager使用指南.md](./04-CacheManager使用指南.md) - CacheManager 使用指南
   - 9个预定义模板的完整实现
   - 任务节点定义和依赖关系配置
   - 并行执行组优化
   - 模板验证和管理机制
   - 完整代码示例

---

## DAG模板清单

### 快速咨询模板

1. **greeting** - 问候闲聊（无需工具调用）
2. **quick_consultation** - 快速咨询（单工具）

### 训练计划模板

3. **complete_training_plan** - 完整训练计划（6必需+3可选工具）
4. **exercise_optimization** - 动作优化（3必需+4可选工具）
5. **progress_analysis** - 进展分析（2必需+1可选工具）

### 营养计划模板

6. **nutrition_planning** - 营养规划（4必需+1可选工具）

### 安全评估模板

7. **safety_assessment** - 安全评估（3必需+2可选工具）
8. **rehabilitation_training** - 康复训练（4必需+3可选工具）

### 综合模板

9. **comprehensive_fitness** - 综合健身方案（8必需+3可选工具）

---

## 代码路径

### DAG模板系统

```
daml-rag-server/src/applications/fitness/
├── dag_template_system.py           # DAG模板系统（9个预定义模板）
├── enhanced_dag_orchestrator.py     # 增强版DAG编排器
└── workflow_executor.py             # 工作流程执行器
```

### 核心类

- `DAGTemplate` - 模板定义数据类
- `DAGTemplateManager` - 模板管理器
- `EnhancedDAGOrchestrator` - DAG编排器
- `TemplateCategory` - 模板类别枚举

---

## 模板结构示例

```python
# 完整训练计划模板
DAGTemplate(
    template_id="complete_training_plan",
    name="完整训练计划",
    description="为用户制定包含动作选择、训练量计算、周期化安排的完整训练计划",
    category=TemplateCategory.COMPREHENSIVE,
    applicable_intents=["制定训练计划", "增肌计划", "力量训练计划"],
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
    tool_dependencies={
        "get_user_profile": [],
        "contraindications_checker": ["get_user_profile"],
        "injury_risk_assessor": ["get_user_profile"],
        "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor"],
        "professional_program_designer": ["intelligent_exercise_selector", "muscle_group_volume_calculator"]
    },
    parallel_groups=[
        ["get_user_profile"],
        ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator"],
        ["intelligent_exercise_selector"],
        ["professional_program_designer"],
        ["periodized_program_designer", "training_split_designer"]
    ],
    estimated_duration_seconds=15.0,
    complexity_level=3
)
```

---

## 相关链接

- **DAG模板架构**: [02-核心架构/03-编排层/02-DAG模板架构.md](../../02-核心架构/03-编排层/02-DAG模板架构.md)（待补充）
- **三段式编排器架构**: [02-核心架构/03-编排层/01-三段式编排器架构.md](../../02-核心架构/03-编排层/01-三段式编排器架构.md)
- **DAG模板开发指南**: [04-开发指南/01-快速上手/01-DAG模板开发指南.md](../../04-开发指南/01-快速上手/01-DAG模板开发指南.md)
- **DAG编排器代码**: [03-代码参考/01-工作流程步骤/08-步骤7-DAG编排器.md](../01-工作流程步骤/08-步骤7-DAG编排器.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
