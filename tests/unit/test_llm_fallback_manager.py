# -*- coding: utf-8 -*-
"""
LLM降级管理器单元测试

测试内容：
- 主要后端失败时的降级逻辑
- 重试机制和超时控制
- 模板化响应生成
- 后端健康检查

作者: BUILD_BODY Team
版本: v1.0.0
创建日期: 2025-12-21
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
        """创建测试用的降级管理器（Ollama已禁用，降级链: DeepSeek → Template）"""
        return LLMFallbackManager(
            primary_backend="deepseek",
            fallback_backends=["template"],
            max_retries=2,
            timeout=5,
            enable_health_check=False  # 测试时禁用健康检查
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
        # Mock DeepSeek调用成功
        with patch.object(manager, '_call_deepseek', new_callable=AsyncMock) as mock_deepseek:
            mock_deepseek.return_value = "这是一个专业的训练计划..."
            
            response = await manager.call_with_fallback(sample_request)
            
            # 验证响应
            assert response.content == "这是一个专业的训练计划..."
            assert response.backend_used == BackendType.DEEPSEEK
            assert response.fallback_used is False
            assert response.attempt_count == 1
            assert response.error is None
            
            # 验证只调用了一次
            mock_deepseek.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fallback_to_template(self, manager, sample_request):
        """测试DeepSeek失败后降级到模板响应（Ollama已禁用）"""
        # Mock DeepSeek失败
        with patch.object(manager, '_call_deepseek', new_callable=AsyncMock) as mock_deepseek:

            mock_deepseek.side_effect = Exception("DeepSeek服务不可用")

            response = await manager.call_with_fallback(sample_request)

            # 验证降级到模板响应
            assert "抱歉，AI分析功能暂时不可用" in response.content
            assert response.backend_used == BackendType.TEMPLATE
            assert response.fallback_used is True
            assert response.attempt_count > 1

            # 验证DeepSeek被重试了max_retries次
            assert mock_deepseek.call_count == manager.max_retries
    
    @pytest.mark.asyncio
    async def test_fallback_to_template_with_tool_results(self, manager, sample_request):
        """测试降级到模板响应时包含工具结果信息"""
        # Mock DeepSeek失败
        with patch.object(manager, '_call_deepseek', new_callable=AsyncMock) as mock_deepseek:

            mock_deepseek.side_effect = Exception("DeepSeek服务不可用")

            response = await manager.call_with_fallback(sample_request)

            # 验证模板响应包含用户档案信息
            assert "抱歉，AI分析功能暂时不可用" in response.content
            assert "您的查询：帮我设计一个训练计划" in response.content
            assert "用户档案" in response.content
            assert response.backend_used == BackendType.TEMPLATE
            assert response.fallback_used is True

            # 验证DeepSeek被重试了max_retries次
            assert mock_deepseek.call_count == manager.max_retries
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, manager, sample_request):
        """测试重试机制"""
        # Mock DeepSeek第1次失败，第2次成功
        with patch.object(manager, '_call_deepseek', new_callable=AsyncMock) as mock_deepseek:
            # 第1次失败，第2次成功
            call_count = 0
            async def side_effect_func(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise Exception(f"第{call_count}次失败")
                return "第2次成功！"
            
            mock_deepseek.side_effect = side_effect_func
            
            response = await manager.call_with_fallback(sample_request)
            
            # 验证响应（第2次成功）
            assert response.content == "第2次成功！"
            assert response.backend_used == BackendType.DEEPSEEK
            # 尝试次数应该是2（初始1次失败 + 1次重试成功）
            assert response.attempt_count == 2
            
            # 验证调用了2次
            assert mock_deepseek.call_count == 2
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, manager, sample_request):
        """测试超时控制（DeepSeek超时后降级到Template）"""
        # Mock DeepSeek超时
        with patch.object(manager, '_call_deepseek', new_callable=AsyncMock) as mock_deepseek:

            mock_deepseek.side_effect = asyncio.TimeoutError("请求超时")

            response = await manager.call_with_fallback(sample_request)

            # 验证降级到Template
            assert "抱歉，AI分析功能暂时不可用" in response.content
            assert response.backend_used == BackendType.TEMPLATE
            assert response.fallback_used is True

            # 验证DeepSeek被重试了max_retries次
            assert mock_deepseek.call_count == manager.max_retries
    
    @pytest.mark.asyncio
    async def test_non_retryable_error(self, manager, sample_request):
        """测试不可重试的错误（如认证错误，直接降级到Template）"""
        import httpx

        # Mock DeepSeek返回401错误
        with patch.object(manager, '_call_deepseek', new_callable=AsyncMock) as mock_deepseek:

            # 创建一个401错误
            response_mock = MagicMock()
            response_mock.status_code = 401
            http_error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response_mock)

            mock_deepseek.side_effect = http_error

            response = await manager.call_with_fallback(sample_request)

            # 验证不会重试，直接降级到Template
            assert mock_deepseek.call_count == 1  # 只调用1次，不重试
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
        
        # 验证响应内容
        assert "抱歉，AI分析功能暂时不可用" in response
        assert "测试错误" in response
        assert query in response
        assert "年龄：25岁" in response
        assert "目标：增肌" in response
        assert "水平：中级" in response
        assert "复杂查询" in response
        assert "找到 5 个相关推荐" in response
        assert "建议" in response
    
    def test_template_response_without_tool_results(self, manager):
        """测试没有工具结果时的模板响应"""
        query = "帮我设计一个训练计划"
        context = {"error": "服务不可用"}
        
        response = manager.get_template_response(query, context)
        
        # 验证基础响应
        assert "抱歉，AI分析功能暂时不可用" in response
        assert query in response
        assert "建议" in response
    
    @pytest.mark.asyncio
    async def test_backend_health_check_deepseek(self, manager):
        """测试DeepSeek健康检查"""
        manager.enable_health_check = True
        
        # Mock健康检查成功
        with patch.object(manager, '_check_deepseek_health', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            
            is_healthy = await manager.check_backend_health(BackendType.DEEPSEEK)
            
            assert is_healthy is True
            mock_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_backend_health_check_ollama(self, manager):
        """测试Ollama健康检查"""
        manager.enable_health_check = True
        
        # Mock健康检查失败
        with patch.object(manager, '_check_ollama_health', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False
            
            is_healthy = await manager.check_backend_health(BackendType.OLLAMA)
            
            assert is_healthy is False
            mock_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_caching(self, manager):
        """测试健康检查缓存"""
        manager.enable_health_check = True
        manager._health_cache_ttl = 60.0
        
        # Mock健康检查
        with patch.object(manager, '_check_deepseek_health', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            
            # 第一次调用
            await manager.check_backend_health(BackendType.DEEPSEEK)
            # 第二次调用（应该使用缓存）
            await manager.check_backend_health(BackendType.DEEPSEEK)
            
            # 验证只调用了一次（第二次使用缓存）
            assert mock_check.call_count == 1
    
    @pytest.mark.asyncio
    async def test_stream_primary_backend_success(self, manager, sample_request):
        """测试流式调用主要后端成功"""
        sample_request.stream = True
        
        # Mock DeepSeek流式调用
        async def mock_stream():
            for chunk in ["这是", "一个", "训练", "计划"]:
                yield chunk
        
        with patch.object(manager, '_call_deepseek_stream', return_value=mock_stream()):
            chunks = []
            final_response = None
            
            async for chunk, response in manager.call_with_fallback_stream(sample_request):
                if response:
                    final_response = response
                else:
                    chunks.append(chunk)
            
            # 验证流式输出
            assert chunks == ["这是", "一个", "训练", "计划"]
            assert final_response is not None
            assert final_response.content == "这是一个训练计划"
            assert final_response.backend_used == BackendType.DEEPSEEK
            assert final_response.fallback_used is False
    
    @pytest.mark.asyncio
    async def test_stream_fallback_to_template(self, manager, sample_request):
        """测试流式调用降级到Template（Ollama已禁用）"""
        sample_request.stream = True

        # Mock DeepSeek流式失败
        with patch.object(manager, '_call_deepseek_stream', side_effect=Exception("流式调用失败")):

            chunks = []
            final_response = None

            async for chunk, response in manager.call_with_fallback_stream(sample_request):
                if response:
                    final_response = response
                else:
                    chunks.append(chunk)

            # 验证降级到Template
            assert any("抱歉，AI分析功能暂时不可用" in c for c in chunks)
            assert final_response is not None
            assert final_response.backend_used == BackendType.TEMPLATE
            assert final_response.fallback_used is True
    
    @pytest.mark.asyncio
    async def test_stream_partial_success(self, manager, sample_request):
        """测试流式调用部分成功（中途中断）"""
        sample_request.stream = True
        
        # Mock DeepSeek流式部分成功
        async def mock_stream_partial():
            yield "这是"
            yield "一个"
            raise asyncio.TimeoutError("中途超时")
        
        with patch.object(manager, '_call_deepseek_stream', return_value=mock_stream_partial()):
            chunks = []
            final_response = None
            
            async for chunk, response in manager.call_with_fallback_stream(sample_request):
                if response:
                    final_response = response
                else:
                    chunks.append(chunk)
            
            # 验证部分成功
            assert chunks == ["这是", "一个"]
            assert final_response is not None
            assert final_response.content == "这是一个"
            assert final_response.partial_success is True
            assert final_response.error is not None
    
    @pytest.mark.asyncio
    async def test_all_backends_fail_with_attempts(self, manager, sample_request):
        """测试所有后端都失败时的尝试次数"""
        # Mock DeepSeek失败（Ollama已禁用，降级链: DeepSeek → Template）
        with patch.object(manager, '_call_deepseek', new_callable=AsyncMock) as mock_deepseek:

            mock_deepseek.side_effect = Exception("DeepSeek失败")

            response = await manager.call_with_fallback(sample_request)

            # 验证尝试次数
            # DeepSeek: 2次重试 = 2次
            # Template: 1次 = 1次
            # 总计: 3次
            assert response.attempt_count == mock_deepseek.call_count + 1  # +1 for template
            assert response.backend_used == BackendType.TEMPLATE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
