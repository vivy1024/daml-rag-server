# 脚本分类快速参考

**版本**: v1.0.0
**更新日期**: 2025-12-20
**维护者**: 薛小川

---

## 🎯 快速导航

### 按用途分类

| 分类 | 数量 | 主要用途 | 典型脚本 |
|------|------|---------|---------|
| **测试脚本** | 26个 | MCP工具测试、功能验证 | `test_*.py`, `validate_*.py` |
| **数据检查** | 5个 | 数据质量快速检查 | `check_*.py` |
| **数据验证** | 4个 | 训练知识验证 | `verify_*.py` |
| **性能优化** | 3个 | 检索性能优化 | `performance/*.py` |
| **数据库操作** | 17个 | Neo4j数据库管理 | `neo4j/*.py` |
| **MCP工具** | 6个 | MCP服务验证 | `mcp/*.py` |
| **数据补充** | 40个 | 数据库增强 | `data_supplement/*.py` |
| **数据导入** | 6个 | 数据导入向量化 | `data_import/*.py` |
| **训练知识** | 2个 | 训练知识管理 | `training_knowledge/*.py` |
| **用户管理** | 1个 | 用户档案管理 | `user_management/*.py` |
| **验证脚本** | 9个 | 系统验证 | `validation/*.py` |

---

## 🧪 测试脚本详解

### P0核心工具测试（5个）
```bash
# 基础功能测试
test_intelligent_exercise_selector.py  # 智能动作选择
test_contraindications_checker.py      # 禁忌症检查
test_injury_risk_assessor.py           # 损伤风险评估
test_muscle_group_volume_calculator.py # 肌群训练量计算
test_tdee_calculator.py                # TDEE计算
```

### P1建议工具测试（8个）
```bash
# 专业功能测试
test_professional_program_designer.py      # 训练计划设计
test_exercise_alternative_finder_improved.py # 动作替代
test_movement_pattern_balancer.py          # 动作模式平衡
test_intelligent_weight_calculator.py      # 智能负重计算
test_safe_exercise_modifier.py             # 安全动作修改
test_nutrition_intake_analyzer.py          # 营养摄入分析
test_meal_plan_designer.py                 # 膳食计划设计
test_exercise_nutrition_optimization.py    # 运动营养优化
```

### P2扩展工具测试（2个）
```bash
# 高级功能测试
test_periodized_program_designer.py  # 周期化训练计划
test_training_split_designer.py      # 训练分化设计
```

### 专项功能测试（11个）
```bash
# 集成和专项测试
test_mcp_tools_integration.py        # MCP工具集成
test_mcp_error_handling.py           # MCP错误处理
test_enhanced_contraindications.py   # 增强禁忌症
test_safety_tools_severity.py        # 安全工具严重性
test_expert_review_improvements.py   # 专家评审改进
test_tools_direct.py                 # 工具直接调用
test_deload_day.py                   # 减量日功能
test_periodization_volume.py         # 周期化训练量
test_new_training_splits.py          # 新训练分化
test_weight_goal_adjustment.py       # 重量目标调整
validate_all_mcp_tools.py            # 全部MCP工具验证
```

**运行方式**:
```bash
# 运行单个测试
docker exec fitness_daml_rag python scripts/tests/test_tdee_calculator.py

# 运行所有测试
docker exec fitness_daml_rag python scripts/tests/validate_all_mcp_tools.py
```

---

## 📊 数据脚本详解

### 数据检查脚本（5个）
```bash
# 快速数据质量检查
check_exercise_id_field.py      # 检查Exercise节点ID
check_exercise_names.py         # 检查动作名称
check_muscle_names.py           # 检查肌肉名称
check_knowledge_coverage.py     # 检查知识覆盖率
check_neo4j_knowledge_simple.py # 简单检查Neo4j知识
```

### 数据验证脚本（4个）
```bash
# 训练知识数据验证
verify_strength_standards.py              # 验证力量标准
verify_training_knowledge_supplementers.py # 验证训练知识补充器
verify_training_volume.py                 # 验证训练量
verify_workout_programs.py                # 验证训练计划
```

