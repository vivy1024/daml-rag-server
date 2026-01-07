# -*- coding: utf-8 -*-
"""
工作流步骤1-2并行执行集成测试

测试工作流中步骤1-2的并行执行优化：
- 确保用户档案加载和会话初始化完全并行
- 验证错误处理机制
- 验证性能监控
- 验证超时控制

版本：v1.0.0
创建日期：2025-12-21
"""

import pytest
import asyncio
import time
from src.framework.orchestration.parallel_step_executor import ParallelStepExecutor


@pytest.mark.asyncio
async def test_workflow_step_1_2_parallel_simulation():
    """模拟工作流步骤1-2的并行执行"""
    
    request_id = "test_workflow_001"
    executor = ParallelStepExecutor(
        request_id=request_id,
        default_timeout=10.0,
        enable_fallback=True,
        enable_monitoring=True
    )
    
    # 模拟步骤1：用户档案加载（耗时200ms）
    user_profile = None
    
    async def load_user_profile():
        nonlocal user_profile
        await asyncio.sleep(0.2)  # 模拟数据库查询
        user_profile = {
            "id": 123,
            "name": "测试用户",
            "age": 25,
            "fitness_goal": "增肌"
        }
        return user_profile
    
    # 模拟步骤2：会话初始化（耗时50ms）
    session_id = None
    
    async def create_session():
        nonlocal session_id
        await asyncio.sleep(0.05)  # 模拟会话创建
        session_id = f"session_123_{int(time.time())}"
        return session_id
    
    # 并行执行
    start_time = time.time()
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "预加载用户档案", load_user_profile),
            (2, "会话记录存储", create_session)
        ],
        timeout=10.0,
        continue_on_error=True
    )
    total_time = time.time() - start_time
    
    # 验证结果
    assert result.success is True
    assert result.all_steps_succeeded is True
    assert len(result.step_results) == 2
    
    # 提取数据
    extracted_profile = executor.extract_step_data(result, 1)
    extracted_session = executor.extract_step_data(result, 2)
    
    assert extracted_profile is not None
    assert extracted_profile["id"] == 123
    assert extracted_session is not None
    assert extracted_session.startswith("session_123_")
    
    # 验证并行执行的性能优势
    # 如果串行执行需要250ms，并行执行应该在220ms左右完成
    assert total_time < 0.3  # 应该远小于串行执行的0.25秒
    assert result.total_duration_ms < 300
    
    print(f"✅ 并行执行成功: 总耗时={total_time*1000:.0f}ms")
    print(f"   - 步骤1: {result.step_results[0].duration_ms:.0f}ms")
    print(f"   - 步骤2: {result.step_results[1].duration_ms:.0f}ms")
    print(f"   - 性能提升: {((0.25 - total_time) / 0.25 * 100):.1f}%")


@pytest.mark.asyncio
async def test_workflow_step_1_failure_with_fallback():
    """测试步骤1失败但工作流继续执行的场景"""
    
    request_id = "test_workflow_002"
    executor = ParallelStepExecutor(
        request_id=request_id,
        default_timeout=10.0,
        enable_fallback=True,
        enable_monitoring=True
    )
    
    # 模拟步骤1：用户档案加载失败
    async def load_user_profile_fail():
        await asyncio.sleep(0.1)
        raise Exception("数据库连接失败")
    
    # 模拟步骤2：会话初始化成功
    async def create_session():
        await asyncio.sleep(0.05)
        return f"session_anonymous_{int(time.time())}"
    
    # 并行执行
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "预加载用户档案", load_user_profile_fail),
            (2, "会话记录存储", create_session)
        ],
        timeout=10.0,
        continue_on_error=True  # 关键：即使步骤1失败也继续
    )
    
    # 验证结果
    assert result.success is True  # continue_on_error=True，所以整体成功
    assert len(result.step_results) == 2
    assert result.any_step_failed is True
    assert len(result.failed_steps) == 1
    assert len(result.successful_steps) == 1
    
    # 验证步骤1失败
    step1_result = executor.get_step_result(result, 1)
    assert step1_result.status.value == "failed"
    assert "数据库连接失败" in step1_result.error
    
    # 验证步骤2成功
    step2_result = executor.get_step_result(result, 2)
    assert step2_result.status.value == "success"
    
    # 提取数据（步骤1使用默认值）
    user_profile = executor.extract_step_data(result, 1, default=None)
    session_id = executor.extract_step_data(result, 2)
    
    assert user_profile is None  # 使用默认值
    assert session_id is not None
    assert session_id.startswith("session_anonymous_")
    
    print(f"✅ 降级策略生效: 步骤1失败但工作流继续")
    print(f"   - 步骤1: 失败 ({step1_result.error})")
    print(f"   - 步骤2: 成功 ({session_id[:30]}...)")


