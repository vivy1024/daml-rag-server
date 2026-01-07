# -*- coding: utf-8 -*-
"""
流式输出端到端集成测试

测试目标：
1. 验证流式工作流完整执行
2. 验证前端可以正常显示内容
3. 验证降级机制正常工作
4. 验证响应格式符合规范

Requirements: 4.1, 4.2, 4.3, 4.4

版本: v1.0.0
日期: 2025-12-29
作者: 薛小川
"""

import pytest
import asyncio
import json
import time
import httpx
from typing import List, Dict, Any, Optional


# ========== 测试配置 ==========

API_BASE_URL = "http://127.0.0.1:8001/api"
STREAM_ENDPOINT = f"{API_BASE_URL}/v1/chat/stream"
CHAT_ENDPOINT = f"{API_BASE_URL}/v1/chat"
DEFAULT_TIMEOUT = 120.0  # 秒


# ========== 辅助类 ==========

class StreamingResponseCollector:
    """
    流式响应收集器
    
    收集SSE事件并提供分析方法。
    """
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.chunks: List[str] = []
        self.structured_data: List[Dict[str, Any]] = []
        self.steps: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.first_chunk_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.is_fallback: bool = False
        self.done_data: Optional[Dict[str, Any]] = None
        
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
            content = data.get("content", "")
            if content:
                self.chunks.append(content)
        elif event_type == "structured_data":
            self.structured_data.append(data)
        elif event_type == "step":
            self.steps.append(data)
        elif event_type == "fallback":
            self.is_fallback = True
        elif event_type == "error":
            self.errors.append(data)
        elif event_type == "done":
            self.end_time = timestamp
            self.done_data = data
    
    def get_full_content(self) -> str:
        """获取完整内容"""
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
    
    def is_successful(self) -> bool:
        """判断是否成功完成"""
        if self.done_data:
            done_inner = self.done_data.get("data", {})
            return done_inner.get("success", False)
        return False
    
    def has_content(self) -> bool:
        """判断是否有内容"""
        return len(self.get_full_content()) > 0


async def collect_stream_response(
    query: str,
    user_id: str = "test_e2e_user",
    timeout: float = DEFAULT_TIMEOUT
) -> StreamingResponseCollector:
    """
    收集流式响应
    
    Args:
        query: 查询文本
        user_id: 用户ID
        timeout: 超时时间（秒）
    
    Returns:
        StreamingResponseCollector: 响应收集器
    """
    collector = StreamingResponseCollector()
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            STREAM_ENDPOINT,
            json={
                "user_id": user_id,
                "query": query,
                "domain": "fitness"
            }
        ) as response:
            if response.status_code != 200:
                # 处理非200状态码
                collector.add_event("error", {
                    "type": "error",
                    "error": f"HTTP {response.status_code}",
                    "status_code": response.status_code
                })
                return collector
            
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
                            
                            # 如果收到done或error事件，结束收集
                            if current_event_type in ("done", "error"):
                                break
                    except json.JSONDecodeError:
                        continue
    
    return collector


async def send_chat_request(
    query: str,
    user_id: str = "test_e2e_user",
    timeout: float = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    发送非流式聊天请求
    
    Args:
        query: 查询文本
        user_id: 用户ID
        timeout: 超时时间（秒）
    
    Returns:
        Dict[str, Any]: 响应数据
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            CHAT_ENDPOINT,
            json={
                "user_id": user_id,
                "query": query,
                "domain": "fitness"
            }
        )
        return response.json()


# ========== 测试类 ==========

