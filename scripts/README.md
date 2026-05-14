# DAML-RAG Scripts 目录

**版本**: v3.0.0
**更新日期**: 2026-05-14
**维护者**: 薛小川

---

## 目录结构

```
scripts/
├── v3_export/            # v3 浪潮引擎数据导出（活跃使用）
├── neo4j/                # Neo4j 数据库运维脚本
├── cleanup/              # 数据库清理工具
├── data_supplement/      # 数据补充脚本（Ollama 翻译等）
├── training_knowledge/   # 训练知识导入
├── user_management/      # 用户管理
├── data/                 # 脚本数据文件
├── archived/             # 已归档的旧脚本（120+个）
└── README.md
```

---

## 活跃脚本

### v3_export/ — v3 数据导出

v3 浪潮引擎的数据准备脚本，从 Neo4j/Qdrant 导出为本地 .npy + .json 文件。

```bash
# 导出向量数据
docker exec fitness_daml_rag python -m scripts.v3_export.export_vectors

# 导出图谱数据
docker exec fitness_daml_rag python -m scripts.v3_export.export_graph

# 构建图谱存储
docker exec fitness_daml_rag python -m scripts.v3_export.build_graph_store
```

### neo4j/ — 数据库运维

Neo4j 数据库验证、修复、查询脚本。

```bash
# 验证数据库结构
docker exec fitness_daml_rag python scripts/neo4j/verify_neo4j_structure.py

# 检查所有关系
docker exec fitness_daml_rag python scripts/neo4j/check_all_relationships.py
```

### cleanup/ — 数据清理

```bash
# 清理 Neo4j 重复数据
docker exec fitness_daml_rag python scripts/cleanup/cleanup_neo4j_duplicates.py
```

### training_knowledge/ — 训练知识

```bash
# 导入训练知识到 Neo4j
docker exec fitness_daml_rag python scripts/training_knowledge/import_training_knowledge_to_neo4j.py
```

---

## 归档说明

`archived/` 目录包含 v1/v2 时期的一次性脚本，按类别组织：

| 子目录 | 内容 |
|--------|------|
| `one-off-fixes/` | 数据修复脚本（fix_*.py, sync_*.py 等） |
| `one-off-tests/` | 旧测试和验证脚本（已被 tests/ 替代） |
| `one-off-data/` | 数据迁移、导入、导出脚本 |
| `batch-scripts/` | Windows/Linux 批处理脚本 |
| `docs-tools/` | 文档管理工具 |
| `legacy-chinese-dirs/` | 旧的中文命名任务目录 |
| `analysis/` | 分析脚本 |
| `diagnostics/` | 诊断脚本 |
| `checks/` | 检查脚本 |
| `migration/` | 数据库迁移 |
| `neo4j_migrations/` | Neo4j 迁移 |
| `neo4j_operations/` | Neo4j 操作 |
| `data_processing/` | 数据处理 |
| `mcp_tool_tests/` | 旧 MCP 工具测试 |

这些脚本保留作为历史参考，不再日常使用。

---

## 测试

v3 引擎的测试已迁移到标准 pytest 结构：

```bash
# 单元测试（本地）
python -m pytest tests/unit/test_v3_wave_engine.py -v

# 集成测试（容器内）
docker exec fitness_daml_rag bash -c "DATA_DIR=/app/data/v3 python -m pytest tests/integration/test_v3_integration.py -v"
```
