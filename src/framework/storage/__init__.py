# -*- coding: utf-8 -*-
"""
Storage Layer - 存储层

模块：
- user_memory.py: 用户级向量库管理器
- vector_store_abstract.py: 向量存储抽象层
- metadata_database.py: 元数据数据库
- intelligent_cache_manager.py: 智能缓存管理器
- progressive_warmup.py: 渐进式预热系统
- smart_preloader.py: 智能预热器（步骤1预热步骤3）
"""

from .user_memory import UserMemory
from .vector_store_abstract import (
    IVectorStore,
    QdrantVectorStore,
    FAISSVectorStore,
    PineconeVectorStore,
    Distance
)
from .metadata_database import MetadataDB
from .intelligent_cache_manager import (
    IntelligentCacheManager,
    CacheConfig,
    CacheLevel,
    CacheEntry,
    CacheStatistics
)
from .intelligent_user_profile_cache import (
    IntelligentUserCache,
    UserProfileEntry,
    PreloadPrediction,
    CacheConfig as UserCacheConfig,
    UserProfileStatus
)
from .intelligent_membership_cache import (
    IntelligentMembershipCache,
    MembershipCacheEntry
)
from .progressive_warmup import (
    ProgressiveWarmup,
    WarmupConfig,
    WarmupPhase,
    WarmupResult,
    WarmupStatistics,
    get_progressive_warmup,
    set_progressive_warmup,
    create_and_start_warmup
)
from .smart_preloader import (
    SmartPreloader,
    SmartPreloaderConfig,
    SmartPreloaderStatistics,
    PreloadTask,
    PreloadStatus,
    get_smart_preloader,
    set_smart_preloader,
    create_smart_preloader
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerMetrics,
    CircuitBreakerRegistry,
    CircuitState,
    CircuitOpenException,
    CircuitBreakerError,
    user_profile_circuit_breaker,
    membership_circuit_breaker
)
from .heat_map import (
    HeatMap,
    HeatMapConfig,
    HeatEntry,
    QueryEntry,
    get_heat_map,
    set_heat_map
)

__all__ = [
    "UserMemory",
    "IVectorStore",
    "QdrantVectorStore",
    "FAISSVectorStore",
    "PineconeVectorStore",
    "Distance",
    "MetadataDB",
    "IntelligentCacheManager",
    "CacheConfig",
    "CacheLevel",
    "CacheEntry",
    "CacheStatistics",
    "IntelligentUserCache",
    "UserProfileEntry",
    "PreloadPrediction",
    "UserCacheConfig",
    "UserProfileStatus",
    "IntelligentMembershipCache",
    "MembershipCacheEntry",
    # 渐进式预热系统
    "ProgressiveWarmup",
    "WarmupConfig",
    "WarmupPhase",
    "WarmupResult",
    "WarmupStatistics",
    "get_progressive_warmup",
    "set_progressive_warmup",
    "create_and_start_warmup",
    # 智能预热器（步骤1预热步骤3）
    "SmartPreloader",
    "SmartPreloaderConfig",
    "SmartPreloaderStatistics",
    "PreloadTask",
    "PreloadStatus",
    "get_smart_preloader",
    "set_smart_preloader",
    "create_smart_preloader",
    # 熔断器组件
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "CircuitBreakerRegistry",
    "CircuitState",
    "CircuitOpenException",
    "CircuitBreakerError",
    "user_profile_circuit_breaker",
    "membership_circuit_breaker",
    # 热度图系统
    "HeatMap",
    "HeatMapConfig",
    "HeatEntry",
    "QueryEntry",
    "get_heat_map",
    "set_heat_map"
]


