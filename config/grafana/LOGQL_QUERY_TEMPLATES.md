# LogQL查询模板库

**版本**: v1.0.0  
**创建日期**: 2025-12-23  
**状态**: ✅ 已完成

---

## 概述

本文档提供DAML-RAG系统的LogQL查询模板库，涵盖请求追踪、错误分析、性能监控、工作流分析等常见场景。

### 使用方法

1. 在Grafana中打开Explore界面
2. 选择Loki数据源
3. 复制相应的LogQL查询语句
4. 将`$variable_name`替换为实际值
5. 选择合适的时间范围
6. 点击"Run query"执行查询

---

## 1. 请求追踪查询

### 1.1 查询特定request_id的所有日志

**用途**: 追踪单个请求的完整执行链路

```logql
{job="daml-rag"} | json | request_id="$request_id"
```

**示例**:
```logql
{job="daml-rag"} | json | request_id="req_20251223_001"
```

**变量说明**:
- `$request_id`: 请求ID，例如：req_abc123

---

### 1.2 查询特定trace_id的所有日志

**用途**: 追踪分布式请求的完整链路

```logql
{job="daml-rag"} | json | trace_id="$trace_id"
```

**示例**:
```logql
{job="daml-rag"} | json | trace_id="550e8400-e29b-41d4-a716-446655440000"
```

**变量说明**:
- `$trace_id`: 追踪ID（UUID格式）

---

### 1.3 查询特定用户的所有请求

**用途**: 查看特定用户的所有请求历史

```logql
{job="daml-rag"} | json | user_id="$user_id"
```

**示例**:
```logql
{job="daml-rag"} | json | user_id="user_001"
```

**变量说明**:
- `$user_id`: 用户ID

---

### 1.4 查询特定用户的失败请求

**用途**: 排查特定用户遇到的错误

```logql
{job="daml-rag"} | json | user_id="$user_id" | level="ERROR"
```

**示例**:
```logql
{job="daml-rag"} | json | user_id="user_001" | level="ERROR"
```

---

### 1.5 查询请求的完整时间线

**用途**: 以时间线格式查看请求的执行过程

```logql
{job="daml-rag"} | json | request_id="$request_id" | line_format "{{.timestamp}} [{{.level}}] {{.step}} - {{.message}}"
```

**示例**:
```logql
{job="daml-rag"} | json | request_id="req_20251223_001" | line_format "{{.timestamp}} [{{.level}}] {{.step}} - {{.message}}"
```

---

## 2. 错误日志查询

### 2.1 查询所有ERROR日志

**用途**: 查看系统中所有错误日志

```logql
{job="daml-rag"} | json | level="ERROR"
```

---

### 2.2 查询所有CRITICAL日志

**用途**: 查看系统中所有严重错误

```logql
{job="daml-rag"} | json | level="CRITICAL"
```

---

### 2.3 查询特定类型的错误

**用途**: 查询特定类型的错误，便于分类处理

```logql
{job="daml-rag"} | json | level="ERROR" | error_type="$error_type"
```

**示例**:
```logql
{job="daml-rag"} | json | level="ERROR" | error_type="Neo4jError"
```

**常见错误类型**:
- `Neo4jError`: Neo4j数据库错误
- `LLMError`: LLM调用错误
- `ValidationError`: 数据验证错误
- `TimeoutError`: 超时错误
- `ConnectionError`: 连接错误

---

### 2.4 查询Neo4j相关错误

**用途**: 排查Neo4j数据库相关问题

```logql
{job="daml-rag"} | json | level="ERROR" |= "Neo4j"
```

---

### 2.5 查询LLM调用错误

**用途**: 排查LLM调用相关问题

```logql
{job="daml-rag"} | json | level="ERROR" |= "LLM"
```

---

### 2.6 查询MCP工具调用错误

**用途**: 排查MCP工具调用问题

```logql
{job="daml-rag"} | json | level="ERROR" |= "MCP"
```

---

### 2.7 统计每分钟错误数

**用途**: 监控错误发生频率

```logql
sum(rate({job="daml-rag"} | json | level="ERROR" [1m]))
```

---

### 2.8 按错误类型统计

