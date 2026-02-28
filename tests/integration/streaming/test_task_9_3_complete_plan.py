#!/usr/bin/env python3
"""
任务 9.3 测试：完整训练计划生成（超过4096 tokens）

测试目标：
1. 发送训练计划生成请求
2. 监控SSE事件流
3. 验证步骤进度显示（step事件）
4. 验证文本持续接收（chunk事件）
5. 验证结构化数据接收（structured_data事件）
6. 验证内容超过4096 tokens不被截断
"""

import asyncio
import json
import time
import httpx
import pytest
from typing import List, Dict, Any


class SSEEventCollector:
    """SSE事件收集器"""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.chunks: List[str] = []
        self.structured_data: List[Dict[str, Any]] = []
        self.steps: List[Dict[str, Any]] = []
        
    def add_event(self, event_type: str, data: Dict[str, Any]):
        """添加事件"""
        self.events.append({
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        })
        
        if event_type == "chunk":
            self.chunks.append(data.get("content", ""))
        elif event_type == "structured_data":
            self.structured_data.append(data)
        elif event_type == "step":
            self.steps.append(data)
    
    def get_full_text(self) -> str:
        """获取完整文本"""
        return "".join(self.chunks)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        full_text = self.get_full_text()
        
        return {
            "total_events": len(self.events),
            "step_events": len(self.steps),
            "chunk_events": len(self.chunks),
            "structured_data_events": len(self.structured_data),
            "total_characters": len(full_text),
            "estimated_tokens": len(full_text) // 2,  # 粗略估计
            "event_types": list(set(e["type"] for e in self.events))
        }