### 数据补充脚本（40个）
```bash
# Ollama集成测试
test_ollama_qwen3.py           # Ollama Qwen3完整测试
test_ollama_quick.py           # Ollama快速测试
test_ollama_integration.py     # Ollama集成测试

# 数据质量检查
check_data_file_sync.py        # 检查数据文件同步
check_exercise_data.py         # 检查Exercise数据
check_food_fields.py           # 检查食物字段
check_missing_zh.py            # 检查缺失中文
check_translation_quality.py   # 检查翻译质量

# 数据清理
clean_exercise_data.py         # 清理Exercise数据
cleanup_exercise_descriptions.py # 清理动作描述
fix_incomplete_translations.py # 修复不完整翻译

# 数据补充
exercise_supplementer.py       # Exercise数据补充
injury_type_supplementer.py    # 损伤类型补充
rehabilitation_phase_creator.py # 康复阶段创建

# 任务验证
verify_task_2_3.py             # 验证任务2.3
verify_task_2_6.py             # 验证任务2.6
verify_injury_type_supplement.py # 验证损伤类型补充
verify_rehabilitation_phase.py # 验证康复阶段
```

---

## ⚡ 性能脚本详解

```bash
# 性能分析和优化
analyze_retrieval_performance.py  # 检索性能分析
optimize_retrieval.py             # 检索优化
optimize_dag_parallelism.py       # DAG并行优化
```

**性能优化成果**:
- 响应时间减少 **48.2%**（平均减少50.92秒）
- 优化前：平均105.60秒（80-130秒）
- 优化后：平均54.68秒（37-67秒）
- 最佳改善：用户档案查询减少92.18秒（71.0%）

---

## 🗄️ 数据库脚本详解

### Neo4j操作（17个）
```bash
# 数据库验证
verify_neo4j_structure.py       # 验证数据库结构
verify_neo4j_correct.py         # 验证数据正确性
check_all_relationships.py      # 检查所有关系
check_all_exercise_fields.py    # 检查所有字段

# 数据修复
fix_neo4j_relationships.py      # 修复关系
create_contraindicated_relations_enhanced.py # 创建禁忌症关系
create_missing_relationships.py # 创建缺失关系
restore_muscle_nodes.py         # 恢复肌肉节点

# 数据查询
query_exercise_data.py          # 查询动作数据
query_exercise_relationships.py # 查询动作关系
find_exercises_with_targets.py  # 查找有目标的动作

# 数据导入
import_exercises_to_neo4j.py    # 导入动作到Neo4j
```

---

## 🔧 实用脚本详解

### 训练知识导入
```bash
# 训练知识导入脚本
import_training_knowledge.py    # 训练知识导入主脚本
# 支持类型: training_volume, strength_standards, workout_programs, acsm_standards, nsca_standards
```

### 配置管理
```bash
# 配置相关脚本
demo_config_manager.py          # 配置管理器演示
validate_llm_config.py          # LLM配置验证
```

### 文档分析
```bash
# 文档处理脚本
document_scanner.py             # 文档扫描器
generate_restructure_plan.py    # 重构计划生成器
problem_identifier.py           # 问题识别器
```

### 备份和同步
```bash
# 备份和同步脚本
test_backup_manager.py          # 备份管理器测试
sync_framework_to_github.py     # GitHub框架同步
```

---

## 🚀 快速使用指南

### 日常测试
```bash
# 1. 测试所有MCP工具
docker exec fitness_daml_rag python scripts/tests/validate_all_mcp_tools.py

# 2. 检查数据质量
docker exec fitness_daml_rag python scripts/check_knowledge_coverage.py

# 3. 验证训练知识
docker exec fitness_daml_rag python scripts/verify_training_knowledge_supplementers.py
```

### 问题排查
```bash
# 1. 验证数据库结构
docker exec fitness_daml_rag python scripts/neo4j/verify_neo4j_structure.py

# 2. 检查所有关系
docker exec fitness_daml_rag python scripts/neo4j/check_all_relationships.py

# 3. 运行完整验证
docker exec fitness_daml_rag python scripts/data_supplement/run_complete_validation.py
```

### 性能优化
```bash
# 1. 分析性能
docker exec fitness_daml_rag python scripts/performance/analyze_retrieval_performance.py

# 2. 优化并行性
docker exec fitness_daml_rag python scripts/performance/optimize_dag_parallelism.py
```

### 数据导入
```bash
# 1. 导入训练知识
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type all

# 2. 模拟导入（不修改数据库）
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type all --dry-run
```

---

## 📊 脚本价值统计

| 分类 | 脚本数量 | 主要价值 | 关键指标 |
|------|---------|---------|---------|
| **测试脚本** | 26个 | 质量保证 | 100% MCP工具覆盖 |
| **数据脚本** | 60+个 | 数据完整性 | 1603个Exercise验证 |
| **性能脚本** | 3个 | 性能优化 | 48.2%响应时间提升 |
| **总计** | 120+个 | 全面保障 | 90%自动化测试 |

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
**版本**: v1.0.0
