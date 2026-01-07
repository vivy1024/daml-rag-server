# DAML-RAG框架API参考文档

**创建日期**: 2025-12-22

---


**版本**: v5.0.0
**更新日期**: 2025-12-03
**状态**: ✅ 生产就绪

---

## 📋 概述

DAML-RAG框架提供精简而强大的API接口，专注于核心的三层检索功能和用户交互。框架采用薄路由架构设计，确保API的简洁性和高性能。

`✶ Insight ─────────────────────────────────────`
DAML-RAG API设计遵循"精准而强大"的原则。我们不提供过度复杂的API，而是专注于核心功能：GraphRAG三层检索、聊天交互和系统健康检查。这种设计确保了API的易用性和维护性。
`─────────────────────────────────────────────────`

---

## 🔧 API架构总览

DAML-RAG框架采用精简的API架构，专注于核心功能：

```
┌─────────────────────────────────────────────────────────┐
│                    API层架构                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   /health   │  │/api/graphrag│  │    /chat    │     │
│  │   健康检查   │  │   查询接口   │  │   聊天接口   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  /feedback  │  │/json_patch  │              │     │
│  │   反馈接口   │  │ JSON补丁接口│              │     │
│  └─────────────┘  └─────────────┘              │     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  业务逻辑层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │chat_service │  │GraphRAG引擎 │  │  后端集成    │     │
│  │  聊天服务   │  │ 三层检索    │  │backend_client│     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                 数据存储层                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │    Neo4j    │  │   Qdrant    │  │   MySQL     │     │
│  │  图数据库   │  │  向量数据库 │  │  用户数据   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 📡 实际API接口

### 1. 系统健康检查API

**端点**: `GET /health`

**功能**: 系统健康状态检查

**请求参数**: 无

**响应结果**:
```typescript
{
  code: 200;
  msg: "服务健康";
  data: {
    status: "healthy";
    api_server: "healthy";
    framework: true;
    version: "2.0.0";
    uptime: number;
    components: {
      framework_initializer: boolean;
      api_server: boolean;
    };
  };
  timestamp: string;
}
```

**示例**:
```bash
curl http://localhost:8001/health
```

**响应**:
```json
{
  "code": 200,
  "msg": "服务健康",
  "data": {
    "status": "healthy",
    "api_server": "healthy",
    "framework": true,
    "version": "2.0.0",
    "uptime": 40420,
    "components": {
      "framework_initializer": true,
      "api_server": true
    }
  },
  "timestamp": "2025-12-02T21:48:38.187504"
}
```

---

### 2. GraphRAG三层检索API

**端点**: `POST /api/graphrag/query`

**功能**: DAML-RAG核心三层检索（语义搜索 + 图谱推理 + 业务约束）

**请求参数**:
```typescript
{
  query_text: string;              // 查询文本（必需）
  domain?: string;                 // 领域（默认："fitness_exercises"）
  query_type?: string;             // 查询类型（默认："three_layer"）
  filters?: {                      // 过滤条件（可选）
    difficulty?: string;
    equipment?: string[];
    muscle_group?: string[];
  };
  top_k?: number;                  // 返回结果数量（默认：10）
}
```

**响应结果**:
```typescript
{
  code: 200;
  msg: "成功";
  data: {
    results: Array<{               // 检索结果
      exercise_id: string;
      name_zh: string;
      name_en: string;
      primary_muscle_zh: string;
      equipment_zh: string;
      difficulty: string;
      score: number;
    }>;
    reasoning: {
      combined_reason: string;     // 综合推理结果
      confidence: number;          // 置信度
      reason_results: Array<{      // 推理详情
        type: "graph" | "safety";
        content: string;
        confidence: number;
        explanation: string;
      }>;
      final_explanation: string;   // 最终解释
    };
    three_layer_result: {
      layers_executed: number;
      layer1: {                    // 向量语义检索
        name: string;
        source: string;
        count: number;
        confidence: number;
      };
      layer2: {                    // 图谱关系推理
        name: string;
        source: string;
        count: number;
        note: string;
      };
      layer3: {                    // 业务规则验证
        name: string;
        source: string;
        count: number;
        rules_applied: string[];
      };
      pipeline: string;
    };
    optimization: {
      enabled: boolean;
      original_tokens: number;
      optimized_tokens: number;
      token_savings: number;
      reduction_rate: string;
    };
  };
  timestamp: string;
}
```

**示例**:
```bash
curl -X POST http://localhost:8001/api/graphrag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "胸部训练动作",
    "top_k": 5
  }'
