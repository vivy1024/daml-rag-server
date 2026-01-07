# LLM模板架构

**版本**: v1.0.0  
**创建日期**: 2025-12-22  
**状态**: ✅ 已完成

---

## 概述

LLM模板系统是DAML-RAG框架三段式架构中的两个关键LLM调用点：
1. **步骤6.5 - LLM决策模板**：LLM从DAG模板库中选择最合适的工作流程
2. **步骤10 - LLM分析模板**：LLM基于真实数据进行深度分析和综合

### 设计理念

**核心思想**：LLM做决策和综合，程序做执行

- ✅ **步骤6.5（决策）**：LLM理解意图，选择DAG方案，不直接调用工具
- ✅ **步骤7-9（执行）**：程序严格执行选定的DAG，保证数据真实性
- ✅ **步骤10（综合）**：LLM基于真实数据进行专业分析，生成个性化建议
- ❌ **避免的问题**：LLM直接调用工具导致的幻觉、虚假数据、不可控行为

### 架构优势

1. **防止幻觉**：LLM不直接生成数据，只基于真实数据进行分析
2. **可追溯性**：所有建议都有明确的数据来源和推理依据
3. **安全性**：禁忌动作和安全约束在提示词中强制执行
4. **个性化**：结合用户档案和工具结果生成定制化建议
5. **降级策略**：LLM调用失败时有可靠的降级方案

---

## 两大LLM模板

### 1. LLM决策模板（步骤6.5）

**职责**：从DAG模板库中选择最合适的工作流程

**输入**：
- 用户查询
- 用户档案
- 可用DAG模板列表
- Few-Shot示例（可选）

**输出**：
```json
{
  "selected_template_id": "complete_training_plan",
  "selection_reason": "用户要求制定完整的增肌训练计划",
  "expected_tools": ["get_user_profile", "contraindications_checker", ...],
  "confidence": 0.95,
  "alternative_templates": ["comprehensive_fitness"],
  "matched_keywords": ["完整", "训练计划", "增肌"]
}
```

**核心特性**：
- 结构化输出验证
- 关键词权重匹配
- 置信度评估
- 降级策略（规则匹配）

---

### 2. LLM分析模板（步骤10）

**职责**：基于真实数据进行深度分析和综合

**输入**：
- 用户查询
- 用户档案
- 工具执行结果（真实数据）
- 禁忌动作列表
- 安全约束

**输出**：
```python
AnalysisResult(
    professional_analysis="专业分析内容...",
    personalized_recommendations=["建议1", "建议2", "建议3"],
    safety_reminders=["安全提醒1", "安全提醒2"],
    reasoning_basis={"tool1": ["依据1", "依据2"], ...},
    confidence=0.85,
    model_used="deepseek-chat"
)
```

**核心特性**：
- 基于真实数据分析
- 强制安全约束
- 推理依据可追溯
- 个性化建议生成

---

## LLM决策模板详解

### 提示词结构

