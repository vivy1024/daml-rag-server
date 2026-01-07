# Grafana监控仪表板配置

**版本**: v1.3.0  
**创建日期**: 2025-12-16  
**最后更新**: 2025-12-23  
**状态**: ✅ 已完成

---

## 📊 概述

本目录包含DAML-RAG系统的Grafana监控仪表板配置，提供完整的性能监控和可视化。

## 📁 目录结构

```
config/grafana/
├── dashboards/
│   ├── daml-rag-performance.json                  # 通用性能监控仪表板
│   ├── streaming-output-performance.json          # 流式输出专用仪表板
│   └── workflow-performance-optimization.json     # 工作流性能优化仪表板
├── datasources/
│   ├── prometheus.yml                             # Prometheus数据源配置
│   └── loki.yml                                   # Loki数据源配置（新增）
├── alerts/
│   └── streaming-alerts.yml                       # 流式输出告警规则
├── logql-queries.json                             # LogQL查询模板库（JSON格式）
├── LOGQL_QUERY_TEMPLATES.md                       # LogQL查询模板库（Markdown格式）
└── README.md                                      # 本文件
```

## 🎯 仪表板功能

### 1. DAML-RAG Performance Dashboard

通用性能监控仪表板，包含以下监控面板：

#### 1. 请求性能
- **Request Duration (P95)**: 请求处理时间95分位数
- **Request Rate**: 每秒请求数
- **Average Response Time**: 平均响应时间

#### 2. 错误监控
- **Error Rate**: 错误率趋势
- **Error Count (1h)**: 最近1小时错误总数

#### 3. 缓存性能
- **Cache Hit Rate**: 缓存命中率

#### 4. 系统资源
- **CPU Usage**: CPU使用率
- **Memory Usage**: 内存使用量
- **Active Connections**: 活跃连接数

#### 5. 检索性能
- **Retrieval Duration by Layer**: 各层检索耗时
- **LLM Call Duration**: LLM调用耗时

#### 6. 系统状态
- **System Health Status**: 系统健康状态
- **Total Requests (24h)**: 24小时请求总数

### 2. Streaming Output Performance Dashboard

流式输出专用监控仪表板，包含以下监控面板：

#### 1. 核心指标（顶部统计卡片）
- **流式会话成功率**: 成功完成的流式会话占比（目标: ≥95%）
- **平均首字节响应时间 (TTFB)**: 首字节响应时间（目标: <2秒）
- **平均生成速度**: Token生成速度（目标: >10 tokens/s）
- **错误率**: 流式会话错误率（目标: <5%）

#### 2. 性能趋势
- **TTFB 趋势 (P50, P95, P99)**: 首字节响应时间分位数趋势
- **生成速度趋势**: 各用户的Token生成速度
- **总耗时分布 (P50, P95, P99)**: 流式会话总耗时分位数
- **内容长度分布**: 生成内容的字符数分布

#### 3. 会话统计
- **流式会话总数**: 总会话数、成功会话、失败会话
- **错误类型分布**: 各类错误的占比（饼图）
- **结构化数据生成统计**: 各类结构化数据的生成频率

#### 4. 稳定性监控
- **降级事件统计**: 降级事件和降级成功的趋势
- **重试次数统计**: 流式会话的重试频率
- **并发流式连接数**: 当前活跃的流式连接数

#### 5. 告警规则
- **成功率低于95%**: 5分钟内成功率持续低于95%触发告警
- **TTFB超过3秒**: P95 TTFB持续超过3秒触发告警
- **错误率超过5%**: 5分钟内错误率持续超过5%触发告警
- **降级率过高**: 降级率超过10%触发告警
- **生成速度过慢**: 平均生成速度低于5 tokens/s触发告警
- **并发连接数过高**: 活跃连接数超过100个触发告警
- **总耗时过长**: P95总耗时超过60秒触发告警
- **重试次数过多**: 每秒重试次数超过10次触发告警

### 3. Workflow Performance Optimization Dashboard

工作流性能优化专用监控仪表板，专注于性能瓶颈分析和优化效果验证：

#### 1. 核心性能指标（顶部统计卡片）
- **工作流成功率**: 工作流执行成功率（目标: ≥95%）
- **并发请求数**: 当前活跃的并发请求数（目标: <100）
- **性能瓶颈总数**: 超过阈值的性能瓶颈数量（目标: <10）
- **TTFB**: 首字节响应时间（目标: <5秒）

