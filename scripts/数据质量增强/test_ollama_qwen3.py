#!/usr/bin/env python3
"""
测试本地Ollama Qwen3 8B是否可用

测试内容：
1. 检查Ollama服务是否运行
2. 检查qwen2.5:3b模型是否可用
3. 测试生成技术检查点的能力
"""

import asyncio
import json
import sys
from typing import Dict, Any


async def test_ollama_connection():
    """测试Ollama连接"""
    print("=" * 60)
    print("测试1：检查Ollama服务连接")
    print("=" * 60)
    
    try:
        from ollama import AsyncClient
        
        # Docker容器内需要连接到宿主机
        # Windows Docker Desktop: host.docker.internal
        # Linux: 172.17.0.1 或 host.docker.internal (需要额外配置)
        ollama_host = "http://host.docker.internal:11434"
        
        print(f"🔗 连接地址: {ollama_host}")
        client = AsyncClient(host=ollama_host)
        
        # 测试连接
        models = await client.list()
        print(f"✅ Ollama服务连接成功")
        print(f"📋 可用模型列表：")
        
        # 处理不同的响应格式
        if isinstance(models, dict):
            model_list = models.get('models', [])
        else:
            model_list = models.models if hasattr(models, 'models') else []
        
        for model in model_list:
            if isinstance(model, dict):
                print(f"   - {model.get('name', model.get('model', 'unknown'))}")
            else:
                print(f"   - {model.name if hasattr(model, 'name') else model.model}")
        
        return True, client
    except Exception as e:
        print(f"❌ Ollama服务连接失败: {e}")
        print(f"💡 请确保Ollama服务正在运行")
        print(f"💡 Windows Docker Desktop应该自动支持host.docker.internal")
        return False, None


async def test_qwen3_model(client):
    """测试qwen3:8b模型"""
    print("\n" + "=" * 60)
    print("测试2：检查qwen3:8b模型")
    print("=" * 60)
    
    try:
        # 简单测试
        response = await client.generate(
            model='qwen3:8b',
            prompt='你好，请回复"测试成功"',
            options={'temperature': 0.3}
        )
        
        print(f"✅ qwen3:8b模型可用")
        print(f"📝 测试响应: {response['response'][:100]}")
        return True
    except Exception as e:
        print(f"❌ qwen3:8b模型不可用: {e}")
        print(f"💡 请运行: ollama pull qwen3:8b")
        return False


async def test_technique_checkpoint_generation(client):
    """测试生成技术检查点"""
    print("\n" + "=" * 60)
    print("测试3：测试生成技术检查点")
    print("=" * 60)
    
    # 测试动作信息
    exercise_info = {
        "name": "杠铃深蹲",
        "description": "双脚与肩同宽站立，杠铃放在斜方肌上部，保持核心稳定，屈髋屈膝下蹲至大腿平行地面，然后站起",
        "force": "push",
        "mechanic": "compound",
        "equipment": "杠铃"
    }
    
    prompt = f"""
你是一位专业的健身教练。请基于以下动作信息，生成3-5个关键的技术检查点。

动作名称：{exercise_info['name']}
动作描述：{exercise_info['description']}
力量类型：{exercise_info['force']}
力学特性：{exercise_info['mechanic']}
所需器械：{exercise_info['equipment']}

要求：
1. 技术检查点应该简洁、专业、可操作
2. 包含起始姿势、动作过程、结束姿势的关键要点
3. 强调安全性和正确发力
4. 以JSON数组格式输出，例如：["起始：...", "动作：...", "结束：..."]

请直接输出JSON数组，不要其他解释：
"""
    
    try:
        print(f"🔄 正在为 {exercise_info['name']} 生成技术检查点...")
        
        response = await client.generate(
            model='qwen3:8b',
            prompt=prompt,
            options={'temperature': 0.3}
        )
        
        # 解析响应
        checkpoints_text = response['response'].strip()
        print(f"\n📝 LLM原始输出：")
        print(checkpoints_text)
        
        # 尝试解析JSON
        try:
            checkpoints = json.loads(checkpoints_text)
            print(f"\n✅ JSON解析成功")
            print(f"📋 生成的技术检查点：")
            for i, checkpoint in enumerate(checkpoints, 1):
                print(f"   {i}. {checkpoint}")
            return True
        except json.JSONDecodeError as e:
            print(f"\n⚠️ JSON解析失败: {e}")
            print(f"💡 LLM输出格式不正确，可能需要调整prompt")
            
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\[.*\]', checkpoints_text, re.DOTALL)
            if json_match:
                try:
                    checkpoints = json.loads(json_match.group())
                    print(f"\n✅ 提取JSON成功")
                    print(f"📋 生成的技术检查点：")
                    for i, checkpoint in enumerate(checkpoints, 1):
                        print(f"   {i}. {checkpoint}")
                    return True
                except:
                    pass
            
            return False
            
    except Exception as e:
        print(f"❌ 生成技术检查点失败: {e}")
        return False


