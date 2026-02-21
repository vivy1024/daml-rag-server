# 步骤6 - Few-Shot检索

**版本**: v1.1.0
**创建日期**: 2026-02-21
**状态**: 持续更新

---

## 概述

步骤6从最佳实践库检索与用户查询相关的 Few-Shot 示例，用于推理时学习（In-Context Learning）。检索结果会在步骤6.5（LLM选择DAG）和步骤10（LLM深度分析）中作为提示词的一部分，提升响应质量。

### 在工作流中的位置

```
步骤5: 智能模型选择
  ↓
步骤6: Few-Shot检索 ⭐ ← 当前
  ↓  输出 few_shot_examples → 写入 WorkflowState
步骤6.5: LLM选择DAG方案（使用 few_shot_examples）
```

---

## 源码位置

| 文件 | 说明 |
|------|------|
| `src/applications/fitness/workflow/nodes.py` (L550-636) | `node_retrieve_few_shot` 主函数 |
| `src/framework/retrieval/enhanced_few_shot_retriever.py` | `EnhancedFewShotRetriever` 检索器 |
| `src/framework/retrieval/best_practices_retriever.py` | `BestPracticesRetriever` 最佳实践检索 |

---

## 函数签名

```python
async def node_retrieve_few_shot(
    state: WorkflowState,
    backend_client=None,
    cache_manager=None
) -> StateUpdate:
```

### 参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `state` | `WorkflowState` | ✅ | 当前工作流状态，包含 `request_id`、`query_text`、`user_profile`、`domain` |
| `backend_client` | `BackendClient \| None` | ❌ | 后端客户端，用于从数据库检索最佳实践 |
| `cache_manager` | `CacheManager \| None` | ❌ | 缓存管理器，缓存检索结果 |

### 返回值

```python
StateUpdate(updates={
    "few_shot_examples": List[Dict],  # 格式化后的 Few-Shot 示例列表
})
```

每个示例的结构：

```python
{
    "query": str,           # 查询模式（如"如何增肌"）
    "response": str,        # 格式化后的响应文本
    "match_score": float,   # 匹配分数（0-1）
    "pattern_id": str,      # 模式ID
}
```

---

## 执行逻辑

### 1. 初始化检索器

```python
from ....framework.retrieval.enhanced_few_shot_retriever import EnhancedFewShotRetriever

few_shot_retriever = EnhancedFewShotRetriever(
    vector_store=None,
    backend_client=backend_client
)
```

### 2. 生成缓存键

基于查询文本、用户目标、领域生成 MD5 哈希：

```python
cache_key_data = f"{query_text}:{user_profile.get('fitness_goal', '') if user_profile else ''}:{domain}"
cache_hash = hashlib.md5(cache_key_data.encode('utf-8')).hexdigest()
cache_key = f"few_shot:{cache_hash}"
```

### 3. 检索最佳实践

```python
async def fetch_few_shot_examples():
    # 检索 top-3 最佳实践
    best_practices = await few_shot_retriever.get_best_practices(
        query=query_text,
        user_profile=user_profile,
        domain=domain,
        top_k=3
    )
    
    # 格式化为 Few-Shot 示例
    examples = []
    for match in best_practices:
        bp = match.best_practice
        formatted = few_shot_retriever.best_practices_retriever.format_best_practice(
            bp, user_profile,
            {"exercise_name": "动作", "goal": user_profile.get("fitness_goal", "健康") if user_profile else "健康"}
        )
        
        examples.append({
            "query": bp.query_pattern,
            "response": formatted,
            "match_score": match.match_score,
            "pattern_id": bp.pattern_id
        })
    
    return examples
```

### 4. 缓存优先查询

```python
if cache_manager:
    few_shot_examples = await cache_manager.get(
        key=cache_key, fetch_func=fetch_few_shot_examples, ttl=1800  # 30分钟
    )
else:
    few_shot_examples = await fetch_few_shot_examples()
```

---

## 错误处理

| 场景 | 处理方式 | 返回值 |
|------|---------|--------|
| 检索器导入失败 | `except Exception` 捕获 | `few_shot_examples=[]` + `warning` |
| 检索执行异常 | `except Exception` 捕获 | `few_shot_examples=[]` + `warning` |
| 检索结果为 None | 转换为空列表 | `few_shot_examples=[]` |

所有失败场景下工作流继续执行，后续步骤需处理空示例列表的情况。

---

## 与后续步骤的数据流

### 输出到步骤6.5（LLM选择DAG）

`state["few_shot_examples"]` 作为 `DAGSelectionRequest.few_shot_examples` 传入 LLM，帮助模型理解如何选择合适的 DAG 模板。

### 输出到步骤10（LLM深度分析）

`state["few_shot_examples"]` 作为提示词的一部分，提供专业回答的参考示例。

---

## 相关文档

- [05-步骤5-智能模型选择.md](./05-步骤5-智能模型选择.md)
- [07-步骤6.5-LLM选择DAG方案.md](./07-步骤6.5-LLM选择DAG方案.md)

---

**维护者**: 薛小川
**最后更新**: 2026-02-21
