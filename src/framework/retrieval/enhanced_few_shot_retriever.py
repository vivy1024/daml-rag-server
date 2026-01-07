# -*- coding: utf-8 -*-
"""
Enhanced Few-Shot Retriever - 增强版Few-Shot检索器

基于质量过滤和相似度筛选的自动化Few-Shot检索

核心改进：
1. 质量过滤：只检索高分历史对话
2. 动态相似度阈值：基于查询复杂度调整
3. 自动化程度提升：与模型选择策略集成
4. 多样性保证：确保检索结果的多样性

版本: v1.0.0
日期: 2025-12-03
作者: 薛小川
"""

import logging
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# 导入BestPracticesRetriever
try:
    from .best_practices_retriever import BestPracticesRetriever, BestPractice, BestPracticeMatch
except ImportError as e:
    logger.warning(f"Could not import BestPracticesRetriever: {e}")
    BestPracticesRetriever = None


@dataclass
class FewShotExample:
    """Few-Shot示例数据类"""
    query: str
    response: str
    user_rating: float
    quality_score: float
    similarity: float
    tools_used: List[str]
    model_used: str
    timestamp: datetime
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    # ✅ v1.1.0新增：训练案例库字段
    training_effect: Optional[str] = None  # 训练效果标签（excellent/good/fair/poor）
    user_feedback: Optional[str] = None    # 用户反馈文本

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "query": self.query,
            "response": self.response,
            "user_rating": self.user_rating,
            "quality_score": self.quality_score,
            "similarity": self.similarity,
            "tools_used": self.tools_used,
            "model_used": self.model_used,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "metadata": self.metadata,
            "training_effect": self.training_effect,
            "user_feedback": self.user_feedback
        }


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
    
    # 三轨评分筛选配置 @requirements 4.3
    three_track_filtering: bool = True           # 是否启用三轨评分筛选
    min_ux_score: float = 4.0                    # 最低用户体验评分
    min_personalization_score: float = 4.0       # 最低个性化感知评分
    min_expert_score: float = 4.0                # 最低专家评分
    safety_veto_threshold: int = 3               # 安全性一票否决门槛
    only_fewshot_eligible: bool = True           # 只返回符合Few-Shot条件的


