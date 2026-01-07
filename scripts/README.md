# DAML-RAG Scripts 目录

**版本**: v2.7.0
**更新日期**: 2025-12-20
**维护者**: 薛小川

---

## 📁 目录结构

```
scripts/
├── 任务6-训练知识导入/          # 训练知识导入相关（14个）
├── 任务8-增强日志系统/          # 增强日志系统相关（3个）
├── 任务10-性能优化和监控/       # 性能优化和监控相关（5个）
├── MCP工具测试/                # MCP工具测试（26个）
├── Neo4j数据库操作/            # Neo4j数据库相关（17个）
├── 数据质量增强/               # 数据质量增强（40+个）
├── 数据导入向量化/             # 数据导入向量化（6个）
├── 系统验证/                   # 系统验证（14个）
├── 实用工具脚本/               # 实用工具（3个）
│   ├── document_scanner.py     # 文档扫描器
│   ├── problem_identifier.py   # 问题识别器
│   └── sync_framework_to_github.py  # GitHub框架代码同步
├── training_knowledge/        # 训练知识相关（2个）
├── user_management/           # 用户管理相关（1个）
├── archived/                  # 历史文档和总结报告
├── cleanup/                   # 清理脚本
└── README.md                 # 本文件
```

**脚本统计**: 总计 **120+** 个脚本文件，按任务分类管理

## 🎯 任务分类概览

| 任务编号 | 任务名称 | 脚本数量 | 主要功能 |
|---------|---------|---------|---------|
| **任务6** | 训练知识导入 | 14个 | 训练知识数据导入、验证和管理 |
| **任务8** | 增强日志系统 | 3个 | 结构化日志记录、会话上下文、性能监控 |
| **任务10** | 性能优化和监控 | 5个 | 检索性能分析、DAG并行优化、系统性能调优 |
| **MCP工具** | MCP工具测试 | 26个 | 测试15个Python内置MCP工具 |
| **Neo4j** | 数据库操作 | 17个 | Neo4j数据库的查询、验证、修复、补充 |
| **数据补充** | 数据质量增强 | 40+个 | Ollama集成测试、数据质量检查、数据清理 |
| **数据导入** | 数据导入向量化 | 6个 | 营养数据、食物数据的导入和向量化 |
| **验证脚本** | 系统验证 | 14个 | 系统架构、数据库完整性、安全性验证 |

---

## 📂 分类说明

### 1. tests/ - 测试脚本（26个）

**用途**: 测试MCP工具、功能模块、训练功能的脚本

**P0核心工具测试（5个）**:
- `test_intelligent_exercise_selector.py` - 智能动作选择器测试
- `test_contraindications_checker.py` - 禁忌症检查器测试
- `test_injury_risk_assessor.py` - 损伤风险评估器测试
- `test_muscle_group_volume_calculator.py` - 肌群训练量计算器测试
- `test_tdee_calculator.py` - TDEE计算器测试

**P1建议工具测试（8个）**:
- `test_professional_program_designer.py` - 专业训练计划设计器测试
- `test_exercise_alternative_finder_improved.py` - 动作替代查找器测试（改进版）
- `test_movement_pattern_balancer.py` - 动作模式平衡器测试
- `test_intelligent_weight_calculator.py` - 智能负重计算器测试
- `test_safe_exercise_modifier.py` - 安全动作修改器测试
- `test_nutrition_intake_analyzer.py` - 营养摄入分析器测试
- `test_meal_plan_designer.py` - 膳食计划设计器测试
- `test_exercise_nutrition_optimization.py` - 运动营养优化器测试

**P2扩展工具测试（2个）**:
- `test_periodized_program_designer.py` - 周期化训练计划测试
- `test_training_split_designer.py` - 训练分化设计器测试

