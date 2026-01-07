# Fitness应用层架构文档

**版本**: v2.0.0  
**创建日期**: 2025-12-18  
**更新日期**: 2025-12-18  
**状态**: ✅ 生产就绪（已集成缓存、监控、可视化）

---

## 📋 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [核心组件](#核心组件)
- [数据流](#数据流)
- [组件职责](#组件职责)
- [使用指南](#使用指南)
- [扩展指南](#扩展指南)

---

## 🎯 概述

Fitness应用层是DAML-RAG框架在健身领域的完整实现，采用**分层架构**和**组件化设计**，确保代码的可维护性和可扩展性。

### 核心特性

- ✅ **11步工作流程**：完整的AI健身教练处理流程
- ✅ **DAG编排系统**：基于模板的任务编排和执行
- ✅ **MCP工具集成**：15个Python内置工具 + 1个stdio服务
- ✅ **流式输出支持**：突破4096 token限制
- ✅ **三段式架构**：LLM决策 + 程序执行 + LLM综合

---

## 🏗️ 架构设计

```
src/applications/fitness/
│
├── 📁 核心编排层
│   ├── workflow_executor.py          # 11步工作流程执行器（入口）
│   ├── enhanced_dag_orchestrator.py  # DAG编排器（任务调度）
│   ├── dag_template_system.py        # DAG模板管理器
│   └── three_stage_orchestrator.py   # 三段式编排器（已废弃）
│
├── 📁 决策分析层
│   ├── llm_decision_engine.py        # LLM决策引擎（选择DAG模板）
│   ├── llm_analysis_engine.py        # LLM综合分析引擎
│   └── intelligent_intent_matcher.py # 智能意图匹配器（已废弃）
│
├── 📁 MCP工具层
│   ├── mcp_tools/
│   │   ├── registry.py               # Python工具注册表
│   │   ├── base_tool.py              # 工具基类
│   │   ├── training/                 # 训练相关工具（5个）
│   │   ├── safety/                   # 安全相关工具（3个）
│   │   ├── exercise/                 # 动作相关工具（4个）
│   │   └── nutrition/                # 营养相关工具（3个）
│   └── __init__.py                   # 工具初始化
│
├── 📁 客户端层
│   └── clients/
│       └── backend_client.py         # Laravel后端客户端
│
├── 📁 数据补充层
│   └── data_supplement/
│       ├── manager.py                # 数据补充管理器
│       ├── exercise_supplementer.py  # 动作数据补充
│       ├── food_supplementer.py      # 食物数据补充
│       └── injury_supplementer.py    # 损伤数据补充
│
└── 📁 遗留代码（待清理）
    ├── fitness_app.py                # 旧版应用入口
    ├── fitness_service.py            # 旧版服务层
    ├── fitness_dag_orchestrator.py   # 旧版DAG编排器
    ├── chat_service.py               # 旧版聊天服务
    ├── complete_dag_system.py        # 旧版完整DAG系统
    ├── component_registrations.py    # 旧版组件注册
    └── intent_templates.py           # 旧版意图模板
```

---

## 🔧 核心组件

### 1️⃣ 工作流程执行器（workflow_executor.py）- 增强版

**职责**：11步工作流程的唯一入口，协调所有组件

**核心函数**：
- `execute_eleven_step_workflow()` - 标准版本（一次性返回）
- `execute_eleven_step_workflow_stream()` - 流式版本（实时输出）
- `get_workflow_statistics()` - 获取统计信息
- `visualize_dag_template()` - 可视化DAG模板
- `shutdown_workflow_components()` - 关闭组件

**增强功能**：
- ✅ **智能缓存**：使用`IntelligentUserCache`实现多级缓存（内存+Redis+数据库）
- ✅ **性能监控**：使用`DAMLWorkflowMonitor`跟踪11步工作流程性能
- ✅ **DAG可视化**：使用`DAGVisualizer`生成ASCII/Mermaid/Graphviz图
- ✅ **统计分析**：提供缓存命中率、响应时间、成功率等指标

**11步流程**：
```
步骤1: 预加载用户档案（智能缓存，0延迟）
步骤2: 会话记录存储（Few-Shot）
步骤3: 检查会员权限
步骤4: BGE复杂度分类
步骤5: 智能模型选择（teacher/student）
步骤6: Few-Shot检索（推理时学习）
步骤6.5: LLM选择DAG模板
步骤7-8: DAG编排执行
步骤9: 工具结果汇总
步骤10: LLM生成最终回答
步骤11: 记录交互
```

**调用示例**：
```python
from applications.fitness.workflow_executor import (
    execute_eleven_step_workflow,
    get_workflow_statistics,
    visualize_dag_template
)

# 执行工作流程
result = await execute_eleven_step_workflow(
    query_text="帮我设计一个增肌训练计划",
    user_id="123",
    domain="fitness"
)

# 获取统计信息
stats = get_workflow_statistics()
print(f"缓存命中率: {stats['cache_stats']['hit_rate']:.2%}")
print(f"平均响应时间: {stats['workflow_stats']['avg_duration_ms']}ms")

# 可视化DAG模板
dag_viz = visualize_dag_template("complete_training_plan", format="ascii")
print(dag_viz)
```

---

### 2️⃣ DAG编排器（enhanced_dag_orchestrator.py）

**职责**：基于模板执行DAG任务，管理依赖关系和并发

**核心类**：
- `EnhancedDAGOrchestrator` - 主编排器
- `DAGTask` - 任务定义
- `DAGExecutionResult` - 执行结果

**特性**：
- ✅ 依赖解析（自动拓扑排序）
- ✅ 并发执行（同层级任务并行）
- ✅ 错误恢复（失败任务降级）
- ✅ 性能监控（执行时间统计）

**调用示例**：
```python
from applications.fitness.enhanced_dag_orchestrator import EnhancedDAGOrchestrator

orchestrator = EnhancedDAGOrchestrator(
    template_manager=template_manager,
    mcp_orchestrator=mcp_tool_manager
)

result = await orchestrator.execute_template(
    template_id="complete_training_plan",
    user_profile={"age": 25, "goal": "增肌"},
    session_context={"query": "设计训练计划"}
)
```

---

### 3️⃣ DAG模板管理器（dag_template_system.py）

**职责**：管理所有DAG模板，提供模板匹配和检索

**核心类**：
- `DAGTemplateManager` - 模板管理器
- `DAGTemplate` - 模板定义
- `TemplateCategory` - 模板分类

**内置模板**：
1. `complete_training_plan` - 完整训练计划（P0）
2. `quick_consultation` - 快速咨询（P0）
3. `exercise_recommendation` - 动作推荐（P1）
4. `nutrition_advice` - 营养建议（P1）
5. `injury_assessment` - 损伤评估（P1）

**调用示例**：
```python
from applications.fitness.dag_template_system import DAGTemplateManager

manager = DAGTemplateManager()

# 获取模板
template = manager.get_template("complete_training_plan")

# 关键词匹配
template_id = manager.match_template_by_keywords("训练计划")
```

---

### 4️⃣ LLM决策引擎（llm_decision_engine.py）

**职责**：使用LLM智能选择最合适的DAG模板

**核心类**：
- `LLMDecisionEngine` - 决策引擎
- `DAGSelectionRequest` - 选择请求
- `DAGSelectionResult` - 选择结果

**决策流程**：
```
用户查询 → LLM分析意图 → 匹配模板 → 返回template_id + 置信度
```

**调用示例**：
```python
from applications.fitness.llm_decision_engine import LLMDecisionEngine

engine = LLMDecisionEngine(template_manager)

result = await engine.select_dag_template(
    DAGSelectionRequest(
        user_query="帮我设计训练计划",
        user_profile={"age": 25},
        available_templates=manager.get_all_templates()
    )
)

print(result.selected_template_id)  # "complete_training_plan"
print(result.confidence)            # 0.95
```

---

### 5️⃣ MCP工具注册表（mcp_tools/registry.py）

**职责**：管理15个Python内置MCP工具

**核心类**：
- `MCPToolRegistry` - 工具注册表

**工具分类**：

| 分类 | 工具数量 | 优先级 | 说明 |
|------|---------|--------|------|
| **训练** | 5个 | P0-P1 | 训练计划设计、分化设计、周期化 |
| **安全** | 3个 | P0 | 禁忌症检查、损伤风险评估、安全修改 |
| **动作** | 4个 | P0-P1 | 智能选择、替代查找、平衡器 |
| **营养** | 3个 | P1 | TDEE计算、摄入分析、膳食设计 |

**调用示例**：
```python
from applications.fitness.mcp_tools.registry import MCPToolRegistry
from applications.fitness.mcp_tools import initialize_all_tools

registry = MCPToolRegistry()
initialize_all_tools(registry, neo4j_client, qdrant_client, three_layer_engine)

# 调用工具
result = await registry.call_tool(
    "intelligent_exercise_selector",
    {
        "user_profile": {...},
        "target_muscles": ["chest", "triceps"],
        "equipment_available": ["barbell", "dumbbell"]
    }
)
```

---

### 6️⃣ 后端客户端（clients/backend_client.py）

**职责**：与Laravel后端通信，获取用户数据

**核心类**：
- `BackendClient` - 后端客户端

**主要方法**：
- `get_user_profile(user_id)` - 获取用户档案
- `get_user_membership(user_id)` - 获取会员信息
- `get_training_history(user_id)` - 获取训练历史

**调用示例**：
```python
from applications.fitness.clients.backend_client import BackendClient

client = BackendClient()
profile = await client.get_user_profile(123)
```

---

## 🔄 数据流

### 标准流程（非流式）

```
用户查询
    ↓
/v1/chat 路由
    ↓
execute_eleven_step_workflow()
    ├─ 步骤1-9: 数据准备和检索
    │   ├─ BackendClient.get_user_profile()
    │   ├─ LLMDecisionEngine.select_dag_template()
    │   ├─ EnhancedDAGOrchestrator.execute_template()
    │   │   └─ MCPToolRegistry.call_tool() × N
    │   └─ 汇总所有数据
    │
    ├─ 步骤10: LLM生成
    │   └─ call_deepseek() → 一次性返回
    │
    └─ 步骤11: 记录交互
    ↓
返回完整结果
```

### 流式流程

```
用户查询
    ↓
/v1/chat/stream 路由
    ↓
execute_eleven_step_workflow_stream()
    ├─ 步骤1-9: 数据准备和检索
    │   └─ yield {"type": "step", "step": N, "message": "..."}
    │
    ├─ 步骤10: LLM流式生成
    │   └─ async for chunk in call_deepseek_stream():
    │       ├─ 检测结构化数据 [TRAINING_PLAN:...]
    │       ├─ yield {"type": "structured_data", "data": {...}}
    │       └─ yield {"type": "chunk", "content": "文本片段"}
    │
    └─ 步骤11: 记录交互
        └─ yield {"type": "done", "data": {...}}
    ↓
SSE流式返回
```

---

## 📊 组件职责矩阵

| 组件 | 职责 | 依赖 | 被依赖 |
|------|------|------|--------|
| **workflow_executor** | 工作流程编排 | 所有组件 | chat路由 |
| **enhanced_dag_orchestrator** | DAG任务调度 | mcp_tools, template_manager | workflow_executor |
| **dag_template_system** | 模板管理 | 无 | orchestrator, decision_engine |
| **llm_decision_engine** | 模板选择 | template_manager, llm_client | workflow_executor |
| **mcp_tools/registry** | 工具管理 | neo4j, qdrant, three_layer | orchestrator |
| **clients/backend_client** | 后端通信 | httpx | workflow_executor |

---

## 🚀 使用指南

### 场景1：添加新的DAG模板

1. **在 `dag_template_system.py` 中定义模板**：

```python
DAGTemplate(
    template_id="my_new_template",
    name="我的新模板",
    category=TemplateCategory.TRAINING,
    description="模板描述",
    tasks=[
        DAGTask(
            tool_name="intelligent_exercise_selector",
            parameters={"target_muscles": ["chest"]},
            dependencies=[],
            priority=TaskPriority.CRITICAL
        )
    ],
    response_hint="请提供专业的分析",
    expected_output_length=2000
)
```

2. **在 `DAGTemplateManager.__init__()` 中注册**：

```python
self.templates["my_new_template"] = my_new_template
```

3. **测试模板**：

```python
result = await orchestrator.execute_template(
    template_id="my_new_template",
    user_profile={},
    session_context={}
)
```

---

### 场景2：添加新的MCP工具

1. **在 `mcp_tools/` 对应目录创建工具文件**：

```python
# mcp_tools/training/my_new_tool.py
from ..base_tool import BaseMCPTool

class MyNewTool(BaseMCPTool):
    def __init__(self, neo4j_client, qdrant_client):
        super().__init__(
            name="my_new_tool",
            description="工具描述"
        )
        self.neo4j = neo4j_client
    
    async def execute(self, **kwargs):
        # 实现工具逻辑
        return {"result": "..."}
```

2. **在 `mcp_tools/__init__.py` 中注册**：

```python
from .training.my_new_tool import MyNewTool

def initialize_all_tools(registry, neo4j_client, qdrant_client, three_layer_engine):
    # ... 其他工具
    registry.register_tool(MyNewTool(neo4j_client, qdrant_client))
```

3. **在DAG模板中使用**：

```python
DAGTask(
    tool_name="my_new_tool",
    parameters={"param1": "value1"},
    dependencies=[]
)
```

---

### 场景3：修改工作流程

**⚠️ 注意**：`workflow_executor.py` 是核心入口，修改需谨慎！

**推荐做法**：
1. 不要修改11步流程的顺序
2. 如需添加新步骤，在步骤6.5和步骤7之间插入
3. 保持向后兼容（同时维护标准版和流式版）

**示例：添加步骤6.6**：

```python
# 在步骤6.5之后添加
# ===== 步骤6.6：我的新步骤 =====
logger.info(f"[{request_id}] 步骤6.6: 我的新步骤")
my_result = await my_new_function()
logger.info(f"✅ [{request_id}] 步骤6.6完成")
```

---

## 🔍 扩展指南

### 添加新的应用领域

如果要添加新的应用领域（如营养、康复），建议：

1. **创建新的应用目录**：
```
src/applications/nutrition/
├── workflow_executor.py
├── dag_template_system.py
├── mcp_tools/
└── clients/
```

2. **复用框架层组件**：
- `framework/clients/llm_client.py`
- `framework/retrieval/`
- `framework/config/`

3. **定义领域特定的模板和工具**

---

## ✅ 代码清理完成

所有遗留代码已清理完毕，优秀组件已集成到新架构：

**已集成的组件**：
- ✅ `IntelligentUserCache` - 智能用户档案缓存（来自chat_service.py）
- ✅ `DAMLWorkflowMonitor` - 完整性能监控（来自chat_service.py）
- ✅ `DAGVisualizer` - DAG可视化支持（来自three_stage_orchestrator.py）

**已删除的遗留文件**：
- 🗑️ `fitness_app.py`
- 🗑️ `fitness_service.py`
- 🗑️ `fitness_dag_orchestrator.py`
- 🗑️ `chat_service.py`
- 🗑️ `three_stage_orchestrator.py`
- 🗑️ `intelligent_intent_matcher.py`
- 🗑️ `intent_templates.py`
- 🗑️ `complete_dag_system.py`
- 🗑️ `component_registrations.py`

**架构优化成果**：
- 📉 代码量减少50%（~3000行 → ~1500行）
- 🚀 单一入口，易于维护
- ✨ 功能更完整（流式输出、智能缓存、性能监控）
- 📊 完整的监控和可视化支持

---

## 📚 相关文档

- [11步工作流程详解](../../docs/02-核心架构/03-完整工作流程.md)
- [DAG编排系统设计](../../docs/02-核心架构/08-DAG编排系统.md)
- [MCP工具开发指南](../../docs/04-开发指南/XX-MCP工具开发指南.md)
- [流式输出实现](../../docs/04-开发指南/42-长文本输出架构方案.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-18  
**版本**: v1.0.0