#### 2. 工作流性能趋势
- **工作流总耗时 (P50, P95, P99)**: 工作流总耗时分位数趋势（目标: P95<30秒）
- **步骤级别性能 (P95)**: 各步骤的P95耗时对比
  - 步骤1-用户档案加载（目标: <500ms）
  - 步骤3-会员权限检查（目标: <300ms）
  - 步骤4-BGE复杂度分类（目标: <500ms）
  - 步骤6.5-LLM选择DAG方案
  - 步骤7-DAG编排执行
  - 步骤8-三层检索
  - 步骤10-LLM深度分析

#### 3. 缓存性能监控
- **缓存命中率 (L1/L2/L3)**: 三层缓存的命中率趋势（目标: >80%）
- **缓存操作统计**: 缓存命中、未命中、淘汰的操作频率

#### 4. 连接池监控
- **连接池使用率 - MySQL**: MySQL连接池的活跃/空闲/最大连接数
- **连接池使用率 - Neo4j**: Neo4j连接池的活跃/空闲/最大连接数
- **连接池使用率 - HTTP**: HTTP连接池的活跃/空闲/最大连接数
- **连接池等待时间**: 各连接池的P95等待时间（目标: <2秒）
- **连接池健康检查失败率**: 连接池健康检查失败频率

#### 5. LLM调用监控
- **LLM调用成功率**: DeepSeek/Ollama/Template的成功率（目标: >99%）
- **LLM调用耗时 (P95)**: 各后端的P95调用耗时（目标: <30秒）
- **LLM降级事件统计**: 降级路径的触发频率
  - DeepSeek → Ollama
  - Ollama → Template
  - DeepSeek → Template
- **LLM Token使用统计**: Prompt/Completion/Total Token的使用趋势

#### 6. 并发控制监控
- **并发限流统计**: 活跃请求/队列请求/最大并发数
- **429错误率**: 并发超限导致的拒绝率（目标: <1%）
- **平均队列等待时间**: 请求在队列中的平均等待时间（目标: <5秒）

#### 7. 告警规则
- **工作流总耗时超过30秒**: P95总耗时持续超过30秒触发告警

## 🚀 部署步骤

### 1. 使用Docker Compose部署

在`docker-compose.yml`中添加Grafana和Prometheus服务：

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: fitness_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - fitness_network

  grafana:
    image: grafana/grafana:latest
    container_name: fitness_grafana
    ports:
      - "3001:3000"
    volumes:
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    depends_on:
      - prometheus
    networks:
      - fitness_network

volumes:
  prometheus_data:
  grafana_data:
```

### 2. 配置Prometheus

创建`config/prometheus/prometheus.yml`：

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'daml-rag'
    static_configs:
      - targets: ['fitness_daml_rag:8001']
    metrics_path: '/api/health/metrics/prometheus'
```

### 3. 配置告警规则

将告警规则添加到Prometheus配置中：

```yaml
# config/prometheus/prometheus.yml
rule_files:
  - '/etc/prometheus/alerts/*.yml'
```

在`docker-compose.yml`中挂载告警规则：

```yaml
prometheus:
  volumes:
    - ./config/grafana/alerts:/etc/prometheus/alerts
```

### 4. 启动服务

```bash
docker-compose up -d prometheus grafana
```

### 5. 访问Grafana

- URL: http://localhost:3001
- 默认用户名: admin
- 默认密码: admin

### 6. 导入仪表板

仪表板会自动通过provisioning加载，也可以手动导入：

1. 登录Grafana
2. 点击左侧菜单 "+" → "Import"
3. 上传JSON文件或粘贴JSON内容
4. 选择Prometheus数据源
5. 点击"Import"

## 📈 指标说明

### 通用指标

#### 延迟指标
- `request_duration_seconds`: 请求处理时间（秒）
- `retrieval_duration_seconds`: 检索耗时（秒）
- `llm_call_duration_seconds`: LLM调用耗时（秒）

#### 吞吐量指标
- `requests_total`: 请求总数
- `retrieval_requests_total`: 检索请求总数

#### 错误率指标
- `errors_total`: 错误总数
- `error_rate`: 错误率

