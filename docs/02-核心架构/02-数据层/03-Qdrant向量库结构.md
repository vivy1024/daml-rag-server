# Qdrant向量库结构

**版本**: v2.0.0  
**创建日期**: 2025-12-21  
**更新日期**: 2026-01-06  
**状态**: ✅ 已完成

---

## 概述

Qdrant是DAML-RAG系统的向量数据库，负责存储和检索语义向量，支持Layer 1的向量语义检索。通过GTE-Large-zh模型生成1024维向量，实现高效的语义相似度搜索。

---

## 核心统计数据

### 集合统计

| 集合名称 | 向量数量 | 说明 | 状态 |
|---------|---------|------|------|
| **chat_sessions_fewshot** | 动态 | Few-Shot样本（步骤6） | ✅ 已完成 |
| **training_knowledge** | 43 | 训练知识文档 | ✅ v5.2更新 |
| **fitness_exercises_v2** | 1,790 | 健身动作（与Neo4j完全同步） | ✅ v8.59更新 |
| **food_nutrition_vector** | 1,851 | 食物营养 | ✅ 已完成 |

**总向量数**: 3,684+ 个（不含动态Few-Shot样本）

### 向量参数

- **模型**: GTE-Large-zh（thenlper/gte-large-zh，阿里达摩院）
- **维度**: 1024维
- **语言**: 中文优化
- **距离度量**: Cosine相似度

### 向量模型选型（v8.54.0）

| 模型 | Top1分数 | Top3分数 | 相关性 | 综合分 |
|------|----------|----------|--------|--------|
| **GTE-Large-zh** ⭐ | 0.6865 | 0.6669 | **94.4%** | 0.7580 |
| M3E-Large | 0.7392 | 0.7287 | 77.8% | 0.7476 |
| GTE-Large-zh | 0.6542 | 0.6425 | 77.8% | 0.6878 |

**选型理由**：
- ✅ 相关性最高（94.4%），语义理解更准确
- ✅ 阿里达摩院出品，中文优化好
- ✅ 1024维输出，与系统架构兼容

---

## 向量集合详解

### 1. chat_sessions_fewshot集合（动态）

#### 集合说明

存储高质量的历史对话作为Few-Shot样本，用于步骤6的推理时上下文学习（In-Context Learning）。这是DAML-RAG系统实现推理时学习的核心机制。

#### 数据来源

**来源**: MySQL的`chat_sessions`表
- 用户评分 ≥ 4.0 的高质量对话
- 最近7天内的对话
- 包含完整的query和response

#### 向量化策略

```python
{
    "text": f"Query: {user_query}\nResponse: {llm_response}",
    "metadata": {
        "session_id": str,        # 会话ID
        "user_id": int,           # 用户ID（可为NULL）
        "model_used": str,        # 使用的模型
        "tools_used": list,       # 调用的工具列表
        "user_rating": float,     # 用户评分（1-5）
        "created_at": str         # 创建时间
    }
}
```

#### 使用场景

1. **Few-Shot检索**（步骤6）
   - 根据当前用户查询检索相似的历史对话
   - 提供3-5个高质量样本作为上下文
   - 提升LLM的响应质量和一致性

2. **推理时学习**
   - 无需微调模型
   - 动态学习用户偏好
   - 保持响应风格一致

3. **质量控制**
   - 只存储高评分对话（≥4.0）
   - 定期清理过期样本（>7天）
   - 确保样本质量

#### 查询示例

```python
# 步骤6：Few-Shot检索
query = "推荐增肌训练计划"
results = qdrant_client.search(
    collection_name="chat_sessions_fewshot",
    query_vector=encode_query(query),
    limit=5,
    query_filter={
        "must": [
            {"key": "user_rating", "range": {"gte": 4.0}}
        ]
    }
)
```

#### 同步机制

**自动同步**:
- 当用户对对话评分≥4.0时，自动添加到Qdrant
- 每天凌晨清理7天前的样本
- 保持集合大小在合理范围（<10,000个）

