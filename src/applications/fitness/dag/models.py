# -*- coding: utf-8 -*-
"""
DAG数据模型定义

定义DAG编排系统使用的所有数据模型，包括：
- TaskStatus: 任务执行状态枚举
- TaskPriority: 任务优先级枚举
- ToolMetadata: 工具元数据
- DAGTask: DAG任务定义
- ExecutionLevel: 执行层级
- DAGExecutionResult: DAG执行结果
- TaskResult: 单个任务执行结果

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-28
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class TaskStatus(Enum):
    """任务执行状态"""
    PENDING = "pending"           # 等待执行
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 执行失败
    SKIPPED = "skipped"          # 跳过（依赖失败或参数缺失）
    CANCELLED = "cancelled"      # 已取消


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 1     # 关键任务（如安全检查）
    HIGH = 2         # 高优先级（如用户档案获取）
    NORMAL = 3       # 普通优先级
    LOW = 4          # 低优先级（可选工具）


@dataclass
class ToolMetadata:
    """
    工具元数据
    
    描述MCP工具的执行特性和约束条件。
    
    Attributes:
        name: 工具名称
        mcp_server: MCP服务器名称
        execution_time: 预估执行时间(秒)
        cacheable: 是否可缓存
        cache_ttl: 缓存TTL(秒)
        parallel_safe: 是否可并行执行
        supports_concurrent: 是否支持并发
        resource_requirements: 资源需求
        dependencies: 依赖的其他工具
        priority: 任务优先级
        retry_count: 最大重试次数
        timeout: 超时时间(秒)
    """
    name: str
    mcp_server: str
    execution_time: float = 1.0
    cacheable: bool = True
    cache_ttl: int = 300
    parallel_safe: bool = True
    supports_concurrent: bool = False
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 3
    timeout: float = 30.0


@dataclass
class DAGTask:
    """
    DAG任务定义
    
    表示DAG中的一个执行节点。
    
    Attributes:
        tool_name: 工具名称
        tool_metadata: 工具元数据
        params: 工具参数
        dependencies: 依赖的任务列表
        status: 当前执行状态
        priority: 任务优先级
        retry_count: 当前重试次数
        result: 执行结果
        error: 错误信息
        start_time: 开始时间
        end_time: 结束时间
        execution_order: 执行顺序
        level: DAG层级
    """
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
    level: Optional[int] = None

    @property
    def duration(self) -> Optional[float]:
        """计算任务执行时长"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_completed(self) -> bool:
        """检查任务是否已完成"""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """检查任务是否失败"""
        return self.status == TaskStatus.FAILED

    @property
    def is_skipped(self) -> bool:
        """检查任务是否被跳过"""
        return self.status == TaskStatus.SKIPPED


@dataclass
class TaskResult:
    """
    单个任务执行结果
    
    Attributes:
        tool_name: 工具名称
        success: 是否成功
        data: 结果数据
        error: 错误信息
        execution_time_ms: 执行时间(毫秒)
        cached: 是否来自缓存
        skipped: 是否被跳过
        skip_reason: 跳过原因
    """
    tool_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    cached: bool = False
    skipped: bool = False
    skip_reason: Optional[str] = None

    @classmethod
    def from_dag_task(cls, task: DAGTask) -> "TaskResult":
        """从DAGTask创建TaskResult"""
        return cls(
            tool_name=task.tool_name,
            success=task.is_completed,
            data=task.result,
            error=task.error,
            execution_time_ms=(task.duration or 0) * 1000,
            cached=False,
            skipped=task.is_skipped,
            skip_reason=task.error if task.is_skipped else None
        )


@dataclass
class ExecutionLevel:
    """
    执行层级
    
    表示DAG中可以并行执行的一组任务。
    
    Attributes:
        level: 层级编号
        tasks: 该层级的任务列表
        parallel_groups: 并行执行组
        estimated_duration: 预估执行时长
        can_parallel: 是否可以并行执行
    """
    level: int
    tasks: List[DAGTask]
    parallel_groups: List[List[DAGTask]] = field(default_factory=list)
    estimated_duration: float = 0.0
    can_parallel: bool = True

    @property
    def task_count(self) -> int:
        """获取任务数量"""
        return len(self.tasks)

    @property
    def tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return [task.tool_name for task in self.tasks]


@dataclass
class DAGExecutionResult:
    """
    DAG执行结果
    
    包含整个DAG执行的完整结果信息。
    
    Attributes:
        execution_id: 执行ID
        intent_pattern: 意图模式/模板ID
        success: 是否成功
        total_time: 总执行时间(秒)
        levels_executed: 执行的层级数
        tasks_completed: 完成的任务数
        tasks_failed: 失败的任务数
        tasks_skipped: 跳过的任务数
        results: 所有任务的结果
        errors: 所有错误信息
        performance_metrics: 性能指标
    """
    execution_id: str
    intent_pattern: str
    success: bool
    total_time: float
    levels_executed: int
    tasks_completed: int
    tasks_failed: int
    tasks_skipped: int = 0
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tasks(self) -> int:
        """获取总任务数"""
        return self.tasks_completed + self.tasks_failed + self.tasks_skipped

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        total = self.total_tasks
        if total == 0:
            return 0.0
        return self.tasks_completed / total

    @property
    def average_task_time(self) -> float:
        """计算平均任务时间"""
        total = self.total_tasks
        if total == 0:
            return 0.0
        return self.total_time / total

    def get_result(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取指定工具的结果"""
        return self.results.get(tool_name)

    def get_error(self, tool_name: str) -> Optional[str]:
        """获取指定工具的错误"""
        return self.errors.get(tool_name)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "execution_id": self.execution_id,
            "intent_pattern": self.intent_pattern,
            "success": self.success,
            "total_time": self.total_time,
            "levels_executed": self.levels_executed,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_skipped": self.tasks_skipped,
            "total_tasks": self.total_tasks,
            "success_rate": self.success_rate,
            "average_task_time": self.average_task_time,
            "results": self.results,
            "errors": self.errors,
            "performance_metrics": self.performance_metrics
        }
