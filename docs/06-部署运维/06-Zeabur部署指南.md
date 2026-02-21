# DAML-RAG Server Zeabur 部署指南

**版本**: v1.0.0  
**更新日期**: 2026-01-07  
**状态**: ✅ 部署就绪

---

## 📋 概述

本文档提供 DAML-RAG Server 在 Zeabur 平台的完整部署指南。

### 仓库信息

- **Docker Hub**: `vivy1024/fitness-daml-rag`
- **GitHub**: `https://github.com/vivy1024/daml-rag-server`
- **端口**: 8001（或通过环境变量 PORT 配置）

---

## 🚀 部署步骤

### 1. 在 Zeabur 中创建服务

1. 登录 Zeabur 控制台
2. 创建新项目或选择现有项目
3. 点击 "Add Service" → "Docker Image"
4. 输入镜像名称：`vivy1024/fitness-daml-rag:latest`

### 2. 配置环境变量

#### 必需环境变量

```bash
# 数据库连接
NEO4J_URI=bolt://your-neo4j-host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

QDRANT_HOST=your-qdrant-host
QDRANT_PORT=6333
QDRANT_COLLECTION=fitness_exercises_v2

MYSQL_HOST=your-mysql-host
MYSQL_PORT=3306
MYSQL_DATABASE=fitness_app
MYSQL_USER=fitness_user
MYSQL_PASSWORD=your-password

REDIS_HOST=your-redis-host
REDIS_PORT=6379

# LLM API配置
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 后端API连接
BACKEND_API_URL=https://your-backend-url.com
INTERNAL_API_TOKEN=your-internal-token
BACKEND_API_TIMEOUT=10.0
BACKEND_API_MAX_RETRIES=3

# 服务配置
HOST=0.0.0.0
PORT=8001
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1

# 性能优化
PERFORMANCE_OPTIMIZATION_ENABLED=true
CACHE_L1_ENABLED=true
CACHE_L2_ENABLED=true
CACHE_L2_HOST=your-redis-host
CACHE_L2_PORT=6379

# 监控配置
MONITORING_ENABLED=true
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8002
```

#### 可选环境变量

```bash
# 备用LLM（可选）
MOONSHOT_API_KEY=your-moonshot-key
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MOONSHOT_MODEL=moonshot-v1-32k

QWEN_API_KEY=your-qwen-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-turbo

# 时区
TZ=Asia/Shanghai
```

### 3. 配置端口

- **容器端口**: 8001
- **协议**: HTTP
- Zeabur 会自动分配外部端口

### 4. 健康检查配置

- **路径**: `/health` 或 `/api/health`
- **间隔**: 30秒
- **超时**: 10秒
- **重试**: 3次

### 5. 资源限制（推荐）

- **CPU**: 2核
- **内存**: 4GB（最低2GB）
- **存储**: 10GB（用于模型缓存）

---

## 🔧 常见问题排查

### 问题1：服务无法启动

**症状**: 容器启动后立即退出

**可能原因**:
1. 环境变量缺失
2. 数据库连接失败
3. 端口配置错误

**解决方案**:
1. 检查所有必需环境变量是否已设置
2. 查看容器日志：`zeabur logs <service-name>`
3. 验证数据库连接是否正常

### 问题2：健康检查失败

**症状**: 服务显示不健康

**可能原因**:
1. 健康检查路径错误
2. 服务启动时间过长
3. 端口不匹配

**解决方案**:
1. 确认健康检查路径为 `/health`
2. 增加启动等待时间（start-period）
3. 验证 PORT 环境变量与容器端口一致

### 问题3：数据库连接失败

**症状**: 日志显示数据库连接错误

**可能原因**:
1. 数据库服务未启动
2. 网络配置问题
3. 认证信息错误

**解决方案**:
1. 确保数据库服务已部署并运行
2. 检查网络连接（Zeabur 内部网络）
3. 验证数据库用户名和密码

### 问题4：模型下载失败

**症状**: 启动时模型下载超时

**可能原因**:
1. 网络问题
2. Hugging Face 镜像源不可用

**解决方案**:
1. 检查 `HF_ENDPOINT` 环境变量
2. 使用国内镜像：`HF_ENDPOINT=https://hf-mirror.com`
3. 增加启动超时时间

---

## 📊 验证部署

### 1. 健康检查

```bash
curl https://your-zeabur-url.com/health
```

预期响应：
```json
{
  "status": "healthy",
  "timestamp": "2026-01-07T03:40:00Z"
}
```

### 2. API测试

```bash
# 测试聊天接口
curl -X POST https://your-zeabur-url.com/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "message": "你好",
    "session_id": "test-session"
  }'
```

### 3. 查看日志

在 Zeabur 控制台查看实时日志，确认：
- ✅ 服务启动成功
- ✅ 数据库连接正常
- ✅ 模型加载完成
- ✅ 无错误信息

---

## 🔗 相关服务部署

### Neo4j 部署

Zeabur 支持 Neo4j，或使用外部 Neo4j 服务。

**环境变量**:
```bash
NEO4J_URI=bolt://neo4j-service:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

### Qdrant 部署

使用 Zeabur 的 Qdrant 服务或外部服务。

**环境变量**:
```bash
QDRANT_HOST=qdrant-service
QDRANT_PORT=6333
```

### MySQL 和 Redis

使用 Zeabur 的数据库服务或外部服务。

---

## 📝 部署检查清单

- [ ] Docker 镜像已推送到 Docker Hub
- [ ] 所有必需环境变量已配置
- [ ] 数据库服务已部署并运行
- [ ] 端口配置正确（8001）
- [ ] 健康检查路径配置正确
- [ ] 资源限制已设置
- [ ] 日志查看正常
- [ ] API 测试通过

---

## 🚨 紧急故障处理

### 服务崩溃

1. 查看日志定位问题
2. 检查资源使用情况（CPU/内存）
3. 重启服务
4. 如问题持续，降低资源限制或扩展资源

### 数据库连接中断

1. 检查数据库服务状态
2. 验证网络连接
3. 检查认证信息
4. 重启数据库服务

### 性能问题

1. 检查资源使用情况
2. 查看 Prometheus 指标（如果启用）
3. 优化缓存配置
4. 考虑扩展资源

---

## 🔗 相关文档

- [Docker部署指南](./Docker部署.md)
- [环境变量配置指南](./环境变量配置指南.md)
- [生产环境部署指南](./生产环境部署指南.md)

---

**维护者**: 薛小川  
**最后更新**: 2026-01-07

