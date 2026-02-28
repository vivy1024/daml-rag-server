# FewShot工具实现

**版本**: v1.0.0
**创建日期**: 2026-02-28
**状态**: 已完成

---

## 概述

本文档详细说明与Few-Shot学习相关的系统组件，包括Few-Shot类型定义、检索器和相关服务。

**代码路径**: `daml-rag-server/src/applications/fitness/` 和 `daml-rag-server/src/framework/retrieval/`

---

## 1. Few-Shot类型定义

**文件路径**: `types/fewshot_types.py`

### 统一数据结构

```python
@dataclass
class UnifiedFewShotExample:
    """
    统一的Few-Shot示例数据结构

    与前端TypeScript定义保持一致，确保前后端数据结构统一。
    """
    # 基础信息
    id: str                                       # 唯一标识
    query: str                                    # 用户问题
    response: str                                 # 系统回复
    session_id: str                               # 会话ID
    user_id: Optional[str] = None                 # 用户ID（可选）

    # 工具和模型信息
    tools_used: List[str] = field(default_factory=list)  # 使用的工具列表
    model_used: str = ""                          # 使用的模型

    # 三轨评分
    user_rating: float = 0.0                      # 用户评分 (1-5)
    quality_score: float = 0.0                    # 质量评分 (0-5)
    similarity: float = 0.0                       # 相似度 (0-1)

    # 三轨评分详情
    three_track_scores: Optional[ThreeTrackScores] = None

    # 训练效果标签
    training_effect: Optional[str] = None

    # 用户反馈
    user_feedback: Optional[str] = None

    # 元数据
    metadata: FewShotMetadata = field(default_factory=FewShotMetadata)

    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)

    # Few-Shot资格
    fewshot_eligible: bool = False
```

### 训练效果标签

```python
class TrainingEffectLabel(str, Enum):
    """训练效果标签枚举"""
    EXCELLENT = "excellent"   # 优秀：训练效果显著，完全达到预期目标
    GOOD = "good"             # 良好：训练效果良好，基本达到预期目标
    FAIR = "fair"            # 一般：训练效果一般，部分达到预期目标
    POOR = "poor"            # 较差：训练效果不佳，未达到预期目标
```

### 三轨评分

```python
@dataclass
class ThreeTrackScores:
    """三轨评分详情"""
    user_experience_avg: Optional[float] = None    # 用户体验平均分
    personalization_avg: Optional[float] = None    # 个性化感知平均分
    expert_avg: Optional[float] = None             # 专家评分平均分（可选）
    safety_score: Optional[float] = None           # 安全性评分（可选）
```

---

## 2. 增强版Few-Shot检索器

**文件路径**: `framework/retrieval/enhanced_few_shot_retriever.py`

### 核心功能

1. **质量过滤**: 只检索高分历史对话
2. **动态相似度阈值**: 基于查询复杂度调整
3. **自动化程度提升**: 与模型选择策略集成
4. **多样性保证**: 确保检索结果的多样性

### 检索配置

```python
@dataclass
class FewShotConfig:
    """Few-Shot检索配置"""
    min_rating_threshold: float = 4.0
    min_quality_threshold: float = 3.5
    max_examples: int = 5
    default_similarity_threshold: float = 0.6
    diversity_threshold: float = 0.3
    recency_weight: float = 0.1
    quality_weight: float = 0.4
    similarity_weight: float = 0.5

    # 动态阈值配置
    simple_query_threshold: float = 0.5
    complex_query_threshold: float = 0.7
    adaptive_mode: bool = True

    # 三轨评分筛选配置
    three_track_filtering: bool = True           # 是否启用三轨评分筛选
    min_ux_score: float = 4.0                    # 最低用户体验评分
    min_personalization_score: float = 4.0       # 最低个性化感知评分
    min_expert_score: float = 4.0                # 最低专家评分
    safety_veto_threshold: int = 3               # 安全性一票否决门槛
    only_fewshot_eligible: bool = True           # 只返回符合Few-Shot条件的
```

### 检索流程

```python
async def retrieve_with_quality_filter(
    self,
    query: str,
    user_id: Optional[str] = None,
    query_complexity: Optional[bool] = None,
    top_k: Optional[int] = None
) -> Tuple[List[FewShotExample], Dict[str, Any]]:
    """
    基于质量过滤的Few-Shot检索

    流程：
    1. 确定相似度阈值
    2. 初始向量检索
    3. 质量过滤
    4. 相似度过滤
    5. 多样性过滤
    6. 最终排序和截取
    """
    # 1. 确定相似度阈值
    similarity_threshold = await self._determine_similarity_threshold(
        query, query_complexity
    )

    # 2. 初始向量检索
    raw_candidates = await self._initial_vector_search(
        query, user_id, top_k=top_k or self.config.max_examples * 3
    )

    # 3. 质量过滤
    quality_filtered = self._filter_by_quality(raw_candidates)

    # 4. 相似度过滤
    similarity_filtered = self._filter_by_similarity(
        quality_filtered, similarity_threshold
    )

    # 5. 多样性过滤
    diversity_filtered = self._ensure_diversity(similarity_filtered)

    # 6. 最终排序和截取
    final_examples = self._rank_and_select(diversity_filtered, query)

    return final_examples, retrieval_stats
```