#### 资源使用指标
- `cpu_usage_percent`: CPU使用率（%）
- `memory_usage_bytes`: 内存使用量（字节）
- `active_connections`: 活跃连接数

#### 业务指标
- `cache_hits_total`: 缓存命中总数
- `cache_misses_total`: 缓存未命中总数
- `cache_hit_rate`: 缓存命中率

### 流式输出专用指标

#### 性能指标
- `streaming_ttfb_seconds`: 首字节响应时间（TTFB）直方图
- `streaming_duration_seconds`: 流式会话总耗时直方图
- `streaming_tokens_generated_total`: 生成的Token总数
- `streaming_content_length`: 生成内容的字符数直方图

#### 质量指标
- `streaming_sessions_total`: 流式会话总数
- `streaming_sessions_success_total`: 成功的流式会话数
- `streaming_errors_total`: 流式错误总数（按error_type分类）
- `streaming_retry_count_total`: 重试次数总计

#### 降级指标
- `streaming_degradation_events_total`: 降级事件总数
- `streaming_degradation_fallback_success_total`: 降级成功（回退到非流式）的次数

#### 业务指标
- `streaming_structured_data_total`: 结构化数据生成总数（按data_type分类）
- `streaming_active_connections`: 当前活跃的流式连接数

### 工作流性能优化专用指标

#### 工作流指标
- `workflow_total_duration_seconds`: 工作流总耗时直方图
- `workflow_step_duration_seconds`: 各步骤耗时直方图
- `workflow_success_rate`: 工作流成功率
- `workflow_concurrent_requests`: 当前并发请求数
- `workflow_bottleneck_total`: 性能瓶颈总数

#### 缓存指标
- `cache_hits_total`: 缓存命中总数（按level分类：L1/L2/L3）
- `cache_misses_total`: 缓存未命中总数（按level分类）
- `cache_evictions_total`: 缓存淘汰总数（按cache_type分类）

#### 连接池指标
- `connection_pool_active`: 活跃连接数（按pool分类：mysql/neo4j/http）
- `connection_pool_idle`: 空闲连接数（按pool分类）
- `connection_pool_max_size`: 最大连接数（按pool分类）
- `connection_pool_wait_time_seconds`: 连接等待时间直方图
- `connection_pool_health_check_failures_total`: 健康检查失败总数

#### LLM指标
- `llm_call_success_total`: LLM调用成功总数（按backend分类：deepseek/ollama/template）
- `llm_call_failure_total`: LLM调用失败总数（按backend分类）
- `llm_call_duration_seconds`: LLM调用耗时直方图
- `llm_fallback_total`: LLM降级事件总数（按from/to分类）
- `llm_tokens_total`: Token使用总数（按type分类：prompt/completion/total）

#### 并发控制指标
- `concurrency_limiter_active_requests`: 活跃请求数
- `concurrency_limiter_queued_requests`: 队列中请求数
- `concurrency_limiter_max_concurrent`: 最大并发数
- `concurrency_limiter_queue_wait_time_seconds`: 队列等待时间
- `http_requests_total`: HTTP请求总数（按status分类，包括429）

## 🔧 自定义配置

### 修改仪表板

1. 在Grafana UI中编辑仪表板
2. 导出JSON配置
3. 替换`dashboards/daml-rag-performance.json`

### 添加新面板

在JSON配置中添加新的panel对象：

```json
{
  "id": 14,
  "title": "New Panel",
  "type": "graph",
  "gridPos": {
    "x": 0,
    "y": 36,
    "w": 12,
    "h": 8
  },
  "targets": [
    {
      "expr": "your_metric_query",
      "legendFormat": "{{label}}",
      "refId": "A"
    }
  ]
}
```

### 配置告警

在Grafana UI中为面板配置告警规则：

1. 编辑面板
2. 切换到"Alert"标签
3. 配置告警条件和通知渠道

## 📊 最佳实践

### 1. 监控关键指标

#### 通用指标阈值
- 响应时间P95 < 5秒
- 错误率 < 1%
- 缓存命中率 > 80%
- CPU使用率 < 80%
- 内存使用 < 8GB

#### 流式输出指标阈值
- 流式会话成功率 ≥ 95%
- TTFB (P95) < 2秒（警告）、< 3秒（严重）
- 生成速度 > 10 tokens/s
- 错误率 < 5%
- 降级率 < 10%
- 并发连接数 < 100个
- 总耗时 (P95) < 60秒

