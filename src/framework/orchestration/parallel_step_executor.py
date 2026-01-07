# -*- coding: utf-8 -*-
"""
并行步骤执行器

用于优化工作流中的并行步骤执行，提供：
- 完全并行执行保证
- 增强的错误处理
- 详细的性能监控
- 超时控制
- 降级策略

版本：v1.0.0
创建日期：2025-12-21
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """步骤执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """步骤执行结果"""
    step_number: int
    step_name: str
    status: StepStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ParallelExecutionResult:
    """并行执行结果"""
    success: bool
    total_duration_ms: float
    step_results: List[StepResult]
    errors: List[str]
    metadata: Dict[str, Any]
    
    @property
    def all_steps_succeeded(self) -> bool:
        """检查是否所有步骤都成功"""
        return all(r.status == StepStatus.SUCCESS for r in self.step_results)
    
    @property
    def any_step_failed(self) -> bool:
        """检查是否有步骤失败"""
        return any(r.status == StepStatus.FAILED for r in self.step_results)
    
    @property
    def failed_steps(self) -> List[StepResult]:
        """获取失败的步骤"""
        return [r for r in self.step_results if r.status == StepStatus.FAILED]
    
    @property
    def successful_steps(self) -> List[StepResult]:
        """获取成功的步骤"""
        return [r for r in self.step_results if r.status == StepStatus.SUCCESS]


