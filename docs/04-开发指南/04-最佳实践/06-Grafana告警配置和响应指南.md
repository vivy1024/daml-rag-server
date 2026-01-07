# Grafana告警配置和响应指南

**版本**: v1.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本指南介绍如何在Grafana中配置告警规则、查看告警Dashboard和响应告警事件。Grafana提供了强大的告警功能，可以基于指标和日志创建告警规则，并通过多种渠道发送通知。

### 核心功能

- **告警规则配置**：基于Prometheus指标和Loki日志创建告警
- **告警Dashboard**：可视化查看活跃告警和历史记录
- **通知渠道**：支持Slack、钉钉、邮件等多种通知方式
- **告警分组**：按标签分组管理告警
- **静默管理**：临时静默特定告警

### 适用场景

- 🚨 **性能监控**：监控TTFB、耗时等性能指标
- ⚠️ **错误告警**：监控错误率和失败率
- 📊 **资源告警**：监控CPU、内存使用率
- 🔔 **业务告警**：监控关键业务指标
- 📱 **多渠道通知**：通过多种方式接收告警

---

## 1. Grafana告警架构

### 1.1 告警系统组成

```
数据源（Prometheus/Loki）
    ↓
Grafana告警规则引擎
    ├─ 评估告警条件
    ├─ 触发告警
    └─ 发送通知
    ↓
通知渠道
    ├─ Slack
    ├─ 钉钉
    ├─ 邮件
    ├─ Webhook
    └─ 企业微信
    ↓
告警Dashboard
    ├─ 活跃告警
    ├─ 告警历史
    └─ 告警统计
```

### 1.2 告警流程

```
1. 数据采集
   ↓
2. 告警规则评估（每1分钟）
   ↓
3. 条件满足 → 触发告警
   ↓
4. 发送通知到配置的渠道
   ↓
5. 记录告警历史
   ↓
6. 问题解决 → 发送恢复通知
```

### 1.3 与Prometheus Alertmanager的关系

| 特性 | Grafana告警 | Prometheus Alertmanager |
|------|------------|------------------------|
| **配置方式** | Web界面配置 | YAML文件配置 |
| **数据源** | 支持多种数据源 | 仅Prometheus |
| **告警分组** | 支持 | 支持 |
| **告警抑制** | 支持 | 支持 |
| **通知渠道** | 内置多种渠道 | 需要配置 |
| **Dashboard集成** | 原生集成 | 需要额外配置 |

**推荐使用**：
- **Grafana告警**：适合快速配置、可视化管理
- **Alertmanager**：适合复杂的告警路由和分组

---

## 2. 告警规则配置

### 2.1 创建告警规则

**步骤1：进入告警配置**
1. 登录Grafana（http://localhost:3001）
2. 点击左侧菜单 "Alerting" → "Alert rules"
3. 点击 "New alert rule"

**步骤2：配置查询**
1. **Rule name**: 输入告警规则名称（如"工作流耗时过高"）
2. **Data source**: 选择Prometheus
3. **Query**: 输入PromQL查询


**示例查询**：
```promql
# 工作流总耗时
workflow_total_duration_seconds

# 错误率
(1 - workflow_success_rate)

# CPU使用率
process_cpu_percent

# 并发请求数
workflow_concurrent_requests
```

**步骤3：设置告警条件**
1. **Condition**: 选择条件类型
   - `IS ABOVE`: 大于阈值
   - `IS BELOW`: 小于阈值
   - `IS OUTSIDE RANGE`: 超出范围
   - `HAS NO VALUE`: 无数据

2. **Threshold**: 设置阈值
   - 例如：30（秒）、0.05（5%）、70（%）

3. **Evaluate**: 设置评估频率
   - `every`: 评估间隔（如1m）
   - `for`: 持续时间（如5m）

**示例配置**：
```
Query: workflow_total_duration_seconds
Condition: IS ABOVE 30
Evaluate: every 1m for 5m
```

**步骤4：配置标签和注释**
1. **Labels**: 添加标签用于分组和路由
   - `severity`: critical / warning
   - `category`: performance / reliability / resource
   - `component`: workflow / llm / cache

