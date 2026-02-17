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

    用法:
        adapter = ToolCallableLLM()
        ai_msg = await adapter.chat_with_tools(
            messages=[SystemMessage(...), HumanMessage(...)],
            tools=[{"type": "function", "function": {...}}],
            temperature=0.3,
        )
    """

    def __init__(self, max_tokens: int = 2000, timeout: float = 120.0):
        self.max_tokens = max_tokens
        self.timeout = timeout

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
