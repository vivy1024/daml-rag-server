#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成测试指标 - 让Grafana仪表盘有数据显示

功能：
1. 模拟工作流请求，生成11步监控指标
2. 模拟流式输出，生成streaming指标
3. 确保所有Prometheus指标都有初始值

使用方法：
    docker exec fitness_daml_rag python scripts/generate_test_metrics.py

版本: v1.0.0
创建日期: 2025-12-24
作者: 薛小川
"""

import sys
import os
import time
import random
import asyncio
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/app')

from src.framework.monitoring.streaming_metrics import (
    streaming_ttfb,
    streaming_duration,
    streaming_tokens_per_second,
    streaming_success,
    streaming_failure
)


def generate_streaming_metrics(count: int = 10):
    """
    生成流式输出测试指标
    
    Args:
        count: 生成的测试会话数量
    """
    print(f"\n🎯 开始生成{count}个流式输出测试指标...")
    
    for i in range(count):
        # 模拟TTFB（首字节响应时间）：1-5秒
        ttfb = random.uniform(1.0, 5.0)
        streaming_ttfb.observe(ttfb)
        
        # 模拟总耗时：10-30秒
        duration = random.uniform(10.0, 30.0)
        streaming_duration.observe(duration)
        
        # 模拟生成速度：10-50 tokens/s
        tokens_per_sec = random.uniform(10.0, 50.0)
        streaming_tokens_per_second.observe(tokens_per_sec)
        
        # 模拟成功/失败（90%成功率）
        if random.random() < 0.9:
            streaming_success.inc()
            status = "✅ 成功"
        else:
            streaming_failure.inc()
            status = "❌ 失败"
        
        print(f"  会话{i+1}: TTFB={ttfb:.2f}s, 耗时={duration:.2f}s, 速度={tokens_per_sec:.1f}t/s, {status}")
        
        # 短暂延迟，模拟真实请求间隔
        time.sleep(0.1)
    
    print(f"✅ 流式输出指标生成完成！")


def generate_workflow_metrics(count: int = 5):
    """
    生成工作流测试指标
    
    Args:
        count: 生成的测试工作流数量
    """
    print(f"\n🎯 开始生成{count}个工作流测试指标...")
    
    try:
        from src.framework.monitoring.daml_workflow_monitor import (
            DAMLWorkflowMonitor,
            WorkflowStep,
            RetrievalLayer
        )
        
        monitor = DAMLWorkflowMonitor()
        
        for i in range(count):
            # 开始会话
            session_id = monitor.start_session(
                user_id=f"test_user_{i}",
                query=f"测试查询{i}：给我一个增肌训练计划",
                metadata={"test": True}
            )
            
            print(f"\n  工作流{i+1} (session_id={session_id[:8]}...):")
            
            # 模拟11步工作流程
            steps = [
                (WorkflowStep.USER_PROFILE_LOADING, 50, 100),
                (WorkflowStep.SESSION_STORAGE, 30, 50),
                (WorkflowStep.MEMBERSHIP_CHECK, 20, 30),
                (WorkflowStep.BGE_COMPLEXITY_CLASSIFICATION, 100, 200),
                (WorkflowStep.MODEL_SELECTION, 50, 100),
                (WorkflowStep.FEW_SHOT_RETRIEVAL, 200, 500),
                (WorkflowStep.DAG_ORCHESTRATION, 500, 1000),
                (WorkflowStep.THREE_LAYER_RETRIEVAL, 1000, 2000),
                (WorkflowStep.TOOL_RESULT_AGGREGATION, 100, 200),
                (WorkflowStep.LLM_GENERATION, 5000, 10000),
                (WorkflowStep.INTERACTION_RECORDING, 50, 100)
            ]
            
            for step, min_ms, max_ms in steps:
                # 开始步骤
                monitor.start_step(session_id, step)
                
                # 模拟步骤执行时间
                duration_ms = random.uniform(min_ms, max_ms)
                time.sleep(duration_ms / 1000)
                
                # 完成步骤（95%成功率）
                success = random.random() < 0.95
                monitor.finish_step(
                    session_id,
                    step,
                    success=success,
                    input_size=random.randint(100, 1000),
                    output_size=random.randint(500, 5000),
                    cache_hit=random.random() < 0.3
                )
                
                status = "✅" if success else "❌"
                print(f"    步骤{step.value}: {duration_ms:.0f}ms {status}")
            
            # 模拟三层检索
            layers = [
                (RetrievalLayer.LAYER1_VECTOR, 100, 50),
                (RetrievalLayer.LAYER2_GRAPH, 50, 20),
                (RetrievalLayer.LAYER3_RULES, 20, 10)
            ]
            
            for layer, candidates_in, candidates_out in layers:
                monitor.start_retrieval_layer(session_id, layer)
                time.sleep(random.uniform(0.1, 0.5))
                monitor.finish_retrieval_layer(
                    session_id,
                    layer,
                    success=True,
                    candidates_in=candidates_in,
                    candidates_out=candidates_out,
                    confidence_score=random.uniform(0.7, 0.95)
                )
            
            # 完成会话
            monitor.finish_session(
                session_id,
                success=True,
                cost_estimate=random.uniform(0.001, 0.01),
                model_used="qwen3:8b",
                quality_score=random.uniform(0.8, 0.95)
            )
            
            print(f"  ✅ 工作流{i+1}完成")
        
        # 打印性能摘要
        print(f"\n📊 性能摘要:")
        summary = monitor.get_performance_summary(time_window_minutes=60)
        print(f"  总会话数: {summary['total_sessions']}")
        print(f"  成功率: {summary['success_rate']:.1%}")
        print(f"  平均耗时: {summary['avg_duration_ms']:.0f}ms")
        print(f"  总成本: ${summary['total_cost']:.4f}")
        
        print(f"\n✅ 工作流指标生成完成！")
        
    except Exception as e:
        print(f"❌ 工作流指标生成失败: {e}")
        import traceback
        traceback.print_exc()


def verify_metrics():
    """验证指标是否可以被Prometheus抓取"""
    print(f"\n🔍 验证Prometheus指标...")
    
    try:
        import requests
        
        # 获取指标端点
        response = requests.get("http://localhost:8001/api/health/metrics/prometheus", timeout=5)
        
        if response.status_code == 200:
            content = response.text
            
            # 检查关键指标
            metrics_to_check = [
                "streaming_session_ttfb_seconds",
                "streaming_session_duration_seconds",
                "streaming_session_tokens_per_second",
                "streaming_session_success_total",
                "streaming_session_failure_total"
            ]
            
            found_metrics = []
            missing_metrics = []
            
            for metric in metrics_to_check:
                if metric in content:
                    found_metrics.append(metric)
                else:
                    missing_metrics.append(metric)
            
            print(f"\n✅ 找到的指标 ({len(found_metrics)}/{len(metrics_to_check)}):")
            for metric in found_metrics:
                print(f"  ✓ {metric}")
            
            if missing_metrics:
                print(f"\n⚠️  缺失的指标 ({len(missing_metrics)}):")
                for metric in missing_metrics:
                    print(f"  ✗ {metric}")
            
            # 显示指标样本
            print(f"\n📋 指标样本（前20行）:")
            lines = content.split('\n')
            for line in lines[:20]:
                if line and not line.startswith('#'):
                    print(f"  {line}")
            
            print(f"\n✅ 指标验证完成！")
            print(f"📊 Prometheus端点: http://localhost:8001/api/health/metrics/prometheus")
            print(f"📊 Prometheus UI: http://localhost:9090")
            print(f"📊 Grafana UI: http://localhost:3001")
            
        else:
            print(f"❌ 无法访问指标端点: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 指标验证失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 DAML-RAG 测试指标生成器")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目的: 为Grafana仪表盘生成测试数据")
    print("=" * 60)
    
    # 1. 生成流式输出指标
    generate_streaming_metrics(count=20)
    
    # 2. 生成工作流指标
    generate_workflow_metrics(count=5)
    
    # 3. 验证指标
    verify_metrics()
    
    print("\n" + "=" * 60)
    print("🎉 测试指标生成完成！")
    print("=" * 60)
    print("\n📌 下一步:")
    print("1. 访问 Grafana: http://localhost:3001")
    print("2. 用户名: admin")
    print("3. 密码: Xxxc1765563156.")
    print("4. 查看仪表盘，应该能看到数据了")
    print("\n💡 提示:")
    print("- 如果仪表盘还是没数据，检查时间范围（右上角）")
    print("- 确保选择了正确的数据源（Prometheus）")
    print("- 刷新浏览器页面")
    print("=" * 60)


if __name__ == "__main__":
    main()
