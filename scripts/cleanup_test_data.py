#!/usr/bin/env python3
"""
清理测试数据脚本
用于流式工作流综合测试前的环境准备
"""

import os
import sys
import redis
import pymysql
from datetime import datetime


def cleanup_redis_cache():
    """清理Redis缓存中的测试数据"""
    print("🧹 清理Redis缓存...")
    try:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'fitness_redis'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            decode_responses=True
        )
        
        # 清理测试用户相关的缓存
        test_patterns = [
            'test_user*',
            'load_test_user*',
            'streaming_test*'
        ]
        
        deleted_count = 0
        for pattern in test_patterns:
            keys = redis_client.keys(pattern)
            if keys:
                deleted_count += redis_client.delete(*keys)
        
        print(f"   ✅ 已清理 {deleted_count} 个Redis缓存键")
        return True
    except Exception as e:
        print(f"   ⚠️ Redis清理失败: {e}")
        return False


def cleanup_mysql_test_data():
    """清理MySQL中的测试数据"""
    print("🧹 清理MySQL测试数据...")
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
        
        # 清理测试用户的对话记录
        test_user_patterns = ['test_user%', 'load_test_user%']
        deleted_sessions = 0
        
        for pattern in test_user_patterns:
            # 删除测试用户的聊天会话
            cursor.execute("DELETE FROM chat_sessions WHERE user_id LIKE %s", (pattern,))
            deleted_sessions += cursor.rowcount
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"   ✅ 已清理 {deleted_sessions} 个测试会话")
        return True
    except Exception as e:
        print(f"   ⚠️ MySQL清理失败: {e}")
        return False


def reset_prometheus_metrics():
    """重置Prometheus指标（通过重启或等待自然过期）"""
    print("📊 准备重置Prometheus指标...")
    print("   ℹ️ Prometheus指标将在下次查询时自动更新")
    print("   ℹ️ 如需完全重置，请重启Prometheus容器")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 开始清理测试环境")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    
    # 执行清理任务
    results.append(("Redis缓存清理", cleanup_redis_cache()))
    results.append(("MySQL测试数据清理", cleanup_mysql_test_data()))
    results.append(("Prometheus指标准备", reset_prometheus_metrics()))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📋 清理结果总结:")
    print("=" * 60)
    
    success_count = 0
    for task_name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"   {task_name}: {status}")
        if success:
            success_count += 1
    
    print("\n" + "=" * 60)
    if success_count == len(results):
        print("✅ 测试环境清理完成！")
        return 0
    else:
        print(f"⚠️ 部分清理任务失败 ({success_count}/{len(results)} 成功)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
