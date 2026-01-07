# 归档目录

此目录包含重构前的原始大文件备份。

## 归档文件

| 文件 | 原始行数 | 归档日期 | 迁移目标 |
|------|----------|----------|----------|
| workflow_executor.py | 3191行 | 2025-12-28 | workflow/ 模块 |
| enhanced_dag_orchestrator.py | 2191行 | 2025-12-28 | dag/ 模块 |
| neo4j_field_mapping.py | ~200行 | 2025-12-28 | config/field_mapping.py |

## 迁移说明

### workflow_executor.py → workflow/

原始文件被拆分为以下模块：
- `workflow/state.py`: 状态定义（WorkflowState TypedDict）
- `workflow/nodes.py`: 节点函数（每个步骤一个纯函数）
- `workflow/edges.py`: 边定义（条件路由逻辑）
- `workflow/graph.py`: 图构建（StateGraph 组装）
- `workflow/executor.py`: 同步执行器
- `workflow/stream_executor.py`: 流式执行器
- `workflow/singletons.py`: 单例管理

### enhanced_dag_orchestrator.py → dag/

原始文件被拆分为以下模块：
- `dag/models.py`: 数据模型定义
- `dag/orchestrator.py`: 核心编排逻辑
- `dag/task_executor.py`: 任务执行器
- `dag/result_aggregator.py`: 结果汇总器
- `dag/parameter_mapper.py`: 参数映射器

### neo4j_field_mapping.py → config/field_mapping.py

字段映射功能迁移到配置模块，增强功能：
- 支持从 YAML 配置文件加载映射规则
- 支持双向映射（MCP ↔ Neo4j）
- 支持动态添加映射规则

## 向后兼容

所有原始导入路径通过 `__init__.py` 重新导出保持兼容：

```python
# 这些导入仍然有效
from applications.fitness.workflow_executor import execute_eleven_step_workflow
from applications.fitness.enhanced_dag_orchestrator import EnhancedDAGOrchestrator
from applications.fitness.neo4j_field_mapping import map_exercise_fields
```

## 注意事项

- 这些文件仅作为备份保留，不应在新代码中使用
- 如需修改功能，请修改对应的新模块
- 归档文件可能在未来版本中删除

---
归档日期: 2025-12-28
版本: v1.0.0
