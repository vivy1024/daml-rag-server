# -*- coding: utf-8 -*-
"""
LLM降级管理器单元测试

测试内容：
- 主要后端失败时的降级逻辑
- 重试机制和超时控制
- 模板化响应生成
- 后端健康检查

作者: BUILD_BODY Team
版本: v2.0.0 — 适配多模型池重构后的通用后端接口
创建日期: 2025-12-21
更新日期: 2026-02-23
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.framework.clients.llm_fallback_manager import (
    LLMFallbackManager,
    LLMRequest,
    LLMResponse,
    BackendType
)


class TestLLMFallbackManager:
    """LLM降级管理器测试类"""

    @pytest.fixture
    def manager(self):
        """创建测试用的降级管理器（降级链: DeepSeek → Template）"""
        return LLMFallbackManager(
            primary_backend="deepseek",
            fallback_backends=["template"],
            max_retries=2,
            timeout=5,
            enable_health_check=False
        )

    @pytest.fixture
    def sample_request(self):
        """创建测试用的LLM请求"""
        return LLMRequest(
            query="帮我设计一个训练计划",
            few_shot_examples=[],
            tool_results={
                "step1_user_profile": {
                    "age": 25,
                    "primary_goal": "增肌",
                    "fitness_level": "中级"
                }
            },
            system_prompt="你是一位专业的健身教练。",
            max_tokens=2000,
            temperature=0.7
        )

    @pytest.mark.asyncio
    async def test_primary_backend_success(self, manager, sample_request):
        """测试主要后端成功的情况"""
        with patch.object(manager, '_call_backend', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "这是一个专业的训练计划..."

            response = await manager.call_with_fallback(sample_request)

            assert response.content == "这是一个专业的训练计划..."
            assert response.backend_used == BackendType.DEEPSEEK
            assert response.fallback_used is False
            assert response.attempt_count == 1
            assert response.error is None
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_to_template(self, manager, sample_request):
        """测试DeepSeek失败后降级到模板响应"""
        with patch.object(manager, '_call_backend', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("DeepSeek服务不可用")

            response = await manager.call_with_fallback(sample_request)

            assert "抱歉，AI分析功能暂时不可用" in response.content
            assert response.backend_used == BackendType.TEMPLATE
            assert response.fallback_used is True
            assert response.attempt_count > 1
            assert mock_call.call_count == manager.max_retries

    @pytest.mark.asyncio
    async def test_fallback_to_template_with_tool_results(self, manager, sample_request):
        """测试降级到模板响应时包含工具结果信息"""
        with patch.object(manager, '_call_backend', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("DeepSeek服务不可用")

            response = await manager.call_with_fallback(sample_request)

            assert "抱歉，AI分析功能暂时不可用" in response.content
            assert "您的查询：帮我设计一个训练计划" in response.content
            assert response.backend_used == BackendType.TEMPLATE
            assert response.fallback_used is True
            assert mock_call.call_count == manager.max_retries

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, manager, sample_request):
        """测试重试机制"""
        with patch.object(manager, '_call_backend', new_callable=AsyncMock) as mock_call:
            call_count = 0
            async def side_effect_func(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise Exception(f"第{call_count}次失败")
                return "第2次成功！"

            mock_call.side_effect = side_effect_func

            response = await manager.call_with_fallback(sample_request)

            assert response.content == "第2次成功！"
            assert response.backend_used == BackendType.DEEPSEEK
            assert response.attempt_count == 2
            assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_handling(self, manager, sample_request):
        """测试超时控制（DeepSeek超时后降级到Template）"""
        with patch.object(manager, '_call_backend', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = asyncio.TimeoutError("请求超时")

            response = await manager.call_with_fallback(sample_request)

            assert "抱歉，AI分析功能暂时不可用" in response.content
            assert response.backend_used == BackendType.TEMPLATE
            assert response.fallback_used is True
            assert mock_call.call_count == manager.max_retries

    @pytest.mark.asyncio
    async def test_non_retryable_error(self, manager, sample_request):
        """测试不可重试的错误（如认证错误，直接降级到Template）"""
        import httpx

        with patch.object(manager, '_call_backend', new_callable=AsyncMock) as mock_call:
            response_mock = MagicMock()
            response_mock.status_code = 401
            http_error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response_mock)
            mock_call.side_effect = http_error

            response = await manager.call_with_fallback(sample_request)

            assert mock_call.call_count == 1  # 不重试
            assert response.backend_used == BackendType.TEMPLATE

    def test_template_response_generation(self, manager):
        """测试模板化响应生成"""
        query = "帮我设计一个训练计划"
        context = {
            "tool_results": {
                "step1_user_profile": {
                    "age": 25,
                    "primary_goal": "增肌",
                    "fitness_level": "中级"
                },
                "step4_complexity": {
                    "is_complex": True
                },
                "step8_retrieval_results": {
                    "count": 5
                }
            },
            "error": "测试错误"
        }

        response = manager.get_template_response(query, context)

        assert "抱歉，AI分析功能暂时不可用" in response
        assert query in response

    def test_template_response_without_tool_results(self, manager):
        """测试没有工具结果时的模板响应"""
        query = "帮我设计一个训练计划"
        context = {"error": "服务不可用"}

        response = manager.get_template_response(query, context)

        assert "抱歉，AI分析功能暂时不可用" in response
        assert query in response

    @pytest.mark.asyncio
    async def test_backend_health_check(self, manager):
        """测试后端健康检查"""
        # Template 后端始终健康
        is_healthy = await manager.check_backend_health(BackendType.TEMPLATE)
        assert is_healthy is True

        # _init_backends() 会无条件注册 DeepSeek 客户端 + health_checker，
        # 清除客户端后走缓存→无缓存→返回 True（假设健康）
        manager._clients.pop(BackendType.DEEPSEEK, None)
        is_healthy = await manager.check_backend_health(BackendType.DEEPSEEK)
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_caching(self, manager):
        """测试健康检查缓存"""
        import time
        manager._health_cache_ttl = 60.0

        # 清除自动注册的客户端，强制走缓存路径
        manager._clients.pop(BackendType.DEEPSEEK, None)

        # 手动写入健康缓存
        manager._health_cache[BackendType.DEEPSEEK] = (True, time.time())
        is_healthy = await manager.check_backend_health(BackendType.DEEPSEEK)
        assert is_healthy is True

        # 写入不健康缓存
        manager._health_cache[BackendType.DEEPSEEK] = (False, time.time())
        is_healthy = await manager.check_backend_health(BackendType.DEEPSEEK)
        assert is_healthy is False

        # 缓存过期后返回默认值 True
        manager._health_cache[BackendType.DEEPSEEK] = (False, time.time() - 120)
        is_healthy = await manager.check_backend_health(BackendType.DEEPSEEK)
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_stream_primary_backend_success(self, manager, sample_request):
        """测试流式调用主要后端成功"""
        sample_request.stream = True

        async def mock_stream(*args, **kwargs):
            for chunk in ["这是", "一个", "训练", "计划"]:
                yield chunk

        with patch.object(manager, '_call_backend_stream', side_effect=mock_stream):
            chunks = []
            final_response = None

            async for chunk, response in manager.call_with_fallback_stream(sample_request):
                if response:
                    final_response = response
                else:
                    chunks.append(chunk)

            assert chunks == ["这是", "一个", "训练", "计划"]
            assert final_response is not None
            assert final_response.content == "这是一个训练计划"
            assert final_response.backend_used == BackendType.DEEPSEEK
            assert final_response.fallback_used is False

    @pytest.mark.asyncio
    async def test_stream_fallback_to_template(self, manager, sample_request):
        """测试流式调用降级到Template"""
        sample_request.stream = True

        with patch.object(manager, '_call_backend_stream', side_effect=Exception("流式调用失败")):
            chunks = []
            final_response = None

            async for chunk, response in manager.call_with_fallback_stream(sample_request):
                if response:
                    final_response = response
                else:
                    chunks.append(chunk)

            assert any("抱歉，AI分析功能暂时不可用" in c for c in chunks)
            assert final_response is not None
            assert final_response.backend_used == BackendType.TEMPLATE
            assert final_response.fallback_used is True

    @pytest.mark.asyncio
    async def test_stream_partial_success(self, manager, sample_request):
        """测试流式调用部分成功（中途中断）"""
        sample_request.stream = True

        async def mock_stream_partial(*args, **kwargs):
            yield "这是"
            yield "一个"
            raise asyncio.TimeoutError("中途超时")

        with patch.object(manager, '_call_backend_stream', side_effect=mock_stream_partial):
            chunks = []
            final_response = None

            async for chunk, response in manager.call_with_fallback_stream(sample_request):
                if response:
                    final_response = response
                else:
                    chunks.append(chunk)

            assert chunks == ["这是", "一个"]
            assert final_response is not None
            assert final_response.content == "这是一个"
            assert final_response.partial_success is True
            assert final_response.error is not None

    @pytest.mark.asyncio
    async def test_all_backends_fail_with_attempts(self, manager, sample_request):
        """测试所有后端都失败时的尝试次数"""
        with patch.object(manager, '_call_backend', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("DeepSeek失败")

            response = await manager.call_with_fallback(sample_request)

            assert response.attempt_count == mock_call.call_count + 1  # +1 for template
            assert response.backend_used == BackendType.TEMPLATE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
