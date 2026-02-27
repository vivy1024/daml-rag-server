#!/usr/bin/env python3
"""
测试监控API的实际运行

通过HTTP请求验证监控API是否正常工作
"""

import requests
import json

def test_streaming_metrics_api():
    """测试流式监控指标API"""
    print("="*80)
    print("🧪 测试流式监控指标API")
    print("="*80)
    
    try:
        # 在容器内使用127.0.0.1而不是localhost
        url = "http://127.0.0.1:8001/api/health/metrics/streaming"
        print(f"\n请求: GET {url}")
        
        response = requests.get(url, params={"time_window": 3600})
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n响应数据:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 验证数据结构
            if 'data' in data:
                stats = data['data']
                print("\n✅ API响应成功")
                print(f"   总会话数: {stats.get('total_sessions', 0)}")
                print(f"   成功率: {stats.get('success_rate', 0):.2%}")
                print(f"   平均TTFB: {stats.get('avg_ttfb_ms', 0):.1f}ms")
                return True
            else:
                print("\n❌ 响应数据格式不正确")
                return False
        else:
            print(f"\n❌ API请求失败: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n⚠️ 无法连接到服务器（localhost:8001）")
        print("   请确保DAML-RAG服务正在运行")
        return False
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False

def test_recent_metrics_api():
    """测试最近流式会话API"""
    print("\n" + "="*80)
    print("🧪 测试最近流式会话API")
    print("="*80)
    
    try:
        # 在容器内使用127.0.0.1而不是localhost
        url = "http://127.0.0.1:8001/api/health/metrics/streaming/recent"
        print(f"\n请求: GET {url}")
        
        response = requests.get(url, params={"limit": 10})
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n响应数据:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 验证数据结构
            if 'data' in data:
                metrics = data['data']
                print(f"\n✅ API响应成功")
                print(f"   返回记录数: {len(metrics)}")
                return True
            else:
                print("\n❌ 响应数据格式不正确")
                return False
        else:
            print(f"\n❌ API请求失败: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n⚠️ 无法连接到服务器（localhost:8001）")
        print("   请确保DAML-RAG服务正在运行")
        return False
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("="*80)
    print("🔍 监控API实际运行测试")
    print("="*80)
    print("\n目标：通过HTTP请求验证监控API是否正常工作")
    
    results = {}
    
    # 测试流式监控指标API
    results['streaming_metrics_api'] = test_streaming_metrics_api()
    
    # 测试最近流式会话API
    results['recent_metrics_api'] = test_recent_metrics_api()
    
    # 总结
    print("\n" + "="*80)
    print("📊 测试结果总结")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    print(f"\n总测试项: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    print("\n详细结果:")
    test_names = {
        'streaming_metrics_api': '流式监控指标API',
        'recent_metrics_api': '最近流式会话API'
    }
    
    for key, name in test_names.items():
        status = "✅ 通过" if results.get(key, False) else "❌ 失败"
        print(f"  {status} - {name}")
    
    if passed_tests == total_tests:
        print("\n" + "="*80)
        print("✅ 所有监控API测试通过！")
        print("="*80)
        print("\n监控API已正常运行，可以通过以下方式访问：")
        print("1. 流式监控统计: GET http://localhost:8001/api/health/metrics/streaming?time_window=3600")
        print("2. 最近会话记录: GET http://localhost:8001/api/health/metrics/streaming/recent?limit=10")
        return True
    else:
        print("\n" + "="*80)
        print("⚠️ 部分监控API测试失败")
        print("="*80)
        print("\n可能的原因：")
        print("1. DAML-RAG服务未启动")
        print("2. 端口8001未开放")
        print("3. API路由配置错误")
        return False

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
