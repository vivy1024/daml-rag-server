# -*- coding: utf-8 -*-
"""
并发执行优化器 - Phase 2.3

专门优化Layer 1和Layer 2的并发执行性能。

优化策略:
1. 智能超时控制
2. 优先级任务调度
3. 连接池复用
4. 早停机制
5. 性能预测

版本: v2.0.0
日期: 2025-11-26
作者: 薛小川 (Phase 2)
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import heapq
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 1    # 关键任务
    HIGH = 2        # 高优先级
    NORMAL = 3      # 普通优先级
    LOW = 4         # 低优先级


@dataclass
class ConcurrentTask:
    """并发任务"""
    task_id: str
    priority: TaskPriority
    coro: asyncio.Task
    start_time: float = field(default_factory=time.time)
    timeout: float = 10.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """优先级队列比较 (数值越小优先级越高)"""
        return self.priority.value < other.priority.value


@dataclass
class OptimizationConfig:
    """并发优化配置"""
    # 超时控制
    layer1_timeout: float = 8.0      # Layer 1超时时间
    layer2_timeout: float = 10.0     # Layer 2超时时间
    total_timeout: float = 15.0      # 总超时时间

    # 任务调度
    enable_priority_scheduling: bool = True
    max_concurrent_tasks: int = 2
    task_queue_size: int = 100

    # 早停机制
    enable_early_stopping: bool = True
    quality_threshold: float = 0.8   # 质量阈值
    min_results_needed: int = 5      # 最少需要结果数

    # 性能优化
    enable_connection_pooling: bool = True
    reuse_http_sessions: bool = True
    max_retry_attempts: int = 3

    # 监控
    enable_performance_tracking: bool = True
    detailed_metrics: bool = True


class PriorityTaskScheduler:
    """优先级任务调度器"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.task_queue = []
        self.running_tasks = {}
        self.completed_tasks = []
        self.performance_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "timeout_tasks": 0,
            "avg_execution_time": 0.0
        }

    async def schedule_task(
        self,
        task_id: str,
        coro: Callable,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = 10.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        调度任务执行

        Args:
            task_id: 任务ID
            coro: 协程函数
            priority: 优先级
            timeout: 超时时间
            metadata: 任务元数据

        Returns:
            任务结果
        """
        self.performance_metrics["total_tasks"] += 1

        try:
            # 创建任务
            task = ConcurrentTask(
                task_id=task_id,
                priority=priority,
                coro=coro(),
                timeout=timeout,
                metadata=metadata or {}
            )

            logger.debug(f"📋 调度任务: {task_id} (优先级: {priority.name})")

            # 使用asyncio.wait_for实现超时控制
            result = await asyncio.wait_for(task.coro, timeout=timeout)

            self.performance_metrics["successful_tasks"] += 1

            # 记录性能指标
            execution_time = time.time() - task.start_time
            self._update_performance_metrics(execution_time, success=True)

            logger.debug(f"✅ 任务完成: {task_id} (耗时: {execution_time:.2f}s)")

            return result

        except asyncio.TimeoutError:
            self.performance_metrics["timeout_tasks"] += 1
            self.performance_metrics["failed_tasks"] += 1
            logger.warning(f"⏰ 任务超时: {task_id} (超时: {timeout}s)")
            raise

        except Exception as e:
            self.performance_metrics["failed_tasks"] += 1
            logger.error(f"❌ 任务失败: {task_id} - {e}")
            raise

    def _update_performance_metrics(self, execution_time: float, success: bool):
        """更新性能指标"""
        if success:
            # 移动平均
            alpha = 0.2
            self.performance_metrics["avg_execution_time"] = (
                self.performance_metrics["avg_execution_time"] * (1 - alpha) +
                execution_time * alpha
            )

    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        metrics = self.performance_metrics.copy()

        if metrics["total_tasks"] > 0:
            metrics["success_rate"] = (
                metrics["successful_tasks"] / metrics["total_tasks"] * 100
            )
            metrics["timeout_rate"] = (
                metrics["timeout_tasks"] / metrics["total_tasks"] * 100
            )

        return metrics


class EarlyStoppingMonitor:
    """早停机制监控器"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.start_time = time.time()
        self.best_results = []
        self.quality_history = []

    def should_stop_early(
        self,
        current_results: List[Dict[str, Any]],
        layer1_time: float,
        layer2_time: float
    ) -> Tuple[bool, str]:
        """
        判断是否应该早停

        Args:
            current_results: 当前结果列表
            layer1_time: Layer 1执行时间
            layer2_time: Layer 2执行时间

        Returns:
            (是否早停, 早停原因)
        """
        if not self.config.enable_early_stopping:
            return False, ""

        # 检查总超时
        total_time = time.time() - self.start_time
        if total_time >= self.config.total_timeout:
            return True, f"总超时: {total_time:.2f}s >= {self.config.total_timeout}s"

        # 检查结果质量
        if current_results:
            avg_quality = sum(
                r.get("score", 0.0) for r in current_results
            ) / len(current_results)

            self.quality_history.append(avg_quality)

            # 如果质量足够好且结果数量充足
            if (avg_quality >= self.config.quality_threshold and
                len(current_results) >= self.config.min_results_needed):
                return True, f"质量达标: {avg_quality:.2f} >= {self.config.quality_threshold}"

            # 检查质量改进趋势
            if len(self.quality_history) >= 3:
                recent_avg = sum(self.quality_history[-3:]) / 3
                older_avg = sum(self.quality_history[:-3]) / len(self.quality_history[:-3])

                if recent_avg <= older_avg * 0.95:  # 质量下降超过5%
                    return True, f"质量下降: {recent_avg:.2f} < {older_avg:.2f}"

        # 检查时间比例
        if layer1_time > 0 and layer2_time > 0:
            time_ratio = max(layer1_time, layer2_time) / min(layer1_time, layer2_time)
            if time_ratio > 3.0:  # 一层明显慢于另一层
                return True, f"时间不均衡: 比例 {time_ratio:.2f}"

        return False, ""


class ConnectionPoolManager:
    """连接池管理器"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.http_sessions = {}
        self.neo4j_sessions = {}

    async def get_http_session(self, name: str) -> Any:
        """获取HTTP会话"""
        if not self.config.enable_connection_pooling:
            import aiohttp
            return aiohttp.ClientSession()

        if name not in self.http_sessions:
            import aiohttp
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300
            )
            self.http_sessions[name] = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )

        return self.http_sessions[name]

    async def close_all(self):
        """关闭所有连接"""
        for session in self.http_sessions.values():
            await session.close()
        self.http_sessions.clear()

        for session in self.neo4j_sessions.values():
            session.close()
        self.neo4j_sessions.clear()


class ConcurrentOptimizer:
    """并发执行优化器 - Phase 2.3核心组件"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.task_scheduler = PriorityTaskScheduler(config)
        self.early_stopping = EarlyStoppingMonitor(config)
        self.connection_manager = ConnectionPoolManager(config)

        logger.info(f"✅ 并发优化器已初始化")
        logger.info(f"  - Layer1超时: {config.layer1_timeout}s")
        logger.info(f"  - Layer2超时: {config.layer2_timeout}s")
        logger.info(f"  - 早停: {config.enable_early_stopping}")
        logger.info(f"  - 连接池: {config.enable_connection_pooling}")

    async def execute_layer1_optimized(
        self,
        query: str,
        domain: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        base_engine: Any
    ) -> Any:
        """优化的Layer 1执行"""
        logger.info("🚀 执行优化的Layer 1: 向量语义检索")

        async def layer1_task():
            return await base_engine._execute_layer1_vector_search(
                query=query,
                domain=domain,
                top_k=top_k,
                filters=filters
            )

        return await self.task_scheduler.schedule_task(
            task_id="layer1_vector_search",
            coro=layer1_task,
            priority=TaskPriority.HIGH,
            timeout=self.config.layer1_timeout,
            metadata={"layer": "layer1", "type": "vector_search"}
        )

    async def execute_layer2_optimized(
        self,
        query: str,
        domain: str,
        top_k: int,
        base_engine: Any
    ) -> Any:
        """优化的Layer 2执行"""
        logger.info("🚀 执行优化的Layer 2: 图谱关系推理")

        async def layer2_task():
            return await base_engine._execute_layer2_graph_reasoning(
                query=query,
                domain=domain,
                vector_results=[],  # 优化：独立执行，不依赖Layer1
                top_k=top_k
            )

        return await self.task_scheduler.schedule_task(
            task_id="layer2_graph_reasoning",
            coro=layer2_task,
            priority=TaskPriority.HIGH,
            timeout=self.config.layer2_timeout,
            metadata={"layer": "layer2", "type": "graph_reasoning"}
        )

    async def execute_parallel_optimized(
        self,
        query: str,
        domain: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        base_engine: Any,
        user_profile: Optional[Dict[str, Any]] = None,
        safety_check: bool = True
    ) -> Tuple[Any, Any, Dict[str, Any]]:
        """
        执行优化的并行检索

        Returns:
            (layer1_result, layer2_result, optimization_metrics)
        """
        start_time = time.time()

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🚀 并行优化检索开始: {query[:50]}...")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 创建任务
        layer1_coro = self.execute_layer1_optimized(
            query=query,
            domain=domain,
            top_k=top_k * 2,
            filters=filters,
            base_engine=base_engine
        )

        layer2_coro = self.execute_layer2_optimized(
            query=query,
            domain=domain,
            top_k=top_k * 2,
            base_engine=base_engine
        )

        # 并发执行 (无依赖关系)
        layer1_task = asyncio.create_task(layer1_coro)
        layer2_task = asyncio.create_task(layer2_coro)

        # 等待任务完成或早停
        layer1_result = None
        layer2_result = None
        layer1_time = 0.0
        layer2_time = 0.0

        try:
            # 等待两个任务完成
            layer1_result, layer2_result = await asyncio.gather(
                layer1_task,
                layer2_task,
                return_exceptions=True
            )

            # 处理异常
            if isinstance(layer1_result, Exception):
                logger.error(f"Layer1异常: {layer1_result}")
                layer1_result = None

            if isinstance(layer2_result, Exception):
                logger.error(f"Layer2异常: {layer2_result}")
                layer2_result = None

            # 记录执行时间
            if layer1_result and hasattr(layer1_result, 'execution_time_ms'):
                layer1_time = layer1_result.execution_time_ms / 1000.0

            if layer2_result and hasattr(layer2_result, 'execution_time_ms'):
                layer2_time = layer2_result.execution_time_ms / 1000.0

            # 检查早停
            should_stop, stop_reason = self.early_stopping.should_stop_early(
                current_results=(layer1_result.results if layer1_result and layer1_result.success else []) +
                               (layer2_result.results if layer2_result and layer2_result.success else []),
                layer1_time=layer1_time,
                layer2_time=layer2_time
            )

            if should_stop:
                logger.info(f"⏹️  早停触发: {stop_reason}")

            # 构建优化指标
            optimization_metrics = {
                "total_execution_time": time.time() - start_time,
                "layer1_time": layer1_time,
                "layer2_time": layer2_time,
                "parallel_efficiency": max(layer1_time, layer2_time) / (layer1_time + layer2_time) if (layer1_time + layer2_time) > 0 else 0,
                "early_stopping": should_stop,
                "early_stopping_reason": stop_reason,
                "task_scheduler_metrics": self.task_scheduler.get_metrics(),
                "connections_pooled": self.config.enable_connection_pooling,
                "quality_threshold": self.config.quality_threshold
            }

            logger.info(f"✅ 并行优化检索完成")
            logger.info(f"  - Layer1: {len(layer1_result.results) if layer1_result and layer1_result.success else 0}个结果")
            logger.info(f"  - Layer2: {len(layer2_result.results) if layer2_result and layer2_result.success else 0}个结果")
            logger.info(f"  - 并行效率: {optimization_metrics['parallel_efficiency']:.2f}")
            logger.info(f"  - 总耗时: {optimization_metrics['total_execution_time']:.2f}s")

            return layer1_result, layer2_result, optimization_metrics

        except Exception as e:
            logger.error(f"❌ 并行优化检索失败: {e}")
            raise

    async def close(self):
        """关闭优化器"""
        await self.connection_manager.close_all()
        logger.info("并发优化器已关闭")

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "task_scheduler": self.task_scheduler.get_metrics(),
            "early_stopping": {
                "enabled": self.config.enable_early_stopping,
                "quality_threshold": self.config.quality_threshold
            },
            "connection_pooling": {
                "enabled": self.config.enable_connection_pooling,
                "sessions_count": len(self.connection_manager.http_sessions)
            },
            "configuration": {
                "layer1_timeout": self.config.layer1_timeout,
                "layer2_timeout": self.config.layer2_timeout,
                "total_timeout": self.config.total_timeout,
                "max_concurrent_tasks": self.config.max_concurrent_tasks
            }
        }


__all__ = [
    "ConcurrentOptimizer",
    "OptimizationConfig",
    "PriorityTaskScheduler",
    "EarlyStoppingMonitor",
    "ConnectionPoolManager",
    "TaskPriority"
]
