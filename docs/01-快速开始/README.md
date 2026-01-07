# 快速开始

**版本**: v3.11.0  
**更新日期**: 2025-11-08  
**状态**: ✅ Docker容器化部署 · 资源需求已验证

---

## 📋 本章内容

| 文档 | 说明 | 更新 |
|-----|------|-----|
| [安装指南](./安装指南.md) | **⭐ 必读** - 真实硬件资源需求和Docker配置 | v3.11.0 |
| [快速开始](./快速开始.md) | 5分钟启动验证 - 完整服务检查清单 | v3.11.0 |
| [环境配置](./环境配置.md) | 各服务详细配置 - MySQL、Neo4j、Qdrant等 | v3.11.0 |

**v3.11.0 重要更新** (2025-11-08):
- ⚠️ 更新真实资源需求：86.3GB磁盘、CPU 1300%峰值、Ollama 8GB内存
- ✅ 明确各服务的资源占用和配置要求
- ✅ 新增Docker镜像清理和优化建议
- ✅ 完善服务健康检查和故障排查流程

---

## ⚠️ 开始前必读

### 真实资源需求（生产环境实测）

```
💾 磁盘空间: 86.3 GB
   ├─ Docker镜像: ~25GB (Neo4j 5.15、Ollama、BGE-M3等)
   ├─ 容器数据卷: ~45GB (MySQL、Neo4j图谱、Qdrant向量)
   └─ Hugging Face缓存: ~16GB (BGE-M3、tokenizer等)

🧠 内存占用: 14-20 GB
   ├─ Ollama (qwen3:8b): 8GB
   ├─ Neo4j 图谱: 1.5GB (512MB pagecache + 1GB heap)
   ├─ MySQL 8.4: 1-2GB
   ├─ Qdrant: 1-2GB
   ├─ DAML-RAG Server AI服务 (BGE-M3): 2-3GB
   ├─ PHP后端: 512MB
   └─ 其他服务: 1-2GB

⚡ CPU使用: 峰值 1300% (13核满负载)
   ├─ 正常运行: 200-400% (2-4核)
   ├─ AI推理时: 800-1300% (8-13核)
   └─ 知识图谱查询: 400-600% (4-6核)
```

### 最低硬件要求

| 组件 | 最低配置 | 推荐配置 | 生产环境 |
|-----|---------|---------|---------|
| **CPU** | 4核心 (i5/Ryzen 5) | 8核心 (i7/Ryzen 7) | 16核心+ (服务器) |
| **内存** | 16GB | 32GB | 64GB+ |
| **磁盘** | 100GB SSD | 256GB NVMe SSD | 512GB+ NVMe SSD |
| **网络** | 10Mbps | 100Mbps | 1Gbps |

**⚠️ 警告**：
- 低于16GB内存会导致Ollama OOM（内存溢出）
- 低于4核CPU会导致AI推理超时
- 磁盘不足会导致Docker无法启动容器

---

## 🚀 快速导航

### 新用户路径（推荐）

```
第1步: 阅读安装指南 → 检查硬件资源、安装Docker
        ↓
第2步: 启动服务 → docker-compose up -d
        ↓
第3步: 验证服务 → 运行快速开始中的检查清单
        ↓
第4步: 配置优化 → 根据环境配置调整资源限制
```

### 5分钟快速启动（已有Docker）

```bash
# 1. 进入项目根目录
cd F:\build_body

# 2. 检查磁盘空间（需要至少100GB可用）
df -h  # Linux/macOS
Get-PSDrive C | Select-Object Used,Free  # Windows PowerShell

# 3. 启动所有服务（包括DAML-RAG Server）
docker-compose up -d

# 4. 等待服务就绪（约2-3分钟）
docker-compose ps

# 5. 验证DAML-RAG Server服务（健康检查）
curl http://localhost:8001/health

# 6. 访问管理界面
# - Neo4j浏览器: http://localhost:7474
# - Qdrant控制台: http://localhost:6333/dashboard
# - phpMyAdmin: http://localhost:8080
# - DAML-RAG Server API文档: http://localhost:8001/docs
```

### 常见问题快速修复

