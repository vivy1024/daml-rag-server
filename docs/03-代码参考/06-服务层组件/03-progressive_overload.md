# progressive_overload.py - 渐进式超负荷计算器

**文件路径**：`src/applications/fitness/services/progressive_overload.py`
**状态**：✅ 已完成

---

## 📋 功能概述

渐进式超负荷计算器基于运动科学原理，科学计算训练强度的渐进式增长计划。确保训练负荷的合理提升，避免过度训练和平台期。

---

## 🎯 核心功能

### 1. 负荷计算
- 基于1RM百分比计算
- 考虑训练历史和恢复状态
- 个性化调整系数

### 2. 进度规划
- 周计划递增模式
- 周期化调整策略
- 平台期突破方案

### 3. 风险控制
- 过度训练预警
- 疲劳累积监测
- 恢复需求评估

---

## 📊 超负荷策略

### 线性递增
- 每周增加2.5-5%负荷
- 适合初级训练者
- 风险较低

### 波浪式递增
- 高低负荷交替
- 适合中级训练者
- 避免平台期

### 周期化递增
- 3-4周递增，1周减载
- 适合高级训练者
- 长期发展优化

---

## 🔧 使用示例

```python
# 初始化计算器
calculator = ProgressiveOverload()

# 计算下次训练负荷
next_load = calculator.calculate_next_load(
    current_weight=80,
    current_volume=3000,
    weeks_trained=4,
    user_level="intermediate"
)
# 返回: {"weight": 85, "volume": 3150, "reasoning": "..."}

# 生成周期化计划
plan = calculator.create_periodized_plan(
    base_volume=3000,
    duration=12,  # 12周
    peak_week=8
)
```

---

## 🔗 集成方式

- **MCP工具**：intelligent_weight_calculator
- **服务层**：volume_adjuster
- **MCP工具**：training_split_designer

---

**维护者**: 薛小川
**最后更新**: 2025-12-31