**用途**: 分析错误类型分布

```logql
sum by (error_type) (rate({job="daml-rag"} | json | level="ERROR" [5m]))
```

---

### 2.9 查询最近1小时的错误趋势

**用途**: 查看错误趋势，判断系统稳定性

```logql
sum(count_over_time({job="daml-rag"} | json | level="ERROR" [1h]))
```

---

## 3. 慢请求查询

### 3.1 查询总耗时超过3秒的请求

**用途**: 查找响应慢的请求

```logql
{job="daml-rag"} | json | total_duration_ms > 3000
```

---

### 3.2 查询总耗时超过5秒的请求

**用途**: 查找严重超时的请求

```logql
{job="daml-rag"} | json | total_duration_ms > 5000
```

---

### 3.3 查询TTFB超过2秒的请求

**用途**: 查找首字节响应慢的请求

```logql
{job="daml-rag"} | json | ttfb_ms > 2000
```

---

### 3.4 查询特定步骤耗时超过阈值

**用途**: 定位性能瓶颈步骤

```logql
{job="daml-rag"} | json | step="$step" | duration_ms > $threshold
```

**示例**:
```logql
{job="daml-rag"} | json | step="步骤7-DAG编排器" | duration_ms > 1000
```

**变量说明**:
- `$step`: 步骤名称
- `$threshold`: 耗时阈值（毫秒）

---

### 3.5 查询LLM调用耗时超过10秒

**用途**: 排查LLM调用性能问题

```logql
{job="daml-rag"} | json |= "LLM" | duration_ms > 10000
```

---

### 3.6 查询数据库查询耗时超过1秒

**用途**: 排查数据库查询性能问题

```logql
{job="daml-rag"} | json |= "Neo4j" | duration_ms > 1000
```

---

### 3.7 统计慢请求数量（每5分钟）

**用途**: 监控慢请求发生频率

```logql
sum(count_over_time({job="daml-rag"} | json | total_duration_ms > 3000 [5m]))
```

---

### 3.8 计算平均响应时间

**用途**: 监控系统平均性能

```logql
avg(rate({job="daml-rag"} | json | unwrap total_duration_ms [5m]))
```

---

### 3.9 查询P95响应时间

**用途**: 监控95%请求的响应时间

```logql
quantile_over_time(0.95, {job="daml-rag"} | json | unwrap total_duration_ms [5m])
```

---

## 4. 步骤日志查询

### 4.1 查询特定步骤的所有日志

**用途**: 查看特定步骤的执行情况

```logql
{job="daml-rag"} | json | step="$step"
```

**示例**:
```logql
{job="daml-rag"} | json | step="步骤7-DAG编排器"
```

**常用步骤名称**:
- `步骤1-预加载用户档案`
- `步骤2-会话记录存储`
- `步骤3-检查会员权限`
- `步骤4-BGE复杂度分类`
- `步骤5-智能模型选择`
- `步骤6-Few-Shot检索`
- `步骤6.5-LLM选择DAG方案`
- `步骤7-DAG编排器`
- `步骤8-三层检索`
- `步骤9-工具结果汇总`
- `步骤10-LLM深度分析`
- `步骤11-记录交互`

---

### 4.2 查询步骤1-预加载用户档案

**用途**: 查看用户档案加载情况

```logql
{job="daml-rag"} | json | step="步骤1-预加载用户档案"
```

---

### 4.3 查询步骤4-BGE复杂度分类

**用途**: 查看复杂度分类结果

```logql
{job="daml-rag"} | json | step="步骤4-BGE复杂度分类"
```

---

### 4.4 查询步骤6.5-LLM选择DAG方案

**用途**: 查看DAG方案选择过程

```logql
{job="daml-rag"} | json | step="步骤6.5-LLM选择DAG方案"
```

---

### 4.5 查询步骤7-DAG编排器

**用途**: 查看DAG编排执行情况

```logql
{job="daml-rag"} | json | step="步骤7-DAG编排器"
```

---

### 4.6 查询步骤8-三层检索

**用途**: 查看检索执行情况

```logql
{job="daml-rag"} | json | step="步骤8-三层检索"
```

