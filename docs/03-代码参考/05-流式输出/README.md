# 05-流式输出

**版本**: v1.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 模块说明

本模块包含流式输出（SSE - Server-Sent Events）的详细代码实现文档。流式输出是DAML-RAG系统的重要特性，能够实时向前端推送工作流程执行状态和LLM生成内容。

### 流式输出架构

**技术选型**
- **协议**：SSE（Server-Sent Events）
- **传输格式**：JSON
- **监控集成**：Prometheus指标收集

**事件类型**
- `workflow_start` - 工作流程开始
- `step_start` - 步骤开始
- `step_progress` - 步骤进度
- `step_complete` - 步骤完成
- `llm_chunk` - LLM生成内容片段
- `workflow_complete` - 工作流程完成
- `error` - 错误事件

---

## 文档列表

### 流式输出实现

1. [01-流式输出代码实现.md](./01-流式输出代码实现.md) - 流式输出的完整代码实现
   - SSE事件生成器实现
   - 流式监控指标集成
   - 降级策略和错误处理
   - 并发限制控制
   - 前端集成示例

---

## 流式输出流程

### 工作流程执行流式输出

```
1. 客户端建立SSE连接
   ↓
2. 发送workflow_start事件
   ↓
3. 执行步骤1-11，每个步骤发送：
   - step_start（步骤开始）
   - step_progress（进度更新）
   - step_complete（步骤完成）
   ↓
4. 步骤10（LLM深度分析）发送：
   - llm_chunk（LLM生成内容片段）
   ↓
5. 发送workflow_complete事件
   ↓
6. 关闭SSE连接
```

### 错误处理流程

```
1. 捕获异常
   ↓
2. 发送error事件
   ↓
3. 记录错误日志
   ↓
4. 关闭SSE连接
```

---

## 代码路径

### 流式输出实现

```
daml-rag-server/src/api/routes/
└── chat.py                    # SSE路由和事件生成器
```

### 监控集成

```
daml-rag-server/src/framework/monitoring/
├── streaming_metrics.py       # 流式输出指标
└── concurrency_limiter.py     # 并发限制器
```

---

## SSE事件格式

### step事件

```json
{
  "event": "step",
  "data": {
    "type": "step",
    "step": 1,
    "message": "预加载用户档案",
    "timestamp": 1703234567.89
  }
}
```

### chunk事件

```json
{
  "event": "chunk",
  "data": {
    "type": "chunk",
    "content": "根据您的训练目标",
    "fallback": false
  }
}
```

### done事件

```json
{
  "event": "done",
  "data": {
    "type": "done",
    "data": {
      "request_id": "abc123",
      "total_length": 8500,
      "fallback": false,
      "success": true
    }
  }
}
```

### error事件

```json
{
  "event": "error",
  "data": {
    "type": "error",
    "error": "服务暂时不可用",
    "fallback_failed": false
  }
}
```

### fallback事件

```json
{
  "event": "fallback",
  "data": {
    "type": "fallback",
    "message": "流式输出暂时不可用，切换到标准模式",
    "reason": "stream_error"
  }
}
```

### rate_limit事件

```json
{
  "event": "rate_limit",
  "data": {
    "type": "rate_limit",
    "message": "服务繁忙，请稍后重试",
    "retry_after": 10
  }
}
```

---

## 监控指标

### 流式输出性能指标

- `streaming_ttfb_seconds` - 首字节时间（TTFB）
- `streaming_duration_seconds` - 流式输出持续时间
- `streaming_tokens_total` - 生成的总令牌数
- `streaming_tokens_per_second` - 令牌生成速率
- `streaming_success_total` - 成功会话总数
- `streaming_failure_total` - 失败会话总数

### 性能目标

- **TTFB**: < 2秒
- **令牌速率**: > 50 tokens/s
- **成功率**: > 95%
- **并发支持**: 50个同时会话

---

## 相关链接

- **流式输出架构**: [02-核心架构/05-监控层/02-流式输出架构.md](../../02-核心架构/05-监控层/02-流式输出架构.md)（待补充）
- **监控系统实现**: [03-代码参考/02-核心组件/04-监控系统.md](../02-核心组件/04-监控系统.md)
- **流式输出使用指南**: [04-开发指南/02-工具使用/04-流式输出使用指南.md](../../04-开发指南/02-工具使用/04-流式输出使用指南.md)（待补充）
- **监控和可观测性指南**: [04-开发指南/04-最佳实践/01-监控和可观测性完整指南.md](../../04-开发指南/04-最佳实践/01-监控和可观测性完整指南.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
