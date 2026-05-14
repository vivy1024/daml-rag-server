#!/usr/bin/env python3
"""
任务8 Checkpoint验证脚本
验证MCP Docker配置标准化的所有配置正确性
"""

import json
import os
import sys
from pathlib import Path

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"🔍 {title}")
    print("=" * 60)

def print_success(message):
    """打印成功信息"""
    print(f"✅ {message}")

def print_warning(message):
    """打印警告信息"""
    print(f"⚠️  {message}")

def print_error(message):
    """打印错误信息"""
    print(f"❌ {message}")

def validate_mcp_registry():
    """验证mcp_registry.json配置"""
    print_header("验证 mcp_registry.json")
    
    registry_path = Path("/app/config/mcp_registry.json")
    
    if not registry_path.exists():
        print_error(f"配置文件不存在: {registry_path}")
        return False
    
    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        servers = config.get('servers', {})
        if not servers:
            print_error("未找到任何MCP服务器配置")
            return False
        
        print_success(f"找到 {len(servers)} 个MCP服务器配置")
        
        all_valid = True
        for server_name, server_config in servers.items():
            # 检查type
            if server_config.get('type') != 'stdio':
                print_error(f"[{server_name}] type应为'stdio'，当前为: {server_config.get('type')}")
                all_valid = False
            else:
                print_success(f"[{server_name}] type = 'stdio'")
            
            # 检查command
            if server_config.get('command') != 'node':
                print_warning(f"[{server_name}] command应为'node'，当前为: {server_config.get('command')}")
            else:
                print_success(f"[{server_name}] command = 'node'")
            
            # 检查args路径
            args = server_config.get('args', [])
            if args and len(args) > 0:
                path = args[0]
                if path.startswith('/app/mcp-servers/'):
                    print_success(f"[{server_name}] args路径正确: {path}")
                else:
                    print_error(f"[{server_name}] args路径应以'/app/mcp-servers/'开头: {path}")
                    all_valid = False
        
        return all_valid
    
    except Exception as e:
        print_error(f"验证失败: {e}")
        return False

def validate_docker_compose():
    """验证docker-compose.yml无HTTP容器"""
    print_header("验证 docker-compose.yml")
    
    # 在容器内无法直接读取宿主机的docker-compose.yml
    # 但我们可以检查环境变量
    
    # 检查是否有HTTP URL环境变量
    http_url_vars = [
        'MCP_USER_PROFILE_URL',
        'MCP_FITNESS_COACH_URL'
    ]
    
    found_http_vars = []
    for var in http_url_vars:
        if os.getenv(var):
            found_http_vars.append(var)
    
    if found_http_vars:
        print_error(f"发现HTTP URL环境变量: {', '.join(found_http_vars)}")
        return False
    else:
        print_success("未发现HTTP URL环境变量")
    
    # 检查MCP目录挂载
    mcp_base = Path("/app/mcp-servers")
    if mcp_base.exists():
        print_success(f"MCP目录挂载正确: {mcp_base}")
    else:
        print_error(f"MCP目录不存在: {mcp_base}")
        return False
    
    return True

def validate_no_http_files():
    """验证无HTTP相关遗留文件"""
    print_header("验证无HTTP相关遗留文件")
    
    mcp_base = Path("/app/mcp-servers")
    
    # 检查是否有Dockerfile.http
    http_dockerfiles = list(mcp_base.rglob("Dockerfile.http"))
    if http_dockerfiles:
        print_error(f"发现HTTP Dockerfile: {len(http_dockerfiles)}个")
        for f in http_dockerfiles:
            print(f"  - {f}")
        return False
    else:
        print_success("未发现Dockerfile.http文件")
    
    # 检查是否有http-server.ts（排除archive目录）
    http_servers = []
    for server_dir in mcp_base.iterdir():
        if server_dir.is_dir() and server_dir.name != 'archive':
            http_server_file = server_dir / "src" / "http-server.ts"
            if http_server_file.exists():
                http_servers.append(http_server_file)
    
    if http_servers:
        print_error(f"发现http-server.ts文件: {len(http_servers)}个")
        for f in http_servers:
            print(f"  - {f}")
        return False
    else:
        print_success("未发现http-server.ts文件（archive目录除外）")
    
    return True

def validate_stdio_files():
    """验证stdio相关文件存在"""
    print_header("验证stdio相关文件")
    
    mcp_base = Path("/app/mcp-servers")
    
    required_servers = [
        "user-profile-stdio",
        "python_builtin"
    ]
    
    all_valid = True
    for server_name in required_servers:
        server_dir = mcp_base / server_name
        
        if not server_dir.exists():
            print_error(f"[{server_name}] 目录不存在")
            all_valid = False
            continue
        
        # 检查src/index.ts
        index_ts = server_dir / "src" / "index.ts"
        if index_ts.exists():
            print_success(f"[{server_name}] src/index.ts存在")
        else:
            print_warning(f"[{server_name}] src/index.ts不存在")
        
        # 检查build目录
        build_dir = server_dir / "build"
        if build_dir.exists():
            js_files = list(build_dir.glob("*.js"))
            print_success(f"[{server_name}] build目录存在，包含{len(js_files)}个JS文件")
        else:
            print_error(f"[{server_name}] build目录不存在")
            all_valid = False
    
    return all_valid

def main():
    """主函数"""
    print_header("任务8 Checkpoint - 配置正确性验证")
    
    results = {
        "mcp_registry": validate_mcp_registry(),
        "docker_compose": validate_docker_compose(),
        "no_http_files": validate_no_http_files(),
        "stdio_files": validate_stdio_files()
    }
    
    print_header("验证摘要")
    
    all_passed = all(results.values())
    
    for check_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {check_name}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有验证通过！配置正确！")
        print("=" * 60)
        return 0
    else:
        print("⚠️  部分验证失败，请检查上述错误")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