2. **Annotations**: 添加描述信息
   - `summary`: 告警摘要
   - `description`: 详细描述
   - `runbook_url`: 处理文档链接
   - `dashboard_url`: 相关Dashboard链接

**示例标签和注释**：
```yaml
Labels:
  severity: warning
  category: performance
  component: workflow

Annotations:
  summary: 工作流总耗时过高
  description: 工作流总耗时 {{ $value }}秒，超过30秒阈值
  runbook_url: https://docs.example.com/runbooks/workflow-duration
  dashboard_url: http://localhost:3000/d/workflow-performance
```

**步骤5：配置通知策略**
1. 选择通知渠道（Contact point）
2. 设置通知频率
3. 配置静默时间（可选）

**步骤6：保存规则**
1. 点击 "Save rule and exit"
2. 规则将立即生效

### 2.2 常用告警规则示例

#### 2.2.1 性能告警

**工作流总耗时过高**
```yaml
Rule name: 工作流总耗时过高
Query: workflow_total_duration_seconds
Condition: IS ABOVE 30
Evaluate: every 1m for 5m
Labels:
  severity: warning
  category: performance
Annotations:
  summary: 工作流总耗时超过30秒
  description: 当前耗时 {{ $value }}秒
```

**TTFB过高**
```yaml
Rule name: TTFB过高
Query: workflow_ttfb_seconds
Condition: IS ABOVE 5
Evaluate: every 1m for 3m
Labels:
  severity: warning
  category: performance
Annotations:
  summary: 首字节响应时间超过5秒
  description: 当前TTFB {{ $value }}秒
```

**步骤耗时过高**
```yaml
Rule name: 步骤耗时过高
Query: workflow_step_duration_seconds{step="8"}
Condition: IS ABOVE 2
Evaluate: every 1m for 3m
Labels:
  severity: warning
  category: performance
  step: "8"
Annotations:
  summary: 步骤8（三层检索）耗时过高
  description: 当前耗时 {{ $value }}秒
```

#### 2.2.2 错误告警

**工作流失败率过高**
```yaml
Rule name: 工作流失败率过高
Query: (1 - workflow_success_rate)
Condition: IS ABOVE 0.05
Evaluate: every 1m for 2m
Labels:
  severity: critical
  category: reliability
Annotations:
  summary: 工作流失败率超过5%
  description: 当前失败率 {{ $value | humanizePercentage }}
```

**LLM错误率过高**
```yaml
Rule name: LLM错误率过高
Query: llm_error_rate
Condition: IS ABOVE 0.05
Evaluate: every 1m for 2m
Labels:
  severity: critical
  category: reliability
  component: llm
Annotations:
  summary: LLM调用错误率超过5%
  description: 当前错误率 {{ $value | humanizePercentage }}
```

#### 2.2.3 资源告警

**CPU使用率过高**
```yaml
Rule name: CPU使用率过高
Query: process_cpu_percent
Condition: IS ABOVE 70
Evaluate: every 1m for 3m
Labels:
  severity: warning
  category: resource
Annotations:
  summary: CPU使用率超过70%
  description: 当前CPU使用率 {{ $value }}%
```

**内存使用率过高**
```yaml
Rule name: 内存使用率过高
Query: process_memory_percent
Condition: IS ABOVE 80
Evaluate: every 1m for 3m
Labels:
  severity: warning
  category: resource
Annotations:
  summary: 内存使用率超过80%
  description: 当前内存使用率 {{ $value }}%
```

#### 2.2.4 并发告警

**并发请求数过高**
```yaml
Rule name: 并发请求数过高
Query: workflow_concurrent_requests
Condition: IS ABOVE 80
Evaluate: every 1m for 2m
Labels:
  severity: warning
  category: concurrency
Annotations:
  summary: 并发请求数超过80
  description: 当前并发数 {{ $value }}
```

#### 2.2.5 基于日志的告警

