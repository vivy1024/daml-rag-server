# Docker性能优化配置指南

**版本**: v1.0.0  
**创建日期**: 2025-12-21  
**状态**: ✅ 已完成

---

## 概述

本文档说明如何配置和使用Docker环境中的性能优化功能，包括Redis缓存、Prometheus监控和Grafana可视化。

---

## 服务架构

### 性能优化相关服务

```
DAML-RAG服务器 (8001)
    ↓
Redis缓存 (6379) ← L2缓存层
    ↓
Prometheus (9090) ← 指标收集
    ↓
Grafana (3001) ← 可视化仪表板
```

---

## 服务配置

### 1. Redis缓存服务

**容器名**: `fitness_redis`  
**端口**: 6379  
**配置文件**: `daml-rag-server/config/redis/redis.conf`

#### 性能配置

```yaml
# 内存限制
maxmemory: 512mb
maxmemory-policy: allkeys-lru

# 连接配置
maxclients: 1000
timeout: 300
tcp-keepalive: 60

# 持久化
appendonly: yes
save: 900 1, 300 10, 60 10000
```

#### 启动命令

```bash
# 启动Redis服务
docker-compose up -d redis

# 查看Redis日志
docker-compose logs -f redis

# 进入Redis CLI
docker exec -it fitness_redis redis-cli

# 查看Redis信息
docker exec fitness_redis redis-cli INFO
```

#### 监控Redis

```bash
# 查看内存使用
docker exec fitness_redis redis-cli INFO memory

# 查看连接数
docker exec fitness_redis redis-cli INFO clients

# 查看慢查询
docker exec fitness_redis redis-cli SLOWLOG GET 10

# 查看缓存命中率
docker exec fitness_redis redis-cli INFO stats
```

---

### 2. Prometheus监控服务

**容器名**: `fitness_prometheus`  
**端口**: 9090  
**配置文件**: `daml-rag-server/config/prometheus/prometheus.yml`

#### 配置说明

```yaml
# 数据保留
storage.tsdb.retention.time: 30d
storage.tsdb.retention.size: 10GB

# 抓取配置
scrape_interval: 15s
evaluation_interval: 15s

# 目标配置
targets:
  - daml-rag-server:8002  # DAML-RAG指标端点
```

#### 启动命令

```bash
# 启动Prometheus服务
docker-compose up -d prometheus

# 查看Prometheus日志
docker-compose logs -f prometheus

# 重新加载配置（无需重启）
docker exec fitness_prometheus kill -HUP 1
```

#### 访问Prometheus

- **Web UI**: http://localhost:9090
- **查询示例**:
  ```promql
  # 工作流总耗时
  workflow_total_duration_seconds
  
  # 缓存命中率
  rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])
  
  # 步骤耗时
  workflow_step_duration_seconds{step="1"}
  ```

---

### 3. Grafana可视化服务

**容器名**: `fitness_grafana`  
**端口**: 3001  
**配置目录**: `daml-rag-server/config/grafana/`

#### 登录信息

- **URL**: http://localhost:3001
- **用户名**: admin
- **密码**: Xxxc1765563156.

#### 启动命令

```bash
# 启动Grafana服务
docker-compose up -d grafana

# 查看Grafana日志
docker-compose logs -f grafana

# 重启Grafana
docker-compose restart grafana
```

#### 仪表板配置

Grafana会自动加载以下仪表板：

1. **工作流性能总览** (`daml-rag-server/config/grafana/dashboards/workflow_performance.json`)
   - 工作流总耗时趋势
   - 步骤级别性能分析
   - TTFB统计
   - 性能瓶颈识别

2. **缓存性能监控** (`daml-rag-server/config/grafana/dashboards/cache_performance.json`)
   - 缓存命中率
   - L1/L2/L3缓存统计
   - 缓存失效率
   - 缓存内存使用