```
你是玉珍健身APP的专业AI助手。用户向你咨询健身问题，你需要选择最合适的工作流程来回答用户。

## 用户信息
- 年龄: 28岁
- 性别: 男
- 训练水平: intermediate
- 训练频率: 每周4次
- 健身目标: 增肌, 力量提升
- 健康状况: 无
- 损伤史: 无

## 用户查询
"我想制定一个完整的增肌训练计划"

## 可选的工作流程（DAG模板）

### 问候闲聊 (ID: greeting)
- **描述**: 友好回应用户的问候和简单闲聊
- **类别**: quick
- **适用场景**: 你好、早上好、晚上好、hi、hello、嗨、在吗
- **复杂度**: ⭐
- **预计耗时**: 1秒
- **必需工具**: 0个
- **可选工具**: 0个

### 完整训练计划 (ID: complete_training_plan) ⭐⭐⭐ 高权重
- **描述**: 为用户制定包含动作选择、训练量计算、周期化安排的完整训练计划
- **类别**: comprehensive
- **适用场景**: 制定训练计划、增肌计划、力量训练计划、完整训练方案、系统训练计划
- **复杂度**: ⭐⭐⭐
- **预计耗时**: 15秒
- **必需工具**: 6个
- **可选工具**: 3个

... (其他7个模板)

## 详细选择指南（请仔细阅读每个模板的定义和示例）

### 1. 问候闲聊 (greeting)
**定义**: 用户只是打招呼、问候或简单闲聊，不涉及具体的健身问题
**关键词**: 你好、早上好、晚上好、hi、hello、嗨、在吗
**示例查询**:
  - "你好"
  - "早上好"
  - "在吗"
**置信度要求**: 必须是明确的问候语才选择此模板（置信度>0.9）

### 2. 完整训练计划 (complete_training_plan) ⭐⭐⭐ 高权重
**定义**: 用户需要系统的、详细的训练方案，包含动作选择、训练量计算、周期化安排
**高权重关键词**: 完整、详细、系统、全面、4周、8周、12周、训练计划、增肌计划、减脂计划、力量计划
**中权重关键词**: 制定、设计、帮我、给我、想要
**示例查询**:
  - "帮我设计一个完整的4周增肌训练计划" ✅ 高置信度（0.95+）
  - "我想制定一个详细的力量训练计划" ✅ 高置信度（0.90+）
  - "给我一个系统的增肌方案" ✅ 高置信度（0.90+）
  - "我需要一个12周的训练计划" ✅ 高置信度（0.95+）
  - "帮我设计增肌训练" ✅ 中等置信度（0.75+）
**置信度要求**: 包含"完整/详细/系统"或"X周"时置信度应>0.85

... (其他7个模板的详细指南)

## 关键词权重规则（重要！）
1. **高权重关键词**（权重×2）: 完整、详细、系统、全面、4周、8周、12周、X周
2. **中权重关键词**（权重×1.5）: 制定、设计、帮我、给我、想要
3. **模板特定关键词**（权重×1）: 各模板定义中的关键词

## 决策流程
1. 首先检查是否包含高权重关键词
2. 如果包含"完整/详细/系统"或"X周"，强烈倾向于 complete_training_plan
3. 如果同时提到训练和营养，选择 comprehensive_fitness
4. 如果只提到营养/饮食，选择 nutrition_planning
5. 如果只提到安全/禁忌，选择 safety_assessment
6. 如果只提到动作推荐/替代，选择 exercise_optimization
7. 只有在查询非常简单且不涉及具体计划时，才选择 quick_consultation

## 输出格式（必须是有效的JSON）
{
  "selected_template_id": "模板ID（必须是上述9个之一）",
  "selection_reason": "选择理由（简洁明确，50字以内，说明匹配了哪些关键词）",
  "expected_tools": ["预期使用的工具列表"],
  "confidence": 0.95,
  "alternative_templates": ["备选模板ID1", "备选模板ID2"],
  "matched_keywords": ["匹配到的关键词列表"]
}

## 重要约束
- ❌ 绝对不要编造模板ID，必须从上述9个中选择
- ✅ 选择理由必须基于用户查询和用户档案
- ✅ 置信度必须真实反映你的判断
- ✅ 必须列出匹配到的关键词
- ⚠️ 如果用户明确要求"完整"、"详细"、"系统"的计划，置信度必须>0.85，且不要选择quick_consultation

请输出你的选择（只输出JSON，不要其他内容）：
```


### 关键词权重系统

**高权重关键词**（权重×2）：
- 完整、详细、系统、全面
- 4周、8周、12周、X周

**中权重关键词**（权重×1.5）：
- 制定、设计、帮我、给我、想要

**模板特定关键词**（权重×1）：
- 各模板定义中的关键词

### 降级策略

当LLM调用失败或选择无效时，使用基于规则的降级策略：

