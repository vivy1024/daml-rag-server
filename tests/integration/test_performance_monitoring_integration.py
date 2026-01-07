# -*- coding: utf-8 -*-
"""
性能监控集成测试

测试工作流执行器中的性能监控集成：
1. start_workflow() 和 finish_workflow()
2. record_step() 记录每个步骤
3. measure() 上下文管理器记录关键操作

版本：v1.0.0
创建日期：2025-12-21
"""

import pytest
import asyncio
from src.framework.monitoring.performance_monitor import get_performance_monitor


@pytest.mark.asyncio
async def test_performance_monitor_workflow_integration():
    """测试性能监控器的工作流集成"""
    
    # 获取性能监控器实例
    performance_monitor = get_performance_monitor()
    
    # 1. 测试 start_workflow()
    request_id = "test_request_123"
    user_id = "test_user_456"
    
    context = performance_monitor.start_workflow(
        request_id=request_id,
        user_id=user_id
    )
    
    assert context is not None
    assert context.request_id == request_id
    assert context.user_id == user_id
    
    # 2. 测试 record_step()
    performance_monitor.record_step(
        context=context,
        step_number=1,
        step_name="测试步骤1",
        duration_ms=100.0,
        success=True,
        metadata={"test": "data"}
    )
    
    performance_monitor.record_step(
        context=context,
        step_number=2,
        step_name="测试步骤2",
        duration_ms=200.0,
        success=True,
        metadata={"test": "data2"}
    )
    
    # 3. 测试 measure() 上下文管理器
    with performance_monitor.measure("test_operation"):
        await asyncio.sleep(0.1)  # 模拟耗时操作
    
    # 验证操作统计
    stats = performance_monitor.get_operation_stats("test_operation")
    assert stats["count"] == 1
    assert stats["avg"] >= 0.1  # 至少100ms
    
    # 4. 测试 finish_workflow()
    performance_monitor.finish_workflow(
        context=context,
        success=True,
        total_duration_ms=500.0
    )
    
    # 5. 验证工作流摘要
    summary = performance_monitor.get_workflow_summary(request_id)
    assert summary is not None
    assert summary["request_id"] == request_id
    assert summary["total_steps"] == 2
    assert summary["success"] is True
    
    print("✅ 性能监控集成测试通过")


@pytest.mark.asyncio
async def test_measure_context_manager_multiple_operations():
    """测试 measure() 上下文管理器记录多个操作"""
    
    performance_monitor = get_performance_monitor()
    
    # 记录多个操作
    operations = ["cache_get", "db_query", "llm_call"]
    
    for operation in operations:
        with performance_monitor.measure(operation):
            await asyncio.sleep(0.05)  # 模拟50ms操作
    
    # 验证所有操作都被记录
    for operation in operations:
        stats = performance_monitor.get_operation_stats(operation)
        assert stats["count"] >= 1
        assert stats["avg"] >= 0.05
    
    print("✅ measure()上下文管理器多操作测试通过")


@pytest.mark.asyncio
async def test_measure_context_manager_with_exception():
    """测试 measure() 上下文管理器在异常情况下的行为"""
    
    performance_monitor = get_performance_monitor()
    
    # 测试异常情况
    try:
        with performance_monitor.measure("failing_operation"):
            await asyncio.sleep(0.05)
            raise ValueError("测试异常")
    except ValueError:
        pass  # 预期的异常
    
    # 验证即使发生异常，操作也被记录
    stats = performance_monitor.get_operation_stats("failing_operation")
    assert stats["count"] == 1
    assert stats["avg"] >= 0.05
    
    print("✅ measure()上下文管理器异常处理测试通过")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_performance_monitor_workflow_integration())
    asyncio.run(test_measure_context_manager_multiple_operations())
    asyncio.run(test_measure_context_manager_with_exception())
    print("\n🎉 所有性能监控集成测试通过！")