async def test_batch_generation(client):
    """测试批量生成能力"""
    print("\n" + "=" * 60)
    print("测试4：测试批量生成能力（3个动作）")
    print("=" * 60)
    
    exercises = [
        {"name": "哑铃弯举", "description": "站立，双手持哑铃，肘关节固定，屈肘将哑铃举至肩部"},
        {"name": "俯卧撑", "description": "俯卧支撑，双手与肩同宽，屈肘下降至胸部接近地面，然后推起"},
        {"name": "平板支撑", "description": "前臂支撑，保持身体呈一条直线，核心收紧"}
    ]
    
    success_count = 0
    
    for i, exercise in enumerate(exercises, 1):
        print(f"\n🔄 [{i}/3] 生成 {exercise['name']} 的技术检查点...")
        
        prompt = f"""
你是一位专业的健身教练。请为"{exercise['name']}"生成3个关键技术检查点。

动作描述：{exercise['description']}

要求：以JSON数组格式输出，例如：["起始：...", "动作：...", "结束：..."]

请直接输出JSON数组：
"""
        
        try:
            response = await client.generate(
                model='qwen3:8b',
                prompt=prompt,
                options={'temperature': 0.3}
            )
            
            checkpoints_text = response['response'].strip()
            
            # 尝试解析JSON
            try:
                checkpoints = json.loads(checkpoints_text)
                print(f"   ✅ 成功生成 {len(checkpoints)} 个检查点")
                success_count += 1
            except:
                # 尝试提取JSON
                import re
                json_match = re.search(r'\[.*\]', checkpoints_text, re.DOTALL)
                if json_match:
                    checkpoints = json.loads(json_match.group())
                    print(f"   ✅ 成功生成 {len(checkpoints)} 个检查点（提取JSON）")
                    success_count += 1
                else:
                    print(f"   ⚠️ JSON解析失败")
                    
        except Exception as e:
            print(f"   ❌ 生成失败: {e}")
    
    print(f"\n📊 批量生成结果: {success_count}/{len(exercises)} 成功")
    return success_count == len(exercises)


async def main():
    """主测试流程"""
    print("\n🚀 开始测试Ollama Qwen3 8B集成")
    print("=" * 60)
    
    # 测试1：连接
    connected, client = await test_ollama_connection()
    if not connected:
        print("\n❌ 测试失败：无法连接到Ollama服务")
        sys.exit(1)
    
    # 测试2：模型
    model_available = await test_qwen3_model(client)
    if not model_available:
        print("\n❌ 测试失败：qwen2.5:3b模型不可用")
        sys.exit(1)
    
    # 测试3：单个生成
    single_success = await test_technique_checkpoint_generation(client)
    
    # 测试4：批量生成
    batch_success = await test_batch_generation(client)
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"✅ Ollama服务连接: 成功")
    print(f"✅ qwen3:8b模型: 可用")
    print(f"{'✅' if single_success else '⚠️'} 单个生成测试: {'成功' if single_success else '需要优化'}")
    print(f"{'✅' if batch_success else '⚠️'} 批量生成测试: {'成功' if batch_success else '需要优化'}")
    
    if single_success and batch_success:
        print("\n🎉 所有测试通过！可以开始集成使用")
        print("\n💡 下一步：")
        print("   1. 开始实施任务1：创建数据补充脚本框架")
        print("   2. 实施任务2.4：集成Ollama生成技术检查点")
    else:
        print("\n⚠️ 部分测试未通过，但基本功能可用")
        print("💡 建议：优化prompt以提高JSON输出的稳定性")


if __name__ == "__main__":
    asyncio.run(main())
