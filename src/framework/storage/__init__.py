# -*- coding: utf-8 -*-
"""
Storage Layer - 存储层

模块：
- vector_store_abstract.py: 向量存储抽象层
- metadata_database.py: 元数据数据库
- unified_cache.py: 统一缓存系统
- user_profile_cache.py: 用户档案缓存
- membership_cache.py: 会员缓存
- warmup.py: 预加载管理器
- circuit_breaker.py: 熔断器
- connection_pool_manager.py: 连接池管理器
"""

from .vector_store_abstract import (
    IVectorStore,
    QdrantVectorStore,
    FAISSVectorStore,
    PineconeVectorStore,
    Distance
)
from .metadata_database import MetadataDB

# 缓存系统
from .unified_cache import (
    UnifiedCache,
    CacheConfig as UnifiedCacheConfig,
    CacheStatistics as UnifiedCacheStatistics
)
from .user_profile_cache import (
    UserProfileCache
)
from .membership_cache import (
    MembershipCache
)
from .warmup import (
    WarmupManager,
    WarmupConfig,
    get_warmup_manager,
    set_warmup_manager
)

# 熔断器
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

__all__ = [
    "IVectorStore",
    "QdrantVectorStore",
    "FAISSVectorStore",
    "PineconeVectorStore",
    "Distance",
    "MetadataDB",
    # 缓存系统
    "UnifiedCache",
    "UnifiedCacheConfig",
    "UnifiedCacheStatistics",
    "UserProfileCache",
    "MembershipCache",
    "WarmupManager",
    "WarmupConfig",
    "get_warmup_manager",
    "set_warmup_manager",
    # 熔断器组件
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "CircuitBreakerRegistry",
    "CircuitState",
    "CircuitOpenException",
    "CircuitBreakerError",
    "user_profile_circuit_breaker",
    "membership_circuit_breaker"
]



