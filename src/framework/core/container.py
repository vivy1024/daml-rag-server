# -*- coding: utf-8 -*-
"""
DependencyContainer - 轻量级依赖注入容器

提供核心服务的集中注册和获取，避免模块间硬编码依赖。
采用延迟初始化（lazy init）模式，首次获取时才创建实例。

注册的核心依赖：
- llm_client: LLM客户端
- neo4j_client: Neo4j图数据库客户端
- qdrant_client: Qdrant向量数据库客户端
- three_layer_engine: 三层检索引擎
- cache: 缓存管理器
- fallback_manager: LLM降级管理器

Task 46 - Phase 7 Batch 4 架构重构
"""

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    轻量级依赖注入容器

    支持两种注册方式：
    1. register(name, instance) — 直接注册实例
    2. register_factory(name, factory) — 注册工厂函数（延迟初始化）

    使用 get(name) 获取依赖，工厂函数只在首次 get 时调用。
    """

    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}

    def register(self, name: str, instance: Any) -> None:
        """注册一个已创建的实例"""
        self._instances[name] = instance
        logger.debug(f"注册依赖: {name} (instance)")

    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """注册一个工厂函数（延迟初始化）"""
        self._factories[name] = factory
        logger.debug(f"注册依赖: {name} (factory)")

    def get(self, name: str) -> Any:
        """
        获取依赖实例。

        优先返回已创建的实例，否则调用工厂函数创建。
        """
        if name in self._instances:
            return self._instances[name]

        if name in self._factories:
            try:
                instance = self._factories[name]()
                self._instances[name] = instance
                logger.info(f"延迟初始化依赖: {name}")
                return instance
            except Exception as e:
                logger.error(f"依赖初始化失败: {name}, error={e}")
                raise

        raise KeyError(f"未注册的依赖: {name}")

    def has(self, name: str) -> bool:
        """检查依赖是否已注册"""
        return name in self._instances or name in self._factories

    def get_or_none(self, name: str) -> Optional[Any]:
        """获取依赖，不存在时返回None"""
        try:
            return self.get(name)
        except KeyError:
            return None

    def reset(self) -> None:
        """清空所有注册（用于测试）"""
        self._instances.clear()
        self._factories.clear()

    @property
    def registered_names(self) -> list:
        """返回所有已注册的依赖名称"""
        names = set(self._instances.keys()) | set(self._factories.keys())
        return sorted(names)


# ─── 全局容器单例 ─────────────────────────────────────────

_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """获取全局依赖容器"""
    return _container


def reset_container() -> None:
    """重置全局容器（仅用于测试）"""
    global _container
    _container = DependencyContainer()
