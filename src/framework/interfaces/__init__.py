# -*- coding: utf-8 -*-
"""
DAML-RAG框架通用接口

提供框架层与应用层解耦的通用接口：
- IDomainAdapter: 领域适配器接口
- IResultProcessor: 结果处理器接口

版本：v2.1.0
日期：2026-01-12
"""

from .adapter_interfaces import (
    IDomainAdapter,
    IQueryAdapter,
    IWorkflowAdapter,
    AdapterContext,
    AdapterResult,
    AdapterRegistry
)

from .result_processor import (
    IResultProcessor,
    ISummarizationProcessor,
    IRecommendationProcessor,
    ProcessingStrategy,
    ProcessingOptions,
    ProcessingResult,
    ProcessorRegistry
)

__all__ = [
    # 适配器相关
    'IDomainAdapter',
    'IQueryAdapter',
    'IWorkflowAdapter',
    'AdapterContext',
    'AdapterResult',
    'AdapterRegistry',

    # 结果处理器相关
    'IResultProcessor',
    'ISummarizationProcessor',
    'IRecommendationProcessor',
    'ProcessingStrategy',
    'ProcessingOptions',
    'ProcessingResult',
    'ProcessorRegistry'
]
