# API文档

**版本**: v3.11.0
**更新日期**: 2025-12-31
**状态**: ✅ 17工具API就绪 - SSE流式响应

---

## 📋 本章内容

| 文档 | 说明 | 状态 |
|-----|------|------|
| [API参考文档](./API参考文档.md) | FastAPI完整接口 | ✅ |
| [MCP工具API](./MCP工具API.md) | MCP工具接口 | ✅ |
| [API_USAGE](./API_USAGE.md) | API使用示例 | ✅ |

**v1.8.0 API更新** (2025-11-07):
- ✅ **服务就绪**: Docker容器健康运行
- ✅ **FastAPI服务**: `http://localhost:8001`
- ✅ **交互式文档**: `http://localhost:8001/docs`
- ✅ **健康检查**: `http://localhost:8001/health`
- ✅ **SSE流式响应**: `/v1/chat/stream` 端点
- ✅ **会员权限控制**: 分级功能权限

---

## 🔌 核心API端点

| 端点 | 方法 | 功能 | 状态 |
|-----|------|------|------|
| `/v1/chat` | POST | 同步对话 | ✅ |
| `/v1/chat/stream` | POST | 流式对话（SSE） | ✅ ⭐ |
| `/v1/feedback` | POST | 提交反馈 | ✅ |
| `/health` | GET | 健康检查 | ✅ |
| `/docs` | GET | 交互式API文档 | ✅ |
| `/admin/learning/stats` | GET | 学习统计 | ✅ |

---

## 🚀 快速示例

### 同步对话请求

```bash
curl -X POST http://localhost:8001/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "我想增肌",
    "membership_level": "free"
  }'
```

### 流式对话请求（SSE）

```bash
curl -N http://localhost:8001/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "制定增肌计划",
    "membership_level": "premium"
  }'
```

### 健康检查

```bash
curl http://localhost:8001/health
# 返回: {"status": "healthy", "qdrant": "connected", ...}
```

### 访问交互式文档

浏览器打开: `http://localhost:8001/docs`

完整API说明参见: [API参考文档.md](./API参考文档.md)

---

## 🔗 相关文档

- [代码参考](../03-代码参考/05-Tools工具层参考.md) - 工具实现细节
- [快速开始](../01-快速开始/快速开始.md) - 使用示例

---

**维护者**: BUILD_BODY Team  
**最后更新**: 2025-12-31


