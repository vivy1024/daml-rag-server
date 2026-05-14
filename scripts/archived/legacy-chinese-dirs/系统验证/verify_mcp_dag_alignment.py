#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP工具与DAG编排器对齐验证脚本

验证以下内容：
1. DAG编排器注册的工具数量
2. MCP配置文件中的Python工具数量
3. 工具名称是否一致
4. mcp_server配置是否正确（python_builtin vs user-profile-stdio）

作者: BUILD_BODY Team
日期: 2025-12-16
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_mcp_config():
    """加载MCP配置文件"""
    config_path = project_root / "config" / "mcp_registry.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_dag_tools():
    """从DAG编排器代码中提取工具列表"""
    dag_file = project_root / "src" / "applications" / "fitness" / "fitness_dag_orchestrator.py"
    
    tools = []
    with open(dag_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'self.tool_registry.register(' in line:
            # 下一行应该是工具名称
            i += 1
            if i < len(lines):
                tool_line = lines[i].strip()
                if tool_line.startswith('"') and tool_line.endswith('",'):
                    tool_name = tool_line.strip('"').strip(',')
                    
                    # 查找mcp_server配置
                    mcp_server = None
                    for j in range(i, min(i + 20, len(lines))):
                        if 'mcp_server=' in lines[j]:
                            server_line = lines[j].strip()
                            if 'mcp_server="' in server_line:
                                mcp_server = server_line.split('mcp_server="')[1].split('"')[0]
                            break
                    
                    tools.append({
                        'name': tool_name,
                        'mcp_server': mcp_server
                    })
        i += 1
    
    return tools


def main():
    print("=" * 80)
    print("🔍 MCP工具与DAG编排器对齐验证")
    print("=" * 80)
    print()
    
    # 1. 加载MCP配置
    print("📋 步骤1: 加载MCP配置文件...")
    mcp_config = load_mcp_config()
    
    # 提取Python工具列表
    python_tools = mcp_config.get('python_tools', {}).get('tools', [])
    python_tool_names = {tool['name'] for tool in python_tools}
    
    # 提取stdio MCP工具
    stdio_tools = []
    for server_name, server_config in mcp_config.get('servers', {}).items():
        for tool in server_config.get('tools', []):
            stdio_tools.append({
                'name': tool['name'],
                'server': server_name
            })
    
    print(f"✅ Python工具数量: {len(python_tools)}")
    print(f"✅ stdio MCP工具数量: {len(stdio_tools)}")
    print()
    
    # 2. 提取DAG编排器工具
    print("📋 步骤2: 提取DAG编排器注册的工具...")
    dag_tools = extract_dag_tools()
    print(f"✅ DAG编排器注册工具数量: {len(dag_tools)}")
    print()
    
    # 3. 分类统计
    print("📋 步骤3: 分类统计...")
    python_builtin_tools = [t for t in dag_tools if t['mcp_server'] == 'python_builtin']
    user_profile_tools = [t for t in dag_tools if t['mcp_server'] == 'user-profile-stdio']
    other_tools = [t for t in dag_tools if t['mcp_server'] not in ['python_builtin', 'user-profile-stdio']]
    
    print(f"  • python_builtin: {len(python_builtin_tools)} 个工具")
    print(f"  • user-profile-stdio: {len(user_profile_tools)} 个工具")
    if other_tools:
        print(f"  ⚠️  其他服务器: {len(other_tools)} 个工具")
    print()
    
    # 4. 验证对齐
    print("📋 步骤4: 验证工具对齐...")
    print()
    
    # 4.1 检查Python工具对齐
    print("🔍 4.1 Python工具对齐检查:")
    python_builtin_names = {t['name'] for t in python_builtin_tools}
    
    # DAG中有但MCP配置中没有
    missing_in_mcp = python_builtin_names - python_tool_names
    if missing_in_mcp:
        print(f"  ❌ DAG中有但MCP配置中缺失的工具 ({len(missing_in_mcp)}):")
        for tool in sorted(missing_in_mcp):
            print(f"     - {tool}")
    else:
        print(f"  ✅ 所有DAG中的python_builtin工具都在MCP配置中")
    
    # MCP配置中有但DAG中没有
    missing_in_dag = python_tool_names - python_builtin_names
    if missing_in_dag:
        print(f"  ⚠️  MCP配置中有但DAG中未注册的工具 ({len(missing_in_dag)}):")
        for tool in sorted(missing_in_dag):
            print(f"     - {tool}")
    else:
        print(f"  ✅ 所有MCP配置中的Python工具都在DAG中注册")
    
    print()
    
    # 4.2 检查user-profile工具
    print("🔍 4.2 user-profile-stdio工具检查:")
    stdio_tool_names = {t['name'] for t in stdio_tools}
    user_profile_names = {t['name'] for t in user_profile_tools}
    
    if user_profile_names == stdio_tool_names:
        print(f"  ✅ user-profile-stdio工具完全对齐 ({len(user_profile_names)} 个)")
        for tool in sorted(user_profile_names):
            print(f"     - {tool}")
    else:
        print(f"  ❌ user-profile-stdio工具不对齐")
        print(f"     DAG中: {sorted(user_profile_names)}")
        print(f"     MCP中: {sorted(stdio_tool_names)}")
    
    print()
    
    # 4.3 检查是否有遗留的旧服务器引用
    if other_tools:
        print("🔍 4.3 发现遗留的旧服务器引用:")
        print(f"  ❌ 以下工具使用了非标准的mcp_server:")
        for tool in other_tools:
            print(f"     - {tool['name']}: {tool['mcp_server']}")
        print()
    
    # 5. 总结
    print("=" * 80)
    print("📊 验证总结")
    print("=" * 80)
    print()
    
    total_tools = len(dag_tools)
    expected_python = len(python_tools)
    expected_stdio = len(stdio_tools)
    expected_total = expected_python + expected_stdio
    
    print(f"预期工具总数: {expected_total} ({expected_python} Python + {expected_stdio} stdio)")
    print(f"实际注册工具: {total_tools}")
    print()
    
    if missing_in_mcp or missing_in_dag or other_tools or user_profile_names != stdio_tool_names:
        print("❌ 验证失败：存在不对齐的工具")
        return 1
    else:
        print("✅ 验证通过：所有工具完全对齐")
        print()
        print("工具分布:")
        print(f"  • Python内置工具: {len(python_builtin_tools)}")
        print(f"  • user-profile-stdio: {len(user_profile_tools)}")
        print(f"  • 总计: {total_tools}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
