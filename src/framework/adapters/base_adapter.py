# -*- coding: utf-8 -*-
"""
基础适配器实现

提供框架层通用适配器的默认实现。

版本：v2.1.0
日期：2026-01-12
"""

import logging
from typing import Dict, Any, List, Optional, Union
from abc import ABC

from ..interfaces.adapter_interfaces import (
    IDomainAdapter,
    IQueryAdapter,
    IWorkflowAdapter,
    AdapterContext,
    AdapterResult
)

logger = logging.getLogger(__name__)


class BaseAdapter(IDomainAdapter):
    """
    基础适配器实现

    提供通用的适配器功能，子类可继承并覆盖特定方法
    """

    def __init__(self, domain: str):
        """
        初始化基础适配器

        Args:
            domain: 领域名称
        """
        super().__init__(domain)
        self.config = {}
        self.resources = {}

    async def initialize(self) -> bool:
        """
        初始化适配器

        默认实现只设置is_initialized标志，子类可覆盖

        Returns:
            bool: 初始化是否成功
        """
        self.is_initialized = True
        logger.info(f"基础适配器初始化完成: {self.domain}")
        return True

    async def process_query(
        self,
        query: str,
        context: AdapterContext,
        **kwargs
    ) -> AdapterResult:
        """
        处理查询请求

        默认实现返回错误，子类必须覆盖

        Args:
            query: 查询文本
            context: 适配器上下文
            **kwargs: 额外参数

        Returns:
            AdapterResult: 处理结果
        """
        return AdapterResult(
            success=False,
            error=f"BaseAdapter未实现process_query方法，请使用子类实现"
        )

    async def get_supported_operations(self) -> List[str]:
        """
        获取支持的操作列表

        Returns:
            List[str]: 支持的操作名称列表
        """
        return ["process_query"]

    async def validate_context(self, context: AdapterContext) -> bool:
        """
        验证上下文是否有效

        Args:
            context: 适配器上下文

        Returns:
            bool: 上下文是否有效
        """
        # 基本验证：确保domain匹配
        if context.domain != self.domain:
            logger.warning(
                f"领域不匹配: 期望{self.domain}, 实际{context.domain}"
            )
            return False
        return True

    async def preprocess_query(self, query: str, context: AdapterContext) -> str:
        """
        预处理查询

        默认实现：去除首尾空格，限制长度

        Args:
            query: 原始查询
            context: 适配器上下文

        Returns:
            str: 预处理后的查询
        """
        # 去除首尾空格
        query = query.strip()

        # 限制长度
        if len(query) > 1000:
            query = query[:1000] + "..."
            logger.warning("查询被截断")

        return query

    async def postprocess_result(
        self,
        result: AdapterResult,
        context: AdapterContext
    ) -> AdapterResult:
        """
        后处理结果

        默认实现：添加元数据

        Args:
            result: 原始结果
            context: 适配器上下文

        Returns:
            AdapterResult: 后处理后的结果
        """
        # 添加处理时间和领域信息
        result.metadata["domain"] = self.domain
        result.metadata["adapter"] = self.__class__.__name__

        return result

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict[str, Any]: 健康状态信息
        """
        base_info = await super().health_check()
        base_info.update({
            "adapter_class": self.__class__.__name__,
            "config_loaded": bool(self.config),
            "resources_loaded": bool(self.resources)
        })
        return base_info


class BaseQueryAdapter(BaseAdapter, IQueryAdapter):
    """
    基础查询适配器实现

    提供通用的查询功能，子类可继承并实现具体查询逻辑
    """

    async def query_vector(
        self,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        向量检索

        默认实现返回错误，子类必须覆盖

        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            AdapterResult: 检索结果
        """
        return AdapterResult(
            success=False,
            error=f"BaseQueryAdapter未实现query_vector方法"
        )

    async def query_graph(
        self,
        query_text: str,
        cypher: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        图检索

        默认实现返回错误，子类必须覆盖

        Args:
            query_text: 查询文本
            cypher: Cypher查询语句（可选）
            filters: 过滤条件

        Returns:
            AdapterResult: 检索结果
        """
        return AdapterResult(
            success=False,
            error=f"BaseQueryAdapter未实现query_graph方法"
        )

    async def hybrid_query(
        self,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> AdapterResult:
        """
        混合检索

        默认实现：尝试向量检索，失败后尝试图检索

        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            AdapterResult: 检索结果
        """
        # 首先尝试向量检索
        vector_result = await self.query_vector(query_text, top_k, filters)
        if vector_result.success and vector_result.data:
            return vector_result

        # 向量检索失败，尝试图检索
        logger.info("向量检索无结果，尝试图检索")
        graph_result = await self.query_graph(query_text, filters=filters)
        if graph_result.success and graph_result.data:
            return graph_result

        # 都失败，返回错误
        return AdapterResult(
            success=False,
            error="向量检索和图检索均未找到结果"
        )

    async def get_supported_operations(self) -> List[str]:
        """
        获取支持的操作列表

        Returns:
            List[str]: 支持的操作名称列表
        """
        return ["query_vector", "query_graph", "hybrid_query"]


class BaseWorkflowAdapter(BaseAdapter, IWorkflowAdapter):
    """
    基础工作流适配器实现

    提供通用的工作流功能，子类可继承并实现具体工作流逻辑
    """

    def __init__(self, domain: str):
        """
        初始化工作流适配器

        Args:
            domain: 领域名称
        """
        super().__init__(domain)
        self.workflows = {}

    async def execute_workflow(
        self,
        workflow_name: str,
        context: AdapterContext,
        **kwargs
    ) -> AdapterResult:
        """
        执行工作流

        默认实现返回错误，子类必须覆盖

        Args:
            workflow_name: 工作流名称
            context: 适配器上下文
            **kwargs: 工作流参数

        Returns:
            AdapterResult: 工作流执行结果
        """
        return AdapterResult(
            success=False,
            error=f"BaseWorkflowAdapter未实现execute_workflow方法"
        )

    async def get_workflow_steps(self, workflow_name: str) -> List[str]:
        """
        获取工作流步骤

        Args:
            workflow_name: 工作流名称

        Returns:
            List[str]: 步骤名称列表
        """
        workflow = self.workflows.get(workflow_name)
        if workflow:
            return workflow.get("steps", [])
        return []

    async def get_supported_operations(self) -> List[str]:
        """
        获取支持的操作列表

        Returns:
            List[str]: 支持的操作名称列表
        """
        return ["execute_workflow", "get_workflow_steps"]

    async def register_workflow(
        self,
        workflow_name: str,
        steps: List[str],
        description: str = ""
    ):
        """
        注册工作流

        Args:
            workflow_name: 工作流名称
            steps: 工作流步骤列表
            description: 工作流描述
        """
        self.workflows[workflow_name] = {
            "steps": steps,
            "description": description
        }
        logger.info(f"注册工作流: {workflow_name} -> {steps}")
