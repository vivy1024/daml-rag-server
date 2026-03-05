# -*- coding: utf-8 -*-
"""步骤4：BGE复杂度分类"""

import os
import logging
import hashlib

from ..state import WorkflowState, StateUpdate

logger = logging.getLogger(__name__)


async def node_classify_complexity(
    state: WorkflowState,
    classifier=None,
    cache_manager=None
) -> StateUpdate:
    """
    步骤4：BGE复杂度分类（带完整错误处理 + 缓存管理器集成）

    注意：当DUAL_MODEL_ENABLED=false时，此步骤会快速跳过

    Args:
        state: 当前工作流状态
        classifier: 复杂度分类器（可选）
        cache_manager: 缓存管理器（可选）

    Returns:
        StateUpdate: 状态更新，包含 complexity_level
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")

    # ✅ 检查是否启用双模型选择，如果禁用则快速跳过
    dual_model_enabled = os.getenv("DUAL_MODEL_ENABLED", "false").lower() == "true"
    if not dual_model_enabled:
        logger.info(f"✅ [{request_id}] 步骤4跳过: 双模型选择已禁用，直接使用DeepSeek")
        return StateUpdate(updates={
            "complexity_level": "complex",  # 默认复杂，使用DeepSeek
            "_complexity_similarity": 1.0,
            "_complexity_reason": "双模型选择已禁用"
        })

    try:
        # 延迟导入分类器
        if classifier is None:
            from .....framework.models.query_complexity_classifier import QueryComplexityClassifier
            classifier = QueryComplexityClassifier()

        # 生成缓存键
        query_hash = hashlib.md5(query_text.encode('utf-8')).hexdigest()
        cache_key = f"bge_complexity:{query_hash}"

        async def fetch_complexity():
            return classifier.classify_complexity(query_text)

        # 使用缓存管理器（如果可用）
        if cache_manager:
            result = await cache_manager.get(
                key=cache_key,
                fetch_func=fetch_complexity,
                ttl=3600  # 1小时TTL
            )
        else:
            result = classifier.classify_complexity(query_text)

        # 提取结果
        is_complex = result.is_complex
        similarity = result.similarity
        reason = result.reason

        # 确定复杂度级别
        if is_complex:
            complexity_level = "complex"
        elif similarity >= 0.5:
            complexity_level = "moderate"
        else:
            complexity_level = "simple"

        logger.info(
            f"✅ [{request_id}] 步骤4完成: 复杂度={complexity_level}, "
            f"相似度={similarity:.2f}, 耗时={result.duration_ms:.2f}ms"
        )

        return StateUpdate(updates={
            "complexity_level": complexity_level,
            "_complexity_similarity": similarity,
            "_complexity_reason": reason
        })

    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤4: BGE复杂度分类失败: {e}")
        # 降级策略：默认为简单查询
        return StateUpdate(
            updates={"complexity_level": "simple"},
            warning=f"BGE复杂度分类失败，使用降级策略: {str(e)}"
        )
