# LLM模板配置指南

**版本**: v1.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

本指南说明如何配置和优化DAML-RAG系统中的两大LLM模板：
1. **LLM决策模板（步骤6.5）**：从DAG模板库中选择最合适的工作流程
2. **LLM分析模板（步骤10）**：基于真实数据进行深度分析和综合

### 配置目标

- ✅ **提高选择准确性**：优化决策模板的关键词和权重
- ✅ **提升分析质量**：优化分析模板的提示词结构
- ✅ **控制Token消耗**：合理设置max_tokens和temperature
- ✅ **优化响应速度**：选择合适的模型和超时时间
- ✅ **降低成本**：平衡质量和成本

---

## 配置文件位置

```
daml-rag-server/
├── config/
│   ├── llm_response_config.yaml      # LLM响应配置
│   └── performance_optimization.yaml  # 性能优化配置
├── src/
│   └── framework/
│       └── llm/
│           ├── llm_decision_engine.py    # 决策引擎
│           └── llm_analysis_engine.py    # 分析引擎
```

---

## LLM决策模板配置

### 配置文件

**文件路径**: `config/llm_response_config.yaml`

```yaml
# LLM决策模板配置（步骤6.5）
llm_decision:
  # 模型选择
  model:
    primary: "deepseek-chat"
    fallback: "ollama-qwen2.5"
  
  # Token配置
  tokens:
    max_tokens: 1000
    temperature: 0.3
  
  # 超时配置
  timeout:
    seconds: 10
  
  # 关键词权重
  keyword_weights:
    high_weight: 2.0      # 完整、详细、系统、X周
    medium_weight: 1.5    # 制定、设计、帮我、给我
    normal_weight: 1.0    # 模板特定关键词
  
  # 置信度阈值
  confidence:
    high: 0.85
    medium: 0.70
    low: 0.50
  
  # 降级策略
  fallback:
    enabled: true
    use_rule_matching: true
    default_template: "quick_consultation"
```

### 关键词配置

**高权重关键词**（权重×2）：

```python
HIGH_WEIGHT_KEYWORDS = [
    "完整", "详细", "系统", "全面",
    "4周", "8周", "12周", "周期"
]
```

**中权重关键词**（权重×1.5）：

```python
MEDIUM_WEIGHT_KEYWORDS = [
    "制定", "设计", "帮我", "给我", "想要"
]
```

**模板特定关键词**（权重×1）：

```python
TEMPLATE_KEYWORDS = {
    "complete_training_plan": [
        "训练计划", "增肌计划", "力量计划", "减脂计划"
    ],
    "nutrition_planning": [
        "营养", "饮食", "膳食", "吃什么", "热量"
    ],
    "safety_assessment": [
        "安全", "禁忌", "风险", "能否", "可以做"
    ],
    # ... 其他模板
}
```

### 提示词优化

**优化方向**：
1. **明确任务**：清晰定义LLM的职责
2. **强制约束**：使用强调标记（❌ ✅ ⚠️）
3. **提供示例**：包含详细的示例和指南
4. **结构化输出**：要求JSON格式输出

**示例提示词结构**：

```
你是玉珍健身APP的专业AI助手。用户向你咨询健身问题，你需要选择最合适的工作流程来回答用户。

## 用户信息
[用户档案]

## 用户查询
[用户查询]

## 可选的工作流程（DAG模板）
[9个模板的详细说明]

## 详细选择指南（请仔细阅读每个模板的定义和示例）
[每个模板的定义、关键词、示例查询、置信度要求]

## 关键词权重规则（重要！）
[高权重、中权重、模板特定关键词]

## 决策流程
[决策步骤]

## 输出格式（必须是有效的JSON）
{
  "selected_template_id": "模板ID",
  "selection_reason": "选择理由",
  "expected_tools": ["工具列表"],
  "confidence": 0.95,
  "alternative_templates": ["备选模板"],
  "matched_keywords": ["匹配的关键词"]
}

## 重要约束
- ❌ 绝对不要编造模板ID
- ✅ 选择理由必须基于用户查询
- ✅ 置信度必须真实反映判断
```

### 调优建议

#### 1. 提高选择准确性

**问题**：选择不准确，经常选错模板

**解决方案**：
```yaml
# 增加高权重关键词的权重
keyword_weights:
  high_weight: 2.5  # 从2.0增加到2.5

# 提高置信度阈值
confidence:
  high: 0.90  # 从0.85提高到0.90
```

**效果**：
- 高权重关键词的影响力增强
- 只有高置信度的选择才会被采纳
- 降低误选率

#### 2. 降低Token消耗

**问题**：Token消耗过高

**解决方案**：
```yaml
# 减少max_tokens
tokens:
  max_tokens: 800  # 从1000减少到800

# 简化提示词
# 移除不必要的示例和说明
```

