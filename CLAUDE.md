# daml-rag-server 开发规则

> 本文件为 AI 服务子项目专属规则，通用规则见根仓库 `CLAUDE.md`。

## 技术栈

- **框架**: FastAPI + DAML-RAG 自研框架
- **Python**: 3.11（容器内）
- **向量库**: Qdrant (`fitness_qdrant`，端口 6333/6334)
- **图数据库**: Neo4j (`fitness_neo4j`，端口 7474/7687)
- **运行环境**: `fitness_daml_rag` 容器（端口 8001）

## 测试命令

```bash
# 单元测试（必须在容器内运行）
docker exec fitness_daml_rag python -m pytest tests/ -x -v

# 指定测试文件
docker exec fitness_daml_rag python -m pytest tests/test_specific.py -v

# 输出重定向（Windows 后台模式）
docker exec fitness_daml_rag python -m pytest tests/ > /f/build_body/_output.txt 2>&1
```

## 代码规范

- 配置统一用环境变量 `os.getenv()`，禁止硬编码密码/密钥
- 异常捕获必须指定具体类型，禁止裸 `except:` 或 `except Exception`
- LLM 调用统一走 `llm_client.py` → `llm_fallback_manager.py` 降级链
- 容器内连接：Qdrant 用 `qdrant`、Neo4j 用 `bolt://neo4j:7687`（不是 localhost）

## 执行模式

- **DAG 模式**（默认）：固定编排，所有用户可用
- **Agent 模式**：动态决策，energy+ 会员专属，DeepSeek function calling

## 关键目录

```
src/framework/           # 核心框架（clients, middleware, pipeline）
src/framework/clients/   # LLM 客户端 + 降级管理器
src/tools/               # 18 个 MCP 工具
src/dag/                 # DAG 编排定义
src/agent/               # Agent 模式逻辑
config/                  # 配置文件
tests/                   # 测试目录
```

## 环境变量（关键）

- `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL` — Kiro RS 代理
- `BYPASS_RATE_LIMIT_FOR_INTERNAL=true` — 内部调用免限流
- `INTERNAL_API_TOKEN=crewai-internal-secret-2025` — 内部服务认证
