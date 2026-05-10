# DAML-RAG Server

**版本**: v3.0.0 (构建号 #55)
**更新日期**: 2026-05-11
**状态**: MCP Server + 三层检索引擎 · Docker 容器部署 · Zeabur 生产环境

---

## 项目定位

DAML-RAG Server 是玉珍健身的 **MCP Server + 三层检索引擎**。v3.0 架构迁移后，Agent 智能层（Skill 选择、对话编排、工具调度）已迁移至 YuzhenFork（TypeScript），本项目精简为：

1. **MCP Server 入口** — 通过 stdio transport 暴露 10 个健身领域工具
2. **三层检索引擎** — 向量语义 + 图谱关系 + 业务规则，配合 4 项检索优化
3. **数据基础设施** — Neo4j 图数据库 + Qdrant 向量库 + Redis 缓存

### 架构图

```
YuzhenFork Agent (TypeScript)
        │
        │ stdio (MCP Protocol)
        ▼
┌─────────────────────────────────────────────────┐
│  DAML-RAG MCP Server (FastMCP)                  │
│                                                 │
│  10 个 MCP 工具                                  │
│    ├── search_exercises        动作语义搜索       │
│    ├── get_exercise_detail     动作详情           │
│    ├── search_foods            食物营养搜索       │
│    ├── get_muscle_volume       肌肉训练容量       │
│    ├── get_training_knowledge  训练知识检索       │
│    ├── get_exercise_for_muscle 肌群动作推荐       │
│    ├── check_contraindications 禁忌症检查         │
│    ├── get_user_profile        用户档案           │
│    ├── get_user_history        对话历史           │
│    └── graphrag_query          GraphRAG 综合检索  │
│                                                 │
├─────────────────────────────────────────────────┤
│  三层检索引擎 + 检索优化                          │
│                                                 │
│  QueryReshaper → L1 向量 → L2 图谱 →            │
│  CalibratedFusion → L3 规则 → GraphConvRerank   │
│                                                 │
│  InMemoryHotCache (<5ms)                        │
├─────────────────────────────────────────────────┤
│  数据层                                          │
│  Qdrant (4,585 向量) │ Neo4j (4,246 节点) │ Redis │
└─────────────────────────────────────────────────┘
```

---

## MCP 工具列表

| # | 工具名 | 说明 | 数据源 |
|---|--------|------|--------|
| 1 | `search_exercises` | 动作语义搜索（名称/肌群/器械/难度） | Qdrant + Neo4j |
| 2 | `get_exercise_detail` | 单个动作完整信息（步骤/注意事项/变体） | Neo4j |
| 3 | `search_foods` | 食物营养搜索（名称/分类/营养素范围） | Qdrant + Neo4j |
| 4 | `get_muscle_volume` | 肌肉训练容量参考（MEV/MAV/MRV） | Neo4j |
| 5 | `get_training_knowledge` | 训练原则/周期化知识检索 | Qdrant |
| 6 | `get_exercise_for_muscle` | 指定肌群的推荐动作列表 | Neo4j |
| 7 | `check_contraindications` | 动作禁忌症/伤病风险检查 | Neo4j 规则 |
| 8 | `get_user_profile` | 获取用户健身档案 | MySQL (via PHP API) |
| 9 | `get_user_history` | 获取对话历史上下文 | MySQL (via PHP API) |
| 10 | `graphrag_query` | GraphRAG 综合检索（三层融合） | 全部 |

---

## 三层检索流程

```
用户查询
    │
    ▼
┌─────────────────┐
│ QueryReshaper   │  用户档案偏置查询向量（性别/目标/水平加权）
└────────┬────────┘
         ▼
┌─────────────────┐
│ InMemoryHotCache│  热数据命中 → 直接返回 (<5ms)
└────────┬────────┘
         │ miss
         ▼
┌─────────────────┐
│ L1: 向量检索     │  Qdrant GTE-Large-zh 1024维语义匹配
└────────┬────────┘
         ▼
┌─────────────────┐
│ L2: 图谱检索     │  Neo4j Cypher 关系推理（肌群→动作→器械）
└────────┬────────┘
         ▼
┌──────────────────────┐
│ CalibratedFusion     │  PhaseGraph 论文：PIT 校准 + Boltzmann 温度融合
│ (L1 + L2 结果融合)    │  替代简单 RRF，自适应权重
└────────┬─────────────┘
         ▼
┌─────────────────┐
│ L3: 规则引擎     │  业务约束验证（禁忌症/容量上限/安全规则）
└────────┬────────┘
         ▼
┌─────────────────┐
│ GraphConvRerank │  Non-param GC 论文：图卷积重排序
│                 │  利用结果间图结构关系优化排序
└────────┬────────┘
         ▼
    最终结果
```

---

## 快速启动

### Docker（开发环境）

```bash
# 容器名: fitness_daml_rag，端口: 8001
# 作为 MCP Server 启动（YuzhenFork 通过 stdio 调用）
docker exec fitness_daml_rag python -m src.mcp_server

# 运行测试
docker exec fitness_daml_rag python -m pytest tests/ -v
```

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 MCP Server（stdio transport）
python -m src.mcp_server

# 启动 HTTP API（兼容旧接口，逐步废弃）
uvicorn src.api.main:app --host 0.0.0.0 --port 8001
```

### Zeabur（生产环境）

- 仓库: `vivy1024/daml-rag-server`
- 分支: `main`（自动部署）
- 环境变量: 见 `.kiro/steering/zeabur-env-vars.md`

---

## Feature Flags

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `MCP_SERVER_ENABLED` | `true` | MCP Server 主开关 |
| `CALIBRATED_FUSION_ENABLED` | `true` | CalibratedFusion 融合（关闭则回退 RRF） |
| `GRAPH_CONV_RERANK_ENABLED` | `true` | GraphConvRerank 重排序 |
| `QUERY_RESHAPER_ENABLED` | `true` | QueryReshaper 查询偏置 |
| `HOT_CACHE_ENABLED` | `true` | InMemoryHotCache 热缓存 |
| `HOT_CACHE_TTL` | `300` | 热缓存 TTL（秒） |
| `LEGACY_HTTP_API_ENABLED` | `true` | 旧 HTTP API 兼容（逐步废弃） |

---

## 目录结构

```
src/
├── mcp_server.py              # MCP Server 入口（FastMCP，10 个工具定义）
├── api/                       # HTTP API（旧接口兼容，逐步废弃）
│   ├── main.py                # FastAPI app
│   └── routes/                # 路由（health/graphrag）
├── framework/                 # 核心框架
│   ├── retrieval/             # 检索引擎
│   │   ├── three_layer/       # 三层检索核心
│   │   │   ├── engine.py      # ThreeLayerEngine 主入口
│   │   │   ├── layer1_vector.py       # L1 向量检索
│   │   │   ├── layer2_graph.py        # L2 图谱检索
│   │   │   ├── layer3_rules.py        # L3 规则引擎
│   │   │   ├── calibrated_fusion.py   # CalibratedFusion（PIT + Boltzmann）
│   │   │   ├── graph_conv_rerank.py   # GraphConvRerank（图卷积重排序）
│   │   │   ├── query_reshaper.py      # QueryReshaper（档案偏置）
│   │   │   ├── result_merger.py       # 结果合并
│   │   │   ├── neo4j_manager.py       # Neo4j 查询管理
│   │   │   ├── fallback.py            # 降级策略
│   │   │   └── models.py             # 数据模型
│   │   └── eval/              # 检索评测（NDCG@K + Recall@K）
│   ├── clients/               # 数据库客户端（Neo4j/Qdrant/MySQL）
│   ├── mcp/                   # MCP 缓存与错误处理
│   ├── safety/                # 安全规则
│   ├── auth/                  # 认证
│   ├── config/                # 配置管理
│   └── models/                # 数据模型
├── harness_v2/                # Harness 安全层（输出校验保留）
├── applications/              # 旧业务逻辑（MCP 工具实现）
│   └── fitness/
│       └── mcp_tools/         # MCP 工具底层实现
└── utils/                     # 工具函数
```

---

## 数据基础设施

### Qdrant 向量库

| 集合 | 数量 | 用途 |
|------|------|------|
| `fitness_exercises_v2` | 1,596 | 健身动作语义搜索 |
| `food_nutrition_vector` | 1,851 | 食物营养匹配 |
| `training_knowledge` | 43 | 训练周期化原则 |

### Neo4j 图数据库

- **4,246 节点**: Exercise(1,603) + Muscle(53) + Food(1,880) + Nutrient(29) + Equipment(17) + 其他
- **61,507 关系**: CONTAINS_NUTRIENT + TARGETS_PRIMARY/SECONDARY + REQUIRES
- **核心能力**: 肌肉训练容量(MEV/MAV/MRV) + 动作-肌肉映射 + 禁忌症关系

---

## 已删除模块（v3.0 迁移）

以下模块已在 v3.0 中删除（30,822 行），职责迁移至 YuzhenFork：

- `src/agent_v2/` — Agent 状态图 + LangGraph 节点
- `src/skills/` — 10 个 Skill YAML + Router + Executor
- `src/applications/fitness/workflow/` — 11 步 DAG 编排
- `src/applications/fitness/dag/` — DAG 模板选择
- `src/applications/fitness/orchestration/` — 编排层

---

## 测试

```bash
# 单元测试
docker exec fitness_daml_rag python -m pytest tests/unit/ -v

# 检索引擎测试
docker exec fitness_daml_rag python -m pytest tests/unit/test_three_layer/ -v

# 评测（NDCG@K + Recall@K）
docker exec fitness_daml_rag python -m pytest tests/eval/ -v
```

---

**维护者**: 薛小川 (vivy1024)
**许可**: Private
