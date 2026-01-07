# Promtail 配置说明

**版本**: v1.0.0  
**创建日期**: 2025-12-23  
**状态**: ✅ 已完成

---

## 概述

Promtail是Grafana Loki的官方日志采集器，负责从多个来源采集日志并发送到Loki进行聚合和查询。

### 配置文件

- **主配置**: `promtail-config.yml`
- **位置**: `daml-rag-server/config/promtail/`

---

## 配置结构

### 1. 服务器配置

```yaml
server:
  http_listen_port: 9080  # HTTP API端口
  grpc_listen_port: 0     # 禁用gRPC
  log_level: info         # 日志级别
```

### 2. Loki客户端配置

```yaml
clients:
  - url: http://loki:3100/loki/api/v1/push
    batchwait: 1s         # 批量等待时间
    batchsize: 1048576    # 批量大小（1MB）
    timeout: 10s          # 超时时间
```

### 3. 日志采集配置

配置了三个采集任务（scrape_configs）：

#### 任务1: Docker容器日志采集

- **job_name**: `daml-rag-container`
- **来源**: Docker容器 `fitness_daml_rag`
- **方式**: Docker Socket自动发现
- **标签**: container, stream, level, logger, request_id

#### 任务2: 日志文件采集

- **job_name**: `daml-rag-files`
- **来源**: `/app/logs/daml-rag-*.log`
- **标签**: level, logger, request_id, user_id, session_id

#### 任务3: 错误日志文件采集

- **job_name**: `daml-rag-error-files`
- **来源**: `/app/logs/daml-rag-error-*.log`
- **标签**: level, logger, request_id, error_type

---

## 日志解析规则

### 正则表达式

Promtail使用以下正则表达式解析DAML-RAG日志：

```regex
^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (?P<logger>\S+) - (?P<level>\S+) - (?P<message>.*)
```

**匹配示例**：
```
2025-12-22 22:15:42,092 - src.api.middleware.security - INFO - 安全中间件已初始化
```

**提取字段**：
- `timestamp`: 2025-12-22 22:15:42,092
- `logger`: src.api.middleware.security
- `level`: INFO
- `message`: 安全中间件已初始化

### 标签提取

#### 基础标签（所有日志）

- **level**: 日志级别（INFO, WARNING, ERROR, CRITICAL）
- **logger**: 日志记录器名称

#### 扩展标签（从消息中提取）

- **request_id**: 请求ID（格式：`req_[a-zA-Z0-9]+`）
  - 示例：`[req_abc123]`
  
- **user_id**: 用户ID（格式：`user_id=[a-zA-Z0-9_]+`）
  - 示例：`user_id=user_456`
  
- **session_id**: 会话ID（格式：`session_id=[a-zA-Z0-9_]+`）
  - 示例：`session_id=sess_789`
  
- **error_type**: 错误类型（格式：`error_type=[a-zA-Z0-9_]+`）
  - 示例：`error_type=ConnectionError`

---

## Pipeline处理流程

每个采集任务都经过以下处理阶段：

```
1. 正则表达式解析
   ↓
2. 提取基础标签（level, logger）
   ↓
3. 解析时间戳
   ↓
4. 提取request_id
   ↓
5. 提取其他标签（user_id, session_id, error_type）
   ↓
6. 输出到Loki
```

---

## 性能配置

### 批量发送

- **批量等待时间**: 1秒
- **批量大小**: 1MB
- **目的**: 减少网络请求，提高吞吐量

### 限制配置

```yaml
limits_config:
  readline_rate: 10000      # 每秒最大读取行数
  readline_burst: 20000     # 突发读取行数
  max_line_size: 256KB      # 单行最大大小
```

### 重试配置

```yaml
backoff_config:
  min_period: 500ms         # 最小重试间隔
  max_period: 5m            # 最大重试间隔
  max_retries: 10           # 最大重试次数
```

---

## 使用示例

### 在Loki中查询日志

#### 查询特定request_id的日志

```logql
{job="daml-rag-files"} |= "req_abc123"
```

#### 查询错误日志

```logql
{job="daml-rag-files", level="ERROR"}
```

#### 查询特定用户的日志

```logql
{job="daml-rag-files", user_id="user_456"}
```

#### 查询特定会话的日志

```logql
{job="daml-rag-files", session_id="sess_789"}
```

#### 查询特定错误类型

```logql
{job="daml-rag-error-files", error_type="ConnectionError"}
```

---

## 故障排查

### 1. Promtail无法启动

**检查项**：
- Docker Socket是否挂载正确
- 配置文件语法是否正确
- Loki服务是否可访问

**查看日志**：
```bash
docker logs fitness_promtail
```

### 2. 日志未被采集

**检查项**：
- 日志文件路径是否正确（`/app/logs/`）
- 容器名称是否正确（`fitness_daml_rag`）
- 正则表达式是否匹配日志格式

**验证采集**：
```bash
# 查看Promtail指标
curl http://localhost:9080/metrics

# 查看采集目标
curl http://localhost:9080/targets
```

### 3. 标签未提取

**检查项**：
- 正则表达式是否正确
- 日志消息格式是否符合预期
- Pipeline配置是否正确

**调试方法**：
- 启用Promtail调试日志：`log_level: debug`
- 查看Promtail日志中的解析错误

### 4. 性能问题

**优化建议**：
- 增加批量大小（`batchsize`）
- 减少采集频率（`refresh_interval`）
- 限制日志行大小（`max_line_size`）
- 使用标签过滤减少数据量

---

## 配置验证

### 验证配置文件语法

```bash
# 在容器内验证
docker exec fitness_promtail promtail -config.file=/etc/promtail/config.yml -dry-run
```

### 测试日志采集

```bash
# 1. 生成测试日志
docker exec fitness_daml_rag python -c "import logging; logging.basicConfig(level=logging.INFO); logging.info('Test log message')"

# 2. 在Loki中查询
curl -G -s "http://localhost:3100/loki/api/v1/query" --data-urlencode 'query={job="daml-rag-files"}' | jq
```

---

## 相关文档

- **Loki配置**: `../loki/loki-config.yml`
- **日志系统架构**: `../../docs/02-核心架构/05-监控层/03-日志系统架构.md`
- **日志查询指南**: `../../docs/04-开发指南/04-最佳实践/05-Grafana日志查询和分析指南.md`
- **Promtail官方文档**: https://grafana.com/docs/loki/latest/clients/promtail/

---

**维护者**: 薛小川  
**创建日期**: 2025-12-23  
**版本**: v1.0.0

