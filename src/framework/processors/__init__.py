# -*- coding: utf-8 -*-
"""
DAML-RAG框架结果处理器

提供框架层通用结果处理器的实现。

版本：v2.0.0
日期：2025-11-26
"""

from .base_processor import (
    BaseResultProcessor,
    BaseSummarizationProcessor,
    BaseRecommendationProcessor
)

__all__ = [
    'BaseResultProcessor',
    'BaseSummarizationProcessor',
    'BaseRecommendationProcessor'
]