```python
# 规则1: 关键词匹配（按优先级排序）
keyword_mapping = {
    "complete_training_plan": ["完整", "详细", "系统", "4周", "8周", "12周"],
    "nutrition_planning": ["营养", "饮食", "膳食", "吃什么"],
    "safety_assessment": ["安全", "禁忌", "风险", "能否"],
    "exercise_optimization": ["动作", "替代", "换", "推荐动作"],
    ...
}

# 规则2: 默认选择（快速咨询）
if no_match:
    return "quick_consultation"
```

### 选择质量监控

```python
selection_stats = {
    "total_selections": 1000,
    "successful_selections": 920,
    "fallback_selections": 80,
    "average_confidence": 0.82,
    "success_rate": 0.92,
    "fallback_rate": 0.08
}
```

---

## LLM分析模板详解

### 提示词结构

```
你是一位专业的健身教练和运动科学专家。你的任务是基于真实的工具执行结果，为用户提供专业、个性化的健身指导。

## 🎯 你的核心任务

1. **专业分析**: 基于提供的真实数据进行深度分析，而不仅仅是翻译数据
2. **个性化建议**: 结合用户档案和健身目标，生成具体可行的建议
3. **安全第一**: 必须强调安全约束和禁忌项，确保用户安全
4. **推理依据**: 所有建议都必须基于提供的真实数据，并说明依据

## ⚠️ 重要约束条件

1. ❌ **绝对禁止推荐禁忌动作** - 如果提供了禁忌动作列表，这些动作绝对不能出现在你的建议中
2. ✅ **必须基于真实数据** - 所有建议必须来自工具执行结果，不要编造或推测
3. ✅ **数据不足时明确告知** - 如果数据不足以回答问题，明确告知用户而不是猜测
4. ✅ **提供推理依据** - 每个建议都要说明来源（来自哪个工具的哪个数据）

## 👤 用户档案

**基本信息：**
- 年龄: 28岁
- 性别: 男
- 体重: 75kg
- 身高: 175cm

**健身配置：**
- 训练水平: intermediate
- 训练频率: 每周4次
- 可用器械: 哑铃, 杠铃, 史密斯机

**健身目标：**
- 主要目标: 增肌
- 次要目标: 力量提升

**健康状况：**
- 损伤史: 无
- 健康状况: 无

## ⚠️ 禁忌动作列表（用户健康原因，严禁推荐）

**以下动作绝对不能推荐给用户：**

1. ❌ **颈后深蹲** - 原因: 颈椎压力过大
2. ❌ **直腿硬拉** - 原因: 腰椎损伤风险
3. ❌ **颈后推举** - 原因: 肩关节不稳定
... (最多显示15个)

## 🔧 工具执行结果（真实数据）

### get_user_profile

- **user_id**: 123
- **fitness_level**: intermediate
- **training_days_per_week**: 4
- **fitness_goals**: ["增肌", "力量提升"]
- **available_equipment**: ["哑铃", "杠铃", "史密斯机"]

### contraindications_checker

共 3 项：
1. 颈后深蹲
2. 直腿硬拉
3. 颈后推举

### intelligent_exercise_selector

共 8 项：
1. 杠铃卧推
2. 哑铃飞鸟
3. 上斜卧推
4. 双杠臂屈伸
5. 绳索夹胸
6. 俯卧撑
7. 史密斯卧推
8. 哑铃卧推

### professional_program_designer

**program:**
```json
{
  "program_name": "4周增肌训练计划",
  "duration_weeks": 4,
  "training_days_per_week": 4,
  "split_type": "upper_lower",
  "weekly_schedule": [
    {
      "day": 1,
      "focus": "上肢推",
      "exercises": [...]
    },
    ...
  ]
}
```

## 🛡️ 安全约束

- 必须执行contraindications_checker
- 必须执行injury_risk_assessor
- 禁忌动作必须从推荐中排除

## 📋 输出要求

请按照以下结构输出你的分析：

### 1. 专业分析
基于工具结果进行深度分析，包括：
- 用户当前状况评估
- 训练计划的科学性分析
- 营养搭配的合理性分析
- 潜在风险评估

### 2. 个性化建议
提供3-5条具体可行的建议，每条建议必须：
- 明确具体（不要泛泛而谈）
- 基于真实数据
- 说明推理依据

### 3. 安全提醒
强调必须注意的安全事项，特别是：
- 禁忌动作提醒
- 健康状况相关注意事项
- 训练强度控制建议

### 4. 推理依据
说明你的建议来自哪些工具的哪些数据，确保可追溯。

---

**记住：你的所有建议都必须基于上述真实数据，不要编造或推测！**
```

