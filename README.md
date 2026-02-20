# DAML-RAG Server

**版本**: v9.83.0
**更新日期**: 2026-02-20
**状态**: ✅ 生产运行 · Docker容器部署 · Zeabur生产环境

---

## 📋 概述

DAML-RAG Server 是玉珍健身的核心AI服务，实现了**面向垂直领域的自适应多源学习型RAG框架**。通过DAG固定编排和三层检索架构（向量+图谱+约束），提供专业、安全、个性化的健身指导服务。

### 🎯 核心价值

- **DAG固定编排**: 预定义工作流程，避免LLM幻觉，保证数据安全
- **三层检索**: 向量语义匹配 + 图谱关系推理 + 业务约束验证
- **知识图谱**: Neo4j(4,246节点) + Qdrant(4,585向量/1024维GTE-Large-zh)
- **18个MCP工具**: 1个stdio用户档案服务 + 17个Python内置工具 + find_similar_training_cases
- **多模型支持**: Anthropic Claude haiku-4.5（主，Kiro RS代理）→ DeepSeek（备）→ Template（兜底）
- **生产验证**: Token节省85%，成本降低93%，质量提升38%

---

## 🏗️ 系统架构

### 核心组件

**DAML-RAG框架**:
- **数据层**: Neo4j知识图谱 + Qdrant向量数据库 + MySQL对话历史
- **检索层**: 向量检索 + 图谱检索 + 业务约束检索
- **编排层**: DAG固定编排器（默认模式）+ Agent动态决策（energy+会员）
- **工具层**: 18个MCP工具（1个stdio + 17个Python内置）
- **服务层**: FastAPI RESTful API + SSE流式输出

**三层检索架构**:
```
用户查询 → Layer1向量语义匹配 → Layer2图谱关系推理 → Layer3规则验证约束 → 个性化推荐
    ↓              ↓                     ↓                     ↓               ↓
Qdrant检索     训练知识/动作相似        肌肉关系/容量模型         安全检查/调整      最终建议
```

### 技术栈

| 组件 | 技术 | 版本 | 状态 |
|------|------|------|------|
| **AI引擎** | Anthropic Claude haiku-4.5 | - | ✅ 主LLM（Kiro RS代理） |
| **备用LLM** | DeepSeek-Chat | - | ✅ 降级备用 |
| **向量检索** | Qdrant + GTE-Large-zh | 1024维 | ✅ 4,585向量 |
| **知识图谱** | Neo4j | 7.4.0 | ✅ 4,246节点 |
| **数据库** | MySQL + Redis | 8.4.0 / 7.2.5 | ✅ 生产运行 |
| **后端框架** | FastAPI + Python | 3.11 | ✅ Docker容器 |
| **协议** | MCP Stdio + REST API + SSE | - | ✅ 18个工具 |

---

## 📊 数据基础设施

### 🗃️ Qdrant向量库（语义检索）

| 集合 | 数量 | 用途 | 状态 |
|------|------|------|------|
| `training_knowledge` | 43个向量 | 训练周期化、力量发展原则 | ✅ 核心 |
| `fitness_exercises_v2` | 1,596个向量 | 健身动作语义搜索 | ✅ 核心 |
| `food_nutrition_vector` | 1,851个向量 | 食物营养匹配 | ✅ 核心 |
| `chat_conversations` | 动态增长 | 对话历史检索 | ✅ 运行 |
| `user_memory` | 动态增长 | 跨对话记忆 | ✅ v9.81.0新增 |

**向量配置**: 1024维 GTE-Large-zh嵌入，余弦相似度，支持中文检索

### 🔗 Neo4j图数据库（关系推理）

**节点类型分布（总计4,246个节点）**:
- **Exercise**: 1,603个动作（中英文名称，主要肌群，31个完整字段）
- **Muscle**: 53个肌群（MEV/MAV/MRV训练容量数据，13个完整字段）
- **Food**: 1,880种食物（中国营养数据库，8个完整字段）
- **Nutrient**: 29个营养素
- **Equipment**: 17种健身器材类型
- **其他**: PeriodizationModel, TrainingLevel, Goal等

**关系类型分布（总计61,507个关系）**:
- **CONTAINS_NUTRIENT**: 44,406个（Food→Nutrient）
- **TARGETS_PRIMARY**: 1,603个（Exercise→Muscle主要目标）
- **TARGETS_SECONDARY**: 2,362个（Exercise→Muscle次要目标）
- **REQUIRES**: 1,596个（Exercise→Equipment）

**核心数据结构**:
- 肌肉训练容量: Chest(MEV:10-12, MAV:12-20, MRV:22+)
- 周期化模型: Linear/Undulating/Block/Conjugate/Reverse
- 动作-肌肉映射: 完整的1,347个关系连接

---

## 🔧 MCP工具体系

### 1个Stdio MCP服务器

**user-profile-stdio** (Node.js):
- `get_user_profile`: 获取用户健身档案
- `update_user_profile`: 更新用户档案

### 17个Python内置工具

**P0核心工具（5个）**:
- `intelligent_exercise_selector`: 智能动作选择器
- `contraindications_checker`: 禁忌症检查器
- `injury_risk_assessor`: 损伤风险评估器
- `muscle_group_volume_calculator`: 肌群训练量计算器
- `tdee_calculator`: TDEE计算器

