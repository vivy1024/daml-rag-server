# 部署运维

**版本**: v3.13.0
**更新日期**: 2025-12-31
**状态**: ✅ Docker生产部署就绪 - v6.0架构

---

## 📋 本章内容

| 文档 | 说明 | 状态 |
|-----|------|------|
| [数据备份与恢复](./数据备份与恢复.md) ⭐ | **一键备份恢复系统** | ✅ v1.0.0 |
| [Docker部署](./Docker部署.md) | 容器化部署指南 | ✅ |
| <!-- [知识图谱快速导入指南](./知识图谱快速导入指南.md) (文档不存在) --> | 知识图谱数据导入 | ✅ |
| [服务器部署完整指南](./服务器部署完整指南.md) | 生产服务器部署 | ✅ |

**v3.12.0 最新更新** (2025-11-08):
- ✨ **新增**: 完整的数据备份恢复系统（一键备份/恢复）
- 💾 **备份**: MySQL + Neo4j + Qdrant（88MB）
- 🚀 **快速部署**: 使用备份文件部署服务器只需5-10分钟
- 📚 **文档**: 4种备份场景详细指南
- ⚠️ **重要**: 代码更新必须重新构建镜像

---

## 🚀 快速部署

### 方案A: 使用备份文件（⭐ 推荐，5-10分钟）

**适用场景**: 服务器部署、环境迁移、快速恢复

```powershell
# Windows
# 1. 本地生成最新备份
powershell -ExecutionPolicy Bypass -File scripts/backup_all.ps1

# 2. 上传备份到服务器
# 复制 ./backups/20251108/ 到服务器

# 3. 在服务器上恢复
powershell -ExecutionPolicy Bypass -File scripts/restore_all.ps1 20251108
```

```bash
# Linux/macOS
# 1. 本地生成最新备份
bash scripts/backup_all.sh

# 2. 上传备份到服务器（使用scp或云存储）
scp -r backups/20251108/ user@server:/path/to/backups/

# 3. 在服务器上恢复
bash scripts/restore_all.sh 20251108
```

**详见**: [数据备份与恢复指南](./数据备份与恢复.md)

---

### 方案B: 从零构建（30-60分钟）

### Docker Compose部署（生产推荐）

```bash
# 1. 进入项目根目录
cd F:\build_body

# 2. 首次构建镜像
docker-compose up -d --build meta-learning-mcp

# 3. 检查服务状态
docker-compose ps
# 确认 fitness_mcp_meta_learning 状态为 healthy

# 4. 健康检查
curl http://localhost:8001/health

# 5. 查看日志
docker-compose logs -f meta-learning-mcp
```

### 代码更新部署流程 ⚠️

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像（重要！）
docker-compose up -d --build meta-learning-mcp

# 3. 验证部署
docker-compose logs meta-learning-mcp --tail=50
curl http://localhost:8001/health

# 4. 如果失败，回滚
git checkout <previous-commit>
docker-compose up -d --build meta-learning-mcp
```

### BUILD_BODY服务组件

| 组件 | 容器名 | 端口 | 状态 |
|-----|--------|------|------|
| **DAML-RAG Server AI服务** | `fitness_mcp_meta_learning` | 8001 | ✅ healthy |
| PHP后端 | `fitness_php_v2` | 8000 | ✅ running |
| MySQL | `fitness_mysql` | 3306 | ✅ healthy |
| Neo4j | `fitness_neo4j` | 7474, 7687 | ✅ healthy |
| Qdrant | `fitness_qdrant` | 6333 | ✅ running |
| Redis | `fitness_redis` | 6379 | ✅ healthy |

---

## 📊 监控与故障排查

### 核心监控端点

```bash
# 健康检查（最重要）
curl http://localhost:8001/health

# 学习统计
curl http://localhost:8001/admin/learning/stats

# 交互式API文档
http://localhost:8001/docs
```

### 常见问题排查

**问题1**: 容器不断重启
```bash
# 查看完整日志
docker-compose logs meta-learning-mcp --tail=200

# 常见原因:
# - 编码错误: SyntaxError Non-UTF-8
# - 模块导入错误: ModuleNotFoundError
# - 缩进错误: IndentationError
```

**问题2**: 代码修改不生效
```bash
# 原因: Docker使用COPY指令，需重新构建
docker-compose up -d --build meta-learning-mcp

# 验证构建时间
docker images | grep meta-learning-mcp
```

**问题3**: 健康检查失败
```bash
# 进入容器检查
docker exec -it fitness_mcp_meta_learning sh
ps aux  # 检查进程
curl http://localhost:8001/health  # 内部测试
```

### 生产监控指标

- **可用性目标**: > 99.9%
- **响应延迟**: < 2s（含AI推理）
- **容器健康**: healthy状态
- **日志清洁**: 无ERROR级别日志

---

## 🔗 相关文档

- <!-- [系统架构](../02-核心架构/系统架构.md) (文档不存在) --> - 架构设计
- [开发指南](../04-开发指南/README.md) - 开发环境

---

**维护者**: 薛小川  
**工具**: Cursor + Claude  
**最后审查**: 2025-12-31


