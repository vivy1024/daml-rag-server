# Zeabur 部署问题排查指南

**版本**: v1.0.0  
**更新日期**: 2026-01-07  
**状态**: ✅ 持续更新

---

## 🔍 常见部署问题

### 问题1：服务无法启动或立即退出

#### 症状
- 容器启动后立即退出
- Zeabur 显示服务状态为 "Failed" 或 "Crashing"

#### 排查步骤

1. **查看日志**
   ```bash
   # 在 Zeabur 控制台查看实时日志
   # 或使用 CLI
   zeabur logs <service-name>
   ```

2. **检查环境变量**
   - 确认所有必需环境变量已设置
   - 特别注意数据库连接信息

3. **验证启动命令**
   - 确认使用正确的启动脚本
   - 检查 entrypoint.sh 是否有执行权限

#### 常见原因

**原因1：环境变量缺失**
```
错误信息：NEO4J_URI is not set
解决方案：在 Zeabur 中配置 NEO4J_URI 环境变量
```

**原因2：数据库连接失败**
```
错误信息：Failed to connect to Neo4j
解决方案：
1. 检查数据库服务是否运行
2. 验证网络连接
3. 确认认证信息正确
```

**原因3：端口配置错误**
```
错误信息：Address already in use
解决方案：
1. 确认 PORT 环境变量与容器端口一致
2. Zeabur 会自动设置 PORT，确保代码从环境变量读取
```

---

### 问题2：健康检查失败

#### 症状
- 服务显示为 "Unhealthy"
- 健康检查端点返回错误

#### 排查步骤

1. **测试健康检查端点**
   ```bash
   # 测试根路径
   curl https://your-zeabur-url.com/health
   
   # 测试完整路径
   curl https://your-zeabur-url.com/api/health
   ```

2. **检查启动时间**
   - 模型下载可能需要较长时间
   - 增加 `start-period` 时间

3. **验证端口**
   - 确认服务监听在正确的端口
   - 检查 PORT 环境变量

#### 解决方案

**方案1：增加启动等待时间**
```yaml
# Zeabur 配置
health_check:
  path: /health
  interval: 30s
  timeout: 10s
  start_period: 180s  # 增加到3分钟
  retries: 5
```

**方案2：使用更简单的健康检查路径**
```yaml
# 使用根路径 /health（更简单，启动更快）
health_check:
  path: /health
```

---

### 问题3：模型下载失败

#### 症状
- 启动日志显示模型下载超时
- 错误信息：`Failed to download model`

#### 解决方案

1. **使用国内镜像源**
   ```bash
   # 在环境变量中设置
   HF_ENDPOINT=https://hf-mirror.com
   ```

2. **增加超时时间**
   ```bash
   # 在 Dockerfile 中已配置
   ENV HF_ENDPOINT=https://hf-mirror.com
   ```

3. **预构建镜像**
   - 模型已在构建时下载
   - 如果仍然失败，检查网络连接

---

### 问题4：数据库连接问题

#### 症状
- 日志显示数据库连接错误
- API 返回 500 错误

#### 排查步骤

1. **检查数据库服务状态**
   - 确认数据库服务已部署
   - 验证服务是否运行正常

2. **验证连接信息**
   ```bash
   # 检查环境变量
   NEO4J_URI=bolt://neo4j-service:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-password
   ```

3. **测试网络连接**
   - 确认服务在同一网络
   - 检查防火墙规则

#### 解决方案

**Neo4j 连接**
```bash
# 使用 Zeabur 内部服务名
NEO4J_URI=bolt://neo4j-service:7687

# 或使用外部服务
NEO4J_URI=bolt://your-external-neo4j:7687
```

**Qdrant 连接**
```bash
# 使用 Zeabur 内部服务名
QDRANT_HOST=qdrant-service
QDRANT_PORT=6333

# 或使用外部服务
QDRANT_HOST=your-external-qdrant.com
QDRANT_PORT=6333
```

---

### 问题5：端口配置问题

#### 症状
- 服务无法访问
- 端口冲突错误

#### 解决方案

**Zeabur 会自动设置 PORT 环境变量**

1. **确保代码从环境变量读取端口**
   ```python
   # start_server.py 已更新
   port = int(os.getenv("PORT", 8001))
   ```

2. **Dockerfile 配置**
   ```dockerfile
   EXPOSE 8001
   ENV PORT=8001  # 默认值，Zeabur 会覆盖
   ```

3. **Zeabur 配置**
   - 容器端口：8001
   - 协议：HTTP
   - Zeabur 会自动分配外部端口

---

## 🛠️ 快速修复清单

### 部署前检查

- [ ] Docker 镜像已推送到 Docker Hub
- [ ] 镜像标签正确（latest 或具体版本）
- [ ] 所有必需环境变量已配置
- [ ] 数据库服务已部署
- [ ] 网络配置正确

### 部署后验证

- [ ] 服务状态为 "Running"
- [ ] 健康检查通过
- [ ] 日志无错误信息
- [ ] API 测试通过

---

## 📊 日志分析

### 正常启动日志

```
🚀 DAML-RAG容器启动中...
✅ MCP工具目录存在
✅ MCP配置文件格式正确
✅ NEO4J_URI = bolt://neo4j:7687
✅ QDRANT_HOST = qdrant
🚀 Starting DAML-RAG server (v3.0 - 精简架构)...
🌐 监听地址: 0.0.0.0:8001
✅ GTE-Large-zh model loaded
✅ 所有准备工作完成，启动DAML-RAG服务器...
```

### 错误日志示例

**数据库连接失败**
```
❌ Failed to connect to Neo4j: Connection refused
解决方案：检查 NEO4J_URI 和网络连接
```

**模型加载失败**
```
❌ Failed to load model: Connection timeout
解决方案：检查网络或使用镜像源
```

**端口冲突**
```
❌ Address already in use: 8001
解决方案：检查 PORT 环境变量
```

---

## 🔗 相关文档

- [Zeabur部署指南](./Zeabur部署指南.md)
- [Docker部署指南](./Docker部署.md)
- [环境变量配置指南](./环境变量配置指南.md)

---

**维护者**: 薛小川  
**最后更新**: 2026-01-07