#### 工作流性能优化指标阈值
- 工作流总耗时 (P95) < 30秒
- 工作流成功率 ≥ 95%
- TTFB < 5秒
- 步骤1-用户档案加载 < 500ms
- 步骤3-会员权限检查 < 300ms
- 步骤4-BGE复杂度分类 < 500ms
- 缓存命中率 > 80%
- 连接池等待时间 (P95) < 2秒
- LLM调用成功率 > 99%
- LLM调用耗时 (P95) < 30秒
- 并发请求数 < 100
- 429错误率 < 1%
- 队列等待时间 < 5秒

### 2. 设置告警

#### 通用告警
- 响应时间超过阈值
- 错误率突然上升
- 缓存命中率下降
- 资源使用过高

#### 流式输出告警（已配置）
- ✅ 成功率低于95%（5分钟持续）
- ✅ TTFB超过3秒（5分钟持续）
- ✅ 错误率超过5%（5分钟持续）
- ✅ 降级率超过10%（5分钟持续）
- ✅ 生成速度低于5 tokens/s（5分钟持续）
- ✅ 并发连接数超过100个（2分钟持续）
- ✅ 总耗时超过60秒（5分钟持续）
- ✅ 重试次数过多（每秒>10次，5分钟持续）

#### 工作流性能优化告警（已配置）
- ✅ 工作流总耗时超过30秒（P95，5分钟持续）

### 3. 定期审查
- 每周查看性能趋势
- 识别性能瓶颈
- 优化慢查询
- 调整缓存策略
- 分析流式输出的TTFB和生成速度
- 检查降级事件的原因
- 优化结构化数据生成逻辑

### 4. 故障排查

#### TTFB过高
1. 检查步骤1-9的执行时间
2. 检查数据库查询性能
3. 检查MCP工具调用耗时
4. 检查网络延迟

#### 生成速度过慢
1. 检查DeepSeek API响应速度
2. 检查提示词长度
3. 检查max_tokens配置
4. 检查网络带宽

#### 降级率过高
1. 检查DeepSeek API稳定性
2. 检查网络连接质量
3. 检查超时配置
4. 检查错误日志

#### 错误率过高
1. 查看错误类型分布
2. 检查错误日志详情
3. 检查API配额和限流
4. 检查代码异常处理

## 🔗 相关文档

- [Prometheus文档](https://prometheus.io/docs/)
- [Grafana文档](https://grafana.com/docs/)
- [LogQL查询模板库](./LOGQL_QUERY_TEMPLATES.md)
- [性能优化指南](../../docs/04-开发指南/23-性能优化指南.md)
- [流式输出监控指标](../../src/framework/monitoring/streaming_metrics.py)
- [流式输出设计文档](../../../.kiro/specs/streaming-output-enhancement/design.md)

## 📝 变更日志

### v1.3.0 (2025-12-23)
- ✨ 新增LogQL查询模板库
- ✨ 创建logql-queries.json（JSON格式）
- ✨ 创建LOGQL_QUERY_TEMPLATES.md（Markdown格式）
- 📚 提供60+个常用LogQL查询示例
  - 请求追踪查询（5个）
  - 错误日志查询（9个）
  - 慢请求查询（9个）
  - 步骤日志查询（10个）
  - 高级查询（8个）
  - 业务查询（5个）
- 📚 添加使用技巧和实战案例

### v1.2.0 (2025-12-21)
- ✨ 新增工作流性能优化专用监控仪表板
- ✨ 新增20个性能监控面板
  - 工作流总耗时和步骤级别性能
  - 三层缓存命中率监控
  - MySQL/Neo4j/HTTP连接池使用率
  - LLM调用成功率和降级统计
  - 并发限流和队列监控
- ✨ 新增工作流总耗时超过30秒的告警规则
- 📚 完善文档，添加工作流性能优化指标说明

### v1.1.0 (2025-12-19)
- ✨ 新增流式输出专用监控仪表板
- ✨ 新增8条流式输出告警规则
- 📚 完善文档，添加流式输出指标说明
- 📚 添加故障排查指南

### v1.0.0 (2025-12-16)
- 🎉 初始版本
- ✨ 创建通用性能监控仪表板
- 📚 创建配置文档

---

**维护者**: 薛小川  
**最后更新**: 2025-12-23