```bash
# 问题1: Docker磁盘空间不足
docker system prune -a --volumes  # ⚠️ 危险：会删除所有未使用的数据

# 问题2: 容器启动失败
docker-compose logs <service_name>  # 查看具体日志

# 问题3: CPU占用过高
docker stats  # 查看各容器资源使用

# 问题4: 内存不足
docker-compose down  # 停止服务
# 修改 docker-compose.yml 中的 mem_limit 配置
```

---

## 📊 服务端口映射

| 服务 | 容器端口 | 宿主机端口 | 用途 | 资源占用 |
|-----|---------|-----------|------|---------|
| **MySQL** | 3306 | 3306 | 数据库 | 1-2GB 内存 |
| **Redis** | 6379 | 6379 | 缓存 | 100-500MB |
| **Neo4j HTTP** | 7474 | 7474 | Web界面 | - |
| **Neo4j Bolt** | 7687 | 7687 | 客户端连接 | 1.5GB 内存 |
| **Qdrant HTTP** | 6333 | 6333 | 向量搜索API | 1-2GB 内存 |
| **Qdrant gRPC** | 6334 | 6334 | gRPC API | - |
| **DAML-RAG Server AI** | 8001 | 8001 | DAML-RAG Server编排器 | 2-3GB 内存 |
| **PHP后端** | 80 | 8000 | Laravel API | 512MB |
| **phpMyAdmin** | 80 | 8080 | 数据库管理 | 100MB |
| **Redis Commander** | 8081 | 8081 | Redis管理 | 50MB |
| **Mailpit Web** | 8025 | 8026 | 邮件测试 | 50MB |
| **Ollama** | 11434 | 11434 | 本地LLM | **8GB 内存** |

**总计**：约14-20GB内存（包括Ollama）

---

## 🎯 下一步行动

### 根据你的情况选择：

| 场景 | 下一步 |
|-----|--------|
| 🆕 **全新安装** | → [安装指南](./安装指南.md) |
| ✅ **已安装Docker** | → [快速开始](./快速开始.md) |
| 🔧 **需要调优** | → [环境配置](./环境配置.md) |
| 🐛 **遇到问题** | → 查看各文档的"常见问题"章节 |

---

## 🔗 相关文档

### 核心文档
- <!-- [系统架构](../02-核心架构/系统架构.md) (文档不存在) --> - 了解整体设计
- [Docker部署](../06-部署运维/Docker部署.md) - 生产部署指南
- <!-- [知识图谱快速导入](../06-部署运维/知识图谱快速导入指南.md) (文档不存在) --> - Neo4j数据导入

### 进阶文档
- [代码参考](../03-代码参考/README.md) - 详细代码说明
- [API文档](../05-API文档/README.md) - MCP工具API
- [双模型使用指南](../04-开发指南/双模型框架使用指南.md) - DeepSeek + Ollama

---

## ⚠️ 重要提示

### Docker磁盘清理

如果磁盘空间不足，运行以下命令清理：

```bash
# 查看Docker磁盘使用情况
docker system df

# 清理未使用的镜像、容器、网络（保留数据卷）
docker system prune -a

# ⚠️ 危险：清理所有未使用数据（包括数据卷）
docker system prune -a --volumes
```

### 资源限制配置

在`docker-compose.yml`中添加资源限制：

```yaml
services:
  meta-learning-mcp:
    deploy:
      resources:
        limits:
          cpus: '8.0'      # 限制最多8核
          memory: 8G       # 限制最多8GB内存
        reservations:
          cpus: '2.0'      # 保留2核
          memory: 4G       # 保留4GB内存
```

### 性能监控

实时监控容器资源使用：

```bash
# 查看所有容器资源使用
docker stats

# 查看特定容器
docker stats fitness_mcp_meta_learning fitness_neo4j fitness_qdrant

# 查看容器日志
docker-compose logs -f --tail=100 meta-learning-mcp
```

---

**维护者**: 薛小川  
**最后更新**: 2025-11-08  
**测试环境**: Windows 11 · Docker Desktop 4.x · 16GB RAM · 8核CPU

---

<div align="center">
<strong>⚠️ 请确保硬件资源充足 · 💾 86GB磁盘 · 🧠 16GB+内存 · ⚡ 4核+CPU</strong>
</div>
