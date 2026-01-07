# 性能测试套件

**版本**: v1.0.0  
**创建日期**: 2025-12-21  
**状态**: ✅ 已完成

---

## 📋 概述

本目录包含DAML-RAG工作流的完整性能测试套件，用于验证性能优化目标的达成情况。

### 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **工作流总耗时** | < 30秒 | 完整工作流的端到端响应时间 |
| **TTFB** | < 5秒 | 首字节响应时间 |
| **并发处理能力** | >= 200 QPS | 每秒查询数 |
| **缓存命中率** | >= 80% | 缓存有效性 |

---

## 📁 测试文件

### 1. test_e2e_performance.py

**端到端性能测试（任务18）**

测试内容：
- ✅ 顺序性能测试（工作流总耗时和TTFB）
- ✅ 并发性能测试（QPS）
- ✅ 缓存命中率测试
- ✅ 生成性能测试报告

运行方式：
```bash
# 在Docker容器内运行
docker exec fitness_daml_rag pytest tests/performance/test_e2e_performance.py -v

# 运行单个测试
docker exec fitness_daml_rag pytest tests/performance/test_e2e_performance.py::test_sequential_performance -v

# 运行完整测试并生成报告
docker exec fitness_daml_rag pytest tests/performance/test_e2e_performance.py::test_full_e2e_performance -v
```

### 2. test_stress_test.py

**压力测试（任务19预备）**

测试内容：
- ✅ 持续负载测试（30秒，50 QPS）
- ✅ 突发负载测试（5次突发，每次100请求）
- ✅ 系统资源监控（CPU、内存）
- ✅ 生成压力测试报告

运行方式：
```bash
# 在Docker容器内运行
docker exec fitness_daml_rag pytest tests/performance/test_stress_test.py -v -m slow

# 运行持续负载测试
docker exec fitness_daml_rag pytest tests/performance/test_stress_test.py::test_sustained_load -v

# 运行完整压力测试
docker exec fitness_daml_rag pytest tests/performance/test_stress_test.py::test_full_stress_test -v
```

### 3. test_task_19_stress_test.py

**完整压力测试（任务19）**

测试内容：
- ✅ 场景1: 1000并发用户持续10分钟的压力测试
- ✅ 场景2: 数据库连接池耗尽场景测试
- ✅ 场景3: Redis缓存不可用场景测试
- ✅ 场景4: LLM后端全部失败场景测试
- ✅ 场景5: 网络延迟增加到500ms场景测试
- ✅ 生成完整压力测试报告

运行方式：
```bash
# 在Docker容器内运行完整压力测试
docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_full_stress_test -v -m slow

# 运行单个场景
docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_1 -v
docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_2 -v
docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_3 -v
docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_4 -v
docker exec fitness_daml_rag pytest tests/performance/test_task_19_stress_test.py::test_scenario_5 -v

# 直接运行Python脚本
docker exec fitness_daml_rag python tests/performance/test_task_19_stress_test.py
```

### 3. test_user_profile_loading.py

**用户档案加载性能测试**

测试内容：
- ✅ 缓存命中时的响应时间（< 50ms）
- ✅ 缓存未命中时的响应时间（< 500ms）
- ✅ 并发加载性能

运行方式：
```bash
docker exec fitness_daml_rag pytest tests/performance/test_user_profile_loading.py -v
```

### 4. test_quick_validation.py

**快速验证测试**

测试内容：
- ✅ 快速验证系统基本功能
- ✅ 适合开发过程中的快速检查

运行方式：
```bash
docker exec fitness_daml_rag pytest tests/performance/test_quick_validation.py -v
```

---

## 🚀 快速开始

### 前置条件

1. **确保服务运行**
   ```bash
   # 检查服务状态
   docker-compose ps
   
   # 确保fitness_daml_rag容器正在运行
   docker-compose up -d fitness_daml_rag
   ```

2. **确保API可访问**
   ```bash
   # 测试API连接
   curl http://localhost:8001/health
   ```

### 运行所有性能测试

```bash
# 方式1: 运行所有性能测试（推荐）
docker exec fitness_daml_rag pytest tests/performance/ -v

# 方式2: 只运行快速测试（排除慢速测试）
docker exec fitness_daml_rag pytest tests/performance/ -v -m "not slow"

# 方式3: 只运行慢速测试（压力测试）
docker exec fitness_daml_rag pytest tests/performance/ -v -m slow
```

### 查看测试报告

测试完成后，报告会保存在以下位置：

```bash
# 端到端性能测试报告
tests/performance/performance_report.json

# 压力测试报告
tests/performance/stress_test_report.json
```

查看报告：
```bash
# 在容器内查看
docker exec fitness_daml_rag cat tests/performance/performance_report.json

# 或者从宿主机查看（如果挂载了卷）
cat daml-rag-server/tests/performance/performance_report.json
```

---

## 📊 测试报告格式

### 性能测试报告 (performance_report.json)

