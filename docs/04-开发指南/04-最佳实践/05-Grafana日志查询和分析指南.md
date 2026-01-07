# Grafana日志查询和分析指南

**版本**: v2.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本指南以**Grafana Loki**为核心，提供现代化的日志查询和分析方法。Grafana提供强大的可视化界面，让日志分析变得直观高效。命令行工具作为应急备选方案。

### 适用场景

- 📊 **日常运维** - 通过Grafana Dashboard查看日志
- 🔍 **问题排查** - 使用LogQL快速定位错误
- 📈 **趋势分析** - 可视化日志量和错误率趋势
- 🚨 **告警响应** - 基于日志配置告警规则

### 工具优先级

1. **Grafana Loki**（主要，80%场景） - 可视化日志查询和分析
2. **命令行工具**（应急，20%场景） - 服务器无法访问Web界面时使用

---

## Grafana Loki日志查询

### 1. 访问Grafana

**访问地址**：http://localhost:3001

**默认凭据**：
- 用户名：`admin`
- 密码：`admin`（首次登录后会要求修改）

### 2. Explore界面

Grafana的Explore界面是日志查询的主要工具。

**访问路径**：
1. 点击左侧菜单的"Explore"图标（罗盘图标）
2. 选择数据源：Loki
3. 开始编写LogQL查询

**界面布局**：
```
┌─────────────────────────────────────────────────────┐
│ 数据源选择: [Loki ▼]  时间范围: [Last 1 hour ▼]    │
├─────────────────────────────────────────────────────┤
│ LogQL查询框                                          │
│ {job="daml-rag"} |= "ERROR"                         │
│ [Run query] [Add query]                             │
├─────────────────────────────────────────────────────┤
│ 📊 日志量趋势图                                      │
│ ▂▃▅▇█▇▅▃▂                                          │
├─────────────────────────────────────────────────────┤
│ 📄 日志列表                                          │
│ 2025-12-22 10:30:45 ERROR Neo4j查询失败...         │
│ 2025-12-22 10:30:50 ERROR LLM调用超时...           │
└─────────────────────────────────────────────────────┘
```

### 3. LogQL查询语言

LogQL是Loki的查询语言，类似Prometheus的PromQL。

#### 基本语法

```logql
{标签选择器} |= "搜索文本" | 过滤器 | 聚合函数
```

#### 标签选择器

```logql
# 查询特定job的日志
{job="daml-rag"}

# 多个标签组合
{job="daml-rag", level="error"}

# 正则匹配
{job=~"daml.*"}
```

#### 文本过滤

```logql
# 包含ERROR
{job="daml-rag"} |= "ERROR"

# 不包含DEBUG
{job="daml-rag"} != "DEBUG"

# 正则匹配
{job="daml-rag"} |~ "步骤[0-9]+完成"

# 多个条件
{job="daml-rag"} |= "ERROR" |= "Neo4j"
```

#### JSON解析

```logql
# 解析JSON日志
{job="daml-rag"} | json

# 提取特定字段
{job="daml-rag"} | json | level="ERROR"

# 过滤字段值
{job="daml-rag"} | json | duration_seconds > 1
```

### 4. 常用LogQL查询示例

#### 查询ERROR日志

```logql
# 查询所有ERROR日志
{job="daml-rag"} |= "ERROR"

# 查询特定类型的ERROR
{job="daml-rag"} |= "ERROR" |= "Neo4j"

# 查询ERROR并解析JSON
{job="daml-rag"} | json | level="ERROR"
```

#### 查询特定用户的日志

```logql
# 查询特定用户
{job="daml-rag"} | json | user_id="user_001"

# 查询用户的ERROR日志
{job="daml-rag"} | json | user_id="user_001" | level="ERROR"
```

#### 查询特定请求的完整链路

```logql
# 使用request_id追踪
{job="daml-rag"} | json | request_id="req_123456"

# 使用trace_id追踪
{job="daml-rag"} | json | trace_id="550e8400-e29b-41d4-a716-446655440000"
```

#### 查询慢操作

```logql
# 查询耗时超过1秒的操作
{job="daml-rag"} | json | duration_seconds > 1

# 查询慢步骤
{job="daml-rag"} |= "步骤" | json | duration_ms > 1000
```

#### 统计查询

