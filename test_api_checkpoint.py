#!/usr/bin/env python3
"""
监控API端点测试脚本
用于Checkpoint 9: 确保所有API测试通过
"""

import requests
import json

def test_api_endpoints():
    """测试所有监控API端点"""
    base_url = 'http://localhost:8001'
    endpoints = [
        '/api/health',
        '/api/health/components',
        '/api/health/metrics',
        '/api/health/metrics/streaming',
        '/api/health/metrics/prometheus'
    ]
    
    print('=' * 60)
    print('监控API端点测试')
    print('=' * 60)
    print()
    
    all_passed = True
    results = []
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'{base_url}{endpoint}', timeout=5)
            
            # 检查状态码
            status_ok = response.status_code == 200
            
            # 检查响应内容
            if 'prometheus' in endpoint:
                # Prometheus端点返回文本格式
                content_ok = len(response.text) > 0 and ('HELP' in response.text or 'TYPE' in response.text)
                content_type = 'text/plain'
            else:
                # 其他端点返回JSON
                try:
                    data = response.json()
                    content_ok = len(data) > 0
                    content_type = 'application/json'
                except:
                    content_ok = False
                    content_type = 'unknown'
            
            passed = status_ok and content_ok
            all_passed = all_passed and passed
            
            result = {
                'endpoint': endpoint,
                'status_code': response.status_code,
                'content_type': content_type,
                'passed': passed
            }
            results.append(result)
            
            status_icon = '✅' if passed else '❌'
            print(f'{status_icon} {endpoint}')
            print(f'   状态码: {response.status_code}')
            print(f'   内容类型: {content_type}')
            print(f'   内容有效: {"是" if content_ok else "否"}')
            print()
            
        except Exception as e:
            all_passed = False
            result = {
                'endpoint': endpoint,
                'error': str(e),
                'passed': False
            }
            results.append(result)
            print(f'❌ {endpoint}')
            print(f'   错误: {str(e)}')
            print()
    
    print('=' * 60)
    if all_passed:
        print('✅ 所有测试通过')
    else:
        print('❌ 有测试失败')
    print('=' * 60)
    
    return all_passed, results


def test_api_functionality():
    """测试API实际功能"""
    print()
    print('=' * 60)
    print('API功能验证')
    print('=' * 60)
    print()
    
    try:
        # 1. 健康检查
        response = requests.get('http://localhost:8001/api/health')
        health_data = response.json()
        status = health_data.get('status', 'unknown')
        print(f'✅ 健康检查: {status}')
        
        # 2. 系统指标
        response = requests.get('http://localhost:8001/api/health/metrics')
        metrics_data = response.json()
        cpu = metrics_data.get('system', {}).get('cpu_percent', 'N/A')
        memory = metrics_data.get('system', {}).get('memory_percent', 'N/A')
        print(f'✅ 系统指标: CPU={cpu}%, Memory={memory}%')
        
        # 3. 流式监控
        response = requests.get('http://localhost:8001/api/health/metrics/streaming')
        streaming_data = response.json()
        stats_count = len(streaming_data.get('statistics', {}))
        print(f'✅ 流式统计: {stats_count} 个指标')
        
        # 4. Prometheus导出
        response = requests.get('http://localhost:8001/api/health/metrics/prometheus')
        prometheus_text = response.text
        lines = [l for l in prometheus_text.split('\n') if l and not l.startswith('#')]
        print(f'✅ Prometheus指标: {len(lines)} 行数据')
        
        print()
        print('=' * 60)
        print('✅ 所有功能验证通过')
        print('=' * 60)
        
        return True
        
    except Exception as e:
        print(f'❌ 功能验证失败: {str(e)}')
        print('=' * 60)
        return False


if __name__ == '__main__':
    # 运行端点测试
    endpoints_passed, results = test_api_endpoints()
    
    # 运行功能测试
    functionality_passed = test_api_functionality()
    
    # 总结
    print()
    print('=' * 60)
    print('测试总结')
    print('=' * 60)
    print(f'端点测试: {"✅ 通过" if endpoints_passed else "❌ 失败"}')
    print(f'功能测试: {"✅ 通过" if functionality_passed else "❌ 失败"}')
    print('=' * 60)
    
    if endpoints_passed and functionality_passed:
        print()
        print('🎉 Checkpoint 9: 所有API测试通过！')
        exit(0)
    else:
        print()
        print('⚠️  Checkpoint 9: 有测试失败，需要修复')
        exit(1)