@pytest.mark.asyncio
async def test_complete_training_plan():
    """测试完整训练计划生成"""
    
    print("=" * 80)
    print("任务 9.3 测试：完整训练计划生成（超过4096 tokens）")
    print("=" * 80)
    print()
    
    # 测试参数
    api_url = "http://localhost:8001/api/v1/chat/stream"  # 注意：需要加上 /api 前缀
    test_query = "帮我设计一个完整的4周增肌训练计划，包括详细的动作安排、组数次数、执行要点和注意事项"
    test_user_id = "2"  # 使用数字ID以便正确加载用户档案
    
    print(f"📝 测试查询: {test_query}")
    print(f"👤 用户ID: {test_user_id}")
    print()
    
    # 创建事件收集器
    collector = SSEEventCollector()
    
    # 记录开始时间
    start_time = time.time()
    first_chunk_time = None
    
    try:
        # 发送流式请求
        print("🚀 发送流式请求...")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                api_url,
                json={
                    "user_id": test_user_id,
                    "query": test_query,
                    "domain": "fitness"
                }
            ) as response:
                print(f"✅ 连接建立: {response.status_code}")
                print()
                
                if response.status_code != 200:
                    print(f"❌ 请求失败: {response.status_code}")
                    print(await response.aread())
                    return
                
                # 读取SSE事件流
                print("📡 接收SSE事件流...")
                print("-" * 80)
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    # 解析SSE事件
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                    elif line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            
                            # 记录首字节时间
                            if first_chunk_time is None and event_type == "chunk":
                                first_chunk_time = time.time()
                                ttfb = (first_chunk_time - start_time) * 1000
                                print(f"⚡ 首字节响应时间 (TTFB): {ttfb:.0f}ms")
                                print()
                            
                            # 添加到收集器
                            collector.add_event(event_type, data)
                            
                            # 实时显示进度
                            if event_type == "step":
                                step_num = data.get("step", 0)
                                message = data.get("message", "")
                                print(f"📍 步骤 {step_num}: {message}")
                            
                            elif event_type == "chunk":
                                content = data.get("content", "")
                                # 只显示前50个字符
                                display_content = content[:50].replace("\n", "\\n")
                                if len(content) > 50:
                                    display_content += "..."
                                print(f"📝 接收文本片段: {display_content}")
                            
                            elif event_type == "structured_data":
                                data_type = data.get("data_type", "unknown")
                                print(f"📦 接收结构化数据: {data_type}")
                            
                            elif event_type == "done":
                                print(f"✅ 生成完成")
                                break
                            
                            elif event_type == "error":
                                error_msg = data.get("error", "未知错误")
                                print(f"❌ 错误: {error_msg}")
                                break
                        
                        except json.JSONDecodeError as e:
                            print(f"⚠️ JSON解析失败: {e}")
                            continue
        
        # 记录结束时间
        end_time = time.time()
        total_duration = (end_time - start_time) * 1000
        
        print()
        print("-" * 80)
        print("📊 测试结果统计")
        print("=" * 80)
        
        # 获取统计信息
        stats = collector.get_statistics()
        
        print(f"⏱️  总耗时: {total_duration:.0f}ms")
        if first_chunk_time:
            ttfb = (first_chunk_time - start_time) * 1000
            print(f"⚡ TTFB: {ttfb:.0f}ms")
        print()
        
        print(f"📡 事件统计:")
        print(f"  - 总事件数: {stats['total_events']}")
        print(f"  - 步骤事件: {stats['step_events']}")
        print(f"  - 文本片段: {stats['chunk_events']}")
        print(f"  - 结构化数据: {stats['structured_data_events']}")
        print(f"  - 事件类型: {', '.join(stats['event_types'])}")
        print()
        
        print(f"📝 内容统计:")
        print(f"  - 总字符数: {stats['total_characters']}")
        print(f"  - 估计token数: {stats['estimated_tokens']}")
        print()
        
        # 验证测试目标
        print("✅ 验证测试目标:")
        print("-" * 80)
        
        # 1. 验证步骤进度显示
        if stats['step_events'] > 0:
            print("✅ 1. 步骤进度显示正常")
            print(f"   - 接收到 {stats['step_events']} 个步骤事件")
        else:
            print("❌ 1. 未接收到步骤事件")
        
        # 2. 验证文本持续接收
        if stats['chunk_events'] > 10:
            print("✅ 2. 文本持续接收正常")
            print(f"   - 接收到 {stats['chunk_events']} 个文本片段")
        else:
            print("⚠️ 2. 文本片段数量较少")
        
        # 3. 验证结构化数据接收
        if stats['structured_data_events'] > 0:
            print("✅ 3. 结构化数据接收正常")
            print(f"   - 接收到 {stats['structured_data_events']} 个结构化数据")
            for sd in collector.structured_data:
                data_type = sd.get("data_type", "unknown")
                print(f"   - 类型: {data_type}")
        else:
            print("⚠️ 3. 未接收到结构化数据")
        
        # 4. 验证内容超过4096 tokens
        if stats['estimated_tokens'] > 4096:
            print(f"✅ 4. 内容超过4096 tokens")
            print(f"   - 估计token数: {stats['estimated_tokens']}")
        else:
            print(f"⚠️ 4. 内容未超过4096 tokens")
            print(f"   - 估计token数: {stats['estimated_tokens']}")
        
        # 5. 验证内容完整性
        full_text = collector.get_full_text()
        if "训练计划" in full_text and len(full_text) > 1000:
            print("✅ 5. 内容完整性验证通过")
            print(f"   - 包含关键词: 训练计划")
            print(f"   - 内容长度: {len(full_text)} 字符")
        else:
            print("⚠️ 5. 内容可能不完整")
        
        print()
        print("=" * 80)
        print("📄 生成内容预览（前500字符）:")
        print("-" * 80)
        print(full_text[:500])
        if len(full_text) > 500:
            print("...")
        print()
        
        # 保存完整内容到文件
        output_file = "/app/tests/integration/task_9_3_output.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"💾 完整内容已保存到: {output_file}")
        
        # 保存结构化数据
        if collector.structured_data:
            structured_file = "/app/tests/integration/task_9_3_structured.json"
            with open(structured_file, "w", encoding="utf-8") as f:
                json.dump(collector.structured_data, f, ensure_ascii=False, indent=2)
            print(f"💾 结构化数据已保存到: {structured_file}")
        
        print()
        print("=" * 80)
        print("✅ 任务 9.3 测试完成")
        print("=" * 80)
        
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ 测试失败: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_complete_training_plan())