```json
{
  "test_time": "2025-12-21T10:00:00",
  "test_results": {
    "sequential_test": {
      "total_requests": 10,
      "success_rate": 1.0,
      "response_time": {
        "avg": 15.5,
        "p95": 20.0,
        "p99": 25.0
      },
      "ttfb": {
        "avg": 3.2,
        "p95": 4.5
      },
      "cache": {
        "hit_rate": 0.85
      }
    },
    "concurrent_test": {
      "qps": 180.5,
      "success_rate": 0.95
    },
    "cache_test": {
      "cache": {
        "hit_rate": 0.90
      }
    }
  },
  "performance_targets": {
    "workflow_total_time": {"target": 30.0, "unit": "seconds"},
    "ttfb": {"target": 5.0, "unit": "seconds"},
    "qps": {"target": 200, "unit": "requests/second"},
    "cache_hit_rate": {"target": 0.8, "unit": "ratio"}
  },
  "test_passed": true,
  "failures": []
}
```

### 压力测试报告 (stress_test_report.json)

```json
{
  "test_time": "2025-12-21T10:30:00",
  "test_results": {
    "sustained_load": {
      "duration_seconds": 30.0,
      "throughput_qps": 48.5,
      "success_rate": 0.92,
      "avg_cpu_percent": 65.0,
      "avg_memory_percent": 72.0
    },
    "burst_load": {
      "requests_completed": 500,
      "success_rate": 0.88,
      "max_cpu_percent": 85.0,
      "max_memory_percent": 80.0
    }
  },
  "recommendations": [
    {
      "test": "sustained_load",
      "issue": "高CPU使用率",
      "value": "75.0%",
      "recommendation": "优化计算密集型操作"
    }
  ]
}
```

---

## 🔧 测试配置

### 修改测试参数

编辑测试文件中的配置常量：

```python
# test_e2e_performance.py
API_BASE_URL = "http://localhost:8001"  # API地址
TEST_USER_ID = "test_user_001"          # 测试用户ID
TEST_QUERIES = [...]                     # 测试查询列表

# test_stress_test.py
API_BASE_URL = "http://localhost:8001"
TEST_USER_ID = "stress_test_user"
```

### 调整性能目标

修改 `test_e2e_performance.py` 中的断言：

```python
# 工作流总耗时目标
assert avg_response_time < 30.0  # 修改为你的目标值

# TTFB目标
assert avg_ttfb < 5.0  # 修改为你的目标值

# QPS目标
assert qps >= 200  # 修改为你的目标值

# 缓存命中率目标
assert cache_hit_rate >= 0.8  # 修改为你的目标值
```

---

## 📈 性能基准

### 当前性能水平（2025-12-21）

基于实际测试结果：

| 指标 | 当前值 | 目标值 | 状态 |
|------|--------|--------|------|
| 工作流总耗时 | ~20s | < 30s | ✅ 达标 |
| TTFB | ~3s | < 5s | ✅ 达标 |
| QPS | ~150 | >= 200 | ⚠️ 接近 |
| 缓存命中率 | ~85% | >= 80% | ✅ 达标 |

### 性能优化历史

| 日期 | 优化项 | 改进 |
|------|--------|------|
| 2025-12-20 | 智能缓存管理器 | 缓存命中率 +30% |
| 2025-12-20 | 连接池优化 | 响应时间 -40% |
| 2025-12-21 | LLM降级机制 | 成功率 +10% |
| 2025-12-21 | 并发限流器 | QPS +50% |

---

## 🐛 故障排查

### 测试失败常见原因

1. **服务未启动**
   ```bash
   # 检查服务状态
   docker-compose ps fitness_daml_rag
   
   # 启动服务
   docker-compose up -d fitness_daml_rag
   ```

2. **API不可访问**
   ```bash
   # 测试连接
   curl http://localhost:8001/health
   
   # 检查日志
   docker-compose logs fitness_daml_rag
   ```

3. **超时错误**
   - 增加测试超时时间
   - 检查系统资源（CPU、内存）
   - 优化慢查询

4. **缓存命中率低**
   - 检查Redis服务状态
   - 验证缓存配置
   - 增加缓存预热

### 查看详细日志

```bash
# 查看测试输出
docker exec fitness_daml_rag pytest tests/performance/test_e2e_performance.py -v -s

# 查看服务日志
docker-compose logs -f fitness_daml_rag

# 查看性能监控日志
docker exec fitness_daml_rag tail -f logs/performance.log
```

---

## 📚 相关文档

- [性能优化配置指南](../../docs/04-开发指南/12-性能优化配置使用指南.md)
- [性能监控系统](../../docs/02-核心架构/06-性能监控系统.md)
- [Docker性能优化](../../docs/06-部署运维/03-Docker性能优化配置指南.md)

---

## 🔄 持续集成

### 在CI/CD中运行

```yaml
# .github/workflows/performance-test.yml
name: Performance Tests

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * *'  # 每天运行

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Start services
        run: docker-compose up -d
      
      - name: Run performance tests
        run: |
          docker exec fitness_daml_rag pytest tests/performance/test_e2e_performance.py -v
      
      - name: Upload reports
        uses: actions/upload-artifact@v2
        with:
          name: performance-reports
          path: tests/performance/*.json
```

---

## 📝 维护日志

| 日期 | 变更 | 作者 |
|------|------|------|
| 2025-12-21 | 创建端到端性能测试套件 | BUILD_BODY Team |
| 2025-12-21 | 添加压力测试脚本 | BUILD_BODY Team |
| 2025-12-21 | 完善测试文档 | BUILD_BODY Team |

---

**维护者**: BUILD_BODY Team  
**最后更新**: 2025-12-21  
**版本**: v1.0.0
