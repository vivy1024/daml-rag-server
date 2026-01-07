# 数据质量增强 📊

**任务目标**: Neo4j数据库增强、数据质量检查、Ollama集成测试

**脚本数量**: 40+个

## 📋 核心分类

### Ollama集成测试（6个）
- `test_ollama_qwen3.py` - Ollama Qwen3完整测试
- `test_ollama_quick.py` - Ollama快速测试
- `test_ollama_integration.py` - Ollama集成测试

### 数据质量检查（15个）
- `check_data_file_sync.py` - 检查数据文件同步
- `check_exercise_data.py` - 检查Exercise数据
- `check_food_fields.py` - 检查食物字段
- `check_missing_zh.py` - 检查缺失中文
- `check_translation_quality.py` - 检查翻译质量
- `check_professional_desc_quality.py` - 检查专业描述质量
- `check_injury_types.py` - 检查损伤类型
- `check_food_carbs.py` - 检查食物碳水化合物

### 数据清理（8个）
- `clean_exercise_data.py` - 清理Exercise数据
- `cleanup_exercise_descriptions.py` - 清理动作描述
- `fix_incomplete_translations.py` - 修复不完整翻译
- `compare_data_versions.py` - 比较数据版本
- `compare_steps_count.py` - 比较步骤数量
- `estimate_cleanup_time.py` - 估算清理时间

### 数据补充（6个）
- `exercise_supplementer.py` - Exercise数据补充
- `injury_type_supplementer.py` - 损伤类型补充
- `rehabilitation_phase_creator.py` - 康复阶段创建器
- `acsm_standard_supplementer.py` - ACSM标准补充器
- `nsca_standard_supplementer.py` - NSCA标准补充器
- `training_knowledge_supplementer.py` - 训练知识补充器

## 🚀 运行方式

```bash
# Ollama测试
docker exec fitness_daml_rag python scripts/数据质量增强/test_ollama_qwen3.py

# 数据验证
docker exec fitness_daml_rag python scripts/数据质量增强/run_complete_validation.py

# 数据补充
docker exec fitness_daml_rag python scripts/数据质量增强/exercise_supplementer.py
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