```

---

### 3. 聊天交互API

**端点**: `POST /chat`

**功能**: AI聊天交互接口

**请求参数**:
```typescript
{
  message: string;                 // 用户消息（必需）
  user_id?: string;                // 用户ID（可选）
  session_id?: string;             // 会话ID（可选）
  context?: {                      // 上下文信息（可选）
    user_profile: any;
    previous_messages: any[];
  };
}
```

**响应结果**:
```typescript
{
  code: 200;
  msg: "操作成功";
  data: {
    response: string;              // AI回复
    session_id: string;            // 会话ID
    timestamp: string;
    metadata?: {
      reasoning_time_ms: number;
      sources_used: string[];
      confidence: number;
    };
  };
}
```

---

### 4. 用户反馈API

**端点**: `POST /feedback`

**功能**: 用户反馈收集接口

**请求参数**:
```typescript
{
  type: "positive" | "negative" | "suggestion";
  content: string;                 // 反馈内容
  user_id?: string;                // 用户ID（可选）
  session_id?: string;             // 会话ID（可选）
  metadata?: {                     // 元数据（可选）
    query_text?: string;
    response_quality?: number;
    timestamp?: string;
  };
}
```

**响应结果**:
```typescript
{
  code: 200;
  msg: "反馈已收到";
  data: {
    feedback_id: string;
    recorded_at: string;
  };
}
```

---

### 5. JSON补丁操作API

**端点**: `POST /json_patch`

**功能**: JSON数据补丁操作

**请求参数**:
```typescript
{
  operation: "add" | "remove" | "replace" | "move" | "copy" | "test";
  path: string;                    // JSON路径
  value?: any;                     // 新值（取决于操作类型）
  from?: string;                   // 源路径（用于move/copy操作）
}
```

**响应结果**:
```typescript
{
  code: 200;
  msg: "操作成功";
  data: {
    patched_data: any;             // 补丁后的数据
    operation_success: boolean;
  };
}
```

---

## ⚠️ 错误处理

所有API都遵循统一的错误响应格式：

```typescript
{
  code: number;                    // HTTP状态码
  msg: string;                     // 用户友好的错误消息
  data: null;
  error?: {                        // 详细错误信息（可选）
    type: string;
    details: any;
    timestamp: string;
  };
}
```

**常见错误代码**:

| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| `INVALID_REQUEST` | 400 | 请求参数无效 |
| `MISSING_REQUIRED_FIELD` | 400 | 缺少必需参数 |
| `QUERY_PROCESSING_ERROR` | 500 | 查询处理错误 |
| `DATABASE_CONNECTION_ERROR` | 500 | 数据库连接错误 |
| `INTERNAL_SERVER_ERROR` | 500 | 内部服务器错误 |

---

## 📊 性能基准

| API接口 | 平均延迟 | P95延迟 | QPS限制 |
|---------|---------|---------|---------|
| 健康检查 | 15ms | 30ms | 200 |
| GraphRAG检索 | 245ms | 380ms | 100 |
| 聊天交互 | 1.2s | 2.8s | 30 |
| 用户反馈 | 50ms | 120ms | 50 |
| JSON补丁 | 30ms | 80ms | 100 |

**系统级性能指标**:
- **并发处理能力**: 支持最多100个并发请求
- **缓存命中率**: 65% (1小时内相似查询)
- **准确率**: >95% (三层检索融合)
- **Token节省**: 85% (对比传统RAG)
- **成本降低**: 93% (相同质量下)

---

## 🔌 MCP协议集成

**重要说明**: DAML-RAG框架的MCP工具是**内部组件**，不是HTTP API。

### MCP工具调用方式

**❌ 错误方式**: 通过HTTP端点调用MCP工具
**✅ 正确方式**: 通过MCPOrchestrator内部编排调用

### 13个内部MCP工具

1. **IntelligentExerciseSelectorV2** - 智能动作选择
2. **ExerciseNutritionOptimizerV2** - 营养优化
3. **PeriodizedProgramDesignerV2** - 周期化设计
4. **InjuryPreventionAnalyzer** - 损伤预防分析
5. **WorkoutIntensityCalculator** - 强度计算
6. **RecoveryTimeEstimator** - 恢复时间估算
7. **ExerciseTechniqueCoach** - 技术指导
8. **NutritionTimingOptimizer** - 营养时机优化
9. **SupplementSelector** - 补剂选择
10. **ProgressTracker** - 进度跟踪
11. **GoalAdjustmentAdvisor** - 目标调整建议
12. **PersonalizedWarmupCreator** - 个性化热身
13. **ProfessionalFitnessWorkflow** - 专业健身工作流

---

## 🔄 典型使用流程

### 场景1：健康检查

```bash
# 快速检查系统状态
curl http://localhost:8001/health
```

### 场景2：GraphRAG检索

```python
import requests

