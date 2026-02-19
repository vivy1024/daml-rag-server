# DAML-Eval: 垂直领域LLM评估体系设计

> **分类**: 体系设计 | **日期**: 2026-02-20 | **作者**: 薛小川
> **状态**: 设计阶段 | **关联**: 多模型集成 spec (Batch 4)

## 1. 核心思想

传统LLM评估（MMLU、HumanEval等）测的是通用能力。但在健身垂直领域，"谁更懂训练计划"这个问题，通用benchmark回答不了。

DAML-Eval 的核心洞察：**利用 DAML-RAG 已有的三轨评分 + Few-Shot 准入机制，将生产环境的真实用户交互转化为垂直领域评估数据**。

```
用户提问 → 多模型生成回答 → 三轨评分(自动) → Few-Shot准入(自动)
                                    ↓
                            记录 backend_used
                                    ↓
                        大量样本积累后 → 统计分析
                                    ↓
                    各模型在健身领域的能力画像
```

与传统评估方法的区别：

| 维度 | 传统Benchmark | DAML-Eval |
|------|-------------|-----------|
| 数据来源 | 人工构造测试集 | 生产环境真实交互 |
| 评估维度 | 通用知识/推理 | 垂直领域专业性 |
| 评分方式 | 标准答案匹配 | 多维度自动评分 |
| 样本量 | 固定（数百~数千） | 持续增长 |
| 场景覆盖 | 预设场景 | 真实用户场景分布 |

## 2. 现有评估基础设施

### 2.1 三轨评分系统 (ThreeTrackRatingService)

位置: `services/three_track_rating.py`

当前4个评分维度：

| 维度 | 含义 | 计算方式 |
|------|------|---------|
| `profile_utilization_rate` | 档案利用率 | LLM回答中引用了多少用户档案字段 |
| `goal_alignment` | 目标对齐度 | 回答与用户健身目标的匹配程度 |
| `uniqueness` | 独特性 | 回答是否针对该用户定制（vs 通用模板） |
| `dynamic_adjustment` | 动态调整 | 是否根据用户当前状态做出调整 |

综合分 = 4维平均值，等级：S(90+) A(75+) B(60+) C(40+) D(0+)

### 2.2 Few-Shot 准入机制

- 准入阈值: `FEWSHOT_THRESHOLD = 4.0`（满分5.0）
- 冷启动阈值: `COLD_START_THRESHOLD = 3.5`
- 准入的回答进入 Qdrant 向量库，作为后续生成的参考示例
- 准入率本身就是一个强评估指标：**模型越好，准入率越高**

### 2.3 当前缺失

1. **不记录 backend_used** — 不知道哪个模型生成了哪个回答
2. **Few-Shot 无模型标签** — 准入的示例不知道来自哪个模型
3. **无聚合统计** — 没有按模型维度的统计分析能力

## 3. 评估维度扩展

### 3.1 从4维到7维

在现有4个个性化维度基础上，新增3个垂直领域关键维度：

| 新增维度 | 含义 | 为什么重要 |
|---------|------|-----------|
| `safety_compliance` | 安全合规性 | 健身建议不能造成运动损伤 |
| `scientific_accuracy` | 科学准确性 | 训练原理、营养知识是否正确 |
| `tool_efficiency` | 工具调用效率 | Agent模式下工具选择和调用的合理性 |

### 3.2 维度权重（按场景）

不同DAG模板场景下，各维度权重不同：

```
安全评估模板 (safety_assessment):
  safety_compliance: 0.35  ← 最重要
  scientific_accuracy: 0.25
  profile_utilization: 0.15
  goal_alignment: 0.15
  uniqueness: 0.05
  dynamic_adjustment: 0.05

训练计划模板 (complete_training_plan):
  goal_alignment: 0.25  ← 最重要
  profile_utilization: 0.20
  scientific_accuracy: 0.20
  dynamic_adjustment: 0.15
  uniqueness: 0.10
  safety_compliance: 0.10

快速咨询模板 (quick_consultation):
  scientific_accuracy: 0.30  ← 最重要
  goal_alignment: 0.25
  uniqueness: 0.20
  profile_utilization: 0.15
  safety_compliance: 0.10
```

### 3.3 安全合规性评分方法

```python
def _calculate_safety_compliance(response: str, user_profile: dict) -> float:
    """
    检查项:
    1. 是否包含运动禁忌提醒（有伤病史时）
    2. 是否建议热身/拉伸
    3. 是否有渐进性原则（不建议突然大幅增加强度）
    4. 是否考虑年龄/性别/体能水平限制
    5. 是否包含"如有不适请停止"类安全提示
    """
```

### 3.4 科学准确性评分方法

利用 Neo4j 知识图谱验证：
- 动作-肌肉关系是否正确（4,246节点可验证）
- 训练容量建议是否在合理范围
- 营养建议是否符合运动营养学原则

## 4. Shadow 模式（公平对比）

### 4.1 问题

生产环境中，不同模板用不同模型（L1用免费模型，L3用Anthropic），直接比较不公平——简单问题本来就容易得高分。

### 4.2 方案

Shadow 模式：对同一请求，同时调用多个模型，只返回主模型结果，但记录所有模型的评分。

```
用户请求 → 主模型(Anthropic) → 返回给用户 + 评分
         → Shadow(Qwen)      → 不返回，只评分
         → Shadow(SiliconFlow) → 不返回，只评分
```

### 4.3 实施约束

- Shadow 调用异步执行，不影响主请求延迟
- 采样率可配置（如 10% 的请求触发 Shadow）
- Shadow 结果只写日志/数据库，不影响用户体验
- 环境变量控制: `SHADOW_EVAL_ENABLED=false`, `SHADOW_EVAL_SAMPLE_RATE=0.1`

