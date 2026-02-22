# -*- coding: utf-8 -*-
"""
ToolCallableLLM 适配器

桥接现有 APIPoolManager（文本-only）与 LangGraph Agent 的 function calling 需求。
复用 APIPoolManager 的多 Key 轮询和健康检查，在请求体中添加 tools 参数，
解析响应中的 tool_calls 并返回 LangChain AIMessage。

版本: v1.0.0
日期: 2026-02-17
"""

import logging
import time
from typing import List, Dict, Any, Optional

import httpx
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage,
)

from src.framework.clients.api_pool_manager import get_api_pool_manager

logger = logging.getLogger(__name__)


def _langchain_msg_to_dict(msg: BaseMessage) -> Dict[str, Any]:
    """
    将 LangChain 消息对象转为 OpenAI API 格式的 dict。

    支持: SystemMessage, HumanMessage, AIMessage (含 tool_calls), ToolMessage
    """
    if isinstance(msg, SystemMessage):
        return {"role": "system", "content": msg.content}

    if isinstance(msg, HumanMessage):
        return {"role": "human" if False else "user", "content": msg.content}

    if isinstance(msg, AIMessage):
        d: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": (
                            tc["args"]
                            if isinstance(tc["args"], str)
                            else __import__("json").dumps(tc["args"], ensure_ascii=False)
                        ),
                    },
                }
                for tc in tool_calls
            ]
        return d

    if isinstance(msg, ToolMessage):
        return {
            "role": "tool",
            "content": msg.content,
            "tool_call_id": msg.tool_call_id,
        }

    # 兜底
    return {"role": "user", "content": str(msg.content)}


