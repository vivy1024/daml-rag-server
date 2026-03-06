# -*- coding: utf-8 -*-
"""
轻量级 DI 容器

集中管理所有全局单例组件的生命周期，替代 singletons.py 中散落的全局变量。

设计原则：
- 零外部依赖（不用 dependency-injector）
- Lazy init：首次访问时才创建实例
- 可测试：override() 注入 mock，reset() 清理状态
- 向后兼容：singletons.py 的 get_xxx() API 保持不变

版本: v1.0.0
日期: 2026-02-23
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AppContainer:
    """
    应用级 DI 容器

    所有组件通过 property 懒加载，首次访问时初始化。
    测试时可通过 override() 注入 mock 对象。

    Usage:
        container = get_container()
        cache = container.user_cache          # 懒加载
        container.override("user_cache", mock) # 测试注入
        container.reset()                      # 清理全部
    """

    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._overrides: Dict[str, Any] = {}
        self._factories: Dict[str, Any] = {}
        self._register_factories()

    def _register_factories(self):
        """注册所有组件的工厂函数"""
        self._factories = {
            "user_cache": self._create_user_cache,
            "membership_cache": self._create_membership_cache,
            "cache_manager": self._create_cache_manager,
            "connection_pool_manager": self._create_connection_pool_manager,
            "llm_fallback_manager": self._create_llm_fallback_manager,
            "concurrency_limiter": self._create_concurrency_limiter,
            "performance_monitor": self._create_performance_monitor,
            "cypher_executor": self._create_cypher_executor,
            "hybrid_search_engine": self._create_hybrid_search_engine,
            "mcp_tool_registry": self._create_mcp_tool_registry,
            "mcp_orchestrator": self._create_mcp_orchestrator,
        }

    # ============ 公共 API ============

    def get(self, name: str, **kwargs) -> Any:
        """
        获取组件实例（懒加载）

        Args:
            name: 组件名称
            **kwargs: 传递给工厂函数的参数

        Returns:
            组件实例
        """
        # 优先返回 override
        if name in self._overrides:
            return self._overrides[name]

        # 已缓存的实例
        if name in self._instances:
            instance = self._instances[name]
            # 支持后续注入依赖（如 backend_client）
            self._post_inject(name, instance, **kwargs)
            return instance

        # 懒加载创建
        if name in self._factories:
            try:
                instance = self._factories[name](**kwargs)
                if instance is not None:
                    self._instances[name] = instance
                return instance
            except Exception as e:
                logger.error(f"❌ 组件 {name} 创建失败: {e}")
                return None

        raise KeyError(f"未注册的组件: {name}")

    def override(self, name: str, instance: Any):
        """测试用：注入 mock 对象"""
        self._overrides[name] = instance

    def reset(self, name: Optional[str] = None):
        """
        重置组件实例

        Args:
            name: 指定组件名，None 则重置全部
        """
        if name:
            self._instances.pop(name, None)
            self._overrides.pop(name, None)
        else:
            self._instances.clear()
            self._overrides.clear()
        logger.info(f"🔄 容器已重置: {name or '全部'}")

    @property
    def initialized_components(self) -> list:
        """返回已初始化的组件名列表"""
        return list(self._instances.keys())

    # ============ Property 快捷访问 ============

    @property
    def user_cache(self):
        return self.get("user_cache")

    @property
    def membership_cache(self):
        return self.get("membership_cache")

    @property
    def cache_manager(self):
        return self.get("cache_manager")

    @property
    def connection_pool_manager(self):
        return self.get("connection_pool_manager")

    @property
    def llm_fallback_manager(self):
        return self.get("llm_fallback_manager")

    @property
    def concurrency_limiter(self):
        return self.get("concurrency_limiter")

    @property
    def performance_monitor(self):
        return self.get("performance_monitor")

    @property
    def cypher_executor(self):
        return self.get("cypher_executor")

    @property
    def hybrid_search_engine(self):
        return self.get("hybrid_search_engine")

    @property
    def mcp_tool_registry(self):
        return self.get("mcp_tool_registry")

    @property
    def mcp_orchestrator(self):
        return self.get("mcp_orchestrator")

    # ============ 工厂函数 ============

    def _post_inject(self, name: str, instance: Any, **kwargs):
        """后续注入依赖（如首次创建时 backend_client=None，后续补充）"""
        backend_client = kwargs.get("backend_client")
        if backend_client is None:
            return

        if name == "user_cache" and hasattr(instance, "db_client"):
            if getattr(instance, "db_client") is None:
                instance.db_client = backend_client
        elif name == "membership_cache" and hasattr(instance, "backend_client"):
            if getattr(instance, "backend_client") is None:
                instance.backend_client = backend_client

    def _create_user_cache(self, backend_client=None, redis_client=None):
        from .storage.user_profile_cache import UserProfileCache
        from .storage.unified_cache import UnifiedCache, CacheConfig

        cache_config = CacheConfig()
        unified_cache = UnifiedCache(redis_client=redis_client, config=cache_config)
        instance = UserProfileCache(
            unified_cache=unified_cache,
            db_client=backend_client,
        )
        logger.info("✅ UserProfileCache 初始化完成 (via Container)")
        return instance

    def _create_membership_cache(self, backend_client=None, redis_client=None):
        from .storage.membership_cache import MembershipCache
        from .storage.unified_cache import UnifiedCache, CacheConfig

        cache_config = CacheConfig()
        unified_cache = UnifiedCache(redis_client=redis_client, config=cache_config)
        instance = MembershipCache(
            unified_cache=unified_cache,
            backend_client=backend_client,
        )
        logger.info("✅ MembershipCache 初始化完成 (via Container)")
        return instance

    def _create_cache_manager(self, **kwargs):
        from .mcp.cache_manager import CacheManager

        try:
            from ..applications.fitness.clients.backend_client import BackendClient
            backend_client = BackendClient()
        except Exception:
            backend_client = None

        user_cache = self.get("user_cache", backend_client=backend_client)
        membership_cache = self.get("membership_cache", backend_client=backend_client)

        instance = CacheManager(
            user_cache=user_cache,
            membership_cache=membership_cache,
            user_profile_ttl=300,
            membership_ttl=600,
        )
        logger.info("✅ CacheManager 初始化完成 (via Container)")
        return instance

    def _create_connection_pool_manager(self, **kwargs):
        from .storage.connection_pool_manager import ConnectionPoolManager, PoolConfig
        from .config import get_config

        app_config = get_config()

        mysql_config = PoolConfig(
            min_size=10, max_size=50, max_idle_time=60,
            max_lifetime=3600, acquire_timeout=2, health_check_interval=30,
        )
        neo4j_config = PoolConfig(
            min_size=5, max_size=20, max_idle_time=120,
            max_lifetime=3600, acquire_timeout=2, health_check_interval=30,
        )

        instance = ConnectionPoolManager(
            mysql_config=mysql_config,
            neo4j_config=neo4j_config,
            mysql_db_config=app_config.database.mysql.to_dict(),
            neo4j_db_config=app_config.database.neo4j.to_dict(),
        )
        logger.info("✅ ConnectionPoolManager 初始化完成 (via Container)")
        return instance

    def _create_llm_fallback_manager(self, **kwargs):
        from .clients.llm_fallback_manager import LLMFallbackManager
        from .config.app_config import get_config

        config = get_config()
        instance = LLMFallbackManager(
            primary_backend="anthropic",
            fallback_backends=["deepseek", "template"],
            max_retries=3,
            timeout=int(config.llm.base.timeout),
            enable_health_check=True,
        )
        logger.info("✅ LLMFallbackManager 初始化完成 (via Container)")
        return instance

    def _create_concurrency_limiter(self, **kwargs):
        from .monitoring.concurrency_limiter import ConcurrencyLimiter

        instance = ConcurrencyLimiter()
        logger.info("✅ ConcurrencyLimiter 初始化完成 (via Container)")
        return instance

    def _create_performance_monitor(self, **kwargs):
        from .monitoring.prometheus_integration import initialize_prometheus_metrics

        initialize_prometheus_metrics()
        logger.info("✅ Prometheus 指标初始化完成 (via Container)")
        return True  # 哨兵值，与原实现一致

    def _create_cypher_executor(self, **kwargs):
        try:
            from .retrieval.cypher_templates import CypherQueryExecutor
            instance = CypherQueryExecutor()
            logger.info("✅ CypherQueryExecutor 初始化完成 (via Container)")
            return instance
        except Exception as e:
            logger.warning(f"⚠️ CypherQueryExecutor 初始化失败，降级到混合检索: {e}")
            return None

    def _create_hybrid_search_engine(self, **kwargs):
        try:
            from .retrieval.hybrid_search import HybridSearchEngine
            instance = HybridSearchEngine()
            logger.info("✅ HybridSearchEngine 初始化完成 (via Container)")
            return instance
        except Exception as e:
            logger.warning(f"⚠️ HybridSearchEngine 初始化失败，降级到 GraphRAG: {e}")
            return None

    def _create_mcp_tool_registry(self, neo4j_client=None, qdrant_client=None,
                                   three_layer_engine=None, backend_client=None, **kwargs):
        try:
            from ..applications.fitness.mcp_tools import MCPToolRegistry, initialize_all_tools

            if neo4j_client is None:
                try:
                    from .clients.neo4j_client import Neo4jClient
                    import asyncio
                    neo4j_client = Neo4jClient()
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(neo4j_client.connect())
                    else:
                        loop.run_until_complete(neo4j_client.connect())
                except Exception as e:
                    logger.warning(f"⚠️ Neo4jClient 创建失败: {e}")

            if qdrant_client is None:
                try:
                    from .clients.qdrant_client import create_qdrant_client
                    from .config.app_config import get_config
                    config = get_config()
                    qdrant_client = create_qdrant_client(
                        host=config.database.qdrant.host,
                        port=config.database.qdrant.port
                    )
                except Exception as e:
                    logger.warning(f"⚠️ QdrantClient 创建失败: {e}")

            if three_layer_engine is None:
                try:
                    from .retrieval.true_three_layer_engine import TrueThreeLayerEngine
                    # 获取 domain_adapter（Task 7）
                    domain_adapter = None
                    try:
                        from src.applications.fitness.fitness_adapter import get_fitness_adapter
                        domain_adapter = get_fitness_adapter()
                    except Exception:
                        pass
                    # 获取 connection_pool_manager（Task 21）
                    connection_pool_manager = None
                    try:
                        connection_pool_manager = self.connection_pool_manager
                    except Exception:
                        pass
                    three_layer_engine = TrueThreeLayerEngine(
                        enable_neo4j_direct=True, enable_parallel_execution=False,
                        domain_adapter=domain_adapter,
                        connection_pool_manager=connection_pool_manager,
                    )
                except Exception as e:
                    logger.warning(f"⚠️ TrueThreeLayerEngine 创建失败: {e}")

            registry = MCPToolRegistry()
            initialize_all_tools(
                registry=registry,
                neo4j_client=neo4j_client,
                qdrant_client=qdrant_client,
                three_layer_engine=three_layer_engine,
                backend_client=backend_client,
                vector_store=None,
            )
            logger.info(f"✅ MCPToolRegistry 初始化完成，{registry.get_tool_count()} 个工具 (via Container)")
            return registry
        except Exception as e:
            logger.error(f"❌ MCPToolRegistry 初始化失败: {e}")
            return None

    def _create_mcp_orchestrator(self, neo4j_client=None, qdrant_client=None,
                                  three_layer_engine=None, backend_client=None, **kwargs):
        try:
            from .orchestration.mcp_orchestrator import MCPOrchestrator
            from .storage.metadata_database import MetadataDB
            from .config.app_config import get_config

            config = get_config()
            metadata_db = MetadataDB(db_path=config.framework.mcp_metadata_db_path)

            tool_registry = self.get(
                "mcp_tool_registry",
                neo4j_client=neo4j_client,
                qdrant_client=qdrant_client,
                three_layer_engine=three_layer_engine,
                backend_client=backend_client,
            )

            instance = MCPOrchestrator(
                metadata_db=metadata_db,
                mcp_client_pool=None,
                cache_ttl=300,
                max_parallel=5,
                tool_registry=tool_registry,
            )
            logger.info("✅ MCPOrchestrator 初始化完成 (via Container)")
            return instance
        except Exception as e:
            logger.error(f"❌ MCPOrchestrator 初始化失败: {e}")
            return None


# ============ 全局容器实例 ============

_container: Optional[AppContainer] = None


def get_container() -> AppContainer:
    """获取全局 DI 容器实例"""
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


def reset_container():
    """重置全局容器（测试用）"""
    global _container
    if _container is not None:
        _container.reset()
    _container = None
    logger.info("🔄 全局 DI 容器已重置")