**错误日志频率过高**
```logql
Rule name: 错误日志频率过高
Query: sum(rate({job="daml-rag"} |= "ERROR" [5m]))
Condition: IS ABOVE 0.1
Evaluate: every 1m for 2m
Labels:
  severity: warning
  category: reliability
Annotations:
  summary: 错误日志频率超过0.1/秒
  description: 当前错误频率 {{ $value }}/秒
```

---

## 3. 通知渠道配置

### 3.1 配置Contact Points

**步骤1：进入通知配置**
1. 点击 "Alerting" → "Contact points"
2. 点击 "New contact point"

**步骤2：选择通知类型**
- Slack
- 钉钉（DingDing）
- 邮件（Email）
- Webhook
- 企业微信（WeChat）

### 3.2 Slack配置

**配置步骤**：
1. **Name**: 输入名称（如"Slack-Critical"）
2. **Integration**: 选择 "Slack"
3. **Webhook URL**: 输入Slack Webhook URL
   ```
   https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
   ```
4. **Channel**: 输入频道名称（如#alerts-critical）
5. **Username**: 输入机器人名称（如"Grafana Alerts"）
6. **Icon**: 选择图标

**测试通知**：
1. 点击 "Test" 按钮
2. 检查Slack频道是否收到测试消息

**消息模板**：
```
🚨 {{ .CommonLabels.severity | toUpper }} Alert

{{ .CommonAnnotations.summary }}

Details:
{{ range .Alerts }}
- {{ .Annotations.description }}
{{ end }}

Dashboard: {{ .CommonAnnotations.dashboard_url }}
```

### 3.3 钉钉配置

**配置步骤**：
1. **Name**: 输入名称（如"DingDing-Alerts"）
2. **Integration**: 选择 "DingDing"
3. **Webhook URL**: 输入钉钉机器人Webhook URL
   ```
   https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN
   ```
4. **Message Type**: 选择 "Markdown"

**钉钉机器人创建**：
1. 打开钉钉群聊
2. 群设置 → 智能群助手 → 添加机器人
3. 选择 "自定义机器人"
4. 设置机器人名称和安全设置
5. 复制Webhook地址

**消息模板**：
```markdown
### {{ .CommonLabels.severity | toUpper }} 告警

**{{ .CommonAnnotations.summary }}**

{{ range .Alerts }}
- {{ .Annotations.description }}
{{ end }}

[查看Dashboard]({{ .CommonAnnotations.dashboard_url }})
```

### 3.4 邮件配置

**配置步骤**：
1. **Name**: 输入名称（如"Email-Alerts"）
2. **Integration**: 选择 "Email"
3. **Addresses**: 输入收件人邮箱（多个用逗号分隔）
   ```
   admin@example.com, ops@example.com
   ```
4. **Subject**: 邮件主题模板
   ```
   [{{ .CommonLabels.severity | toUpper }}] {{ .CommonAnnotations.summary }}
   ```
5. **Message**: 邮件正文模板

**SMTP配置**（在grafana.ini中）：
```ini
[smtp]
enabled = true
host = smtp.example.com:587
user = alerts@example.com
password = your_password
from_address = alerts@example.com
from_name = Grafana Alerts
```

### 3.5 Webhook配置

**配置步骤**：
1. **Name**: 输入名称（如"Webhook-DAML-RAG"）
2. **Integration**: 选择 "Webhook"
3. **URL**: 输入Webhook端点
   ```
   http://localhost:8001/api/alerts/webhook/critical
   ```
4. **HTTP Method**: 选择 "POST"
5. **Authorization**: 配置认证（可选）

**Webhook请求格式**：
```json
{
  "receiver": "webhook-daml-rag",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "WorkflowDurationHigh",
        "severity": "warning",
        "category": "performance"
      },
      "annotations": {
        "summary": "工作流总耗时过高",
        "description": "工作流总耗时 35秒，超过30秒阈值"
      },
      "startsAt": "2025-12-22T10:30:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://localhost:3000/alerting/grafana/..."
    }
  ],
  "groupLabels": {
    "alertname": "WorkflowDurationHigh"
  },
  "commonLabels": {
    "alertname": "WorkflowDurationHigh",
    "severity": "warning",
    "category": "performance"
  },
  "commonAnnotations": {
    "summary": "工作流总耗时过高",
    "description": "工作流总耗时 35秒，超过30秒阈值"
  },
  "externalURL": "http://localhost:3000"
}
```


