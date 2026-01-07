# Prometheus 告警配置说明

**版本**: v1.0.0  
**创建日期**: 2025-12-21  
**需求**: 6.4

---

## 概述

本文档说明DAML-RAG工作流性能优化的Prometheus告警规则配置。

---

## 告警规则分类

### 1. 性能瓶颈告警 (performance_bottleneck)

| 告警名称 | 触发条件 | 阈值 | 持续时间 | 严重级别 |
|---------|---------|------|---------|---------|
| WorkflowTotalDurationHigh | 工作流总耗时 | >30秒 | 1分钟 | warning |
| WorkflowStepDurationHigh | 步骤耗时 | >1秒 | 1分钟 | warning |
| TTFBHigh | 首字节响应时间 | >5秒 | 1分钟 | warning |
| UserProfileLoadingHigh | 用户档案加载 | >500ms | 1分钟 | warning |
| MembershipCheckHigh | 会员权限检查 | >300ms | 1分钟 | warning |
| BGEClassificationHigh | BGE复杂度分类 | >500ms | 1分钟 | warning |

**对应需求**: 1.1, 2.1, 5.1, 6.1

### 2. 错误率告警 (error_rate)

| 告警名称 | 触发条件 | 阈值 | 持续时间 | 严重级别 |
|---------|---------|------|---------|---------|
| WorkflowFailureRateHigh | 工作流失败率 | >5% | 2分钟 | critical |
| LLMErrorRateHigh | LLM调用错误率 | >5% | 2分钟 | critical |
| LLMFallbackCountHigh | LLM降级频率 | >0.1/秒 | 2分钟 | warning |
| CacheMissRateHigh | 缓存未命中率 | >50% | 5分钟 | warning |

**对应需求**: 3.1, 3.2, 8.2

### 3. 资源使用告警 (resource_usage)

| 告警名称 | 触发条件 | 阈值 | 持续时间 | 严重级别 |
|---------|---------|------|---------|---------|
| CPUUsageHigh | CPU使用率 | >70% | 3分钟 | warning |
| CPUUsageCritical | CPU使用率严重 | >90% | 1分钟 | critical |
| MemoryUsageHigh | 内存使用率 | >80% | 3分钟 | warning |
| MemoryUsageCritical | 内存使用率严重 | >95% | 1分钟 | critical |
| ConnectionPoolUsageHigh | 连接池使用率 | >80% | 3分钟 | warning |
| ConnectionPoolWaitTimeHigh | 连接池等待时间 | >2秒 | 1分钟 | warning |

**对应需求**: 7.2, 7.5

### 4. 并发控制告警 (concurrency_control)

| 告警名称 | 触发条件 | 阈值 | 持续时间 | 严重级别 |
|---------|---------|------|---------|---------|
| ConcurrentRequestsHigh | 并发请求数 | >80 | 2分钟 | warning |
| ConcurrentRequestsCritical | 并发请求数严重 | >95 | 1分钟 | critical |
| QueueLengthHigh | 请求队列长度 | >150 | 2分钟 | warning |
| RateLimitErrorsHigh | 429错误频率 | >0.1/秒 | 2分钟 | warning |

**对应需求**: 4.2, 4.3

### 5. 服务健康告警 (service_health)

| 告警名称 | 触发条件 | 阈值 | 持续时间 | 严重级别 |
|---------|---------|------|---------|---------|
| ServiceDown | DAML-RAG服务 | 不可用 | 1分钟 | critical |
| RedisDown | Redis服务 | 不可用 | 1分钟 | critical |
| MySQLDown | MySQL服务 | 不可用 | 1分钟 | critical |
| Neo4jDown | Neo4j服务 | 不可用 | 1分钟 | critical |

**对应需求**: 8.5

---

## 告警路由配置

### 路由策略

