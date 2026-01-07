# -*- coding: utf-8 -*-
"""
并行步骤执行器单元测试

测试并行步骤执行器的功能：
- 并行执行多个步骤
- 错误处理和降级
- 超时控制
- 性能监控

版本：v1.0.0
创建日期：2025-12-21
"""

import pytest
import asyncio
import time
from src.framework.orchestration.parallel_step_executor import (
    ParallelStepExecutor,
    StepStatus,
    StepResult,
    ParallelExecutionResult
)


@pytest.mark.asyncio
async def test_parallel_execution_success():
    """测试并行执行成功的场景"""
    executor = ParallelStepExecutor(
        request_id="test_001",
        default_timeout=5.0
    )
    
    # 定义两个简单的步骤
    async def step1():
        await asyncio.sleep(0.1)
        return "step1_result"
    
    async def step2():
        await asyncio.sleep(0.1)
        return "step2_result"
    
    # 并行执行
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "步骤1", step1),
            (2, "步骤2", step2)
        ],
        timeout=5.0
    )
    
    # 验证结果
    assert result.success is True
    assert len(result.step_results) == 2
    assert result.all_steps_succeeded is True
    assert result.any_step_failed is False
    assert result.total_duration_ms < 500  # 应该在500ms内完成（并行执行）
    
    # 验证步骤1的结果
    step1_result = executor.get_step_result(result, 1)
    assert step1_result is not None
    assert step1_result.status == StepStatus.SUCCESS
    assert step1_result.result == "step1_result"
    
    # 验证步骤2的结果
    step2_result = executor.get_step_result(result, 2)
    assert step2_result is not None
    assert step2_result.status == StepStatus.SUCCESS
    assert step2_result.result == "step2_result"


@pytest.mark.asyncio
async def test_parallel_execution_with_failure():
    """测试并行执行中某个步骤失败的场景"""
    executor = ParallelStepExecutor(
        request_id="test_002",
        default_timeout=5.0
    )
    
    # 定义一个成功的步骤和一个失败的步骤
    async def step1():
        await asyncio.sleep(0.1)
        return "step1_result"
    
    async def step2():
        await asyncio.sleep(0.1)
        raise ValueError("步骤2失败")
    
    # 并行执行（continue_on_error=True）
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "步骤1", step1),
            (2, "步骤2", step2)
        ],
        timeout=5.0,
        continue_on_error=True
    )
    
    # 验证结果
    assert result.success is True  # continue_on_error=True，所以整体成功
    assert len(result.step_results) == 2
    assert result.all_steps_succeeded is False
    assert result.any_step_failed is True
    assert len(result.failed_steps) == 1
    assert len(result.successful_steps) == 1
    
    # 验证步骤1成功
    step1_result = executor.get_step_result(result, 1)
    assert step1_result.status == StepStatus.SUCCESS
    
    # 验证步骤2失败
    step2_result = executor.get_step_result(result, 2)
    assert step2_result.status == StepStatus.FAILED
    assert "步骤2失败" in step2_result.error


@pytest.mark.asyncio
async def test_parallel_execution_with_timeout():
    """测试并行执行中某个步骤超时的场景"""
    executor = ParallelStepExecutor(
        request_id="test_003",
        default_timeout=1.0
    )
    
    # 定义一个快速步骤和一个慢速步骤
    async def step1():
        await asyncio.sleep(0.1)
        return "step1_result"
    
    async def step2():
        await asyncio.sleep(5.0)  # 超过超时时间
        return "step2_result"
    
    # 并行执行
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "步骤1", step1),
            (2, "步骤2", step2)
        ],
        timeout=1.0,
        continue_on_error=True
    )
    
    # 验证结果
    assert result.success is True  # continue_on_error=True
    assert len(result.step_results) == 2
    
    # 验证步骤1成功
    step1_result = executor.get_step_result(result, 1)
    assert step1_result.status == StepStatus.SUCCESS
    
    # 验证步骤2超时
    step2_result = executor.get_step_result(result, 2)
    assert step2_result.status == StepStatus.TIMEOUT
    assert "超时" in step2_result.error


@pytest.mark.asyncio
async def test_extract_step_data():
    """测试提取步骤数据的功能"""
    executor = ParallelStepExecutor(
        request_id="test_004",
        default_timeout=5.0
    )
    
    # 定义步骤
    async def step1():
        return {"key": "value"}
    
    async def step2():
        raise ValueError("失败")
    
    # 并行执行
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "步骤1", step1),
            (2, "步骤2", step2)
        ],
        timeout=5.0,
        continue_on_error=True
    )
    
    # 提取步骤1的数据（成功）
    step1_data = executor.extract_step_data(result, 1, default="default_value")
    assert step1_data == {"key": "value"}
    
    # 提取步骤2的数据（失败，应返回默认值）
    step2_data = executor.extract_step_data(result, 2, default="default_value")
    assert step2_data == "default_value"
    
    # 提取不存在的步骤（应返回默认值）
    step3_data = executor.extract_step_data(result, 3, default="default_value")
    assert step3_data == "default_value"


@pytest.mark.asyncio
async def test_parallel_execution_performance():
    """测试并行执行的性能优势"""
    executor = ParallelStepExecutor(
        request_id="test_005",
        default_timeout=10.0
    )
    
    # 定义3个各需要0.5秒的步骤
    async def step1():
        await asyncio.sleep(0.5)
        return "step1"
    
    async def step2():
        await asyncio.sleep(0.5)
        return "step2"
    
    async def step3():
        await asyncio.sleep(0.5)
        return "step3"
    
    # 并行执行
    start_time = time.time()
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "步骤1", step1),
            (2, "步骤2", step2),
            (3, "步骤3", step3)
        ],
        timeout=10.0
    )
    total_time = time.time() - start_time
    
    # 验证结果
    assert result.success is True
    assert result.all_steps_succeeded is True
    
    # 验证并行执行的性能优势
    # 如果串行执行需要1.5秒，并行执行应该在0.6秒左右完成
    assert total_time < 1.0  # 应该远小于串行执行的1.5秒
    assert result.total_duration_ms < 1000


@pytest.mark.asyncio
async def test_continue_on_error_false():
    """测试 continue_on_error=False 的场景"""
    executor = ParallelStepExecutor(
        request_id="test_006",
        default_timeout=5.0
    )
    
    # 定义步骤
    async def step1():
        return "step1_result"
    
    async def step2():
        raise ValueError("步骤2失败")
    
    # 并行执行（continue_on_error=False）
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "步骤1", step1),
            (2, "步骤2", step2)
        ],
        timeout=5.0,
        continue_on_error=False
    )
    
    # 验证结果
    # 即使 continue_on_error=False，由于使用了 asyncio.gather(return_exceptions=True)
    # 所有任务都会完成，但整体结果会标记为失败
    assert result.success is False  # 有错误且 continue_on_error=False
    assert result.any_step_failed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