**手动同步**:
```bash
# 同步最近7天的高质量对话
python scripts/sync_fewshot_to_qdrant.py --days 7 --min-rating 4.0
```

---

### 2. training_knowledge集合（43个向量）

#### 集合说明

存储训练相关的知识文档，支持LLM决策时的语义检索。

#### 向量来源

**1. 训练决策树**（recommendation_decision_tree.md）
- 训练分化选择逻辑
- 训练频率建议
- 训练周期计算
- 训练量分配策略

**2. 用户档案分析逻辑**（user_profile_analysis_logic.md）
- 用户水平评估
- 目标分析
- 个性化建议生成

#### 向量化策略

```python
{
    "chunk_size": 512,        # 分块大小（tokens）
    "overlap": 50,            # 重叠大小（tokens）
    "metadata": {
        "source_file": str,   # 源文件名
        "chunk_index": int,   # 块索引
        "text": str          # 原始文本
    }
}
```

#### 使用场景

1. **LLM决策支持**
   - 步骤6.5：LLM选择DAG方案时检索相关训练知识
   - 提供科学依据和决策参考

2. **训练计划生成**
   - 生成训练计划时参考训练科学原理
   - 确保计划符合训练学理论

3. **用户问答**
   - 回答用户训练相关问题
   - 提供专业的训练建议

#### 查询示例

```python
# 查询训练分化建议
query = "初学者应该选择什么训练分化？"
results = qdrant_client.search(
    collection_name="training_knowledge",
    query_vector=encode_query(query),
    limit=3
)
```

---

### 3. fitness_exercises_v2集合（1,790个向量）

#### 集合说明

存储Exercise节点的语义向量，支持自然语言查询健身动作。

#### 向量生成

**数据来源**: Neo4j的Exercise节点（1,790个）

**向量化模型**: GTE-Large-zh（thenlper/gte-large-zh）

**搜索文本构建策略**（权重设计）:
1. **名称（中英文）**：重复3次，权重最高
2. **主要肌群**：重复2次，权重高
3. **次要肌群、力类型、动作类型**：各1次
4. **描述**：取前500字
5. **步骤说明**：取前300字

**包含字段**:
- 名称（中英文）
- 所有肌群信息
- 力类型、动作类型、动力链
- 握法、器械、难度
- 训练参数（次数、组数）
- 描述和步骤说明
- 安全等级

#### Payload字段结构

与Neo4j Exercise节点完全统一，支持丰富的过滤和检索：

**基础信息**:
| 字段 | 类型 | 说明 |
|------|------|------|
| exercise_id | int | 整数ID，与Neo4j关联 |
| name_zh | string | 中文名称 |
| name_en | string | 英文名称 |
| slug | string | URL友好标识 |

**肌肉信息**:
| 字段 | 类型 | 说明 |
|------|------|------|
| primary_muscle_zh | string | 主要肌群（中文） |
| primary_muscle_en | string | 主要肌群（英文） |
| secondary_muscles_zh | list | 次要肌群列表 |
| all_muscles_zh | list | 所有相关肌群 |

**运动学分类**:
| 字段 | 类型 | 说明 |
|------|------|------|
| force_zh | string | 力类型：推力/拉力/保持 |
| mechanic_zh | string | 动作类型：复合/单关节 |
| kinetic_chain_type | string | 动力链：open_chain/closed_chain/mixed |
| grips_zh | list | 握法列表 |

**训练参数**:
| 字段 | 类型 | 说明 |
|------|------|------|
| equipment_zh | string | 器械（中文） |
| difficulty | string | 难度等级 |
| rep_range | string | 次数范围 |
| set_range | string | 组数范围 |
| rest_period | string | 休息时间 |

**安全信息**:
| 字段 | 类型 | 说明 |
|------|------|------|
| safety_level | string | 安全等级：LOW_RISK/MODERATE_RISK/HIGH_RISK |
| safety_level_zh | string | 安全等级中文 |

#### 使用场景

1. **动作推荐**
   - 用户查询："推荐胸部训练动作"
   - 返回相关动作的ID列表