3. **连接池监控** (`daml-rag-server/config/grafana/dashboards/connection_pool.json`)
   - MySQL连接池使用率
   - Neo4j连接池使用率
   - HTTP连接池使用率
   - 连接等待时间

4. **LLM调用监控** (`daml-rag-server/config/grafana/dashboards/llm_performance.json`)
   - LLM调用成功率
   - 降级次数统计
   - 调用耗时分布
   - 后端健康状态

---

## DAML-RAG服务配置

### 环境变量

在`docker-compose.yml`中，DAML-RAG服务已配置以下性能优化环境变量：

```yaml
# 性能优化配置
PERFORMANCE_OPTIMIZATION_ENABLED: "true"
PERFORMANCE_CONFIG_PATH: /app/config/performance_optimization.yaml

# 缓存配置
CACHE_L1_ENABLED: "true"
CACHE_L2_ENABLED: "true"
CACHE_L2_HOST: redis
CACHE_L2_PORT: 6379

# 监控配置
MONITORING_ENABLED: "true"
PROMETHEUS_ENABLED: "true"
PROMETHEUS_PORT: 8002
METRICS_EXPORT_INTERVAL: 10

# 并发限流配置
CONCURRENCY_MAX_CONCURRENT: 100
CONCURRENCY_MAX_QUEUE_SIZE: 200
CONCURRENCY_TIMEOUT: 30

# 连接池配置
CONNECTION_POOL_MYSQL_MIN: 10
CONNECTION_POOL_MYSQL_MAX: 50
CONNECTION_POOL_NEO4J_MIN: 5
CONNECTION_POOL_NEO4J_MAX: 20
CONNECTION_POOL_HTTP_MIN: 20
CONNECTION_POOL_HTTP_MAX: 100
```

### 指标端点

DAML-RAG服务暴露Prometheus指标端点：

- **URL**: http://localhost:8002/metrics
- **格式**: Prometheus文本格式

---

## 完整启动流程

### 1. 启动所有服务

```bash
# 启动所有服务（包括性能监控）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看所有日志
docker-compose logs -f
```

### 2. 验证服务

```bash
# 验证Redis
docker exec fitness_redis redis-cli PING
# 预期输出: PONG

# 验证Prometheus
curl http://localhost:9090/-/healthy
# 预期输出: Prometheus is Healthy.

# 验证Grafana
curl http://localhost:3001/api/health
# 预期输出: {"commit":"...","database":"ok","version":"..."}

# 验证DAML-RAG指标
curl http://localhost:8002/metrics
# 预期输出: Prometheus指标数据
```

### 3. 访问监控界面

1. **Prometheus**: http://localhost:9090
   - 查看目标状态: Status → Targets
   - 执行查询: Graph → 输入PromQL

2. **Grafana**: http://localhost:3001
   - 登录: admin / Xxxc1765563156.
   - 查看仪表板: Dashboards → Browse

3. **Redis Commander**: http://localhost:8081
   - 查看缓存数据
   - 监控Redis状态

---

## 性能监控指标

### 工作流指标

| 指标名称 | 说明 | 单位 |
|---------|------|------|
| `workflow_total_duration_seconds` | 工作流总耗时 | 秒 |
| `workflow_step_duration_seconds` | 步骤耗时 | 秒 |
| `workflow_success_rate` | 工作流成功率 | 百分比 |
| `workflow_concurrent_requests` | 并发请求数 | 个 |

### 缓存指标

| 指标名称 | 说明 | 单位 |
|---------|------|------|
| `cache_hit_rate` | 缓存命中率 | 百分比 |
| `cache_miss_rate` | 缓存未命中率 | 百分比 |
| `cache_eviction_count` | 缓存淘汰次数 | 次 |
| `cache_memory_usage_bytes` | 缓存内存使用 | 字节 |

### 连接池指标

| 指标名称 | 说明 | 单位 |
|---------|------|------|
| `connection_pool_active` | 活跃连接数 | 个 |
| `connection_pool_idle` | 空闲连接数 | 个 |
| `connection_pool_wait_time_seconds` | 连接等待时间 | 秒 |

