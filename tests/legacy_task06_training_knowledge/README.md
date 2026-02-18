# 任务6：训练知识导入测试 🧪

**任务目标**: 测试训练知识数据的导入、验证和管理功能

**测试文件数量**: 3个

## 📋 测试文件

### 核心测试
- `test_training_knowledge_supplementers.py` - 训练知识补充器测试
- `test_training_knowledge_validator.py` - 训练知识验证器测试
- `test_training_cycle_calculation.py` - 训练周期计算测试

## 🚀 运行方式

```bash
# 运行所有任务6测试
docker exec fitness_daml_rag pytest tests/任务6-训练知识导入/ -v

# 运行单个测试
docker exec fitness_daml_rag pytest tests/任务6-训练知识导入/test_training_knowledge_supplementers.py -v
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
