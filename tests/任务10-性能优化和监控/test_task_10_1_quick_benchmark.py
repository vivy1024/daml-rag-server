"""
任务10.1 快速性能基准测试

测试目标：
- TTFB < 5秒
- 生成速度 > 15 tokens/s

验证需求: 4.1, 6.1
"""

import asyncio
import time
import httpx
import json


async def test_single_session():
    """测试单个流式会话"""
    url = "http://localhost:8001/api/v1/chat/stream"
    payload = {
        "user_id": "test_user",
        "query": "帮我设计一个完整的4周增肌训练计划",
        "session_id": f"perf_test_{int(time.time() * 1000)}"
    }
    
    start_time = time.time()
    ttfb = None
    total_tokens = 0
    first_chunk = False
    
    print(f"\n{'='*80}")
    print(f"开始性能测试...")
    print(f"{'='*80}\n")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if not first_chunk:
                        ttfb = (time.time() - start_time) * 1000
                        first_chunk = True
                        print(f"✅ 首字节响应时间 (TTFB): {ttfb:.0f}ms")
                    
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "chunk":
                                content = data.get("content", "")
                                total_tokens += len(content) / 2
                        except:
                            pass
        
        total_time = (time.time() - start_time) * 1000
        speed = (total_tokens / (total_time / 1000)) if total_time > 0 else 0
        
        print(f"✅ 总耗时: {total_time:.0f}ms")
        print(f"✅ 生成速度: {speed:.1f} tokens/s")
        print(f"✅ 总token数: {total_tokens:.0f}")
        
        # 性能评估
        ttfb_pass = ttfb < 5000
        speed_pass = speed > 15
        
        print(f"\n{'='*80}")
        print(f"性能评估结果")
        print(f"{'='*80}\n")
        print(f"TTFB < 5000ms: {'✅ 通过' if ttfb_pass else '❌ 未通过'} ({ttfb:.0f}ms)")
        print(f"速度 > 15 tokens/s: {'✅ 通过' if speed_pass else '❌ 未通过'} ({speed:.1f} tokens/s)")
        
        if ttfb_pass and speed_pass:
            print(f"\n🎉 所有性能指标都达标！")
            return 0
        else:
            print(f"\n⚠️ 部分性能指标未达标")
            return 1
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_single_session())
    exit(exit_code)
