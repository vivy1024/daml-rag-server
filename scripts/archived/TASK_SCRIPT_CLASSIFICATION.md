# 脚本任务分类表

**版本**: v1.0.0
**更新日期**: 2025-12-20
**维护者**: 薛小川

---

## 📋 任务分类总览

| 任务编号 | 任务名称 | 脚本数量 | 主要脚本 |
|---------|---------|---------|---------|
| **任务6** | 训练知识导入 | 15个 | import_training_knowledge.py, verify_*.py |
| **任务8** | 增强日志系统 | 3个 | demo_config_manager.py, validate_llm_config.py |
| **任务10** | 性能优化和监控 | 5个 | performance/*.py, test_monitoring.py |
| **MCP工具** | MCP工具测试 | 26个 | tests/*.py, validate_all_mcp_tools.py |
| **Neo4j** | 数据库操作 | 17个 | neo4j/*.py |
| **数据补充** | 数据质量增强 | 40个 | data_supplement/*.py |
| **数据导入** | 数据导入向量化 | 6个 | data_import/*.py |
| **验证脚本** | 系统验证 | 9个 | validation/*.py |

---

## 🎯 详细任务分类

### 任务6：训练知识导入 📚

**任务目标**: 实现训练知识数据导入、验证和管理

**核心脚本**:
- `import_training_knowledge.py` - 训练知识导入主脚本
  - 支持6种训练知识类型导入（training_volume, strength_standards, workout_programs, acsm_standards, nsca_standards）
  - 支持模拟导入模式（--dry-run）
  - 支持JSON格式报告输出（--output-json）
  - 实现进度跟踪器

**验证脚本**:
- `verify_strength_standards.py` - 验证力量标准
- `verify_training_knowledge_supplementers.py` - 验证训练知识补充器
- `verify_training_volume.py` - 验证训练量
- `verify_workout_programs.py` - 验证训练计划

**检查脚本**:
- `check_knowledge_coverage.py` - 检查知识覆盖率
- `check_exercise_id_field.py` - 检查Exercise节点ID字段
- `check_exercise_names.py` - 检查动作名称
- `check_muscle_names.py` - 检查肌肉名称
- `check_neo4j_knowledge_simple.py` - 简单检查Neo4j知识

**测试脚本**:
- `test_training_knowledge_import.py` - 训练知识导入测试
- `test_validator.py` - 验证器测试
- `test_validator_simple.py` - 简单验证器测试

**运行方式**:
```bash
# 导入所有训练知识
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type all

# 验证训练知识
docker exec fitness_daml_rag python scripts/verify_training_knowledge_supplementers.py

# 检查知识覆盖率
docker exec fitness_daml_rag python scripts/check_knowledge_coverage.py
```

---

### 任务8：增强日志系统 📝

**任务目标**: 实现结构化日志记录、会话上下文、性能监控

**配置脚本**:
- `demo_config_manager.py` - 配置管理器演示
  - 演示LLM响应配置管理器的使用方法
  - 展示配置文件的读写操作
  - 提供配置验证功能

- `validate_llm_config.py` - LLM配置验证
  - 验证LLM配置文件的正确性
  - 检查配置参数完整性

**监控脚本**:
- `test_monitoring.py` - 监控功能测试
  - 测试监控系统API
  - 验证性能指标收集

**运行方式**:
```bash
# 配置管理器演示
docker exec fitness_daml_rag python scripts/demo_config_manager.py

# LLM配置验证
docker exec fitness_daml_rag python scripts/validate_llm_config.py

# 监控功能测试
docker exec fitness_daml_rag python scripts/test_monitoring.py
```

---

### 任务10：性能优化和监控 ⚡

**任务目标**: 实现性能监控、BGE缓存优化、系统性能调优

**性能分析脚本**:
- `performance/analyze_retrieval_performance.py` - 检索性能分析
  - 分析检索性能瓶颈
  - 生成性能报告
  - 提供优化建议

- `performance/optimize_retrieval.py` - 检索优化
  - 优化检索算法
  - 实现缓存机制
  - 提升响应速度

- `performance/optimize_dag_parallelism.py` - DAG并行优化
  - 优化DAG执行并行性
  - 提升工作流程效率
  - 减少执行时间

**备份脚本**:
- `test_backup_manager.py` - 备份管理器测试
- `test_backup_simple.py` - 简单备份测试

**性能优化成果**:
- 响应时间减少 **48.2%**（平均减少50.92秒）
- 优化前：平均105.60秒（80-130秒）
- 优化后：平均54.68秒（37-67秒）
- 最佳改善：用户档案查询减少92.18秒（71.0%）

**运行方式**:
```bash
# 性能分析
docker exec fitness_daml_rag python scripts/performance/analyze_retrieval_performance.py

# 性能优化
docker exec fitness_daml_rag python scripts/performance/optimize_retrieval.py

# DAG并行优化
docker exec fitness_daml_rag python scripts/performance/optimize_dag_parallelism.py
```

---

## 🧪 MCP工具测试分类

### P0核心工具测试（5个）

**测试脚本**:
- `tests/test_intelligent_exercise_selector.py` - 智能动作选择器测试
- `tests/test_contraindications_checker.py` - 禁忌症检查器测试
- `tests/test_injury_risk_assessor.py` - 损伤风险评估器测试
- `tests/test_muscle_group_volume_calculator.py` - 肌群训练量计算器测试
- `tests/test_tdee_calculator.py` - TDEE计算器测试

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/tests/test_intelligent_exercise_selector.py
docker exec fitness_daml_rag python scripts/tests/test_contraindications_checker.py
docker exec fitness_daml_rag python scripts/tests/test_injury_risk_assessor.py
docker exec fitness_daml_rag python scripts/tests/test_muscle_group_volume_calculator.py
docker exec fitness_daml_rag python scripts/tests/test_tdee_calculator.py
```

### P1建议工具测试（8个）

**测试脚本**:
- `tests/test_professional_program_designer.py` - 专业训练计划设计器测试
- `tests/test_exercise_alternative_finder_improved.py` - 动作替代查找器测试（改进版）
- `tests/test_movement_pattern_balancer.py` - 动作模式平衡器测试
- `tests/test_intelligent_weight_calculator.py` - 智能负重计算器测试
- `tests/test_safe_exercise_modifier.py` - 安全动作修改器测试
- `tests/test_nutrition_intake_analyzer.py` - 营养摄入分析器测试
- `tests/test_meal_plan_designer.py` - 膳食计划设计器测试
- `tests/test_exercise_nutrition_optimization.py` - 运动营养优化器测试

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/tests/test_professional_program_designer.py
docker exec fitness_daml_rag python scripts/tests/test_meal_plan_designer.py
```

### P2扩展工具测试（2个）

**测试脚本**:
- `tests/test_periodized_program_designer.py` - 周期化训练计划测试
- `tests/test_training_split_designer.py` - 训练分化设计器测试

**专项功能测试（11个）**:
- `tests/test_mcp_tools_integration.py` - MCP工具集成测试
- `tests/test_mcp_error_handling.py` - MCP错误处理测试
- `tests/test_enhanced_contraindications.py` - 增强禁忌症测试
- `tests/test_safety_tools_severity.py` - 安全工具严重性测试
- `tests/test_expert_review_improvements.py` - 专家评审改进测试
- `tests/test_tools_direct.py` - 工具直接调用测试
- `tests/test_deload_day.py` - 减量日功能测试
- `tests/test_periodization_volume.py` - 周期化训练量测试
- `tests/test_new_training_splits.py` - 新训练分化测试
- `tests/test_weight_goal_adjustment.py` - 重量目标调整测试
- `tests/validate_all_mcp_tools.py` - 全部MCP工具验证

**运行方式**:
```bash
# 运行所有MCP工具测试
docker exec fitness_daml_rag python scripts/tests/validate_all_mcp_tools.py

# 运行专项功能测试
docker exec fitness_daml_rag python scripts/tests/test_mcp_tools_integration.py
docker exec fitness_daml_rag python scripts/tests/test_deload_day.py
```

---

## 🗄️ Neo4j数据库操作分类

### 数据库验证脚本（17个）

**验证脚本**:
- `neo4j/verify_neo4j_structure.py` - 验证数据库结构
- `neo4j/verify_neo4j_correct.py` - 验证数据正确性
- `neo4j/check_all_relationships.py` - 检查所有关系
- `neo4j/check_all_exercise_fields.py` - 检查所有字段

**修复脚本**:
- `neo4j/fix_neo4j_relationships.py` - 修复关系
- `neo4j/create_contraindicated_relations_enhanced.py` - 创建禁忌症关系
- `neo4j/create_missing_relationships.py` - 创建缺失关系
- `neo4j/restore_muscle_nodes.py` - 恢复肌肉节点

**查询脚本**:
- `neo4j/query_exercise_data.py` - 查询动作数据
- `neo4j/query_exercise_relationships.py` - 查询动作关系
- `neo4j/find_exercises_with_targets.py` - 查找有目标的动作

**导入脚本**:
- `neo4j/import_exercises_to_neo4j.py` - 导入动作到Neo4j

**分析脚本**:
- `neo4j/analyze_injury_data.py` - 分析损伤数据
- `neo4j/analyze_relationships.py` - 分析关系
- `neo4j/check_contraindicated_for.py` - 检查禁忌症关系
- `neo4j/check_neo4j_fields.py` - 检查Neo4j字段
- `neo4j/get_valid_exercise_ids.py` - 获取有效动作ID

**运行方式**:
```bash
# 验证数据库结构
docker exec fitness_daml_rag python scripts/neo4j/verify_neo4j_structure.py

# 检查所有关系
docker exec fitness_daml_rag python scripts/neo4j/check_all_relationships.py

# 导入动作数据
docker exec fitness_daml_rag python scripts/neo4j/import_exercises_to_neo4j.py
```

---

## 📊 数据补充分类

### Ollama集成测试（6个）

**测试脚本**:
- `data_supplement/test_ollama_qwen3.py` - Ollama Qwen3完整测试
- `data_supplement/test_ollama_quick.py` - Ollama快速测试
- `data_supplement/test_ollama_integration.py` - Ollama集成测试
- `data_supplement/test_ollama_*.py` (其他Ollama测试)

**数据质量检查（15个）**:
- `data_supplement/check_data_file_sync.py` - 检查数据文件同步
- `data_supplement/check_exercise_data.py` - 检查Exercise数据
- `data_supplement/check_food_fields.py` - 检查食物字段
- `data_supplement/check_missing_zh.py` - 检查缺失中文
- `data_supplement/check_translation_quality.py` - 检查翻译质量
- `data_supplement/check_professional_desc_quality.py` - 检查专业描述质量
- `data_supplement/check_injury_types.py` - 检查损伤类型
- `data_supplement/check_food_carbs.py` - 检查食物碳水化合物
- `data_supplement/verify_*.py` (5个验证脚本)

**数据清理（8个）**:
- `data_supplement/clean_exercise_data.py` - 清理Exercise数据
- `data_supplement/cleanup_exercise_descriptions.py` - 清理动作描述
- `data_supplement/fix_incomplete_translations.py` - 修复不完整翻译
- `data_supplement/compare_data_versions.py` - 比较数据版本
- `data_supplement/compare_steps_count.py` - 比较步骤数量
- `data_supplement/estimate_cleanup_time.py` - 估算清理时间
- `data_supplement/show_translation_examples.py` - 显示翻译示例
- `data_supplement/manual_translate_remaining.py` - 手动翻译剩余

**数据补充（6个）**:
- `data_supplement/exercise_supplementer.py` - Exercise数据补充
- `data_supplement/injury_type_supplementer.py` - 损伤类型补充
- `data_supplement/rehabilitation_phase_creator.py` - 康复阶段创建器
- `data_supplement/acsm_standard_supplementer.py` - ACSM标准补充器
- `data_supplement/nsca_standard_supplementer.py` - NSCA标准补充器
- `data_supplement/training_knowledge_supplementer.py` - 训练知识补充器

**任务验证（5个）**:
- `data_supplement/verify_task_2_3.py` - 验证任务2.3
- `data_supplement/verify_task_2_6.py` - 验证任务2.6
- `data_supplement/verify_injury_type_supplement.py` - 验证损伤类型补充
- `data_supplement/verify_rehabilitation_phase.py` - 验证康复阶段
- `data_supplement/verify_*.py` (其他验证脚本)

**运行方式**:
```bash
# Ollama测试
docker exec fitness_daml_rag python scripts/data_supplement/test_ollama_qwen3.py

# 数据验证
docker exec fitness_daml_rag python scripts/data_supplement/run_complete_validation.py

# 数据补充
docker exec fitness_daml_rag python scripts/data_supplement/exercise_supplementer.py
```

---

## 📥 数据导入分类

### 营养数据导入（6个）

**导入脚本**:
- `data_import/batch_import_nutrition.py` - 批量导入营养数据
- `data_import/optimized_nutrition_import.py` - 优化营养导入
- `data_import/vectorize_food_nutrition.py` - 向量化食物营养
- `data_import/vectorize_nutrition_knowledge.py` - 向量化营养知识
- `data_import/docker_vectorize_foods.py` - Docker环境食物向量化

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/data_import/batch_import_nutrition.py
docker exec fitness_daml_rag python scripts/data_import/docker_vectorize_foods.py
```

---

## ✅ 验证脚本分类

### 系统验证（9个）

**验证脚本**:
- `validation/architecture_validator.py` - 架构验证
- `validation/checkpoint_validation.py` - 检查点验证
- `validation/check_equipment_format.py` - 检查设备格式
- `validation/check_source_data.py` - 检查源数据
- `validation/test_dag_simple.py` - 简单DAG测试
- `validation/test_database_integrity.py` - 数据库完整性测试
- `validation/test_error_handling.py` - 错误处理测试
- `validation/test_performance.py` - 性能测试
- `validation/test_security_integration.py` - 安全集成测试

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/validation/architecture_validator.py
docker exec fitness_daml_rag python scripts/validation/test_database_integrity.py
```

---

## 🎯 其他实用脚本

### 训练知识管理（2个）

**脚本**:
- `training_knowledge/import_training_knowledge_to_neo4j.py` - 导入训练知识到Neo4j
- `training_knowledge/vectorize_and_import_training_knowledge.py` - 向量化并导入训练知识

### 用户管理（1个）

**脚本**:
- `user_management/create_user_profile_nodes.py` - 创建用户档案节点

### 文档分析（3个）

**脚本**:
- `document_scanner.py` - 文档扫描器
- `generate_restructure_plan.py` - 重构计划生成器
- `problem_identifier.py` - 问题识别器

### GitHub同步（1个）

**脚本**:
- `sync_framework_to_github.py` - GitHub框架代码同步

**运行方式**:
```bash
# 训练知识管理
docker exec fitness_daml_rag python scripts/training_knowledge/import_training_knowledge_to_neo4j.py

# 用户管理
docker exec fitness_daml_rag python scripts/user_management/create_user_profile_nodes.py

# 文档分析
docker exec fitness_daml_rag python scripts/document_scanner.py
```

---

## 📊 脚本统计

### 按任务分类统计

| 任务编号 | 任务名称 | 脚本数量 | 覆盖率 |
|---------|---------|---------|--------|
| **任务6** | 训练知识导入 | 15个 | 100% |
| **任务8** | 增强日志系统 | 3个 | 100% |
| **任务10** | 性能优化和监控 | 5个 | 100% |
| **MCP工具** | MCP工具测试 | 26个 | 100% |
| **Neo4j** | 数据库操作 | 17个 | 100% |
| **数据补充** | 数据质量增强 | 40个 | 95% |
| **数据导入** | 数据导入向量化 | 6个 | 100% |
| **验证脚本** | 系统验证 | 9个 | 100% |

### 总计统计

- **总脚本数量**: 120+个
- **任务覆盖**: 8个主要任务
- **MCP工具测试**: 26个脚本（100%）
- **数据脚本**: 60+个（数据完整性保障）
- **性能脚本**: 3个（48.2%性能提升）
- **自动化测试**: 90%覆盖率

---

## 🚀 快速运行脚本

### 按任务运行
```bash
# 任务6：训练知识导入
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type all
docker exec fitness_daml_rag python scripts/verify_training_knowledge_supplementers.py

# 任务8：增强日志系统
docker exec fitness_daml_rag python scripts/demo_config_manager.py
docker exec fitness_daml_rag python scripts/validate_llm_config.py

# 任务10：性能优化和监控
docker exec fitness_daml_rag python scripts/performance/analyze_retrieval_performance.py
docker exec fitness_daml_rag python scripts/test_backup_manager.py
```

### 运行所有测试
```bash
# 所有MCP工具测试
docker exec fitness_daml_rag python scripts/tests/validate_all_mcp_tools.py

# 所有Neo4j验证
docker exec fitness_daml_rag python scripts/neo4j/verify_neo4j_structure.py

# 所有数据验证
docker exec fitness_daml_rag python scripts/data_supplement/run_complete_validation.py
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
**版本**: v1.0.0
