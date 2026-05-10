# 03-MCP Server 层

**版本**: v3.0.0
**更新日期**: 2026-05-09
**状态**: ✅ v3.0 架构重构完成

---

## 📋 模块说明

本模块包含 DAML-RAG v3.0 的 MCP Server 层架构文档。

v3.0 中，DAML-RAG 的职责精简为：
- **MCP Server**：通过 stdio transport 被 YuzhenFork Agent 调用
- **三层检索引擎**：Qdrant 向量检索 + Neo4j 图检索 + 规则约束检索
- **18 个 MCP 工具实现**：健身领域专业工具
- **健康检查 API**：服务状态监控

> ⚠️ **v3.0 架构变更说明**：
> 旧的 DAG 编排器、三段式编排架构、工作流执行器已在 v3.0 中**全部删除**。
> 编排职责已上移至 YuzhenFork Agent Loop（Skills-first Agent）。
> 删除的模块：`agent_v2/`, `skills/`, `workflow/`, `dag/`, `orchestration/`, `harness/`, `context/`

---

## 🏗️ MCP Server 入口

### src/mcp_server.py

DAML-RAG v3.0 的唯一入口点，基于 FastMCP 框架实现。

**核心特性**：
- **FastMCP 框架**：使用 `mcp` 库的 FastMCP 类
- **stdio transport**：通过标准输入/输出与 YuzhenFork Agent 通信
- **延迟初始化**：客户端（Qdrant、Neo4j、Redis、MySQL）在首次调用时才初始化，减少启动时间
- **10 个暴露的 MCP 工具**：对外暴露的核心工具接口

### 暴露的 MCP 工具

| # | 工具名 | 功能 |
|---|--------|------|
| 1 | `get_user_profile` | 获取用户健身档案 |
| 2 | `contraindications_checker` | 禁忌症检查 |
| 3 | `injury_risk_assessor` | 损伤风险评估 |
| 4 | `intelligent_exercise_selector` | 智能动作选择 |
| 5 | `muscle_group_volume_calculator` | 肌群容量计算 |
| 6 | `professional_program_designer` | 专业计划设计 |
| 7 | `nutrition_advisor` | 营养建议 |
| 8 | `retrieval_search` | 三层检索搜索 |
| 9 | `health_check` | 健康检查 |
| 10 | `movement_pattern_balancer` | 动作模式平衡 |

### 延迟初始化客户端

```python
# 客户端在首次工具调用时初始化
@mcp.tool()
async def get_user_profile(user_id: str):
    client = await get_or_init_client("mysql")  # 延迟初始化
    ...
```

支持的客户端：
- **Qdrant**：向量数据库（语义检索）
- **Neo4j**：图数据库（关系检索）
- **Redis**：缓存（热数据 + 会话）
- **MySQL**：关系数据库（用户档案）

---

## 📚 文档列表

### 核心架构文档

1. **01-三段式编排器架构.md** — ⚠️ 已过时，仅供历史参考
2. **03-MCP工具架构.md** — MCP 工具的分类和功能说明（仍有参考价值）
3. **04-MCP架构演进历史.md** — 架构演进历程（含 v3.0 精简记录）

---

## 🔗 相关模块

- **01-系统架构**: 了解 MCP Server 在整体系统中的位置
- **02-数据层**: 了解三层检索如何访问数据
- **06-优化层**: 了解 v3.0 新增的优化模块（CalibratedFusion、GraphConvRerank 等）
- **03-代码参考/03-MCP工具实现**: 查看 MCP 工具的具体实现代码

---

## 🎯 快速导航

- 想了解 MCP Server 如何启动? → 查看 `src/mcp_server.py`
- 想了解 MCP 工具有哪些? → 阅读 `03-MCP工具架构.md`
- 想了解架构演进历史? → 阅读 `04-MCP架构演进历史.md`
- 想了解 v3.0 优化模块? → 查看 `../06-优化层/`

---

**维护者**: 薛小川
**最后更新**: 2026-05-09
