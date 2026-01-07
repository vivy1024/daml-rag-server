# Prometheus告警快速参考

**版本**: v1.0.0  
**创建日期**: 2025-12-21

---

## 告警规则速查表

### 性能瓶颈告警 (6个)

| 告警 | 阈值 | 严重级别 |
|------|------|---------|
| WorkflowTotalDurationHigh | >30秒 | warning |
| WorkflowStepDurationHigh | >1秒 | warning |
| TTFBHigh | >5秒 | warning |
| UserProfileLoadingHigh | >500ms | warning |
| MembershipCheckHigh | >300ms | warning |
| BGEClassificationHigh | >500ms | warning |

### 错误率告警 (4个)

| 告警 | 阈值 | 严重级别 |
|------|------|---------|
| WorkflowFailureRateHigh | >5% | critical |
| LLMErrorRateHigh | >5% | critical |
| LLMFallbackCountHigh | >0.1/秒 | warning |
| CacheMissRateHigh | >50% | warning |

### 资源使用告警 (6个)

| 告警 | 阈值 | 严重级别 |
|------|------|---------|
| CPUUsageHigh | >70% | warning |
| CPUUsageCritical | >90% | critical |
| MemoryUsageHigh | >80% | warning |
| MemoryUsageCritical | >95% | critical |
| ConnectionPoolUsageHigh | >80% | warning |
| ConnectionPoolWaitTimeHigh | >2秒 | warning |

### 并发控制告警 (4个)

| 告警 | 阈值 | 严重级别 |
|------|------|---------|
| ConcurrentRequestsHigh | >80 | warning |
| ConcurrentRequestsCritical | >95 | critical |
| QueueLengthHigh | >150 | warning |
| RateLimitErrorsHigh | >0.1/秒 | warning |

### 服务健康告警 (4个)

| 告警 | 阈值 | 严重级别 |
|------|------|---------|
| ServiceDown | 不可用 | critical |
| RedisDown | 不可用 | critical |
| MySQLDown | 不可用 | critical |
| Neo4jDown | 不可用 | critical |

---

## 常用命令

### 验证配置

```bash
# 验证Prometheus配置
docker exec fitness_prometheus promtool check config /etc/prometheus/prometheus.yml

# 验证告警规则
docker exec fitness_prometheus promtool check rules /etc/prometheus/alerts/workflow_performance.yml

# 验证Alertmanager配置
docker exec fitness_alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# 使用Python脚本验证
docker exec fitness_daml_rag python scripts/validate_prometheus_config.py
```

### 查看服务

```bash
# 查看Prometheus日志
docker-compose logs -f prometheus

# 查看Alertmanager日志
docker-compose logs -f alertmanager

# 重启服务
docker-compose restart prometheus alertmanager
```

### 访问界面

- **Prometheus**: http://localhost:9090
  - 告警规则: http://localhost:9090/alerts
  - 指标查询: http://localhost:9090/graph

- **Alertmanager**: http://localhost:9093
  - 告警列表: http://localhost:9093/#/alerts
  - 静默管理: http://localhost:9093/#/silences

- **Grafana**: http://localhost:3001
  - 工作流性能仪表板

---

## 告警处理流程

### 1. 性能瓶颈告警

```
收到告警 → 查看Grafana仪表板 → 定位慢步骤 → 优化代码/配置
```

**常见原因**:
- 数据库查询慢
- 缓存未命中
- 网络延迟
- 并发过高

### 2. 错误率告警

```
收到告警 → 查看日志 → 分析错误类型 → 修复问题
```

**常见原因**:
- LLM后端不可用
- 数据库连接失败
- 配置错误
- 代码bug

### 3. 资源使用告警

```
收到告警 → 查看资源监控 → 分析资源瓶颈 → 扩容/优化
```

**常见原因**:
- 内存泄漏
- CPU密集计算
- 连接池耗尽
- 并发过高

### 4. 并发控制告警

```
收到告警 → 查看并发统计 → 调整限流配置 → 扩容服务
```

**常见原因**:
- 流量突增
- 限流配置过低
- 服务能力不足

### 5. 服务健康告警

```
收到告警 → 检查服务状态 → 重启服务 → 检查依赖
```

**常见原因**:
- 服务崩溃
- 网络问题
- 资源耗尽
- 配置错误

---

## 静默告警

### 通过Web界面

访问 http://localhost:9093/#/silences 创建静默规则

### 通过API

```bash
# 静默特定告警
curl -X POST http://localhost:9093/api/v1/silences -d '{
  "matchers": [
    {"name": "alertname", "value": "WorkflowStepDurationHigh"}
  ],
  "startsAt": "2025-12-21T00:00:00Z",
  "endsAt": "2025-12-21T23:59:59Z",
  "comment": "正在优化中",
  "createdBy": "admin"
}'

# 静默所有warning级别告警
curl -X POST http://localhost:9093/api/v1/silences -d '{
  "matchers": [
    {"name": "severity", "value": "warning"}
  ],
  "startsAt": "2025-12-21T00:00:00Z",
  "endsAt": "2025-12-21T12:00:00Z",
  "comment": "维护窗口",
  "createdBy": "admin"
}'
```

---

## 测试告警

### 手动触发测试告警

```bash
# 发送测试告警到Alertmanager
curl -X POST http://localhost:9093/api/v1/alerts -d '[
  {
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning",
      "category": "test"
    },
    "annotations": {
      "summary": "测试告警",
      "description": "这是一个测试告警，用于验证告警系统"
    },
    "startsAt": "2025-12-21T10:00:00Z"
  }
]'
```

### 查看告警状态

```bash
# 查看当前活跃告警
curl http://localhost:9093/api/v1/alerts

# 查看Prometheus告警规则状态
curl http://localhost:9090/api/v1/rules
```

---

## 调优建议

### 1. 调整阈值

根据实际运行情况调整告警阈值，避免误报：

```yaml
# 示例：调整工作流总耗时阈值
- alert: WorkflowTotalDurationHigh
  expr: workflow_total_duration_seconds > 30  # 调整为40
  for: 1m  # 调整为2m
```

### 2. 调整持续时间

增加持续时间可以减少瞬时波动导致的误报：

```yaml
# 示例：调整CPU告警持续时间
- alert: CPUUsageHigh
  expr: process_cpu_percent > 70
  for: 3m  # 从3分钟调整到5分钟
```

### 3. 调整重复间隔

根据告警重要性调整重复通知间隔：

```yaml
# 在alertmanager.yml中调整
routes:
  - match:
      severity: warning
    receiver: 'default'
    repeat_interval: 12h  # 调整为6h或24h
```

---

## 故障排查

### Prometheus无法启动

1. 检查配置文件语法
2. 检查端口占用
3. 查看日志: `docker-compose logs prometheus`

### Alertmanager无法发送告警

1. 检查配置文件语法
2. 测试Webhook连接
3. 查看日志: `docker-compose logs alertmanager`

### 告警规则不生效

1. 检查规则文件语法
2. 验证PromQL表达式
3. 确认指标名称正确
4. 检查标签匹配

---

## 相关文档

- [完整配置说明](./ALERT_CONFIGURATION.md)
- [Grafana仪表板](../grafana/README.md)
- [性能优化指南](../../docs/04-开发指南/11-性能优化指南.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-21
