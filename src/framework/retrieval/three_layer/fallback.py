# -*- coding: utf-8 -*-
"""
三层检索引擎 - 规则匹配降级方案
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .models import LayerExecutionResult

logger = logging.getLogger(__name__)


class FallbackMixin:
    """规则匹配降级 Mixin"""

    async def _execute_rule_based_fallback(
        self,
        query: str,
        user_profile: Optional[Dict[str, Any]],
        top_k: int
    ) -> LayerExecutionResult:
        """
        规则匹配降级方案：当Layer1和Layer2都失败时使用

        策略：
        1. 基于关键词匹配推荐通用项目
        2. 基于用户档案推荐适合的难度
        3. 返回安全的基础项目

        框架层领域无关（Requirements 6.1, 6.2）：
        - 推荐数据从领域适配器获取
        - 如果没有适配器，返回空结果
        """
        start_time = datetime.now()
        logger.info("→ 规则匹配降级: 基于关键词的通用推荐")

        try:
            # 从领域适配器获取推荐数据（框架层领域无关）
            if not self.domain_adapter:
                logger.warning("  ⚠️ 未配置领域适配器，无法执行规则匹配降级")
                return self._empty_layer_result("Layer2-RuleBased-Fallback", error="未配置领域适配器")

            # 从适配器获取降级推荐数据
            rule_based_recommendations = self.domain_adapter.get_fallback_recommendations()
            default_fallback_items = self.domain_adapter.get_default_fallback_items()

            # 从查询中提取关键词
            query_lower = query.lower()
            matched_results = []

            for keyword, items in rule_based_recommendations.items():
                if keyword in query_lower:
                    # 根据用户档案过滤难度
                    user_level = user_profile.get("fitness_level", "intermediate") if user_profile else "intermediate"

                    for item in items:
                        item_difficulty = item.get("difficulty", "intermediate")
                        if user_level == "beginner" and item_difficulty in ["beginner"]:
                            matched_results.append({
                                **item,
                                "source": "rule_based_fallback",
                                "score": 0.5,
                                "rule_matched": keyword
                            })
                        elif user_level == "intermediate" and item_difficulty in ["beginner", "intermediate"]:
                            matched_results.append({
                                **item,
                                "source": "rule_based_fallback",
                                "score": 0.5,
                                "rule_matched": keyword
                            })
                        elif user_level == "advanced":
                            matched_results.append({
                                **item,
                                "source": "rule_based_fallback",
                                "score": 0.5,
                                "rule_matched": keyword
                            })

            # 如果没有匹配到关键词，返回默认项目
            if not matched_results:
                logger.info("  → 未匹配到关键词，返回默认项目")
                matched_results = default_fallback_items.copy()

            # 限制返回数量
            matched_results = matched_results[:top_k]

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            confidence = 0.5 if matched_results else 0.0

            logger.info(f"  ✓ 规则匹配完成: {len(matched_results)}个通用推荐")

            return LayerExecutionResult(
                layer_name="Layer2-RuleBased-Fallback",
                success=bool(matched_results),
                results=matched_results,
                execution_time_ms=execution_time,
                confidence=confidence,
                metadata={
                    "source": "rule_based_fallback",
                    "count": len(matched_results),
                    "fallback_reason": "Layer1和Layer2均失败",
                    "domain": self.domain_adapter.get_name() if self.domain_adapter else "unknown"
                }
            )

        except Exception as e:
            logger.error(f"  ✗ 规则匹配失败: {e}")
            return self._empty_layer_result("Layer2-RuleBased-Fallback", error=str(e))
