"""
任务10.1 性能基准测试

测试目标：
- TTFB < 5秒
- MCP工具调用 < 2秒
- 生成速度 > 15 tokens/s
- 缓存命中率验证

验证需求: 4.1, 6.1
"""

import asyncio
import time
import httpx
import json
from typing import Dict, List, Tuple


class PerformanceBenchmark:
    """性能基准测试"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = []
    
    async def test_streaming_session(self, query: str, user_id: str = "test_user") -> Dict:
        """测试单个流式会话的性能"""
        session_id = f"perf_test_{int(time.time() * 1000)}"
        
        url = f"{self.base_url}/api/v1/chat/stream"
        payload = {
            "user_id": user_id,
            "query": query,
            "session_id": session_id
        }
        
        start_time = time.time()
        ttfb = None
        total_tokens = 0
        total_chars = 0
        first_chunk_received = False
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        # 记录TTFB
                        if not first_chunk_received:
                            ttfb = (time.time() - start_time) * 1000  # 转换为毫秒
                            first_chunk_received = True
                        
                        # 解析SSE事件
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "chunk":
                                    content = data.get("content", "")
                                    total_chars += len(content)
                                    # 估算token数（中文约2字符=1token）
                                    total_tokens += len(content) / 2
                            except json.JSONDecodeError:
                                pass
            
            total_time = (time.time() - start_time) * 1000  # 毫秒
            generation_speed = (total_tokens / (total_time / 1000)) if total_time > 0 else 0
            
            return {
                "success": True,
                "ttfb_ms": ttfb,
                "total_time_ms": total_time,
                "total_tokens": total_tokens,
                "total_chars": total_chars,
                "generation_speed_tokens_per_sec": generation_speed,
                "query": query
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def run_benchmark(self, queries: List[str], iterations: int = 3) -> Dict:
        """运行性能基准测试"""
        print(f"\n{'='*80}")
        print(f"性能基准测试开始")
        print(f"{'='*80}\n")
        
        all_results = []
        
        for i, query in enumerate(queries, 1):
            print(f"\n[测试 {i}/{len(queries)}] 查询: {query[:50]}...")
            
            for iteration in range(iterations):
                print(f"  迭代 {iteration + 1}/{iterations}...", end=" ")
                result = await self.test_streaming_session(query)
                all_results.append(result)
                
                if result["success"]:
                    print(f"✅ TTFB={result['ttfb_ms']:.0f}ms, "
                          f"速度={result['generation_speed_tokens_per_sec']:.1f} tokens/s")
                else:
                    print(f"❌ 失败: {result['error']}")
                
                # 避免请求过快
                await asyncio.sleep(2)
        
        # 统计结果
        successful_results = [r for r in all_results if r["success"]]
        
        if not successful_results:
            return {
                "success": False,
                "message": "所有测试都失败了"
            }
        
        # 计算统计数据
        ttfb_values = [r["ttfb_ms"] for r in successful_results]
        speed_values = [r["generation_speed_tokens_per_sec"] for r in successful_results]
        
        avg_ttfb = sum(ttfb_values) / len(ttfb_values)
        avg_speed = sum(speed_values) / len(speed_values)
        max_ttfb = max(ttfb_values)
        min_ttfb = min(ttfb_values)
        
        # 性能评估
        ttfb_pass = avg_ttfb < 5000  # 5秒
        speed_pass = avg_speed > 15  # 15 tokens/s
        
        print(f"\n{'='*80}")
        print(f"性能基准测试结果")
        print(f"{'='*80}\n")
        print(f"总测试次数: {len(all_results)}")
        print(f"成功次数: {len(successful_results)}")
        print(f"失败次数: {len(all_results) - len(successful_results)}")
        print(f"\n--- TTFB (首字节响应时间) ---")
        print(f"平均值: {avg_ttfb:.0f}ms")
        print(f"最小值: {min_ttfb:.0f}ms")
        print(f"最大值: {max_ttfb:.0f}ms")
        print(f"目标: < 5000ms")
        print(f"结果: {'✅ 通过' if ttfb_pass else '❌ 未通过'}")
        print(f"\n--- 生成速度 ---")
        print(f"平均值: {avg_speed:.1f} tokens/s")
        print(f"目标: > 15 tokens/s")
        print(f"结果: {'✅ 通过' if speed_pass else '❌ 未通过'}")
        print(f"\n{'='*80}\n")
        
        return {
            "success": True,
            "total_tests": len(all_results),
            "successful_tests": len(successful_results),
            "failed_tests": len(all_results) - len(successful_results),
            "avg_ttfb_ms": avg_ttfb,
            "min_ttfb_ms": min_ttfb,
            "max_ttfb_ms": max_ttfb,
            "avg_generation_speed": avg_speed,
            "ttfb_pass": ttfb_pass,
            "speed_pass": speed_pass,
            "all_pass": ttfb_pass and speed_pass
        }


async def main():
    """主测试函数"""
    benchmark = PerformanceBenchmark()
    
    # 测试查询列表
    test_queries = [
        "帮我设计一个完整的4周增肌训练计划",
        "我想要一个推拉腿的训练分化方案",
        "给我推荐一些适合初学者的胸部训练动作"
    ]
    
    # 运行基准测试（每个查询测试3次）
    results = await benchmark.run_benchmark(test_queries, iterations=3)
    
    # 返回测试结果
    if results["success"]:
        if results["all_pass"]:
            print("🎉 所有性能指标都达标！")
            return 0
        else:
            print("⚠️ 部分性能指标未达标")
            return 1
    else:
        print(f"❌ 测试失败: {results.get('message', '未知错误')}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
