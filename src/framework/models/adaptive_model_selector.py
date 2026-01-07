# -*- coding: utf-8 -*-
"""
Adaptive Model Selector - 自适应模型选择器

基于动态阈值和历史成功率的智能模型选择

核心改进：
1. 动态阈值调整：基于历史成功率自动调整阈值
2. 成本敏感度控制：可配置的成本优化策略
3. 多因子决策：综合查询复杂度、Few-Shot质量、历史表现
4. 学习机制：从历史决策中学习优化策略

版本: v1.0.0
日期: 2025-12-03
作者: 薛小川
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import json

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """模型类型枚举"""
    TEACHER = "teacher"  # DeepSeek (高质量，付费)
    STUDENT = "student"  # Ollama (低成本，免费)


@dataclass
class SelectionDecision:
    """模型选择决策"""
    model_type: ModelType
    confidence: float
    reasoning: str
    factors: Dict[str, float]
    threshold_used: float
    cost_estimate: float
    expected_quality: float


@dataclass
class ModelPerformance:
    """模型性能记录"""
    model_type: ModelType
    success_rate: float
    avg_response_time: float
    avg_quality_score: float
    total_usage: int
    recent_successes: List[bool] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class AdaptiveConfig:
    """自适应配置"""
    # 基础阈值
    base_high_threshold: float = 0.7
    base_low_threshold: float = 0.5

    # 动态调整参数
    threshold_adjustment_factor: float = 0.1  # 阈值调整幅度
    success_rate_weight: float = 0.3          # 成功率权重
    cost_sensitivity: float = 0.5              # 成本敏感度 (0=质量优先, 1=成本优先)

    # 学习参数
    learning_window_size: int = 20             # 学习窗口大小
    min_samples_for_adjustment: int = 5       # 调整所需最小样本数

    # 成本参数
    teacher_cost_per_token: float = 0.001     # DeepSeek成本
    student_cost_per_token: float = 0.0       # Ollama成本（免费）
    avg_tokens_per_request: int = 1000        # 平均token数


class AdaptiveModelSelector:
    """
    自适应模型选择器

    核心特性：
    1. 动态阈值调整：基于历史成功率自动优化阈值
    2. 成本敏感决策：可配置的成本/质量平衡策略
    3. 多因子评估：综合查询复杂度、Few-Shot质量、历史表现
    4. 持续学习：从每次决策结果中学习和改进
    5. 性能监控：详细的决策统计和性能跟踪
    """

    def __init__(
        self,
        config: Optional[AdaptiveConfig] = None,
        query_complexity_classifier=None,
        few_shot_retriever=None
    ):
        """
        初始化自适应模型选择器

        Args:
            config: 自适应配置
            query_complexity_classifier: 查询复杂度分类器
            few_shot_retriever: Few-Shot检索器
        """
        self.config = config or AdaptiveConfig()
        self.query_complexity_classifier = query_complexity_classifier
        self.few_shot_retriever = few_shot_retriever

        # 当前动态阈值
        self.current_high_threshold = self.config.base_high_threshold
        self.current_low_threshold = self.config.base_low_threshold

        # 模型性能记录
        self.model_performance = {
            ModelType.TEACHER: ModelPerformance(
                model_type=ModelType.TEACHER,
                success_rate=0.95,  # 教师模型初始高成功率
                avg_response_time=2.0,
                avg_quality_score=4.5,
                total_usage=0
            ),
            ModelType.STUDENT: ModelPerformance(
                model_type=ModelType.STUDENT,
                success_rate=0.80,  # 学生模型初始成功率
                avg_response_time=0.8,
                avg_quality_score=3.8,
                total_usage=0
            )
        }

        # 决策历史
        self.decision_history: List[Dict[str, Any]] = []

        # 统计信息
        self.stats = {
            "total_decisions": 0,
            "teacher_selections": 0,
            "student_selections": 0,
            "correct_decisions": 0,
            "cost_savings": 0.0,
            "avg_confidence": 0.0
        }

        logger.info(
            f"AdaptiveModelSelector initialized: "
            f"cost_sensitivity={self.config.cost_sensitivity}, "
            f"thresholds=[{self.current_low_threshold:.2f}, {self.current_high_threshold:.2f}]"
        )

    async def select_model(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        few_shot_count: Optional[int] = None
    ) -> SelectionDecision:
        """
        智能模型选择

        Args:
            query: 用户查询
            user_context: 用户上下文信息
            few_shot_count: Few-Shot示例数量

        Returns:
            SelectionDecision: 模型选择决策
        """
        start_time = datetime.now()
        self.stats["total_decisions"] += 1

        try:
            # 1. 获取查询复杂度
            is_complex, similarity_score, complexity_reason = await self._get_query_complexity(query)

            # 2. 获取Few-Shot质量（如果可用）
            few_shot_quality = await self._evaluate_few_shot_quality(few_shot_count, user_context)

            # 3. 计算历史成功率加权
            history_weight = self._calculate_history_weight(is_complex)

            # 4. 动态调整阈值
            adjusted_thresholds = self._get_adjusted_thresholds()

            # 5. 多因子决策
            decision = await self._make_multi_factor_decision(
                query, is_complex, similarity_score, few_shot_quality, history_weight, adjusted_thresholds
            )

            # 6. 更新统计
            self._update_stats(decision)

            # 7. 记录决策
            self._record_decision(query, decision, is_complex, similarity_score, few_shot_count)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                f"模型选择完成: {decision.model_type.value}, "
                f"置信度={decision.confidence:.2f}, "
                f"耗时={execution_time:.0f}ms, "
                f"理由={decision.reasoning[:50]}..."
            )

            return decision

        except Exception as e:
            logger.error(f"模型选择失败: {e}")
            # 降级到教师模型（保守策略）
            return SelectionDecision(
                model_type=ModelType.TEACHER,
                confidence=0.5,
                reasoning=f"决策失败，降级到教师模型: {str(e)}",
                factors={},
                threshold_used=self.current_high_threshold,
                cost_estimate=self.config.teacher_cost_per_token * self.config.avg_tokens_per_request,
                expected_quality=4.0
            )

    async def _get_query_complexity(self, query: str) -> Tuple[bool, float, str]:
        """获取查询复杂度"""
        if self.query_complexity_classifier:
            try:
                is_complex, similarity, reason = self.query_complexity_classifier.classify_complexity(query)
                return is_complex, similarity, reason
            except Exception as e:
                logger.warning(f"查询复杂度分类失败: {e}")

        # 降级到简单启发式规则
        complex_keywords = ['计划', '设计', '方案', '康复', '个性化', '营养']
        is_complex = any(keyword in query for keyword in complex_keywords)
        similarity = 0.8 if is_complex else 0.3
        reason = "启发式规则" + ("(复杂)" if is_complex else "(简单)")

        return is_complex, similarity, reason

    async def _evaluate_few_shot_quality(
        self,
        few_shot_count: Optional[int],
        user_context: Optional[Dict[str, Any]]
    ) -> float:
        """
        评估Few-Shot质量

        Args:
            few_shot_count: Few-Shot示例数量
            user_context: 用户上下文

        Returns:
            float: Few-Shot质量评分 (0-1)
        """
        if few_shot_count is None:
            # 尝试从Few-Shot检索器获取
            if self.few_shot_retriever and user_context:
                try:
                    examples, stats = await self.few_shot_retriever.retrieve_with_quality_filter(
                        query=user_context.get("query", ""),
                        user_id=user_context.get("user_id")
                    )
                    few_shot_count = len(examples)
                except Exception as e:
                    logger.debug(f"Few-Shot检索失败: {e}")
                    few_shot_count = 0

        # 基于数量计算质量评分
        if few_shot_count >= 5:
            return 1.0
        elif few_shot_count >= 3:
            return 0.8
        elif few_shot_count >= 1:
            return 0.6
        else:
            return 0.0

    def _calculate_history_weight(self, is_complex: bool) -> float:
        """
        计算历史成功率权重

        Args:
            is_complex: 是否复杂查询

        Returns:
            float: 历史权重 (0-1)
        """
        teacher_perf = self.model_performance[ModelType.TEACHER]
        student_perf = self.model_performance[ModelType.STUDENT]

        if is_complex:
            # 复杂查询更重视历史成功率
            return teacher_perf.success_rate - student_perf.success_rate
        else:
            # 简单查询可以容忍更低的成功率
            return (teacher_perf.success_rate - student_perf.success_rate) * 0.5

    def _get_adjusted_thresholds(self) -> Tuple[float, float]:
        """
        获取动态调整后的阈值

        Returns:
            Tuple[float, float]: (低阈值, 高阈值)
        """
        # 基于历史成功率调整阈值
        teacher_success = self.model_performance[ModelType.TEACHER].success_rate
        student_success = self.model_performance[ModelType.STUDENT].success_rate

        # 如果学生模型表现良好，降低高阈值（更多使用学生模型）
        if student_success > 0.85:
            adjustment = self.config.threshold_adjustment_factor * (student_success - 0.85) * 2
            high_threshold = max(
                self.config.base_low_threshold + 0.1,
                self.current_high_threshold - adjustment
            )
        else:
            # 如果学生模型表现不佳，提高阈值（更多使用教师模型）
            adjustment = self.config.threshold_adjustment_factor * (0.85 - student_success)
            high_threshold = min(
                0.95,
                self.current_high_threshold + adjustment
            )

        # 低阈值调整相对保守
        low_threshold = max(
            0.2,
            self.current_low_threshold
        )

        return low_threshold, high_threshold

    async def _make_multi_factor_decision(
        self,
        query: str,
        is_complex: bool,
        similarity_score: float,
        few_shot_quality: float,
        history_weight: float,
        thresholds: Tuple[float, float]
    ) -> SelectionDecision:
        """
        多因子决策

        Args:
            query: 查询文本
            is_complex: 是否复杂查询
            similarity_score: 相似度分数
            few_shot_quality: Few-Shot质量
            history_weight: 历史权重
            thresholds: 调整后的阈值

        Returns:
            SelectionDecision: 最终决策
        """
        low_threshold, high_threshold = thresholds

        # 因子评分
        factors = {
            "similarity": similarity_score,
            "few_shot_quality": few_shot_quality,
            "history_weight": history_weight,
            "complexity_penalty": 0.2 if is_complex else 0.0,
            "cost_sensitivity": self.config.cost_sensitivity
        }

        # 综合评分
        # 复杂查询：偏向教师模型
        # 简单查询 + 高质量Few-Shot：偏向学生模型
        if is_complex:
            if similarity_score >= high_threshold or few_shot_quality < 0.5:
                # 复杂查询且相似度高 或 Few-Shot质量差 -> 教师模型
                model_type = ModelType.TEACHER
                confidence = 0.9
                reasoning = f"复杂查询，相似度{similarity_score:.2f}>=高阈值{high_threshold:.2f}"
            elif similarity_score <= low_threshold and few_shot_quality >= 0.8:
                # 复杂查询但相似度低且Few-Shot质量好 -> 可以尝试学生模型
                model_type = ModelType.STUDENT
                confidence = 0.7
                reasoning = f"复杂查询但Few-Shot质量高({few_shot_quality:.2f})，尝试学生模型"
            else:
                # 中等情况，考虑成本
                cost_factor = 1 - self.config.cost_sensitivity
                if cost_factor > 0.5:  # 更重视质量
                    model_type = ModelType.TEACHER
                    confidence = 0.8
                    reasoning = "复杂查询，优先考虑质量"
                else:
                    model_type = ModelType.STUDENT
                    confidence = 0.6
                    reasoning = "复杂查询，但成本敏感度高"
        else:
            # 简单查询
            if similarity_score <= low_threshold and few_shot_quality >= 0.6:
                # 简单查询且相似度低且Few-Shot质量好 -> 学生模型
                model_type = ModelType.STUDENT
                confidence = 0.9
                reasoning = f"简单查询，Few-Shot充足({few_shot_quality:.2f})，使用学生模型"
            else:
                # 其他情况，基于历史表现决定
                if history_weight > 0.1:
                    model_type = ModelType.TEACHER
                    confidence = 0.7
                    reasoning = f"基于历史表现选择教师模型（权重{history_weight:.2f}）"
                else:
                    model_type = ModelType.STUDENT
                    confidence = 0.6
                    reasoning = "简单查询，学生模型足够"

        # 估算成本
        cost_estimate = (
            self.config.teacher_cost_per_token if model_type == ModelType.TEACHER
            else self.config.student_cost_per_token
        ) * self.config.avg_tokens_per_request

        # 估算预期质量
        perf = self.model_performance[model_type]
        expected_quality = perf.avg_quality_score

        return SelectionDecision(
            model_type=model_type,
            confidence=confidence,
            reasoning=reasoning,
            factors=factors,
            threshold_used=high_threshold if model_type == ModelType.TEACHER else low_threshold,
            cost_estimate=cost_estimate,
            expected_quality=expected_quality
        )

    def _update_stats(self, decision: SelectionDecision):
        """更新统计信息"""
        if decision.model_type == ModelType.TEACHER:
            self.stats["teacher_selections"] += 1
        else:
            self.stats["student_selections"] += 1

        # 更新平均置信度
        total_confidence = self.stats["avg_confidence"] * (self.stats["total_decisions"] - 1) + decision.confidence
        self.stats["avg_confidence"] = total_confidence / self.stats["total_decisions"]

    def _record_decision(
        self,
        query: str,
        decision: SelectionDecision,
        is_complex: bool,
        similarity_score: float,
        few_shot_count: Optional[int]
    ):
        """记录决策历史"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "query_preview": query[:50] + "..." if len(query) > 50 else query,
            "model_type": decision.model_type.value,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "is_complex": is_complex,
            "similarity_score": similarity_score,
            "few_shot_count": few_shot_count,
            "cost_estimate": decision.cost_estimate,
            "threshold_used": decision.threshold_used
        }

        self.decision_history.append(record)

        # 限制历史记录大小
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-500:]

    async def record_outcome(
        self,
        decision: SelectionDecision,
        success: bool,
        quality_score: Optional[float] = None,
        response_time: Optional[float] = None
    ):
        """
        记录决策结果，用于学习和优化

        Args:
            decision: 原始决策
            success: 是否成功
            quality_score: 响应质量评分
            response_time: 响应时间
        """
        perf = self.model_performance[decision.model_type]

        # 更新成功率
        perf.recent_successes.append(success)
        if len(perf.recent_successes) > self.config.learning_window_size:
            perf.recent_successes.pop(0)

        # 计算新的成功率
        if len(perf.recent_successes) >= self.config.min_samples_for_adjustment:
            new_success_rate = sum(perf.recent_successes) / len(perf.recent_successes)
            perf.success_rate = new_success_rate

            # 触发阈值重新调整
            await self._adjust_thresholds_based_on_performance()

        # 更新其他性能指标
        if quality_score is not None:
            perf.avg_quality_score = (
                perf.avg_quality_score * 0.9 + quality_score * 0.1
            )

        if response_time is not None:
            perf.avg_response_time = (
                perf.avg_response_time * 0.9 + response_time * 0.1
            )

        perf.total_usage += 1
        perf.last_updated = datetime.now()

        # 更新统计
        if success:
            self.stats["correct_decisions"] += 1

        # 计算成本节省
        if decision.model_type == ModelType.STUDENT:
            cost_saved = self.config.teacher_cost_per_token * self.config.avg_tokens_per_request
            self.stats["cost_savings"] += cost_saved

        logger.info(
            f"记录决策结果: {decision.model_type.value}, "
            f"成功={success}, "
            f"当前成功率={perf.success_rate:.2f}"
        )

    async def _adjust_thresholds_based_on_performance(self):
        """基于性能数据动态调整阈值"""
        teacher_success = self.model_performance[ModelType.TEACHER].success_rate
        student_success = self.model_performance[ModelType.STUDENT].success_rate

        # 如果学生模型表现接近或超过教师模型，积极调整阈值
        if student_success >= teacher_success - 0.05:
            # 降低高阈值，更多使用学生模型
            new_high_threshold = max(
                self.config.base_low_threshold + 0.2,
                self.current_high_threshold - self.config.threshold_adjustment_factor
            )
            if abs(new_high_threshold - self.current_high_threshold) > 0.01:
                self.current_high_threshold = new_high_threshold
                logger.info(f"学生模型表现优异，降低高阈值至{new_high_threshold:.2f}")

        # 如果学生模型表现显著下降，提高阈值
        elif student_success < teacher_success - 0.15:
            # 提高阈值，更多使用教师模型
            new_high_threshold = min(
                0.9,
                self.current_high_threshold + self.config.threshold_adjustment_factor
            )
            if abs(new_high_threshold - self.current_high_threshold) > 0.01:
                self.current_high_threshold = new_high_threshold
                logger.info(f"学生模型表现下降，提高高阈值至{new_high_threshold:.2f}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        total = self.stats["total_decisions"]

        if total == 0:
            return {
                "total_decisions": 0,
                "teacher_usage_rate": 0,
                "student_usage_rate": 0,
                "success_rate": 0,
                "cost_savings": 0.0
            }

        return {
            **self.stats,
            "teacher_usage_rate": self.stats["teacher_selections"] / total * 100,
            "student_usage_rate": self.stats["student_selections"] / total * 100,
            "success_rate": self.stats["correct_decisions"] / total * 100,
            "current_thresholds": {
                "low": self.current_low_threshold,
                "high": self.current_high_threshold
            },
            "model_performance": {
                model_type.value: {
                    "success_rate": perf.success_rate,
                    "avg_quality": perf.avg_quality_score,
                    "avg_response_time": perf.avg_response_time,
                    "total_usage": perf.total_usage
                }
                for model_type, perf in self.model_performance.items()
            },
            "recent_decisions": self.decision_history[-10:] if self.decision_history else []
        }


# 导出
__all__ = [
    "AdaptiveModelSelector",
    "SelectionDecision",
    "ModelType",
    "ModelPerformance",
    "AdaptiveConfig"
]