### LLM指标

| 指标名称 | 说明 | 单位 |
|---------|------|------|
| `llm_call_duration_seconds` | LLM调用耗时 | 秒 |
| `llm_fallback_count` | 降级次数 | 次 |
| `llm_error_rate` | 错误率 | 百分比 |

---

## 告警配置

### Prometheus告警规则

告警规则位于: `daml-rag-server/config/prometheus/alerts/`

#### 性能瓶颈告警

```yaml
- alert: WorkflowPerformanceBottleneck
  expr: workflow_step_duration_seconds > 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "工作流步骤耗时超过1秒"
```

#### 错误率告警

```yaml
- alert: HighErrorRate
  expr: rate(workflow_errors_total[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "错误率超过5%"
```

#### 资源使用告警

```yaml
- alert: HighCPUUsage
  expr: process_cpu_seconds_total > 0.7
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "CPU使用率超过70%"
```

---

## 故障排查

### Redis连接问题

```bash
# 检查Redis是否运行
docker-compose ps redis

# 查看Redis日志
docker-compose logs redis

# 测试Redis连接
docker exec fitness_redis redis-cli PING

# 检查Redis配置
docker exec fitness_redis redis-cli CONFIG GET maxmemory
```

### Prometheus抓取失败

```bash
# 检查Prometheus目标状态
curl http://localhost:9090/api/v1/targets

# 查看Prometheus日志
docker-compose logs prometheus

# 验证DAML-RAG指标端点
curl http://localhost:8002/metrics
```

### Grafana仪表板不显示数据

```bash
# 检查Grafana数据源配置
curl -u admin:Xxxc1765563156. http://localhost:3001/api/datasources

# 查看Grafana日志
docker-compose logs grafana

# 验证Prometheus连接
curl http://localhost:9090/api/v1/query?query=up
```

---

## 性能调优建议

### Redis优化

1. **内存调优**
   ```bash
   # 根据实际使用调整maxmemory
   # 建议: 系统内存的25-50%
   maxmemory 1gb
   ```

2. **持久化优化**
   ```bash
   # 如果不需要持久化，可以禁用
   appendonly no
   save ""
   ```

3. **连接池优化**
   ```bash
   # 增加最大客户端连接数
   maxclients 2000
   ```

### Prometheus优化

1. **数据保留优化**
   ```bash
   # 根据磁盘空间调整保留时间
   --storage.tsdb.retention.time=15d
   --storage.tsdb.retention.size=5GB
   ```

2. **抓取频率优化**
   ```yaml
   # 降低抓取频率以减少负载
   scrape_interval: 30s
   ```

### Grafana优化

1. **查询优化**
   - 使用时间范围限制
   - 避免过于复杂的查询
   - 使用变量简化仪表板

2. **刷新频率优化**
   - 开发环境: 30秒
   - 生产环境: 1分钟

---

## 配置文件参考

### 主要配置文件

| 文件路径 | 说明 |
|---------|------|
| `docker-compose.yml` | Docker服务配置 |
| `daml-rag-server/config/performance_optimization.yaml` | 性能优化配置 |
| `daml-rag-server/config/redis/redis.conf` | Redis配置 |
| `daml-rag-server/config/prometheus/prometheus.yml` | Prometheus配置 |
| `daml-rag-server/config/grafana/datasources/` | Grafana数据源配置 |
| `daml-rag-server/config/grafana/dashboards/` | Grafana仪表板配置 |

---

## 相关文档

- [性能优化配置使用指南](../03-配置管理/04-性能优化配置使用指南.md)
- [Prometheus配置快速参考](../../config/prometheus/QUICK_REFERENCE.md)
- [Grafana部署指南](../../config/grafana/DEPLOYMENT_GUIDE.md)
- [性能优化设计文档](../../.kiro/specs/workflow-performance-optimization/design.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-21
