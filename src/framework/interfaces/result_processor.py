# -*- coding: utf-8 -*-
"""
结果处理器基础接口

定义所有结果处理器必须实现的通用接口，用于处理和格式化检索结果。

版本：v2.0.0
日期：2025-11-26
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

import logging

logger = logging.getLogger(__name__)


class ProcessingStrategy(Enum):
    """处理策略"""
    SUMMARY = "summary"  # 摘要
    DETAILED = "detailed"  # 详细
    COMPARATIVE = "comparative"  # 对比
    RECOMMENDATION = "recommendation"  # 推荐
    ANALYSIS = "analysis"  # 分析


@dataclass
class ProcessingOptions:
    """处理选项"""
    strategy: ProcessingStrategy = ProcessingStrategy.SUMMARY
    max_length: int = 1000
    include_reasoning: bool = True
    include_sources: bool = True
    format: str = "markdown"  # markdown, json, text
    language: str = "zh-CN"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool
    processed_text: str = ""
    raw_results: List[Any] = None
    reasoning: Optional[Dict[str, Any]] = None
    sources: List[Dict[str, Any]] = None
    confidence_score: float = 0.0
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.raw_results is None:
            self.raw_results = []
        if self.sources is None:
            self.sources = []
        if self.metadata is None:
            self.metadata = {}


class IResultProcessor(ABC):
    """
    结果处理器接口

    负责将原始检索结果转换为用户友好的格式
    """

    def __init__(self, domain: str):
        """
        初始化结果处理器

        Args:
            domain: 领域名称（如 'fitness', 'nutrition', 'rehabilitation'）
        """
        self.domain = domain
        self.is_initialized = False
        logger.info(f"创建结果处理器: {domain}")

    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化处理器

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    async def process(
        self,
        raw_results: List[Any],
        user_profile: Dict[str, Any],
        options: Optional[ProcessingOptions] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        处理结果

        Args:
            raw_results: 原始检索结果
            user_profile: 用户档案
            options: 处理选项
            **kwargs: 额外参数

        Returns:
            ProcessingResult: 处理后的结果
        """
        pass

    @abstractmethod
    async def get_supported_strategies(self) -> List[ProcessingStrategy]:
        """
        获取支持的处理策略

        Returns:
            List[ProcessingStrategy]: 支持的策略列表
        """
        pass

    async def validate_results(
        self,
        raw_results: List[Any]
    ) -> bool:
        """
        验证结果是否有效

        Args:
            raw_results: 原始结果

        Returns:
            bool: 是否有效
        """
        # 默认验证逻辑，子类可覆盖
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
        # 默认提取逻辑，子类可覆盖
        sources = []
        for result in raw_results:
            if isinstance(result, dict) and "source" in result:
                sources.append(result["source"])
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
        # 默认计算逻辑，子类可覆盖
        # 基于结果数量和用户匹配度计算
        if not raw_results:
            return 0.0
        return min(0.9, 0.5 + len(raw_results) * 0.05)

    def is_ready(self) -> bool:
        """
        检查处理器是否就绪

        Returns:
            bool: 是否已初始化并可用
        """
        return self.is_initialized

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict[str, Any]: 健康状态信息
        """
        return {
            "domain": self.domain,
            "initialized": self.is_initialized,
            "status": "healthy" if self.is_initialized else "not_initialized"
        }


class ISummarizationProcessor(IResultProcessor):
    """
    摘要处理器接口

    专门用于生成摘要的结果处理器
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass


class IRecommendationProcessor(IResultProcessor):
    """
    推荐处理器接口

    专门用于生成推荐的处理器
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass


# 注册表用于管理所有处理器
class ProcessorRegistry:
    """处理器注册表"""

    _processors: Dict[str, type] = {}
    _instances: Dict[str, IResultProcessor] = {}

    @classmethod
    def register(cls, domain: str, processor_class: type):
        """
        注册处理器类

        Args:
            domain: 领域名称
            processor_class: 处理器类
        """
        cls._processors[domain] = processor_class
        logger.info(f"注册结果处理器: {domain} -> {processor_class.__name__}")

    @classmethod
    def get_processor_class(cls, domain: str) -> Optional[type]:
        """
        获取处理器类

        Args:
            domain: 领域名称

        Returns:
            Optional[type]: 处理器类或None
        """
        return cls._processors.get(domain)

    @classmethod
    async def get_processor(
        cls,
        domain: str,
        **kwargs
    ) -> Optional[IResultProcessor]:
        """
        获取处理器实例（单例）

        Args:
            domain: 领域名称
            **kwargs: 初始化参数

        Returns:
            Optional[IResultProcessor]: 处理器实例或None
        """
        if domain not in cls._instances:
            processor_class = cls.get_processor_class(domain)
            if processor_class:
                processor = processor_class(domain, **kwargs)
                await processor.initialize()
                cls._instances[domain] = processor
                return processor
            return None
        return cls._instances[domain]

    @classmethod
    def list_domains(cls) -> List[str]:
        """
        列出所有已注册的领域

        Returns:
            List[str]: 领域名称列表
        """
        return list(cls._processors.keys())
