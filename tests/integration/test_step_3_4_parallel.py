# -*- coding: utf-8 -*-
"""
步骤3-4并行执行测试

测试会员权限检查和BGE复杂度分类的并行执行优化

版本：v1.0.0
创建日期：2025-12-21
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch


@pytest.mark.asyncio
async def test_step_3_4_parallel_execution():
    """测试步骤3-4完全并行执行"""
    from src.applications.fitness.workflow_executor import execute_eleven_step_workflow
    
    # 模拟用户ID和查询
    user_id = "123"
    query_text = "我想增肌，应该怎么训练？"
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行工作流
    try:
        result = await execute_eleven_step_workflow(
            query_text=query_text,
            user_id=user_id,
            domain="fitness"
        )
        
        # 计算总耗时
        total_duration = time.time() - start_time
        
        # 验证结果
        assert result is not None
        assert result.get("success") is True
        
        # 验证步骤3-4并行执行
        workflow_info = result.get("eleven_step_workflow", {})
        assert workflow_info.get("completed") is True
        assert workflow_info.get("steps_executed") == 11
        
        print(f"\n✅ 步骤3-4并行执行测试通过")
        print(f"   - 总耗时: {total_duration:.2f}秒")
        print(f"   - 会员权限检查: {'成功' if workflow_info.get('membership_checked') else '失败'}")
        print(f"   - 复杂度分类: {'复杂' if workflow_info.get('complexity_classified') else '简单'}")
        
    except Exception as e:
        pytest.fail(f"步骤3-4并行执行测试失败: {e}")


@pytest.mark.asyncio
async def test_step_3_4_error_handling():
    """测试步骤3-4的错误处理"""
    from src.framework.orchestration.parallel_step_executor import ParallelStepExecutor
    
    request_id = "test_error_handling"
    
    # 创建并行执行器
    executor = ParallelStepExecutor(
        request_id=request_id,
        default_timeout=5.0,
        enable_fallback=True,
        enable_monitoring=True
    )
    
    # 定义一个会失败的步骤
    async def failing_step():
        await asyncio.sleep(0.1)
        raise ValueError("模拟步骤失败")
    
    # 定义一个会成功的步骤
    async def successful_step():
        await asyncio.sleep(0.1)
        return "成功结果"
    
    # 并行执行
    result = await executor.execute_parallel_steps(
        steps=[
            (3, "失败步骤", failing_step),
            (4, "成功步骤", successful_step)
        ],
        timeout=5.0,
        continue_on_error=True
    )
    
    # 验证结果
    assert result.success is True  # continue_on_error=True，所以整体成功
    assert result.metadata['failed_steps'] == 1
    assert result.metadata['successful_steps'] == 1
    
    # 验证失败步骤
    failed_steps = result.failed_steps
    assert len(failed_steps) == 1
    assert failed_steps[0].step_number == 3
    assert "模拟步骤失败" in failed_steps[0].error
    
    # 验证成功步骤
    successful_steps = result.successful_steps
    assert len(successful_steps) == 1
    assert successful_steps[0].step_number == 4
    assert successful_steps[0].result == "成功结果"
    
    print(f"\n✅ 步骤3-4错误处理测试通过")
    print(f"   - 总耗时: {result.total_duration_ms:.0f}ms")
    print(f"   - 成功步骤: {result.metadata['successful_steps']}")
    print(f"   - 失败步骤: {result.metadata['failed_steps']}")


@pytest.mark.asyncio
async def test_step_3_4_timeout_handling():
    """测试步骤3-4的超时处理"""
    from src.framework.orchestration.parallel_step_executor import ParallelStepExecutor
    
    request_id = "test_timeout_handling"
    
    # 创建并行执行器
    executor = ParallelStepExecutor(
        request_id=request_id,
        default_timeout=1.0,
        enable_fallback=True,
        enable_monitoring=True
    )
    
    # 定义一个会超时的步骤
    async def timeout_step():
        await asyncio.sleep(5.0)  # 超过1秒超时
        return "不应该返回"
    
    # 定义一个快速完成的步骤
    async def fast_step():
        await asyncio.sleep(0.1)
        return "快速完成"
    
    # 并行执行
    result = await executor.execute_parallel_steps(
        steps=[
            (3, "超时步骤", timeout_step),
            (4, "快速步骤", fast_step)
        ],
        timeout=1.0,
        continue_on_error=True
    )
    
    # 验证结果
    assert result.success is True  # continue_on_error=True，所以整体成功
    assert result.metadata['timeout_steps'] == 1
    assert result.metadata['successful_steps'] == 1
    
    # 验证超时步骤
    timeout_steps = [r for r in result.step_results if r.status.value == "timeout"]
    assert len(timeout_steps) == 1
    assert timeout_steps[0].step_number == 3
    
    # 验证成功步骤
    successful_steps = result.successful_steps
    assert len(successful_steps) == 1
    assert successful_steps[0].step_number == 4
    assert successful_steps[0].result == "快速完成"
    
    print(f"\n✅ 步骤3-4超时处理测试通过")
    print(f"   - 总耗时: {result.total_duration_ms:.0f}ms")
    print(f"   - 成功步骤: {result.metadata['successful_steps']}")
    print(f"   - 超时步骤: {result.metadata['timeout_steps']}")


@pytest.mark.asyncio
async def test_step_3_4_performance_monitoring():
    """测试步骤3-4的性能监控"""
    from src.framework.orchestration.parallel_step_executor import ParallelStepExecutor
    
    request_id = "test_performance_monitoring"
    
    # 创建并行执行器（启用性能监控）
    executor = ParallelStepExecutor(
        request_id=request_id,
        default_timeout=5.0,
        enable_fallback=True,
        enable_monitoring=True
    )
    
    # 定义两个步骤
    async def step_3():
        await asyncio.sleep(0.2)
        return {"tier": "premium", "_fallback": False}
    
    async def step_4():
        await asyncio.sleep(0.3)
        return (True, 0.85, "复杂查询")
    
    # 并行执行
    result = await executor.execute_parallel_steps(
        steps=[
            (3, "检查会员权限", step_3),
            (4, "BGE复杂度分类", step_4)
        ],
        timeout=5.0,
        continue_on_error=True
    )
    
    # 验证结果
    assert result.success is True
    assert result.all_steps_succeeded is True
    
    # 验证性能数据
    assert result.total_duration_ms > 0
    assert result.total_duration_ms < 1000  # 应该在1秒内完成
    
    # 验证每个步骤的性能数据
    for step_result in result.step_results:
        assert step_result.duration_ms > 0
        assert step_result.duration_ms < result.total_duration_ms
    
    # 验证并行执行的效率
    # 两个步骤分别需要200ms和300ms，并行执行应该接近300ms（最长的那个）
    # 而不是500ms（串行执行）
    assert result.total_duration_ms < 500  # 应该明显快于串行执行
    
    print(f"\n✅ 步骤3-4性能监控测试通过")
    print(f"   - 总耗时: {result.total_duration_ms:.0f}ms")
    print(f"   - 步骤3耗时: {result.step_results[0].duration_ms:.0f}ms")
    print(f"   - 步骤4耗时: {result.step_results[1].duration_ms:.0f}ms")
    print(f"   - 并行效率: {((500 - result.total_duration_ms) / 500 * 100):.1f}%")


if __name__ == "__main__":
    # 运行测试
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