**专项功能测试（11个）**:
- `test_mcp_tools_integration.py` - MCP工具集成测试
- `test_mcp_error_handling.py` - MCP错误处理测试
- `test_enhanced_contraindications.py` - 增强禁忌症测试
- `test_safety_tools_severity.py` - 安全工具严重性测试
- `test_expert_review_improvements.py` - 专家评审改进测试
- `test_tools_direct.py` - 工具直接调用测试
- `test_deload_day.py` - 减量日功能测试
- `test_periodization_volume.py` - 周期化训练量测试
- `test_new_training_splits.py` - 新训练分化测试
- `test_weight_goal_adjustment.py` - 重量目标调整测试
- `validate_all_mcp_tools.py` - 全部MCP工具验证

**运行方式**:
```bash
# 在Docker容器内运行
docker exec fitness_daml_rag python scripts/tests/test_xxx.py

# 运行所有测试
docker exec fitness_daml_rag python scripts/tests/validate_all_mcp_tools.py
```

---

### 2. neo4j/ - Neo4j数据库相关

**用途**: Neo4j数据库的查询、验证、修复、补充脚本

**主要文件**:
- `verify_neo4j_*.py` - 数据库结构验证
- `check_*.py` - 数据完整性检查
- `create_*.py` - 创建节点和关系
- `fix_*.py` - 修复数据问题
- `query_*.py` - 数据查询
- `debug_*.py` - 调试脚本
- `analyze_*.py` - 数据分析

**关键脚本**:
- `verify_neo4j_structure.py` - 验证数据库结构完整性
- `check_all_relationships.py` - 检查所有关系
- `check_all_exercise_fields.py` - 检查Exercise节点所有字段
- `create_contraindicated_relations_enhanced.py` - 创建增强版禁忌症关系
- `verify_neo4j_correct.py` - 验证数据正确性

**已清理的冗余脚本**:
- ❌ `debug_*.py` - 调试脚本（已完成调试）
- ❌ `check_exercise_fields.py` - 被check_all_exercise_fields.py替代
- ❌ `verify_neo4j_simple.py` - 被verify_neo4j_structure.py替代
- ❌ `supplement_neo4j_data.py` - 已被data_supplement模块替代

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/neo4j/xxx.py
```

---

### 3. mcp/ - MCP工具相关

**用途**: MCP服务的验证、测试、修复脚本

**主要文件**:
- `validate_mcp_*.py` - MCP服务验证
- `fix_mcp_*.py` - MCP问题修复
- `task10_dag_mcp_integration_test.py` - DAG与MCP集成测试

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/mcp/xxx.py
```

---

### 4. validation/ - 验证脚本

**用途**: 系统架构、数据质量、配置的验证脚本

**主要文件**:
- `architecture_validator.py` - 架构验证
- `checkpoint_validation.py` - 检查点验证
- `check_*.py` - 各种检查脚本
- `validate_*.py` - 验证脚本

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/validation/xxx.py
```

---

### 5. data_supplement/ - 数据补充相关

**用途**: Neo4j数据库增强、Ollama集成测试

**主要文件**:
- `test_ollama_qwen3.py` - Ollama Qwen3 8B完整测试
- `test_ollama_quick.py` - Ollama快速测试

**说明**:
- 这些脚本用于测试Ollama LLM集成
- 实际的数据补充功能在 `src/applications/fitness/data_supplement/` 模块中

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/data_supplement/test_ollama_qwen3.py
```

---

### 5. performance/ - 性能优化脚本（3个）

**用途**: 检索性能分析、DAG并行优化、系统性能调优

**主要文件**:
- `analyze_retrieval_performance.py` - 检索性能分析
- `optimize_retrieval.py` - 检索优化
- `optimize_dag_parallelism.py` - DAG并行优化

