#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试DAG执行是否正常

验证FindSimilarTrainingCasesTool修复后，DAG编排器能否正常工作
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.applications.fitness.mcp_tools.registry import MCPToolRegistry
from src.applications.fitness.mcp_tools import initialize_all_tools


async def test_tool_registration():
    """测试工具注册"""
    print("=" * 60)
    print("测试1: 工具注册")
    print("=" * 60)
    
    try:
        registry = MCPToolRegistry()
        initialize_all_tools(registry, None, None, None, None, None)
        
        # list_tools返回的是ToolMetadata列表，不是工具名称列表
        tool_metadatas = registry.list_tools()
        print(f"✅ 成功注册 {len(tool_metadatas)} 个工具")
        print("\n工具列表:")
        for i, metadata in enumerate(tool_metadatas, 1):
            print(f"  {i:2d}. {metadata.name:40s} [{metadata.category:10s}] {metadata.complexity}")
        
        # 特别检查FindSimilarTrainingCasesTool
        tool_names = [m.name for m in tool_metadatas]
        if "find_similar_training_cases" in tool_names:
            print("\n✅ FindSimilarTrainingCasesTool 已成功注册")
            tool = registry.get_tool("find_similar_training_cases")
            
            # 验证抽象方法
            input_schema = tool.get_input_schema()
            output_schema = tool.get_output_schema()
            print(f"   - 输入Schema: {input_schema.__name__}")
            print(f"   - 输出Schema: {output_schema.__name__}")
        else:
            print("\n❌ FindSimilarTrainingCasesTool 未注册")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 工具注册失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_instantiation():
    """测试工具实例化"""
    print("\n" + "=" * 60)
    print("测试2: 工具实例化")
    print("=" * 60)
    
    try:
        from src.applications.fitness.mcp_tools.find_similar_training_cases import (
            FindSimilarTrainingCasesTool,
            FindSimilarTrainingCasesInput,
            FindSimilarTrainingCasesOutput
        )
        
        # 创建工具实例
        tool = FindSimilarTrainingCasesTool(backend_client=None, vector_store=None)
        print(f"✅ 工具实例创建成功: {tool.get_name()}")
        
        # 验证Schema
        input_schema = tool.get_input_schema()
        output_schema = tool.get_output_schema()
        print(f"✅ 输入Schema: {input_schema.__name__}")
        print(f"✅ 输出Schema: {output_schema.__name__}")
        
        # 验证元数据
        metadata = tool.get_metadata()
        print(f"✅ 元数据: category={metadata.category}, complexity={metadata.complexity}")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具实例化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("\n🧪 开始测试DAG执行修复\n")
    
    # 测试1: 工具注册
    test1_passed = await test_tool_registration()
    
    # 测试2: 工具实例化
    test2_passed = await test_tool_instantiation()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"测试1 (工具注册):   {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"测试2 (工具实例化): {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！DAG执行修复成功！")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
