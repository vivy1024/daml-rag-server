# -*- coding: utf-8 -*-
"""
DAML-RAG框架适配器

提供框架层通用适配器的实现和领域适配器抽象接口。

版本：v3.0.0
日期：2026-01-11
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

from .base_adapter import (
    BaseAdapter,
    BaseQueryAdapter,
    BaseWorkflowAdapter
)

from .domain_adapter import (
    # 数据类
    Layer3Rule,
    DAGTemplateDefinition,
    ToolDefinition,
    DomainConfig,
    RuleSeverity,
    RuleCategory,
    # 抽象基类
    DomainAdapter,
    # 注册表
    DomainAdapterRegistry,
    get_domain_registry,
    register_domain_adapter,
)

from ..interfaces.adapter_interfaces import (
    AdapterContext,
    AdapterResult
)

logger = logging.getLogger(__name__)


# ================================================================================
# DomainContext - 领域上下文（兼容fitness_service.py）
# ================================================================================

@dataclass
class DomainContext:
    """
    领域上下文 - 用于传递领域特定配置

    兼容旧版FitnessService使用的上下文格式
    """
    domain_name: str
    domain_config: Dict[str, Any] = None
    business_rules: list = None
    constraints: Dict[str, Any] = None

    def __post_init__(self):
        if self.domain_config is None:
            self.domain_config = {}
        if self.business_rules is None:
            self.business_rules = []
        if self.constraints is None:
            self.constraints = {}


# ================================================================================
# AdapterRegistry - 适配器注册表（旧版，保持兼容）
# ================================================================================

class AdapterRegistry:
    """
    适配器注册表 - 管理所有领域适配器

    提供适配器的注册、获取、初始化等功能
    
    注意：新代码应使用 DomainAdapterRegistry
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._adapters = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, name: str, adapter: BaseAdapter) -> None:
        """注册适配器"""
        self._adapters[name] = adapter
        logger.info(f"注册适配器: {name}")

    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        """获取适配器"""
        return self._adapters.get(name)

    def list_adapters(self) -> list:
        """列出所有已注册的适配器"""
        return list(self._adapters.keys())

    def is_registered(self, name: str) -> bool:
        """检查适配器是否已注册"""
        return name in self._adapters

    async def initialize_all(self) -> bool:
        """初始化所有适配器"""
        success = True
        for name, adapter in self._adapters.items():
            try:
                if hasattr(adapter, 'initialize'):
                    await adapter.initialize()
                    logger.info(f"适配器初始化成功: {name}")
            except Exception as e:
                logger.error(f"适配器初始化失败: {name} - {e}")
                success = False
        self._initialized = success
        return success


# 全局适配器注册表实例
adapter_registry = AdapterRegistry()


__all__ = [
    # 领域适配器（新版）
    'DomainAdapter',
    'Layer3Rule',
    'DAGTemplateDefinition',
    'ToolDefinition',
    'DomainConfig',
    'RuleSeverity',
    'RuleCategory',
    'DomainAdapterRegistry',
    'get_domain_registry',
    'register_domain_adapter',
    # 基础适配器类
    'BaseAdapter',
    'BaseQueryAdapter',
    'BaseWorkflowAdapter',
    # 上下文和结果类
    'AdapterContext',
    'AdapterResult',
    'DomainContext',
    # 注册表（旧版，保持兼容）
    'AdapterRegistry',
    'adapter_registry',
]
