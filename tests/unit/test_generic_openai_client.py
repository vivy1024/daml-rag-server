# -*- coding: utf-8 -*-
"""
GenericOpenAIClient 单元测试

测试通用OpenAI兼容后端客户端的核心功能：
- 非流式调用 (call)
- 健康检查 (health_check)
- 消息构建 (_build_messages)

多模型集成 - Task 1 单元测试
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.framework.clients.backends.generic_openai_client import GenericOpenAIClient


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def client():
    """创建测试用 GenericOpenAIClient 实例"""
    return GenericOpenAIClient(
        backend_name="test_backend",
        base_url="https://api.test.com/v1",
        api_key="sk-test-key-123",
        model="test-model-v1",
    )


@pytest.fixture
def mock_request():
    """创建模拟的 LLMRequest"""
    req = MagicMock()
    req.messages = None
    req.system_prompt = "你是一个健身教练"
    req.query = "如何做深蹲？"
    req.few_shot_examples = []
    req.tool_results = []
    req.max_tokens = 1024
    req.temperature = 0.7
    return req


@pytest.fixture
def mock_request_with_messages():
    """创建带预构建 messages 的 LLMRequest"""
    req = MagicMock()
    req.messages = [
        {"role": "system", "content": "你是健身教练"},
        {"role": "user", "content": "深蹲怎么做？"},
    ]
    req.max_tokens = 512
    req.temperature = 0.5
    return req


def _make_http_client_mock(post_return=None, get_return=None, get_side_effect=None):
    """构建 httpx.AsyncClient 的 context manager mock"""
    mock_http = AsyncMock()
    if post_return is not None:
        mock_http.post = AsyncMock(return_value=post_return)
    if get_return is not None:
        mock_http.get = AsyncMock(return_value=get_return)
    if get_side_effect is not None:
        mock_http.get = AsyncMock(side_effect=get_side_effect)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    return mock_http


def _make_json_response(content: str):
    """构建模拟的 OpenAI JSON 响应"""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return resp


PATCH_TARGET = "src.framework.clients.backends.generic_openai_client.httpx.AsyncClient"


# ═══════════════════════════════════════════════════════════
# 基础属性测试
# ═══════════════════════════════════════════════════════════

class TestGenericOpenAIClientInit:
    """初始化和属性测试"""

    def test_init_stores_params(self, client):
        assert client.backend_name == "test_backend"
        assert client.base_url == "https://api.test.com/v1"
        assert client.api_key == "sk-test-key-123"
        assert client.model == "test-model-v1"

    def test_base_url_trailing_slash_stripped(self):
        c = GenericOpenAIClient("x", "https://api.test.com/v1/", "key", "model")
        assert c.base_url == "https://api.test.com/v1"

    def test_repr(self, client):
        r = repr(client)
        assert "test_backend" in r
        assert "test-model-v1" in r


# ═══════════════════════════════════════════════════════════
# call() 非流式调用测试
# ═══════════════════════════════════════════════════════════

class TestCall:
    """非流式调用测试"""

    def test_call_success(self, client, mock_request):
        """正常调用返回 content"""
        mock_resp = _make_json_response("深蹲要注意膝盖不超过脚尖")
        mock_http = _make_http_client_mock(post_return=mock_resp)

        with patch(PATCH_TARGET, return_value=mock_http):
            result = asyncio.get_event_loop().run_until_complete(
                client.call(mock_request, timeout=10)
            )

        assert result == "深蹲要注意膝盖不超过脚尖"
        mock_http.post.assert_called_once()
        call_url = mock_http.post.call_args[0][0]
        assert "/chat/completions" in call_url

    def test_call_uses_prebuilt_messages(self, client, mock_request_with_messages):
        """当 request.messages 存在时直接使用"""
        mock_resp = _make_json_response("OK")
        mock_http = _make_http_client_mock(post_return=mock_resp)

        with patch(PATCH_TARGET, return_value=mock_http):
            result = asyncio.get_event_loop().run_until_complete(
                client.call(mock_request_with_messages)
            )

        assert result == "OK"
        payload = mock_http.post.call_args[1]["json"]
        assert payload["messages"] == mock_request_with_messages.messages

    def test_call_sends_correct_headers(self, client, mock_request):
        """验证 Authorization 和 Content-Type 头"""
        mock_resp = _make_json_response("test")
        mock_http = _make_http_client_mock(post_return=mock_resp)

        with patch(PATCH_TARGET, return_value=mock_http):
            asyncio.get_event_loop().run_until_complete(client.call(mock_request))

        headers = mock_http.post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer sk-test-key-123"
        assert headers["Content-Type"] == "application/json"

    def test_call_payload_structure(self, client, mock_request):
        """验证请求 payload 结构"""
        mock_resp = _make_json_response("ok")
        mock_http = _make_http_client_mock(post_return=mock_resp)

        with patch(PATCH_TARGET, return_value=mock_http):
            asyncio.get_event_loop().run_until_complete(client.call(mock_request))

        payload = mock_http.post.call_args[1]["json"]
        assert payload["model"] == "test-model-v1"
        assert payload["max_tokens"] == 1024
        assert payload["temperature"] == 0.7
        assert payload["stream"] is False


# ═══════════════════════════════════════════════════════════
# health_check() 测试
# ═══════════════════════════════════════════════════════════

class TestHealthCheck:
    """健康检查测试"""

    def test_health_check_success(self, client):
        """API 返回 200 时健康"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http = _make_http_client_mock(get_return=mock_resp)

        with patch(PATCH_TARGET, return_value=mock_http):
            result = asyncio.get_event_loop().run_until_complete(client.health_check())

        assert result is True
        call_url = mock_http.get.call_args[0][0]
        assert call_url.endswith("/models")

    def test_health_check_failure(self, client):
        """API 返回非 200 时不健康"""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_http = _make_http_client_mock(get_return=mock_resp)

        with patch(PATCH_TARGET, return_value=mock_http):
            result = asyncio.get_event_loop().run_until_complete(client.health_check())

        assert result is False

    def test_health_check_no_api_key(self):
        """api_key 为空时直接返回 False"""
        c = GenericOpenAIClient("test", "https://api.test.com", "", "model")
        result = asyncio.get_event_loop().run_until_complete(c.health_check())
        assert result is False

    def test_health_check_network_error(self, client):
        """网络异常时返回 False"""
        mock_http = _make_http_client_mock(
            get_side_effect=Exception("Connection refused")
        )

        with patch(PATCH_TARGET, return_value=mock_http):
            result = asyncio.get_event_loop().run_until_complete(client.health_check())

        assert result is False


# ═══════════════════════════════════════════════════════════
# _build_messages() 测试
# ═══════════════════════════════════════════════════════════

class TestBuildMessages:
    """消息构建测试"""

    def test_basic_messages(self, client, mock_request):
        """基本消息构建：system + user"""
        messages = client._build_messages(mock_request)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "你是一个健身教练"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "如何做深蹲？"

    def test_with_few_shot_examples(self, client, mock_request):
        """包含 few-shot 示例"""
        mock_request.few_shot_examples = [
            {"query": "卧推怎么做？", "response": "卧推需要注意肩胛骨收紧"},
        ]
        messages = client._build_messages(mock_request)
        assert len(messages) == 4  # system + example_user + example_assistant + user
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "卧推怎么做？"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "卧推需要注意肩胛骨收紧"

    def test_with_tool_results(self, client, mock_request):
        """包含工具调用结果"""
        mock_request.tool_results = [{"tool": "tdee", "result": "2500 kcal"}]

        with patch(
            "src.framework.clients.llm_client._format_tool_results",
            return_value="TDEE: 2500 kcal",
        ):
            messages = client._build_messages(mock_request)

        # system + tool_context + user = 3
        assert len(messages) == 3
        assert "工具调用结果" in messages[1]["content"]