**P1建议工具（8个）**:
- `professional_program_designer`: 专业训练计划设计器
- `exercise_alternative_finder`: 动作替代查找器
- `movement_pattern_balancer`: 动作模式平衡器
- `intelligent_weight_calculator`: 智能负重计算器
- `safe_exercise_modifier`: 安全动作修改器
- `nutrition_intake_analyzer`: 营养摄入分析器
- `meal_plan_designer`: 膳食计划设计器
- `exercise_nutrition_optimization`: 运动营养优化器

**P2扩展工具（4个）**:
- `periodized_program_designer`: 周期化训练设计器
- `training_split_designer`: 训练分化设计器
- `find_similar_training_cases`: 相似训练案例检索
- `record_training_feedback`: 训练反馈记录

**安全评估工具（新增）**:
- `postural_assessor`: 体态评估器

---

## 🚀 快速开始

### Docker部署（推荐）

```bash
# 启动容器
docker-compose up -d fitness_daml_rag

# 查看日志
docker logs -f fitness_daml_rag

# 健康检查
curl http://localhost:8001/health
```

### 环境变量配置

**关键环境变量**（在 `.env` 或 Zeabur 中配置）:

```env
# Anthropic Claude（主LLM，通过Kiro RS代理）
ANTHROPIC_API_KEY=your_kiro_rs_api_key
ANTHROPIC_BASE_URL=https://api.kiro.rs/v1
ANTHROPIC_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_ENABLED=true

# DeepSeek（备用LLM）
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_ENABLED=true

# 数据库连接（容器内使用服务名）
NEO4J_URI=bolt://neo4j:7687
QDRANT_URL=http://qdrant:6333
MYSQL_HOST=mysql
REDIS_HOST=redis

# 内部服务认证
INTERNAL_API_TOKEN=crewai-internal-secret-2025
BYPASS_RATE_LIMIT_FOR_INTERNAL=true
```

---

## 📚 API文档

### 核心接口

**GraphRAG查询**:
```bash
POST /api/graphrag/query
Content-Type: application/json

{
    "query_text": "胸肌训练动作推荐",
    "domain": "fitness_exercises",
    "query_type": "semantic_search",
    "top_k": 5,
    "user_profile": {
        "age": 30,
        "gender": "male",
        "training_level": "intermediate"
    }
}
```

**对话接口（SSE流式输出）**:
```bash
POST /api/chat
Content-Type: application/json

{
    "user_id": 1,
    "message": "我想练胸肌",
    "persona_id": "professional",
    "attachments": []
}
```

---

## 📊 性能指标

- **端到端响应时间**: <1.2s（95%请求）
- **TTFB（首字节时间）**: <2秒
- **令牌生成速率**: >50 tokens/s
- **成功率**: >95%
- **并发支持**: 50个同时会话

---

## 📖 文档

完整文档位于 `docs/` 目录，采用模块化组织结构：

- **01-快速开始**: 新手入门指南
- **02-核心架构**: 系统设计和架构决策
- **03-代码参考**: 详细代码实现
- **04-开发指南**: 使用指南和最佳实践
- **05-API文档**: API接口文档
- **06-部署运维**: 部署和运维指南
- **07-测试报告**: 测试报告和验收报告

**推荐阅读路径**:
1. [快速开始](docs/01-快速开始/快速开始.md)
2. [系统架构总览](docs/02-核心架构/01-系统架构/01-系统架构总览.md)
3. [完整工作流程](docs/02-核心架构/01-系统架构/02-完整工作流程.md)
4. [MCP工具架构](docs/02-核心架构/03-编排层/03-MCP工具架构.md)

---

## 🔗 相关项目

| 子项目 | 本地路径 | GitHub仓库 |
|--------|---------|-----------|
| 官网 | `yuzhen-website/` | `vivy1024/yuzhen-website` |
| 前端 | `yuzhen_fitness/` | `vivy1024/yuzhen-fitness-frontend` |
| 后端 | `yuzhen-backend/` | `vivy1024/yuzhen-backend` |
| AI服务 | `daml-rag-server/` | `vivy1024/daml-rag-server` |

---

## 📝 更新历史

### v9.83.0 (2026-02-20) - 代码库清理：死代码删除

- 删除 `mcp_tool_manager.py`（1,300行，无引用）
- 删除 `llm_analysis_engine.py`（576行，无引用）
- 删除 `agent_stream_executor.py`（539行，无引用）
- 删除 6个关联测试/脚本文件（~1,330行）

### v9.82.0 (2026-02-20) - 跨对话记忆 + WebSearch兜底 + Token预算管理

- 新增 DuckDuckGo WebSearch 兜底检索（Layer4，完全免费）
- 新增 TokenBudgetManager 8000 token 总预算管理器
- 新增 user_memory 跨对话记忆服务（Qdrant存储）

### v9.81.0 (2026-02-20) - SystemPersona风格系统 + 蓝绿多模型池扩展

- 新增 3种教练风格（专业/友好/简洁）
- 新增 9模型4层级YAML蓝绿池（加权随机选择）
- 新增 4个Vision模型蓝绿池
- 新增 VisionMessageBuilder 多模态消息构建

完整更新历史请查看 [CHANGELOG.md](CHANGELOG.md)

---

**维护者**: 薛小川
**联系方式**: 1336495069@qq.com | 微信: xxc1765563156
**GitHub**: vivy1024
**项目状态**: ✅ 生产运行 · Docker容器部署 · Zeabur生产环境
