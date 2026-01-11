# -*- coding: utf-8 -*-
"""
MCPOrchestrator - MCP工具编排器（通用框架）

基于DAG任务分解 + Kahn拓扑排序 + 异步并行执行

理论基础：
1. Task Decomposition: 将复杂查询拆分为可独立执行的子任务
2. Dependency Resolution: 使用DAG表示任务依赖关系
3. Topological Sorting (Kahn's Algorithm): 确定合法的执行顺序
4. Asynchronous I/O (asyncio): 并行执行无依赖任务，提升吞吐量
5. TTL Caching: 避免短时间内重复调用相同MCP工具

论文参考：
- "Airflow" (Apache, 2014): DAG任务编排框架
- "Temporal" (Uber, 2019): 分布式工作流引擎
- "Kahn's Algorithm" (1962): 拓扑排序经典算法

设计原则：
- 领域无关：不依赖特定MCP工具
- 自动并行：识别并行机会，最大化吞吐量
- 容错机制：单个任务失败不影响其他任务

数学原理（Kahn拓扑排序）：
    1. 计算每个节点的入度（依赖数量）
    2. 将入度为0的节点加入队列
    3. 从队列取出节点，执行并减少其后继节点的入度
    4. 重复直到所有节点执行完毕
    
    时间复杂度：O(V + E)，V=节点数，E=边数

Example:
    >>> orchestrator = MCPOrchestrator(metadata_db)
    >>> 
    >>> # 定义任务DAG
    >>> tasks = [
    ...     Task("get_profile", "user-profile-stdio", "get_user_profile", 
    ...          params={"user_id": "zhangsan"}),
    ...     Task("get_exercises", "professional-fitness-coach-stdio", "search-exercises-semantic",
    ...          params={"muscle_group": "chest"}, depends_on=["get_profile"]),
    ...     Task("create_plan", "enhanced-coach-stdio", "create_training_plan",
    ...          params={}, depends_on=["get_profile", "get_exercises"])
    ... ]
    >>> 
    >>> # 执行编排
    >>> results = await orchestrator.execute(tasks)
    >>> print(results["create_plan"])

版本：v1.0.0
日期：2025-10-28
"""

import asyncio
import hashlib
import json
import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    SKIPPED = "skipped"       # 跳过（依赖失败）


