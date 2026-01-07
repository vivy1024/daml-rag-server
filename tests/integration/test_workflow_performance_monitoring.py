# -*- coding: utf-8 -*-
"""
工作流性能监控集成测试

测试性能监控器与工作流执行器的集成，验证：
1. 完整工作流的性能记录
2. 性能瓶颈的检测和告警
3. 性能摘要的生成

版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from src.framework.monitoring.performance_monitor import PerformanceMonitor, get_performance_monitor
from src.applications.fitness.workflow_executor import execute_eleven_step_workflow


class TestWorkflowPerformanceMonitoring:
    """工作流性能监控集成测试"""
    
    @pytest.fixture
    def performance_monitor(self):
        """创建性能监控器实例"""
        monitor = PerformanceMonitor(
            max_history_size=100,
            bottleneck_threshold_ms=1000.0
        )
        return monitor
    
    @pytest.fixture
    def mock_backend_client(self):
        """模拟后端客户端"""
        client = Mock()
        client.get_user_profile = AsyncMock(return_value={
            "id": 1,
            "age": 25,
            "training_experience": "intermediate",
            "fitness_goal": "muscle_gain"
        })
        client.get_user_membership = AsyncMock(return_value={
            "tier": "premium",
            "expires_at": "2025-12-31"
        })
        client.save_chat_session = AsyncMock(return_value={"id": 123})
        return client
    
    @pytest.mark.asyncio
    async def test_complete_workflow_performance_recording(self, performance_monitor):
        """测试完整工作流的性能记录"""
        # 启动工作流监控
        request_id = "test_request_001"
        context = performance_monitor.start_workflow(
            request_id=request_id,
            user_id="test_user"
        )
        
        # 模拟步骤执行
        steps = [
            (1, "预加载用户档案", 50, True),
            (2, "会话记录存储", 30, True),
            (3, "检查会员权限", 100, True),
            (4, "BGE复杂度分类", 200, True),
            (5, "智能模型选择", 10, True),
            (6, "Few-Shot检索", 150, True),
            (7, "LLM选择DAG模板", 300, True),
            (8, "DAG编排执行", 500, True),
            (9, "工具结果汇总", 80, True),
            (10, "LLM生成回答", 1200, True),  # 超过阈值
            (11, "记录交互", 60, True)
        ]
        
        for step_num, step_name, duration_ms, success in steps:
            performance_monitor.record_step(
                context=context,
                step_number=step_num,
                step_name=step_name,
                duration_ms=duration_ms,
                success=success
            )
        
        # 完成工作流
        total_duration_ms = sum(s[2] for s in steps)
        performance_monitor.finish_workflow(
            context=context,
            success=True,
            total_duration_ms=total_duration_ms
        )
        
        # 验证性能记录
        assert len(context.steps) == 11
        assert context.steps[0].step_name == "预加载用户档案"
        assert context.steps[0].duration_ms == 50
        assert context.steps[10].step_name == "记录交互"
        assert context.steps[10].duration_ms == 60
        
        # 验证所有步骤都成功
        assert all(step.success for step in context.steps)
        
        print(f"✅ 测试通过: 完整工作流性能记录")
        print(f"   - 记录步骤数: {len(context.steps)}")
        print(f"   - 总耗时: {total_duration_ms}ms")
    
    @pytest.mark.asyncio
    async def test_performance_bottleneck_detection(self, performance_monitor):
        """测试性能瓶颈的检测和告警"""
        # 启动工作流监控
        request_id = "test_request_002"
        context = performance_monitor.start_workflow(
            request_id=request_id,
            user_id="test_user"
        )
        
        # 模拟步骤执行，包含性能瓶颈
        steps = [
            (1, "预加载用户档案", 50, True),
            (2, "会话记录存储", 30, True),
            (3, "检查会员权限", 1500, True),  # 瓶颈1
            (4, "BGE复杂度分类", 200, True),
            (5, "智能模型选择", 10, True),
            (6, "Few-Shot检索", 150, True),
            (7, "LLM选择DAG模板", 300, True),
            (8, "DAG编排执行", 2000, True),  # 瓶颈2
            (9, "工具结果汇总", 80, True),
            (10, "LLM生成回答", 1200, True),  # 瓶颈3
            (11, "记录交互", 60, True)
        ]
        
        for step_num, step_name, duration_ms, success in steps:
            performance_monitor.record_step(
                context=context,
                step_number=step_num,
                step_name=step_name,
                duration_ms=duration_ms,
                success=success
            )
        
        # 完成工作流
        total_duration_ms = sum(s[2] for s in steps)
        performance_monitor.finish_workflow(
            context=context,
            success=True,
            total_duration_ms=total_duration_ms
        )
        
        # 获取性能瓶颈
        bottlenecks = performance_monitor.get_bottlenecks(threshold_ms=1000)
        
        # 验证瓶颈检测
        assert len(bottlenecks) == 3
        assert bottlenecks[0].step_name == "DAG编排执行"  # 最慢的
        assert bottlenecks[0].duration_ms == 2000
        assert bottlenecks[1].step_name == "检查会员权限"
        assert bottlenecks[1].duration_ms == 1500
        assert bottlenecks[2].step_name == "LLM生成回答"
        assert bottlenecks[2].duration_ms == 1200
        
        print(f"✅ 测试通过: 性能瓶颈检测")
        print(f"   - 检测到瓶颈数: {len(bottlenecks)}")
        for i, bottleneck in enumerate(bottlenecks, 1):
            print(f"   - 瓶颈{i}: {bottleneck.step_name} ({bottleneck.duration_ms}ms)")
    
    @pytest.mark.asyncio
    async def test_performance_summary_generation(self, performance_monitor):
        """测试性能摘要的生成"""
        # 启动工作流监控
        request_id = "test_request_003"
        context = performance_monitor.start_workflow(
            request_id=request_id,
            user_id="test_user"
        )
        
        # 模拟步骤执行
        steps = [
            (1, "预加载用户档案", 50, True),
            (2, "会话记录存储", 30, True),
            (3, "检查会员权限", 100, True),
            (4, "BGE复杂度分类", 200, True),
            (5, "智能模型选择", 10, True),
            (6, "Few-Shot检索", 150, True),
            (7, "LLM选择DAG模板", 300, True),
            (8, "DAG编排执行", 500, True),
            (9, "工具结果汇总", 80, True),
            (10, "LLM生成回答", 1200, True),
            (11, "记录交互", 60, True)
        ]
        
        for step_num, step_name, duration_ms, success in steps:
            performance_monitor.record_step(
                context=context,
                step_number=step_num,
                step_name=step_name,
                duration_ms=duration_ms,
                success=success
            )
        
        # 完成工作流
        total_duration_ms = sum(s[2] for s in steps)
        performance_monitor.finish_workflow(
            context=context,
            success=True,
            total_duration_ms=total_duration_ms
        )
        
        # 获取性能摘要
        summary = performance_monitor.get_workflow_summary(request_id)
        
        # 验证摘要内容
        assert summary is not None
        assert summary["request_id"] == request_id
        assert summary["user_id"] == "test_user"
        assert summary["total_duration_ms"] == total_duration_ms
        assert summary["total_steps"] == 11
        assert summary["success"] is True
        assert summary["bottleneck_count"] == 1  # 只有步骤10超过1000ms
        
        # 验证步骤详情
        assert len(summary["steps"]) == 11
        assert summary["steps"][0]["step_name"] == "预加载用户档案"
        assert summary["steps"][0]["duration_ms"] == 50
        assert summary["steps"][9]["step_name"] == "LLM生成回答"
        assert summary["steps"][9]["is_bottleneck"] is True
        
        # 验证瓶颈列表
        assert len(summary["bottlenecks"]) == 1
        assert summary["bottlenecks"][0]["step_name"] == "LLM生成回答"
        assert summary["bottlenecks"][0]["duration_ms"] == 1200
        
        print(f"✅ 测试通过: 性能摘要生成")
        print(f"   - 请求ID: {summary['request_id']}")
        print(f"   - 总耗时: {summary['total_duration_ms']}ms")
        print(f"   - 总步骤: {summary['total_steps']}")
        print(f"   - 性能瓶颈: {summary['bottleneck_count']}个")
    
    @pytest.mark.asyncio
    async def test_failed_workflow_performance_recording(self, performance_monitor):
        """测试失败工作流的性能记录"""
        # 启动工作流监控
        request_id = "test_request_004"
        context = performance_monitor.start_workflow(
            request_id=request_id,
            user_id="test_user"
        )
        
        # 模拟步骤执行，包含失败步骤
        steps = [
            (1, "预加载用户档案", 50, True),
            (2, "会话记录存储", 30, True),
            (3, "检查会员权限", 100, True),
            (4, "BGE复杂度分类", 200, True),
            (5, "智能模型选择", 10, True),
            (6, "Few-Shot检索", 150, True),
            (7, "LLM选择DAG模板", 300, True),
            (8, "DAG编排执行", 500, False),  # 失败
        ]
        
        for step_num, step_name, duration_ms, success in steps:
            performance_monitor.record_step(
                context=context,
                step_number=step_num,
                step_name=step_name,
                duration_ms=duration_ms,
                success=success,
                error="DAG执行失败" if not success else None
            )
        
        # 完成工作流（失败）
        total_duration_ms = sum(s[2] for s in steps)
        performance_monitor.finish_workflow(
            context=context,
            success=False,
            total_duration_ms=total_duration_ms
        )
        
        # 获取性能摘要
        summary = performance_monitor.get_workflow_summary(request_id)
        
        # 验证失败记录
        assert summary is not None
        assert summary["success"] is False
        assert len(summary["steps"]) == 8
        assert summary["steps"][7]["success"] is False
        assert summary["steps"][7]["error"] == "DAG执行失败"
        
        print(f"✅ 测试通过: 失败工作流性能记录")
        print(f"   - 执行步骤数: {len(summary['steps'])}")
        print(f"   - 失败步骤: {summary['steps'][7]['step_name']}")
        print(f"   - 错误信息: {summary['steps'][7]['error']}")
    
    @pytest.mark.asyncio
    async def test_prometheus_metrics_export(self, performance_monitor):
        """测试Prometheus指标导出"""
        # 执行多个工作流
        for i in range(3):
            request_id = f"test_request_00{i+5}"
            context = performance_monitor.start_workflow(
                request_id=request_id,
                user_id="test_user"
            )
            
            # 模拟步骤执行
            steps = [
                (1, "预加载用户档案", 50, True),
                (2, "会话记录存储", 30, True),
                (10, "LLM生成回答", 1000 + i * 100, True),
            ]
            
            for step_num, step_name, duration_ms, success in steps:
                performance_monitor.record_step(
                    context=context,
                    step_number=step_num,
                    step_name=step_name,
                    duration_ms=duration_ms,
                    success=success
                )
            
            total_duration_ms = sum(s[2] for s in steps)
            performance_monitor.finish_workflow(
                context=context,
                success=True,
                total_duration_ms=total_duration_ms
            )
        
        # 导出Prometheus指标
        metrics = performance_monitor.export_metrics(format="prometheus")
        
        # 验证指标格式
        assert "workflow_total_duration_seconds" in metrics
        assert "workflow_success_total" in metrics
        assert "workflow_failure_total" in metrics
        assert "workflow_concurrent_requests" in metrics
        
        # 验证指标值
        assert "workflow_success_total 3" in metrics
        
        print(f"✅ 测试通过: Prometheus指标导出")
        print(f"   - 指标长度: {len(metrics)}字节")
        print(f"   - 包含指标: workflow_total_duration_seconds, workflow_success_total")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