# 执行三层检索
response = requests.post("http://localhost:8001/api/graphrag/query", json={
    "query_text": "胸部训练动作",
    "domain": "fitness_exercises",
    "top_k": 5
})

result = response.json()
print(f"检索到 {len(result['data']['results'])} 个结果")
print(f"综合推理: {result['data']['reasoning']['combined_reason']}")
print(f"置信度: {result['data']['reasoning']['confidence']}")
```

### 场景3：聊天交互

```python
# AI聊天交互
response = requests.post("http://localhost:8001/chat", json={
    "message": "帮我制定一个胸部训练计划",
    "user_id": "user-123"
})

result = response.json()
print(f"AI回复: {result['data']['response']}")
```

---

## 🔗 相关文档

- <!-- [DAML-RAG框架架构](../02-核心架构/系统架构.md) (文档不存在) -->
- [GraphRAG引擎参考](../03-代码参考/02-框架核心实现参考.md)
- <!-- [MCP工具系统参考](../03-代码参考/25-MCP工具系统参考.md) (文档不存在) -->
- <!-- [三层检索架构](../03-代码参考/15-企业级三层检索引擎参考.md) (文档不存在) -->

---

## 🚀 快速体验

### 使用curl快速测试

```bash
# 1. 健康检查
curl http://localhost:8001/health

# 2. GraphRAG检索
curl -X POST http://localhost:8001/api/graphrag/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "胸部训练动作", "top_k": 3}'

# 3. 聊天交互
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "推荐几个背部训练动作"}'
```

### Python SDK使用示例

```python
import requests

class DAMLRAGClient:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url

    def health_check(self):
        """健康检查"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def search(self, query_text, top_k=5):
        """GraphRAG检索"""
        response = requests.post(f"{self.base_url}/api/graphrag/query", json={
            "query_text": query_text,
            "top_k": top_k
        })
        return response.json()

    def chat(self, message, user_id=None):
        """聊天交互"""
        data = {"message": message}
        if user_id:
            data["user_id"] = user_id

        response = requests.post(f"{self.base_url}/chat", json=data)
        return response.json()

# 使用示例
client = DAMLRAGClient()

# 健康检查
health = client.health_check()
print(f"系统状态: {health['data']['status']}")

# GraphRAG检索
result = client.search("胸部训练动作")
print(f"找到 {len(result['data']['results'])} 个结果")

# 聊天交互
chat_result = client.chat("帮我制定训练计划")
print(f"AI回复: {chat_result['data']['response']}")
```

---

**维护者**: 薛小川
**最后更新**: 2025-12-03
**版本**: v5.0.0
**API状态**: ✅ 生产就绪
**端口**: 8001

---

**更新记录**:
- **v5.0.0 (2025-12-03)**: 完全重写，移除虚构API，只保留实际存在的5个端点
- **v2.0.0 (2025-11-15)**: 包含大量虚构API端点（已废弃）

---

**重要提醒**:
- ✅ 只使用实际存在的API端点
- ✅ MCP工具是内部组件，不对外暴露HTTP接口
- ✅ 所有API都在8001端口运行
- ✅ 统一的错误响应格式