@dataclass
class Task:
    """
    任务定义
    
    Attributes:
        task_id: 任务唯一标识
        mcp_server: MCP服务器名称（例如："user-profile-stdio"）
        tool_name: 工具名称（例如："get_user_profile"）
        params: 工具参数（字典）
        depends_on: 依赖的任务ID列表（默认为空）
        status: 任务状态（默认PENDING）
        result: 执行结果（成功后填充）
        error: 错误信息（失败时填充）
        start_time: 开始时间
        end_time: 结束时间
    
    Example:
        >>> task = Task(
        ...     task_id="get_profile",
        ...     mcp_server="user-profile-stdio",
        ...     tool_name="get_user_profile",
        ...     params={"user_id": "zhangsan"},
        ...     depends_on=[]
        ... )
    """
    task_id: str
    mcp_server: str
    tool_name: str
    params: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class MCPOrchestrator:
    """
    MCP工具编排器（通用框架）
    
    核心算法：Kahn拓扑排序 + asyncio并行执行
    
    工作流程：
    1. 构建DAG图（任务 + 依赖关系）
    2. 检测循环依赖（如果存在则报错）
    3. Kahn拓扑排序（确定执行顺序）
    4. 异步并行执行（无依赖任务并行）
    5. 结果聚合
    
    设计原则：
    - 领域无关：不依赖特定MCP工具
    - 自动并行：识别并行机会
    - 缓存优化：TTL缓存避免重复调用
    
    Example:
        >>> orchestrator = MCPOrchestrator(metadata_db)
        >>> 
        >>> tasks = [
        ...     Task("task1", "mcp1", "tool1", {}),
        ...     Task("task2", "mcp2", "tool2", {}, depends_on=["task1"]),
        ...     Task("task3", "mcp3", "tool3", {}, depends_on=["task1"]),
        ...     Task("task4", "mcp4", "tool4", {}, depends_on=["task2", "task3"])
        ... ]
        >>> 
        >>> results = await orchestrator.execute(tasks)
        >>> # task1 先执行
        >>> # task2 和 task3 并行执行
        >>> # task4 最后执行
    """
    
    def __init__(
        self,
        metadata_db,  # MetadataDB实例
        cache_ttl: int = 300,  # 缓存TTL（秒）
        max_parallel: int = 5,   # 最大并行数
        mcp_client_pool = None,  # ConfigurableMCPClient实例（可选）
        user_profile_provider = None,  # 用户档案提供器（可选，由应用层注入）
        tool_registry = None  # 工具注册器（可选，由应用层注入领域特定工具）
    ):
        """
        初始化编排器

        Args:
            metadata_db: MetadataDB实例（用于缓存）
            cache_ttl: 缓存TTL（默认300秒）
            max_parallel: 最大并行任务数（默认5）
            mcp_client_pool: ConfigurableMCPClient实例（可选，使用stdio协议）
            user_profile_provider: 用户档案提供器（可选，由应用层注入，保持Framework层领域无关性）
            tool_registry: 工具注册器（可选，由应用层注入领域特定工具，保持Framework层领域无关性）
        """
        self.metadata_db = metadata_db
        self.cache_ttl = cache_ttl
        self.max_parallel = max_parallel
        self.semaphore = asyncio.Semaphore(max_parallel)

        # 用户档案提供器（由应用层注入，保持Framework层领域无关性）
        self.user_profile_provider = user_profile_provider

        # 工具注册器（由应用层注入，保持Framework层领域无关性）
        self.tool_registry = tool_registry

        # MCP客户端池（仅支持Stdio模式）
        self.mcp_client_pool = mcp_client_pool

        # 确定MCP模式
        if self.mcp_client_pool:
            mcp_mode = "stdio"
        else:
            mcp_mode = "local"

        logger.info(
            f"MCPOrchestrator v3.0 initialized: cache_ttl={cache_ttl}s, "
            f"max_parallel={max_parallel}, mcp_mode={mcp_mode}"
        )
    
    async def execute(
        self,
        tasks: List[Task],
        user_id: Optional[str] = None,
        preloaded_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行任务编排（异步）
        
        工作流程：
        1. 构建任务字典
        2. 检测循环依赖
        3. Kahn拓扑排序
        4. 并行执行每一层级的任务
        5. 返回结果
        
        Args:
            tasks: 任务列表
            user_id: 用户ID（用于缓存命名空间）
            preloaded_results: 预加载的结果数据（v3.2.1新增）
                用于注入已知数据，避免重复执行任务
                例如: {"get_user_profile": {...}}
        
        Returns:
            Dict[str, Any]: 任务结果字典
                {
                    "task1": {...},
                    "task2": {...},
                    ...
                }
        
        Raises:
            ValueError: 如果存在循环依赖
        
        Example:
            >>> tasks = [
            ...     Task("t1", "mcp1", "tool1", {}),
            ...     Task("t2", "mcp2", "tool2", {}, depends_on=["t1"])
            ... ]
            >>> results = await orchestrator.execute(tasks)
        """
        logger.info(f"Starting orchestration: {len(tasks)} tasks")
        
        # 1. 构建任务字典
        task_dict = {t.task_id: t for t in tasks}
        
        # 2. 检测循环依赖
        if self._has_cycle(task_dict):
            raise ValueError("Circular dependency detected in task graph")
        
        # 3. Kahn拓扑排序
        execution_order = self._topological_sort(task_dict)
        
        logger.debug(f"Execution order: {execution_order}")
        
        # 4. 初始化结果（包含预加载数据）
        results = preloaded_results.copy() if preloaded_results else {}
        
        if preloaded_results:
            logger.info(
                f"✅ [预加载注入] 初始化 {len(preloaded_results)} 个预加载结果: "
                f"{list(preloaded_results.keys())}"
            )
        
        for level_tasks in execution_order:
            # 并行执行同一层级的任务
            level_results = await asyncio.gather(
                *[
                    self._execute_task(
                        task_dict[task_id],
                        results,
                        user_id
                    )
                    for task_id in level_tasks
                ],
                return_exceptions=True
            )
            
            # 收集结果
            for task_id, result in zip(level_tasks, level_results):
                if isinstance(result, Exception):
                    task_dict[task_id].status = TaskStatus.FAILED
                    task_dict[task_id].error = str(result)
                    logger.error(
                        f"Task {task_id} failed: {result}"
                    )
                else:
                    results[task_id] = result
        
        logger.info(
            f"Orchestration completed: "
            f"{sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)}/{len(tasks)} succeeded"
        )
        
        return results
    
    def inject_preloaded_data(
        self,
        results: Dict[str, Any],
        preloaded_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        注入预加载数据到结果中（v3.2.0新增）
        
        用于将外部预加载的数据（如用户档案）注入到DAG执行结果中，
        避免重复调用MCP工具。
        
        Args:
            results: 当前执行结果
            preloaded_data: 预加载数据字典
                {
                    "get_user_profile": {...},  # 预加载的用户档案
                    "cached_exercises": [...]   # 预加载的动作库
                }
        
        Returns:
            Dict[str, Any]: 合并后的结果（不修改原results）
        
        Example:
            >>> results = await orchestrator.execute(tasks)
            >>> preloaded = {"get_user_profile": {"age": 25, "weight": 70}}
            >>> final_results = orchestrator.inject_preloaded_data(
            ...     results, preloaded
            ... )
            >>> # final_results 包含 results + preloaded 数据
        
        注意：
            - 预加载数据优先级高于执行结果（会覆盖）
            - 仅注入不存在的键，避免覆盖已执行的结果
            - 记录注入日志，便于调试
        """
        # 创建合并后的结果（浅拷贝，避免修改原数据）
        merged_results = {**results}
        
        injected_count = 0
        for key, value in preloaded_data.items():
            if key not in merged_results:
                # 仅注入不存在的键
                merged_results[key] = value
                injected_count += 1
                logger.debug(f"✅ [数据注入] 注入预加载数据: {key}")
            else:
                logger.debug(
                    f"⚠️ [数据注入] 跳过已存在的键: {key} "
                    "(保留执行结果，不覆盖)"
                )
        
        if injected_count > 0:
            logger.info(
                f"📊 [数据注入] 成功注入 {injected_count} 个预加载数据项"
            )
        
        return merged_results
    
    def _has_cycle(self, task_dict: Dict[str, Task]) -> bool:
        """
        检测循环依赖（DFS）
        
        算法：深度优先搜索，使用三色标记
        - WHITE（0）: 未访问
        - GRAY（1）: 访问中
        - BLACK（2）: 已完成
        
        如果访问到GRAY节点，说明存在环
        
        Args:
            task_dict: 任务字典
        
        Returns:
            bool: True表示有环，False表示无环
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {task_id: WHITE for task_id in task_dict}
        
        def dfs(task_id: str) -> bool:
            if color[task_id] == GRAY:
                return True  # 找到环
            
            if color[task_id] == BLACK:
                return False  # 已访问过
            
            color[task_id] = GRAY
            
            for dep in task_dict[task_id].depends_on:
                if dep in task_dict and dfs(dep):
                    return True
            
            color[task_id] = BLACK
            return False
        
        # 检查所有节点
        for task_id in task_dict:
            if color[task_id] == WHITE:
                if dfs(task_id):
                    return True
        
        return False
    
    def _topological_sort(
        self,
        task_dict: Dict[str, Task]
    ) -> List[List[str]]:
        """
        Kahn拓扑排序（分层）
        
        返回分层的任务ID列表，同一层级的任务可以并行执行
        
        算法：
        1. 计算每个任务的入度（依赖数量）
        2. 将入度为0的任务加入第一层
        3. 执行第一层任务后，更新依赖任务的入度
        4. 将新的入度为0的任务加入下一层
        5. 重复直到所有任务分配完毕
        
        Args:
            task_dict: 任务字典
        
        Returns:
            List[List[str]]: 分层的任务ID列表
                [
                    ["task1", "task2"],  # 第1层（并行）
                    ["task3"],           # 第2层
                    ["task4", "task5"]   # 第3层（并行）
                ]
        
        Example:
            >>> # DAG: t1 → t2 → t4
            >>> #      t1 → t3 → t4
            >>> result = orchestrator._topological_sort(task_dict)
            >>> # [[t1], [t2, t3], [t4]]
        """
        # 计算入度
        in_degree = {task_id: 0 for task_id in task_dict}
        
        for task in task_dict.values():
            for dep in task.depends_on:
                if dep in in_degree:
                    in_degree[task.task_id] += 1
        
        # 分层执行
        levels = []
        remaining = set(task_dict.keys())
        
        while remaining:
            # 找到当前入度为0的任务
            current_level = [
                task_id for task_id in remaining
                if in_degree[task_id] == 0
            ]
            
            if not current_level:
                # 不应该发生（已检测环）
                break
            
            levels.append(current_level)
            
            # 更新入度
            for task_id in current_level:
                remaining.remove(task_id)
                
                # 减少后继任务的入度
                for other_id in remaining:
                    if task_id in task_dict[other_id].depends_on:
                        in_degree[other_id] -= 1
        
        return levels
    
    async def _execute_task(
        self,
        task: Task,
        results: Dict[str, Any],
        user_id: Optional[str]
    ) -> Any:
        """
        执行单个任务（异步）
        
        工作流程：
        1. 检查依赖是否都成功
        2. 检查缓存
        3. 执行MCP工具调用（模拟）
        4. 更新缓存
        5. 返回结果
        
        Args:
            task: 任务对象
            results: 已完成任务的结果字典
            user_id: 用户ID
        
        Returns:
            Any: 任务执行结果
        
        Raises:
            RuntimeError: 如果依赖任务失败
        """
        async with self.semaphore:
            task.status = TaskStatus.RUNNING
            task.start_time = time.time()
            
            try:
                # 检查依赖
                for dep_id in task.depends_on:
                    if dep_id not in results:
                        raise RuntimeError(
                            f"Dependency {dep_id} not completed"
                        )
                
                # 检查缓存
                cache_key = self._build_cache_key(
                    task.mcp_server,
                    task.tool_name,
                    task.params,
                    user_id
                )
                
                cached_result = self.metadata_db.get_cache(cache_key)
                
                if cached_result is not None:
                    logger.info(
                        f"Cache hit for task {task.task_id}: {cache_key}"
                    )
                    task.result = cached_result
                    task.status = TaskStatus.COMPLETED
                    task.end_time = time.time()
                    return cached_result
                
                # 执行MCP工具调用（模拟）
                logger.info(
                    f"Executing task {task.task_id}: "
                    f"{task.mcp_server}.{task.tool_name}"
                )

                # 确保参数是可序列化的
                serializable_params = {}
                for key, value in task.params.items():
                    if hasattr(value, 'to_dict'):
                        # 如果对象有to_dict方法，使用它
                        serializable_params[key] = value.to_dict()
                    elif isinstance(value, dict):
                        # 如果是字典，递归处理嵌套对象
                        serializable_params[key] = self._make_dict_serializable(value)
                    elif hasattr(value, '__dict__'):
                        # 对于有属性的对象，尝试安全序列化
                        serializable_params[key] = str(value)
                    else:
                        # 对于其他类型，直接使用
                        serializable_params[key] = value

                result = await self._call_mcp_tool(
                    task.mcp_server,
                    task.tool_name,
                    serializable_params
                )
                
                # 更新缓存
                # 生成params_hash（用于MetadataDB.set_cache）
                # 确保所有参数都是JSON可序列化的
                # 使用已经在上面处理好的serializable_params
                # 再次确保所有值都是可序列化的（双重保护）

                # 额外序列化检查，防止UserProfile等对象漏网
                def deep_serialize(obj):
                    if hasattr(obj, 'to_dict'):
                        return obj.to_dict()
                    elif isinstance(obj, dict):
                        return {k: deep_serialize(v) for k, v in obj.items()}
                    elif isinstance(obj, (list, tuple)):
                        return [deep_serialize(item) for item in obj]
                    elif hasattr(obj, '__dict__'):
                        return str(obj)  # 对于其他对象，转换为字符串
                    else:
                        return obj

                # 深度序列化所有参数值
                fully_serializable_params = {}
                for k, v in serializable_params.items():
                    fully_serializable_params[k] = deep_serialize(v)

                sorted_params = sorted(fully_serializable_params.items())
                params_json = json.dumps(sorted_params, sort_keys=True)
                params_hash = hashlib.md5(params_json.encode()).hexdigest()
                
                # 确保result也是可序列化的
                serializable_result = self._make_dict_serializable(result)

                self.metadata_db.set_cache(
                    cache_key=cache_key,
                    tool_name=task.tool_name,
                    params_hash=params_hash,
                    result=serializable_result,
                    ttl=self.cache_ttl
                )
                
                # 更新任务状态
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.end_time = time.time()
                
                logger.info(
                    f"Task {task.task_id} completed in "
                    f"{task.end_time - task.start_time:.2f}s"
                )
                
                return result
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.end_time = time.time()
                
                logger.error(
                    f"Task {task.task_id} failed: {e}"
                )
                
                raise
    
    def _make_dict_serializable(self, obj: Any) -> Any:
        """
        递归处理字典中的对象，确保其可序列化

        Args:
            obj: 需要处理的对象（字典、列表或其他类型）

        Returns:
            Any: 处理后的可序列化对象
        """
        if obj is None:
            return None

        if hasattr(obj, 'to_dict'):
            # 如果对象有to_dict方法，使用它
            return obj.to_dict()
        elif isinstance(obj, dict):
            # 递归处理字典
            result = {}
            for key, value in obj.items():
                # 确保key是字符串
                if not isinstance(key, str):
                    key = str(key)
                result[key] = self._make_dict_serializable(value)
            return result
        elif isinstance(obj, (list, tuple)):
            # 递归处理列表/元组
            return [self._make_dict_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # 对于有属性的对象，尝试转换为字符串
            try:
                return str(obj)
            except Exception:
                return f"<{type(obj).__name__} object>"
        elif isinstance(obj, (str, int, float, bool)):
            # 基本类型直接返回
            return obj
        else:
            # 其他类型尝试转换为字符串
            try:
                return str(obj)
            except Exception:
                return f"<{type(obj).__name__} object>"

    def _build_cache_key(
        self,
        mcp_server: str,
        tool_name: str,
        params: Dict[str, Any],
        user_id: Optional[str]
    ) -> str:
        """
        构建缓存键
        
        格式：mcp://{user_id}/{mcp_server}/{tool_name}?{params}
        
        Args:
            mcp_server: MCP服务器名称
            tool_name: 工具名称
            params: 参数字典
            user_id: 用户ID（可选）
        
        Returns:
            str: 缓存键
        
        Example:
            >>> key = orchestrator._build_cache_key(
            ...     "user-profile-stdio",
            ...     "get_user_profile",
            ...     {"user_id": "zhangsan"},
            ...     "zhangsan"
            ... )
            >>> # "mcp://zhangsan/user-profile-stdio/get_user_profile?user_id=zhangsan"
        """
        # 排序参数以保证一致性
        sorted_params = sorted(params.items())
        params_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        
        user_prefix = f"{user_id}/" if user_id else ""
        
        return f"mcp://{user_prefix}{mcp_server}/{tool_name}?{params_str}"
    
    async def call_tool(
        self,
        mcp_server: str,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        调用MCP工具（公开方法）- v3.0仅支持Stdio模式

        根据客户端池类型，自动切换Stdio或本地实现

        Args:
            mcp_server: MCP服务器名称
            tool_name: 工具名称
            params: 参数字典

        Returns:
            Any: 工具调用结果

        Raises:
            RuntimeError: 如果MCP调用失败
        """
        return await self._call_mcp_tool(mcp_server, tool_name, params)

    async def _call_mcp_tool(
        self,
        mcp_server: str,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        调用MCP工具（私有方法）- v3.0仅支持Stdio模式

        根据客户端池类型，自动切换Stdio或本地实现

        Args:
            mcp_server: MCP服务器名称
            tool_name: 工具名称
            params: 参数字典

        Returns:
            Any: 工具调用结果

        Raises:
            RuntimeError: 如果MCP调用失败
        """
        # Stdio客户端模式
        if self.mcp_client_pool:
            try:
                logger.debug(
                    f"Calling Stdio MCP tool: server={mcp_server}, tool={tool_name}"
                )

                # 使用ConfigurableMCPClient的request方法
                result = await self.mcp_client_pool.request({
                    "server_name": mcp_server,
                    "tool_name": tool_name,
                    "arguments": params
                })

                logger.debug(
                    f"Stdio MCP tool completed: server={mcp_server}, tool={tool_name}"
                )

                return result

            except Exception as e:
                logger.error(
                    f"Stdio MCP tool call failed: server={mcp_server}, "
                    f"tool={tool_name}, error={e}"
                )
                # 降级到本地实现而不是报错
                logger.info(f"Falling back to LOCAL implementation: server={mcp_server}, tool={tool_name}")
                return await self._call_local_implementation(
                    mcp_server, tool_name, params
                )

        # 本地实现模式（直接调用GraphRAG和BackendClient）
        else:
            logger.info(
                f"Using LOCAL implementation: server={mcp_server}, "
                f"tool={tool_name}"
            )

            # 根据工具名称直接调用本地实现
            return await self._call_local_implementation(
                mcp_server, tool_name, params
            )
    
    async def _call_local_implementation(
        self,
        mcp_server: str,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        本地实现模式：直接调用GraphRAG、BackendClient和HTTP API

        替代真实的MCP服务器调用，用于DAML-RAG项目（v4.0统一DAML-RAG Server架构）

        Args:
            mcp_server: MCP服务器名称（当前架构使用内置本地实现）
            tool_name: 工具名称
            params: 参数字典

        Returns:
            Any: 工具调用结果
        """
        try:
            # 1. 用户档案工具 - 通过BackendClient调用Laravel API
            if tool_name == "get_user_profile":
                user_id = params.get("user_id")
                if not user_id:
                    return {"error": "user_id is required"}

                # 从params中检查是否有预加载的用户档案
                preloaded_profile = params.get("preloaded_user_profile")
                if preloaded_profile:
                    logger.info(f"✓ Using preloaded user profile for user_id={user_id}")
                    # 确保返回可序列化的字典格式
                    if hasattr(preloaded_profile, 'to_dict'):
                        return preloaded_profile.to_dict()
                    elif isinstance(preloaded_profile, dict):
                        return preloaded_profile
                    else:
                        # 如果是其他类型，尝试转换为字典
                        return {
                            "user_id": getattr(preloaded_profile, 'user_id', str(user_id)),
                            "basic_info": getattr(preloaded_profile, 'basic_info', {}),
                            "nutrition_profile": getattr(preloaded_profile, 'nutrition_profile', {}),
                            "fitness_config": getattr(preloaded_profile, 'fitness_config', {}),
                            "fitness_goals": getattr(preloaded_profile, 'fitness_goals', {}),
                            "strength_levels": getattr(preloaded_profile, 'strength_levels', {}),
                            "health_profile": getattr(preloaded_profile, 'health_profile', {}),
                            "created_at": getattr(preloaded_profile, 'created_at', None),
                            "updated_at": getattr(preloaded_profile, 'updated_at', None),
                        }

                # 通过注入的用户档案获取器获取用户档案
                # Framework层不应直接依赖BackendClient，应由应用层注入用户档案获取器
                if hasattr(self, 'user_profile_provider') and self.user_profile_provider:
                    try:
                        profile = await self.user_profile_provider(user_id)
                        return profile
                    except Exception as e:
                        logger.warning(f"User profile provider failed: {e}")

                # 返回基础用户信息，避免硬编码依赖
                return {
                    "user_id": str(user_id),
                    "note": "No user profile provider available in Framework layer",
                    "fallback_mode": True
                }

            # 2. GraphRAG查询工具 - 直接调用GraphRAG
            elif tool_name == "query_knowledge_graph":
                try:
                    from src.framework.retrieval.graphrag import GraphRAGQueryTool
                    from src.framework.retrieval.graph.kg_full import KnowledgeGraphFull
                    import os

                    # 初始化KnowledgeGraphFull
                    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
                    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
                    neo4j_password = os.getenv('NEO4J_PASSWORD', 'build_body_2024')
                    qdrant_host = os.getenv('QDRANT_HOST', 'qdrant')
                    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))

                    kg_full = KnowledgeGraphFull(
                        neo4j_uri=neo4j_uri,
                        neo4j_user=neo4j_user,
                        neo4j_password=neo4j_password,
                        qdrant_host=qdrant_host,
                        qdrant_port=qdrant_port,
                        qdrant_collection="training_knowledge",
                        vector_size=1024,  # 使用BGE-M3
                        embedding_model="BAAI/bge-m3"  # 指定BGE-M3模型
                    )

                    # 创建GraphRAG查询工具
                    graphrag_tool = GraphRAGQueryTool(kg_full)

                    # 执行查询
                    # 框架层领域无关 - Requirements 6.1, 6.2
                    # domain参数默认为"general"，由应用层传入具体领域
                    query_args = {
                        "query_type": params.get("query_type", "hybrid"),
                        "domain": params.get("domain", "general"),
                        "query_text": params.get("query_text", ""),
                        "filters": params.get("filters", {}),
                        "top_k": params.get("top_k", 10),
                        "min_similarity": params.get("min_similarity", 0.5),
                        "return_reason": params.get("return_reason", True)
                    }

                    result = await graphrag_tool.query(query_args)
                    return result

                except Exception as e:
                    logger.error(f"GraphRAG query failed: {e}")
                    return {
                        "tool": tool_name,
                        "query_text": params.get("query_text", ""),
                        "results": [],
                        "error": f"GraphRAG integration failed: {e}"
                    }

            # 3. 领域工具 - 通过工具注册器动态调用（v8.14.0重构：移除硬编码）
            # ========== 工具注册机制 ==========
            # Framework层通过工具注册器处理领域特定工具
            # 由应用层注册工具，保持Framework层领域无关性
            # 不再使用硬编码工具列表，而是直接检查tool_registry
            if hasattr(self, 'tool_registry') and self.tool_registry:
                # 检查工具是否已注册
                tool = self.tool_registry.get_tool(tool_name)
                if tool:
                    logger.info(f"📝 Calling registered tool via tool_registry: {tool_name}")
                    try:
                        # 方式1：如果registry有call_tool方法（推荐）
                        if hasattr(self.tool_registry, 'call_tool'):
                            result = await self.tool_registry.call_tool(tool_name, params)
                            return result
                        
                        # 方式2：如果registry返回工具实例（BaseMCPTool）
                        # BaseMCPTool实例需要调用execute方法
                        if hasattr(tool, 'execute'):
                            result = await tool.execute(params)
                            return result
                        # 如果是可调用对象
                        elif callable(tool):
                            result = await tool(params)
                            return result
                    except Exception as e:
                        logger.error(f"Tool '{tool_name}' execution failed: {e}")
                        return {"tool": tool_name, "status": "error", "error": str(e)}
            
            # 如果工具未注册，返回错误信息
            logger.warning(f"Tool '{tool_name}' not registered in tool_registry")
            return {
                "tool": tool_name,
                "status": "not_found",
                "error": f"Tool '{tool_name}' is not registered. Please register tools at application layer."
            }

        except Exception as e:
            logger.error(f"Local implementation failed: {tool_name}, error={e}")
            raise RuntimeError(f"Local implementation of '{tool_name}' failed: {e}")

    def get_execution_summary(self, tasks: List[Task]) -> Dict:
        """
        获取执行摘要
        
        Args:
            tasks: 任务列表
        
        Returns:
            Dict: 执行摘要
                {
                    "total": 10,
                    "completed": 8,
                    "failed": 1,
                    "skipped": 1,
                    "avg_duration": 0.25,
                    "total_duration": 2.5,
                    "parallel_efficiency": 0.75
                }
        
        Example:
            >>> summary = orchestrator.get_execution_summary(tasks)
            >>> print(f"成功率: {summary['completed'] / summary['total']:.1%}")
        """
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)
        
        # 计算执行时长
        durations = [
            t.end_time - t.start_time
            for t in tasks
            if t.start_time and t.end_time
        ]
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 总时长（从最早开始到最晚结束）
        start_times = [t.start_time for t in tasks if t.start_time]
        end_times = [t.end_time for t in tasks if t.end_time]
        
        total_duration = (
            max(end_times) - min(start_times)
            if start_times and end_times
            else 0
        )
        
        # 并行效率 = 理论时长 / 实际时长
        theoretical_duration = sum(durations)
        parallel_efficiency = (
            theoretical_duration / total_duration
            if total_duration > 0
            else 0
        )
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "avg_duration": avg_duration,
            "total_duration": total_duration,
            "parallel_efficiency": parallel_efficiency
        }

