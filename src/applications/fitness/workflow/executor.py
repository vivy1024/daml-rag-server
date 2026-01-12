# -*- coding: utf-8 -*-
"""
工作流执行器模块

执行工作流图，管理状态转换和监控。
集成现有的 DAMLWorkflowMonitor 进行性能监控。

版本: v1.0.0
日期: 2025-12-28

主要类:
- WorkflowExecutor: 工作流执行器（同步执行）
"""

import logging
import time
import uuid
import asyncio
from typing import Dict, Any, Optional, List

from .state import (
    WorkflowState,
    StateUpdate,
    WorkflowStep,
    create_initial_state,
    serialize_state,
)
from .graph import WorkflowGraph, get_default_graph

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    工作流执行器
    
    执行工作流图，管理状态转换，集成监控。
    """
    
    def __init__(
        self,
        graph: Optional[WorkflowGraph] = None,
        enable_monitoring: bool = True,
        enable_performance: bool = True
    ):
        """
        初始化执行器
        
        Args:
            graph: 工作流图（默认使用全局图）
            enable_monitoring: 是否启用工作流监控
            enable_performance: 是否启用性能监控
        """
        self.graph = graph or get_default_graph()
        self.enable_monitoring = enable_monitoring
        self.enable_performance = enable_performance
        
        # 监控器（延迟初始化）
        self._workflow_monitor = None
        self._performance_monitor = None
        
        # 依赖组件（延迟初始化）
        self._backend_client = None
        self._cache_manager = None
        self._user_cache = None
        self._membership_cache = None
    
    @property
    def workflow_monitor(self):
        """获取工作流监控器"""
        # 注意：旧版 DAMLWorkflowMonitor 已移除，避免运行时导入失败
        return None
    
    @property
    def performance_monitor(self):
        """获取性能监控器（已废弃，返回None）"""
        # 注意：performance_monitor已删除
        return None
    
    def _get_backend_client(self):
        """获取后端客户端"""
        if self._backend_client is None:
            from ..clients.backend_client import BackendClient
            self._backend_client = BackendClient()
        return self._backend_client
    
    def _get_cache_manager(self):
        """获取缓存管理器"""
        if self._cache_manager is None:
            from .singletons import get_cache_manager
            self._cache_manager = get_cache_manager()
        return self._cache_manager
    
    def _get_user_cache(self):
        """获取用户缓存"""
        if self._user_cache is None:
            from .singletons import get_user_cache
            self._user_cache = get_user_cache(backend_client=self._get_backend_client())
        return self._user_cache
    
    def _get_membership_cache(self):
        """获取会员缓存"""
        if self._membership_cache is None:
            from .singletons import get_membership_cache
            self._membership_cache = get_membership_cache(backend_client=self._get_backend_client())
        return self._membership_cache
    
    async def execute(
        self,
        query_text: str,
        user_id: str,
        domain: str = "fitness",
        user_profile: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            query_text: 用户查询文本
            user_id: 用户ID
            domain: 领域（默认 fitness）
            user_profile: 用户档案（可选）
            session_id: 会话ID（可选）
            **kwargs: 其他初始状态字段
            
        Returns:
            执行结果字典
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        logger.info(f"🚀 [{request_id}] 开始执行11步工作流程")
        logger.info(f"📝 查询: {query_text[:50]}...")
        logger.info(f"👤 用户: {user_id}")
        
        # 初始化状态
        state = create_initial_state(
            request_id=request_id,
            user_id=user_id,
            query_text=query_text,
            domain=domain,
            is_streaming=False,
            user_profile=user_profile,
            session_id=session_id,
            **kwargs
        )
        
        # 开始监控会话
        monitor_session_id = None
        perf_context = None
        
        if self.workflow_monitor:
            monitor_session_id = self.workflow_monitor.start_session(
                user_id=user_id,
                query=query_text,
                metadata={"session_id": session_id, "request_id": request_id}
            )
        
        if self.performance_monitor:
            perf_context = self.performance_monitor.start_workflow(
                request_id=request_id,
                user_id=str(user_id)
            )
        
        try:
            # 执行图
            state = await self._execute_graph(
                state=state,
                monitor_session_id=monitor_session_id,
                perf_context=perf_context
            )
            
            # 计算总耗时
            processing_time = time.time() - start_time
            
            # 构建结果
            final_result = {
                "success": True,
                "response": state.get("final_response", ""),
                "request_id": request_id,
                "processing_time": processing_time,
                "metadata": {
                    "user_id": user_id,
                    "session_id": state.get("session_id"),
                    "domain": domain,
                    "complexity_level": state.get("complexity_level"),
                    "selected_model": state.get("selected_model"),
                    "dag_template_id": state.get("dag_template_id"),
                    "mcp_tools_called": state.get("_mcp_tools_called", []),
                    "interaction_logged": state.get("interaction_logged", False),
                    "step_timings": state.get("step_timings", {}),
                    "errors": state.get("errors", []),
                    "warnings": state.get("warnings", [])
                }
            }
            
            # 完成监控
            if self.performance_monitor and perf_context:
                self.performance_monitor.finish_workflow(
                    context=perf_context,
                    success=True,
                    total_duration_ms=processing_time * 1000
                )
            
            logger.info(f"🎉 [{request_id}] 工作流执行成功! 耗时: {processing_time:.2f}秒")
            return final_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ [{request_id}] 工作流执行失败: {e}", exc_info=True)
            
            # 完成监控（失败）
            if self.performance_monitor and perf_context:
                self.performance_monitor.finish_workflow(
                    context=perf_context,
                    success=False,
                    total_duration_ms=processing_time * 1000
                )
            
            return {
                "success": False,
                "response": "",
                "request_id": request_id,
                "processing_time": processing_time,
                "error": str(e),
                "metadata": {
                    "errors": state.get("errors", []) + [str(e)],
                    "step_timings": state.get("step_timings", {})
                }
            }
    
    async def _execute_graph(
        self,
        state: WorkflowState,
        monitor_session_id: Optional[str] = None,
        perf_context: Optional[Any] = None
    ) -> WorkflowState:
        """
        执行工作流图
        
        Args:
            state: 初始状态
            monitor_session_id: 监控会话ID
            perf_context: 性能上下文
            
        Returns:
            最终状态
        """
        request_id = state.get("request_id", "unknown")
        current_node = WorkflowGraph.START
        
        # 获取依赖组件
        backend_client = self._get_backend_client()
        cache_manager = self._get_cache_manager()
        user_cache = self._get_user_cache()
        membership_cache = self._get_membership_cache()
        
        while current_node != WorkflowGraph.END:
            # 获取下一个节点
            next_node = self.graph.get_next_node(current_node, state)
            
            if next_node == WorkflowGraph.END:
                break
            
            # 获取节点配置
            node_config = self.graph.get_node(next_node)
            if not node_config:
                logger.error(f"❌ [{request_id}] 节点不存在: {next_node}")
                break
            
            # 检查是否是并行组
            if node_config.parallel_group:
                # 执行并行组
                state = await self._execute_parallel_group(
                    state=state,
                    group_name=node_config.parallel_group,
                    backend_client=backend_client,
                    cache_manager=cache_manager,
                    user_cache=user_cache,
                    membership_cache=membership_cache,
                    perf_context=perf_context
                )
                
                # 跳过并行组中的其他节点
                parallel_nodes = self.graph.get_parallel_group(node_config.parallel_group)
                for pn in parallel_nodes:
                    if pn != next_node:
                        # 更新当前节点以跳过
                        pass
            else:
                # 执行单个节点
                state = await self._execute_node(
                    state=state,
                    node_name=next_node,
                    node_config=node_config,
                    backend_client=backend_client,
                    cache_manager=cache_manager,
                    user_cache=user_cache,
                    membership_cache=membership_cache,
                    perf_context=perf_context
                )
            
            # 更新当前节点
            current_node = next_node
            
            # 更新状态中的当前步骤
            state["current_step"] = node_config.step_number
            state["current_step_name"] = next_node
        
        return state
    
    async def _execute_node(
        self,
        state: WorkflowState,
        node_name: str,
        node_config,
        backend_client=None,
        cache_manager=None,
        user_cache=None,
        membership_cache=None,
        perf_context=None
    ) -> WorkflowState:
        """
        执行单个节点
        
        Args:
            state: 当前状态
            node_name: 节点名称
            node_config: 节点配置
            backend_client: 后端客户端
            cache_manager: 缓存管理器
            user_cache: 用户缓存
            membership_cache: 会员缓存
            perf_context: 性能上下文
            
        Returns:
            更新后的状态
        """
        request_id = state.get("request_id", "unknown")
        step_start = time.time()
        
        logger.info(f"[{request_id}] 步骤{node_config.step_number}: {node_config.description}")
        
        try:
            # 准备节点参数
            node_kwargs = self._prepare_node_kwargs(
                node_name=node_name,
                state=state,
                backend_client=backend_client,
                cache_manager=cache_manager,
                user_cache=user_cache,
                membership_cache=membership_cache
            )
            
            # 执行节点函数
            update = await node_config.func(state, **node_kwargs)
            
            # 合并更新到状态
            if isinstance(update, StateUpdate):
                state = update.merge_into(state)
            elif isinstance(update, dict):
                state.update(update)
            
            # 记录耗时
            step_duration = (time.time() - step_start) * 1000
            state["step_timings"][node_name] = step_duration
            
            # 记录性能
            if self.performance_monitor and perf_context:
                self.performance_monitor.record_step(
                    context=perf_context,
                    step_number=node_config.step_number,
                    step_name=node_config.description,
                    duration_ms=step_duration,
                    success=True
                )
            
            return state
            
        except Exception as e:
            logger.error(f"❌ [{request_id}] 节点 {node_name} 执行失败: {e}")
            
            # 记录错误
            errors = state.get("errors", [])
            errors.append(f"{node_name}: {str(e)}")
            state["errors"] = errors
            
            # 记录性能（失败）
            step_duration = (time.time() - step_start) * 1000
            if self.performance_monitor and perf_context:
                self.performance_monitor.record_step(
                    context=perf_context,
                    step_number=node_config.step_number,
                    step_name=node_config.description,
                    duration_ms=step_duration,
                    success=False,
                    error=str(e)
                )
            
            return state
    
    async def _execute_parallel_group(
        self,
        state: WorkflowState,
        group_name: str,
        backend_client=None,
        cache_manager=None,
        user_cache=None,
        membership_cache=None,
        perf_context=None
    ) -> WorkflowState:
        """
        执行并行组
        
        Args:
            state: 当前状态
            group_name: 并行组名称
            backend_client: 后端客户端
            cache_manager: 缓存管理器
            user_cache: 用户缓存
            membership_cache: 会员缓存
            perf_context: 性能上下文
            
        Returns:
            更新后的状态
        """
        request_id = state.get("request_id", "unknown")
        parallel_nodes = self.graph.get_parallel_group(group_name)
        
        if not parallel_nodes:
            return state
        
        logger.info(f"[{request_id}] 并行执行组 {group_name}: {parallel_nodes}")
        
        parallel_start = time.time()
        
        # 创建并行任务
        tasks = []
        for node_name in parallel_nodes:
            node_config = self.graph.get_node(node_name)
            if node_config:
                task = self._execute_node(
                    state=state.copy(),  # 使用状态副本
                    node_name=node_name,
                    node_config=node_config,
                    backend_client=backend_client,
                    cache_manager=cache_manager,
                    user_cache=user_cache,
                    membership_cache=membership_cache,
                    perf_context=perf_context
                )
                tasks.append((node_name, task))
        
        # 并行执行
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        # 合并结果
        for i, (node_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"❌ [{request_id}] 并行节点 {node_name} 失败: {result}")
                errors = state.get("errors", [])
                errors.append(f"{node_name}: {str(result)}")
                state["errors"] = errors
            elif isinstance(result, dict):
                # 合并状态更新
                for key, value in result.items():
                    if key not in ["errors", "warnings", "step_timings"]:
                        state[key] = value
                    elif key == "errors":
                        state["errors"] = state.get("errors", []) + value
                    elif key == "warnings":
                        state["warnings"] = state.get("warnings", []) + value
                    elif key == "step_timings":
                        state["step_timings"].update(value)
        
        parallel_duration = (time.time() - parallel_start) * 1000
        logger.info(f"✅ [{request_id}] 并行组 {group_name} 完成，耗时: {parallel_duration:.0f}ms")
        
        return state
    
    def _prepare_node_kwargs(
        self,
        node_name: str,
        state: WorkflowState,
        backend_client=None,
        cache_manager=None,
        user_cache=None,
        membership_cache=None
    ) -> Dict[str, Any]:
        """
        准备节点函数的参数
        
        Args:
            node_name: 节点名称
            state: 当前状态
            backend_client: 后端客户端
            cache_manager: 缓存管理器
            user_cache: 用户缓存
            membership_cache: 会员缓存
            
        Returns:
            节点参数字典
        """
        kwargs = {}
        
        # 根据节点名称准备不同的参数
        if node_name == "preload_user_profile":
            kwargs["backend_client"] = backend_client
            kwargs["cache_manager"] = cache_manager
            kwargs["user_cache"] = user_cache
        
        elif node_name == "check_membership":
            kwargs["backend_client"] = backend_client
            kwargs["cache_manager"] = cache_manager
            kwargs["membership_cache"] = membership_cache
        
        elif node_name == "classify_complexity":
            kwargs["cache_manager"] = cache_manager
        
        elif node_name == "retrieve_few_shot":
            kwargs["backend_client"] = backend_client
            kwargs["cache_manager"] = cache_manager
        
        elif node_name == "execute_dag":
            # 获取MCP编排器
            from .singletons import get_mcp_orchestrator
            kwargs["mcp_tool_manager"] = get_mcp_orchestrator()
        
        elif node_name == "log_interaction":
            kwargs["backend_client"] = backend_client
        
        return kwargs


# ============ 便捷函数 ============

async def execute_workflow(
    query_text: str,
    user_id: str,
    domain: str = "fitness",
    user_profile: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    执行工作流的便捷函数
    
    Args:
        query_text: 用户查询文本
        user_id: 用户ID
        domain: 领域
        user_profile: 用户档案
        session_id: 会话ID
        **kwargs: 其他参数
        
    Returns:
        执行结果
    """
    executor = WorkflowExecutor()
    return await executor.execute(
        query_text=query_text,
        user_id=user_id,
        domain=domain,
        user_profile=user_profile,
        session_id=session_id,
        **kwargs
    )


# ============ 导出 ============

__all__ = [
    "WorkflowExecutor",
    "execute_workflow",
]