class EnhancedFewShotRetriever:
    """
    增强版Few-Shot检索器

    核心特性：
    1. 质量过滤：基于用户评分和质量评分
    2. 动态相似度阈值：根据查询复杂度调整
    3. 多样性保证：避免结果过于相似
    4. 自动化：与模型选择策略无缝集成
    5. 性能监控：详细的检索统计
    """

    def __init__(
        self,
        vector_store=None,
        backend_client=None,
        config: Optional[FewShotConfig] = None
    ):
        """
        初始化增强版Few-Shot检索器

        Args:
            vector_store: 向量存储实例
            backend_client: 后端客户端实例
            config: Few-Shot配置
        """
        self.vector_store = vector_store
        self.backend_client = backend_client
        self.config = config or FewShotConfig()

        # 初始化BestPracticesRetriever
        if BestPracticesRetriever:
            self.best_practices_retriever = BestPracticesRetriever(
                backend_client=backend_client,
                vector_store=vector_store,
                min_quality_threshold=4.0,
                min_usage_threshold=3
            )
            logger.info("✓ BestPracticesRetriever integrated")
        else:
            self.best_practices_retriever = None
            logger.warning("⚠ BestPracticesRetriever not available")

        # 性能统计
        self.stats = {
            "total_retrievals": 0,
            "avg_similarity": 0.0,
            "avg_quality": 0.0,
            "cache_hits": 0,
            "diversity_filtered": 0,
            "quality_filtered": 0,
            "best_practices_used": 0
        }

        # 查询复杂度分类器（懒加载）
        self._query_classifier = None

        logger.info(
            f"EnhancedFewShotRetriever initialized: "
            f"min_rating={self.config.min_rating_threshold}, "
            f"max_examples={self.config.max_examples}"
        )

    async def retrieve_with_quality_filter(
        self,
        query: str,
        user_id: Optional[str] = None,
        query_complexity: Optional[bool] = None,
        top_k: Optional[int] = None
    ) -> Tuple[List[FewShotExample], Dict[str, Any]]:
        """
        基于质量过滤的Few-Shot检索

        Args:
            query: 当前查询
            user_id: 用户ID（用于个性化检索）
            query_complexity: 查询复杂度（True=复杂，False=简单）
            top_k: 返回的示例数量

        Returns:
            Tuple[List[FewShotExample], Dict[str, Any]]:
                (Few-Shot示例列表, 检索统计信息)
        """
        start_time = datetime.now()
        self.stats["total_retrievals"] += 1

        try:
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
            self.stats["quality_filtered"] += len(raw_candidates) - len(quality_filtered)

            # 4. 相似度过滤
            similarity_filtered = self._filter_by_similarity(
                quality_filtered, similarity_threshold
            )

            # 5. 多样性过滤
            diversity_filtered = self._ensure_diversity(similarity_filtered)
            self.stats["diversity_filtered"] += len(similarity_filtered) - len(diversity_filtered)

            # 6. 最终排序和截取
            final_examples = self._rank_and_select(diversity_filtered, query)

            # 7. 更新统计信息
            await self._update_statistics(final_examples)

            # 8. 构建检索统计
            retrieval_stats = {
                "query_complexity": query_complexity,
                "similarity_threshold": similarity_threshold,
                "total_candidates": len(raw_candidates),
                "quality_filtered": len(raw_candidates) - len(quality_filtered),
                "similarity_filtered": len(quality_filtered) - len(similarity_filtered),
                "diversity_filtered": len(similarity_filtered) - len(diversity_filtered),
                "final_examples": len(final_examples),
                "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "avg_quality": np.mean([ex.quality_score for ex in final_examples]) if final_examples else 0.0,
                "avg_similarity": np.mean([ex.similarity for ex in final_examples]) if final_examples else 0.0
            }

            logger.info(
                f"Few-Shot检索完成: {len(final_examples)}/{len(raw_candidates)} 示例, "
                f"平均质量={retrieval_stats['avg_quality']:.2f}, "
                f"耗时={retrieval_stats['execution_time_ms']:.0f}ms"
            )

            return final_examples, retrieval_stats

        except Exception as e:
            logger.error(f"Few-Shot检索失败: {e}")
            return [], {"error": str(e), "execution_time_ms": 0}

    async def _determine_similarity_threshold(
        self,
        query: str,
        query_complexity: Optional[bool]
    ) -> float:
        """
        动态确定相似度阈值

        Args:
            query: 查询文本
            query_complexity: 查询复杂度

        Returns:
            float: 相似度阈值
        """
        if not self.config.adaptive_mode:
            return self.config.default_similarity_threshold

        # 如果已提供复杂度，直接使用对应阈值
        if query_complexity is not None:
            return (
                self.config.complex_query_threshold
                if query_complexity
                else self.config.simple_query_threshold
            )

        # 懒加载查询复杂度分类器
        if self._query_classifier is None:
            try:
                from ..models.query_complexity_classifier import QueryComplexityClassifier
                self._query_classifier = QueryComplexityClassifier()
            except Exception as e:
                logger.warning(f"无法加载查询复杂度分类器: {e}")
                return self.config.default_similarity_threshold

        # 使用分类器确定复杂度
        try:
            is_complex, similarity, _ = self._query_classifier.classify_complexity(query)
            threshold = (
                self.config.complex_query_threshold
                if is_complex
                else self.config.simple_query_threshold
            )

            logger.debug(f"查询复杂度分类: {is_complex}, 阈值: {threshold}")
            return threshold

        except Exception as e:
            logger.warning(f"查询复杂度分类失败: {e}")
            return self.config.default_similarity_threshold

    async def _initial_vector_search(
        self,
        query: str,
        user_id: Optional[str],
        top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """
        初始向量搜索

        Args:
            query: 查询文本
            user_id: 用户ID
            top_k: 检索数量

        Returns:
            List[Dict[str, Any]]: 原始候选结果
        """
        try:
            if self.vector_store:
                # 使用向量存储检索
                results = await self.vector_store.search_conversations(
                    query=query,
                    user_id=user_id,
                    top_k=top_k,
                    filters={
                        "min_rating": self.config.min_rating_threshold,
                        "days_back": 90  # 最近90天的对话
                    }
                )
                return results
            else:
                # 降级到后端API
                if self.backend_client:
                    results = await self.backend_client.search_similar_conversations(
                        query=query,
                        user_id=user_id,
                        limit=top_k,
                        min_rating=self.config.min_rating_threshold
                    )
                    return results.get("conversations", [])
                else:
                    logger.warning("无可用的向量存储或后端客户端")
                    return []

        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    def _filter_by_quality(self, candidates: List[Dict[str, Any]]) -> List[FewShotExample]:
        """
        基于质量过滤候选结果（包含三轨评分筛选）

        @requirements 4.3 - 检索时过滤低评分案例

        Args:
            candidates: 原始候选结果

        Returns:
            List[FewShotExample]: 质量过滤后的示例
        """
        filtered = []

        for candidate in candidates:
            try:
                # 提取质量指标
                user_rating = float(candidate.get("user_rating", 0))
                quality_score = float(candidate.get("quality_score", 0))

                # 基础质量过滤
                if (user_rating < self.config.min_rating_threshold or
                    quality_score < self.config.min_quality_threshold):
                    continue
                
                # 三轨评分筛选 @requirements 4.3
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
                        pers_avg = three_track_scores.get("personalization_avg")
                        if pers_avg is not None and pers_avg < self.config.min_personalization_score:
                            continue
                        
                        # 专家评分检查（如果有）
                        expert_avg = three_track_scores.get("expert_avg")
                        if expert_avg is not None and expert_avg < self.config.min_expert_score:
                            continue
                        
                        # 安全性一票否决
                        safety_score = three_track_scores.get("safety_score")
                        if safety_score is not None and safety_score < self.config.safety_veto_threshold:
                            logger.debug(f"安全性一票否决: session_id={candidate.get('session_id')}, safety={safety_score}")
                            continue

                example = FewShotExample(
                    query=candidate.get("query", ""),
                    response=candidate.get("response", ""),
                    user_rating=user_rating,
                    quality_score=quality_score,
                    similarity=float(candidate.get("similarity", 0)),
                    tools_used=candidate.get("tools_used", []),
                    model_used=candidate.get("model_used", ""),
                    timestamp=datetime.fromisoformat(
                        candidate.get("timestamp", datetime.now().isoformat())
                    ),
                    session_id=candidate.get("session_id", ""),
                    metadata=candidate.get("metadata", {}),
                    # ✅ v1.1.0新增：训练案例库字段
                    training_effect=candidate.get("training_effect"),
                    user_feedback=candidate.get("user_feedback")
                )
                filtered.append(example)

            except Exception as e:
                logger.debug(f"质量过滤时跳过无效候选: {e}")
                continue

        return filtered

    def _filter_by_similarity(
        self,
        examples: List[FewShotExample],
        threshold: float
    ) -> List[FewShotExample]:
        """
        基于相似度过滤

        Args:
            examples: 示例列表
            threshold: 相似度阈值

        Returns:
            List[FewShotExample]: 相似度过滤后的示例
        """
        return [ex for ex in examples if ex.similarity >= threshold]

    def _ensure_diversity(
        self,
        examples: List[FewShotExample]
    ) -> List[FewShotExample]:
        """
        确保结果多样性

        Args:
            examples: 示例列表

        Returns:
            List[FewShotExample]: 多样化后的示例
        """
        if len(examples) <= 2:
            return examples

        diverse = [examples[0]]  # 总是包含最相似的

        for ex in examples[1:]:
            # 检查与已选择示例的相似性
            is_diverse = True
            for selected in diverse:
                # 简单的文本相似性检查
                similarity = self._calculate_text_similarity(ex.query, selected.query)
                if similarity > self.config.diversity_threshold:
                    is_diverse = False
                    break

            if is_diverse:
                diverse.append(ex)
                if len(diverse) >= self.config.max_examples:
                    break

        return diverse

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似性（简化版）

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            float: 相似度 (0-1)
        """
        # 简单的词汇重叠计算
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = words1 & words2
        union = words1 | words2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _rank_and_select(
        self,
        examples: List[FewShotExample],
        query: str
    ) -> List[FewShotExample]:
        """
        最终排序和选择

        Args:
            examples: 示例列表
            query: 当前查询

        Returns:
            List[FewShotExample]: 排序后的示例
        """
        def calculate_final_score(example: FewShotExample) -> float:
            """
            计算最终评分

            评分公式：
            final_score = w1 * similarity + w2 * quality + w3 * recency
            """
            # 1. 相似度评分
            similarity_score = example.similarity

            # 2. 质量评分
            quality_score = example.quality_score / 5.0  # 归一化到0-1

            # 3. 时效性评分（最近的对话得分更高）
            days_old = (datetime.now() - example.timestamp).days
            recency_score = max(0, 1 - days_old / 90)  # 90天内的对话

            # 加权计算
            final_score = (
                self.config.similarity_weight * similarity_score +
                self.config.quality_weight * quality_score +
                self.config.recency_weight * recency_score
            )

            return final_score

        # 计算最终评分并排序
        scored_examples = [(ex, calculate_final_score(ex)) for ex in examples]
        scored_examples.sort(key=lambda x: x[1], reverse=True)

        # 选择top-k
        selected = [ex for ex, score in scored_examples[:self.config.max_examples]]

        return selected

    async def _update_statistics(self, examples: List[FewShotExample]):
        """更新统计信息"""
        if not examples:
            return

        # 更新平均质量
        avg_quality = np.mean([ex.quality_score for ex in examples])
        self.stats["avg_quality"] = (
            (self.stats["avg_quality"] * (self.stats["total_retrievals"] - 1) + avg_quality) /
            self.stats["total_retrievals"]
        )

        # 更新平均相似度
        avg_similarity = np.mean([ex.similarity for ex in examples])
        self.stats["avg_similarity"] = (
            (self.stats["avg_similarity"] * (self.stats["total_retrievals"] - 1) + avg_similarity) /
            self.stats["total_retrievals"]
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取检索统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["total_retrievals"] - self.stats.get("errors", 0)
            ) / max(self.stats["total_retrievals"], 1) * 100,
            "avg_examples_per_retrieval": (
                self.stats.get("total_examples_returned", 0) / max(self.stats["total_retrievals"], 1)
            )
        }

    def should_use_teacher_model(
        self,
        few_shot_count: int,
        query_complexity: Optional[bool] = None
    ) -> bool:
        """
        基于Few-Shot结果决定是否使用教师模型

        Args:
            few_shot_count: Few-Shot示例数量
            query_complexity: 查询复杂度

        Returns:
            bool: 是否使用教师模型
        """
        # 如果查询复杂且Few-Shot不足，使用教师模型
        if query_complexity and few_shot_count < 3:
            return True

        # 如果查询简单但Few-Shot很少，使用教师模型保险
        if not query_complexity and few_shot_count < 2:
            return True

        # 如果Few-Shot充足，可以使用学生模型
        if few_shot_count >= 3:
            return False

        # 默认使用教师模型（保守策略）
        return True

    async def get_best_practices(
        self,
        query: str,
        user_profile: Optional[Dict[str, Any]] = None,
        domain: str = "fitness",
        top_k: int = 3
    ) -> List[BestPracticeMatch]:
        """
        获取最佳实践（集成BestPracticesRetriever）

        Args:
            query: 用户查询
            user_profile: 用户档案
            domain: 领域
            top_k: 返回数量

        Returns:
            List[BestPracticeMatch]: 最佳实践匹配列表
        """
        if not self.best_practices_retriever:
            logger.warning("BestPracticesRetriever not available")
            return []

        try:
            matches = await self.best_practices_retriever.retrieve_best_practices(
                query=query,
                user_profile=user_profile,
                domain=domain,
                top_k=top_k
            )

            if matches:
                self.stats["best_practices_used"] += len(matches)
                logger.info(f"Retrieved {len(matches)} best practices for query")

            return matches

        except Exception as e:
            logger.error(f"Get best practices failed: {e}")
            return []

    async def _evaluate_few_shot_quality(
        self,
        few_shot_examples: Optional[List[FewShotExample]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        评估Few-Shot示例的质量

        Args:
            few_shot_examples: Few-Shot示例列表（可选）
            context: 上下文信息，包含user_id和query等

        Returns:
            Dict[str, Any]: 质量评估结果
        """
        try:
            # 如果没有提供示例，尝试检索一些
            if few_shot_examples is None:
                user_id = context.get("user_id") if context else None
                query = context.get("query") if context else ""

                few_shot_examples, _ = await self.retrieve_with_quality_filter(
                    query=query,
                    user_id=user_id,
                    top_k=3
                )

            if not few_shot_examples:
                return {
                    "quality_score": 0.0,
                    "example_count": 0,
                    "avg_similarity": 0.0,
                    "avg_quality": 0.0,
                    "recommendation": "insufficient_examples",
                    "should_use_teacher_model": True
                }

            # 计算质量指标
            example_count = len(few_shot_examples)
            avg_similarity = np.mean([ex.similarity for ex in few_shot_examples])
            avg_quality = np.mean([ex.quality_score for ex in few_shot_examples])

            # 质量评分计算 (0-100)
            quality_score = (
                (avg_similarity * 40) +  # 相似度权重40%
                (avg_quality * 20) +     # 质量权重20%
                (min(example_count, 5) / 5 * 40)  # 数量权重40%
            )

            # 推荐策略
            if quality_score >= 80:
                recommendation = "excellent"
                should_use_teacher_model = False
            elif quality_score >= 60:
                recommendation = "good"
                should_use_teacher_model = False
            elif quality_score >= 40:
                recommendation = "acceptable"
                should_use_teacher_model = True
            else:
                recommendation = "poor"
                should_use_teacher_model = True

            logger.debug(
                f"Few-Shot质量评估: score={quality_score:.1f}, "
                f"count={example_count}, recommendation={recommendation}"
            )

            return {
                "quality_score": quality_score,
                "example_count": example_count,
                "avg_similarity": avg_similarity,
                "avg_quality": avg_quality,
                "recommendation": recommendation,
                "should_use_teacher_model": should_use_teacher_model,
                "examples": [ex.to_dict() for ex in few_shot_examples]
            }

        except Exception as e:
            logger.error(f"Few-Shot质量评估失败: {e}")
            return {
                "quality_score": 0.0,
                "example_count": 0,
                "avg_similarity": 0.0,
                "avg_quality": 0.0,
                "recommendation": "error",
                "should_use_teacher_model": True,
                "error": str(e)
            }


# 导出
__all__ = [
    "EnhancedFewShotRetriever",
    "FewShotExample",
    "FewShotConfig",
    "BestPractice",
    "BestPracticeMatch"
]