**效果**：
- Token消耗降低20%
- 响应速度提升
- 成本降低

#### 3. 提升响应速度

**问题**：响应速度慢

**解决方案**：
```yaml
# 使用更快的模型
model:
  primary: "ollama-qwen2.5"  # 本地模型更快

# 减少超时时间
timeout:
  seconds: 5  # 从10秒减少到5秒
```

**效果**：
- 响应速度提升50%
- 用户体验改善

---

## LLM分析模板配置

### 配置文件

**文件路径**: `config/llm_response_config.yaml`

```yaml
# LLM分析模板配置（步骤10）
llm_analysis:
  # 模型选择
  model:
    primary: "deepseek-chat"
    fallback: "ollama-qwen2.5"
  
  # Token配置
  tokens:
    max_tokens: 3000
    temperature: 0.7
  
  # 超时配置
  timeout:
    seconds: 30
  
  # 输出格式
  output:
    sections:
      - "专业分析"
      - "个性化建议"
      - "安全提醒"
      - "推理依据"
    min_recommendations: 3
    max_recommendations: 7
  
  # 安全约束
  safety:
    enforce_contraindications: true
    max_contraindications_display: 15
    highlight_safety: true
  
  # 降级策略
  fallback:
    enabled: true
    use_template_response: true
```

### 提示词优化

**优化方向**：
1. **专业分析**：基于真实数据进行深度分析
2. **个性化建议**：结合用户档案生成定制化建议
3. **安全第一**：强调安全约束和禁忌项
4. **推理依据**：所有建议都有明确的数据来源

**示例提示词结构**：

```
你是一位专业的健身教练和运动科学专家。你的任务是基于真实的工具执行结果，为用户提供专业、个性化的健身指导。

## 🎯 你的核心任务
1. **专业分析**: 基于提供的真实数据进行深度分析
2. **个性化建议**: 结合用户档案和健身目标
3. **安全第一**: 必须强调安全约束和禁忌项
4. **推理依据**: 所有建议都必须基于提供的真实数据

## ⚠️ 重要约束条件
1. ❌ **绝对禁止推荐禁忌动作**
2. ✅ **必须基于真实数据**
3. ✅ **数据不足时明确告知**
4. ✅ **提供推理依据**

## 👤 用户档案
[用户档案]

## ⚠️ 禁忌动作列表（严禁推荐）
[禁忌动作列表]

## 🔧 工具执行结果（真实数据）
[工具结果]

## 🛡️ 安全约束
[安全约束]

## 📋 输出要求
### 1. 专业分析
[分析要求]

### 2. 个性化建议
[建议要求]

### 3. 安全提醒
[安全提醒要求]

### 4. 推理依据
[推理依据要求]

---
**记住：你的所有建议都必须基于上述真实数据，不要编造或推测！**
```

### 调优建议

#### 1. 提升分析质量

**问题**：分析不够深入，建议泛泛而谈

**解决方案**：
```yaml
# 增加max_tokens
tokens:
  max_tokens: 4000  # 从3000增加到4000

# 提高temperature
tokens:
  temperature: 0.8  # 从0.7提高到0.8

# 优化提示词
# 添加更多分析示例
# 强调深度分析的重要性
```

**效果**：
- 分析更加深入和专业
- 建议更加具体和可行
- 用户满意度提升

#### 2. 强化安全约束

**问题**：偶尔推荐禁忌动作

**解决方案**：
```yaml
# 强化安全约束
safety:
  enforce_contraindications: true
  max_contraindications_display: 20  # 增加显示数量
  highlight_safety: true

# 优化提示词
# 在多个地方强调禁忌动作
# 使用❌标记突出显示
# 提供禁忌理由
```

**效果**：
- 禁忌动作推荐率降低到0
- 安全性大幅提升
- 用户信任度增强

#### 3. 优化推理依据

**问题**：推理依据不清晰

**解决方案**：
```yaml
# 要求明确的推理依据
output:
  sections:
    - "专业分析"
    - "个性化建议"
    - "安全提醒"
    - "推理依据"  # 必需章节

# 优化提示词
# 要求每个建议都说明来源
# 格式：建议 → 来自工具X的数据Y
```

**效果**：
- 推理依据清晰可追溯
- 用户信任度提升
- 便于调试和优化

---

## 模型选择策略

### 教师-学生模型

**策略**：根据查询复杂度选择模型