---

### 4.7 查询步骤10-LLM深度分析

**用途**: 查看LLM分析过程

```logql
{job="daml-rag"} | json | step="步骤10-LLM深度分析"
```

---

### 4.8 统计各步骤执行次数

**用途**: 分析各步骤的执行频率

```logql
sum by (step) (count_over_time({job="daml-rag"} | json | step!="" [5m]))
```

---

### 4.9 统计各步骤平均耗时

**用途**: 分析各步骤的性能表现

```logql
avg by (step) (rate({job="daml-rag"} | json | step!="" | unwrap duration_ms [5m]))
```

---

### 4.10 查询步骤执行失败的日志

**用途**: 排查特定步骤的失败原因

```logql
{job="daml-rag"} | json | step="$step" | level="ERROR"
```

**示例**:
```logql
{job="daml-rag"} | json | step="步骤7-DAG编排器" | level="ERROR"
```

---

## 5. 高级查询

### 5.1 查询请求的完整执行链路（格式化）

**用途**: 以可读格式查看请求的完整执行过程

```logql
{job="daml-rag"} | json | request_id="$request_id" | line_format "[{{.timestamp}}] {{.step}} ({{.duration_ms}}ms) - {{.message}}"
```

**示例**:
```logql
{job="daml-rag"} | json | request_id="req_20251223_001" | line_format "[{{.timestamp}}] {{.step}} ({{.duration_ms}}ms) - {{.message}}"
```

---

### 5.2 查询特定时间段的错误日志

**用途**: 分析特定时间段的错误情况

```logql
{job="daml-rag"} | json | level="ERROR" | timestamp >= "$start_time" | timestamp <= "$end_time"
```

**示例**:
```logql
{job="daml-rag"} | json | level="ERROR" | timestamp >= "2025-12-23 10:00:00" | timestamp <= "2025-12-23 11:00:00"
```

---

### 5.3 查询包含特定关键词的日志

**用途**: 搜索包含特定关键词的日志

```logql
{job="daml-rag"} | json |= "$keyword"
```

**示例**:
```logql
{job="daml-rag"} | json |= "timeout"
```

**常用关键词**:
- `timeout`: 超时相关
- `connection`: 连接相关
- `cache`: 缓存相关
- `retry`: 重试相关
- `fallback`: 降级相关

---

### 5.4 查询多个条件组合

**用途**: 精确定位特定用户在特定步骤的错误

```logql
{job="daml-rag"} | json | user_id="$user_id" | level="ERROR" | step="$step"
```

**示例**:
```logql
{job="daml-rag"} | json | user_id="user_001" | level="ERROR" | step="步骤7-DAG编排器"
```

---

### 5.5 统计日志级别分布

**用途**: 分析日志级别分布，了解系统健康状况

```logql
sum by (level) (count_over_time({job="daml-rag"} | json [5m]))
```

---

### 5.6 查询缓存命中情况

**用途**: 分析缓存命中率

```logql
{job="daml-rag"} | json |= "cache" | json | cache_hit="true"
```

---

### 5.7 查询降级事件

**用途**: 监控系统降级情况

```logql
{job="daml-rag"} | json |= "降级" | json | fallback="true"
```

---

### 5.8 查询重试事件

**用途**: 分析重试频率和原因

```logql
{job="daml-rag"} | json |= "重试" | json | retry_count > 0
```

---

## 6. 业务查询

### 6.1 查询训练计划生成日志

**用途**: 查看训练计划生成情况

```logql
{job="daml-rag"} | json |= "训练计划"
```

---

### 6.2 查询动作推荐日志

**用途**: 查看动作推荐情况

```logql
{job="daml-rag"} | json |= "动作推荐"
```

---

### 6.3 查询营养建议日志

**用途**: 查看营养建议生成情况

```logql
{job="daml-rag"} | json |= "营养建议"
```

---

### 6.4 查询用户档案更新日志

**用途**: 查看用户档案更新情况

```logql
{job="daml-rag"} | json |= "用户档案" |= "更新"
```

---

### 6.5 统计各业务功能使用频率

**用途**: 分析各业务功能的使用情况

