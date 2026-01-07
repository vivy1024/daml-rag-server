# Grafana 流式输出监控部署指南

**版本**: v1.1.0  
**创建日期**: 2025-12-19  
**最后更新**: 2025-12-19  
**状态**: ✅ 已部署

---

## 📋 概述

本指南说明如何部署流式输出监控仪表板和告警规则。

## ✅ 部署状态

**任务 5.3 已完成部署！**

所有监控服务已成功启动并运行：

1. ✅ 在 `docker-compose.yml` 中添加了 Prometheus 和 Grafana 服务
2. ✅ 创建了 Prometheus 配置文件
3. ✅ 创建了 Grafana 数据源配置
4. ✅ 启动了 Docker 容器
5. ✅ 验证了服务健康状态

## 🎯 已完成的工作

✅ 创建了流式输出专用 Grafana 仪表板配置
✅ 创建了 8 条告警规则配置
✅ 更新了 Grafana 配置文档
✅ 创建了仪表板自动加载配置
✅ 部署了 Prometheus 和 Grafana 服务
✅ 配置了数据源和抓取规则

## 📁 创建的文件

```
config/grafana/
├── dashboards/
│   ├── streaming-output-performance.json  # 流式输出仪表板（新增）
│   └── dashboards.yml                     # 自动加载配置（新增）
├── alerts/
│   └── streaming-alerts.yml               # 告警规则（新增）
└── README.md                              # 更新文档
```

## 🎉 部署完成

### 当前运行状态

```bash
# 查看服务状态
docker-compose ps prometheus grafana

# 输出示例：
# NAME                 STATUS                   PORTS
# fitness_prometheus   Up (healthy)             0.0.0.0:9090->9090/tcp
# fitness_grafana      Up (healthy)             0.0.0.0:3001->3000/tcp
```

### 访问监控服务

1. **Prometheus**: http://localhost:9090
   - 查看指标采集状态
   - 查看告警规则
   - 执行 PromQL 查询

2. **Grafana**: http://localhost:3001
   - 默认用户名: `admin`
   - 默认密码: `admin`
   - 首次登录后会要求修改密码

### 查看仪表板

1. 登录 Grafana
2. 点击左侧菜单 "Dashboards"
3. 进入 "DAML-RAG" 文件夹
4. 选择仪表板：
   - **DAML-RAG Performance Dashboard** - 通用性能监控
   - **Streaming Output Performance** - 流式输出专用监控
   - **Workflow Performance Optimization** - 工作流性能优化监控（新增）

## 🚀 部署步骤（已完成）

### 步骤 1: 更新 docker-compose.yml ✅

已在 `docker-compose.yml` 中添加 Prometheus 和 Grafana 服务：

```yaml
services:
  # ... 现有服务 ...

  prometheus:
    image: prom/prometheus:latest
    container_name: fitness_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./daml-rag-server/config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./daml-rag-server/config/grafana/alerts:/etc/prometheus/alerts
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
      - ./daml-rag-server/config/grafana/datasources:/etc/grafana/provisioning/datasources
      - ./daml-rag-server/config/grafana/dashboards:/etc/grafana/provisioning/dashboards
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

### 步骤 2: 创建 Prometheus 配置 ✅

已创建 `daml-rag-server/config/prometheus/prometheus.yml`：

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

rule_files:
  - '/etc/prometheus/alerts/*.yml'

scrape_configs:
  - job_name: 'daml-rag'
    static_configs:
      - targets: ['fitness_daml_rag:8001']
    metrics_path: '/api/health/metrics/prometheus'
```

### 步骤 3: 在应用中暴露 Prometheus 指标 ✅

Prometheus 指标端点已存在于 `daml-rag-server/src/api/routes/health.py`：

```python
@router.get("/metrics/prometheus")
async def prometheus_metrics():
    """Prometheus 指标端点"""
    from fastapi.responses import PlainTextResponse
    
    try:
        prometheus_text = metrics_collector.export_prometheus()
        return PlainTextResponse(content=prometheus_text)
    except Exception as e:
        structured_logger.error(
            "Prometheus指标导出失败",
            error=str(e),
            component="metrics"
        )
        return PlainTextResponse(
            content=f"# Error exporting metrics: {str(e)}",
            status_code=500
        )
```

### 步骤 4: 启动服务 ✅

已成功启动 Prometheus 和 Grafana：

```bash
# 启动命令（已执行）
docker-compose up -d prometheus grafana

# 查看服务状态
docker-compose ps prometheus grafana

# 查看日志
docker-compose logs -f prometheus grafana
```

### 步骤 5: 访问 Grafana ✅

Grafana 已成功启动并可访问：

1. 打开浏览器访问: http://localhost:3001
2. 使用默认凭据登录:
   - 用户名: `admin`
   - 密码: `admin`
3. 首次登录后会要求修改密码
4. 仪表板已自动加载到 "DAML-RAG" 文件夹中

### 步骤 6: 验证监控

验证步骤：

1. 在 Grafana 中打开 "Streaming Output Performance" 仪表板
2. 发送一些流式请求测试
3. 观察指标是否正常显示
4. 检查告警规则是否正常工作

**注意**: 由于刚部署，可能需要等待一些流式请求产生数据后才能看到图表。

## 📊 仪表板功能

### 核心指标
- 流式会话成功率（目标: ≥95%）
- 平均 TTFB（目标: <2秒）
- 平均生成速度（目标: >10 tokens/s）
- 错误率（目标: <5%）

### 告警规则
1. 成功率低于 95%
2. TTFB 超过 3 秒
3. 错误率超过 5%
4. 降级率超过 10%
5. 生成速度低于 5 tokens/s
6. 并发连接数超过 100 个
7. 总耗时超过 60 秒
8. 重试次数过多

## 🔧 故障排查

### Prometheus 无法抓取指标
- 检查 `fitness_daml_rag` 容器是否运行
- 检查 `/api/health/metrics/prometheus` 端点是否可访问
- 检查网络配置是否正确

### Grafana 无法连接 Prometheus
- 检查 Prometheus 数据源配置
- 检查 Prometheus 服务是否运行
- 检查网络连接

### 仪表板无数据
- 检查 Prometheus 是否成功抓取指标
- 检查时间范围设置
- 检查查询表达式是否正确

## 📝 注意事项

1. **可选任务**: 此任务在任务列表中标记为可选（`- [-]`），主要用于生产环境监控
2. **开发环境**: 开发环境可以跳过此步骤，使用日志进行调试
3. **生产环境**: 生产环境强烈建议部署完整的监控系统
4. **资源消耗**: Prometheus 和 Grafana 会占用额外的系统资源

## 🔗 相关文档

- [Grafana 配置文档](./README.md)
- [流式输出设计文档](../../../.kiro/specs/streaming-output-enhancement/design.md)
- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)

---

**维护者**: 薛小川  
**创建日期**: 2025-12-19
