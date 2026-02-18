# DAML-RAG Server 测试与脚本命名规则

**版本**: v1.0.0 | **创建日期**: 2026-02-18 | **维护者**: 薛小川

---

## 1. 目录结构

### tests/ 目录

```
tests/
├── unit/                    # 单元测试（mock所有外部依赖）
│   ├── mcp_tools/           # MCP工具单元测试
│   ├── services/            # 服务层单元测试
│   └── llm_components/      # LLM组件单元测试
├── integration/             # 集成测试（需要Docker服务）
├── e2e/                     # 端到端测试（完整工作流）
├── performance/             # 性能/压力测试
├── security/                # 安全测试
├── utility/                 # 工具函数测试
├── legacy_task*/            # 历史任务测试（只读，不新增）
└── archived/                # 已归档（不参与pytest收集）
```

### scripts/ 目录

```
scripts/
├── analysis/                # 数据分析脚本 (analyze_*.py)
├── checks/                  # 数据检查脚本 (check_*.py)
├── cleanup/                 # 数据清理脚本 (cleanup_*.py, clean_*.py)
├── data_processing/         # 数据处理脚本 (enrich_*, extract_*, entity_*)
├── data_supplement/         # 数据补充脚本 (ACSM/NSCA标准等)
├── data_import/             # 数据导入脚本 (ingest_*, import_*)
├── diagnostics/             # 诊断脚本 (diagnose_*, debug_*)
├── migration/               # 数据迁移脚本 (migrate_*.py)
├── mcp_tool_tests/          # MCP工具手动测试脚本
├── neo4j_operations/        # Neo4j数据库操作脚本
├── performance/             # 性能优化脚本
├── training_knowledge/      # 训练知识处理脚本
├── validation/              # 系统验证脚本
├── data/                    # 静态数据文件
└── archived/                # 已归档（历史脚本）
```

---

## 2. 文件命名规则

### 测试文件

| 规则 | 格式 | 示例 |
|------|------|------|
| 单元测试 | `test_{module_name}.py` | `test_contraindications_checker.py` |
| 集成测试 | `test_{feature}_integration.py` | `test_streaming_metrics_integration.py` |
| E2E测试 | `test_{workflow}_e2e.py` | `test_greeting_workflow.py` |
| 性能测试 | `test_{feature}_performance.py` | `test_e2e_performance.py` |

### 脚本文件

| 类型 | 前缀 | 示例 |
|------|------|------|
| 分析 | `analyze_` | `analyze_neo4j_full_structure.py` |
| 检查 | `check_` | `check_neo4j_stats.py` |
| 清理 | `cleanup_` / `clean_` | `cleanup_neo4j_duplicates.py` |
| 诊断 | `diagnose_` / `debug_` | `diagnose_missing_relationships.py` |
| 迁移 | `migrate_` | `migrate_qdrant.py` |
| 导入 | `ingest_` / `import_` | `ingest_markdown_knowledge.py` |
| 验证 | `verify_` / `validate_` | `verify_neo4j_structure.py` |
| 测试 | `test_` | `test_reranker.py` |

---

## 3. 通用规则

1. **语言**: 目录名和文件名一律使用英文，禁止中文
2. **分隔符**: 使用下划线 `_`，禁止连字符 `-` 或空格
3. **大小写**: 全小写，禁止驼峰命名
4. **前缀**: 脚本文件必须使用上述类型前缀
5. **历史文件**: 不再使用的文件移到 `archived/`，不要删除（保留历史记录）
6. **新增目录**: 需要新增子目录时，先在本文档中登记

---

## 4. conftest.py 规则

- 每个测试子目录可以有自己的 `conftest.py`
- 公共 fixtures 放在 `tests/conftest.py`
- 禁止在 conftest.py 中导入具体测试模块

---

## 5. legacy_task* 目录说明

以 `legacy_task` 开头的目录是历史任务的测试文件，保留用于回归验证：

| 目录 | 原名 | 内容 |
|------|------|------|
| `legacy_task06_training_knowledge` | 任务6-训练知识导入 | 训练周期计算测试 |
| `legacy_task08_enhanced_logging` | 任务8-增强日志系统 | 日志验证/监控API测试 |
| `legacy_task09_streaming_output` | 任务9-流式输出测试 | 流式输出完整性测试 |
| `legacy_task10_performance_monitoring` | 任务10-性能优化和监控 | 性能基准/功能验证 |
| `legacy_task18_user_profile` | 任务18-用户档案管理 | 用户档案CRUD测试 |
| `legacy_task23_data_standards` | 任务23-数据标准 | 数据标准验证 |

这些目录只读，不新增文件。新测试应放到对应的 `unit/`、`integration/` 或 `e2e/` 目录。
