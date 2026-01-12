# -*- coding: utf-8 -*-
"""
通用DAG编排器 - 框架层核心组件

提供领域无关的DAG编排逻辑，支持：
1. 拓扑排序（Kahn算法）
2. 并行执行优化
3. 依赖解析
4. 错误处理和重试
5. 缓存管理

特点：
- 领域无关：不包含任何业务逻辑
- 可配置：通过ToolRegistry注入工具
- 可扩展：支持自定义执行策略

版本: v1.0.0
日期: 2025-12-14
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from ..tools.registry import ToolRegistry, ToolConfig, TaskPriority

# 向后兼容别名
ToolMetadata = ToolConfig

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务执行状态"""
    PENDING = "pending"           # 等待执行
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 执行失败
    SKIPPED = "skipped"          # 跳过（依赖失败）
    CANCELLED = "cancelled"      # 已取消


@dataclass
class DAGTask:
    """DAG任务定义"""
    tool_name: str
    tool_metadata: ToolMetadata
    params: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    execution_order: Optional[int] = None
    level: Optional[int] = None  # DAG层级


@dataclass
class ExecutionLevel:
    """执行层级"""
    level: int
    tasks: List[DAGTask]
    parallel_groups: List[List[DAGTask]] = field(default_factory=list)
    estimated_duration: float = 0.0
    can_parallel: bool = True


@dataclass
class DAGTemplate:
    """DAG模板定义"""
    template_id: str
    name: str
    description: str
    required_tools: List[str]
    optional_tools: List[str] = field(default_factory=list)
    tool_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    parallel_groups: List[List[str]] = field(default_factory=list)
    complexity_level: int = 1  # 1-3
    estimated_duration_seconds: float = 0.0