2. **动作搜索**
   - 用户查询："哑铃练手臂的动作"
   - 返回匹配的动作

3. **替代动作查找**
   - 用户查询："杠铃卧推的替代动作"
   - 返回相似的动作

#### 搜索质量验证

| 查询 | Top1结果 | 分数 | 相关性 |
|------|----------|------|--------|
| 胸部训练 卧推 | 哑铃卧推 | 0.7164 | ✅ |
| - | 杠铃卧推 | 0.7049 | ✅ |
| - | 杠铃屈膝卧推 | 0.7014 | ✅ |

**质量标准**:
- ✅ 最高分 >0.70
- ✅ 平均分 >0.65
- ✅ 前3结果与查询高度相关

#### 查询示例

```python
# 查询胸部训练动作
query = "推荐胸部训练动作"
results = qdrant_client.search(
    collection_name="fitness_exercises_v2",
    query_vector=encode_query(query),
    limit=10,
    query_filter={
        "must": [
            {"key": "difficulty", "match": {"value": "beginner"}}
        ]
    }
)
```

#### 运维命令

```bash
# 重新向量化
docker exec fitness_daml_rag python scripts/数据导入向量化/import_exercises_to_qdrant.py -r

# 验证搜索质量
docker exec fitness_daml_rag python scripts/测试/test_models_sample.py gte
```

---

### 4. food_nutrition_vector集合（1,851个向量）

#### 集合说明

存储Food节点的语义向量，支持自然语言查询食物营养信息。

#### 向量生成

**数据来源**: Neo4j的Food节点（1,880个）

**向量化字段**:
```python
text = f"{food.name} {food.category} "
       f"蛋白质{food.protein}g 碳水{food.carbs}g "
       f"脂肪{food.fat}g 热量{food.calories}kcal"
```

**元数据**:
```python
{
    "food_id": str,           # Neo4j节点ID
    "name": str,              # 食物名称
    "category": str,          # 食物分类
    "calories": float,        # 热量（kcal）
    "protein": float,         # 蛋白质（g）
    "carbs": float,           # 碳水化合物（g）
    "fat": float,             # 脂肪（g）
    "glycemic_index": int     # 血糖指数
}
```

#### 使用场景

1. **食物推荐**
   - 用户查询："推荐高蛋白低脂肪的食物"
   - 返回匹配的食物列表

2. **营养查询**
   - 用户查询："鸡胸肉的营养成分"
   - 返回详细营养信息

3. **饮食计划**
   - 用户查询："增肌期适合吃什么"
   - 返回适合的食物

#### 查询示例

```python
# 查询高蛋白食物
query = "高蛋白低脂肪的食物"
results = qdrant_client.search(
    collection_name="food_nutrition_vector",
    query_vector=encode_query(query),
    limit=10,
    query_filter={
        "must": [
            {"key": "protein", "range": {"gte": 20}},
            {"key": "fat", "range": {"lte": 5}}
        ]
    }
)
```

---

## 三层检索架构集成

Qdrant作为三层检索的Layer1（向量语义检索）：

```
Layer1: Qdrant向量检索（语义相似度）
    ↓ 召回 top_k × 5 个候选
Layer2: Neo4j图谱推理（结构化过滤）
    ↓ 基于关系和属性筛选
Layer3: 约束验证（安全检查）
    ↓ 禁忌症、损伤风险评估
最终结果
```

**Layer1配置**:
- **召回倍数**：`top_k × 5`（例如top_k=10时召回50个）
- **质量评估阈值**：0.70（低于此值标记为低质量）
- **动态调整**：低质量时Layer2增加召回倍数补偿

---

## 向量检索流程

### 完整检索流程

```
用户查询（自然语言）
    ↓
GTE-Large-zh编码（1024维向量）
    ↓
Qdrant相似度搜索（Cosine距离）
    ↓
返回Top-K相似向量（带元数据）
    ↓
提取Neo4j节点ID或会话ID
    ↓
Neo4j图查询或MySQL查询获取完整信息
    ↓
返回结构化结果
```

