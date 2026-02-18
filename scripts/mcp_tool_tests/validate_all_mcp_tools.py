#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证所有MCP工具的参数配置

检查 mcp_tool_manager.py 中的参数schema是否与实际工具的输入schema匹配
"""

import sys
import os
from typing import Dict, List, Set

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.framework.clients.mcp_tool_manager import MCPToolManager
from src.applications.fitness.mcp_tools import initialize_all_tools


def get_tool_input_schema(tool_class) -> Dict[str, Set[str]]:
    """获取工具的输入schema"""
    try:
        input_schema = tool_class.get_input_schema(tool_class)
        if hasattr(input_schema, 'model_fields'):
            # Pydantic v2
            fields = input_schema.model_fields
            required = set()
            optional = set()
            
            for field_name, field_info in fields.items():
                if field_info.is_required():
                    required.add(field_name)
                else:
                    optional.add(field_name)
            
            return {"required": required, "optional": optional}
        else:
            return {"required": set(), "optional": set()}
    except Exception as e:
        print(f"  ⚠️ 无法获取输入schema: {e}")
        return {"required": set(), "optional": set()}


def validate_tool_config(tool_name: str, manager_config: Dict, actual_schema: Dict) -> Dict:
    """验证工具配置"""
    issues = []
    
    # 获取配置中的参数
    config_required = set(manager_config.get("required_params", []))
    config_optional = set(manager_config.get("optional_params", []))
    config_all = config_required | config_optional
    
    # 获取实际的参数
    actual_required = actual_schema.get("required", set())
    actual_optional = actual_schema.get("optional", set())
    actual_all = actual_required | actual_optional
    
    # 检查缺失的必需参数
    missing_required = actual_required - config_all
    if missing_required:
        issues.append(f"缺失必需参数: {missing_required}")
    
    # 检查多余的必需参数
    extra_required = config_required - actual_all
    if extra_required:
        issues.append(f"多余的必需参数: {extra_required}")
    
    # 检查参数分类错误（必需标记为可选，或可选标记为必需）
    misclassified_as_optional = (config_optional & actual_required)
    if misclassified_as_optional:
        issues.append(f"应为必需但标记为可选: {misclassified_as_optional}")
    
    misclassified_as_required = (config_required & actual_optional)
    if misclassified_as_required:
        issues.append(f"应为可选但标记为必需: {misclassified_as_required}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "config_required": config_required,
        "config_optional": config_optional,
        "actual_required": actual_required,
        "actual_optional": actual_optional
    }


def main():
    """主验证函数"""
    print("\n" + "="*80)
    print("MCP工具参数配置验证")
    print("="*80)
    print()
    
    # 初始化所有工具
    print("📦 初始化MCP工具...")
    from src.applications.fitness.mcp_tools.registry import MCPToolRegistry
    
    registry = MCPToolRegistry()
    initialize_all_tools(
        registry=registry,
        neo4j_client=None,
        qdrant_client=None,
        three_layer_engine=None
    )
    tool_registry = registry.tools
    print(f"✅ 已注册 {len(tool_registry)} 个工具")
    print()
    
    # 初始化工具管理器
    print("📦 初始化工具管理器...")
    manager = MCPToolManager()
    print(f"✅ 已配置 {len(manager.tool_mapping)} 个工具")
    print()
    
    # 验证每个工具
    results = []
    
    print("🔍 开始验证工具配置...")
    print()
    
    for tool_name, tool_class in tool_registry.items():
        print(f"📋 验证工具: {tool_name}")
        
        # 获取管理器中的配置
        manager_config = manager.tool_mapping.get(tool_name)
        if not manager_config:
            print(f"  ❌ 工具未在mcp_tool_manager中配置")
            results.append((tool_name, False, ["工具未配置"]))
            print()
            continue
        
        # 获取实际的输入schema
        actual_schema = get_tool_input_schema(tool_class)
        
        # 验证配置
        validation = validate_tool_config(tool_name, manager_config, actual_schema)
        
        if validation["valid"]:
            print(f"  ✅ 配置正确")
            print(f"     必需参数: {len(validation['actual_required'])}个")
            print(f"     可选参数: {len(validation['actual_optional'])}个")
        else:
            print(f"  ❌ 配置错误:")
            for issue in validation["issues"]:
                print(f"     - {issue}")
            
            # 显示详细对比
            print(f"  📊 详细对比:")
            print(f"     配置中的必需参数: {validation['config_required']}")
            print(f"     实际的必需参数: {validation['actual_required']}")
            if validation['config_optional']:
                print(f"     配置中的可选参数: {validation['config_optional']}")
            if validation['actual_optional']:
                print(f"     实际的可选参数: {validation['actual_optional']}")
        
        results.append((tool_name, validation["valid"], validation["issues"]))
        print()
    
    # 检查管理器中配置但未注册的工具
    print("🔍 检查未注册的工具...")
    unregistered = set(manager.tool_mapping.keys()) - set(tool_registry.keys())
    if unregistered:
        print(f"⚠️ 以下工具在mcp_tool_manager中配置但未注册:")
        for tool_name in unregistered:
            print(f"  - {tool_name}")
            results.append((tool_name, False, ["工具未注册"]))
    else:
        print("✅ 所有配置的工具都已注册")
    print()
    
    # 总结
    print("="*80)
    print("验证总结")
    print("="*80)
    print()
    
    valid_count = sum(1 for _, valid, _ in results if valid)
    invalid_count = len(results) - valid_count
    
    print(f"总工具数: {len(results)}")
    print(f"✅ 配置正确: {valid_count}")
    print(f"❌ 配置错误: {invalid_count}")
    print()
    
    if invalid_count > 0:
        print("❌ 配置错误的工具:")
        for tool_name, valid, issues in results:
            if not valid:
                print(f"  - {tool_name}:")
                for issue in issues:
                    print(f"    • {issue}")
        print()
        return 1
    else:
        print("🎉 所有工具配置正确！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