### 3.6 企业微信配置

**配置步骤**：
1. **Name**: 输入名称（如"WeChat-Alerts"）
2. **Integration**: 选择 "WeChat"
3. **Corp ID**: 企业ID
4. **Agent ID**: 应用AgentID
5. **Secret**: 应用Secret
6. **To User**: 接收人（@all表示全部）

**企业微信应用创建**：
1. 登录企业微信管理后台
2. 应用管理 → 创建应用
3. 获取Corp ID、Agent ID和Secret
4. 配置可信IP（Grafana服务器IP）

---

## 4. 告警Dashboard配置

### 4.1 创建告警Dashboard

**步骤1：创建Dashboard**
1. 点击 "+" → "Dashboard"
2. 点击 "Add new panel"

**步骤2：配置面板**

#### 4.1.1 活跃告警面板

**面板类型**：Alert list

**配置**：
- **Title**: "活跃告警"
- **Data source**: Grafana
- **Options**:
  - Show: Current state
  - State filter: Alerting
  - Alert name filter: (留空显示所有)
  - Folder: (选择告警规则所在文件夹)
- **Display**:
  - Show annotations: ✅
  - Show time: ✅

**使用场景**：实时查看当前所有活跃告警

#### 4.1.2 告警历史面板

**面板类型**：Table

**查询配置**：
```promql
ALERTS{alertstate="firing"}
```

**面板设置**：
- **Title**: "告警历史（最近24小时）"
- **Columns**:
  - alertname: 告警名称
  - severity: 严重级别
  - category: 分类
  - value: 当前值
  - startsAt: 开始时间
- **Time range**: Last 24 hours

**使用场景**：查看历史告警记录

#### 4.1.3 告警统计面板

**面板类型**：Stat

**查询A - 活跃告警数**：
```promql
count(ALERTS{alertstate="firing"})
```

**查询B - 严重告警数**：
```promql
count(ALERTS{alertstate="firing", severity="critical"})
```

**查询C - 警告告警数**：
```promql
count(ALERTS{alertstate="firing", severity="warning"})
```

**面板设置**：
- **Title**: "告警统计"
- **Display**:
  - Orientation: Horizontal
  - Text mode: Value and name
- **Thresholds**:
  - 🟢 0
  - 🟡 1-5
  - 🔴 > 5

**使用场景**：快速了解告警概况

#### 4.1.4 告警趋势图

**面板类型**：Time series

**查询A - 总告警数**：
```promql
count(ALERTS{alertstate="firing"})
```

**查询B - 按严重级别分组**：
```promql
sum by (severity) (ALERTS{alertstate="firing"})
```

**面板设置**：
- **Title**: "告警趋势"
- **Legend**: {{severity}}
- **Y-axis**:
  - Unit: short
  - Min: 0
- **Display**:
  - Draw style: Line
  - Fill opacity: 20

**使用场景**：监控告警数量变化趋势

#### 4.1.5 按分类统计面板

**面板类型**：Pie chart

**查询配置**：
```promql
sum by (category) (ALERTS{alertstate="firing"})
```

**面板设置**：
- **Title**: "告警分类分布"
- **Legend**: {{category}}
- **Display**:
  - Pie chart type: Pie
  - Show legend: ✅
  - Show values: Percent

**使用场景**：了解告警分类分布

### 4.2 完整Dashboard示例

**Dashboard结构**：
```
DAML-RAG告警监控
├─ Row 1: 概览
│  ├─ 活跃告警数（Stat）
│  ├─ 严重告警数（Stat）
│  └─ 警告告警数（Stat）
├─ Row 2: 活跃告警
│  └─ 活跃告警列表（Alert list）
├─ Row 3: 趋势分析
│  ├─ 告警趋势图（Time series）
│  └─ 分类分布（Pie chart）
└─ Row 4: 历史记录
   └─ 告警历史表格（Table）
```

