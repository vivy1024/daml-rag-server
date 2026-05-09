# DAML-RAG Server

**版本**: v2.0.0 (构建号 #58)
**更新日期**: 2026-05-10
**状态**: ✅ 生产运行 · Docker容器部署 · Zeabur生产环境

---

## 📋 概述

DAML-RAG Server 是玉珍健身的核心 AI 服务，实现了 **Skills-first Autonomous Agent** 架构。通过 LangGraph 状态图驱动 Skill 选择与工具链执行，配合 Harness 安全层和 HITL 人机协作，提供专业、安全、个性化的健身指导。

### 🎯 核心价值

- **Skills-first Agent**: LLM 自主选择 Skill → 工具链自动执行 → 输出校验，替代旧的固定 11 步 workflow
- **Harness 安全层**: PreSkillPolicy + ToolAllowlist + OutputVerifier，fail-closed 设计
- **HITL 人机协作**: 高风险操作自动中断等待用户确认（LangGraph interrupt/resume）
- **三层检索**: 向量语义匹配 + 图谱关系推理 + 业务约束验证
- **知识图谱**: Neo4j(4,246节点) + Qdrant(4,585向量/1024维GTE-Large-zh)
- **多模型池**: Anthropic Claude（主）→ DeepSeek/GLM/Qwen（备）→ Template（兜底）

---

## 🏗️ 系统架构

### Agent v2 流程（6 步）

```
1. 接收请求 + 恢复线程 (init_thread)
2. 意图理解 + Skill 选择 (skill_select) — LLM function calling
3. 安全策略 + HITL (safety_check) — PreSkillPolicy + interrupt
4. Skill 执行 (skill_execute) — 工具链并行/串行执行
5. 输出校验 + LLM 综合 (output_generate) — OutputVerifier + 自然语言生成
6. 记录 + 评测采集 (record) — Checkpoint + HarnessTracer
```

### LangGraph 状态图

```
init_thread → skill_select → safety_check ─┬─ (pass) → skill_execute → output_generate → record
                                            └─ (HITL)  → [interrupt] → resume → skill_execute → ...
                    ↑                       └─ (deny)  → output_generate (降级回答)
                    └── direct_reply ←── (简单问候/闲聊)
```

### 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| Agent v2 | `src/agent_v2/` | 状态图 + 6 节点 + SSE 流式输出 |
| Skills | `src/skills/` | 10 个 Skill YAML + Loader + Router + Executor |
| Harness v2 | `src/harness_v2/` | Policy + Allowlist + Verifier + Tracer |
| Framework | `src/framework/` | LLMPool + Checkpointer + Auth + 三层检索 |
| API | `src/api/` | FastAPI 路由（chat/thread/approval/health） |
| 旧 Workflow | `src/applications/` | 11 步 DAG 编排（feature flag 控制，逐步废弃） |

### 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| AI 引擎 | Anthropic Claude | haiku-4.5 / sonnet-4 |
| Agent 框架 | LangGraph | 0.4+ |
| 向量检索 | Qdrant + GTE-Large-zh | 1024维 |
| 知识图谱 | Neo4j | 7.4.0 |
| 数据库 | MySQL + Redis | 8.4.0 / 7.2.5 |
| 后端框架 | FastAPI + Python | 3.11 |
| 流式协议 | SSE (Server-Sent Events) | - |

---

## 🧠 Skills 体系

10 个核心 Skill，每个定义为 YAML 文件（`src/skills/definitions/`）：

| Skill | 场景 | 工具数 |
|-------|------|--------|
| `safe_training_plan` | 制定安全训练计划 | 6 |
| `strength_program` | 力量训练方案 | 7 |
| `fat_loss_program` | 减脂方案 | 9 |
| `nutrition_planning` | 营养规划 | 5 |
| `exercise_optimization` | 动作优化 | 6 |
| `posture_correction` | 体态矫正 | 6 |
| `rehabilitation_training` | 康复训练 | 6 |
| `progress_analysis` | 进度分析 | 5 |
| `safety_assessment` | 安全评估 | 5 |
| `quick_consultation` | 快速咨询 | 3 |

### Skill 选择机制

LLM function calling 从 10 个 Skill 中选择最匹配的：
- 每个 Skill 有 `triggers`（触发条件）和 `requires_profile`（是否需要用户档案）
- 简单问候/闲聊 → `direct_reply`（跳过 Skill 执行）
- 无档案 + 需要档案的 Skill → 提示补充

---

## 🛡️ Harness v2 安全层

| 组件 | 职责 | 触发条件 |
|------|------|---------|
| PreSkillPolicy | Skill 前安全检查 | 有伤病/健康状况 + 高强度 Skill |
| ToolAllowlist | 工具权限控制 | 每次工具调用前 |
| OutputVerifier | 输出 6 维度校验 | 生成回答后 |
| HarnessTracer | 决策链追踪 | 全程记录 |

**HITL (Human-in-the-Loop)**:
- 高风险操作自动 interrupt → 前端弹出 ApprovalDialog
- 用户确认后 resume → 继续执行（走 safety_assessment Skill）
- 用户拒绝 → 降级回答

---

## 📊 数据基础设施

### Qdrant 向量库

| 集合 | 数量 | 用途 |
|------|------|------|
| `fitness_exercises_v2` | 1,596 | 健身动作语义搜索 |
| `food_nutrition_vector` | 1,851 | 食物营养匹配 |
| `training_knowledge` | 43 | 训练周期化原则 |
| `chat_conversations` | 动态 | 对话历史检索 |
| `user_memory` | 动态 | 跨对话记忆 |

### Neo4j 图数据库

- **4,246 节点**: Exercise(1,603) + Muscle(53) + Food(1,880) + Nutrient(29) + Equipment(17) + 其他
- **61,507 关系**: CONTAINS_NUTRIENT + TARGETS_PRIMARY/SECONDARY + REQUIRES
- **核心能力**: 肌肉训练容量(MEV/MAV/MRV) + 动作-肌肉映射 + 禁忌症关系

---

## 🔌 API 端点

### Agent v2（新）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/agent` | Agent v2 流式对话（SSE） |
| POST | `/api/v1/approval/respond` | HITL 审批响应 |
| GET | `/api/v1/approval/pending` | 查询待审批状态 |
| POST | `/api/v1/thread/create` | 创建对话线程 |
| GET | `/api/v1/thread/list` | 列出用户线程 |
| DELETE | `/api/v1/thread/{id}` | 删除线程 |

### 旧接口（兼容）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/stream` | 旧 11 步 workflow 流式对话 |
| POST | `/api/v1/chat/sync` | 同步对话 |
| GET | `/api/v1/health` | 健康检查 |

### SSE 事件类型

```
event: skill_started    — Skill 开始执行
event: tool_completed   — 单个工具完成
event: approval_required — HITL 审批请求
event: content          — 流式文本内容
event: done             — 完成
event: error            — 错误
```

---

## 🚀 部署

### Docker（开发环境）

```bash
# 容器名: fitness_daml_rag，端口: 8001
docker exec fitness_daml_rag python -m pytest tests/
docker exec fitness_daml_rag python tests/integration/test_agent_v2_smoke.py
```

### Zeabur（生产环境）

- 仓库: `vivy1024/daml-rag-server`
- 分支: `main`（自动部署）
- 环境变量: 见 `.kiro/steering/zeabur-env-vars.md`

### Feature Flag

```env
AGENT_V2_ENABLED=true          # 主开关
AGENT_V2_SKILL_WHITELIST=      # 空=全量启用
AGENT_V2_USER_WHITELIST=       # 空=全量启用
```

---

## 🧪 测试

```bash
# 单元测试
docker exec fitness_daml_rag python -m pytest tests/unit/ -v

# 集成测试
docker exec fitness_daml_rag python tests/integration/test_agent_v2_smoke.py
docker exec fitness_daml_rag python tests/integration/test_skill_execution.py
docker exec fitness_daml_rag python tests/integration/test_harness_v2.py
docker exec fitness_daml_rag python tests/integration/test_harness_feature_flag.py
```

---

## 📁 目录结构

```
src/
├── agent_v2/           # Agent v2 核心
│   ├── state.py        # AgentState TypedDict
│   ├── graph.py        # LangGraph StateGraph
│   ├── sse_emitter.py  # SSE 流式输出
│   ├── feature_flag.py # Feature flag 控制
│   └── nodes/          # 6 个节点
├── skills/             # Skills 体系
│   ├── definitions/    # 10 个 Skill YAML
│   ├── definition.py   # SkillDefinition dataclass
│   ├── loader.py       # YAML 加载器
│   ├── manager.py      # SkillManager
│   ├── router.py       # SkillRouter (LLM function calling)
│   └── executor.py     # SkillExecutor (工具链执行)
├── harness_v2/         # Harness v2 安全层
│   ├── pre_skill_policy.py
│   ├── tool_allowlist.py
│   ├── output_verifier.py
│   └── harness_tracer.py
├── framework/          # 基础设施
│   ├── models/         # LLMPoolManager
│   ├── persistence/    # Checkpointer
│   ├── auth/           # FailClosedPermissionChecker
│   └── retrieval/      # 三层检索引擎
├── api/                # FastAPI 路由
│   ├── routes/         # chat/thread/approval/health
│   └── models/         # 请求/响应模型
└── applications/       # 旧 workflow（逐步废弃）
    └── fitness/
        ├── workflow/   # 11 步 DAG 编排
        └── mcp_tools/  # MCP 工具实现
```

---

## 📝 版本历史

见 `CHANGELOG.md`（构建号）和根仓库 `CHANGELOG.md`（产品版本）。

---

**维护者**: 薛小川 (vivy1024)
**许可**: Private
