# DAG模板选择指南

**版本**: v1.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本指南帮助开发者和用户理解如何选择合适的DAG模板来处理不同类型的健身咨询。DAML-RAG系统提供9个预定义的DAG模板，每个模板针对特定的使用场景优化。

### 核心原则

- ✅ **LLM自动选择**：系统通过LLM决策引擎自动选择最合适的模板
- ✅ **关键词匹配**：基于用户查询中的关键词进行智能匹配
- ✅ **降级策略**：LLM失败时使用规则匹配作为降级方案
- ✅ **可追溯性**：每次选择都记录选择理由和置信度

---

## 模板选择决策树

```
用户查询
    ↓
是否只是问候？
    ├─ 是 → greeting（问候闲聊）
    └─ 否 ↓
        ↓
是否包含"完整/详细/系统"或"X周"？
    ├─ 是 → complete_training_plan（完整训练计划）
    └─ 否 ↓
        ↓
是否同时提到训练和营养？
    ├─ 是 → comprehensive_fitness（综合健身方案）
    └─ 否 ↓
        ↓
是否只提到营养/饮食？
    ├─ 是 → nutrition_planning（营养规划）
    └─ 否 ↓
        ↓
是否只提到安全/禁忌/风险？
    ├─ 是 → safety_assessment（安全评估）
    └─ 否 ↓
        ↓
是否只提到动作推荐/替代？
    ├─ 是 → exercise_optimization（动作优化）
    └─ 否 ↓
        ↓
是否提到康复/伤后恢复？
    ├─ 是 → rehabilitation_training（康复训练）
    └─ 否 ↓
        ↓
是否提到进展/分析/效果？
    ├─ 是 → progress_analysis（进展分析）
    └─ 否 ↓
        ↓
默认 → quick_consultation（快速咨询）
```

---

## 9个模板详解

### 1. 问候闲聊 (greeting)

**模板ID**: `greeting`  
**复杂度**: ⭐ (1秒)  
**类别**: QUICK

#### 适用场景

- 用户只是打招呼、问候
- 简单闲聊，不涉及具体健身问题
- 测试系统是否在线

#### 关键词

```
你好、早上好、晚上好、hi、hello、嗨、在吗
```

#### 示例查询

✅ **适合使用此模板**：
- "你好"
- "早上好"
- "在吗"
- "hi"

❌ **不适合使用此模板**：
- "你好，我想制定训练计划"（应选择complete_training_plan）
- "早上好，今天吃什么"（应选择nutrition_planning）

#### 响应特点

- 简短友好，1-2句话
- 不提供训练建议
- 引导用户提出具体问题

---

### 2. 完整训练计划 (complete_training_plan)

**模板ID**: `complete_training_plan`  
**复杂度**: ⭐⭐⭐ (15秒)  
**类别**: COMPREHENSIVE

#### 适用场景

- 制定系统的、详细的训练方案
- 包含动作选择、训练量计算、周期化安排
- 用户明确要求"完整"、"详细"、"系统"的计划
- 用户指定训练周期（如4周、8周、12周）

#### 关键词

**高权重关键词**（权重×2）：
```
完整、详细、系统、全面、4周、8周、12周、训练计划、增肌计划、力量计划
```

**中权重关键词**（权重×1.5）：
```
制定、设计、帮我、给我、想要
```

#### 示例查询

✅ **适合使用此模板**（置信度>0.85）：
- "帮我设计一个完整的4周增肌训练计划"
- "我想制定一个详细的力量训练计划"
- "给我一个系统的增肌方案"
- "我需要一个12周的训练计划"

⚠️ **中等置信度**（0.70-0.85）：
- "帮我设计增肌训练"（缺少"完整/详细/系统"）
- "我想练胸"（太简单，应选择exercise_optimization）

❌ **不适合使用此模板**：
- "推荐几个胸部动作"（应选择exercise_optimization）
- "我今天吃什么"（应选择nutrition_planning）

#### 工具链

**必需工具**（6个）：
1. get_user_profile - 获取用户档案
2. contraindications_checker - 禁忌症检查
3. injury_risk_assessor - 损伤风险评估
4. intelligent_exercise_selector - 智能动作选择
5. muscle_group_volume_calculator - 训练量计算
6. professional_program_designer - 专业计划设计

