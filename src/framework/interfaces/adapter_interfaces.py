# -*- coding: utf-8 -*-
"""
领域适配器接口定义 (adapter_interfaces.py)

定义所有领域适配器必须实现的通用接口，确保框架层与应用层解耦。

重命名说明：
- 原文件名：base_adapter.py
- 新文件名：adapter_interfaces.py
- 重命名原因：避免与adapters/base_adapter.py混淆

版本：v2.1.0
日期：2026-01-12
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

import logging

logger = logging.getLogger(__name__)


@dataclass
class AdapterContext:
    """适配器上下文"""
    user_id: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None
    domain: str = "general"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AdapterResult:
    """适配器结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IDomainAdapter(ABC):
    """
    领域适配器接口

    所有具体领域的适配器必须实现此接口：
    - Fitness领域：FitnessAdapter
    - Nutrition领域：NutritionAdapter
    - Rehabilitation领域：RehabilitationAdapter
    """

    def __init__(self, domain: str):
        """
        初始化适配器

        Args:
            domain: 领域名称（如 'fitness', 'nutrition', 'rehabilitation'）
        """
        self.domain = domain
        self.is_initialized = False
        logger.info(f"创建领域适配器: {domain}")

    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化适配器

        加载必要的资源、配置数据库连接等

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    async def process_query(
        self,
        query: str,
        context: AdapterContext,
        **kwargs
    ) -> AdapterResult:
        """
        处理查询请求

        Args:
            query: 查询文本
            context: 适配器上下文
            **kwargs: 额外参数

        Returns:
            AdapterResult: 处理结果
        """
        pass

    @abstractmethod
    async def get_supported_operations(self) -> List[str]:
        """
        获取支持的操作列表

        Returns:
            List[str]: 支持的操作名称列表
        """
        pass

    async def validate_context(self, context: AdapterContext) -> bool:
        """
        验证上下文是否有效

        Args:
            context: 适配器上下文

        Returns:
            bool: 上下文是否有效
        """
        # 默认验证逻辑，子类可覆盖
        return True

    async def preprocess_query(self, query: str, context: AdapterContext) -> str:
        """
        预处理查询（可选）

        Args:
            query: 原始查询
            context: 适配器上下文

        Returns:
            str: 预处理后的查询
        """
        # 默认不做处理，子类可覆盖
        return query

    async def postprocess_result(
        self,
        result: AdapterResult,
        context: AdapterContext
    ) -> AdapterResult:
        """
        后处理结果（可选）

        Args:
            result: 原始结果
            context: 适配器上下文

        Returns:
            AdapterResult: 后处理后的结果
        """
        # 默认不做处理，子类可覆盖
        return result

    def is_ready(self) -> bool:
        """
        检查适配器是否就绪

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


class IQueryAdapter(IDomainAdapter):
    """
    查询适配器接口

    专门用于处理查询请求的适配器
    """

    @abstractmethod
    async def query_vector(
        self,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        向量检索

        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            AdapterResult: 检索结果
        """
        pass

    @abstractmethod
    async def query_graph(
        self,
        query_text: str,
        cypher: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        图检索

        Args:
            query_text: 查询文本
            cypher: Cypher查询语句（可选）
            filters: 过滤条件

        Returns:
            AdapterResult: 检索结果
        """
        pass

    @abstractmethod
    async def hybrid_query(
        self,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        混合检索（向量+图）

        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            AdapterResult: 检索结果
        """
        pass


class IWorkflowAdapter(IDomainAdapter):
    """
    工作流适配器接口

    用于编排多个步骤的业务流程
    """

    @abstractmethod
    async def execute_workflow(
        self,
        workflow_name: str,
        context: AdapterContext,
        **kwargs
    ) -> AdapterResult:
        """
        执行工作流

        Args:
            workflow_name: 工作流名称
            context: 适配器上下文
            **kwargs: 工作流参数

        Returns:
            AdapterResult: 工作流执行结果
        """
        pass

    @abstractmethod
    async def get_workflow_steps(self, workflow_name: str) -> List[str]:
        """
        获取工作流步骤

        Args:
            workflow_name: 工作流名称

        Returns:
            List[str]: 步骤名称列表
        """
        pass


# 注册表用于管理所有适配器
class AdapterRegistry:
    """适配器注册表"""

    _adapters: Dict[str, type] = {}
    _instances: Dict[str, IDomainAdapter] = {}

    @classmethod
    def register(cls, domain: str, adapter_class: type):
        """
        注册适配器类

        Args:
            domain: 领域名称
            adapter_class: 适配器类
        """
        cls._adapters[domain] = adapter_class
        logger.info(f"注册领域适配器: {domain} -> {adapter_class.__name__}")

    @classmethod
    def get_adapter_class(cls, domain: str) -> Optional[type]:
        """
        获取适配器类

        Args:
            domain: 领域名称

        Returns:
            Optional[type]: 适配器类或None
        """
        return cls._adapters.get(domain)

    @classmethod
    async def get_adapter(
        cls,
        domain: str,
        **kwargs
    ) -> Optional[IDomainAdapter]:
        """
        获取适配器实例（单例）

        Args:
            domain: 领域名称
            **kwargs: 初始化参数

        Returns:
            Optional[IDomainAdapter]: 适配器实例或None
        """
        if domain not in cls._instances:
            adapter_class = cls.get_adapter_class(domain)
            if adapter_class:
                adapter = adapter_class(domain, **kwargs)
                await adapter.initialize()
                cls._instances[domain] = adapter
                return adapter
            return None
        return cls._instances[domain]

    @classmethod
    def list_domains(cls) -> List[str]:
        """
        列出所有已注册的领域

        Returns:
            List[str]: 领域名称列表
        """
        return list(cls._adapters.keys())