```logql
sum by (function_name) (count_over_time({job="daml-rag"} | json | function_name!="" [1h]))
```

---

## 7. 常用模式

### 7.1 标签过滤

```logql
{job="daml-rag", level="ERROR"}
```

### 7.2 文本搜索

```logql
{job="daml-rag"} |= "keyword"
```

### 7.3 JSON解析

```logql
{job="daml-rag"} | json | field="value"
```

### 7.4 数值过滤

```logql
{job="daml-rag"} | json | duration_ms > 1000
```

### 7.5 聚合查询

```logql
sum(rate({job="daml-rag"} [5m]))
```

### 7.6 格式化输出

```logql
{job="daml-rag"} | json | line_format "{{.field1}} - {{.field2}}"
```

---

## 8. 使用技巧

### 8.1 提高查询性能

✅ **使用标签过滤**
```logql
# 好的做法：使用标签
{job="daml-rag", level="error"}

# 不好的做法：文本搜索
{job="daml-rag"} |= "ERROR"
```

✅ **限制时间范围**
```logql
# 好的做法：限制时间范围
{job="daml-rag"} [1h] |= "ERROR"

# 不好的做法：查询所有历史
{job="daml-rag"} |= "ERROR"
```

✅ **使用聚合查询**
```logql
# 好的做法：聚合后再查询
sum by (level) (rate({job="daml-rag"} [5m]))

# 不好的做法：查询原始日志再聚合
{job="daml-rag"} | json
```

### 8.2 保存常用查询

1. 在Grafana中创建Dashboard
2. 添加查询面板
3. 保存为可复用的面板
4. 使用变量实现动态查询

### 8.3 配置告警

1. 基于查询结果配置告警规则
2. 设置合理的阈值
3. 配置通知渠道（钉钉、邮件等）
4. 避免告警疲劳

---

## 9. 实战案例

### 案例1：追踪用户请求失败

**场景**: 用户user_001报告查询失败

**步骤1**: 查找用户最近的请求
```logql
{job="daml-rag"} | json | user_id="user_001" | line_format "{{.timestamp}} {{.message}}"
```

**步骤2**: 找到失败的request_id（在日志列表中找到包含"ERROR"的日志）

**步骤3**: 追踪完整请求链路
```logql
{job="daml-rag"} | json | request_id="req_123456"
```

**步骤4**: 分析错误原因（查看日志中的error_type和error_message字段）

---

### 案例2：分析系统性能下降

**场景**: 系统响应变慢，需要找出原因

**步骤1**: 查看耗时趋势
```logql
quantile_over_time(0.95, {job="daml-rag"} | json | unwrap total_duration_ms [5m])
```

**步骤2**: 找出慢步骤
```logql
avg by (step) (rate({job="daml-rag"} | json | step!="" | unwrap duration_ms [5m]))
```

**步骤3**: 查看慢查询日志
```logql
{job="daml-rag"} | json | duration_ms > 1000
```

**步骤4**: 分析根因（查看慢查询的详细信息）

---

### 案例3：监控错误率突增

**场景**: 错误率突然上升，需要快速定位

**步骤1**: 查看错误趋势
```logql
sum(rate({job="daml-rag"} | json | level="ERROR" [1m]))
```

**步骤2**: 分析错误类型分布
```logql
sum by (error_type) (rate({job="daml-rag"} | json | level="ERROR" [5m]))
```

**步骤3**: 查看具体错误日志
```logql
{job="daml-rag"} | json | level="ERROR" | error_type="Neo4jError"
```

**步骤4**: 定位问题并修复

---

## 10. 相关文档

- **Grafana日志查询和分析指南**: `docs/04-开发指南/04-最佳实践/05-Grafana日志查询和分析指南.md`
- **监控系统架构**: `docs/02-核心架构/05-监控层/01-监控系统架构.md`
- **日志系统架构**: `docs/02-核心架构/05-监控层/03-日志系统架构.md`
- **Loki配置**: `config/loki/loki-config.yml`
- **Promtail配置**: `config/promtail/promtail-config.yml`

---

**维护者**: 薛小川  
**创建日期**: 2025-12-23  
**版本**: v1.0.0

