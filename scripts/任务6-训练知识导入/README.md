# 任务6：训练知识导入 📚

**任务目标**: 实现训练知识数据导入、验证和管理

**脚本数量**: 14个

## 📋 核心脚本

### 导入脚本
- `import_training_knowledge.py` - 训练知识导入主脚本
  - 支持6种训练知识类型导入
  - 支持模拟导入模式（--dry-run）
  - 支持JSON格式报告输出（--output-json）

### 验证脚本
- `verify_strength_standards.py` - 验证力量标准
- `verify_training_knowledge_supplementers.py` - 验证训练知识补充器
- `verify_training_volume.py` - 验证训练量
- `verify_workout_programs.py` - 验证训练计划

### 检查脚本
- `check_knowledge_coverage.py` - 检查知识覆盖率
- `check_exercise_id_field.py` - 检查Exercise节点ID字段
- `check_exercise_names.py` - 检查动作名称
- `check_muscle_names.py` - 检查肌肉名称
- `check_neo4j_knowledge_simple.py` - 简单检查Neo4j知识

### 测试脚本
- `test_training_knowledge_import.py` - 训练知识导入测试
- `test_validator.py` - 验证器测试
- `test_validator_simple.py` - 简单验证器测试

## 🚀 运行方式

```bash
# 导入所有训练知识
docker exec fitness_daml_rag python scripts/任务6-训练知识导入/import_training_knowledge.py --data-type all

# 验证训练知识
docker exec fitness_daml_rag python scripts/任务6-训练知识导入/verify_training_knowledge_supplementers.py

# 检查知识覆盖率
docker exec fitness_daml_rag python scripts/任务6-训练知识导入/check_knowledge_coverage.py
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
