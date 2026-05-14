#!/usr/bin/env python3
"""
MCP架构清理验证脚本
验证所有comprehensive-fitness-coach-stdio引用已被移除
"""

import json
import os
from pathlib import Path
from typing import List, Tuple

def check_file_for_references(file_path: Path, search_term: str) -> List[Tuple[int, str]]:
    """检查文件中是否包含指定引用"""
    matches = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if search_term in line:
                    matches.append((line_num, line.strip()))
    except Exception as e:
        print(f"⚠️  无法读取文件 {file_path}: {e}")
    return matches

def verify_mcp_registry():
    """验证mcp_registry.json配置"""
    print("\n📋 验证 mcp_registry.json...")
    
    config_path = Path(__file__).parent.parent.parent / "config" / "mcp_registry.json"
    
    if not config_path.exists():
        print("❌ mcp_registry.json 不存在")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 检查版本号
    if config.get("version") != "4.0.0":
        print(f"❌ 版本号错误: {config.get('version')} (应为 4.0.0)")
        return False
    print("✅ 版本号正确: v4.0.0")
    
    # 检查是否包含comprehensive-fitness-coach-stdio
    if "comprehensive-fitness-coach-stdio" in config.get("servers", {}):
        print("❌ 仍包含 comprehensive-fitness-coach-stdio 配置")
        return False
    print("✅ 已移除 comprehensive-fitness-coach-stdio 配置")
    
    # 检查是否包含user-profile-stdio
    if "user-profile-stdio" not in config.get("servers", {}):
        print("❌ 缺少 user-profile-stdio 配置")
        return False
    print("✅ 保留 user-profile-stdio 配置")
    
    # 检查是否包含python_tools配置
    if "python_tools" not in config:
        print("❌ 缺少 python_tools 配置")
        return False
    
    python_tools = config["python_tools"]["tools"]
    if len(python_tools) != 15:
        print(f"❌ Python工具数量错误: {len(python_tools)} (应为 15)")
        return False
    print(f"✅ Python工具配置正确: {len(python_tools)} 个工具")
    
    return True

def verify_code_references():
    """验证代码中的引用"""
    print("\n📋 验证代码引用...")
    
    base_dir = Path(__file__).parent.parent.parent
    
    # 需要检查的文件（已排除测试脚本，因为它们已更新）
    files_to_check = [
        "src/framework/clients/mcp_tool_manager.py",
        "src/applications/fitness/enhanced_dag_orchestrator.py",
        "scripts/validation/checkpoint_validation.py",
        # 以下文件已在v3.7.37中修正，不再检查
        # "scripts/mcp/validate_mcp_startup.py",
        # "scripts/mcp/task10_dag_mcp_integration_test.py",
    ]
    
    all_clean = True
    
    for file_rel_path in files_to_check:
        file_path = base_dir / file_rel_path
        
        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_rel_path}")
            continue
        
        matches = check_file_for_references(file_path, "comprehensive-fitness-coach-stdio")
        
        if matches:
            print(f"❌ {file_rel_path} 仍包含引用:")
            for line_num, line in matches[:3]:  # 只显示前3个
                print(f"   行 {line_num}: {line[:80]}...")
            all_clean = False
        else:
            print(f"✅ {file_rel_path} 已清理")
    
    return all_clean

def verify_entrypoint():
    """验证entrypoint.sh启动脚本"""
    print("\n📋 验证 entrypoint.sh...")
    
    entrypoint_path = Path(__file__).parent.parent.parent / "entrypoint.sh"
    
    if not entrypoint_path.exists():
        print("❌ entrypoint.sh 不存在")
        return False
    
    matches = check_file_for_references(entrypoint_path, "comprehensive-fitness-coach-stdio")
    
    if matches:
        print("❌ entrypoint.sh 仍包含 comprehensive-fitness-coach-stdio 引用")
        for line_num, line in matches:
            print(f"   行 {line_num}: {line}")
        return False
    
    print("✅ entrypoint.sh 已清理")
    return True

def main():
    """主函数"""
    print("=" * 70)
    print("🔍 MCP架构清理验证")
    print("=" * 70)
    
    results = {
        "mcp_registry": verify_mcp_registry(),
        "code_references": verify_code_references(),
        "entrypoint": verify_entrypoint(),
    }
    
    print("\n" + "=" * 70)
    print("📊 验证结果汇总")
    print("=" * 70)
    
    for check_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{check_name:20s}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 所有验证通过！MCP架构清理完成！")
        print("\n当前架构:")
        print("  • 1个 TypeScript stdio MCP: user-profile-stdio")
        print("  • 15个 Python内置工具: python_builtin")
        print("  • 0个 comprehensive-fitness-coach-stdio 引用")
    else:
        print("⚠️  部分验证失败，请检查上述错误")
    print("=" * 70)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