```logql
# 统计ERROR数量（每分钟）
sum(rate({job="daml-rag"} |= "ERROR" [1m]))

# 按级别统计日志量
sum by (level) (rate({job="daml-rag"} | json [5m]))

# 统计各步骤平均耗时
avg by (step) (
  rate({job="daml-rag"} |= "步骤" | json | unwrap duration_ms [5m])
)
```

### 5. 创建日志Dashboard

#### 步骤1：创建新Dashboard

1. 点击左侧菜单"+"→"Dashboard"
2. 点击"Add new panel"
3. 选择数据源：Loki

#### 步骤2：配置日志量趋势面板

```json
{
  "title": "日志量趋势",
  "type": "graph",
  "targets": [
    {
      "expr": "sum(rate({job=\"daml-rag\"} [5m]))",
      "legendFormat": "总日志量"
    },
    {
      "expr": "sum(rate({job=\"daml-rag\"} |= \"ERROR\" [5m]))",
      "legendFormat": "ERROR日志"
    }
  ]
}
```

#### 步骤3：配置日志列表面板

```json
{
  "title": "最近日志",
  "type": "logs",
  "targets": [
    {
      "expr": "{job=\"daml-rag\"}"
    }
  ],
  "options": {
    "showTime": true,
    "showLabels": true,
    "wrapLogMessage": true
  }
}
```

#### 步骤4：配置错误率面板

```json
{
  "title": "错误率",
  "type": "stat",
  "targets": [
    {
      "expr": "sum(rate({job=\"daml-rag\"} |= \"ERROR\" [5m])) / sum(rate({job=\"daml-rag\"} [5m]))"
    }
  ],
  "options": {
    "unit": "percentunit",
    "thresholds": {
      "mode": "absolute",
      "steps": [
        {"value": 0, "color": "green"},
        {"value": 0.01, "color": "yellow"},
        {"value": 0.05, "color": "red"}
      ]
    }
  }
}
```

### 6. 配置日志告警

#### 在Grafana中配置告警

**步骤1：编辑面板**
1. 点击面板标题→"Edit"
2. 切换到"Alert"标签

**步骤2：配置告警规则**

```yaml
# ERROR日志过多告警
Alert Rule:
  Name: High Error Rate
  Condition: WHEN avg() OF query(A, 5m, now) IS ABOVE 10
  
Query A:
  sum(rate({job="daml-rag"} |= "ERROR" [1m]))
  
Notifications:
  - Send to: Slack Channel
  - Message: ERROR日志过多，每分钟超过10条
```

**步骤3：配置通知渠道**

1. 点击左侧菜单"Alerting"→"Notification channels"
2. 点击"Add channel"
3. 选择类型（Slack、Email、钉钉等）
4. 配置通知参数

### 7. 日志分析实战案例

#### 案例1：追踪用户请求失败

**场景**：用户user_001报告查询失败

**步骤1：查找用户最近的请求**

```logql
{job="daml-rag"} | json | user_id="user_001" | line_format "{{.timestamp}} {{.message}}"
```

**步骤2：找到失败的request_id**

在日志列表中找到包含"ERROR"的日志，记录request_id

**步骤3：追踪完整请求链路**

```logql
{job="daml-rag"} | json | request_id="req_123456"
```

**步骤4：分析错误原因**

查看日志中的error_type和error_message字段

#### 案例2：分析系统性能下降

**场景**：系统响应变慢，需要找出原因

**步骤1：查看耗时趋势**

```logql
# 查看P95耗时
quantile_over_time(0.95, 
  {job="daml-rag"} | json | unwrap duration_seconds [5m]
)
```

**步骤2：找出慢步骤**

```logql
# 各步骤平均耗时
avg by (step) (
  rate({job="daml-rag"} |= "步骤" | json | unwrap duration_ms [5m])
)
```

**步骤3：查看慢查询日志**

```logql
{job="daml-rag"} | json | duration_ms > 1000
```

**步骤4：分析根因**

查看慢查询的详细信息，确定是数据库、缓存还是LLM调用慢

---

## 命令行应急工具

当Grafana不可用时，使用命令行工具进行应急排查。

### 1. Docker日志查看

```bash
# 查看实时日志
docker logs -f fitness_daml_rag

# 查看最近100行
docker logs --tail 100 fitness_daml_rag

# 查看特定时间段
docker logs --since "2025-12-22T10:00:00" fitness_daml_rag
```

