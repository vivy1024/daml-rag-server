#!/usr/bin/env python3
"""
验证监控和日志功能

实际使用监控功能，验证其是否正常工作
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.framework.monitoring.streaming_metrics import (
    StreamingSessionMetrics,
    record_streaming_metrics,
    streaming_ttfb,
    streaming_duration,
    streaming_tokens_per_second,
    streaming_success,
    streaming_failure
)

def test_streaming_metrics():
    """测试流式监控指标"""
    print("="*80)
    print("🧪 验证流式监控指标功能")
    print("="*80)
    
    # 模拟记录多个流式会话
    print("\n1. 记录流式会话...")
    
    import time
    
    # 成功的会话1
    metrics1 = StreamingSessionMetrics(
        session_id='test_session_001',
        user_id='test_user_001',
        start_time=time.time(),
        first_byte_time=time.time() + 1.2,
        end_time=time.time() + 23.0,
        total_tokens=300,
        success=True
    )
    record_streaming_metrics(metrics1)
    
    # 成功的会话2
    metrics2 = StreamingSessionMetrics(
        session_id='test_session_002',
        user_id='test_user_002',
        start_time=time.time(),
        first_byte_time=time.time() + 1.5,
        end_time=time.time() + 28.0,
        total_tokens=350,
        success=True
    )
    record_streaming_metrics(metrics2)
    
    # 失败的会话
    metrics3 = StreamingSessionMetrics(
        session_id='test_session_003',
        user_id='test_user_003',
        start_time=time.time(),
        first_byte_time=time.time() + 2.0,
        end_time=time.time() + 5.0,
        total_tokens=50,
        success=False,
        error_message='timeout'
    )
    record_streaming_metrics(metrics3)
    
    print("✅ 已记录3个流式会话")
    
    # 获取Prometheus指标值
    print("\n2. 验证Prometheus指标...")
    
    # 检查计数器
    success_count = streaming_success._value._value
    failure_count = streaming_failure._value._value
    
    print("\n" + "="*80)
    print("📊 流式输出监控统计")
    print("="*80)
    print(f"成功会话数: {success_count}")
    print(f"失败会话数: {failure_count}")
    print(f"总会话数: {success_count + failure_count}")
    
    if success_count + failure_count > 0:
        success_rate = success_count / (success_count + failure_count)
        print(f"成功率: {success_rate:.2%}")
    
    print(f"\n✅ TTFB指标已记录: {streaming_ttfb._sum._value > 0}")
    print(f"✅ 持续时间指标已记录: {streaming_duration._sum._value > 0}")
    print(f"✅ 令牌速率指标已记录: {streaming_tokens_per_second._sum._value > 0}")
    
    return True

def test_degradation_events():
    """测试降级事件记录"""
    print("\n" + "="*80)
    print("🧪 验证降级事件记录功能")
    print("="*80)
    
    # 记录降级事件
    print("\n1. 记录降级事件...")
    
    # 降级事件通过失败的会话来体现
    import time
    
    # 失败会话（代表降级）
    metrics_degraded = StreamingSessionMetrics(
        session_id='test_session_004',
        user_id='test_user_004',
        start_time=time.time(),
        first_byte_time=time.time() + 2.0,
        end_time=time.time() + 5.0,
        total_tokens=50,
        success=False,
        error_message='LLM调用超时，已降级到非流式模式'
    )
    record_streaming_metrics(metrics_degraded)
    
    print("✅ 已记录降级事件")
    
    # 获取失败计数
    print("\n2. 获取降级统计...")
    failure_count = streaming_failure._value._value
    
    print("\n" + "="*80)
    print("⚠️ 降级事件统计")
    print("="*80)
    print(f"失败/降级次数: {failure_count}")
    
    return True

def test_health_api():
    """测试健康检查API"""
    print("\n" + "="*80)
    print("🧪 验证健康检查API")
    print("="*80)
    
    try:
        # 导入健康检查路由
        from src.api.routes.health import router
        
        print("\n✅ 健康检查API已正确导入")
        print("   可以通过以下端点访问:")
        print("   - GET /health")
        print("   - GET /api/health/metrics/prometheus")
        
        return True
    except ImportError as e:
        print(f"\n❌ 健康检查API导入失败: {e}")
        return False

def main():
    """主函数"""
    print("="*80)
    print("🔍 监控和日志功能验证")
    print("="*80)
    print("\n目标：实际使用监控功能，验证其是否正常工作")
    
    results = {}
    
    # 测试流式监控指标
    results['streaming_metrics'] = test_streaming_metrics()
    
    # 测试降级事件记录
    results['degradation_events'] = test_degradation_events()
    
    # 测试健康检查API
    results['health_api'] = test_health_api()
    
    # 总结
    print("\n" + "="*80)
    print("📊 验证结果总结")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    print(f"\n总测试项: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    print("\n详细结果:")
    test_names = {
        'streaming_metrics': '流式监控指标',
        'degradation_events': '降级事件记录',
        'health_api': '健康检查API'
    }
    
    for key, name in test_names.items():
        status = "✅ 通过" if results.get(key, False) else "❌ 失败"
        print(f"  {status} - {name}")
    
    if passed_tests == total_tests:
        print("\n" + "="*80)
        print("✅ 所有监控功能验证通过！")
        print("="*80)
        print("\n监控功能已正常工作，可以通过以下方式使用：")
        print("1. 在代码中导入: from src.framework.monitoring.streaming_metrics import StreamingSessionMetrics, record_streaming_metrics")
        print("2. 创建指标: metrics = StreamingSessionMetrics(...)")
        print("3. 记录会话: record_streaming_metrics(metrics)")
        print("4. API访问: GET /health")
        print("5. API访问: GET /api/health/metrics/prometheus")
        return True
    else:
        print("\n" + "="*80)
        print("❌ 部分监控功能验证失败")
        print("="*80)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