---

## 5. 告警响应流程

### 5.1 标准响应流程

```
1. 接收告警通知
   ↓
2. 确认告警（Acknowledge）
   ↓
3. 查看告警详情
   ↓
4. 分析根本原因
   ↓
5. 实施修复措施
   ↓
6. 验证问题解决
   ↓
7. 关闭告警（Resolve）
   ↓
8. 记录处理过程
```

### 5.2 接收告警

**通知渠道**：
- Slack消息
- 钉钉消息
- 邮件
- 短信（如果配置）

**告警信息包含**：
- 告警名称
- 严重级别
- 告警摘要
- 详细描述
- 当前值
- Dashboard链接
- 处理文档链接

### 5.3 确认告警

**在Grafana中确认**：
1. 进入 "Alerting" → "Alert rules"
2. 找到触发的告警规则
3. 点击 "Acknowledge"
4. 添加确认备注

**效果**：
- 告警状态变为"已确认"
- 停止重复通知
- 记录确认人和时间

### 5.4 查看告警详情

**步骤1：打开告警Dashboard**
- 点击通知中的Dashboard链接
- 或访问：http://localhost:3000/d/alerts-dashboard

**步骤2：查看相关指标**
- 查看告警触发时的指标值
- 查看指标变化趋势
- 对比历史数据

**步骤3：查看日志**
- 切换到日志Dashboard
- 使用request_id追踪完整流程
- 查找错误和异常

### 5.5 分析根本原因

**性能告警分析**：
1. 查看各步骤耗时分布
2. 识别性能瓶颈步骤
3. 查看数据库查询日志
4. 检查缓存命中率
5. 分析并发请求数

**错误告警分析**：
1. 查看错误日志详情
2. 分析错误类型和频率
3. 查看错误堆栈
4. 检查相关组件状态
5. 对比成功和失败请求

**资源告警分析**：
1. 查看资源使用趋势
2. 识别资源消耗高峰
3. 分析资源泄漏可能
4. 检查并发请求数
5. 查看系统负载

### 5.6 实施修复措施

**临时措施**：
- 重启服务
- 清理缓存
- 增加资源配额
- 启用降级策略
- 限制并发请求

**永久措施**：
- 优化代码逻辑
- 添加索引
- 调整配置参数
- 扩容服务器
- 重构架构

### 5.7 验证问题解决

**验证步骤**：
1. 查看告警是否自动恢复
2. 检查相关指标是否正常
3. 查看日志是否还有错误
4. 测试相关功能
5. 监控一段时间确保稳定

### 5.8 关闭告警

**自动关闭**：
- 当告警条件不再满足时，Grafana自动发送恢复通知
- 告警状态变为"已解决"

**手动关闭**：
1. 进入 "Alerting" → "Alert rules"
2. 找到告警规则
3. 点击 "Resolve"
4. 添加解决备注

### 5.9 记录处理过程

**记录内容**：
- 告警触发时间
- 告警详情
- 根本原因分析
- 采取的措施
- 解决时间
- 后续改进建议

**记录位置**：
- Grafana告警备注
- 运维日志系统
- 事故报告文档

---

## 6. 告警优化建议

### 6.1 减少误报

**策略**：
1. **合理设置阈值**
   - 基于历史数据的P95或P99
   - 避免过于敏感

2. **增加持续时间**
   - 瞬时波动不应触发告警
   - 建议至少持续1-3分钟

3. **使用告警抑制**
   - 服务不可用时抑制其他告警
   - 严重告警抑制警告告警

4. **定期审查规则**
   - 每月审查告警规则
   - 调整不合理的阈值
   - 删除无用的规则

### 6.2 合理设置阈值

**基于数据的阈值设置**：

| 指标 | 推荐阈值 | 依据 |
|------|---------|------|
| **工作流耗时** | P95 + 50% | 历史P95分位数 |
| **TTFB** | 3-5秒 | 用户体验标准 |
| **错误率** | 5% | 业务可接受范围 |
| **CPU使用率** | 70% (warning), 90% (critical) | 系统负载标准 |
| **内存使用率** | 80% (warning), 95% (critical) | 系统负载标准 |

