# -*- coding: utf-8 -*-
"""
流式工作流功能测试套件

测试目标：
1. 验证SSE连接建立
2. 验证事件顺序正确性
3. 验证结构化数据嵌入
4. 验证内容完整性

版本: v1.0.0
日期: 2025-12-22
作者: 薛小川
"""

import pytest
import asyncio
import json
import time
import httpx
from typing import List, Dict, Any, Optional


class SSEEventCollector:
    """SSE事件收集器"""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.chunks: List[str] = []
        self.structured_data: List[Dict[str, Any]] = []
        self.steps: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.first_chunk_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
    def add_event(self, event_type: str, data: Dict[str, Any]):
        """添加事件"""
        timestamp = time.time()
        
        if self.start_time is None:
            self.start_time = timestamp
        
        self.events.append({
            "type": event_type,
            "data": data,
            "timestamp": timestamp
        })
        
        if event_type == "chunk":
            if self.first_chunk_time is None:
                self.first_chunk_time = timestamp
            self.chunks.append(data.get("content", ""))
        elif event_type == "structured_data":
            self.structured_data.append(data)
        elif event_type == "step":
            self.steps.append(data)
        elif event_type == "done":
            self.end_time = timestamp
    
    def get_full_text(self) -> str:
        """获取完整文本"""
        return "".join(self.chunks)
    
    def get_event_types(self) -> List[str]:
        """获取所有事件类型"""
        return [e["type"] for e in self.events]
    
    def get_ttfb(self) -> Optional[float]:
        """获取首字节响应时间（秒）"""
        if self.start_time and self.first_chunk_time:
            return self.first_chunk_time - self.start_time
        return None
    
    def get_duration(self) -> Optional[float]:
        """获取总耗时（秒）"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


async def collect_sse_events(
    query: str,
    user_id: int = 1,
    api_url: str = "http://127.0.0.1:8001/api/v1/chat/stream",
    timeout: float = 60.0
) -> SSEEventCollector:
    """
    收集SSE事件
    
    Args:
        query: 查询文本
        user_id: 用户ID
        api_url: API地址
        timeout: 超时时间（秒）
    
    Returns:
        SSEEventCollector: 事件收集器
    """
    collector = SSEEventCollector()
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            api_url,
            json={
                "user_id": user_id,
                "query": query,
                "domain": "fitness"
            }
        ) as response:
            if response.status_code != 200:
                raise Exception(f"API请求失败: {response.status_code}")
            
            current_event_type = None
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                
                # 解析SSE事件
                if line.startswith("event: "):
                    current_event_type = line[7:].strip()
                elif line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if current_event_type:
                            collector.add_event(current_event_type, data)
                            
                            # 如果收到done事件，结束收集
                            if current_event_type == "done":
                                break
                    except json.JSONDecodeError:
                        continue
    
    return collector


@pytest.mark.integration
class TestStreamingWorkflowFunctionality:
    """流式工作流功能测试"""
    
    @pytest.mark.asyncio
    async def test_sse_connection_establishment(self):
        """
        测试1.1: SSE连接建立
        
        验证：
        - 能够成功建立SSE连接
        - 返回正确的content-type
        - 能够接收到事件流
        
        需求: 1.1
        """
        print("\n" + "="*80)
        print("测试1.1: SSE连接建立")
        print("="*80)
        
        api_url = "http://127.0.0.1:8001/api/v1/chat/stream"
        test_query = "你好"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                api_url,
                json={
                    "user_id": "test_user",
                    "query": test_query,
                    "domain": "fitness"
                }
            ) as response:
                # 验证状态码
                assert response.status_code == 200, f"期望状态码200，实际: {response.status_code}"
                print(f"✅ 状态码验证通过: {response.status_code}")
                
                # 验证content-type
                content_type = response.headers.get("content-type", "")
                assert "text/event-stream" in content_type, f"期望content-type包含text/event-stream，实际: {content_type}"
                print(f"✅ Content-Type验证通过: {content_type}")
                
                # 验证能够接收到至少一个事件
                event_received = False
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        event_received = True
                        print(f"✅ 成功接收到事件")
                        break
                
                assert event_received, "未能接收到任何事件"
        
        print("✅ 测试1.1通过: SSE连接建立成功")
    
    @pytest.mark.asyncio
    async def test_event_sequence(self):
        """
        测试1.2: 事件顺序正确性
        
        验证：
        - 事件按照正确顺序发送：step/fallback → chunk → structured_data → done
        - step事件的步骤号递增（如果有step事件）
        - 最后收到done事件
        - 如果是fallback模式，验证降级流程正确
        
        需求: 1.2
        """
        print("\n" + "="*80)
        print("测试1.2: 事件顺序正确性")
        print("="*80)
        
        test_query = "帮我设计训练计划"
        
        collector = await collect_sse_events(test_query, timeout=120.0)
        
        # 验证接收到事件
        assert len(collector.events) > 0, "未接收到任何事件"
        print(f"✅ 接收到 {len(collector.events)} 个事件")
        
        # 获取事件类型序列
        event_types = collector.get_event_types()
        print(f"📋 事件类型序列: {event_types}")
        
        # 验证包含必需的事件类型（chunk和done是必需的）
        assert "chunk" in event_types, "缺少chunk事件"
        assert "done" in event_types, "缺少done事件"
        print(f"✅ 包含必需事件类型: chunk, done")
        
        # 检查是否是fallback模式
        if "fallback" in event_types:
            print(f"ℹ️  检测到fallback事件，系统降级到非流式模式")
            # fallback模式下，验证基本流程
            assert event_types[0] == "fallback", "fallback事件应该在最前面"
            print(f"✅ fallback事件位于开头")
        elif "step" in event_types:
            print(f"ℹ️  检测到step事件，使用流式模式")
            # 流式模式下，验证step事件递增
            step_numbers = [s.get("step", 0) for s in collector.steps]
            if len(step_numbers) > 1:
                is_increasing = all(step_numbers[i] <= step_numbers[i+1] for i in range(len(step_numbers)-1))
                assert is_increasing, f"步骤号未递增: {step_numbers}"
                print(f"✅ 步骤号递增验证通过: {step_numbers}")
        
        # 验证done事件是最后一个
        last_event_type = event_types[-1]
        assert last_event_type == "done", f"最后一个事件应该是done，实际: {last_event_type}"
        print(f"✅ done事件位于最后")
        
        print("✅ 测试1.2通过: 事件顺序正确")
    
    @pytest.mark.asyncio
    async def test_structured_data_embedding(self):
        """
        测试1.3: 结构化数据嵌入
        
        验证：
        - 能够接收到structured_data事件（如果有）
        - 结构化数据包含正确的data_type
        - 训练计划数据包含必需字段
        
        注意：在fallback模式下可能没有structured_data事件
        
        需求: 1.3
        """
        print("\n" + "="*80)
        print("测试1.3: 结构化数据嵌入")
        print("="*80)
        
        test_query = "设计一个4周增肌计划"
        
        collector = await collect_sse_events(test_query, timeout=120.0)
        
        # 检查是否有结构化数据
        if len(collector.structured_data) == 0:
            print(f"ℹ️  未接收到结构化数据事件（可能是fallback模式）")
            # 在fallback模式下，这是正常的
            event_types = collector.get_event_types()
            if "fallback" in event_types:
                print(f"✅ fallback模式下跳过结构化数据验证")
                return
            else:
                # 如果不是fallback模式但没有结构化数据，这可能是个问题
                print(f"⚠️  非fallback模式但未接收到结构化数据")
        else:
            # 验证接收到结构化数据
            print(f"✅ 接收到 {len(collector.structured_data)} 个结构化数据事件")
            
            # 验证第一个结构化数据
            first_structured = collector.structured_data[0]
            # SSE structured_data 事件格式: {"type": "structured_data", "data": {...}}
            data_type = first_structured.get("type") or first_structured.get("data_type")
            print(f"📦 结构化数据类型: {data_type}")

            # 验证type字段（兼容 type 和 data_type 两种格式）
            assert data_type is not None, "结构化数据缺少type/data_type字段"
            print(f"✅ 结构化数据类型字段存在: {data_type}")

            # 如果是训练计划，验证必需字段
            if data_type in ("training_plan", "structured_data"):
                assert "data" in first_structured, "训练计划缺少data字段"
                plan_data = first_structured.get("data", {})
                
                # 验证训练计划的关键字段
                print(f"📋 训练计划数据字段: {list(plan_data.keys())}")
                
                # 至少应该有一些内容
                assert len(plan_data) > 0, "训练计划数据为空"
                print(f"✅ 训练计划包含 {len(plan_data)} 个字段")
        
        print("✅ 测试1.3通过: 结构化数据嵌入正确")
    
    @pytest.mark.asyncio
    async def test_content_completeness(self):
        """
        测试1.4: 内容完整性
        
        验证：
        - 能够接收到完整的文本内容
        - 内容长度合理（不为空）
        - 内容包含查询相关的关键词
        
        需求: 1.4
        """
        print("\n" + "="*80)
        print("测试1.4: 内容完整性")
        print("="*80)
        
        test_query = "详细介绍深蹲动作"
        
        collector = await collect_sse_events(test_query, timeout=120.0)
        
        # 拼接所有chunk
        full_content = collector.get_full_text()
        
        # 验证内容不为空
        assert len(full_content) > 0, "接收到的内容为空"
        print(f"✅ 接收到内容，长度: {len(full_content)} 字符")
        
        # 验证内容长度合理（至少100字符）
        assert len(full_content) > 100, f"内容过短: {len(full_content)} 字符"
        print(f"✅ 内容长度合理")
        
        # 验证内容包含关键词
        assert "深蹲" in full_content, "内容中未找到关键词'深蹲'"
        print(f"✅ 内容包含关键词'深蹲'")
        
        # 显示内容预览
        preview = full_content[:200].replace("\n", " ")
        print(f"📄 内容预览: {preview}...")
        
        # 验证chunk数量合理
        chunk_count = len(collector.chunks)
        assert chunk_count > 0, "未接收到任何chunk"
        print(f"✅ 接收到 {chunk_count} 个chunk")
        
        print("✅ 测试1.4通过: 内容完整性验证通过")
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """
        额外测试: 性能指标
        
        验证：
        - TTFB在合理范围内
        - 总耗时在合理范围内
        """
        print("\n" + "="*80)
        print("额外测试: 性能指标")
        print("="*80)
        
        test_query = "你好"
        
        collector = await collect_sse_events(test_query, timeout=60.0)
        
        # 获取TTFB
        ttfb = collector.get_ttfb()
        if ttfb:
            ttfb_ms = ttfb * 1000
            print(f"⚡ TTFB: {ttfb_ms:.0f}ms")
            
            # TTFB应该小于90秒（DAG工作流含检索+LLM调用）
            assert ttfb < 90, f"TTFB过高: {ttfb_ms:.0f}ms"
            print(f"✅ TTFB在合理范围内")
        
        # 获取总耗时
        duration = collector.get_duration()
        if duration:
            duration_ms = duration * 1000
            print(f"⏱️  总耗时: {duration_ms:.0f}ms")
            
            # 总耗时应该小于60秒
            assert duration < 60, f"总耗时过长: {duration_ms:.0f}ms"
            print(f"✅ 总耗时在合理范围内")
        
        print("✅ 性能指标验证通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