### 质量过滤逻辑

```python
def _filter_by_quality(self, candidates: List[Dict[str, Any]]) -> List[FewShotExample]:
    """基于质量过滤候选结果（包含三轨评分筛选）"""
    filtered = []

    for candidate in candidates:
        # 提取质量指标
        user_rating = float(candidate.get("user_rating", 0))
        quality_score = float(candidate.get("quality_score", 0))

        # 基础质量过滤
        if (user_rating < self.config.min_rating_threshold or
            quality_score < self.config.min_quality_threshold):
            continue

        # 三轨评分筛选
        if self.config.three_track_filtering:
            # 检查是否符合Few-Shot条件
            if self.config.only_fewshot_eligible:
                fewshot_eligible = candidate.get("fewshot_eligible", True)
                if not fewshot_eligible:
                    continue

            # 提取三轨评分
            three_track_scores = candidate.get("three_track_scores", {})
            if three_track_scores:
                # 用户体验评分检查
                ux_avg = three_track_scores.get("user_experience_avg")
                if ux_avg is not None and ux_avg < self.config.min_ux_score:
                    continue

                # 个性化感知评分检查
                pers_avg = three_track_scores.get("personalization_score")
                if pers_avg is not None and pers_avg < self.config.min_personalization_score:
                    continue

                # 安全性一票否决
                safety_score = three_track_scores.get("safety_score")
                if safety_score is not None and safety_score < self.config.safety_veto_threshold:
                    continue

        # 构建示例对象
        example = FewShotExample(...)
        filtered.append(example)

    return filtered
```

---

## 3. 最佳实践检索器

**文件路径**: `framework/retrieval/best_practices_retriever.py`

### 功能

- 从知识库中检索最佳实践
- 支持领域特定的最佳实践过滤
- 与用户档案匹配

### 使用示例

```python
retriever = EnhancedFewShotRetriever(
    vector_store=vector_store,
    backend_client=backend_client,
    config=FewShotConfig()
)

# 获取最佳实践
best_practices = await retriever.get_best_practices(
    query="如何提高卧推成绩",
    user_profile=user_profile,
    domain="fitness",
    top_k=3
)
```

---

## 4. Few-Shot工具函数

### 准入检查

```python
def check_basic_fewshot_eligibility(example: Dict[str, Any]) -> bool:
    """
    检查是否符合Few-Shot基本条件

    条件：
    - 质量评分 >= 4.0
    - 用户评分 >= 4.0
    - 三轨评分全部 >= 4.0（如果存在）
    - 安全性评分 >= 3（如果存在，低于3则一票否决）
    """
    MIN_QUALITY_SCORE = 4.0
    MIN_USER_RATING = 4.0
    SAFETY_VETO_THRESHOLD = 3

    quality_score = example.get("quality_score", 0)
    user_rating = example.get("user_rating", 0)

    if quality_score < MIN_QUALITY_SCORE:
        return False

    if user_rating < MIN_USER_RATING:
        return False

    # 检查三轨评分（如果有）
    three_track_scores = example.get("three_track_scores")
    if three_track_scores:
        user_experience_avg = three_track_scores.get("user_experience_avg")
        personalization_avg = three_track_scores.get("personalization_score")
        safety_score = three_track_scores.get("safety_score")

        if user_experience_avg is not None and user_experience_avg < MIN_QUALITY_SCORE:
            return False

        if personalization_avg is not None and personalization_avg < MIN_QUALITY_SCORE:
            return False

        # 安全性一票否决
        if safety_score is not None and safety_score < SAFETY_VETO_THRESHOLD:
            return False

    return True
```

---

## 5. 统计与监控

### 检索统计

```python
@dataclass
class FewShotRetrievalStats:
    """Few-Shot检索统计"""
    query_complexity: Optional[bool] = None
    similarity_threshold: float = 0.0
    total_candidates: int = 0
    quality_filtered: int = 0
    similarity_filtered: int = 0
    diversity_filtered: int = 0
    final_examples: int = 0
    execution_time_ms: float = 0.0
    avg_quality: float = 0.0
    avg_similarity: float = 0.0
```

### 池统计

```python
@dataclass
class FewShotPoolStats:
    """Few-Shot池统计"""
    total_sessions: int = 0
    rated_sessions: int = 0
    eligible_sessions: int = 0
    eligibility_rate: float = 0.0
    grade_distribution: Dict[str, int] = field(default_factory=dict)
    safety_veto_count: int = 0
    thresholds: Dict[str, float] = field(default_factory=dict)
```

---

## 相关链接

- **基础架构**: [02-基础架构与工具注册.md](./02-基础架构与工具注册.md)
- **向量存储**: [02-数据层/03-Qdrant向量库结构.md](../02-数据层/03-Qdrant向量库结构.md)
- **MCP工具**: [03-MCP工具实现/01-MCP工具注册表.md](./01-MCP工具注册表.md)

---

**维护者**: 薛小川
**最后更新**: 2026-02-28