**动态阈值**：
```promql
# 基于过去7天的P95设置阈值
workflow_total_duration_seconds > 
  quantile_over_time(0.95, workflow_total_duration_seconds[7d]) * 1.5
```

### 6.3 告警分组策略

**按严重级别分组**：
- Critical告警：立即通知，重复间隔1小时
- Warning告警：延迟通知，重复间隔6小时

**按分类分组**：
- 性能告警：发送到性能团队
- 错误告警：发送到开发团队
- 资源告警：发送到运维团队

**按时间分组**：
- 工作时间：所有告警正常通知
- 非工作时间：仅Critical告警通知

### 6.4 通知频率控制

**配置示例**：
```yaml
# Notification policy
Group wait: 30s        # 等待30秒收集同组告警
Group interval: 5m     # 每5分钟发送一次分组告警
Repeat interval: 4h    # 未解决的告警每4小时重复通知
```

**建议设置**：
- Critical告警：重复间隔1小时
- Warning告警：重复间隔4-6小时
- Info告警：不重复通知


---

## 7. 告警静默管理

### 7.1 创建静默规则

**使用场景**：
- 计划维护期间
- 已知问题暂时无法修复
- 测试环境告警
- 特定时间段静默

**步骤1：进入静默配置**
1. 点击 "Alerting" → "Silences"
2. 点击 "New silence"

**步骤2：配置静默规则**
1. **Matchers**: 匹配条件
   - Label: 选择标签（如severity）
   - Operator: 选择操作符（=, !=, =~, !~）
   - Value: 输入值（如warning）

2. **Duration**: 静默时长
   - 2h: 2小时
   - 1d: 1天
   - Custom: 自定义时间范围

3. **Comment**: 静默原因
   - 例如："计划维护：数据库升级"

**步骤3：保存静默规则**
- 点击 "Submit"
- 静默规则立即生效

### 7.2 静默规则示例

**维护期间静默所有告警**：
```yaml
Matchers:
  - job = daml-rag
Duration: 2h
Comment: 计划维护：系统升级
```

**静默特定分类的告警**：
```yaml
Matchers:
  - category = performance
Duration: 1d
Comment: 性能优化进行中，暂时静默性能告警
```

**静默特定严重级别的告警**：
```yaml
Matchers:
  - severity = warning
Duration: 4h
Comment: 已知问题，正在修复中
```

### 7.3 管理静默规则

**查看活跃静默**：
1. 进入 "Alerting" → "Silences"
2. 查看 "Active" 标签页

**编辑静默规则**：
1. 找到要编辑的静默规则
2. 点击 "Edit"
3. 修改配置
4. 保存

**删除静默规则**：
1. 找到要删除的静默规则
2. 点击 "Expire"
3. 静默规则立即失效

**查看已过期静默**：
1. 进入 "Alerting" → "Silences"
2. 查看 "Expired" 标签页

---

## 8. Prometheus Alertmanager配置（20%）

虽然Grafana提供了完整的告警功能，但在某些场景下仍需要使用Prometheus Alertmanager。

### 8.1 Alertmanager配置文件

**配置文件位置**：
```
config/prometheus/alertmanager.yml
```

**基本配置**：
```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'category', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 0s
      repeat_interval: 1h

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:8001/api/alerts/webhook'
        send_resolved: true
        
  - name: 'critical-alerts'
    webhook_configs:
      - url: 'http://localhost:8001/api/alerts/webhook/critical'
        send_resolved: true
```

### 8.2 告警规则文件

**规则文件位置**：
```
config/prometheus/alerts/workflow_performance.yml
```

**规则示例**：
```yaml
groups:
  - name: performance_bottleneck
    interval: 30s
    rules:
      - alert: WorkflowTotalDurationHigh
        expr: workflow_total_duration_seconds > 30
        for: 1m
        labels:
          severity: warning
          category: performance
        annotations:
          summary: "工作流总耗时过高"
          description: "工作流总耗时 {{ $value }}秒，超过30秒阈值"
```