**性能优化成果**:
- 响应时间减少 **48.2%**（平均减少50.92秒）
- 优化前：平均105.60秒（80-130秒）
- 优化后：平均54.68秒（37-67秒）
- 最佳改善：用户档案查询减少92.18秒（71.0%）

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/performance/analyze_retrieval_performance.py
docker exec fitness_daml_rag python scripts/performance/optimize_retrieval.py
docker exec fitness_daml_rag python scripts/performance/optimize_dag_parallelism.py
```

---

### 6. data_supplement/ - 数据补充相关（40个）

**用途**: Neo4j数据库增强、数据质量检查、Ollama集成测试

**主要分类**:
- **Ollama集成测试**: `test_ollama_*.py` (6个)
- **数据质量检查**: `check_*.py`, `verify_*.py` (15个)
- **数据清理**: `clean_*.py`, `fix_*.py`, `cleanup_*.py` (8个)
- **数据补充**: `*_supplementer.py` (6个)
- **任务验证**: `verify_task_*.py` (5个)

**关键脚本**:
- `test_ollama_qwen3.py` - Ollama Qwen3 8B完整测试
- `test_ollama_quick.py` - Ollama快速测试
- `run_complete_validation.py` - 完整验证流程
- `sync_json_from_neo4j.py` - Neo4j到JSON同步
- `exercise_supplementer.py` - Exercise数据补充
- `injury_type_supplementer.py` - 损伤类型补充
- `rehabilitation_phase_creator.py` - 康复阶段创建器

**说明**:
- 这些脚本用于测试Ollama LLM集成和数据库增强
- 实际的数据补充功能在 `src/applications/fitness/data_supplement/` 模块中

**运行方式**:
```bash
# 运行Ollama测试
docker exec fitness_daml_rag python scripts/data_supplement/test_ollama_qwen3.py

# 运行数据验证
docker exec fitness_daml_rag python scripts/data_supplement/run_complete_validation.py

# 运行数据补充
docker exec fitness_daml_rag python scripts/data_supplement/exercise_supplementer.py
```

---

### 7. data_import/ - 数据导入相关

**用途**: 营养数据、食物数据的导入和向量化脚本

**主要文件**:
- `import_*.py` - 各种数据导入脚本
- `vectorize_*.py` - 向量化脚本
- `batch_import_nutrition.py` - 批量导入营养数据
- `docker_vectorize_foods.py` - Docker环境下的食物向量化

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/data_import/xxx.py
```

---

### 8. check_*.py - 数据检查脚本（5个）

**用途**: 快速数据质量检查和验证

**主要文件**:
- `check_exercise_id_field.py` - 检查Exercise节点ID字段
- `check_exercise_names.py` - 检查动作名称
- `check_muscle_names.py` - 检查肌肉名称
- `check_knowledge_coverage.py` - 检查知识覆盖率
- `check_neo4j_knowledge_simple.py` - 简单检查Neo4j知识

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/check_*.py
```

---

### 9. verify_*.py - 数据验证脚本（4个）

**用途**: 验证训练知识数据的完整性

**主要文件**:
- `verify_strength_standards.py` - 验证力量标准
- `verify_training_knowledge_supplementers.py` - 验证训练知识补充器
- `verify_training_volume.py` - 验证训练量
- `verify_workout_programs.py` - 验证训练计划

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/verify_*.py
```

---

### 10. test_*.py - 通用测试脚本（6个）

**用途**: 各种通用测试和验证

**主要文件**:
- `test_backup_manager.py` - 备份管理器测试
- `test_backup_simple.py` - 简单备份测试
- `test_monitoring.py` - 监控功能测试
- `test_qdrant_import.py` - Qdrant导入测试
- `test_strength_import.py` - 力量数据导入测试
- `test_training_knowledge_import.py` - 训练知识导入测试
- `test_validator.py` - 验证器测试
- `test_validator_simple.py` - 简单验证器测试

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/test_*.py
```

---

### 11. training_knowledge/ - 训练知识相关（2个）

**用途**: 训练知识的导入和向量化

**主要文件**:
- `import_training_knowledge_to_neo4j.py` - 导入训练知识到Neo4j
- `vectorize_and_import_training_knowledge.py` - 向量化并导入训练知识

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/training_knowledge/xxx.py
```