@pytest.mark.asyncio
async def test_workflow_step_1_timeout():
    """测试步骤1超时的场景"""
    
    request_id = "test_workflow_003"
    executor = ParallelStepExecutor(
        request_id=request_id,
        default_timeout=1.0,  # 1秒超时
        enable_fallback=True,
        enable_monitoring=True
    )
    
    # 模拟步骤1：用户档案加载超时
    async def load_user_profile_slow():
        await asyncio.sleep(5.0)  # 超过超时时间
        return {"id": 123}
    
    # 模拟步骤2：会话初始化快速完成
    async def create_session():
        await asyncio.sleep(0.05)
        return f"session_123_{int(time.time())}"
    
    # 并行执行
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "预加载用户档案", load_user_profile_slow),
            (2, "会话记录存储", create_session)
        ],
        timeout=1.0,
        continue_on_error=True
    )
    
    # 验证结果
    assert result.success is True  # continue_on_error=True
    assert len(result.step_results) == 2
    
    # 验证步骤1超时
    step1_result = executor.get_step_result(result, 1)
    assert step1_result.status.value == "timeout"
    assert "超时" in step1_result.error
    
    # 验证步骤2成功
    step2_result = executor.get_step_result(result, 2)
    assert step2_result.status.value == "success"
    
    # 验证总时间接近超时时间（约1秒）
    assert result.total_duration_ms < 1500  # 应该在1.5秒内完成
    
    print(f"✅ 超时控制生效: 步骤1超时但步骤2成功")
    print(f"   - 总耗时: {result.total_duration_ms:.0f}ms")
    print(f"   - 步骤1: 超时 (>{step1_result.metadata['timeout']}s)")
    print(f"   - 步骤2: 成功 ({step2_result.duration_ms:.0f}ms)")


@pytest.mark.asyncio
async def test_workflow_performance_comparison():
    """对比串行执行和并行执行的性能差异"""
    
    # 定义两个步骤
    async def step1():
        await asyncio.sleep(0.2)
        return "step1_result"
    
    async def step2():
        await asyncio.sleep(0.2)
        return "step2_result"
    
    # 串行执行
    serial_start = time.time()
    result1 = await step1()
    result2 = await step2()
    serial_time = time.time() - serial_start
    
    # 并行执行
    executor = ParallelStepExecutor(
        request_id="test_perf",
        default_timeout=10.0
    )
    
    parallel_start = time.time()
    result = await executor.execute_parallel_steps(
        steps=[
            (1, "步骤1", step1),
            (2, "步骤2", step2)
        ],
        timeout=10.0
    )
    parallel_time = time.time() - parallel_start
    
    # 验证并行执行的性能优势
    assert parallel_time < serial_time
    improvement = ((serial_time - parallel_time) / serial_time) * 100
    
    print(f"✅ 性能对比:")
    print(f"   - 串行执行: {serial_time*1000:.0f}ms")
    print(f"   - 并行执行: {parallel_time*1000:.0f}ms")
    print(f"   - 性能提升: {improvement:.1f}%")
    
    assert improvement > 40  # 至少提升40%


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

