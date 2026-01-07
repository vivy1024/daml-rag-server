#!/usr/bin/env python3
"""
快速测试Ollama Qwen3 8B
"""

import asyncio
import json
from ollama import AsyncClient


async def main():
    print("🚀 快速测试Ollama Qwen3 8B")
    
    # 连接到宿主机Ollama
    client = AsyncClient(host="http://host.docker.internal:11434")
    
    # 测试生成技术检查点
    prompt = """
你是一位专业的健身教练。请为"杠铃深蹲"生成3个关键技术检查点。

要求：以JSON数组格式输出，例如：["起始：...", "动作：...", "结束：..."]

请直接输出JSON数组：
"""
    
    print("🔄 生成技术检查点...")
    response = await client.generate(
        model='qwen3:8b',
        prompt=prompt,
        options={'temperature': 0.3}
    )
    
    checkpoints_text = response['response'].strip()
    print(f"\n📝 LLM输出：\n{checkpoints_text}")
    
    # 解析JSON
    checkpoints = json.loads(checkpoints_text)
    print(f"\n✅ 成功生成 {len(checkpoints)} 个检查点")
    for i, cp in enumerate(checkpoints, 1):
        print(f"   {i}. {cp}")
    
    print("\n🎉 测试成功！Ollama Qwen3 8B可以用于生成技术检查点")


if __name__ == "__main__":
    asyncio.run(main())
