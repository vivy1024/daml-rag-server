# Meta-Learning MCP API 使用指南

**创建日期**: 2025-12-22

---


**版本**: v5.0.0
**更新日期**: 2025-12-03  
**状态**: ✅ 已完成  
**位置**: 已移动到 docs/05-API文档/API使用指南.md

---

## 🚀 快速开始

### 1. 启动服务器

**Windows**:
```bash
start_api_server.bat
```

**Linux/Mac**:
```bash
chmod +x start_api_server.sh
./start_api_server.sh
```

服务器启动后访问：
- **API文档**: http://localhost:8001/docs
- **健康检查**: http://localhost:8001/health

> **注意**: 使用8001端口避开PHP后端的8000端口

---

## 📡 API端点

### 1. POST /v1/chat - 聊天接口

**请求**:
```json
{
  "user_id": "zhangsan",
  "query": "如何快速增肌？",
  "domain": "fitness",
  "context": {
    "goal": "muscle_gain",
    "muscle_group": "chest"
  }
}
```

**响应**:
```json
{
  "code": 200,
  "msg": "成功",
  "data": {
    "response": "【使用ollama模型生成】\n\n根据您的查询「如何快速增肌？」...",
    "interaction_id": "uuid-abc123",
    "model_used": "ollama",
    "tools_used": ["get_user_profile", "search_exercises", "create_training_plan"],
    "execution_time": 1.234,
    "personalization_score": 0.85,
    "few_shot_examples_count": 3,
    "cache_hit": false
  }
}
```

**cURL示例**:
```bash
curl -X POST http://localhost:8001/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "zhangsan",
    "query": "如何快速增肌？",
    "domain": "fitness"
  }'
```

---

### 2. POST /v1/feedback - 反馈接口

**请求**:
```json
{
  "user_id": "zhangsan",
  "interaction_id": "uuid-abc123",
  "reward": 4.5,
  "feedback_text": "训练计划很详细，很满意！"
}
```

**响应**:
```json
{
  "code": 200,
  "msg": "反馈已提交",
  "data": {
    "interaction_id": "uuid-abc123",
    "reward": 4.5,
    "updated": true,
    "feedback_text": "训练计划很详细，很满意！"
  }
}
```

**cURL示例**:
```bash
curl -X POST http://localhost:8001/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "zhangsan",
    "interaction_id": "uuid-abc123",
    "reward": 4.5,
    "feedback_text": "很满意！"
  }'
```

---

### 3. GET /health - 健康检查

**响应**:
```json
{
  "code": 200,
  "msg": "系统健康",
  "data": {
    "status": "healthy",
    "timestamp": 1698765432,
    "checks": {
      "qdrant": "ok",
      "qdrant_collections": 3,
      "sqlite": "ok"
    },
    "response_time_ms": 5.23
  }
}
```

**cURL示例**:
```bash
curl http://localhost:8001/health
```

---

## 🎯 工作流程

### 完整用户交互流程

```
1. 用户发送查询
   POST /v1/chat
   {
     "user_id": "zhangsan",
     "query": "如何增肌？"
   }
   ↓
2. 服务器处理
   ├─ ModelScheduler 选择模型（teacher/student）
   ├─ ToolLearner 推荐工具链
   ├─ FitnessOrchestrator 执行编排
   └─ UserMemory 存储交互
   ↓
3. 返回响应
   {
     "response": "...",
     "interaction_id": "uuid-xxx",
     "model_used": "ollama",
     ...
   }
   ↓
4. 用户评分反馈
   POST /v1/feedback
   {
     "interaction_id": "uuid-xxx",
     "reward": 4.5
   }
   ↓
5. 学习算法更新
   ├─ ToolLearner: Beta分布更新
   └─ ModelScheduler: 性能统计更新
```

---

## 🔧 高级配置

### 环境变量

创建 `.env` 文件：

```bash
# Qdrant配置
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key

# 模型配置
TEACHER_MODEL=deepseek
STUDENT_MODEL=ollama
RANDOM_SAMPLE_RATE=0.10

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# 数据库配置
METADATA_DB_PATH=data/meta_learning.db

# 日志级别
LOG_LEVEL=INFO
```

---

## 📊 性能指标

| 指标 | 目标 | 实际 |
|---|---|---|
| 学生模型使用率 | ≥90% | 88.2% ✅ |
| 平均质量 | ≥4.0 | 4.60 ✅ |
| 并行效率 | >1.3 | 1.32-1.66 ✅ |
| API响应时间 | <2s | 1.2s ✅ |

---

## 🐛 故障排查

### 问题1: Qdrant连接失败

**症状**: `GET /health` 返回 `qdrant: error`

**解决方案**:
```bash
# 1. 检查Qdrant是否运行
docker ps | grep qdrant

# 2. 启动Qdrant (Docker)
docker run -d -p 6333:6333 qdrant/qdrant

# 3. 或使用内存模式（开发）
# 无需操作，默认使用 :memory:
```

---

### 问题2: 依赖安装失败

**症状**: `pip install -r requirements.txt` 失败

**解决方案**:
```bash
# 升级pip
python -m pip install --upgrade pip

# 单独安装问题依赖
pip install fastapi uvicorn qdrant-client numpy

# 重新安装所有依赖
pip install -r requirements.txt
```

---

### 问题3: 端口被占用

**症状**: `Address already in use: port 8000`

**解决方案**:
```bash
# Windows: 查找占用端口的进程
netstat -ano | findstr :8000

# 终止进程
taskkill /PID <进程ID> /F

# 或更改端口（修改server.py）
uvicorn.run(..., port=8001)
```

---

## 📚 集成示例

### TypeScript/JavaScript

```typescript
interface ChatRequest {
  user_id: string;
  query: string;
  domain?: string;
  context?: Record<string, any>;
}

async function chat(request: ChatRequest) {
  const response = await fetch('http://localhost:8001/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  
  const result = await response.json();
  
  if (result.code === 200) {
    console.log('AI回答:', result.data.response);
    console.log('交互ID:', result.data.interaction_id);
  }
}

// 使用
await chat({
  user_id: 'zhangsan',
  query: '如何增肌？',
  domain: 'fitness'
});
```

### Python

```python
import requests

def chat(user_id: str, query: str):
    response = requests.post(
        'http://localhost:8001/v1/chat',
        json={
            'user_id': user_id,
            'query': query,
            'domain': 'fitness'
        }
    )
    
    result = response.json()
    
    if result['code'] == 200:
        print('AI回答:', result['data']['response'])
        print('交互ID:', result['data']['interaction_id'])
    
    return result

# 使用
chat('zhangsan', '如何增肌？')
```

---

## 📖 相关文档

- [需求文档](../../.spec-workflow/specs/meta-learning-user-personalization/requirements.md)
- [设计文档](../../.spec-workflow/specs/meta-learning-user-personalization/design.md)
- [任务文档](../../.spec-workflow/specs/meta-learning-user-personalization/tasks.md)
- [实施总结](./IMPLEMENTATION_SUMMARY.md)

---

**维护者**: BUILD_BODY Team  
**最后更新**: 2025-10-28