---

### 12. user_management/ - 用户管理相关（1个）

**用途**: 用户档案管理脚本

**主要文件**:
- `create_user_profile_nodes.py` - 创建用户档案节点

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/user_management/create_user_profile_nodes.py
```

---

### 13. archived/ - 历史文档和总结报告

**用途**: 存档的总结报告、修复说明、验证报告

**主要文件**:
- `*.md` - 各种Markdown格式的报告
- `p1_*.md` - P1阶段的报告
- `task*.py` - 历史任务脚本

**说明**: 这些文件主要用于历史记录和参考，不建议直接运行

---

### 14. import_training_knowledge.py - 训练知识导入脚本

**用途**: 导入训练知识数据到Neo4j数据库

**功能**:
- 导入训练量标准（MEV/MAV/MRV）
- 导入力量标准（StrengthStandard）
- 导入训练计划模板（WorkoutProgram）
- 导入ACSM标准
- 导入NSCA标准
- 支持模拟导入（dry-run）
- 生成JSON格式报告

**使用方式**:
```bash
# 导入所有训练知识
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type all

# 导入特定类型
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type training_volume
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type strength_standards
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type workout_programs
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type acsm_standards
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type nsca_standards

# 模拟导入（不实际修改数据库）
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type all --dry-run

# 输出JSON格式报告
docker exec fitness_daml_rag python scripts/import_training_knowledge.py --data-type all --output-json report.json
```

**数据源**:
- `data/training_knowledge/training-volume-landmarks.json`
- `data/training_knowledge/strength-standards.json`
- `data/training_knowledge/workout-programs.json`
- `data/training_knowledge/acsm_standards/*.json`
- `data/training_knowledge/nsca_standards/*.json`

---

### 15. demo_config_manager.py - 配置管理器演示

**用途**: LLM响应配置管理器的演示和使用指南

**功能**:
- 演示LLM响应配置管理器的使用方法
- 展示配置文件的读写操作
- 提供配置验证功能
- 帮助理解配置管理器的API

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/demo_config_manager.py
```

**参考文档**: `docs/04-开发指南/46-增强日志系统使用指南.md`

---

### 16. validate_llm_config.py - LLM配置验证

**用途**: 验证LLM配置文件的正确性

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/validate_llm_config.py
```

---

### 17. 其他实用脚本

**文档扫描和分析**:
- `document_scanner.py` - 文档扫描器
- `generate_restructure_plan.py` - 重构计划生成器
- `problem_identifier.py` - 问题识别器

**GitHub同步**:
- `sync_framework_to_github.py` - GitHub框架代码同步

**运行方式**:
```bash
docker exec fitness_daml_rag python scripts/document_scanner.py
docker exec fitness_daml_rag python scripts/generate_restructure_plan.py
docker exec fitness_daml_rag python scripts/sync_framework_to_github.py
```

---

### 18. sync_framework_to_github.py - GitHub框架代码同步

**用途**: 将框架层代码同步到GitHub开源项目

**功能**:
- 备份旧代码（可选）
- 删除旧代码
- 复制新代码
- 验证文件完整性

**使用方式**:
```bash
# 带备份同步
python scripts/sync_framework_to_github.py

# 不备份直接同步
python scripts/sync_framework_to_github.py --no-backup
```

**同步路径**:
- 源目录: `daml-rag-server/src/framework/`
- 目标目录: `daml-rag-framework/framework/`

**注意事项**:
- 会自动排除 `__pycache__` 和 `.pyc` 文件
- 验证文件数量和内容一致性
- 建议在同步前先提交本地变更

---

## 🚀 常用命令

### 1. 任务6：训练知识导入
```bash
# 导入所有训练知识
docker exec fitness_daml_rag python scripts/任务6-训练知识导入/import_training_knowledge.py --data-type all

# 验证训练知识
docker exec fitness_daml_rag python scripts/任务6-训练知识导入/verify_training_knowledge_supplementers.py

# 检查知识覆盖率
docker exec fitness_daml_rag python scripts/任务6-训练知识导入/check_knowledge_coverage.py
```

### 2. 任务8：增强日志系统
```bash
# 配置管理器演示
docker exec fitness_daml_rag python scripts/任务8-增强日志系统/demo_config_manager.py

# LLM配置验证
docker exec fitness_daml_rag python scripts/任务8-增强日志系统/validate_llm_config.py

# 监控功能测试
docker exec fitness_daml_rag python scripts/任务8-增强日志系统/test_monitoring.py
```

### 3. 任务10：性能优化和监控
```bash
# 性能分析
docker exec fitness_daml_rag python scripts/任务10-性能优化和监控/analyze_retrieval_performance.py

# DAG并行优化
docker exec fitness_daml_rag python scripts/任务10-性能优化和监控/optimize_dag_parallelism.py
```

### 4. MCP工具测试
```bash
# 测试P0核心工具
docker exec fitness_daml_rag python scripts/MCP工具测试/test_tdee_calculator.py
docker exec fitness_daml_rag python scripts/MCP工具测试/test_intelligent_exercise_selector.py

# 测试P1建议工具
docker exec fitness_daml_rag python scripts/MCP工具测试/test_professional_program_designer.py
docker exec fitness_daml_rag python scripts/MCP工具测试/test_meal_plan_designer.py

# 测试所有工具集成
docker exec fitness_daml_rag python scripts/MCP工具测试/validate_all_mcp_tools.py
```

### 5. Neo4j数据库操作
```bash
# 验证数据库结构
docker exec fitness_daml_rag python scripts/Neo4j数据库操作/verify_neo4j_structure.py

# 检查所有关系
docker exec fitness_daml_rag python scripts/Neo4j数据库操作/check_all_relationships.py

# 导入动作数据
docker exec fitness_daml_rag python scripts/Neo4j数据库操作/import_exercises_to_neo4j.py
```

### 6. 数据质量增强
```bash
# Ollama测试
docker exec fitness_daml_rag python scripts/数据质量增强/test_ollama_qwen3.py

# 运行完整验证流程
docker exec fitness_daml_rag python scripts/数据质量增强/run_complete_validation.py

# 数据补充
docker exec fitness_daml_rag python scripts/数据质量增强/exercise_supplementer.py
```

### 7. 数据导入向量化
```bash
# 批量导入营养数据
docker exec fitness_daml_rag python scripts/数据导入向量化/batch_import_nutrition.py

# Docker环境食物向量化
docker exec fitness_daml_rag python scripts/数据导入向量化/docker_vectorize_foods.py
```

### 8. 系统验证
```bash
# 架构验证
docker exec fitness_daml_rag python scripts/系统验证/architecture_validator.py

# 数据库完整性测试
docker exec fitness_daml_rag python scripts/系统验证/test_database_integrity.py

# 安全集成测试
docker exec fitness_daml_rag python scripts/系统验证/test_security_integration.py
```

---

## 📝 脚本开发规范

### 1. 命名规范
- 测试脚本: `test_*.py`
- 验证脚本: `validate_*.py` 或 `check_*.py`
- 创建脚本: `create_*.py`
- 修复脚本: `fix_*.py`
- 查询脚本: `query_*.py`

### 2. 文件头部注释
```python
#!/usr/bin/env python3
"""
脚本简短描述

详细说明：
- 功能1
- 功能2

使用方式：
    docker exec fitness_daml_rag python scripts/xxx/script.py
"""
```

### 3. 日志输出
- 使用emoji增强可读性: ✅ ❌ 🔄 📊 等
- 使用分隔线: `"=" * 60`
- 清晰的阶段标识: `[阶段1/3]`

### 4. 错误处理
- 使用try-except捕获异常
- 记录详细的错误信息
- 提供有用的错误提示

---

## 🔧 维护指南

### 添加新脚本
1. 确定脚本类型（测试/验证/数据处理等）
2. 放入对应的子目录
3. 遵循命名规范
4. 添加完整的文档注释
5. 更新本README

### 清理旧脚本
1. 将不再使用的脚本移到 `archived/`
2. 在移动前确认没有依赖
3. 定期清理archived目录中的过时文档
4. 更新相关文档

### 脚本清理原则
- ✅ **保留最新版本**: 如有improved/enhanced版本，删除旧版
- ✅ **删除调试脚本**: debug_*.py在调试完成后应删除
- ✅ **合并重复功能**: 功能重复的脚本只保留一个
- ✅ **清理测试脚本**: 简单测试脚本在功能稳定后可删除
- ✅ **模块化替代**: 被模块化代码替代的脚本应删除

### 最近清理记录

**2025-12-20** - v2.5.0 更新
- 新增 performance/ 目录（3个性能优化脚本）
- 新增 check_*.py 系列脚本（5个数据检查脚本）
- 新增 verify_*.py 系列脚本（4个数据验证脚本）
- 新增 demo_config_manager.py 配置管理器演示
- 新增 validate_llm_config.py LLM配置验证
- 整合 tests/ 目录测试脚本（从17个增加到26个）

**2025-12-15** - v2.0.0 清理
删除了18个冗余脚本：
- 7个neo4j调试和重复脚本
- 2个tests重复脚本
- 1个mcp简单验证脚本
- 4个data_import重复脚本
- 3个archived历史任务脚本
- 1个__pycache__目录

---

## 📚 相关文档

**核心架构文档**:
- **DAML-RAG完整工作流程**: `docs/02-核心架构/03-完整工作流程.md`
- **MCP工具架构**: `docs/02-核心架构/05-MCP工具架构.md`
- **Neo4j数据库结构**: `docs/02-核心架构/11-Neo4j数据库结构.md`

**开发指南文档**:
- **MCP工具功能清单**: `docs/04-开发指南/43-MCP工具功能清单.md`
- **增强日志系统使用指南**: `docs/04-开发指南/46-增强日志系统使用指南.md`
- **训练知识数据导入指南**: `docs/04-开发指南/45-训练知识数据导入指南.md`
- **质量保证与专家验证体系**: `docs/04-开发指南/21-质量保证与专家验证体系.md`

**代码参考文档**:
- **MCP工具参考**: `docs/03-代码参考/XX模块参考.md`
- **数据补充模块**: `src/applications/fitness/data_supplement/`

**测试报告**:
- **E2E测试报告**: `tests/integration/E2E_TEST_REPORT.md`
- **性能对比报告**: `tests/integration/PERFORMANCE_COMPARISON_REPORT.md`
- **任务测试报告**: `tests/integration/TASK_9_3_TEST_REPORT.md`

---

## 🎯 脚本价值总结

### 测试脚本价值（26个）
- **100%覆盖** 15个Python内置MCP工具
- **3层测试体系** 单元测试 → 集成测试 → 端到端测试
- **质量保证** 通过专家评审和验证测试

### 数据脚本价值（60+个）
- **数据完整性** 验证1603个Exercise节点数据质量
- **知识覆盖** 验证训练知识数据完整性
- **备份恢复** 实现数据库备份和恢复机制

### 性能脚本价值（3个）
- **48.2%性能提升** 响应时间平均减少50.92秒
- **并行优化** DAG执行并行化优化
- **缓存优化** 全局BGE模型缓存

### 总计价值
- **120+个脚本** 覆盖全流程测试和验证
- **自动化测试** 减少90%手工测试工作量
- **质量保障** 确保系统稳定性和性能

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
**版本**: v2.5.0