```yaml
# 智能模型选择
model_selection:
  # 教师模型（DeepSeek）
  teacher:
    model: "deepseek-chat"
    use_for:
      - complexity: "complex"
      - similarity: ">= 0.7"
    advantages:
      - "更准确的分析"
      - "更专业的建议"
      - "更好的推理能力"
  
  # 学生模型（Ollama）
  student:
    model: "ollama-qwen2.5"
    use_for:
      - complexity: "simple"
      - similarity: "< 0.7"
    advantages:
      - "更快的响应"
      - "更低的成本"
      - "本地部署"
```

### 降级策略

**策略**：DeepSeek → Ollama → Template

```yaml
# 降级管理
fallback:
  enabled: true
  strategy:
    - primary: "deepseek-chat"
    - fallback_1: "ollama-qwen2.5"
    - fallback_2: "template"
  
  # 降级条件
  conditions:
    - timeout: 30  # 超时30秒
    - error: "connection_error"  # 连接错误
    - error: "rate_limit"  # 速率限制
  
  # 重试配置
  retry:
    max_retries: 3
    retry_delay: 1  # 秒
```

---

## 性能监控

### 监控指标

```yaml
# 监控配置
monitoring:
  # 决策质量监控
  decision:
    metrics:
      - "total_selections"
      - "successful_selections"
      - "fallback_selections"
      - "average_confidence"
      - "success_rate"
    alerts:
      - metric: "success_rate"
        threshold: 0.90
        action: "notify"
  
  # 分析质量监控
  analysis:
    metrics:
      - "total_analyses"
      - "successful_analyses"
      - "fallback_analyses"
      - "average_confidence"
      - "average_recommendations"
    alerts:
      - metric: "average_confidence"
        threshold: 0.70
        action: "notify"
  
  # 性能监控
  performance:
    metrics:
      - "step_6_5_avg_duration_ms"
      - "step_6_5_p95_duration_ms"
      - "step_10_avg_duration_ms"
      - "step_10_p99_duration_ms"
    alerts:
      - metric: "step_6_5_p95_duration_ms"
        threshold: 5000
        action: "notify"
```

### 查看监控数据

```bash
# 查看Prometheus指标
curl http://localhost:9090/api/v1/query?query=llm_decision_duration_seconds

# 查看日志
docker exec fitness_daml_rag tail -f /app/logs/daml_rag.log | grep "LLM"

# 查看统计信息
curl http://localhost:8001/api/health/metrics/llm
```

---

## 常见问题

### Q1: 如何提高LLM决策的准确性？

**A**: 
1. 增加高权重关键词的权重
2. 提高置信度阈值
3. 优化提示词，添加更多示例
4. 使用更强大的模型（DeepSeek）

### Q2: 如何降低Token消耗？

**A**:
1. 减少max_tokens设置
2. 简化提示词，移除不必要的内容
3. 使用更小的模型（Ollama）
4. 启用缓存机制

### Q3: 如何提升响应速度？

**A**:
1. 使用本地模型（Ollama）
2. 减少超时时间
3. 启用并行执行
4. 优化提示词长度

### Q4: 如何确保不推荐禁忌动作？

**A**:
1. 在提示词中多次强调禁忌动作
2. 使用❌标记突出显示
3. 提供禁忌理由
4. 在输出验证中检查禁忌动作

### Q5: 如何调试LLM输出？

**A**:
1. 查看日志文件
2. 检查置信度分数
3. 查看匹配的关键词
4. 使用测试工具验证

---

## 最佳实践

### 1. 提示词设计

✅ **明确任务**：清晰定义LLM的职责和输出格式  
✅ **强制约束**：使用强调标记突出重要约束  
✅ **提供示例**：包含详细的示例和指南  
✅ **结构化输出**：要求JSON格式或特定章节结构

### 2. 安全约束

✅ **禁忌优先**：禁忌动作列表放在提示词最前面  
✅ **重复强调**：在多个地方强调安全约束  
✅ **明确标记**：使用❌标记禁忌动作  
✅ **验证输出**：检查输出中是否包含禁忌动作

### 3. 性能优化

✅ **缓存决策**：缓存步骤6.5的选择结果  
✅ **并行执行**：步骤6.5与步骤7并行  
✅ **超时控制**：设置合理的超时时间  
✅ **降级快速**：降级策略响应快速

### 4. 监控和维护

✅ **持续监控**：监控LLM输出质量和性能  
✅ **定期优化**：根据监控数据优化配置  
✅ **用户反馈**：收集用户反馈改进提示词  
✅ **A/B测试**：测试不同配置的效果

---

## 相关文档

- **LLM模板架构**: `../../02-核心架构/04-LLM层/03-LLM模板架构.md`
- **智能模型选择架构**: `../../02-核心架构/04-LLM层/01-智能模型选择架构.md`
- **LLM响应配置管理器使用指南**: `02-LLM响应配置管理器使用指南.md`
- **DAG模板选择指南**: `../02-工具使用/01-DAG模板选择指南.md`

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