**可选工具**（3个）：
7. movement_pattern_balancer - 动作模式平衡
8. periodized_program_designer - 周期化设计
9. training_split_designer - 训练分化设计

#### 响应特点

- 详细专业，300-500字
- 提供完整的训练计划
- 包含动作选择、组数次数、训练量分配
- 包含周期化安排和训练分化建议

---

### 3. 营养规划 (nutrition_planning)

**模板ID**: `nutrition_planning`  
**复杂度**: ⭐⭐ (10秒)  
**类别**: NUTRITION

#### 适用场景

- 制定营养方案、膳食计划
- 关注饮食、营养摄入
- 计算TDEE和宏量营养素

#### 关键词

```
营养、饮食、吃什么、膳食、食物、热量、蛋白质、碳水
```

#### 示例查询

✅ **适合使用此模板**：
- "我应该吃什么来增肌"
- "帮我制定营养计划"
- "我的TDEE是多少"
- "增肌期间怎么吃"

❌ **不适合使用此模板**：
- "我想练胸"（应选择exercise_optimization）
- "帮我设计完整的训练和营养方案"（应选择comprehensive_fitness）

#### 工具链

**必需工具**（4个）：
1. get_user_profile - 获取用户档案
2. tdee_calculator - TDEE计算
3. nutrition_intake_analyzer - 营养摄入分析
4. meal_plan_designer - 膳食计划设计

**可选工具**（1个）：
5. exercise_nutrition_optimization - 运动营养优化

#### 响应特点

- 专业详细，200-400字
- 提供TDEE计算结果
- 提供宏量营养素分配建议
- 提供膳食计划建议

---

### 4. 安全评估 (safety_assessment)

**模板ID**: `safety_assessment`  
**复杂度**: ⭐⭐ (8秒)  
**类别**: SAFETY

#### 适用场景

- 评估运动安全性
- 识别风险和禁忌
- 检查动作是否适合用户

#### 关键词

```
安全、禁忌、风险、能否、可以做、不能做、危险
```

#### 示例查询

✅ **适合使用此模板**：
- "我能做深蹲吗"
- "这个动作有风险吗"
- "我有腰伤，哪些动作不能做"
- "检查一下我的训练安全性"

❌ **不适合使用此模板**：
- "推荐几个安全的动作"（应选择exercise_optimization）
- "我想制定康复计划"（应选择rehabilitation_training）

#### 工具链

**必需工具**（3个）：
1. get_user_profile - 获取用户档案
2. contraindications_checker - 禁忌症检查
3. injury_risk_assessor - 损伤风险评估

**可选工具**（2个）：
4. safe_exercise_modifier - 安全动作调整
5. exercise_alternative_finder - 替代动作查找

#### 响应特点

- 专业严谨，150-300字
- 重点说明安全风险和禁忌事项
- 提供具体的安全建议
- 提供替代方案

---

### 5. 动作优化 (exercise_optimization)

**模板ID**: `exercise_optimization`  
**复杂度**: ⭐ (6秒)  
**类别**: TRAINING

#### 适用场景

- 动作推荐、替代方案
- 动作调整和优化
- 查找特定肌肉群的动作

#### 关键词

```
动作、替代、换、推荐、选择、哪些动作
```

#### 示例查询

✅ **适合使用此模板**：
- "推荐几个胸部动作"
- "深蹲的替代动作有哪些"
- "我想换一个背部动作"
- "哪些动作练肩"

❌ **不适合使用此模板**：
- "帮我设计完整的训练计划"（应选择complete_training_plan）
- "这个动作安全吗"（应选择safety_assessment）

#### 工具链

**必需工具**（3个）：
1. get_user_profile - 获取用户档案
2. intelligent_exercise_selector - 智能动作选择
3. exercise_alternative_finder - 替代动作查找

**可选工具**（4个）：
4. contraindications_checker - 禁忌症检查
5. safe_exercise_modifier - 安全动作调整
6. movement_pattern_balancer - 动作模式平衡
7. intelligent_weight_calculator - 智能重量计算

#### 响应特点

- 简洁实用，100-200字
- 重点推荐2-3个动作
- 说明选择理由和执行要点
- 提供替代方案