### 8.3 验证配置

**验证Alertmanager配置**：
```bash
docker exec fitness_prometheus amtool check-config /etc/alertmanager/alertmanager.yml
```

**验证告警规则**：
```bash
docker exec fitness_prometheus promtool check rules /etc/prometheus/alerts/workflow_performance.yml
```

### 8.4 查看Alertmanager Web界面

**访问地址**：
```
http://localhost:9093
```

**功能**：
- 查看活跃告警
- 管理静默规则
- 查看告警历史
- 测试告警路由

---

## 9. 实战案例

### 9.1 案例1：配置性能告警

**场景**：监控工作流总耗时，超过30秒告警

**步骤1：创建告警规则**
```yaml
Rule name: 工作流总耗时过高
Query: workflow_total_duration_seconds
Condition: IS ABOVE 30
Evaluate: every 1m for 5m
Labels:
  severity: warning
  category: performance
Annotations:
  summary: 工作流总耗时超过30秒
  description: 当前耗时 {{ $value }}秒，建议优化性能
  dashboard_url: http://localhost:3000/d/workflow-performance
```

**步骤2：配置Slack通知**
```yaml
Contact point: Slack-Performance
Channel: #performance-alerts
Message: 
  🐌 性能告警
  {{ .CommonAnnotations.summary }}
  当前值: {{ .ValueString }}
  [查看Dashboard]({{ .CommonAnnotations.dashboard_url }})
```

**步骤3：测试告警**
1. 触发一个慢请求（耗时>30秒）
2. 等待5分钟
3. 检查Slack是否收到通知

**步骤4：响应告警**
1. 点击Dashboard链接
2. 查看各步骤耗时
3. 识别瓶颈步骤
4. 实施优化措施

### 9.2 案例2：配置错误率告警

**场景**：监控工作流失败率，超过5%立即告警

**步骤1：创建告警规则**
```yaml
Rule name: 工作流失败率过高
Query: (1 - workflow_success_rate)
Condition: IS ABOVE 0.05
Evaluate: every 1m for 2m
Labels:
  severity: critical
  category: reliability
Annotations:
  summary: 工作流失败率超过5%
  description: 当前失败率 {{ $value | humanizePercentage }}，需要立即处理
  runbook_url: https://docs.example.com/runbooks/failure-rate
```

**步骤2：配置钉钉通知**
```yaml
Contact point: DingDing-Critical
Message:
  ### 🚨 严重告警
  
  **{{ .CommonAnnotations.summary }}**
  
  当前失败率: {{ .ValueString }}
  
  [处理文档]({{ .CommonAnnotations.runbook_url }})
```

**步骤3：配置告警升级**
- 如果2分钟内未解决，发送第二次通知
- 如果10分钟内未解决，通知管理员

**步骤4：响应流程**
1. 立即确认告警
2. 查看错误日志
3. 分析失败原因
4. 实施紧急修复
5. 验证失败率下降
6. 记录处理过程

### 9.3 案例3：配置资源告警

**场景**：监控CPU使用率，超过70%警告，超过90%严重

**步骤1：创建警告级别告警**
```yaml
Rule name: CPU使用率过高（警告）
Query: process_cpu_percent
Condition: IS ABOVE 70
Evaluate: every 1m for 3m
Labels:
  severity: warning
  category: resource
Annotations:
  summary: CPU使用率超过70%
  description: 当前CPU使用率 {{ $value }}%，建议关注
```

**步骤2：创建严重级别告警**
```yaml
Rule name: CPU使用率过高（严重）
Query: process_cpu_percent
Condition: IS ABOVE 90
Evaluate: every 1m for 1m
Labels:
  severity: critical
  category: resource
Annotations:
  summary: CPU使用率超过90%
  description: 当前CPU使用率 {{ $value }}%，需要立即处理
```

**步骤3：配置不同通知渠道**
- Warning级别：发送到Slack #resource-alerts
- Critical级别：发送到钉钉 + 短信