### 输出解析

**专业分析提取**：
```python
professional_analysis = self._extract_section(
    llm_output,
    ["专业分析", "### 1. 专业分析", "## 专业分析"]
)
```

**个性化建议提取**：
```python
recommendations_text = self._extract_section(
    llm_output,
    ["个性化建议", "### 2. 个性化建议", "## 个性化建议"]
)
personalized_recommendations = self._parse_recommendations(recommendations_text)
```

**安全提醒提取**：
```python
safety_text = self._extract_section(
    llm_output,
    ["安全提醒", "### 3. 安全提醒", "## 安全提醒"]
)
safety_reminders = self._parse_safety_reminders(safety_text)
```

**推理依据提取**：
```python
reasoning_text = self._extract_section(
    llm_output,
    ["推理依据", "### 4. 推理依据", "## 推理依据"]
)
reasoning_basis = self._parse_reasoning_basis(reasoning_text)
```

### 置信度计算

```python
def _calculate_confidence(
    professional_analysis: str,
    recommendations: List[str],
    safety_reminders: List[str],
    reasoning_basis: Dict[str, List[str]]
) -> float:
    """计算分析结果的置信度"""
    confidence = 0.0
    
    # 专业分析存在且有内容 (+0.3)
    if professional_analysis and len(professional_analysis) > 100:
        confidence += 0.3
    
    # 建议数量合理 (+0.3)
    if 3 <= len(recommendations) <= 7:
        confidence += 0.3
    elif len(recommendations) > 0:
        confidence += 0.15
    
    # 安全提醒存在 (+0.2)
    if len(safety_reminders) > 0:
        confidence += 0.2
    
    # 推理依据完整 (+0.2)
    if len(reasoning_basis) > 0:
        confidence += 0.2
    
    return min(confidence, 1.0)
```

### 降级策略

当LLM调用失败时，返回降级响应：

```python
def _create_fallback_response(
    request: AnalysisRequest,
    error_message: str
) -> AnalysisResult:
    """创建降级响应"""
    return AnalysisResult(
        professional_analysis=f"抱歉，分析过程中出现了错误：{error_message}。请稍后重试。",
        personalized_recommendations=[
            "建议咨询专业健身教练获取个性化指导",
            "确保训练前进行充分热身",
            "注意倾听身体信号，避免过度训练"
        ],
        safety_reminders=[
            "如有任何不适，请立即停止训练并咨询医生",
            "遵循渐进式训练原则，不要急于求成"
        ],
        reasoning_basis={
            "error": [error_message]
        },
        confidence=0.0,
        model_used="fallback"
    )
```

---

## LLM调用策略

### 模型选择

**教师模型（DeepSeek）**：
- 用于复杂查询（BGE分类为复杂）
- 用于高相似度查询（相似度≥0.7）
- 提供更准确的分析和建议

**学生模型（Ollama）**：
- 用于简单查询
- 用于低相似度查询
- 提供快速响应

### 降级管理

使用`LLMFallbackManager`进行自动降级：

```python
# 降级策略：DeepSeek → Ollama → Template
fallback_manager = LLMFallbackManager(
    primary_backend="deepseek",
    fallback_backends=["ollama", "template"],
    max_retries=3,
    timeout=30,
    enable_health_check=True
)

# 调用LLM（自动降级）
llm_response = await fallback_manager.call_with_fallback(llm_request)
```

### 超时控制

**步骤6.5（决策）**：
- 超时时间：10秒
- 降级策略：规则匹配

**步骤10（分析）**：
- 超时时间：30秒
- 降级策略：降级响应

---

## 性能优化

### 1. 缓存策略

