# daml-rag-server 开发规则

> 本文件为 AI 服务子项目专属规则，通用规则见根仓库 `CLAUDE.md`。

## 技术栈

- **框架**: FastAPI + DAML-RAG 自研框架
- **Python**: 3.11（容器内）
- **向量库**: Qdrant (`fitness_qdrant`，端口 6333/6334，1024维 GTE-Large-zh)
- **图数据库**: Neo4j (`fitness_neo4j`，端口 7474/7687，4,246节点)
- **运行环境**: `fitness_daml_rag` 容器（端口 8001）
- **LLM**: Anthropic Claude haiku-4.5（主）→ DeepSeek（备）→ Template（兜底）

## 测试命令

```bash
# 单元测试（必须在容器内运行）
docker exec fitness_daml_rag python -m pytest tests/ -x -v

# 指定测试文件
docker exec fitness_daml_rag python -m pytest tests/test_specific.py -v

# 输出重定向（Windows 后台模式）
docker exec fitness_daml_rag python -m pytest tests/ > /f/build_body/_output.txt 2>&1
```

## 执行模式

- **DAG 模式**（默认）：固定编排，所有用户可用，三段式架构（LLM决策→程序执行→LLM综合）
- **Agent 模式**：动态决策，energy+ 会员专属，DeepSeek function calling

## MCP 工具架构

18个 Python 内置工具（1-5ms）+ 1个 stdio MCP 服务（用户档案，5-10ms）

**P0 核心（5个）**：intelligent_exercise_selector, contraindications_checker, injury_risk_assessor, muscle_group_volume_calculator, tdee_calculator

**P1 建议（10个）**：professional_program_designer, exercise_alternative_finder, movement_pattern_balancer, intelligent_weight_calculator, safe_exercise_modifier, nutrition_intake_analyzer, meal_plan_designer, exercise_nutrition_optimization, record_training_feedback, postural_assessor

**P2 扩展（3个）**：periodized_program_designer, training_split_designer, find_similar_training_cases

## 代码规范

- 配置统一用环境变量 `os.getenv()`，禁止硬编码密码/密钥
- 异常捕获必须指定具体类型，禁止裸 `except:` 或 `except Exception`
- LLM 调用统一走 `llm_client.py` → `llm_fallback_manager.py` 降级链
- 容器内连接：Qdrant 用 `qdrant`、Neo4j 用 `bolt://neo4j:7687`（不是 localhost）
- 函数单一职责，≤50行，≤4参数，Python 必须完整类型注解

## 环境变量（关键）

- `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` / `ANTHROPIC_ENABLED` — Kiro RS 代理
- `BYPASS_RATE_LIMIT_FOR_INTERNAL=true` — 内部调用免限流
- `INTERNAL_API_TOKEN=crewai-internal-secret-2025` — 内部服务认证
- `LEGACY_AUTH_ENABLED=true` — 兼容旧认证

## 部署

- **本地**: Docker 容器 `fitness_daml_rag`（端口 8001）
- **生产**: Zeabur（阿里云北京），Git 推送自动部署
- **域名**: ai.yuzhen-fitness.cn（仅内网，前端不直连）
- **健康检查**: `/api/health`, `/health/components`, `/health/metrics`

## 关键目录

```
src/framework/               # 核心框架（clients, middleware, pipeline）
src/framework/clients/       # LLM 客户端 + 降级管理器
src/tools/                   # 18 个 MCP 工具
src/applications/fitness/services/  # 16 个服务层组件
src/dag/                     # DAG 编排定义
src/agent/                   # Agent 模式逻辑
config/                      # 配置文件
tests/                       # 测试目录
```

## 按需加载参考

| 场景 | 参考文件 |
|------|---------|
| 完整工作流程 | `docs/02-核心架构/03-完整工作流程.md` |
| Neo4j 数据库结构 | `docs/02-核心架构/02-数据层/02-Neo4j数据库结构.md` |
| MCP 工具架构详细版 | `docs/02-核心架构/06-MCP工具架构.md` |
| MCP 工具列表 | `.kiro/steering/mcp-tools-reference.md` |
| LLM 客户端源码 | `src/framework/clients/llm_client.py` |
| LLM 降级管理器 | `src/framework/clients/llm_fallback_manager.py` |
| Zeabur 环境变量 | `.kiro/steering/zeabur-env-vars.md` |
