# 步骤6：Few-Shot检索代码参考

**版本**: v1.0.0  
**创建日期**: 2025-12-17  
**状态**: ✅ 已完成

---

## 概述

步骤6从Qdrant检索历史高质量对话作为Few-Shot示例，用于推理时学习（In-Context Learning）。

### 文件位置

- **主文件**: `src/framework/retrieval/qdrant_helper.py`
- **调用位置**: `src/applications/fitness/fitness_orchestrator.py`

### 核心实现

```python
async def search_similar_conversations(
    query_vector: List[float],
    top_k: int = 5,
    min_similarity: float = 0.6,
    min_rating: int = 4  # 只检索高分对话
) -> List[Dict[str, Any]]:
    """检索相似的高质量对话"""
    results = qdrant_client.search(
        collection_name="chat_conversations",
        query_vector=query_vector,
        limit=top_k,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="user_rating",
                    range=Range(gte=min_rating)
                )
            ]
        ),
        score_threshold=min_similarity
    )
    
    return [
        {
            "user_query": hit.payload["user_query"],
            "ai_response": hit.payload["ai_response"],
            "similarity": hit.score,
            "user_rating": hit.payload["user_rating"]
        }
        for hit in results
    ]
```

---

## 相关文档

- **上一步骤**: [06-步骤5-智能模型选择.md](./05-步骤5-智能模型选择.md)
- **下一步骤**: [08-步骤6.5-LLM选择DAG方案.md](./07-步骤6.5-LLM选择DAG方案.md)
- **数据存储**: [03-步骤2-会话记录存储.md](./02-步骤2-会话记录存储.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-17
