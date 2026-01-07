# Docker部署

**创建日期**: 2025-12-22

---


**版本**: v5.0.0
**更新日期**: 2025-12-03  
**状态**: ✅ 生产就绪

---

## 📋 概述

本文档介绍如何使用Docker部署元学习MCP到生产环境。

---

## 🐳 部署架构

```
┌─────────────────────────────────────┐
│          Docker Compose             │
├─────────────────────────────────────┤
│  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │Neo4j │  │Qdrant│  │Redis │      │
│  │:7687 │  │:6333 │  │:6379 │      │
│  └──────┘  └──────┘  └──────┘      │
│                                      │
│  ┌──────────────────────────┐      │
│  │  Meta-Learning MCP       │      │
│  │  :8000                   │      │
│  └──────────────────────────┘      │
└─────────────────────────────────────┘
```

---

## 🚀 快速部署

### 1. 准备配置

```bash
# 克隆项目
git clone <repo-url>
cd mcp-servers/meta-learning-mcp

# 复制配置
cp config/meta_learning.json.example config/meta_learning.json
cp .env.example .env
```

### 2. 编辑配置

**编辑 `.env`**:
```bash
# API Keys
DEEPSEEK_API_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here

# Database
NEO4J_PASSWORD=your-secure-password
```

**编辑 `config/meta_learning.json`**:
```json
{
  "dual_model": {
    "teacher": {
      "api_key": "${DEEPSEEK_API_KEY}"
    }
  }
}
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 检查状态
docker-compose ps
```

### 4. 验证部署

```bash
# 检查健康状态
curl http://localhost:8001/health

# 预期输出
{
  "status": "healthy",
  "services": {
    "neo4j": true,
    "qdrant": true,
    "redis": true
  }
}
```

### 5. 构建知识图谱

```bash
# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 运行构建脚本
python build_kg_full.py
```

**预期输出**:
```
🚀 开始构建完整知识图谱 (Neo4j + Qdrant)
✅ Neo4j连接成功
✅ VectorSearchEngine已初始化
📋 第1步：处理健身动作数据
  批次 1: 创建了 1000 个节点
  批次 2: 创建了 603 个节点
✅ 健身动作数据处理完成: 1603 个动作
✅ 知识图谱构建完成
```

### 6. 测试系统

```bash
# 测试知识图谱
python tests/test_kg_queries.py

# 预期结果
✅ Neo4j: 连接正常
✅ Qdrant: 连接正常
✅ 总节点数: 2,447
✅ 总关系数: 5,569
✅ 语义搜索: 正常（BGE模型）
```

---

## 🎉 部署完成状态

**完成时间**: 2025-10-28  
**状态**: ✅ 生产就绪

### 系统状态

| 组件 | 状态 | 数据量 |
|-----|------|--------|
| **Neo4j** | ✅ 运行中 | 2,447 节点 |
| **关系** | ✅ 已建立 | 5,569 关系 |
| **Qdrant** | ✅ 运行中 | 2,177 向量 |
| **BGE模型** | ✅ GPU加速 | 768维向量 |
| **语义搜索** | ✅ 85%准确率 | 生产就绪 |

**关系类型**:
- `TARGETS_PRIMARY`: 1,703 个（主要肌群）
- `TARGETS_SECONDARY`: 2,163 个（次要肌群）
- `USES_EQUIPMENT`: 1,703 个（器械）

---

## 📦 Docker Compose配置

**文件位置**: [`docker-compose.yml`](../../docker-compose.yml)

### 核心服务配置

```yaml
version: '3.8'

services:
  # Neo4j图数据库
  neo4j:
    image: neo4j:5.14
    ports:
      - "7474:7474"  # Web UI
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_memory_heap_max__size: 2G
    volumes:
      - neo4j_data:/data
    restart: unless-stopped

  # Qdrant向量搜索
  qdrant:
    image: qdrant/qdrant:v1.7
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  # Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --save 60 1
    restart: unless-stopped

  # MCP Server (可选)
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - neo4j
      - qdrant
      - redis
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - QDRANT_HOST=qdrant
      - REDIS_HOST=redis
    volumes:
      - ./config:/app/config
    restart: unless-stopped

volumes:
  neo4j_data:
  qdrant_data:
  redis_data:
```

---

## 🔧 生产环境优化

### 1. 资源限制

```yaml
services:
  neo4j:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### 2. 持久化配置

```yaml
services:
  redis:
    command: redis-server --save 60 1 --appendonly yes
    volumes:
      - redis_data:/data
```

### 3. 日志配置

```yaml
services:
  neo4j:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

### 4. 健康检查

```yaml
services:
  neo4j:
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## 📊 监控和管理

### 查看服务状态

```bash
# 查看所有服务
docker-compose ps

# 查看资源使用
docker stats

# 查看日志
docker-compose logs -f neo4j
docker-compose logs -f qdrant
```

### 重启服务

```bash
# 重启单个服务
docker-compose restart neo4j

# 重启所有服务
docker-compose restart

# 重新构建并启动
docker-compose up -d --build
```

### 备份数据

```bash
# Neo4j备份
docker exec neo4j neo4j-admin database dump neo4j > neo4j_backup_$(date +%Y%m%d).dump

# Qdrant快照
curl -X POST 'http://localhost:6333/collections/fitness_kg/snapshots'

# 数据卷备份
docker run --rm -v neo4j_data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j_data.tar.gz /data
```

---

## 🛠️ 故障排查

### 常见问题

#### 1. 端口冲突

**症状**: 服务启动失败，提示端口被占用

**解决**:
```bash
# 检查端口占用
netstat -an | grep 7687

# 修改docker-compose.yml
ports:
  - "7688:7687"  # 改用7688
```

#### 2. 内存不足

**症状**: Neo4j或Qdrant OOM

**解决**:
```yaml
neo4j:
  environment:
    NEO4J_dbms_memory_heap_max__size: 4G
```

#### 3. 权限问题

**症状**: 数据卷挂载失败

**解决**:
```bash
# 修改数据目录权限
sudo chown -R $USER:$USER ./data

# 或使用命名卷（推荐）
volumes:
  neo4j_data:  # Docker管理的卷
```

#### 4. 网络问题

**症状**: 容器间无法通信

**解决**:
```bash
# 检查网络
docker network ls
docker network inspect meta-learning-mcp_default

# 重建网络
docker-compose down
docker-compose up -d
```

---

## 🔒 安全加固

### 1. 修改默认密码

```bash
# .env
NEO4J_PASSWORD=your-strong-password-here
REDIS_PASSWORD=your-redis-password
```

### 2. 限制网络访问

```yaml
services:
  neo4j:
    ports:
      - "127.0.0.1:7474:7474"  # 仅本地访问
      - "127.0.0.1:7687:7687"
```

### 3. 使用secrets

```yaml
secrets:
  neo4j_password:
    external: true

services:
  neo4j:
    secrets:
      - neo4j_password
```

---

## 📈 扩展部署

### 多副本部署

```yaml
services:
  mcp-server:
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
```

### 负载均衡

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - mcp-server
```

---

## 🔗 相关文档

- [环境配置](../01-快速开始/环境配置.md) - 详细配置说明
- <!-- [监控告警](./监控告警.md) (文档不存在) --> - 生产监控
- <!-- [故障排查](./故障排查.md) (文档不存在) --> - 常见问题

---

**维护者**: BUILD_BODY Team  
**最后更新**: 2025-10-28

---

<div align="center">
<strong>🐳 Docker部署 · 容器化 · 生产就绪 🐳</strong>
</div>

