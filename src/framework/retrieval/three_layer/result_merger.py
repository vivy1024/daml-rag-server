# -*- coding: utf-8 -*-
"""
三层检索引擎 - 结果合并与构建
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import LayerExecutionResult, ThreeLayerResult

from ..reranker import get_reranker

logger = logging.getLogger(__name__)


class ResultMergerMixin:
    """结果合并 Mixin"""

    def _empty_layer_result(
        self,
        layer_name: str,
        error: Optional[str] = None
    ) -> LayerExecutionResult:
        """创建空的层级结果"""
        return LayerExecutionResult(
            layer_name=layer_name,
            success=False,
            results=[],
            execution_time_ms=0.0,
            confidence=0.0,
            metadata={},
            error=error
        )

    def _build_final_result(
        self,
        query: str,
        domain: str,
        layer1: LayerExecutionResult,
        layer2: LayerExecutionResult,
        layer3: LayerExecutionResult,
        start_time: datetime,
        knowledge_context: Optional[List[Dict[str, Any]]] = None
    ) -> ThreeLayerResult:
        """构建最终结果"""
        # 确定最终结果来源
        if layer3.success and layer3.results:
            final_results = layer3.results
            reasoning = f"三层检索完成: Layer1({len(layer1.results)}) → Layer2({len(layer2.results)}) → Layer3({len(layer3.results)}) 最终推荐"
        elif layer2.success and layer2.results:
            final_results = layer2.results[:10]
            reasoning = f"部分检索: Layer1({len(layer1.results)}) → Layer2({len(layer2.results)}) 图谱推荐"
        elif layer1.success and layer1.results:
            final_results = layer1.results[:10]
            reasoning = f"基础检索: Layer1({len(layer1.results)}) 向量推荐"
        else:
            final_results = []
            reasoning = "检索失败: 未找到任何结果"

        # Reranker 重排序（如果启用且有结果）
        enable_reranker = os.getenv("ENABLE_RERANKER", "true").lower() == "true"
        if enable_reranker and final_results and len(final_results) > 1:
            try:
                reranker = get_reranker()
                original_count = len(final_results)
                final_results = reranker.rerank(
                    query=query,
                    documents=final_results,
                    top_k=min(10, len(final_results)),
                    score_threshold=0.0
                )
                reasoning += f" → Reranker重排序({original_count}→{len(final_results)})"
                logger.info(f"Reranker重排序: {original_count} → {len(final_results)} 结果")
            except Exception as e:
                logger.warning(f"Reranker重排序失败，使用原始结果: {e}")

        # 计算总置信度
        layer_confidences = [
            layer1.confidence * 0.3,
            layer2.confidence * 0.4,
            layer3.confidence * 0.3
        ]
        total_confidence = sum(layer_confidences)

        # 计算总耗时
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        # 构建metadata，包含知识上下文
        metadata = {
            "neo4j_direct_used": layer2.metadata.get("source") == "neo4j_direct",
            "layer_execution_times": {
                "layer1": layer1.execution_time_ms,
                "layer2": layer2.execution_time_ms,
                "layer3": layer3.execution_time_ms
            },
            "stats": self.get_stats()
        }

        if knowledge_context:
            metadata["knowledge_context"] = knowledge_context
            metadata["knowledge_context_count"] = len(knowledge_context)
            reasoning += f" + 知识上下文({len(knowledge_context)}条)"

        return ThreeLayerResult(
            query=query,
            domain=domain,
            final_results=final_results,
            layer_1_result=layer1,
            layer_2_result=layer2,
            layer_3_result=layer3,
            total_confidence=total_confidence,
            total_execution_time_ms=total_time,
            reasoning=reasoning,
            metadata=metadata
        )
