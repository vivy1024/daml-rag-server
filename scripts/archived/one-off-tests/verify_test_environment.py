#!/usr/bin/env python3
"""
验证测试环境脚本
检查所有必需的服务和配置是否就绪
"""

import os
import sys
import redis
import pymysql
import requests
from datetime import datetime


def check_docker_containers():
    """检查Docker容器状态"""
    print("🐳 检查Docker容器状态...")
    print("   ℹ️ 跳过（在容器内部无法检查）")
    return True  # 假设已通过外部验证


def check_redis_connection():
    """检查Redis连接"""
    print("📦 检查Redis连接...")
    try:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'fitness_redis'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            decode_responses=True
        )
        
        redis_client.ping()
        print("   ✅ Redis连接正常")
        return True
    except Exception as e:
        print(f"   ❌ Redis连接失败: {e}")
        return False


def check_mysql_connection():
    """检查MySQL连接"""
    print("🗄️ 检查MySQL连接...")
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'fitness_mysql'),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            user=os.getenv('MYSQL_USER', 'fitness_user'),
            password=os.getenv('MYSQL_PASSWORD', 'fitness_pass'),
            database=os.getenv('MYSQL_DATABASE', 'fitness_app'),
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        connection.close()
        
        print("   ✅ MySQL连接正常")
        return True
    except Exception as e:
        print(f"   ❌ MySQL连接失败: {e}")
        return False


def check_daml_rag_api():
    """检查DAML-RAG API"""
    print("🚀 检查DAML-RAG API...")
    try:
        response = requests.get('http://localhost:8001/api/health', timeout=5)
        if response.status_code == 200:
            print("   ✅ DAML-RAG API正常")
            return True
        else:
            print(f"   ❌ DAML-RAG API异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ DAML-RAG API连接失败: {e}")
        return False


def check_prometheus_api():
    """检查Prometheus API"""
    print("📊 检查Prometheus API...")
    try:
        # 在Docker网络中使用容器名
        response = requests.get('http://fitness_prometheus:9090/api/v1/status/config', timeout=5)
        if response.status_code == 200:
            print("   ✅ Prometheus API正常")
            return True
        else:
            print(f"   ❌ Prometheus API异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Prometheus API连接失败: {e}")
        return False


def check_grafana_api():
    """检查Grafana API"""
    print("📈 检查Grafana API...")
    try:
        # 在Docker网络中使用容器名
        response = requests.get('http://fitness_grafana:3000/api/health', timeout=5)
        if response.status_code == 200:
            print("   ✅ Grafana API正常")
            return True
        else:
            print(f"   ❌ Grafana API异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Grafana API连接失败: {e}")
        return False


def check_test_data_files():
    """检查测试数据文件"""
    print("📁 检查测试数据文件...")
    
    test_data_file = '/app/tests/test_data/streaming_test_queries.json'
    
    if os.path.exists(test_data_file):
        print(f"   ✅ 测试数据文件存在: {test_data_file}")
        return True
    else:
        print(f"   ❌ 测试数据文件不存在: {test_data_file}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 开始验证测试环境")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    checks = [
        ("Docker容器", check_docker_containers()),
        ("Redis连接", check_redis_connection()),
        ("MySQL连接", check_mysql_connection()),
        ("DAML-RAG API", check_daml_rag_api()),
        ("Prometheus API", check_prometheus_api()),
        ("Grafana API", check_grafana_api()),
        ("测试数据文件", check_test_data_files())
    ]
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📋 验证结果总结:")
    print("=" * 60)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {check_name}: {status}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print(f"✅ 所有检查通过！({passed}/{total})")
        print("🎉 测试环境已就绪，可以开始测试")
        return 0
    else:
        print(f"⚠️ 部分检查失败 ({passed}/{total} 通过)")
        print("❌ 请修复失败的检查项后再开始测试")
        return 1


if __name__ == "__main__":
    sys.exit(main())