---

### 6. 综合健身方案 (comprehensive_fitness)

**模板ID**: `comprehensive_fitness`  
**复杂度**: ⭐⭐⭐ (20秒)  
**类别**: COMPREHENSIVE

#### 适用场景

- 需要训练+营养的完整解决方案
- 系统性的健身指导
- 同时关注训练和饮食

#### 关键词

```
综合、全面、完整方案、系统方案、训练和营养
```

#### 示例查询

✅ **适合使用此模板**：
- "帮我制定综合健身方案"
- "我想要训练和营养的完整计划"
- "全面的增肌方案"
- "系统的健身指导"

❌ **不适合使用此模板**：
- "只要训练计划"（应选择complete_training_plan）
- "只要营养计划"（应选择nutrition_planning）

#### 工具链

**必需工具**（8个）：
1. get_user_profile
2. contraindications_checker
3. injury_risk_assessor
4. intelligent_exercise_selector
5. muscle_group_volume_calculator
6. professional_program_designer
7. tdee_calculator
8. meal_plan_designer

**可选工具**（3个）：
9. periodized_program_designer
10. training_split_designer
11. exercise_nutrition_optimization

#### 响应特点

- 全面系统，500-800字
- 提供训练和营养的完整方案
- 包含安全评估、训练计划、营养计划
- 包含周期化安排

---

### 7. 快速咨询 (quick_consultation)

**模板ID**: `quick_consultation`  
**复杂度**: ⭐ (2秒)  
**类别**: QUICK

#### 适用场景

- 简单的、一般性的健身问题
- 不需要复杂的工具链
- 快速回答基础问题

#### 关键词

```
简单问题、快速咨询、基础问题、一般咨询
```

#### 示例查询

✅ **适合使用此模板**：
- "什么是TDEE"
- "增肌和减脂的区别"
- "训练后要拉伸吗"
- "蛋白质摄入量怎么算"

⚠️ **重要约束**：
- 如果用户明确要求"完整"、"详细"、"系统"的计划，绝对不要选择此模板
- 仅当查询非常简单且不涉及具体计划时选择

❌ **不适合使用此模板**：
- "帮我设计完整的训练计划"（应选择complete_training_plan）
- "推荐几个胸部动作"（应选择exercise_optimization）

#### 工具链

**必需工具**（1个）：
1. get_user_profile - 获取用户档案

#### 响应特点

- 简洁明了，100-200字
- 直接回答用户问题
- 提供实用建议
- 2-3段话

---

### 8. 进展分析 (progress_analysis)

**模板ID**: `progress_analysis`  
**复杂度**: ⭐⭐ (8秒)  
**类别**: TRAINING

#### 适用场景

- 分析训练进展
- 数据分析和效果评估
- 优化训练方案

#### 关键词

```
进展、分析、效果、数据、进度、评估
```

#### 示例查询

✅ **适合使用此模板**：
- "分析一下我的训练进展"
- "我的训练效果怎么样"
- "评估一下我的数据"
- "我的进度如何"

❌ **不适合使用此模板**：
- "帮我制定训练计划"（应选择complete_training_plan）
- "推荐几个动作"（应选择exercise_optimization）

#### 工具链

**必需工具**（2个）：
1. get_user_profile - 获取用户档案
2. muscle_group_volume_calculator - 训练量计算

**可选工具**（1个）：
3. periodized_program_designer - 周期化设计

#### 响应特点

- 数据驱动，200-300字
- 分析训练进展和效果
- 指出优化方向
- 提供具体的改进建议

---

### 9. 康复训练 (rehabilitation_training)

**模板ID**: `rehabilitation_training`  
**复杂度**: ⭐⭐⭐ (12秒)  
**类别**: SAFETY

#### 适用场景

- 有伤病史的用户
- 需要安全的康复训练方案
- 伤后恢复训练

#### 关键词

```
康复、伤后、恢复、受伤、伤病
```

#### 示例查询

✅ **适合使用此模板**：
- "我腰伤了，怎么康复训练"
- "伤后恢复训练计划"
- "膝盖受伤后怎么练"
- "康复期间的训练方案"

❌ **不适合使用此模板**：
- "我能做深蹲吗"（应选择safety_assessment）
- "推荐几个安全的动作"（应选择exercise_optimization）

