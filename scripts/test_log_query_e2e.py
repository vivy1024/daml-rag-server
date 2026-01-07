#!/usr/bin/env python3
"""
端到端日志查询测试脚本

功能：
1. 发送测试请求到DAML-RAG服务
2. 提取request_id
3. 在日志文件中查询完整链路
4. 验证日志完整性

使用方法：
    python scripts/test_log_query_e2e.py
"""

import requests
import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 配置
DAML_RAG_URL = "http://localhost:8001"
LOG_DIR = Path("/app/logs")
TEST_QUERY = "我想练胸肌，给我推荐一些动作"
TEST_USER_ID = 2
TEST_DOMAIN = "fitness"


def send_test_request() -> Optional[str]:
    """
    发送测试请求到DAML-RAG服务
    
    Returns:
        request_id: 请求ID，如果失败返回None
    """
    print("=" * 80)
    print("步骤1: 发送测试请求到DAML-RAG")
    print("=" * 80)
    
    # 生成唯一的session_id
    session_id = f"e2e_test_{int(time.time())}"
    
    payload = {
        "message": TEST_QUERY,
        "user_id": TEST_USER_ID,
        "domain": TEST_DOMAIN,
        "session_id": session_id
    }
    
    print(f"\n请求参数:")
    print(f"  URL: {DAML_RAG_URL}/api/v1/chat/stream")
    print(f"  Query: {TEST_QUERY}")
    print(f"  User ID: {TEST_USER_ID}")
    print(f"  Session ID: {session_id}")
    print(f"  Domain: {TEST_DOMAIN}")
    
    try:
        print(f"\n发送请求...")
        response = requests.post(
            f"{DAML_RAG_URL}/api/v1/chat/stream",
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            return None
        
        print(f"✅ 请求成功: HTTP {response.status_code}")
        
        # 从响应中提取request_id
        request_id = None
        chunk_count = 0
        
        print(f"\n接收流式响应...")
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # 跳过注释行
                if line_str.startswith(':'):
                    continue
                
                # 解析SSE数据
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # 移除 'data: ' 前缀
                    
                    try:
                        data = json.loads(data_str)
                        chunk_count += 1
                        
                        # 提取request_id
                        if 'request_id' in data and not request_id:
                            request_id = data['request_id']
                            print(f"✅ 提取到request_id: {request_id}")
                        
                        # 显示内容片段
                        if 'content' in data and data['content']:
                            content = data['content'][:50]
                            print(f"  接收内容片段 #{chunk_count}: {content}...")
                        
                        # 检查是否完成
                        if data.get('done', False):
                            print(f"\n✅ 流式响应完成，共接收 {chunk_count} 个数据块")
                            break
                    
                    except json.JSONDecodeError:
                        continue
        
        if not request_id:
            print(f"❌ 未能从响应中提取request_id")
            return None
        
        return request_id
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        return None


def search_logs_by_request_id(request_id: str) -> Dict[str, List[str]]:
    """
    在日志文件中搜索指定request_id的所有日志
    
    Args:
        request_id: 请求ID
    
    Returns:
        日志字典，按文件分类
    """
    print("\n" + "=" * 80)
    print(f"步骤2: 在日志文件中查询request_id: {request_id}")
    print("=" * 80)
    
    # 获取今天的日志文件
    today = datetime.now().strftime("%Y%m%d")
    log_files = [
        LOG_DIR / f"daml-rag-{today}.log",
        LOG_DIR / f"daml-rag-error-{today}.log"
    ]
    
    results = {}
    
    for log_file in log_files:
        if not log_file.exists():
            print(f"⚠️  日志文件不存在: {log_file}")
            continue
        
        print(f"\n搜索文件: {log_file.name}")
        
        matching_lines = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if request_id in line:
                    matching_lines.append(line.strip())
        
        if matching_lines:
            results[log_file.name] = matching_lines
            print(f"✅ 找到 {len(matching_lines)} 条匹配日志")
        else:
            print(f"⚠️  未找到匹配日志")
    
    return results


def analyze_log_chain(logs: Dict[str, List[str]]) -> Dict[str, any]:
    """
    分析日志链路完整性
    
    Args:
        logs: 日志字典
    
    Returns:
        分析结果
    """
    print("\n" + "=" * 80)
    print("步骤3: 分析日志链路完整性")
    print("=" * 80)
    
    all_logs = []
    for file_logs in logs.values():
        all_logs.extend(file_logs)
    
    if not all_logs:
        print("❌ 没有找到任何日志")
        return {
            "success": False,
            "error": "No logs found"
        }
    
    print(f"\n总共找到 {len(all_logs)} 条日志")
    
    # 分析日志内容
    analysis = {
        "total_logs": len(all_logs),
        "has_session_start": False,
        "has_session_complete": False,
        "steps_found": [],
        "errors_found": [],
        "structured_data_found": [],
        "success": False
    }
    
    # 正则表达式模式
    session_start_pattern = r"🚀.*流式会话开始"
    session_complete_pattern = r"🎉.*流式会话完成"
    step_pattern = r"步骤(\d+)"
    error_pattern = r"❌.*错误"
    structured_data_pattern = r"📦.*检测到结构化数据"
    
    for log in all_logs:
        # 检查会话开始
        if re.search(session_start_pattern, log):
            analysis["has_session_start"] = True
            print(f"✅ 找到会话开始日志")
        
        # 检查会话完成
        if re.search(session_complete_pattern, log):
            analysis["has_session_complete"] = True
            print(f"✅ 找到会话完成日志")
        
        # 检查步骤
        step_match = re.search(step_pattern, log)
        if step_match:
            step_num = int(step_match.group(1))
            if step_num not in analysis["steps_found"]:
                analysis["steps_found"].append(step_num)
        
        # 检查错误
        if re.search(error_pattern, log):
            analysis["errors_found"].append(log)
        
        # 检查结构化数据
        if re.search(structured_data_pattern, log):
            analysis["structured_data_found"].append(log)
    
    # 排序步骤
    analysis["steps_found"].sort()
    
    print(f"\n步骤执行情况:")
    print(f"  找到的步骤: {analysis['steps_found']}")
    print(f"  步骤数量: {len(analysis['steps_found'])}")
    
    if analysis["errors_found"]:
        print(f"\n⚠️  发现 {len(analysis['errors_found'])} 个错误:")
        for error in analysis["errors_found"][:3]:  # 只显示前3个
            print(f"  - {error[:100]}...")
    
    if analysis["structured_data_found"]:
        print(f"\n📦 发现 {len(analysis['structured_data_found'])} 个结构化数据:")
        for data in analysis["structured_data_found"][:3]:
            print(f"  - {data[:100]}...")
    
    # 判断链路是否完整
    analysis["success"] = (
        analysis["has_session_start"] and
        analysis["has_session_complete"] and
        len(analysis["steps_found"]) > 0
    )
    
    return analysis


def display_log_samples(logs: Dict[str, List[str]], max_samples: int = 10):
    """
    显示日志样本
    
    Args:
        logs: 日志字典
        max_samples: 最大显示数量
    """
    print("\n" + "=" * 80)
    print("步骤4: 显示日志样本")
    print("=" * 80)
    
    for file_name, file_logs in logs.items():
        print(f"\n文件: {file_name}")
        print("-" * 80)
        
        for i, log in enumerate(file_logs[:max_samples], 1):
            # 截断过长的日志
            if len(log) > 200:
                log = log[:200] + "..."
            print(f"{i}. {log}")
        
        if len(file_logs) > max_samples:
            print(f"... 还有 {len(file_logs) - max_samples} 条日志未显示")


def generate_grafana_query(request_id: str):
    """
    生成Grafana LogQL查询语句
    
    Args:
        request_id: 请求ID
    """
    print("\n" + "=" * 80)
    print("步骤5: 生成Grafana查询语句")
    print("=" * 80)
    
    logql_queries = [
        f'{{job="daml-rag"}} |= "{request_id}"',
        f'{{job="daml-rag"}} | json | request_id="{request_id}"',
        f'{{job="daml-rag"}} |= "{request_id}" |= "步骤"',
        f'{{job="daml-rag"}} |= "{request_id}" |= "ERROR"',
    ]
    
    print(f"\n在Grafana中使用以下LogQL查询:")
    print(f"\n1. 查询所有相关日志:")
    print(f'   {logql_queries[0]}')
    
    print(f"\n2. 使用JSON解析查询:")
    print(f'   {logql_queries[1]}')
    
    print(f"\n3. 查询步骤执行日志:")
    print(f'   {logql_queries[2]}')
    
    print(f"\n4. 查询错误日志:")
    print(f'   {logql_queries[3]}')
    
    print(f"\n访问Grafana Explore:")
    print(f"  URL: http://localhost:3001/explore")
    print(f"  数据源: Loki")
    print(f"  时间范围: Last 15 minutes")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("DAML-RAG 端到端日志查询测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 步骤1: 发送测试请求
    request_id = send_test_request()
    
    if not request_id:
        print("\n❌ 测试失败: 无法获取request_id")
        return 1
    
    # 等待日志写入
    print(f"\n等待3秒，确保日志已写入...")
    time.sleep(3)
    
    # 步骤2: 搜索日志
    logs = search_logs_by_request_id(request_id)
    
    if not logs:
        print(f"\n❌ 测试失败: 未找到任何日志")
        return 1
    
    # 步骤3: 分析日志链路
    analysis = analyze_log_chain(logs)
    
    # 步骤4: 显示日志样本
    display_log_samples(logs, max_samples=15)
    
    # 步骤5: 生成Grafana查询
    generate_grafana_query(request_id)
    
    # 最终结果
    print("\n" + "=" * 80)
    print("测试结果总结")
    print("=" * 80)
    
    print(f"\n✅ Request ID: {request_id}")
    print(f"✅ 总日志数: {analysis['total_logs']}")
    print(f"{'✅' if analysis['has_session_start'] else '❌'} 会话开始日志")
    print(f"{'✅' if analysis['has_session_complete'] else '❌'} 会话完成日志")
    print(f"✅ 执行步骤数: {len(analysis['steps_found'])}")
    print(f"{'⚠️ ' if analysis['errors_found'] else '✅'} 错误数: {len(analysis['errors_found'])}")
    
    if analysis["success"]:
        print(f"\n🎉 测试成功! 日志链路完整")
        print(f"\n验收标准检查:")
        print(f"  ✅ 发送测试请求到DAML-RAG")
        print(f"  ✅ 提取request_id: {request_id}")
        print(f"  ✅ 在日志文件中查询到完整链路")
        print(f"  ✅ 验证日志包含会话开始、步骤执行、会话完成")
        return 0
    else:
        print(f"\n❌ 测试失败: 日志链路不完整")
        return 1


if __name__ == "__main__":
    exit(main())