@dataclass
class DAGExecutionResult:
    """DAG执行结果"""
    execution_id: str
    template_id: str
    success: bool
    total_time: float
    levels_executed: int
    tasks_completed: int
    tasks_failed: int
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class GenericDAGOrchestrator:
    """
    通用DAG编排器（框架层）
    
    特点：
    - 领域无关：不包含任何业务逻辑
    - 可配置：通过ToolRegistry注入工具
    - 可扩展：支持自定义执行策略
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        tool_executor: Optional[Callable] = None,
        cache_manager: Optional[Any] = None,
        resource_pools: Optional[Dict[str, asyncio.Semaphore]] = None
    ):
        """
        初始化通用DAG编排器
        
        Args:
            tool_registry: 工具注册表（由应用层注入）
            tool_executor: 工具执行器（可选，用于实际调用工具）
            cache_manager: 缓存管理器（可选）
            resource_pools: 资源池（可选，用于并发控制）
        """
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.cache_manager = cache_manager
        self.resource_pools = resource_pools or {}
        
        self.execution_history = []
        self.performance_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "cache_hit_rate": 0.0
        }
        
        logger.info(f"✅ 通用DAG编排器初始化完成，工具注册表包含 {len(tool_registry)} 个工具")
    
    async def execute_template(
        self,
        template: DAGTemplate,
        context: Dict[str, Any],
        cached_results: Optional[Dict[str, Any]] = None
    ) -> DAGExecutionResult:
        """
        执行DAG模板（通用逻辑）
        
        Args:
            template: DAG模板
            context: 执行上下文
            cached_results: 缓存结果（可选）
        
        Returns:
            DAGExecutionResult: 执行结果
        """
        execution_id = self._generate_execution_id()
        start_time = time.time()
        
        logger.info(f"🚀 开始DAG执行: {execution_id}")
        logger.info(f"📋 模板: {template.name} (ID: {template.template_id})")
        
        self.performance_stats["total_executions"] += 1
        
        try:
            # 步骤1: 从模板构建任务图
            tasks = self._build_tasks_from_template(template, context)
            logger.info(f"📦 构建了 {len(tasks)} 个任务")
            
            # 步骤2: 拓扑排序
            execution_levels = self._topological_sort(tasks, template.tool_dependencies)
            logger.info(f"📊 拓扑排序完成，共 {len(execution_levels)} 个层级")
            
            # 步骤3: 并行优化
            optimized_levels = self._optimize_parallel_execution(execution_levels, cached_results)
            logger.info(f"⚡ 并行优化完成")
            
            # 步骤4: 执行DAG
            result = await self._execute_levels(
                execution_id,
                optimized_levels,
                context,
                cached_results
            )
            
            # 更新性能统计
            self.performance_stats["successful_executions"] += 1
            execution_time = time.time() - start_time
            self._update_average_execution_time(execution_time)
            
            # 记录执行历史
            self.execution_history.append({
                "execution_id": execution_id,
                "timestamp": start_time,
                "template_id": template.template_id,
                "template_name": template.name,
                "execution_time": execution_time,
                "success": result.success
            })
            
            logger.info(f"✅ DAG执行成功: {execution_id}, 耗时: {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.performance_stats["failed_executions"] += 1
            logger.error(f"❌ DAG执行失败: {execution_id}, 错误: {e}", exc_info=True)
            
            return DAGExecutionResult(
                execution_id=execution_id,
                template_id=template.template_id,
                success=False,
                total_time=time.time() - start_time,
                levels_executed=0,
                tasks_completed=0,
                tasks_failed=1,
                errors={"execution": str(e)}
            )
    
    def _build_tasks_from_template(
        self,
        template: DAGTemplate,
        context: Dict[str, Any]
    ) -> List[DAGTask]:
        """
        从模板构建任务列表（使用注入的ToolRegistry）
        
        Args:
            template: DAG模板
            context: 执行上下文
        
        Returns:
            List[DAGTask]: 任务列表
        """
        tasks = []
        
        # 处理必需工具
        for tool_name in template.required_tools:
            # 转换工具名格式（kebab-case -> snake_case）
            registry_tool_name = tool_name.replace('-', '_')
            
            # 从注册表获取工具元数据
            metadata = self.tool_registry.get_metadata(registry_tool_name)
            if not metadata:
                logger.warning(f"⚠️ 工具未注册: {tool_name}，跳过")
                continue
            
            # 构建任务参数
            params = self._build_task_params(registry_tool_name, context)
            
            # 创建任务
            task = DAGTask(
                tool_name=registry_tool_name,
                tool_metadata=metadata,
                params=params,
                dependencies=[dep.replace('-', '_') for dep in template.tool_dependencies.get(tool_name, [])],
                priority=metadata.priority
            )
            tasks.append(task)
        
        # 处理可选工具
        for tool_name in template.optional_tools:
            registry_tool_name = tool_name.replace('-', '_')
            
            metadata = self.tool_registry.get_metadata(registry_tool_name)
            if not metadata:
                logger.warning(f"⚠️ 可选工具未注册: {tool_name}，跳过")
                continue
            
            params = self._build_task_params(registry_tool_name, context)
            
            task = DAGTask(
                tool_name=registry_tool_name,
                tool_metadata=metadata,
                params=params,
                dependencies=[dep.replace('-', '_') for dep in template.tool_dependencies.get(tool_name, [])],
                priority=TaskPriority.LOW  # 可选工具优先级较低
            )
            tasks.append(task)
        
        # 分配执行顺序
        for i, task in enumerate(tasks):
            task.execution_order = i
        
        return tasks
    
    def _build_task_params(
        self,
        tool_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建任务参数（通用逻辑）
        
        Args:
            tool_name: 工具名称
            context: 执行上下文
        
        Returns:
            Dict: 任务参数
        """
        # 基础参数
        params = {
            "tool_name": tool_name,
            "context": context
        }
        
        # 从上下文中提取常用参数
        if "user_profile" in context:
            params["user_profile"] = context["user_profile"]
        
        if "user_id" in context:
            params["user_id"] = context["user_id"]
        
        if "session_context" in context:
            params["session_context"] = context["session_context"]
        
        return params
    
    def _topological_sort(
        self,
        tasks: List[DAGTask],
        dependencies: Dict[str, List[str]]
    ) -> List[ExecutionLevel]:
        """
        拓扑排序 - Kahn算法
        
        Args:
            tasks: 任务列表
            dependencies: 依赖关系
        
        Returns:
            List[ExecutionLevel]: 执行层级列表
        """
        # 计算入度
        in_degree = {task.tool_name: 0 for task in tasks}
        task_map = {task.tool_name: task for task in tasks}
        
        # 转换依赖关系中的工具名格式
        normalized_dependencies = {}
        for tool_name, deps in dependencies.items():
            normalized_tool_name = tool_name.replace('-', '_')
            normalized_deps = [dep.replace('-', '_') for dep in deps]
            normalized_dependencies[normalized_tool_name] = normalized_deps
        
        # 计算入度
        for task in tasks:
            for dep in normalized_dependencies.get(task.tool_name, []):
                if dep in in_degree:
                    in_degree[task.tool_name] += 1
        
        # 初始化层级
        levels = []
        remaining_tasks = set(task_map.keys())
        
        level_num = 0
        while remaining_tasks:
            # 找到当前入度为0的任务
            current_level_tasks = []
            for task_name in list(remaining_tasks):
                if in_degree[task_name] == 0:
                    current_level_tasks.append(task_map[task_name])
            
            if not current_level_tasks:
                # 存在循环依赖，选择一个任务继续
                task_name = list(remaining_tasks)[0]
                current_level_tasks = [task_map[task_name]]
                logger.warning(f"⚠️ 检测到循环依赖，选择任务继续: {task_name}")
            
            # 按优先级排序
            current_level_tasks.sort(key=lambda t: t.priority.value)
            
            # 创建执行层级
            level = ExecutionLevel(
                level=level_num,
                tasks=current_level_tasks,
                estimated_duration=max(task.tool_metadata.execution_time for task in current_level_tasks),
                can_parallel=all(task.tool_metadata.parallel_safe for task in current_level_tasks)
            )
            
            levels.append(level)
            
            # 更新入度
            for task in current_level_tasks:
                remaining_tasks.remove(task.tool_name)
                task.level = level_num
                
                # 减少依赖任务的入度
                for other_task_name in remaining_tasks:
                    if task.tool_name in normalized_dependencies.get(other_task_name, []):
                        in_degree[other_task_name] -= 1
            
            level_num += 1
        
        return levels
    
    def _optimize_parallel_execution(
        self,
        levels: List[ExecutionLevel],
        cached_results: Optional[Dict[str, Any]] = None
    ) -> List[ExecutionLevel]:
        """
        并行执行优化
        
        Args:
            levels: 执行层级列表
            cached_results: 缓存结果
        
        Returns:
            List[ExecutionLevel]: 优化后的执行层级列表
        """
        optimized_levels = []
        
        for level in levels:
            if not level.can_parallel:
                optimized_levels.append(level)
                continue
            
            # 分析并行安全组
            parallel_groups = self._group_parallel_safe_tasks(level.tasks, cached_results)
            level.parallel_groups = parallel_groups
            optimized_levels.append(level)
        
        return optimized_levels
    
    def _group_parallel_safe_tasks(
        self,
        tasks: List[DAGTask],
        cached_results: Optional[Dict[str, Any]] = None
    ) -> List[List[DAGTask]]:
        """
        分组并行安全的任务
        
        Args:
            tasks: 任务列表
            cached_results: 缓存结果
        
        Returns:
            List[List[DAGTask]]: 并行组列表
        """
        groups = []
        used_tasks = set()
        
        # 优先处理缓存的任务
        if cached_results:
            cached_tasks = [task for task in tasks if task.tool_name in cached_results]
            if cached_tasks:
                groups.append(cached_tasks)
                used_tasks.update(task.tool_name for task in cached_tasks)
        
        # 按MCP服务器分组（使用server_name属性，兼容ToolConfig）
        mcp_groups = defaultdict(list)
        for task in tasks:
            if task.tool_name not in used_tasks:
                # 兼容处理：优先使用server_name，回退到mcp_server
                server_name = getattr(task.tool_metadata, 'server_name', None) or getattr(task.tool_metadata, 'mcp_server', 'default')
                mcp_groups[server_name].append(task)
        
        # 为每个MCP服务器创建组
        for server_name, server_tasks in mcp_groups.items():
            if len(server_tasks) == 1:
                # 单个任务直接成组
                groups.append(server_tasks)
            else:
                # 多个任务按资源限制分组
                if server_name in self.resource_pools:
                    semaphore = self.resource_pools[server_name]
                    max_concurrent = semaphore._value
                    for i in range(0, len(server_tasks), max_concurrent):
                        group = server_tasks[i:i + max_concurrent]
                        groups.append(group)
                else:
                    # 没有资源限制，可以并行
                    groups.append(server_tasks)
        
        return groups
    
    async def _execute_levels(
        self,
        execution_id: str,
        levels: List[ExecutionLevel],
        context: Dict[str, Any],
        cached_results: Optional[Dict[str, Any]] = None
    ) -> DAGExecutionResult:
        """
        执行DAG层级
        
        Args:
            execution_id: 执行ID
            levels: 执行层级列表
            context: 执行上下文
            cached_results: 缓存结果
        
        Returns:
            DAGExecutionResult: 执行结果
        """
        start_time = time.time()
        all_results = (cached_results or {}).copy()
        all_errors = {}
        tasks_completed = 0
        tasks_failed = 0
        
        logger.info(f"📊 执行DAG: {len(levels)}个层级")
        
        for level_index, level in enumerate(levels):
            logger.info(f"🔄 执行层级 {level_index + 1}/{len(levels)}: {len(level.tasks)}个任务")
            
            # 执行当前层级
            if level.parallel_groups:
                # 并行执行组
                for group_index, group in enumerate(level.parallel_groups):
                    logger.info(f"  📦 执行并行组 {group_index + 1}/{len(level.parallel_groups)}: {len(group)}个任务")
                    
                    # 并行执行组内任务
                    group_results = await asyncio.gather(
                        *[self._execute_single_task(task, execution_id, all_results) for task in group],
                        return_exceptions=True
                    )
                    
                    # 收集结果
                    for task, result in zip(group, group_results):
                        if isinstance(result, Exception):
                            all_errors[task.tool_name] = str(result)
                            tasks_failed += 1
                            logger.error(f"❌ 任务失败: {task.tool_name}, 错误: {result}")
                        else:
                            all_results[task.tool_name] = result
                            tasks_completed += 1
                            logger.info(f"✅ 任务完成: {task.tool_name}")
            
            else:
                # 串行执行
                for task in level.tasks:
                    try:
                        result = await self._execute_single_task(task, execution_id, all_results)
                        all_results[task.tool_name] = result
                        tasks_completed += 1
                        logger.info(f"✅ 任务完成: {task.tool_name}")
                    except Exception as e:
                        all_errors[task.tool_name] = str(e)
                        tasks_failed += 1
                        logger.error(f"❌ 任务失败: {task.tool_name}, 错误: {e}")
        
        total_time = time.time() - start_time
        
        return DAGExecutionResult(
            execution_id=execution_id,
            template_id=context.get("template_id", "unknown"),
            success=tasks_failed == 0,
            total_time=total_time,
            levels_executed=len(levels),
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            results=all_results,
            errors=all_errors,
            performance_metrics={
                "total_tasks": tasks_completed + tasks_failed,
                "success_rate": tasks_completed / max(tasks_completed + tasks_failed, 1),
                "average_task_time": total_time / max(tasks_completed + tasks_failed, 1)
            }
        )
    
    async def _execute_single_task(
        self,
        task: DAGTask,
        execution_id: str,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单个任务
        
        Args:
            task: 任务
            execution_id: 执行ID
            previous_results: 之前的结果
        
        Returns:
            Dict: 任务结果
        """
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        
        try:
            # 获取资源锁（兼容处理：优先使用server_name，回退到mcp_server）
            server_name = getattr(task.tool_metadata, 'server_name', None) or getattr(task.tool_metadata, 'mcp_server', 'default')
            if server_name in self.resource_pools:
                async with self.resource_pools[server_name]:
                    result = await self._execute_task_with_retry(task, previous_results)
            else:
                result = await self._execute_task_with_retry(task, previous_results)
            
            task.status = TaskStatus.COMPLETED
            task.end_time = time.time()
            
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.end_time = time.time()
            raise
    
    async def _execute_task_with_retry(
        self,
        task: DAGTask,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        带重试的任务执行
        
        Args:
            task: 任务
            previous_results: 之前的结果
        
        Returns:
            Dict: 任务结果
        """
        max_retries = task.tool_metadata.retry_count
        
        for attempt in range(max_retries + 1):
            try:
                # 检查缓存
                if task.tool_metadata.cacheable:
                    cached_result = await self._check_cache(task)
                    if cached_result:
                        logger.debug(f"💾 使用缓存结果: {task.tool_name}")
                        return cached_result
                
                # 执行任务
                result = await self._call_tool(task, previous_results)
                
                # 缓存结果
                if task.tool_metadata.cacheable:
                    await self._cache_result(task, result)
                
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    task.retry_count = attempt + 1
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(f"⚠️ 任务 {task.tool_name} 执行失败，{wait_time}s后重试 (第{attempt + 1}次)")
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        raise RuntimeError(f"任务 {task.tool_name} 达到最大重试次数")
    
    async def _check_cache(self, task: DAGTask) -> Optional[Dict[str, Any]]:
        """检查缓存"""
        if self.cache_manager:
            try:
                cache_key = self._generate_cache_key(task)
                cached_result = await self.cache_manager.get_cache(cache_key)
                if cached_result:
                    return cached_result
            except Exception as e:
                logger.warning(f"缓存检查失败: {task.tool_name}, {e}")
        
        return None
    
    async def _cache_result(self, task: DAGTask, result: Dict[str, Any]):
        """缓存结果"""
        if self.cache_manager and task.tool_metadata.cacheable:
            try:
                cache_key = self._generate_cache_key(task)
                await self.cache_manager.set_cache(
                    cache_key,
                    result,
                    ttl=task.tool_metadata.cache_ttl
                )
            except Exception as e:
                logger.warning(f"缓存存储失败: {task.tool_name}, {e}")
    
    def _generate_cache_key(self, task: DAGTask) -> str:
        """生成缓存键"""
        key_data = {
            "tool_name": task.tool_name,
            "params": task.params,
            "user_id": task.params.get("user_id")
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _call_tool(
        self,
        task: DAGTask,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用工具
        
        Args:
            task: 任务
            previous_results: 之前的结果
        
        Returns:
            Dict: 工具结果
        """
        if self.tool_executor:
            # 使用注入的工具执行器
            return await self.tool_executor(
                task.tool_name,
                task.tool_metadata,
                task.params,
                previous_results
            )
        else:
            # 默认实现（返回模拟结果）
            logger.warning(f"⚠️ 未提供工具执行器，返回模拟结果: {task.tool_name}")
            return {
                "tool": task.tool_name,
                "status": "success",
                "data": task.params,
                "timestamp": time.time(),
                "note": "模拟结果（未提供工具执行器）"
            }
    
    def _generate_execution_id(self) -> str:
        """生成执行ID"""
        import uuid
        return f"dag_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    def _update_average_execution_time(self, execution_time: float):
        """更新平均执行时间"""
        total = self.performance_stats["successful_executions"]
        avg = self.performance_stats["average_execution_time"]
        self.performance_stats["average_execution_time"] = (
            (avg * (total - 1) + execution_time) / total
        )
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            **self.performance_stats,
            "execution_history": self.execution_history[-10:],  # 最近10次执行
            "tool_count": len(self.tool_registry)
        }
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history[-limit:]