#### 工具链

**必需工具**（4个）：
1. get_user_profile
2. contraindications_checker
3. injury_risk_assessor
4. safe_exercise_modifier

**可选工具**（3个）：
5. exercise_alternative_finder
6. intelligent_exercise_selector
7. movement_pattern_balancer

#### 响应特点

- 谨慎专业，300-400字
- 重点强调安全性和循序渐进
- 提供详细的康复训练计划
- 提供注意事项

---

## 配置示例

### 手动指定模板

如果需要手动指定模板（调试或测试），可以在请求中指定：

```python
# API请求
POST /api/chat/stream
{
  "query": "推荐几个胸部动作",
  "user_id": "user_123",
  "force_template": "exercise_optimization"  # 强制使用指定模板
}
```

### 查看选择结果

系统会在响应中返回模板选择信息：

```json
{
  "selected_template_id": "complete_training_plan",
  "selection_reason": "用户要求制定完整的增肌训练计划",
  "confidence": 0.95,
  "matched_keywords": ["完整", "训练计划", "增肌"],
  "alternative_templates": ["comprehensive_fitness"]
}
```

---

## 常见问题

### Q1: 如何提高模板选择的准确性？

**A**: 在查询中使用明确的关键词：
- 使用"完整"、"详细"、"系统"表示需要完整计划
- 使用"X周"（如4周、8周）表示需要周期化计划
- 明确说明是训练、营养还是两者都要
- 说明具体的健身目标（增肌、减脂、力量）

### Q2: 为什么我的查询被选择为quick_consultation？

**A**: 可能的原因：
- 查询太简单，没有明确的关键词
- 没有说明需要"完整"或"详细"的计划
- 查询不涉及具体的训练或营养计划

**解决方案**：
- 添加"完整"、"详细"、"系统"等关键词
- 明确说明需要什么类型的计划
- 提供更多上下文信息

### Q3: 如何查看模板选择的置信度？

**A**: 在API响应中查看`confidence`字段：
- 0.9-1.0：高置信度，选择非常确定
- 0.7-0.9：中等置信度，选择较为确定
- 0.5-0.7：低置信度，可能需要人工确认
- <0.5：非常低置信度，建议使用降级策略

### Q4: 模板选择失败时会怎样？

**A**: 系统有完善的降级策略：
1. **LLM选择失败**：使用基于规则的关键词匹配
2. **关键词匹配失败**：默认选择quick_consultation
3. **所有策略失败**：返回错误信息，提示用户重新提问

### Q5: 可以同时使用多个模板吗？

**A**: 不可以。每次查询只能选择一个模板。如果需要多个功能，建议：
- 使用comprehensive_fitness模板（包含训练和营养）
- 分多次查询，每次专注一个主题
- 在查询中明确说明需要"综合方案"

---

## 最佳实践

### 1. 查询优化

✅ **明确关键词**：使用"完整"、"详细"、"系统"等关键词  
✅ **说明目标**：明确说明健身目标（增肌、减脂、力量）  
✅ **提供上下文**：说明训练水平、可用器械、时间安排  
✅ **具体问题**：避免过于宽泛的问题

### 2. 模板选择

✅ **信任系统**：LLM决策引擎通常能做出正确选择  
✅ **查看置信度**：关注置信度，低置信度时可能需要重新提问  
✅ **使用降级**：降级策略提供可靠的备选方案  
✅ **反馈改进**：提供反馈帮助改进选择算法

### 3. 错误处理

✅ **重新提问**：选择不准确时，重新提问并使用更明确的关键词  
✅ **手动指定**：调试时可以手动指定模板  
✅ **查看日志**：查看选择理由和匹配的关键词  
✅ **联系支持**：持续出现问题时联系技术支持

---

## 相关文档

- **DAG模板架构**: `../../02-核心架构/03-编排层/02-DAG模板架构.md`
- **DAG模板代码实现**: `../../03-代码参考/04-DAG模板实现/03-DAG模板代码实现.md`
- **LLM模板架构**: `../../02-核心架构/04-LLM层/03-LLM模板架构.md`
- **DAG模板开发指南**: `../01-快速上手/01-DAG模板开发指南.md`

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