```yaml
默认路由 (default)
├─ 严重告警 (critical) → critical-alerts
│  ├─ 立即发送 (group_wait: 0s)
│  └─ 1小时重复 (repeat_interval: 1h)
│
├─ 性能告警 (performance) → performance-alerts
│  ├─ 30秒等待 (group_wait: 30s)
│  └─ 6小时重复 (repeat_interval: 6h)
│
├─ 资源告警 (resource) → resource-alerts
│  ├─ 1分钟等待 (group_wait: 1m)
│  └─ 6小时重复 (repeat_interval: 6h)
│
├─ 并发告警 (concurrency) → concurrency-alerts
│  ├─ 30秒等待 (group_wait: 30s)
│  └─ 3小时重复 (repeat_interval: 3h)
│
└─ 可用性告警 (availability) → availability-alerts
   ├─ 立即发送 (group_wait: 0s)
   └─ 30分钟重复 (repeat_interval: 30m)
```

### 抑制规则

1. **服务不可用抑制其他告警**
   - 当服务不可用时，抑制该服务的其他警告级别告警
   
2. **严重告警抑制警告告警**
   - CPU严重告警时，抑制CPU警告告警
   - 内存严重告警时，抑制内存警告告警

---

## 通知渠道配置

### Webhook接收器

所有告警通过Webhook发送到DAML-RAG服务：

```
http://localhost:8001/api/alerts/webhook/{category}
```

**支持的分类**:
- `critical` - 严重告警
- `performance` - 性能告警
- `resource` - 资源告警
- `concurrency` - 并发告警
- `availability` - 可用性告警

### 扩展通知方式

可以在 `alertmanager.yml` 中添加其他通知方式：

#### Email通知

```yaml
email_configs:
  - to: 'admin@example.com'
    from: 'alertmanager@example.com'
    smarthost: 'smtp.example.com:587'
    auth_username: 'alertmanager@example.com'
    auth_password: 'password'
```

#### Slack通知

```yaml
slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
    channel: '#alerts-critical'
    title: '严重告警'
```

#### 企业微信通知

```yaml
wechat_configs:
  - corp_id: 'YOUR_CORP_ID'
    api_secret: 'YOUR_API_SECRET'
    to_user: '@all'
    agent_id: 'YOUR_AGENT_ID'
```

---

## 告警模板

告警通知使用 `templates/alert.tmpl` 模板，支持：

- **文本格式**: 用于Webhook和日志
- **Slack格式**: 用于Slack通知
- **HTML格式**: 用于Email通知

### 模板变量

- `{{ .Labels }}` - 告警标签
- `{{ .Annotations }}` - 告警注释
- `{{ .StartsAt }}` - 触发时间
- `{{ .EndsAt }}` - 恢复时间
- `{{ .GeneratorURL }}` - Prometheus链接

---

## 部署配置

### Docker Compose配置

在 `docker-compose.yml` 中添加Prometheus和Alertmanager服务：

```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: fitness_prometheus
  volumes:
    - ./daml-rag-server/config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    - ./daml-rag-server/config/prometheus/alerts:/etc/prometheus/alerts
    - prometheus_data:/prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--web.console.libraries=/usr/share/prometheus/console_libraries'
    - '--web.console.templates=/usr/share/prometheus/consoles'
  ports:
    - "9090:9090"
  networks:
    - fitness_network

alertmanager:
  image: prom/alertmanager:latest
  container_name: fitness_alertmanager
  volumes:
    - ./daml-rag-server/config/prometheus/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    - ./daml-rag-server/config/prometheus/templates:/etc/alertmanager/templates
    - alertmanager_data:/alertmanager
  command:
    - '--config.file=/etc/alertmanager/alertmanager.yml'
    - '--storage.path=/alertmanager'
  ports:
    - "9093:9093"
  networks:
    - fitness_network
```

### 启动服务

```bash
# 启动Prometheus和Alertmanager
docker-compose up -d prometheus alertmanager

# 查看日志
docker-compose logs -f prometheus
docker-compose logs -f alertmanager
```

---

## 验证配置

### 1. 验证Prometheus配置

```bash
# 检查配置文件语法
docker exec fitness_prometheus promtool check config /etc/prometheus/prometheus.yml

# 检查告警规则语法
docker exec fitness_prometheus promtool check rules /etc/prometheus/alerts/workflow_performance.yml
```

### 2. 验证Alertmanager配置