**步骤4：响应措施**
- Warning：查看CPU使用趋势，计划优化
- Critical：立即检查进程，考虑扩容

---

## 10. 最佳实践

### 10.1 告警规则设计

**DO**：
- ✅ 基于历史数据设置阈值
- ✅ 设置合理的持续时间
- ✅ 提供清晰的描述和处理文档
- ✅ 使用标签进行分类
- ✅ 定期审查和优化规则

**DON'T**：
- ❌ 阈值过于敏感导致误报
- ❌ 阈值过于宽松导致漏报
- ❌ 不提供处理文档
- ❌ 告警描述不清晰
- ❌ 创建后不维护

### 10.2 通知配置

**DO**：
- ✅ 根据严重级别选择通知渠道
- ✅ 设置合理的通知频率
- ✅ 使用告警分组减少通知
- ✅ 提供Dashboard链接
- ✅ 测试通知渠道

**DON'T**：
- ❌ 所有告警都发送到同一渠道
- ❌ 通知频率过高导致疲劳
- ❌ 不提供上下文信息
- ❌ 通知消息格式混乱
- ❌ 不测试就上线

### 10.3 告警响应

**DO**：
- ✅ 及时确认告警
- ✅ 查看相关指标和日志
- ✅ 分析根本原因
- ✅ 记录处理过程
- ✅ 验证问题解决

**DON'T**：
- ❌ 忽略告警
- ❌ 只看告警不看数据
- ❌ 治标不治本
- ❌ 不记录处理过程
- ❌ 不验证就关闭

### 10.4 告警优化

**DO**：
- ✅ 定期审查告警规则
- ✅ 分析误报原因并调整
- ✅ 删除无用的规则
- ✅ 优化告警阈值
- ✅ 收集团队反馈

**DON'T**：
- ❌ 创建后不维护
- ❌ 不分析误报
- ❌ 保留无用规则
- ❌ 不调整阈值
- ❌ 不听取反馈

---

## 11. 常见问题

### 11.1 告警相关

**Q: 告警规则不触发？**

A: 检查以下几点：
- 查询语法是否正确
- 数据源是否有数据
- 阈值设置是否合理
- 评估间隔是否合适
- 持续时间是否过长

**Q: 告警频繁触发和恢复？**

A: 可能原因：
- 指标值在阈值附近波动
- 持续时间设置过短
- 阈值设置不合理

解决方案：
- 增加持续时间（如从1m改为5m）
- 调整阈值（增加缓冲区）
- 使用移动平均平滑指标

**Q: 告警延迟？**

A: 检查：
- 评估间隔设置（建议1m）
- Grafana服务器性能
- 数据源查询性能
- 网络延迟

### 11.2 通知相关

**Q: 没有收到通知？**

A: 排查步骤：
1. 检查Contact point配置
2. 测试通知渠道
3. 检查通知策略路由
4. 查看Grafana日志
5. 检查网络连接

**Q: 通知格式不正确？**

A: 检查：
- 消息模板语法
- 变量名称是否正确
- 数据格式是否匹配
- 通知渠道限制

**Q: 通知过多？**

A: 优化方案：
- 使用告警分组
- 增加重复间隔
- 使用告警抑制
- 调整阈值减少误报

### 11.3 Dashboard相关

**Q: 告警Dashboard显示不正确？**

A: 检查：
- 数据源配置
- 查询语法
- 时间范围设置
- 面板类型选择

**Q: 告警历史查询慢？**

A: 优化：
- 缩小时间范围
- 使用索引
- 增加Grafana资源
- 优化查询语句

---

## 12. 相关文档

- **告警系统架构**: `../../02-核心架构/05-监控层/04-告警系统架构.md`
- **监控系统架构**: `../../02-核心架构/05-监控层/01-监控系统架构.md`
- **日志查询指南**: `./05-日志查询和分析指南.md`
- **性能问题排查**: `./07-Grafana性能问题排查指南.md`
- **监控最佳实践**: `./01-监控和可观测性完整指南.md`

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