def _parse_tool_calls(raw_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将 OpenAI 格式的 tool_calls 响应解析为 LangChain AIMessage 所需的格式。

    OpenAI 格式:
        {"id": "call_xxx", "type": "function",
         "function": {"name": "tool_name", "arguments": "{\"key\": \"val\"}"}}

    LangChain 格式:
        {"id": "call_xxx", "name": "tool_name", "args": {"key": "val"}}
    """
    import json

    parsed = []
    for tc in raw_calls:
        func = tc.get("function", {})
        args_raw = func.get("arguments", "{}")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except (json.JSONDecodeError, TypeError):
            args = {"raw": args_raw}

        parsed.append({
            "id": tc.get("id", ""),
            "name": func.get("name", ""),
            "args": args,
        })
    return parsed


class ToolCallableLLM:
    """
    支持 function calling 的 LLM 适配器。

    复用 APIPoolManager 的多 Key 轮询机制，在 DeepSeek API 请求中
    添加 tools 参数，解析 tool_calls 响应，返回 LangChain AIMessage。

    支持通过参数或环境变量 AGENT_LLM_BACKEND 切换到其他 OpenAI 兼容后端。

    用法:
        # 默认走 APIPoolManager (DeepSeek)
        adapter = ToolCallableLLM()

        # 指定后端
        adapter = ToolCallableLLM(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="sk-xxx",
            model="qwen-plus",
        )

        ai_msg = await adapter.chat_with_tools(
            messages=[SystemMessage(...), HumanMessage(...)],
            tools=[{"type": "function", "function": {...}}],
            temperature=0.3,
        )
    """

    def __init__(
        self,
        max_tokens: int = 2000,
        timeout: float = 120.0,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.max_tokens = max_tokens
        self.timeout = timeout

        # 如果传了参数，直接用；否则检查环境变量 AGENT_LLM_BACKEND
        self._custom_base_url = base_url
        self._custom_api_key = api_key
        self._custom_model = model

        if not base_url:
            self._resolve_from_env()

    def _resolve_from_env(self):
        """从 AGENT_LLM_BACKEND 环境变量解析后端配置"""
        import os
        backend = os.getenv("AGENT_LLM_BACKEND", "").lower()
        if not backend or backend == "deepseek":
            return  # 走默认 APIPoolManager

        env_map = {
            "qwen": ("QWEN_BASE_URL", "QWEN_API_KEY", "QWEN_MODEL", "qwen-plus"),
            "siliconflow": ("SILICONFLOW_BASE_URL", "SILICONFLOW_API_KEY", "SILICONFLOW_MODEL", "Qwen/Qwen3-8B"),
            "glm": ("GLM_BASE_URL", "GLM_API_KEY", "GLM_MODEL", "glm-4-flash"),
        }

        if backend in env_map:
            url_key, key_key, model_key, default_model = env_map[backend]
            self._custom_base_url = os.getenv(url_key)
            self._custom_api_key = os.getenv(key_key)
            self._custom_model = os.getenv(model_key, default_model)
            if self._custom_base_url and self._custom_api_key:
                logger.info(f"Agent LLM 后端切换到: {backend} ({self._custom_model})")
            else:
                logger.warning(f"AGENT_LLM_BACKEND={backend} 但缺少配置，回退到 DeepSeek")
                self._custom_base_url = None
                self._custom_api_key = None
                self._custom_model = None

    @property
    def _use_custom_backend(self) -> bool:
        return bool(self._custom_base_url and self._custom_api_key and self._custom_model)

    async def chat_with_tools(
        self,
        messages: List[BaseMessage],
        tools: List[Dict[str, Any]],
        temperature: float = 0.3,
    ) -> AIMessage:
        """
        带 function calling 的 LLM 调用。

        Args:
            messages: LangChain 消息列表
            tools: OpenAI function-calling schema 列表
            temperature: 采样温度

        Returns:
            AIMessage，可能包含 tool_calls 属性（LLM 决定调用工具时）
        """
        if self._use_custom_backend:
            return await self._call_custom_backend(messages, tools, temperature)
        return await self._call_pool_backend(messages, tools, temperature)

    async def _call_custom_backend(
        self,
        messages: List[BaseMessage],
        tools: List[Dict[str, Any]],
        temperature: float,
    ) -> AIMessage:
        """直接调用自定义后端（不走 APIPoolManager）"""
        openai_messages = [_langchain_msg_to_dict(m) for m in messages]
        request_body: Dict[str, Any] = {
            "model": self._custom_model,
            "messages": openai_messages,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
        }
        if tools:
            request_body["tools"] = tools
            request_body["tool_choice"] = "auto"

        start = time.time()
        timeout_config = httpx.Timeout(
            connect=10.0, read=self.timeout, write=10.0, pool=5.0,
        )

        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(
                f"{self._custom_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._custom_api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
            result = response.json()

        elapsed = time.time() - start
        choice = result["choices"][0]["message"]
        content = choice.get("content", "") or ""
        raw_tool_calls = choice.get("tool_calls")

        if raw_tool_calls:
            tool_calls = _parse_tool_calls(raw_tool_calls)
            logger.info(
                f"LLM({self._custom_model}) 返回 {len(tool_calls)} 个 tool_calls, "
                f"耗时 {elapsed:.2f}s"
            )
            return AIMessage(content=content, tool_calls=tool_calls)

        logger.info(f"LLM({self._custom_model}) 返回文本回答, 耗时 {elapsed:.2f}s")
        return AIMessage(content=content)

    async def _call_pool_backend(
        self,
        messages: List[BaseMessage],
        tools: List[Dict[str, Any]],
        temperature: float,
    ) -> AIMessage:
        """通过 APIPoolManager 调用（原有逻辑）"""
        pool = get_api_pool_manager()
        openai_messages = [_langchain_msg_to_dict(m) for m in messages]

        # 构建请求体（比 APIPoolManager._call_deepseek 多了 tools 字段）
        request_body: Dict[str, Any] = {
            "model": pool.model,
            "messages": openai_messages,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
        }
        if tools:
            request_body["tools"] = tools
            request_body["tool_choice"] = "auto"

        # 复用 APIPoolManager 的多 Key 轮询逻辑
        tried_keys = set()
        last_error = None

        while len(tried_keys) < len(pool.key_statuses):
            status = pool.get_available_key()
            if status is None:
                break

            if status.key in tried_keys:
                pool._rotate_index()
                continue

            tried_keys.add(status.key)

            try:
                logger.info(f"ToolCallableLLM 使用 API Key: {status.masked_key}")
                start = time.time()

                timeout_config = httpx.Timeout(
                    connect=10.0,
                    read=self.timeout,
                    write=10.0,
                    pool=5.0,
                )

                async with httpx.AsyncClient(timeout=timeout_config) as client:
                    response = await client.post(
                        f"{pool.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {status.key}",
                            "Content-Type": "application/json",
                        },
                        json=request_body,
                    )
                    response.raise_for_status()
                    result = response.json()

                elapsed = time.time() - start
                pool.mark_success(status)

                # 解析响应
                choice = result["choices"][0]["message"]
                content = choice.get("content", "") or ""
                raw_tool_calls = choice.get("tool_calls")

                if raw_tool_calls:
                    tool_calls = _parse_tool_calls(raw_tool_calls)
                    logger.info(
                        f"LLM 返回 {len(tool_calls)} 个 tool_calls, "
                        f"耗时 {elapsed:.2f}s"
                    )
                    return AIMessage(content=content, tool_calls=tool_calls)

                logger.info(f"LLM 返回文本回答, 耗时 {elapsed:.2f}s")
                return AIMessage(content=content)

            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(
                    f"ToolCallableLLM Key {status.masked_key} "
                    f"调用失败: {error_msg[:100]}"
                )
                pool.mark_failure(status, error_msg)
                continue

        error_msg = (
            f"ToolCallableLLM 所有 API Key 都失败"
            f"（尝试 {len(tried_keys)} 个）: {last_error}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
