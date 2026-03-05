# -*- coding: utf-8 -*-
"""
流式工作流执行器模块

执行工作流图，支持流式输出。
步骤1-9保持同步执行，步骤10改为流式LLM调用。
集成 StreamingMetrics 进行流式监控。
集成 ContextEngineering 进行多轮对话上下文管理。

版本: v1.2.0
日期: 2026-03-05

主要类:
- StreamWorkflowExecutor: 流式工作流执行器（由 3 个 Mixin + WorkflowExecutor 组合）

更新记录:
- v1.1.0: 集成上下文工程模块（Requirements 8.1-8.5）
- v1.2.0: Mixin 拆分（PipelineMixin + LLMStreamMixin + PermissionMixin）
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator

from .graph import WorkflowGraph
from .executor import WorkflowExecutor

# 导入上下文工程模块
from ..context import (
    ContextEngineering,
    ContextConfig,
    ContextResult,
)

# 导入 Mixin
from .stream_executor_pipeline import PipelineMixin
from .stream_executor_llm import LLMStreamMixin
from .stream_executor_permission import PermissionMixin

logger = logging.getLogger(__name__)


class StreamWorkflowExecutor(
    PipelineMixin,
    LLMStreamMixin,
    PermissionMixin,
    WorkflowExecutor
):
    """
    流式工作流执行器

    继承自 WorkflowExecutor，通过 Mixin 组合添加：
    - PipelineMixin: 管线步骤编排（execute_stream + 步骤1-9 + 步骤11）
    - LLMStreamMixin: 流式LLM生成（步骤10）
    - PermissionMixin: 权限检查 + 三轨评分 + 用量计数 + 积分上报

    集成上下文工程模块（Requirements 8.1-8.5）：
    - 对话历史管理（滑动窗口）
    - Token智能压缩
    - 用户档案自动注入
    - 话题切换逻辑
    """

    def __init__(
        self,
        graph: Optional[WorkflowGraph] = None,
        enable_monitoring: bool = True,
        enable_performance: bool = True,
        enable_streaming_metrics: bool = True,
        enable_context_engineering: bool = True,
        context_config: Optional[ContextConfig] = None,
    ):
        """
        初始化流式执行器

        Args:
            graph: 工作流图
            enable_monitoring: 是否启用工作流监控
            enable_performance: 是否启用性能监控
            enable_streaming_metrics: 是否启用流式监控
            enable_context_engineering: 是否启用上下文工程
            context_config: 上下文工程配置
        """
        super().__init__(
            graph=graph,
            enable_monitoring=enable_monitoring,
            enable_performance=enable_performance
        )
        self.enable_streaming_metrics = enable_streaming_metrics
        self._streaming_monitor = None

        # 上下文工程（Requirements 8.1-8.5）
        self.enable_context_engineering = enable_context_engineering
        self._context_engine: Optional[ContextEngineering] = None
        self._context_config = context_config

    @property
    def streaming_monitor(self):
        """获取流式监控器"""
        if self._streaming_monitor is None and self.enable_streaming_metrics:
            from ....framework.monitoring.streaming_metrics import streaming_monitor
            self._streaming_monitor = streaming_monitor
        return self._streaming_monitor

    @property
    def context_engine(self) -> Optional[ContextEngineering]:
        """
        获取上下文工程实例（懒加载）

        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
        """
        if self._context_engine is None and self.enable_context_engineering:
            try:
                backend_client = self._get_backend_client()
                llm_client = self._get_llm_client()

                self._context_engine = ContextEngineering(
                    config=self._context_config,
                    backend_client=backend_client,
                    llm_client=llm_client,
                )
                logger.info("上下文工程模块初始化成功")
            except (ImportError, AttributeError, TypeError, ConnectionError) as e:
                logger.warning(f"上下文工程模块初始化失败: {e}")
                self._context_engine = None
        return self._context_engine

    def _get_llm_client(self):
        """获取LLM客户端（懒加载）"""
        try:
            from ....framework.clients.llm_client import get_llm_client
            return get_llm_client()
        except (ImportError, AttributeError) as e:
            logger.warning(f"获取LLM客户端失败: {e}")
            return None


# ============ 便捷函数 ============

async def execute_workflow_stream(
    query_text: str,
    user_id: str,
    domain: str = "fitness",
    user_profile: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    strategy: str = "dag",
    **kwargs
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    流式执行工作流的便捷函数

    Args:
        query_text: 用户查询文本
        user_id: 用户ID
        domain: 领域
        user_profile: 用户档案
        session_id: 会话ID
        topic_id: 话题ID（用于多轮对话）
        strategy: 执行策略（dag或agent，默认dag）
        **kwargs: 其他参数

    Yields:
        SSE事件
    """
    executor = StreamWorkflowExecutor()
    async for event in executor.execute_stream(
        query_text=query_text,
        user_id=user_id,
        domain=domain,
        user_profile=user_profile,
        session_id=session_id,
        topic_id=topic_id,
        strategy=strategy,
        **kwargs
    ):
        yield event


# ============ 导出 ============

__all__ = [
    "StreamWorkflowExecutor",
    "execute_workflow_stream",
]
