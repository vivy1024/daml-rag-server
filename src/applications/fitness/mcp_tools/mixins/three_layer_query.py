# -*- coding: utf-8 -*-
"""
ThreeLayerQueryMixin - 三层检索标准化Mixin

提供 execute_three_layer_query() 和降级处理，
所有MCP工具通过此方法查询动作数据。

对应 Requirements 17.1-17.6。

Task 44 - Phase 7 Batch 4
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ThreeLayerQueryResult:
    """三层检索查询结果"""
    success: bool
    results: List[Dict[str, Any]]
    layer_stats: Dict[str, Any]
    execution_time_ms: float
    confidence: float
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "results": self.results,
            "layer_stats": self.layer_stats,
            "execution_time_ms": self.execution_time_ms,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


class ThreeLayerQueryMixin:
    """
    三层检索标准化Mixin

    依赖 self.three_layer_engine（由BaseMCPTool.__init__注入）
    和 self.get_name()。
    """

    async def execute_three_layer_query(
        self,
        query: str,
        user_profile: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        domain: str = "fitness_exercises",
        safety_check: bool = True,
    ) -> ThreeLayerQueryResult:
        """
        标准化三层检索调用 (Req 17.2, 17.3)

        所有MCP工具应通过此方法查询动作，而不是直接访问数据库。
        """
        start_time = time.time()
        tool_name = self.get_name()
        _logger = getattr(self, "logger", logger)

        engine = getattr(self, "three_layer_engine", None)
        if engine is None:
            _logger.error(f"❌ 工具 {tool_name} 未注入三层检索引擎")
            return ThreeLayerQueryResult(
                success=False, results=[], layer_stats={},
                execution_time_ms=0, confidence=0,
                reasoning="三层检索引擎未初始化",
            )

        try:
            _logger.info(
                f"🔍 [{tool_name}] 调用三层检索引擎 | "
                f"查询: {query[:50]}... | top_k: {top_k}"
            )

            result = await engine.execute_three_layer_query(
                query=query, domain=domain,
                user_profile=user_profile, filters=filters,
                top_k=top_k, safety_check=safety_check,
            )

            execution_time_ms = (time.time() - start_time) * 1000

            layer_stats = {}
            for layer_name in ("layer_1_result", "layer_2_result", "layer_3_result"):
                layer_key = layer_name.replace("_result", "").replace("_", "")
                layer_data = getattr(result, layer_name, None)
                if layer_data:
                    layer_stats[layer_key] = {
                        "success": layer_data.success,
                        "count": len(layer_data.results),
                        "confidence": layer_data.confidence,
                        "execution_time_ms": layer_data.execution_time_ms,
                    }

            _logger.info(
                f"✅ [{tool_name}] 三层检索完成 | "
                f"结果数: {len(result.final_results)} | "
                f"置信度: {result.total_confidence:.2f} | "
                f"耗时: {execution_time_ms:.0f}ms"
            )

            return ThreeLayerQueryResult(
                success=True,
                results=result.final_results,
                layer_stats=layer_stats,
                execution_time_ms=execution_time_ms,
                confidence=result.total_confidence,
                reasoning=result.reasoning,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            _logger.error(
                f"❌ [{tool_name}] 三层检索失败 | "
                f"错误: {e} | 耗时: {execution_time_ms:.0f}ms",
                exc_info=True,
            )
            return await self._handle_three_layer_failure(
                query=query, filters=filters, top_k=top_k, error=e,
            )

    async def _handle_three_layer_failure(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        top_k: int,
        error: Exception,
    ) -> ThreeLayerQueryResult:
        """三层检索失败时的降级处理 (Req 17.6)"""
        tool_name = self.get_name()
        _logger = getattr(self, "logger", logger)
        _logger.warning(f"⚠️ [{tool_name}] 启动降级策略 | 原因: {error}")

        return ThreeLayerQueryResult(
            success=False, results=[],
            layer_stats={"error": str(error), "fallback_used": True},
            execution_time_ms=0, confidence=0,
            reasoning=f"三层检索失败: {error}",
        )