```bash
# 检查配置文件语法
docker exec fitness_alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

### 3. 访问Web界面

- **Prometheus**: http://localhost:9090
  - 查看告警规则: http://localhost:9090/alerts
  - 查看指标: http://localhost:9090/graph
  
- **Alertmanager**: http://localhost:9093
  - 查看告警: http://localhost:9093/#/alerts
  - 静默告警: http://localhost:9093/#/silences

### 4. 测试告警

```bash
# 手动触发告警（通过Alertmanager API）
curl -X POST http://localhost:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning",
      "category": "test"
    },
    "annotations": {
      "summary": "测试告警",
      "description": "这是一个测试告警"
    }
  }
]'
```

---

## 告警处理流程

### 1. 接收告警

```
Prometheus检测到指标异常
    ↓
触发告警规则
    ↓
发送到Alertmanager
    ↓
Alertmanager路由到对应接收器
    ↓
发送Webhook到DAML-RAG服务
```

### 2. 告警响应

1. **查看告警详情**
   - 访问Prometheus查看指标图表
   - 访问Grafana查看性能仪表板
   
2. **分析根因**
   - 检查日志: `docker-compose logs -f fitness_daml_rag`
   - 检查资源使用: `docker stats fitness_daml_rag`
   - 检查数据库连接: 访问PHPMyAdmin/Neo4j Browser
   
3. **采取行动**
   - 性能瓶颈: 优化代码、增加缓存、调整配置
   - 资源不足: 扩容服务器、优化资源使用
   - 服务不可用: 重启服务、检查依赖
   
4. **静默告警**（如果是已知问题）
   ```bash
   # 通过Alertmanager Web界面静默
   # 或使用API
   curl -X POST http://localhost:9093/api/v1/silences -d '{
     "matchers": [{"name": "alertname", "value": "WorkflowStepDurationHigh"}],
     "startsAt": "2025-12-21T00:00:00Z",
     "endsAt": "2025-12-21T23:59:59Z",
     "comment": "正在优化中"
   }'
   ```

---

## 告警调优

### 调整阈值

根据实际运行情况调整告警阈值：

```yaml
# 示例：调整工作流总耗时阈值
- alert: WorkflowTotalDurationHigh
  expr: workflow_total_duration_seconds > 30  # 从30秒调整到其他值
  for: 1m  # 从1分钟调整到其他值
```

### 调整持续时间

```yaml
# 示例：调整CPU告警持续时间
- alert: CPUUsageHigh
  expr: process_cpu_percent > 70
  for: 3m  # 从3分钟调整到5分钟，减少误报
```

### 调整重复间隔

```yaml
# 在alertmanager.yml中调整
routes:
  - match:
      severity: warning
    receiver: 'default'
    repeat_interval: 12h  # 从12小时调整到其他值
```

---

## 最佳实践

1. **告警分级**
   - critical: 需要立即处理的严重问题
   - warning: 需要关注但不紧急的问题
   
2. **避免告警疲劳**
   - 设置合理的阈值和持续时间
   - 使用抑制规则避免重复告警
   - 定期审查和调整告警规则
   
3. **告警可操作性**
   - 每个告警都应该有明确的处理步骤
   - 提供足够的上下文信息
   - 包含相关文档链接
   
4. **监控告警系统本身**
   - 监控Prometheus和Alertmanager的健康状态
   - 定期测试告警通知渠道
   - 备份告警配置

---

## 故障排查

### Prometheus无法启动

```bash
# 检查配置文件语法
docker exec fitness_prometheus promtool check config /etc/prometheus/prometheus.yml

# 查看日志
docker-compose logs prometheus
```

### Alertmanager无法发送告警

```bash
# 检查配置文件
docker exec fitness_alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# 查看日志
docker-compose logs alertmanager

# 测试Webhook连接
curl -X POST http://localhost:8001/api/alerts/webhook -d '{}'
```

### 告警规则不生效

1. 检查规则文件语法
2. 确认指标名称正确
3. 验证PromQL表达式
4. 检查标签匹配

---

## 相关文档

- [Prometheus官方文档](https://prometheus.io/docs/)
- [Alertmanager官方文档](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [PromQL查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana仪表板配置](./grafana/README.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-21
