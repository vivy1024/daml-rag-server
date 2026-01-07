# MCP工具测试 🧪

**任务目标**: 测试所有MCP工具的功能和性能

**脚本数量**: 26个

## 📋 测试分类

### P0核心工具测试（5个）
- `test_intelligent_exercise_selector.py` - 智能动作选择器测试
- `test_contraindications_checker.py` - 禁忌症检查器测试
- `test_injury_risk_assessor.py` - 损伤风险评估器测试
- `test_muscle_group_volume_calculator.py` - 肌群训练量计算器测试
- `test_tdee_calculator.py` - TDEE计算器测试

### P1建议工具测试（8个）
- `test_professional_program_designer.py` - 专业训练计划设计器测试
- `test_exercise_alternative_finder_improved.py` - 动作替代查找器测试（改进版）
- `test_movement_pattern_balancer.py` - 动作模式平衡器测试
- `test_intelligent_weight_calculator.py` - 智能负重计算器测试
- `test_safe_exercise_modifier.py` - 安全动作修改器测试
- `test_nutrition_intake_analyzer.py` - 营养摄入分析器测试
- `test_meal_plan_designer.py` - 膳食计划设计器测试
- `test_exercise_nutrition_optimization.py` - 运动营养优化器测试

### P2扩展工具测试（2个）
- `test_periodized_program_designer.py` - 周期化训练计划测试
- `test_training_split_designer.py` - 训练分化设计器测试

### 专项功能测试（11个）
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

## 🚀 运行方式

```bash
# 测试P0核心工具
docker exec fitness_daml_rag python scripts/MCP工具测试/test_tdee_calculator.py
docker exec fitness_daml_rag python scripts/MCP工具测试/test_intelligent_exercise_selector.py

# 测试P1建议工具
docker exec fitness_daml_rag python scripts/MCP工具测试/test_professional_program_designer.py
docker exec fitness_daml_rag python scripts/MCP工具测试/test_meal_plan_designer.py

# 运行所有工具集成测试
docker exec fitness_daml_rag python scripts/MCP工具测试/validate_all_mcp_tools.py
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
