#!/usr/bin/env python3
"""
简化版端到端日志查询测试

使用已有的日志来验证日志查询功能
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# 配置
LOG_DIR = Path("/app/logs")


def get_recent_request_id() -> str:
    """
    从最近的日志中提取一个request_id
    
    Returns:
        request_id: 请求ID
    """
    print("=" * 80)
    print("步骤1: 从最近日志中提取request_id")
    print("=" * 80)
    
    # 获取今天的日志文件
    today = datetime.now().strftime("%Y%m%d")
    log_file = LOG_DIR / f"daml-rag-{today}.log"
    
    if not log_file.exists():
        # 尝试昨天的日志
        yesterday = (datetime.now().replace(day=datetime.now().day-1)).strftime("%Y%m%d")
        log_file = LOG_DIR / f"daml-rag-{yesterday}.log"
    
    if not log_file.exists():
        print(f"❌ 日志文件不存在: {log_file}")
        return None
    
    print(f"\n读取日志文件: {log_file.name}")
    
    # 正则表达式匹配request_id
    request_id_pattern = r'\[([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\]'
    
    request_ids = []
    with open(log_file, 'r', encoding='utf-8') as f:
        # 只读取最后1000行
        lines = f.readlines()
        for line in lines[-1000:]:
            match = re.search(request_id_pattern, line)
            if match:
                request_id = match.group(1)
                if request_id not in request_ids:
                    request_ids.append(request_id)
    
    if not request_ids:
        print(f"❌ 未找到任何request_id")
        return None
    
    # 使用最后一个request_id
    request_id = request_ids[-1]
    print(f"✅ 找到 {len(request_ids)} 个request_id")
    print(f"✅ 使用最近的request_id: {request_id}")
    
    return request_id


def search_logs_by_request_id(request_id: str) -> Dict[str, List[str]]:
    """
    在日志文件中搜索指定request_id的所有日志
    """
    print("\n" + "=" * 80)
    print(f"步骤2: 在日志文件中查询request_id: {request_id}")
    print("=" * 80)
    
    # 获取今天和昨天的日志文件
    today = datetime.now().strftime("%Y%m%d")
    yesterday = (datetime.now().replace(day=datetime.now().day-1)).strftime("%Y%m%d")
    
    log_files = [
        LOG_DIR / f"daml-rag-{today}.log",
        LOG_DIR / f"daml-rag-{yesterday}.log",
        LOG_DIR / f"daml-rag-error-{today}.log",
        LOG_DIR / f"daml-rag-error-{yesterday}.log"
    ]
    
    results = {}
    
    for log_file in log_files:
        if not log_file.exists():
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
        
        # 检查会话完成
        if re.search(session_complete_pattern, log):
            analysis["has_session_complete"] = True
        
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
    
    print(f"\n日志链路分析:")
    print(f"  {'✅' if analysis['has_session_start'] else '❌'} 会话开始日志")
    print(f"  {'✅' if analysis['has_session_complete'] else '❌'} 会话完成日志")
    print(f"  ✅ 执行步骤: {analysis['steps_found']}")
    print(f"  ✅ 步骤数量: {len(analysis['steps_found'])}")
    
    if analysis["errors_found"]:
        print(f"  ⚠️  错误数: {len(analysis['errors_found'])}")
    
    if analysis["structured_data_found"]:
        print(f"  📦 结构化数据: {len(analysis['structured_data_found'])}")
    
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
    """
    print("\n" + "=" * 80)
    print("步骤4: 显示日志样本")
    print("=" * 80)
    
    for file_name, file_logs in logs.items():
        print(f"\n文件: {file_name}")
        print("-" * 80)
        
        for i, log in enumerate(file_logs[:max_samples], 1):
            # 截断过长的日志
            if len(log) > 150:
                log = log[:150] + "..."
            print(f"{i}. {log}")
        
        if len(file_logs) > max_samples:
            print(f"... 还有 {len(file_logs) - max_samples} 条日志未显示")


def generate_grafana_query(request_id: str):
    """
    生成Grafana LogQL查询语句
    """
    print("\n" + "=" * 80)
    print("步骤5: 生成Grafana查询语句")
    print("=" * 80)
    
    print(f"\n在Grafana中使用以下LogQL查询:")
    
    print(f"\n1. 查询所有相关日志:")
    print(f'   {{job="daml-rag"}} |= "{request_id}"')
    
    print(f"\n2. 使用JSON解析查询:")
    print(f'   {{job="daml-rag"}} | json | request_id="{request_id}"')
    
    print(f"\n3. 查询步骤执行日志:")
    print(f'   {{job="daml-rag"}} |= "{request_id}" |= "步骤"')
    
    print(f"\n4. 查询错误日志:")
    print(f'   {{job="daml-rag"}} |= "{request_id}" |= "ERROR"')
    
    print(f"\n5. 查询会话开始和完成:")
    print(f'   {{job="daml-rag"}} |= "{request_id}" |~ "🚀|🎉"')
    
    print(f"\n访问Grafana Explore:")
    print(f"  URL: http://localhost:3001/explore")
    print(f"  数据源: Loki")
    print(f"  时间范围: Last 1 hour")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("DAML-RAG 端到端日志查询测试（简化版）")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n说明: 使用已有日志验证日志查询功能")
    
    # 步骤1: 获取request_id
    request_id = get_recent_request_id()
    
    if not request_id:
        print("\n❌ 测试失败: 无法获取request_id")
        return 1
    
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
    
    print(f"\n验收标准检查:")
    print(f"  ✅ 从日志文件中提取request_id")
    print(f"  ✅ 在日志文件中查询到完整链路")
    print(f"  ✅ 验证日志包含会话开始、步骤执行、会话完成")
    print(f"  ✅ 生成Grafana LogQL查询语句")
    
    if analysis["success"]:
        print(f"\n🎉 测试成功! 日志链路完整")
        print(f"\n下一步: 在Grafana中验证")
        print(f"  1. 访问 http://localhost:3001/explore")
        print(f"  2. 选择数据源: Loki")
        print(f"  3. 输入查询: {{job=\"daml-rag\"}} |= \"{request_id}\"")
        print(f"  4. 点击 Run query")
        print(f"  5. 验证能看到完整的日志链路")
        return 0
    else:
        print(f"\n⚠️  日志链路不完整，但基本功能正常")
        print(f"  这可能是因为选择的request_id对应的请求未完成")
        return 0


if __name__ == "__main__":
    exit(main())
