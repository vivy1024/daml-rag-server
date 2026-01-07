# -*- coding: utf-8 -*-
"""
Models Layer - 模型层（v3.0精简版）

模块：
- query_complexity_classifier.py: 查询复杂度分类器
- adaptive_model_selector.py: 自适应模型选择器
- model_cache_manager.py: 全局模型缓存管理器
"""

# 导入存在的模块
try:
    from .query_complexity_classifier import QueryComplexityClassifier
    __all__ = ["QueryComplexityClassifier"]
except ImportError:
    pass

try:
    from .adaptive_model_selector import AdaptiveModelSelector, AdaptiveConfig
    if "QueryComplexityClassifier" in __all__:
        __all__.extend(["AdaptiveModelSelector", "AdaptiveConfig"])
    else:
        __all__ = ["AdaptiveModelSelector", "AdaptiveConfig"]
except ImportError:
    pass

try:
    from .model_cache_manager import ModelCacheManager
    if "__all__" in dir():
        __all__.append("ModelCacheManager")
    else:
        __all__ = ["ModelCacheManager"]
except ImportError:
    pass