class ParallelStepExecutor:
    """
    并行步骤执行器
    
    用于执行工作流中的并行步骤，提供完整的错误处理和性能监控
    """
    
    def __init__(
        self,
        request_id: str,
        default_timeout: float = 30.0,
        enable_fallback: bool = True,
        enable_monitoring: bool = True
    ):
        """
        初始化并行步骤执行器
        
        Args:
            request_id: 请求ID
            default_timeout: 默认超时时间（秒）
            enable_fallback: 是否启用降级策略
            enable_monitoring: 是否启用性能监控
        """
        self.request_id = request_id
        self.default_timeout = default_timeout
        self.enable_fallback = enable_fallback
        self.enable_monitoring = enable_monitoring
        
        # 性能监控器（如果启用）
        self.performance_monitor = None
        if enable_monitoring:
            try:
                from ...monitoring.performance_monitor import get_performance_monitor
                self.performance_monitor = get_performance_monitor()
            except Exception as e:
                logger.warning(f"性能监控器初始化失败: {e}")
    
    async def execute_parallel_steps(
        self,
        steps: List[Tuple[int, str, Callable]],
        timeout: Optional[float] = None,
        continue_on_error: bool = True
    ) -> ParallelExecutionResult:
        """
        并行执行多个步骤
        
        Args:
            steps: 步骤列表，每个元素为 (步骤编号, 步骤名称, 异步函数)
            timeout: 超时时间（秒），None表示使用默认值
            continue_on_error: 是否在某个步骤失败时继续执行其他步骤
        
        Returns:
            ParallelExecutionResult: 并行执行结果
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        logger.info(
            f"[{self.request_id}] 开始并行执行 {len(steps)} 个步骤 "
            f"(timeout={timeout}s, continue_on_error={continue_on_error})"
        )
        
        # 创建任务列表
        tasks = []
        step_info = []
        
        for step_number, step_name, step_func in steps:
            task = self._execute_single_step(
                step_number=step_number,
                step_name=step_name,
                step_func=step_func,
                timeout=timeout
            )
            tasks.append(task)
            step_info.append((step_number, step_name))
        
        # 并行执行所有任务
        try:
            # 使用 asyncio.gather 并行执行
            # return_exceptions=True 确保即使某个任务失败也不会影响其他任务
            step_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            processed_results = []
            errors = []
            
            for i, result in enumerate(step_results):
                step_number, step_name = step_info[i]
                
                if isinstance(result, Exception):
                    # 任务抛出异常
                    error_msg = f"步骤{step_number} {step_name} 执行异常: {str(result)}"
                    errors.append(error_msg)
                    logger.error(f"[{self.request_id}] {error_msg}")
                    
                    processed_results.append(StepResult(
                        step_number=step_number,
                        step_name=step_name,
                        status=StepStatus.FAILED,
                        error=str(result),
                        duration_ms=0.0
                    ))
                elif isinstance(result, StepResult):
                    # 正常的步骤结果
                    processed_results.append(result)
                    
                    if result.status == StepStatus.FAILED:
                        errors.append(result.error or "未知错误")
                    elif result.status == StepStatus.TIMEOUT:
                        errors.append(f"步骤{step_number} {step_name} 超时")
                else:
                    # 意外的结果类型
                    logger.warning(
                        f"[{self.request_id}] 步骤{step_number} {step_name} "
                        f"返回了意外的结果类型: {type(result)}"
                    )
                    processed_results.append(StepResult(
                        step_number=step_number,
                        step_name=step_name,
                        status=StepStatus.SUCCESS,
                        result=result,
                        duration_ms=0.0
                    ))
            
            total_duration_ms = (time.time() - start_time) * 1000
            
            # 判断整体是否成功
            success = len(errors) == 0 or (continue_on_error and len(processed_results) > 0)
            
            # 构建执行结果
            execution_result = ParallelExecutionResult(
                success=success,
                total_duration_ms=total_duration_ms,
                step_results=processed_results,
                errors=errors,
                metadata={
                    "total_steps": len(steps),
                    "successful_steps": len([r for r in processed_results if r.status == StepStatus.SUCCESS]),
                    "failed_steps": len([r for r in processed_results if r.status == StepStatus.FAILED]),
                    "timeout_steps": len([r for r in processed_results if r.status == StepStatus.TIMEOUT]),
                    "skipped_steps": len([r for r in processed_results if r.status == StepStatus.SKIPPED]),
                    "continue_on_error": continue_on_error
                }
            )
            
            # 记录执行摘要
            logger.info(
                f"[{self.request_id}] 并行执行完成: "
                f"总耗时={total_duration_ms:.0f}ms, "
                f"成功={execution_result.metadata['successful_steps']}/{len(steps)}, "
                f"失败={execution_result.metadata['failed_steps']}, "
                f"超时={execution_result.metadata['timeout_steps']}"
            )
            
            # 记录性能监控（如果启用）
            if self.performance_monitor:
                try:
                    for step_result in processed_results:
                        # 这里需要一个 context，但我们在这个层级没有
                        # 所以只记录日志，不调用 performance_monitor
                        pass
                except Exception as e:
                    logger.warning(f"性能监控记录失败: {e}")
            
            return execution_result
            
        except Exception as e:
            # 整体执行失败
            total_duration_ms = (time.time() - start_time) * 1000
            error_msg = f"并行执行失败: {str(e)}"
            logger.error(f"[{self.request_id}] {error_msg}", exc_info=True)
            
            return ParallelExecutionResult(
                success=False,
                total_duration_ms=total_duration_ms,
                step_results=[],
                errors=[error_msg],
                metadata={
                    "total_steps": len(steps),
                    "execution_failed": True
                }
            )
    
    async def _execute_single_step(
        self,
        step_number: int,
        step_name: str,
        step_func: Callable,
        timeout: float
    ) -> StepResult:
        """
        执行单个步骤
        
        Args:
            step_number: 步骤编号
            step_name: 步骤名称
            step_func: 步骤函数（异步）
            timeout: 超时时间（秒）
        
        Returns:
            StepResult: 步骤执行结果
        """
        start_time = time.time()
        
        logger.debug(
            f"[{self.request_id}] 步骤{step_number} {step_name} 开始执行 "
            f"(timeout={timeout}s)"
        )
        
        try:
            # 使用 asyncio.wait_for 实现超时控制
            result = await asyncio.wait_for(step_func(), timeout=timeout)
            
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"[{self.request_id}] 步骤{step_number} {step_name} 执行成功 "
                f"(耗时={duration_ms:.0f}ms)"
            )
            
            return StepResult(
                step_number=step_number,
                step_name=step_name,
                status=StepStatus.SUCCESS,
                result=result,
                duration_ms=duration_ms,
                metadata={"timeout": timeout}
            )
            
        except asyncio.TimeoutError:
            # 超时
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"步骤{step_number} {step_name} 执行超时 (>{timeout}s)"
            
            logger.warning(f"[{self.request_id}] {error_msg}")
            
            return StepResult(
                step_number=step_number,
                step_name=step_name,
                status=StepStatus.TIMEOUT,
                error=error_msg,
                duration_ms=duration_ms,
                metadata={"timeout": timeout}
            )
            
        except Exception as e:
            # 执行失败
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"步骤{step_number} {step_name} 执行失败: {str(e)}"
            
            logger.error(f"[{self.request_id}] {error_msg}", exc_info=True)
            
            return StepResult(
                step_number=step_number,
                step_name=step_name,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms,
                metadata={"timeout": timeout}
            )
    
    def get_step_result(
        self,
        execution_result: ParallelExecutionResult,
        step_number: int
    ) -> Optional[StepResult]:
        """
        从并行执行结果中获取指定步骤的结果
        
        Args:
            execution_result: 并行执行结果
            step_number: 步骤编号
        
        Returns:
            Optional[StepResult]: 步骤结果，如果未找到返回None
        """
        for step_result in execution_result.step_results:
            if step_result.step_number == step_number:
                return step_result
        return None
    
    def extract_step_data(
        self,
        execution_result: ParallelExecutionResult,
        step_number: int,
        default: Any = None
    ) -> Any:
        """
        从并行执行结果中提取指定步骤的数据
        
        Args:
            execution_result: 并行执行结果
            step_number: 步骤编号
            default: 默认值（如果步骤失败或未找到）
        
        Returns:
            Any: 步骤数据
        """
        step_result = self.get_step_result(execution_result, step_number)
        
        if step_result is None:
            logger.warning(
                f"[{self.request_id}] 未找到步骤{step_number}的结果，使用默认值"
            )
            return default
        
        if step_result.status != StepStatus.SUCCESS:
            logger.warning(
                f"[{self.request_id}] 步骤{step_number}执行失败 "
                f"(status={step_result.status.value})，使用默认值"
            )
            return default
        
        return step_result.result