**步骤6.5（决策）**：
- 缓存键：基于查询文本的哈希
- TTL：1小时（相同查询的选择结果可以缓存较长时间）
- 缓存层级：L1（内存）+ L2（Redis）

**步骤10（分析）**：
- 不缓存（每次分析都基于最新的工具结果）

### 2. 并行执行

**步骤6.5与步骤7并行**：
- 步骤6.5：LLM选择DAG模板
- 步骤7：DAG编排器准备执行图
- 并行执行可减少总耗时

### 3. Token优化

**步骤6.5（决策）**：
- max_tokens：1000（选择结果较短）
- temperature：0.3（较低温度以获得更确定的选择）

**步骤10（分析）**：
- max_tokens：3000（分析需要更多token）
- temperature：0.7（较高温度以获得更自然的表达）

---

## 监控和统计

### 决策质量监控

```python
selection_stats = {
    "total_selections": 1000,
    "successful_selections": 920,
    "fallback_selections": 80,
    "average_confidence": 0.82,
    "success_rate": 0.92,
    "fallback_rate": 0.08,
    "by_template": {
        "complete_training_plan": 350,
        "nutrition_planning": 200,
        "exercise_optimization": 180,
        "quick_consultation": 150,
        ...
    }
}
```

### 分析质量监控

```python
analysis_stats = {
    "total_analyses": 1000,
    "successful_analyses": 950,
    "fallback_analyses": 50,
    "average_confidence": 0.75,
    "average_recommendations": 4.2,
    "average_safety_reminders": 2.8,
    "model_usage": {
        "deepseek-chat": 600,
        "ollama-qwen2.5": 350,
        "fallback": 50
    }
}
```

### 性能指标

```python
performance_metrics = {
    "step_6_5_avg_duration_ms": 2500,
    "step_6_5_p95_duration_ms": 4000,
    "step_6_5_p99_duration_ms": 6000,
    "step_10_avg_duration_ms": 3500,
    "step_10_p95_duration_ms": 5500,
    "step_10_p99_duration_ms": 8000
}
```

---

## 最佳实践

### 1. 提示词设计原则

✅ **明确任务**：清晰定义LLM的职责和输出格式  
✅ **强制约束**：使用强调标记（❌ ✅ ⚠️）突出重要约束  
✅ **提供示例**：包含详细的示例和指南  
✅ **结构化输出**：要求JSON格式或特定章节结构  
✅ **降级策略**：提供明确的降级规则

### 2. 安全约束原则

✅ **禁忌优先**：禁忌动作列表放在提示词最前面  
✅ **重复强调**：在多个地方强调安全约束  
✅ **明确标记**：使用❌标记禁忌动作  
✅ **提供理由**：说明为什么禁忌  
✅ **验证输出**：检查输出中是否包含禁忌动作

### 3. 数据真实性原则

✅ **数据来源**：明确标注数据来自哪个工具  
✅ **推理依据**：要求LLM说明建议的数据来源  
✅ **避免编造**：明确禁止LLM编造或推测数据  
✅ **数据不足**：数据不足时明确告知用户  
✅ **可追溯性**：所有建议都可以追溯到具体数据

### 4. 性能优化原则

✅ **缓存决策**：缓存步骤6.5的选择结果  
✅ **并行执行**：步骤6.5与步骤7并行  
✅ **超时控制**：设置合理的超时时间  
✅ **降级快速**：降级策略响应快速  
✅ **监控质量**：持续监控LLM输出质量

---

## 相关文档

- **DAG模板架构**: `../03-编排层/02-DAG模板架构.md`
- **智能模型选择架构**: `01-智能模型选择架构.md`
- **Few-Shot检索架构**: `02-Few-Shot检索架构.md`
- **LLM客户端实现**: `../../03-代码参考/02-核心组件/02-LLM客户端.md`
- **LLM响应优化使用指南**: `../../04-开发指南/03-配置管理/02-LLM响应配置管理器使用指南.md`

---

**维护者**: 薛小川  
**最后更新**: 2025-12-22
