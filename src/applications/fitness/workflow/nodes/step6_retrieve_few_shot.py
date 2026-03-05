# -*- coding: utf-8 -*-
"""步骤6：Few-Shot检索"""

import logging
import hashlib

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_retrieve_few_shot(
    state: WorkflowState,
    backend_client=None,
    cache_manager=None
) -> StateUpdate:
    """
    步骤6：Few-Shot检索（推理时学习 + 缓存管理器集成）

    Args:
        state: 当前工作流状态
        backend_client: 后端客户端（可选）
        cache_manager: 缓存管理器（可选）

    Returns:
        StateUpdate: 状态更新，包含 few_shot_examples
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    user_profile = state.get("user_profile")
    domain = state.get("domain", "fitness")

    few_shot_examples = []

    try:
        from .....framework.retrieval.enhanced_few_shot_retriever import EnhancedFewShotRetriever  # noqa: E501

        few_shot_retriever = EnhancedFewShotRetriever(
            vector_store=None,
            backend_client=backend_client
        )

        # 生成缓存键
        cache_key_data = f"{query_text}:{user_profile.get('fitness_goal', '') if user_profile else ''}:{domain}"
        cache_hash = hashlib.md5(cache_key_data.encode('utf-8')).hexdigest()
        cache_key = f"few_shot:{cache_hash}"

        async def fetch_few_shot_examples():
            best_practices = await few_shot_retriever.get_best_practices(
                query=query_text,
                user_profile=user_profile,
                domain=domain,
                top_k=3
            )

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

        # 使用缓存管理器（如果可用）
        if cache_manager:
            few_shot_examples = await cache_manager.get(
                key=cache_key,
                fetch_func=fetch_few_shot_examples,
                ttl=1800  # 30分钟TTL
            )
        else:
            few_shot_examples = await fetch_few_shot_examples()

        if few_shot_examples is None:
            few_shot_examples = []

        logger.info(f"✅ [{request_id}] 步骤6完成: {len(few_shot_examples)}个最佳实践")

        return StateUpdate(updates={"few_shot_examples": few_shot_examples})

    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤6: Few-Shot检索异常: {e}")
        return StateUpdate(
            updates={"few_shot_examples": []},
            warning=f"Few-Shot检索异常: {str(e)}"
        )
