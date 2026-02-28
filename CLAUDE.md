# daml-rag-server 开发规则

> 本文件为 AI 服务子项目专属规则，通用规则见根仓库 `CLAUDE.md`。

## 技术栈

- **框架**: FastAPI + DAML-RAG 自研框架 | **Python**: 3.11（容器内）
- **向量库**: Qdrant (1024维 GTE-Large-zh) | **图数据库**: Neo4j (4,264节点/65,147关系)
- **运行环境**: `fitness_daml_rag` 容器（端口 8001）
- **LLM**: Anthropic Claude haiku-4.5（主）→ DeepSeek（备）→ Template（兜底）

## 测试命令

```bash
docker exec fitness_daml_rag python -m pytest tests/ -x -v
# Windows 后台模式
docker exec fitness_daml_rag python -m pytest tests/ > /f/build_body/_output.txt 2>&1
```

## 执行模式

- **DAG 模式**（默认）：固定编排，所有用户，三段式（LLM决策→程序执行→LLM综合）
- **Agent 模式**：动态决策，energy+ 会员，DeepSeek function calling

## MCP 工具

18个 Python 内置工具(1-5ms) + 1个 stdio MCP(用户档案,5-10ms)

- **P0 核心(5)**: intelligent_exercise_selector, contraindications_checker, injury_risk_assessor, muscle_group_volume_calculator, tdee_calculator
- **P1 建议(10)**: professional_program_designer, exercise_alternative_finder, movement_pattern_balancer, intelligent_weight_calculator, safe_exercise_modifier, nutrition_intake_analyzer, meal_plan_designer, exercise_nutrition_optimization, record_training_feedback, postural_assessor
- **P2 扩展(3)**: periodized_program_designer, training_split_designer, find_similar_training_cases

## 代码规范

- 配置统一用 `os.getenv()`，禁止硬编码密码/密钥
- 异常捕获必须指定具体类型，禁止裸 `except:`
- LLM 调用统一走 `llm_client.py` → `llm_fallback_manager.py` 降级链
- 容器内连接：Qdrant→`qdrant`、Neo4j→`bolt://neo4j:7687`（不是localhost）
- 函数 ≤50行，≤4参数，完整类型注解

## 部署

- **本地**: Docker `fitness_daml_rag`(8001) | **生产**: Zeabur(阿里云北京)
- **域名**: ai.yuzhen-fitness.cn（仅内网）| **健康检查**: `/health`

## Neo4j 同步工具

```bash
# 全量对比+同步（幂等）
docker exec fitness_daml_rag bash -c "python scripts/neo4j_migrations/sync.py --check"
docker exec fitness_daml_rag bash -c "python scripts/neo4j_migrations/sync.py --sync"
```

同步注意：Exercise 用 `id` 匹配，`CONTRAINDICATED_FOR` 是安全核心(6,371条)必须保持同步。

## 关键目录

```
src/framework/clients/       # LLM 客户端 + 降级管理器
src/tools/                   # 18 个 MCP 工具
src/applications/fitness/services/  # 16 个服务层
src/dag/                     # DAG 编排
src/agent/                   # Agent 模式
scripts/neo4j_migrations/    # Neo4j 同步 + Migration
```

## 按需加载参考

| 场景 | 参考文件 |
|------|---------|
| ⭐ 枚举映射（三端数据流） | `docs/03-代码参考/12-枚举映射说明.md` |
| 数据库连接信息（含生产） | `.kiro/steering/db-connections.md` |
| MCP 工具列表 | `.kiro/steering/mcp-tools-reference.md` |
| Zeabur 环境变量 | `.kiro/steering/zeabur-env-vars.md` |
| 跨端枚举契约 | `.kiro/steering/cross-stack-data-contract.md` |

> ⚠️ 涉及枚举值、字段名映射时，必须先读 `12-枚举映射说明.md`。
