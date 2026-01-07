# 测试环境说明

## 测试环境准备

### 快速开始

运行以下命令准备测试环境：

**Windows:**
```bash
cd daml-rag-server/scripts
.\prepare_test_environment.bat
```

**Linux/Mac:**
```bash
cd daml-rag-server/scripts
./prepare_test_environment.sh
```

### 准备步骤

测试环境准备脚本会自动执行以下步骤：

1. **验证Docker容器运行状态**
   - fitness_daml_rag
   - fitness_prometheus
   - fitness_grafana

2. **清理测试数据和历史记录**
   - 清理Redis缓存中的测试数据
   - 清理MySQL中的测试会话
   - 准备重置Prometheus指标

3. **验证测试环境配置**
   - Redis连接
   - MySQL连接
   - DAML-RAG API
   - Prometheus API
   - Grafana API
   - 测试数据文件

### 测试数据

测试查询数据位于：`tests/test_data/streaming_test_queries.json`

包含三类测试查询：
- **简单查询**: 你好、谢谢、再见
- **中等查询**: 介绍深蹲动作、如何增肌、营养建议
- **复杂查询**: 设计训练计划、分析进度、制定方案

### 测试用户

- `test_user_1`: 初学者用户
- `test_user_2`: 中级用户
- `test_user_3`: 高级用户
- `load_test_user`: 压力测试用户模板

### 性能目标

- TTFB < 5秒
- 生成速度 > 15 tokens/s
- 总耗时 < 30秒
- 并发成功率 > 90%

## 手动清理

如需手动清理测试数据：

```bash
docker exec fitness_daml_rag python scripts/cleanup_test_data.py
```

## 手动验证

如需手动验证测试环境：

```bash
docker exec fitness_daml_rag python scripts/verify_test_environment.py
```

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
