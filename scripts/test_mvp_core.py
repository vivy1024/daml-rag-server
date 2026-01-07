#!/usr/bin/env python3
"""MVP核心功能测试脚本"""
import asyncio
import sys
import traceback

async def test_workflow():
    """测试完整工作流"""
    try:
        print("=" * 60)
        print("🚀 开始测试DAML-RAG工作流")
        print("=" * 60)
        
        # 测试1: 导入模块
        print("\n[1/3] 测试模块导入...")
        from src.applications.fitness.workflow_executor import execute_eleven_step_workflow
        print("✅ 模块导入成功")
        
        # 测试2: 执行简单对话
        print("\n[2/3] 测试简单对话...")
        result = await execute_eleven_step_workflow(
            query_text="你好",
            user_id="1",
            domain="fitness",
            user_profile=None,
            session_id="test_session_1"
        )
        print(f"✅ 简单对话成功")
        print(f"   响应长度: {len(str(result))} 字符")
        
        # 测试3: 测试训练计划生成
        print("\n[3/3] 测试训练计划生成...")
        result = await execute_eleven_step_workflow(
            query_text="帮我设计一个增肌训练计划",
            user_id="1",
            domain="fitness",
            user_profile=None,
            session_id="test_session_2"
        )
        
        # 提取响应
        eleven_step_data = result.get("eleven_step_workflow", {})
        final_response = eleven_step_data.get("final_response", "")
        
        print(f"✅ 训练计划生成成功")
        print(f"   响应长度: {len(final_response)} 字符")
        print(f"   使用模型: {eleven_step_data.get('model_selected', 'unknown')}")
        print(f"   处理时间: {result.get('processing_time', 0):.2f}秒")
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！系统可以上线")
        print("=" * 60)
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试失败: {str(e)}")
        print("=" * 60)
        print("\n详细错误信息:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_workflow())
    sys.exit(0 if success else 1)
