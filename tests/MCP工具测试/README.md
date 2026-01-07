# MCP工具测试 🧪

**任务目标**: 测试所有MCP工具的功能和性能

**测试文件数量**: 15个

## 📋 测试分类

### P0核心工具测试（5个）
- `test_intelligent_exercise_selector.py` - 智能动作选择器测试
- `test_contraindications_checker.py` - 禁忌症检查器测试
- `test_injury_risk_assessor.py` - 损伤风险评估器测试
- `test_muscle_group_volume_calculator.py` - 肌群训练量计算器测试
- `test_tdee_calculator.py` - TDEE计算器测试

### P1建议工具测试（8个）
- `test_exercise_alternative_finder.py` - 动作替代查找器测试
- `test_intelligent_weight_calculator.py` - 智能负重计算器测试
- `test_movement_pattern_balancer.py` - 动作模式平衡器测试
- `test_safe_exercise_modifier.py` - 安全动作修改器测试

### 工具基础测试（2个）
- `test_mcp_base_tool.py` - MCP基础工具测试
- `test_mcp_registry.py` - MCP注册表测试

## 🚀 运行方式

```bash
# 运行所有MCP工具测试
docker exec fitness_daml_rag pytest tests/MCP工具测试/ -v

# 运行P0核心工具测试
docker exec fitness_daml_rag pytest tests/MCP工具测试/test_intelligent_exercise_selector.py -v
docker exec fitness_daml_rag pytest tests/MCP工具测试/test_tdee_calculator.py -v
```

---

**最后更新**: 2025-12-20
**维护者**: 薛小川
