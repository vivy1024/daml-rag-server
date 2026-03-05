# -*- coding: utf-8 -*-
"""步骤8：意图路由 + 检索"""

import logging
import asyncio
from typing import Dict, Any, List, Optional

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_retrieve_context(
    state: WorkflowState,
    three_layer_engine=None,
    graphrag_retriever=None,
    hybrid_search_engine=None,
    cypher_executor=None,
) -> StateUpdate:
    """
    步骤8：意图路由检索（Phase 4C）

    路由逻辑：
    0. DAG已有结果 → 直接使用
    1. 意图分类器判断查询类型
       - structured → Neo4j Cypher 直查（跳过向量检索，~50ms）
       - semantic   → HybridSearch（BM25 + 向量 + RRF，~200ms）
       - hybrid     → Neo4j + HybridSearch 融合
    2. 降级链：GraphRAG → 三层检索 → 空结果
    3. 所有路径均追加 knowledge_articles 知识库检索结果（knowledge_refs）

    Args:
        state: 当前工作流状态
        three_layer_engine: 旧三层检索引擎（降级用）
        graphrag_retriever: 新 GraphRAG 检索器
        hybrid_search_engine: 混合检索引擎
        cypher_executor: Neo4j Cypher 直查执行器

    Returns:
        StateUpdate: 状态更新，包含 retrieval_results（含 knowledge_refs）
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    domain = state.get("domain", "fitness")
    dag_results = state.get("dag_results")

    # 并行启动 knowledge_articles 检索（不阻塞主检索路径）
    knowledge_task: Optional[asyncio.Task] = None
    if hybrid_search_engine is not None:
        try:
            knowledge_task = asyncio.ensure_future(
                hybrid_search_engine.search_knowledge_articles(query_text, top_k=5)
            )
        except Exception as e:
            logger.warning(f"⚠️ [{request_id}] 步骤8: 启动知识库检索任务失败: {e}")

    async def _get_knowledge_refs() -> List[Dict]:
        """等待知识库检索任务，失败时返回空列表"""
        if knowledge_task is None:
            return []
        try:
            return await knowledge_task
        except Exception as e:
            logger.warning(f"⚠️ [{request_id}] 步骤8: 知识库检索任务失败: {e}")
            return []

    # 如果DAG已经返回结果，可能不需要额外检索
    if dag_results:
        knowledge_refs = await _get_knowledge_refs()
        logger.info(f"✅ [{request_id}] 步骤8完成: 使用DAG结果，跳过检索")
        return StateUpdate(updates={
            "retrieval_results": {
                "results": _convert_dag_results_to_list(dag_results),
                "query_type": "dag_orchestration",
                "domain": domain,
                "count": len(dag_results),
                "knowledge_refs": knowledge_refs,
            }
        })

    # ─── Phase 4C: 意图分类路由 ───
    intent_result = None
    try:
        from .....framework.retrieval.intent_classifier import classify_intent, QueryIntent
        intent_result = classify_intent(query_text)
    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤8: 意图分类失败，降级到混合检索: {e}")

    # 路由1: structured → Neo4j Cypher 直查
    if (intent_result
            and intent_result.intent == QueryIntent.STRUCTURED
            and intent_result.structured_type
            and intent_result.extracted_entity):
        try:
            if cypher_executor is None:
                from .....framework.retrieval.cypher_templates import CypherQueryExecutor
                cypher_executor = CypherQueryExecutor()

            neo4j_results = cypher_executor.execute(
                query_type=intent_result.structured_type,
                entity=intent_result.extracted_entity,
                limit=10
            )

            if neo4j_results:
                knowledge_refs = await _get_knowledge_refs()
                logger.info(
                    f"✅ [{request_id}] 步骤8完成: "
                    f"Neo4j直查({intent_result.structured_type.value}) "
                    f"返回 {len(neo4j_results)} 个结果, "
                    f"实体='{intent_result.extracted_entity}'"
                )
                return StateUpdate(updates={
                    "retrieval_results": {
                        "results": neo4j_results,
                        "query_type": f"neo4j_structured:{intent_result.structured_type.value}",
                        "domain": domain,
                        "count": len(neo4j_results),
                        "intent": intent_result.intent.value,
                        "entity": intent_result.extracted_entity,
                        "knowledge_refs": knowledge_refs,
                    }
                })
            else:
                logger.info(
                    f"⚠️ [{request_id}] 步骤8: Neo4j直查无结果，降级到混合检索"
                )
        except Exception as e:
            logger.warning(
                f"⚠️ [{request_id}] 步骤8: Neo4j直查失败，降级到混合检索: {e}"
            )

    # 路由2: hybrid → Neo4j + HybridSearch 融合
    if intent_result and intent_result.intent == QueryIntent.HYBRID:
        try:
            neo4j_results = []
            if intent_result.extracted_entity and cypher_executor:
                try:
                    from .....framework.retrieval.intent_classifier import StructuredQueryType
                    neo4j_results = cypher_executor.execute(
                        query_type=StructuredQueryType.EXERCISE_DETAILS,
                        entity=intent_result.extracted_entity,
                        limit=5
                    )
                except Exception:
                    pass

            # 同时走混合检索
            hybrid_results = []
            if hybrid_search_engine:
                try:
                    hybrid_results = await hybrid_search_engine.hybrid_search(
                        query=query_text, domain=domain, top_k=10,
                        intent_type="HYBRID"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [{request_id}] 步骤8: 混合检索失败: {e}")

            # 融合：Neo4j 结果排前面，HybridSearch 结果排后面（去重）
            merged = _merge_results(neo4j_results, hybrid_results, max_total=10)

            if merged:
                knowledge_refs = await _get_knowledge_refs()
                logger.info(
                    f"✅ [{request_id}] 步骤8完成: "
                    f"Hybrid路由(Neo4j={len(neo4j_results)}+Search={len(hybrid_results)}) "
                    f"→ 融合{len(merged)}个结果"
                )
                return StateUpdate(updates={
                    "retrieval_results": {
                        "results": merged,
                        "query_type": "intent_hybrid",
                        "domain": domain,
                        "count": len(merged),
                        "intent": "hybrid",
                        "entity": intent_result.extracted_entity,
                        "knowledge_refs": knowledge_refs,
                    }
                })
        except Exception as e:
            logger.warning(
                f"⚠️ [{request_id}] 步骤8: Hybrid路由整体失败，降级到语义检索: {e}"
            )

    # 路由3: semantic → HybridSearch（BM25 + 向量 + 加权RRF）
    if hybrid_search_engine:
        try:
            search_intent = intent_result.intent.value if intent_result else "SEMANTIC"
            hybrid_results = await hybrid_search_engine.hybrid_search(
                query=query_text,
                domain=domain,
                top_k=10,
                intent_type=search_intent
            )
            query_type_label = "hybrid_search"
            if intent_result and intent_result.intent == QueryIntent.SEMANTIC:
                query_type_label = "semantic_hybrid_search"

            logger.info(
                f"✅ [{request_id}] 步骤8完成: "
                f"HybridSearch(BM25+向量+RRF) 返回 {len(hybrid_results)} 个结果"
            )
            knowledge_refs = await _get_knowledge_refs()
            return StateUpdate(updates={
                "retrieval_results": {
                    "results": hybrid_results,
                    "query_type": query_type_label,
                    "domain": domain,
                    "count": len(hybrid_results),
                    "intent": intent_result.intent.value if intent_result else "unknown",
                    "knowledge_refs": knowledge_refs,
                }
            })
        except Exception as e:
            logger.warning(
                f"⚠️ [{request_id}] 步骤8: 混合检索失败，降级到GraphRAG: {e}"
            )

    # 降级：GraphRAG 或旧三层检索
    retriever = graphrag_retriever or three_layer_engine

    try:
        if retriever:
            retrieval_results = await retriever.search(
                query=query_text,
                domain=domain,
                top_k=10
            )

            retriever_name = getattr(retriever, '__class__', type(retriever)).__name__
            logger.info(
                f"✅ [{request_id}] 步骤8完成: "
                f"{retriever_name} 返回 {len(retrieval_results.get('results', []))} 个结果"
            )

            knowledge_refs = await _get_knowledge_refs()
            retrieval_results["knowledge_refs"] = knowledge_refs
            return StateUpdate(updates={"retrieval_results": retrieval_results})
        else:
            knowledge_refs = await _get_knowledge_refs()
            logger.warning(f"⚠️ [{request_id}] 步骤8: 无检索引擎")
            return StateUpdate(
                updates={"retrieval_results": {"results": [], "count": 0, "knowledge_refs": knowledge_refs}},
                warning="无检索引擎"
            )

    except Exception as e:
        logger.error(f"❌ [{request_id}] 步骤8: 检索异常: {e}")
        return StateUpdate(
            updates={"retrieval_results": {"results": [], "count": 0, "knowledge_refs": []}},
            error=f"检索异常: {str(e)}"
        )


def _merge_results(
    neo4j_results: List[Dict],
    hybrid_results: List[Dict],
    max_total: int = 10
) -> List[Dict]:
    """融合 Neo4j 和 HybridSearch 结果（去重）"""
    seen_texts = set()
    merged = []

    # Neo4j 结果优先
    for r in neo4j_results:
        text_key = r.get("text", "")[:80]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            merged.append(r)

    # HybridSearch 结果补充
    for r in hybrid_results:
        if len(merged) >= max_total:
            break
        text_key = r.get("text", "")[:80]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            merged.append(r)

    return merged


def _convert_dag_results_to_list(dag_results: Dict[str, Any]) -> list:
    """将DAG结果转换为列表格式"""
    if not dag_results:
        return []

    results = []
    for task_name, result in dag_results.items():
        if result and isinstance(result, dict) and "error" not in result:
            results.append({
                "id": f"{task_name}_result",
                "content": str(result),
                "score": 0.8,
                "metadata": {
                    "layer": "dag_task",
                    "source": task_name,
                    "task": task_name
                }
            })
    return results