### 2. grep快速搜索

```bash
# 查询ERROR日志
docker logs fitness_daml_rag | grep "ERROR"

# 查询特定用户
docker logs fitness_daml_rag | grep "user_001"

# 查询特定请求
docker logs fitness_daml_rag | grep "req_123456"

# 统计ERROR数量
docker logs fitness_daml_rag | grep -c "ERROR"
```

### 3. jq处理JSON日志

```bash
# 提取ERROR日志
docker logs fitness_daml_rag | jq 'select(.level == "ERROR")'

# 提取特定字段
docker logs fitness_daml_rag | jq '{timestamp, level, message, request_id}'

# 统计各级别日志数量
docker logs fitness_daml_rag | jq -r '.level' | sort | uniq -c
```

---

## 最佳实践

### 1. 日志查询优化

✅ **使用时间范围限制**
```logql
# 好的做法：限制时间范围
{job="daml-rag"} [1h] |= "ERROR"

# 不好的做法：查询所有历史
{job="daml-rag"} |= "ERROR"
```

✅ **使用标签过滤**
```logql
# 好的做法：使用标签
{job="daml-rag", level="error"}

# 不好的做法：文本搜索
{job="daml-rag"} |= "ERROR"
```

✅ **合理使用聚合**
```logql
# 好的做法：聚合后再查询
sum by (level) (rate({job="daml-rag"} [5m]))

# 不好的做法：查询原始日志再聚合
{job="daml-rag"} | json
```

### 2. Dashboard设计

✅ **分层展示**
- 顶部：关键指标（错误率、日志量）
- 中部：趋势图表
- 底部：详细日志列表

✅ **使用变量**
```
# 定义变量
$user_id = user_001
$time_range = 1h

# 在查询中使用
{job="daml-rag"} | json | user_id="$user_id"
```

✅ **设置合理的刷新间隔**
- 实时监控：5-10秒
- 日常查看：30秒-1分钟
- 历史分析：不自动刷新

### 3. 告警配置

✅ **设置合理阈值**
- ERROR率 > 5%：告警
- 日志量突增 > 2倍：告警
- 特定错误出现：立即告警

✅ **避免告警疲劳**
- 设置冷却时间
- 合并相似告警
- 分级告警（WARNING/CRITICAL）

---

## 常见问题排查

### 问题1：Grafana无法连接Loki

**症状**：Dashboard显示"No data"

**排查步骤**：

1. 检查Loki服务状态
```bash
docker-compose ps loki
```

2. 检查Loki日志
```bash
docker-compose logs loki
```

3. 测试Loki API
```bash
curl http://localhost:3100/ready
```

4. 检查Grafana数据源配置
- 访问：Configuration → Data Sources → Loki
- 测试连接：点击"Save & Test"

### 问题2：日志查询很慢

**原因**：
- 时间范围太大
- 查询条件不够精确
- 日志量过大

**解决方案**：

1. 缩小时间范围
```logql
# 从1天缩小到1小时
{job="daml-rag"} [1h]
```

2. 添加更多过滤条件
```logql
# 添加标签过滤
{job="daml-rag", level="error"} |= "Neo4j"
```

3. 使用聚合查询
```logql
# 使用rate聚合
sum(rate({job="daml-rag"} [5m]))
```

### 问题3：找不到特定日志

**可能原因**：
- 日志还未被Loki采集
- 查询条件不正确
- 日志已过期被删除

**排查步骤**：

1. 检查Promtail状态
```bash
docker-compose ps promtail
docker-compose logs promtail
```

2. 验证日志文件路径
```bash
# 检查日志文件是否存在
docker exec fitness_daml_rag ls -la logs/
```

3. 检查Loki保留策略
```yaml
# loki-config.yaml
limits_config:
  retention_period: 168h  # 7天
```

---

## 相关文档

- **监控系统架构**: `02-核心架构/05-监控层/01-监控系统架构.md`
- **日志系统架构**: `02-核心架构/05-监控层/03-日志系统架构.md`
- **Grafana告警配置指南**: `04-开发指南/04-最佳实践/06-Grafana告警配置和响应指南.md`
- **Grafana性能排查指南**: `04-开发指南/04-最佳实践/07-Grafana性能问题排查指南.md`
- **Grafana配置文档**: `config/grafana/README.md`

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
