# MCP Registry配置清理总结

**日期**: 2025-12-13  
**操作**: 删除无效的fitness-tools-mcp配置  
**状态**: ✅ 完成

---

## 🔍 发现的问题

### fitness-tools-mcp配置错误

**问题描述**:
- 配置路径: `/app/mcp-servers/daml-rag-server/src/applications/fitness/mcp_server/server.py`
- 实际情况: ❌ 该路径在容器内**不存在**
- 原因: 该服务已于2025-12-12归档到`archive/old_mcp_server/`

**历史背景**:
- 旧架构: Python实现的MCP服务器，集成在应用层内部（12个工具）
- 新架构: 独立的TypeScript微服务`comprehensive-fitness-coach-stdio`（23个工具）
- 迁移日期: 2025-12-12

---

## ✅ 执行的操作

### 1. 删除fitness-tools-mcp配置

**删除前**:
```json
{
  "servers": {
    "user-profile-stdio": { ... },
    "fitness-tools-mcp": { ... },  // ❌ 路径不存在
    "professional-fitness-coach-stdio": { ... }
  }
}
```

**删除后**:
```json
{
  "servers": {
    "user-profile-stdio": { ... },
    "professional-fitness-coach-stdio": { ... }  // 已标记为废弃
  }
}
```

### 2. 当前有效的MCP服务器

| 服务器名称 | 类型 | 状态 | 说明 |
|-----------|------|------|------|
| `user-profile-stdio` | stdio | ✅ 活跃 | 用户档案管理（2个工具） |
| `professional-fitness-coach-stdio` | stdio | ⚠️ 已废弃 | 已被comprehensive-fitness-coach-stdio替代 |

---

## 🎯 实际使用的MCP服务

根据docker-compose.yml和实际运行情况：

### HTTP容器（仍在运行）

```bash
$ docker ps --filter "name=fitness_mcp"
NAMES                      STATUS                  PORTS
fitness_mcp_coach          Up 3 hours (healthy)    0.0.0.0:3002->3002/tcp
```

**说明**:
- 容器名: `fitness_mcp_coach`
- 端口: 3002
- 协议: HTTP（不是stdio）
- 服务: `comprehensive-fitness-coach-stdio`（23个专业工具）
- 状态: ✅ 正常运行

### Stdio配置（mcp_registry.json）

```json
{
  "user-profile-stdio": {
    "type": "stdio",
    "command": "node",
    "args": ["/app/mcp-servers/user-profile-stdio/build/index.js"]
  }
}
```

**说明**:
- 配置为stdio协议
- 路径正确，文件存在
- 应在DAML-RAG容器内启动

---

## ⚠️ 架构不一致问题

### 发现的矛盾

1. **mcp_registry.json**: 配置为stdio协议
2. **docker-compose.yml**: 注释掉了HTTP容器配置
3. **实际运行**: HTTP容器`fitness_mcp_coach`仍在运行

### 根本原因

- docker-compose.yml已更新（注释HTTP容器）
- 但旧容器未停止，仍在运行
- mcp_registry.json配置为stdio，但实际使用HTTP

---

## 📋 建议的后续操作

### 1. 停止遗留的HTTP容器

```bash
docker stop fitness_mcp_coach
docker rm fitness_mcp_coach
```

### 2. 重启DAML-RAG容器

```bash
docker-compose restart fitness_daml_rag
```

**原因**: config目录未挂载，需要重启容器才能加载新配置

### 3. 验证stdio协议工作

```bash
# 检查MCP进程
docker exec fitness_daml_rag ps aux | grep node

# 检查日志
docker-compose logs fitness_daml_rag | grep "MCP"
```

---

## 📊 清理前后对比

### 清理前（3个服务器）

```
✅ user-profile-stdio (stdio, 活跃)
❌ fitness-tools-mcp (stdio, 路径不存在)
⚠️ professional-fitness-coach-stdio (stdio, 已废弃)
```

### 清理后（2个服务器）

```
✅ user-profile-stdio (stdio, 活跃)
⚠️ professional-fitness-coach-stdio (stdio, 已废弃)
```

---

## 🔗 相关文档

- **旧MCP服务器归档**: `daml-rag-server/archive/old_mcp_server/README.md`
- **新MCP架构**: `mcp-servers/comprehensive-fitness-coach-stdio/`
- **Docker配置**: `docker-compose.yml`
- **任务文档**: `.kiro/specs/mcp-docker-configuration-standardization/`

---

## ✅ 验证结果

**本地文件**:
- ✅ fitness-tools-mcp已删除
- ✅ JSON格式正确
- ✅ 只剩2个服务器配置

**容器内文件**:
- ⚠️ 仍是旧版本（包含fitness-tools-mcp）
- 📝 需要重启容器才能生效

---

**操作人**: Kiro AI  
**完成时间**: 2025-12-13  
**下一步**: 重启DAML-RAG容器，验证stdio协议工作