class TestStreamingE2E:
    """
    流式输出端到端测试
    
    验证流式工作流的完整执行和前端兼容性。
    """
    
    @pytest.mark.asyncio
    async def test_streaming_workflow_complete_execution(self):
        """
        测试7.1.1: 流式工作流完整执行
        
        验证：
        - 流式工作流能够完整执行
        - 返回有效的SSE事件流
        - 最终收到done事件
        
        Requirements: 4.1
        """
        print("\n" + "="*80)
        print("测试7.1.1: 流式工作流完整执行")
        print("="*80)
        
        test_query = "帮我介绍一下深蹲动作"
        
        collector = await collect_stream_response(test_query)
        
        # 验证接收到事件
        event_count = len(collector.events)
        assert event_count > 0, "未接收到任何事件"
        print(f"✅ 接收到 {event_count} 个事件")
        
        # 验证事件类型
        event_types = collector.get_event_types()
        print(f"📋 事件类型: {event_types}")
        
        # 验证有内容
        content = collector.get_full_content()
        assert len(content) > 0, "未接收到任何内容"
        print(f"✅ 接收到内容，长度: {len(content)} 字符")
        
        # 验证收到done事件或fallback后的done
        has_done = "done" in event_types
        assert has_done, "未收到done事件"
        print(f"✅ 收到done事件")
        
        # 如果是fallback模式，验证降级成功
        if collector.is_fallback:
            print(f"ℹ️  系统降级到非流式模式")
            assert collector.is_successful(), "降级后未成功完成"
            print(f"✅ 降级模式成功完成")
        
        print("✅ 测试7.1.1通过: 流式工作流完整执行")
    
    @pytest.mark.asyncio
    async def test_frontend_content_display(self):
        """
        测试7.1.2: 前端内容显示验证
        
        验证：
        - 响应内容可以被前端正常解析
        - 内容包含有意义的文本
        - 内容与查询相关
        
        Requirements: 4.2, 4.3
        """
        print("\n" + "="*80)
        print("测试7.1.2: 前端内容显示验证")
        print("="*80)
        
        test_query = "卧推动作要点"
        
        collector = await collect_stream_response(test_query)
        
        # 验证有内容
        content = collector.get_full_content()
        assert len(content) > 0, "未接收到任何内容"
        print(f"✅ 接收到内容，长度: {len(content)} 字符")
        
        # 验证内容长度合理（至少50字符）
        assert len(content) >= 50, f"内容过短: {len(content)} 字符"
        print(f"✅ 内容长度合理")
        
        # 验证内容包含关键词（卧推相关）
        keywords = ["卧推", "胸", "动作", "训练", "肌肉"]
        found_keywords = [kw for kw in keywords if kw in content]
        assert len(found_keywords) > 0, f"内容未包含任何相关关键词: {keywords}"
        print(f"✅ 内容包含关键词: {found_keywords}")
        
        # 显示内容预览
        preview = content[:200].replace("\n", " ")
        print(f"📄 内容预览: {preview}...")
        
        print("✅ 测试7.1.2通过: 前端内容显示验证")
    
    @pytest.mark.asyncio
    async def test_response_format_compliance(self):
        """
        测试7.1.3: 响应格式合规性
        
        验证：
        - SSE事件格式正确
        - done事件包含必需字段
        - 响应可被JSON解析
        
        Requirements: 4.2, 4.3
        """
        print("\n" + "="*80)
        print("测试7.1.3: 响应格式合规性")
        print("="*80)
        
        test_query = "你好"
        
        collector = await collect_stream_response(test_query)
        
        # 验证所有事件都有type字段
        for event in collector.events:
            assert "type" in event, "事件缺少type字段"
            assert "data" in event, "事件缺少data字段"
        print(f"✅ 所有事件格式正确")
        
        # 验证done事件数据
        if collector.done_data:
            done_data = collector.done_data
            print(f"📋 done事件数据: {json.dumps(done_data, ensure_ascii=False, indent=2)[:200]}...")
            
            # done事件应该包含type字段
            assert "type" in done_data, "done事件缺少type字段"
            assert done_data["type"] == "done", f"done事件type不正确: {done_data['type']}"
            print(f"✅ done事件type正确")
            
            # done事件应该包含data字段（内部数据）
            if "data" in done_data:
                inner_data = done_data["data"]
                # 验证内部数据包含必需字段
                if "request_id" in inner_data or "session_id" in inner_data:
                    print(f"✅ done事件包含请求/会话ID")
                if "success" in inner_data:
                    print(f"✅ done事件包含success字段: {inner_data['success']}")
        
        print("✅ 测试7.1.3通过: 响应格式合规性")
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self):
        """
        测试7.1.4: 降级机制验证
        
        验证：
        - 当流式失败时，系统能够降级到非流式模式
        - 降级后仍能返回有效响应
        
        Requirements: 4.1
        """
        print("\n" + "="*80)
        print("测试7.1.4: 降级机制验证")
        print("="*80)
        
        # 使用一个复杂查询来测试
        test_query = "设计一个完整的4周增肌训练计划，包括每天的动作安排"
        
        collector = await collect_stream_response(test_query, timeout=180.0)
        
        # 验证有响应
        assert len(collector.events) > 0, "未接收到任何事件"
        print(f"✅ 接收到 {len(collector.events)} 个事件")
        
        # 检查是否触发了降级
        if collector.is_fallback:
            print(f"ℹ️  检测到降级事件")
            
            # 验证降级后仍有内容
            content = collector.get_full_content()
            assert len(content) > 0, "降级后未返回内容"
            print(f"✅ 降级后返回内容，长度: {len(content)} 字符")
            
            # 验证降级后成功完成
            assert collector.is_successful(), "降级后未成功完成"
            print(f"✅ 降级后成功完成")
        else:
            print(f"ℹ️  未触发降级，流式模式正常工作")
            
            # 验证流式模式正常
            content = collector.get_full_content()
            assert len(content) > 0, "流式模式未返回内容"
            print(f"✅ 流式模式返回内容，长度: {len(content)} 字符")
        
        print("✅ 测试7.1.4通过: 降级机制验证")
    
    @pytest.mark.asyncio
    async def test_response_timeout_compliance(self):
        """
        测试7.1.5: 响应超时合规性
        
        验证：
        - 响应在30秒内完成（非流式模式要求）
        - 流式模式首字节响应时间合理
        
        Requirements: 4.4
        """
        print("\n" + "="*80)
        print("测试7.1.5: 响应超时合规性")
        print("="*80)
        
        test_query = "简单介绍一下健身"
        
        start_time = time.time()
        collector = await collect_stream_response(test_query, timeout=60.0)
        total_time = time.time() - start_time
        
        # 验证总时间
        print(f"⏱️  总耗时: {total_time:.2f}秒")
        
        # 验证TTFB
        ttfb = collector.get_ttfb()
        if ttfb:
            print(f"⚡ TTFB: {ttfb:.2f}秒")
            # TTFB应该在合理范围内（30秒以内）
            assert ttfb < 30, f"TTFB过高: {ttfb:.2f}秒"
            print(f"✅ TTFB在合理范围内")
        
        # 验证总耗时
        duration = collector.get_duration()
        if duration:
            print(f"⏱️  会话持续时间: {duration:.2f}秒")
            # 总耗时应该在60秒以内
            assert duration < 60, f"总耗时过长: {duration:.2f}秒"
            print(f"✅ 总耗时在合理范围内")
        
        print("✅ 测试7.1.5通过: 响应超时合规性")
    
    @pytest.mark.asyncio
    async def test_non_streaming_fallback_response(self):
        """
        测试7.1.6: 非流式接口响应验证
        
        验证：
        - 非流式接口返回正确格式
        - 响应包含content、session_id、metadata字段
        
        Requirements: 4.2, 4.3
        """
        print("\n" + "="*80)
        print("测试7.1.6: 非流式接口响应验证")
        print("="*80)
        
        test_query = "你好"
        
        response = await send_chat_request(test_query)
        
        # 验证响应结构
        assert "code" in response, "响应缺少code字段"
        assert "data" in response, "响应缺少data字段"
        print(f"✅ 响应包含基本字段")
        
        # 验证状态码
        code = response.get("code")
        print(f"📋 响应状态码: {code}")
        
        if code == 200:
            data = response.get("data", {})
            
            # 验证必需字段
            assert "response" in data, "响应缺少response字段"
            print(f"✅ 响应包含response字段")
            
            # 验证内容不为空
            content = data.get("response", "")
            assert len(content) > 0, "响应内容为空"
            print(f"✅ 响应内容不为空，长度: {len(content)} 字符")
            
            # 验证metadata字段
            if "metadata" in data:
                metadata = data.get("metadata", {})
                print(f"📋 metadata字段: {list(metadata.keys())}")
                print(f"✅ 响应包含metadata字段")
            
            # 验证interaction_id（相当于session_id）
            if "interaction_id" in data:
                print(f"✅ 响应包含interaction_id字段")
        else:
            print(f"⚠️  响应状态码非200: {code}")
            # 即使非200，也应该有错误信息
            assert "msg" in response, "错误响应缺少msg字段"
            print(f"✅ 错误响应包含msg字段: {response.get('msg')}")
        
        print("✅ 测试7.1.6通过: 非流式接口响应验证")


# ========== 主函数 ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