### 检索参数

```python
search_params = {
    "limit": 10,              # 返回Top-K结果
    "score_threshold": 0.7,   # 相似度阈值
    "with_payload": True,     # 返回元数据
    "with_vectors": False     # 不返回向量（节省带宽）
}
```

### 过滤条件

Qdrant支持丰富的过滤条件：

```python
# 精确匹配
{"key": "difficulty", "match": {"value": "beginner"}}

# 范围过滤
{"key": "calories", "range": {"gte": 100, "lte": 300}}

# 多条件组合
{
    "must": [
        {"key": "category", "match": {"value": "蔬菜类"}},
        {"key": "glycemic_index", "range": {"lte": 55}}
    ]
}
```

---

## 性能优化

### 索引优化

**HNSW索引参数**:
```python
{
    "m": 16,                  # 每个节点的连接数
    "ef_construct": 100,      # 构建时的搜索深度
    "ef": 128                 # 查询时的搜索深度
}
```

**性能指标**:
- 平均查询延迟: <50ms
- 召回率: >95%
- 内存使用: ~2GB

### 缓存策略

**查询缓存**:
- 缓存热门查询的向量编码
- 缓存Top-K结果
- TTL: 1小时

**向量缓存**:
- 缓存常用向量
- 减少重复编码
- 内存限制: 500MB

---

## 数据同步

### Neo4j → Qdrant同步

**同步触发条件**:
1. Neo4j新增节点
2. Neo4j更新节点
3. 定期全量同步（每周）

**同步流程**:
```python
1. 从Neo4j查询新增/更新的节点
2. 生成向量（GTE-Large-zh编码）
3. 更新Qdrant集合
4. 验证同步结果
```

**同步脚本**:
```bash
# 增量同步
python scripts/sync_neo4j_to_qdrant.py --incremental

# 全量同步
python scripts/sync_neo4j_to_qdrant.py --full
```

### MySQL → Qdrant同步（Few-Shot）

**同步触发条件**:
1. 用户对对话评分≥4.0
2. 定期清理过期样本（每天凌晨）

**同步流程**:
```python
1. 从MySQL查询高质量对话（rating≥4.0，7天内）
2. 生成向量（GTE-Large-zh编码）
3. 添加到chat_sessions_fewshot集合
4. 删除7天前的样本
```

---

## 监控指标

### 关键指标

| 指标 | 目标值 | 当前值 | 状态 |
|------|--------|--------|------|
| 查询延迟 | <100ms | ~50ms | ✅ 优秀 |
| 召回率 | >90% | ~95% | ✅ 优秀 |
| 内存使用 | <4GB | ~2GB | ✅ 正常 |
| 向量数量 | - | 3,684+ | ✅ 正常 |

### 监控告警

**告警规则**:
- 查询延迟 > 200ms
- 召回率 < 85%
- 内存使用 > 6GB
- 查询失败率 > 1%

---

## 维护操作

### 备份策略

**备份频率**: 每周全量备份

**备份命令**:
```bash
# 导出集合
qdrant-cli export --collection chat_sessions_fewshot --output backup/

# 恢复集合
qdrant-cli import --collection chat_sessions_fewshot --input backup/
```

### 重建索引

**重建触发条件**:
- 向量数量增长 > 50%
- 查询性能下降
- 索引损坏

**重建命令**:
```bash
python scripts/rebuild_qdrant_index.py --collection fitness_exercises_v2
```

---

## 相关文档

- [Neo4j数据库结构](./02-Neo4j数据库结构.md)
- [MySQL数据结构](./04-MySQL数据结构.md)
- [数据库结构总览](./01-数据库结构总览.md)
- [三层检索引擎](../../03-代码参考/01-工作流程步骤/08-步骤8-三层检索.md)
- [Few-Shot检索](../../03-代码参考/01-工作流程步骤/06-步骤6-Few-Shot检索.md)

---

**维护者**: 薛小川  
**最后更新**: 2026-01-06
