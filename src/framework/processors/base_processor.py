# -*- coding: utf-8 -*-
"""
基础结果处理器实现

提供框架层通用结果处理器的默认实现。

版本：v2.0.0
日期：2025-11-26
"""

import time
import logging
from typing import Dict, Any, List, Optional
from abc import ABC

from ..interfaces.result_processor import (
    IResultProcessor,
    ISummarizationProcessor,
    IRecommendationProcessor,
    ProcessingStrategy,
    ProcessingOptions,
    ProcessingResult
)

logger = logging.getLogger(__name__)


class BaseResultProcessor(IResultProcessor):
    """
    基础结果处理器实现

    提供通用的结果处理功能，子类可继承并覆盖特定方法
    """

    def __init__(self, domain: str):
        """
        初始化基础结果处理器

        Args:
            domain: 领域名称
        """
        super().__init__(domain)
        self.templates = {}
        self.formatters = {}

    async def initialize(self) -> bool:
        """
        初始化处理器

        默认实现：加载模板和格式化器

        Returns:
            bool: 初始化是否成功
        """
        # 加载默认模板
        await self._load_default_templates()

        # 加载格式化器
        await self._load_formatters()

        self.is_initialized = True
        logger.info(f"基础结果处理器初始化完成: {self.domain}")
        return True

    async def process(
        self,
        raw_results: List[Any],
        user_profile: Dict[str, Any],
        options: Optional[ProcessingOptions] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        处理结果

        默认实现：使用默认摘要策略

        Args:
            raw_results: 原始检索结果
            user_profile: 用户档案
            options: 处理选项
            **kwargs: 额外参数

        Returns:
            ProcessingResult: 处理后的结果
        """
        start_time = time.time()

        # 设置默认选项
        if options is None:
            options = ProcessingOptions()

        # 验证结果
        if not await self.validate_results(raw_results):
            return ProcessingResult(
                success=False,
                error="无效的检索结果"
            )

        try:
            # 根据策略处理结果
            if options.strategy == ProcessingStrategy.SUMMARY:
                processed_text = await self._summarize(raw_results, options)
            elif options.strategy == ProcessingStrategy.DETAILED:
                processed_text = await self._detailed_process(raw_results, options)
            elif options.strategy == ProcessingStrategy.RECOMMENDATION:
                processed_text = await self._recommend(raw_results, user_profile, options)
            else:
                processed_text = await self._summarize(raw_results, options)

            # 提取信息源
            sources = await self.extract_sources(raw_results)

            # 计算置信度
            confidence = await self.calculate_confidence(raw_results, user_profile)

            # 后处理
            result = ProcessingResult(
                success=True,
                processed_text=processed_text,
                raw_results=raw_results,
                reasoning={"strategy": options.strategy.value},
                sources=sources,
                confidence_score=confidence,
                processing_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "domain": self.domain,
                    "processor": self.__class__.__name__,
                    "options": options.__dict__
                }
            )

            return result

        except Exception as e:
            logger.error(f"处理结果失败: {e}")
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )

    async def get_supported_strategies(self) -> List[ProcessingStrategy]:
        """
        获取支持的处理策略

        Returns:
            List[ProcessingStrategy]: 支持的策略列表
        """
        return list(ProcessingStrategy)

    async def validate_results(self, raw_results: List[Any]) -> bool:
        """
        验证结果是否有效

        Args:
            raw_results: 原始结果

        Returns:
            bool: 是否有效
        """
        # 默认验证：确保有结果且不为空
        return len(raw_results) > 0

    async def extract_sources(
        self,
        raw_results: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        提取信息源

        Args:
            raw_results: 原始结果

        Returns:
            List[Dict[str, Any]]: 信息源列表
        """
        sources = []
        for result in raw_results:
            if isinstance(result, dict):
                source = result.get("source")
                if source:
                    sources.append(source)
                # 也可以从metadata中提取
                metadata = result.get("metadata", {})
                if "source" in metadata:
                    sources.append(metadata["source"])

        return sources

    async def calculate_confidence(
        self,
        raw_results: List[Any],
        user_profile: Dict[str, Any]
    ) -> float:
        """
        计算置信度

        Args:
            raw_results: 原始结果
            user_profile: 用户档案

        Returns:
            float: 置信度分数 (0.0-1.0)
        """
        # 默认计算：基于结果数量和一致性
        if not raw_results:
            return 0.0

        # 基础分数：基于结果数量
        base_score = min(0.8, len(raw_results) * 0.1)

        # 调整分数：基于用户档案匹配
        if user_profile:
            # 检查是否有匹配的用户信息
            matches = sum(1 for result in raw_results if self._matches_user_profile(result, user_profile))
            match_ratio = matches / len(raw_results)
            base_score += match_ratio * 0.2

        return min(1.0, base_score)

    def _matches_user_profile(self, result: Any, user_profile: Dict[str, Any]) -> bool:
        """
        检查结果是否匹配用户档案

        Args:
            result: 单个结果
            user_profile: 用户档案

        Returns:
            bool: 是否匹配
        """
        # 默认实现：简单检查level或goal字段
        if isinstance(result, dict):
            result_level = result.get("level")
            result_goal = result.get("goal")
            user_level = user_profile.get("fitness_level")
            user_goal = user_profile.get("training_goal")

            if result_level and user_level and result_level.lower() == user_level.lower():
                return True
            if result_goal and user_goal and result_goal.lower() == user_goal.lower():
                return True

        return False

    async def _summarize(
        self,
        raw_results: List[Any],
        options: ProcessingOptions
    ) -> str:
        """
        生成摘要

        默认实现：简单的文本拼接

        Args:
            raw_results: 原始结果
            options: 处理选项

        Returns:
            str: 摘要文本
        """
        summary_parts = []

        # 获取模板
        template = self.templates.get("summary", "{title}: {content}")

        # 处理每个结果
        for i, result in enumerate(raw_results[:5]):  # 最多5个结果
            if isinstance(result, dict):
                title = result.get("name", f"结果 {i+1}")
                content = result.get("description", str(result))
                summary_parts.append(template.format(title=title, content=content))
            else:
                summary_parts.append(str(result))

        # 拼接摘要
        summary = "\n\n".join(summary_parts)

        # 限制长度
        if len(summary) > options.max_length:
            summary = summary[:options.max_length] + "..."

        return summary

    async def _detailed_process(
        self,
        raw_results: List[Any],
        options: ProcessingOptions
    ) -> str:
        """
        详细处理

        默认实现：返回详细格式的结果

        Args:
            raw_results: 原始结果
            options: 处理选项

        Returns:
            str: 详细文本
        """
        details = []

        for i, result in enumerate(raw_results):
            if isinstance(result, dict):
                detail_parts = []
                for key, value in result.items():
                    if key != "metadata":
                        detail_parts.append(f"**{key}**: {value}")
                details.append(f"## 结果 {i+1}\n\n" + "\n".join(detail_parts))

        return "\n\n".join(details)

    async def _recommend(
        self,
        raw_results: List[Any],
        user_profile: Dict[str, Any],
        options: ProcessingOptions
    ) -> str:
        """
        生成推荐

        默认实现：基于用户档案排序推荐

        Args:
            raw_results: 原始结果
            user_profile: 用户档案
            options: 处理选项

        Returns:
            str: 推荐文本
        """
        # 排序结果
        sorted_results = sorted(
            raw_results,
            key=lambda r: self._get_relevance_score(r, user_profile),
            reverse=True
        )

        # 生成推荐
        recommendations = []
        for i, result in enumerate(sorted_results[:3]):  # 推荐前3个
            if isinstance(result, dict):
                name = result.get("name", f"推荐 {i+1}")
                reason = result.get("reason", "基于您的档案推荐")
                recommendations.append(f"- **{name}**: {reason}")

        return "\n".join(recommendations)

    def _get_relevance_score(self, result: Any, user_profile: Dict[str, Any]) -> float:
        """
        计算相关性分数

        Args:
            result: 单个结果
            user_profile: 用户档案

        Returns:
            float: 相关性分数
        """
        # 默认实现：简单的匹配分数
        if not isinstance(result, dict):
            return 0.0

        score = 0.0

        # 匹配训练目标
        user_goal = user_profile.get("training_goal")
        result_goal = result.get("goal")
        if user_goal and result_goal and user_goal.lower() == result_goal.lower():
            score += 1.0

        # 匹配训练水平
        user_level = user_profile.get("fitness_level")
        result_level = result.get("level")
        if user_level and result_level and user_level.lower() == result_level.lower():
            score += 0.5

        return score

    async def _load_default_templates(self):
        """加载默认模板"""
        self.templates = {
            "summary": "{title}: {content}",
            "detailed": "## {title}\n\n{content}",
            "recommendation": "推荐: {title} - {reason}"
        }

    async def _load_formatters(self):
        """加载格式化器"""
        self.formatters = {
            "markdown": self._format_markdown,
            "json": self._format_json,
            "text": self._format_text
        }

    async def _format_markdown(self, text: str) -> str:
        """Markdown格式化"""
        return text

    async def _format_json(self, text: str) -> str:
        """JSON格式化"""
        return text

    async def _format_text(self, text: str) -> str:
        """纯文本格式化"""
        # 移除Markdown格式
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # 粗体
        text = re.sub(r'\*(.*?)\*', r'\1', text)  # 斜体
        return text


class BaseSummarizationProcessor(BaseResultProcessor, ISummarizationProcessor):
    """
    基础摘要处理器实现

    提供专门的摘要功能
    """

    async def summarize(
        self,
        raw_results: List[Any],
        max_length: int = 500,
        **kwargs
    ) -> ProcessingResult:
        """
        生成摘要

        Args:
            raw_results: 原始结果
            max_length: 最大长度
            **kwargs: 额外参数

        Returns:
            ProcessingResult: 摘要结果
        """
        options = ProcessingOptions(
            strategy=ProcessingStrategy.SUMMARY,
            max_length=max_length
        )

        return await self.process(raw_results, {}, options)

    async def extract_key_points(
        self,
        raw_results: List[Any],
        max_points: int = 5
    ) -> List[str]:
        """
        提取关键点

        Args:
            raw_results: 原始结果
            max_points: 最大关键点数量

        Returns:
            List[str]: 关键点列表
        """
        key_points = []

        for result in raw_results[:max_points]:
            if isinstance(result, dict):
                name = result.get("name", "")
                description = result.get("description", "")
                if description:
                    key_points.append(f"• {name}: {description}")
                else:
                    key_points.append(f"• {name}")

        return key_points


class BaseRecommendationProcessor(BaseResultProcessor, IRecommendationProcessor):
    """
    基础推荐处理器实现

    提供专门的推荐功能
    """

    async def generate_recommendations(
        self,
        raw_results: List[Any],
        user_profile: Dict[str, Any],
        num_recommendations: int = 5,
        **kwargs
    ) -> ProcessingResult:
        """
        生成推荐

        Args:
            raw_results: 原始结果
            user_profile: 用户档案
            num_recommendations: 推荐数量
            **kwargs: 额外参数

        Returns:
            ProcessingResult: 推荐结果
        """
        options = ProcessingOptions(
            strategy=ProcessingStrategy.RECOMMENDATION
        )

        return await self.process(raw_results, user_profile, options)

    async def rank_results(
        self,
        raw_results: List[Any],
        user_profile: Dict[str, Any],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        排序结果

        Args:
            raw_results: 原始结果
            user_profile: 用户档案
            **kwargs: 排序参数

        Returns:
            List[Dict[str, Any]]: 排序后的结果
        """
        # 为每个结果添加分数
        for result in raw_results:
            if isinstance(result, dict):
                result["relevance_score"] = self._get_relevance_score(result, user_profile)

        # 排序
        return sorted(
            raw_results,
            key=lambda r: r.get("relevance_score", 0),
            reverse=True
        )

    def _get_relevance_score(self, result: Any, user_profile: Dict[str, Any]) -> float:
        """
        计算相关性分数（覆盖父类方法）

        Args:
            result: 单个结果
            user_profile: 用户档案

        Returns:
            float: 相关性分数
        """
        return super()._get_relevance_score(result, user_profile)