## 5. 标准测试集

### 5.1 为什么需要

生产数据有偏差（用户问题分布不均匀），需要标准测试集做基线对比。

### 5.2 构建方法

从现有 Few-Shot 库（Qdrant 4,585向量）中筛选：

```
1. 按13个DAG模板分类
2. 每个模板选取 10-20 个高分样本（三轨评分 ≥ 4.5）
3. 人工审核确认质量
4. 形成 130-260 条标准测试集
```

### 5.3 测试集格式

```json
{
  "test_id": "eval_001",
  "template_id": "complete_training_plan",
  "query": "我是25岁男性，体重75kg，想增肌，每周能练4天",
  "user_profile": { "age": 25, "gender": "male", "weight": 75, "goal": "muscle_gain" },
  "reference_response": "...(高分参考回答)",
  "reference_scores": {
    "profile_utilization_rate": 92,
    "goal_alignment": 88,
    "uniqueness": 85,
    "dynamic_adjustment": 80
  },
  "key_points": ["渐进超负荷", "分化训练", "蛋白质摄入建议"]
}
```

## 6. 统计方法

### 6.1 基础指标

| 指标 | 公式 | 含义 |
|------|------|------|
| Few-Shot 准入率 | 准入数 / 总调用数 | 模型生成高质量回答的比例 |
| 平均三轨评分 | Σ(综合分) / N | 模型在各维度的平均表现 |
| 评分标准差 | σ(综合分) | 模型输出的稳定性 |
| 场景覆盖率 | 有数据的模板数 / 13 | 模型在多少场景下被测试过 |

### 6.2 统计显著性

- 最小样本量: 每个模型每个模板至少 30 次调用
- 使用 Welch's t-test 比较两个模型的评分差异
- p < 0.05 才认为差异显著
- 报告 95% 置信区间

### 6.3 模型能力画像

最终输出每个模型的雷达图数据：

```json
{
  "model": "qwen-plus",
  "total_calls": 1250,
  "fewshot_admission_rate": 0.72,
  "avg_scores": {
    "profile_utilization_rate": 78.5,
    "goal_alignment": 82.1,
    "uniqueness": 65.3,
    "dynamic_adjustment": 71.8,
    "safety_compliance": 85.2,
    "scientific_accuracy": 79.6,
    "tool_efficiency": null
  },
  "best_templates": ["greeting", "quick_consultation"],
  "worst_templates": ["safety_assessment"],
  "cost_per_call_rmb": 0.003,
  "cost_effectiveness": 24.03
}
```

`cost_effectiveness` = `fewshot_admission_rate` / `cost_per_call_rmb`，衡量性价比。

## 7. 数据流设计

```
LLM调用
  ├→ LLMResponse.backend_used = "qwen"
  │
  ├→ stream_executor 记录到 llm_call_logger
  │     {request_id, template_id, backend_used, duration_ms}
  │
  ├→ ThreeTrackRatingService.calculate()
  │     接收 backend_used 参数
  │     评分结果关联模型信息
  │
  ├→ fewshot_eligible = (综合分 ≥ 4.0)
  │     FewShotExample.backend_model = "qwen-plus"
  │     存入 Qdrant 时携带 backend_model payload
  │
  └→ /internal/model-evaluation/stats
        聚合查询，按 backend_used 分组统计
```

## 8. API 端点设计

### GET /internal/model-evaluation/stats

```json
{
  "period": "2026-02-01 ~ 2026-02-20",
  "models": {
    "anthropic": {
      "total_calls": 3200,
      "fewshot_admission_rate": 0.81,
      "avg_score": 4.2,
      "by_template": {
        "complete_training_plan": {"calls": 450, "avg_score": 4.3, "admission_rate": 0.85},
        "quick_consultation": {"calls": 800, "avg_score": 4.1, "admission_rate": 0.78}
      }
    },
    "qwen": { "..." },
    "siliconflow": { "..." }
  },
  "comparison": {
    "best_overall": "anthropic",
    "best_cost_effective": "siliconflow",
    "insufficient_data": ["glm"]
  }
}
```

## 9. 实施路线

| 阶段 | 内容 | 前置条件 |
|------|------|---------|
| Phase 1 | `backend_used` 元数据传递 | 多模型集成 Batch 1-2 完成 |
| Phase 2 | Few-Shot 模型标签 + Qdrant payload | Phase 1 |
| Phase 3 | 评估统计服务 + API 端点 | Phase 2 |
| Phase 4 | Shadow 模式 | Phase 3 + 生产环境稳定 |
| Phase 5 | 标准测试集构建 | Phase 3 + 足够样本积累 |
| Phase 6 | 7维评分扩展 | Phase 5 + 评分方法验证 |

Phase 1-3 对应 multi-model-integration spec 的 Batch 4 (Tasks 7-9)。
Phase 4-6 是后续迭代，不在本次 spec 范围内。

## 10. 已知局限与改进方向

1. **评分者偏差**: 三轨评分本身由 LLM 执行，不同模型可能对自己的输出评分偏高 → 需要固定评分模型（如始终用 Anthropic 评分）
2. **时间衰减**: 模型会更新，历史评分可能不代表当前能力 → 需要按时间窗口统计
3. **样本偏差**: 简单模板调用量远大于复杂模板 → 统计时需按模板加权
4. **Tool Calling 评估**: 当前三轨评分不覆盖工具调用质量 → `tool_efficiency` 维度需要独立评估逻辑

> 注：三轨评分已包含用户、专家、个性化三个维度的评价，Few-Shot 准入本身就是一种多维度用户反馈筛选机制，不存在"用户反馈缺失"的问题。
