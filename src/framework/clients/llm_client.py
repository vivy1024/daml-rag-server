# -*- coding: utf-8 -*-
"""
LLM调用模块

支持多个LLM提供商:
- DeepSeek (teacher模型，经济实惠) - 支持API池轮询
- Ollama (student模型，本地部署) - 已禁用（服务器无Ollama）
- Moonshot Kimi (备用，长文本)

版本: v1.1.0
更新: 2026-01-06 - 添加API池轮询，禁用Ollama
"""

import os
import logging
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
import httpx

logger = logging.getLogger(__name__)


class LLMConfig:
    """LLM配置 - 从环境变量读取"""

    # DeepSeek (teacher模型)
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Ollama (student模型) - 已禁用
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"  # 默认禁用

    # Moonshot (备用)
    MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "")
    MOONSHOT_BASE_URL = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
    MOONSHOT_MODEL = os.getenv("MOONSHOT_MODEL", "moonshot-v1-32k")

    # 通义千问 (备用)
    QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-turbo")

    # Anthropic Claude (通过Kiro RS反向代理)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://kirors.yuzhen-fitness.cn")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    ANTHROPIC_ENABLED = os.getenv("ANTHROPIC_ENABLED", "true").lower() == "true"

    # 通用配置
    TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120.0"))  # 增加到120秒，适应复杂查询
    MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    
    # 重试配置
    MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))  # 最大重试次数
    RETRY_DELAY = float(os.getenv("LLM_RETRY_DELAY", "2.0"))  # 重试延迟（秒）
    
    # API池配置
    USE_API_POOL = os.getenv("USE_API_POOL", "true").lower() == "true"  # 默认启用API池
    
    # 双模型选择配置
    DUAL_MODEL_ENABLED = os.getenv("DUAL_MODEL_ENABLED", "false").lower() == "true"  # 默认禁用

    @classmethod
    def validate(cls):
        """验证必需的API密钥是否已配置"""
        if not cls.DEEPSEEK_API_KEY:
            logger.warning("DEEPSEEK_API_KEY未配置，DeepSeek功能将不可用")
        if not cls.MOONSHOT_API_KEY:
            logger.warning("MOONSHOT_API_KEY未配置，Moonshot功能将不可用")
        if not cls.QWEN_API_KEY:
            logger.warning("QWEN_API_KEY未配置，通义千问功能将不可用")
        if not cls.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY未配置，Anthropic Claude功能将不可用")
        if cls.ANTHROPIC_ENABLED:
            logger.info(f"Anthropic Claude已启用: model={cls.ANTHROPIC_MODEL}")
        if not cls.OLLAMA_ENABLED:
            logger.info("Ollama已禁用（服务器环境）")
        if cls.USE_API_POOL:
            logger.info("API池轮询已启用")
        if not cls.DUAL_MODEL_ENABLED:
            logger.info("双模型选择已禁用，直接使用DeepSeek")
    
    @classmethod
    def validate_dependencies(cls):
        """
        验证所有必需的依赖项是否存在
        
        Raises:
            ImportError: 如果缺少必需的依赖模块
        """
        required_modules = ["httpx", "json", "asyncio", "logging"]
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
                logger.error(f"缺少必需模块: {module}")
        
        if missing_modules:
            raise ImportError(
                f"缺少必需的依赖模块: {', '.join(missing_modules)}。"
                f"请运行: pip install {' '.join(missing_modules)}"
            )


async def call_deepseek(
    query: str,
    few_shot_examples: List[Dict[str, Any]],
    tool_results: Dict[str, Any],
    system_prompt: str = "你是一位专业的健身教练，擅长根据用户档案提供个性化的训练建议。",
    max_tokens: int = LLMConfig.MAX_TOKENS,
    temperature: float = LLMConfig.TEMPERATURE
) -> str:
    """
    调用DeepSeek API (teacher模型) - 支持自动重试
    
    Args:
        query: 用户查询
        few_shot_examples: Few-Shot示例列表
        tool_results: 工具调用结果
        system_prompt: 系统提示词
        max_tokens: 最大生成token数
        temperature: 温度参数（0.0-1.0）

    Returns:
        str: AI回答
    """
    # 检查API密钥
    if not LLMConfig.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY未配置，请在.env文件中配置")

    # 构建消息（在重试循环外，避免重复构建）
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # 添加Few-Shot示例
    for example in few_shot_examples:
        messages.append({
            "role": "user",
            "content": example.get("query", "")
        })
        messages.append({
            "role": "assistant",
            "content": example.get("response", "")
        })

    # 添加工具结果到上下文
    tool_context = _format_tool_results(tool_results)
    if tool_context:
        messages.append({
            "role": "system",
            "content": f"工具调用结果:\n{tool_context}"
        })

    # 添加当前查询
    messages.append({
        "role": "user",
        "content": query
    })

    # 重试逻辑
    last_error = None
    for attempt in range(LLMConfig.MAX_RETRIES + 1):
        try:
            if attempt > 0:
                logger.info(f"DeepSeek重试 {attempt}/{LLMConfig.MAX_RETRIES}...")
                await asyncio.sleep(LLMConfig.RETRY_DELAY * attempt)  # 指数退避

            # 调用DeepSeek API（使用更精细的超时配置）
            timeout_config = httpx.Timeout(
                connect=10.0,  # 连接超时10秒
                read=LLMConfig.TIMEOUT,  # 读取超时120秒
                write=10.0,  # 写入超时10秒
                pool=5.0  # 连接池超时5秒
            )
            
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(
                    f"{LLMConfig.DEEPSEEK_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {LLMConfig.DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": LLMConfig.DEEPSEEK_MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )

                response.raise_for_status()
                result = response.json()

                answer = result["choices"][0]["message"]["content"]

                logger.info(
                    f"DeepSeek调用成功 (尝试{attempt + 1}): "
                    f"tokens={result.get('usage', {}).get('total_tokens', 0)}, "
                    f"length={len(answer)}"
                )

                return answer

        except httpx.ReadTimeout as e:
            last_error = e
            logger.warning(
                f"DeepSeek读取超时 (尝试{attempt + 1}/{LLMConfig.MAX_RETRIES + 1}): {e}\n"
                f"  - 超时设置: {LLMConfig.TIMEOUT}秒\n"
                f"  - 查询长度: {len(query)}\n"
                f"  - 工具结果数: {len(tool_results) if tool_results else 0}"
            )
            if attempt >= LLMConfig.MAX_RETRIES:
                break
            continue

        except httpx.HTTPError as e:
            last_error = e
            logger.error(
                f"DeepSeek HTTP错误 (尝试{attempt + 1}): {e}\n"
                f"上下文信息:\n"
                f"  - 模型: {LLMConfig.DEEPSEEK_MODEL}\n"
                f"  - 查询长度: {len(query)}\n"
                f"  - Few-Shot示例数: {len(few_shot_examples)}\n"
                f"  - 工具结果数: {len(tool_results) if tool_results else 0}\n"
                f"  - Max Tokens: {max_tokens}",
                exc_info=True
            )
            # HTTP错误通常不需要重试（如401、403等）
            break

        except Exception as e:
            last_error = e
            logger.error(
                f"DeepSeek调用失败 (尝试{attempt + 1}): {e}\n"
                f"上下文信息:\n"
                f"  - 模型: {LLMConfig.DEEPSEEK_MODEL}\n"
                f"  - 查询: {query[:100]}...\n"
                f"  - Few-Shot示例数: {len(few_shot_examples)}",
                exc_info=True
            )
            break

    # 所有重试都失败，返回降级响应
    return get_fallback_response(
        query=query,
        tool_results=tool_results,
        reason=f"DeepSeek调用失败（已重试{LLMConfig.MAX_RETRIES}次）: {str(last_error)}"
    )


async def call_ollama(
    query: str,
    few_shot_examples: List[Dict[str, Any]],
    tool_results: Dict[str, Any],
    system_prompt: str = "你是一位专业的健身教练，擅长根据用户档案提供个性化的训练建议。",
    model: str = LLMConfig.OLLAMA_MODEL,
    max_tokens: int = LLMConfig.MAX_TOKENS,
    temperature: float = LLMConfig.TEMPERATURE
) -> str:
    """
    调用Ollama API (student模型)

    Args:
        query: 用户查询
        few_shot_examples: Few-Shot示例列表
        tool_results: 工具调用结果
        system_prompt: 系统提示词
        model: Ollama模型名称
        max_tokens: 最大生成token数
        temperature: 温度参数（0.0-1.0）

    Returns:
        str: AI回答
    """
    try:
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # 添加Few-Shot示例
        for example in few_shot_examples:
            messages.append({
                "role": "user",
                "content": example.get("query", "")
            })
            messages.append({
                "role": "assistant",
                "content": example.get("response", "")
            })

        # 添加工具结果到上下文
        tool_context = _format_tool_results(tool_results)
        if tool_context:
            messages.append({
                "role": "system",
                "content": f"工具调用结果:\n{tool_context}"
            })

        # 添加当前查询
        messages.append({
            "role": "user",
            "content": query
        })

        # 调用Ollama API
        async with httpx.AsyncClient(timeout=LLMConfig.TIMEOUT) as client:
            response = await client.post(
                f"{LLMConfig.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                }
            )

            response.raise_for_status()
            result = response.json()

            answer = result["message"]["content"]

            logger.info(
                f"Ollama调用成功: model={model}, length={len(answer)}"
            )

            return answer

    except httpx.HTTPError as e:
        # 记录详细的错误上下文
        logger.error(
            f"Ollama HTTP错误: {e}\n"
            f"上下文信息:\n"
            f"  - 模型: {model}\n"
            f"  - 基础URL: {LLMConfig.OLLAMA_BASE_URL}\n"
            f"  - 查询长度: {len(query)}\n"
            f"  - Few-Shot示例数: {len(few_shot_examples)}\n"
            f"  - 工具结果数: {len(tool_results) if tool_results else 0}",
            exc_info=True
        )
        # 返回降级响应而不是抛出异常
        return get_fallback_response(
            query=query,
            tool_results=tool_results,
            reason=f"Ollama HTTP错误: {str(e)}"
        )
    except Exception as e:
        # 记录详细的错误上下文
        logger.error(
            f"Ollama调用失败: {e}\n"
            f"上下文信息:\n"
            f"  - 模型: {model}\n"
            f"  - 查询: {query[:100]}...\n"
            f"  - Few-Shot示例数: {len(few_shot_examples)}\n"
            f"  - 系统提示词长度: {len(system_prompt)}",
            exc_info=True
        )
        # 返回降级响应而不是抛出异常
        return get_fallback_response(
            query=query,
            tool_results=tool_results,
            reason=f"Ollama调用失败: {str(e)}"
        )


async def call_moonshot(
    query: str,
    few_shot_examples: List[Dict[str, Any]],
    tool_results: Dict[str, Any],
    system_prompt: str = "你是一位专业的健身教练。"
) -> str:
    """
    调用Moonshot API (备用，适合长文本)

    Args:
        query: 用户查询
        few_shot_examples: Few-Shot示例列表
        tool_results: 工具调用结果
        system_prompt: 系统提示词

    Returns:
        str: AI回答
    """
    # 检查API密钥
    if not LLMConfig.MOONSHOT_API_KEY:
        raise ValueError("MOONSHOT_API_KEY未配置，请在.env文件中配置")

    try:
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # 添加Few-Shot示例
        for example in few_shot_examples:
            messages.append({
                "role": "user",
                "content": example.get("query", "")
            })
            messages.append({
                "role": "assistant",
                "content": example.get("response", "")
            })

        # 添加工具结果
        tool_context = _format_tool_results(tool_results)
        if tool_context:
            messages.append({
                "role": "system",
                "content": f"工具调用结果:\n{tool_context}"
            })

        messages.append({
            "role": "user",
            "content": query
        })

        async with httpx.AsyncClient(timeout=LLMConfig.TIMEOUT) as client:
            response = await client.post(
                f"{LLMConfig.MOONSHOT_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLMConfig.MOONSHOT_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": LLMConfig.MOONSHOT_MODEL,
                    "messages": messages,
                    "max_tokens": LLMConfig.MAX_TOKENS,
                    "temperature": LLMConfig.TEMPERATURE
                }
            )

            response.raise_for_status()
            result = response.json()

            return result["choices"][0]["message"]["content"]

    except Exception as e:
        # 记录详细的错误上下文
        logger.error(
            f"Moonshot调用失败: {e}\n"
            f"上下文信息:\n"
            f"  - 模型: {LLMConfig.MOONSHOT_MODEL}\n"
            f"  - 查询: {query[:100]}...\n"
            f"  - Few-Shot示例数: {len(few_shot_examples)}\n"
            f"  - 系统提示词长度: {len(system_prompt)}\n"
            f"  - Max Tokens: {LLMConfig.MAX_TOKENS}",
            exc_info=True
        )
        # 返回降级响应而不是抛出异常
        return get_fallback_response(
            query=query,
            tool_results=tool_results,
            reason=f"Moonshot调用失败: {str(e)}"
        )


async def call_anthropic(
    query: str,
    few_shot_examples: List[Dict[str, Any]],
    tool_results: Dict[str, Any],
    system_prompt: str = "你是一位专业的健身教练，擅长根据用户档案提供个性化的训练建议。",
    max_tokens: int = LLMConfig.MAX_TOKENS,
    temperature: float = LLMConfig.TEMPERATURE
) -> str:
    """
    调用Anthropic Claude API (通过Kiro RS反向代理)

    使用Anthropic Messages API格式 (/v1/messages)
    """
    if not LLMConfig.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY未配置")

    # Anthropic格式: system是单独字段，不在messages中
    messages = []
    for example in few_shot_examples:
        messages.append({"role": "user", "content": example.get("query", "")})
        messages.append({"role": "assistant", "content": example.get("response", "")})

    # 工具结果合并到用户消息中
    tool_context = _format_tool_results(tool_results)
    user_content = query
    if tool_context:
        user_content = f"工具调用结果:\n{tool_context}\n\n用户查询: {query}"
    messages.append({"role": "user", "content": user_content})

    last_error = None
    for attempt in range(LLMConfig.MAX_RETRIES + 1):
        try:
            if attempt > 0:
                logger.info(f"Anthropic重试 {attempt}/{LLMConfig.MAX_RETRIES}...")
                await asyncio.sleep(LLMConfig.RETRY_DELAY * attempt)

            timeout_config = httpx.Timeout(connect=10.0, read=LLMConfig.TIMEOUT, write=10.0, pool=5.0)

            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(
                    f"{LLMConfig.ANTHROPIC_BASE_URL}/v1/messages",
                    headers={
                        "x-api-key": LLMConfig.ANTHROPIC_API_KEY,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": LLMConfig.ANTHROPIC_MODEL,
                        "system": system_prompt,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
                response.raise_for_status()
                result = response.json()
                answer = result["content"][0]["text"]

                logger.info(
                    f"Anthropic调用成功 (尝试{attempt + 1}): "
                    f"model={result.get('model', 'N/A')}, "
                    f"tokens={result.get('usage', {}).get('input_tokens', 0)}+"
                    f"{result.get('usage', {}).get('output_tokens', 0)}, "
                    f"length={len(answer)}"
                )
                return answer

        except httpx.ReadTimeout as e:
            last_error = e
            logger.warning(f"Anthropic读取超时 (尝试{attempt + 1}/{LLMConfig.MAX_RETRIES + 1}): {e}")
            if attempt >= LLMConfig.MAX_RETRIES:
                break
            continue
        except httpx.HTTPError as e:
            last_error = e
            logger.error(f"Anthropic HTTP错误 (尝试{attempt + 1}): {e}", exc_info=True)
            break
        except Exception as e:
            last_error = e
            logger.error(f"Anthropic调用失败 (尝试{attempt + 1}): {e}", exc_info=True)
            break

    return get_fallback_response(
        query=query,
        tool_results=tool_results,
        reason=f"Anthropic调用失败（已重试{LLMConfig.MAX_RETRIES}次）: {str(last_error)}"
    )


def _format_tool_results(tool_results: Dict[str, Any]) -> str:
    """
    格式化工具结果为可读文本

    Args:
        tool_results: 工具调用结果字典

    Returns:
        str: 格式化的文本
    """
    if not tool_results:
        return ""

    lines = []
    for tool_name, result in tool_results.items():
        lines.append(f"【{tool_name}】")

        if isinstance(result, dict):
            for key, value in result.items():
                lines.append(f"  - {key}: {value}")
        elif isinstance(result, list):
            for item in result:
                lines.append(f"  - {item}")
        else:
            lines.append(f"  {result}")

    return "\n".join(lines)


def get_fallback_response(
    query: str,
    tool_results: Optional[Dict[str, Any]] = None,
    reason: str = "LLM服务暂时不可用"
) -> str:
    """
    获取降级响应（基于查询和工具结果生成有意义的默认响应）
    
    Args:
        query: 用户查询
        tool_results: 工具调用结果（可选）
        reason: 降级原因
    
    Returns:
        str: 有意义的降级响应文本
    """
    logger.warning(f"使用降级响应: {reason}")
    
    # 基础响应模板
    response_parts = [
        f"抱歉，AI分析功能暂时不可用（{reason}）。",
        "",
        f"📝 您的查询：{query}",
        ""
    ]
    
    # 如果有工具结果，提供结构化信息
    if tool_results:
        response_parts.append("✅ 已完成以下数据分析：")
        response_parts.append("")
        
        # 提取关键信息
        if "step1_user_profile" in tool_results:
            profile = tool_results["step1_user_profile"]
            if profile and isinstance(profile, dict):
                response_parts.append("👤 **用户档案**：")
                if "age" in profile:
                    response_parts.append(f"  - 年龄：{profile['age']}岁")
                if "primary_goal" in profile:
                    response_parts.append(f"  - 目标：{profile['primary_goal']}")
                if "fitness_level" in profile:
                    response_parts.append(f"  - 水平：{profile['fitness_level']}")
                response_parts.append("")
        
        if "step4_complexity" in tool_results:
            complexity = tool_results["step4_complexity"]
            if complexity and isinstance(complexity, dict):
                is_complex = complexity.get("is_complex", False)
                response_parts.append(f"🔍 **查询分析**：{'复杂' if is_complex else '简单'}查询")
                response_parts.append("")
        
        if "step8_retrieval_results" in tool_results:
            retrieval = tool_results["step8_retrieval_results"]
            if retrieval and isinstance(retrieval, dict):
                count = retrieval.get("count", 0)
                response_parts.append(f"📊 **检索结果**：找到 {count} 个相关推荐")
                response_parts.append("")
    
    # 添加建议
    response_parts.extend([
        "💡 **建议**：",
        "  - 请稍后重试获取AI分析",
        "  - 或联系客服获取人工指导",
        "  - 您也可以查看上述数据自行分析",
        "",
        "感谢您的理解！"
    ])
    
    return "\n".join(response_parts)


async def call_deepseek_stream(
    messages: List[Dict[str, str]],
    max_tokens: int = 8000,
    temperature: float = 0.7,
    timeout: float = 180.0
) -> AsyncIterator[str]:
    """
    流式调用DeepSeek API - 支持API池轮询和重试
    
    Args:
        messages: 对话消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
        max_tokens: 最大生成token数（流式模式下可超过4096，建议8000）
        temperature: 温度参数（0.0-1.0）
        timeout: 超时时间（秒），默认180秒
    
    Yields:
        str: 流式返回的文本片段
    
    Raises:
        ValueError: API密钥未配置
        httpx.HTTPError: HTTP请求错误
        json.JSONDecodeError: JSON解析错误
    
    Example:
        ```python
        messages = [
            {"role": "system", "content": "你是一位专业的健身教练。"},
            {"role": "user", "content": "帮我设计一个训练计划"}
        ]
        
        async for chunk in call_deepseek_stream(messages, max_tokens=8000):
            print(chunk, end="", flush=True)
        ```
    """
    # ✅ 优先使用API池轮询
    if LLMConfig.USE_API_POOL:
        from .api_pool_manager import get_api_pool_manager
        
        pool = get_api_pool_manager()
        if pool.api_keys:
            logger.info(f"使用API池轮询（{len(pool.api_keys)}个Key）")
            async for chunk in pool.call_stream(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout
            ):
                yield chunk
            return
        else:
            logger.warning("API池为空，回退到单Key模式")
    
    # 检查API密钥
    if not LLMConfig.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY未配置，请在.env文件中配置")
    
    # 单Key模式的重试逻辑
    last_error = None
    for attempt in range(LLMConfig.MAX_RETRIES + 1):
        try:
            if attempt > 0:
                logger.info(f"DeepSeek流式调用重试 {attempt}/{LLMConfig.MAX_RETRIES}...")
                await asyncio.sleep(LLMConfig.RETRY_DELAY * attempt)  # 指数退避
            
            # 配置超时
            timeout_config = httpx.Timeout(
                connect=10.0,  # 连接超时10秒
                read=timeout,  # 读取超时（流式需要更长）
                write=10.0,  # 写入超时10秒
                pool=5.0  # 连接池超时5秒
            )
            
            # 流式调用DeepSeek API
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                async with client.stream(
                    "POST",
                    f"{LLMConfig.DEEPSEEK_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {LLMConfig.DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": LLMConfig.DEEPSEEK_MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True  # 关键：启用流式输出
                    }
                ) as response:
                    response.raise_for_status()
                    
                    # 逐行读取SSE流
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # 去掉 "data: " 前缀
                            
                            # 检测结束标记
                            if data == "[DONE]":
                                logger.info(
                                    f"DeepSeek流式调用完成 (尝试{attempt + 1}): "
                                    f"max_tokens={max_tokens}"
                                )
                                return
                            
                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0]["delta"]
                                
                                if "content" in delta:
                                    yield delta["content"]
                            except json.JSONDecodeError as e:
                                logger.warning(f"解析流式响应失败: {e}, data={data[:100]}")
                                continue
                            except (KeyError, IndexError) as e:
                                logger.warning(f"提取content失败: {e}, chunk={chunk}")
                                continue
            
            # 成功完成，退出重试循环
            return
        
        except httpx.ReadTimeout as e:
            last_error = e
            logger.warning(
                f"DeepSeek流式读取超时 (尝试{attempt + 1}/{LLMConfig.MAX_RETRIES + 1}): {e}\n"
                f"  - 超时设置: {timeout}秒\n"
                f"  - Max Tokens: {max_tokens}\n"
                f"  - 消息数: {len(messages)}"
            )
            if attempt >= LLMConfig.MAX_RETRIES:
                break
            continue
        
        except httpx.HTTPStatusError as e:
            last_error = e
            logger.error(
                f"DeepSeek流式HTTP状态错误 (尝试{attempt + 1}): {e}\n"
                f"  - 状态码: {e.response.status_code}\n"
                f"  - 响应: {e.response.text[:200]}\n"
                f"  - 模型: {LLMConfig.DEEPSEEK_MODEL}\n"
                f"  - Max Tokens: {max_tokens}",
                exc_info=True
            )
            # HTTP状态错误通常不需要重试（如401、403、429等）
            if e.response.status_code in [401, 403, 404]:
                break
            # 429 (Rate Limit) 可以重试
            if e.response.status_code == 429 and attempt < LLMConfig.MAX_RETRIES:
                continue
            break
        
        except httpx.HTTPError as e:
            last_error = e
            logger.error(
                f"DeepSeek流式HTTP错误 (尝试{attempt + 1}): {e}\n"
                f"  - 模型: {LLMConfig.DEEPSEEK_MODEL}\n"
                f"  - 消息数: {len(messages)}\n"
                f"  - Max Tokens: {max_tokens}",
                exc_info=True
            )
            if attempt >= LLMConfig.MAX_RETRIES:
                break
            continue
        
        except httpx.StreamError as e:
            # ✅ 处理流式响应错误（如连接中断、服务器提前关闭）
            last_error = e
            logger.warning(
                f"DeepSeek流式响应错误 (尝试{attempt + 1}/{LLMConfig.MAX_RETRIES + 1}): {e}\n"
                f"  - 这通常是网络不稳定或服务器端问题\n"
                f"  - 模型: {LLMConfig.DEEPSEEK_MODEL}"
            )
            if attempt >= LLMConfig.MAX_RETRIES:
                break
            continue
        
        except Exception as e:
            last_error = e
            error_msg = str(e)
            
            # ✅ 检查是否为可重试的流式错误
            is_stream_error = (
                "streaming response content" in error_msg.lower() or
                "without having called" in error_msg.lower() or
                "connection" in error_msg.lower()
            )
            
            if is_stream_error:
                logger.warning(
                    f"DeepSeek流式连接错误 (尝试{attempt + 1}/{LLMConfig.MAX_RETRIES + 1}): {e}\n"
                    f"  - 这是网络层面的偶发问题，将重试"
                )
                if attempt >= LLMConfig.MAX_RETRIES:
                    break
                continue
            
            # 其他未知错误，记录详细信息
            logger.error(
                f"DeepSeek流式调用失败 (尝试{attempt + 1}): {e}\n"
                f"  - 模型: {LLMConfig.DEEPSEEK_MODEL}\n"
                f"  - 消息数: {len(messages)}\n"
                f"  - Max Tokens: {max_tokens}\n"
                f"  - Temperature: {temperature}",
                exc_info=True
            )
            break
    
    # 所有重试都失败，抛出最后的错误
    error_msg = f"DeepSeek流式调用失败（已重试{LLMConfig.MAX_RETRIES}次）: {str(last_error)}"
    logger.error(error_msg)
    raise RuntimeError(error_msg) from last_error


async def call_anthropic_stream(
    messages: List[Dict[str, str]],
    max_tokens: int = 8000,
    temperature: float = 0.7,
    timeout: float = 180.0
) -> AsyncIterator[str]:
    """
    流式调用Anthropic Claude API

    Args:
        messages: 对话消息列表（OpenAI格式，自动转换为Anthropic格式）
        max_tokens: 最大生成token数
        temperature: 温度参数
        timeout: 超时时间
    """
    if not LLMConfig.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY未配置")

    # 从OpenAI格式messages中提取system prompt
    system_prompt = ""
    anthropic_messages = []
    for msg in messages:
        if msg["role"] == "system":
            if system_prompt:
                system_prompt += "\n\n"
            system_prompt += msg["content"]
        else:
            anthropic_messages.append(msg)

    if not system_prompt:
        system_prompt = "你是一位专业的健身教练。"

    last_error = None
    for attempt in range(LLMConfig.MAX_RETRIES + 1):
        try:
            if attempt > 0:
                logger.info(f"Anthropic流式重试 {attempt}/{LLMConfig.MAX_RETRIES}...")
                await asyncio.sleep(LLMConfig.RETRY_DELAY * attempt)

            timeout_config = httpx.Timeout(connect=10.0, read=timeout, write=10.0, pool=5.0)

            async with httpx.AsyncClient(timeout=timeout_config) as client:
                async with client.stream(
                    "POST",
                    f"{LLMConfig.ANTHROPIC_BASE_URL}/v1/messages",
                    headers={
                        "x-api-key": LLMConfig.ANTHROPIC_API_KEY,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": LLMConfig.ANTHROPIC_MODEL,
                        "system": system_prompt,
                        "messages": anthropic_messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True
                    }
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            return
                        try:
                            event = json.loads(data)
                            event_type = event.get("type", "")
                            if event_type == "content_block_delta":
                                delta = event.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                            elif event_type == "message_stop":
                                return
                        except (json.JSONDecodeError, KeyError):
                            continue

            return

        except httpx.ReadTimeout as e:
            last_error = e
            logger.warning(f"Anthropic流式读取超时 (尝试{attempt + 1}): {e}")
            if attempt >= LLMConfig.MAX_RETRIES:
                break
            continue
        except httpx.HTTPError as e:
            last_error = e
            logger.error(f"Anthropic流式HTTP错误 (尝试{attempt + 1}): {e}", exc_info=True)
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in [401, 403, 404]:
                break
            if attempt >= LLMConfig.MAX_RETRIES:
                break
            continue
        except Exception as e:
            last_error = e
            logger.error(f"Anthropic流式调用失败 (尝试{attempt + 1}): {e}", exc_info=True)
            break

    error_msg = f"Anthropic流式调用失败（已重试{LLMConfig.MAX_RETRIES}次）: {str(last_error)}"
    logger.error(error_msg)
    raise RuntimeError(error_msg) from last_error


async def stream_deepseek(
    query: str,
    few_shot_examples: List[Dict[str, Any]],
    tool_results: Dict[str, Any],
    system_prompt: str = "你是一位专业的健身教练。"
) -> AsyncIterator[str]:
    """
    流式调用DeepSeek API（旧版本，保留向后兼容）
    
    注意：推荐使用新的 call_deepseek_stream() 函数，它支持更大的token限制和重试机制

    Args:
        query: 用户查询
        few_shot_examples: Few-Shot示例列表
        tool_results: 工具调用结果
        system_prompt: 系统提示词

    Yields:
        str: 流式返回的文本片段
    """
    # 检查API密钥
    if not LLMConfig.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY未配置，请在.env文件中配置")

    try:
        # 构建消息（同步版本）
        messages = [{"role": "system", "content": system_prompt}]

        for example in few_shot_examples:
            messages.append({"role": "user", "content": example.get("query", "")})
            messages.append({"role": "assistant", "content": example.get("response", "")})

        tool_context = _format_tool_results(tool_results)
        if tool_context:
            messages.append({"role": "system", "content": f"工具调用结果:\n{tool_context}"})

        messages.append({"role": "user", "content": query})

        # 使用新的流式函数
        async for chunk in call_deepseek_stream(
            messages=messages,
            max_tokens=LLMConfig.MAX_TOKENS,
            temperature=LLMConfig.TEMPERATURE,
            timeout=LLMConfig.TIMEOUT
        ):
            yield chunk

    except Exception as e:
        # 记录详细的错误上下文
        logger.error(
            f"DeepSeek流式调用失败: {e}\n"
            f"上下文信息:\n"
            f"  - 模型: {LLMConfig.DEEPSEEK_MODEL}\n"
            f"  - 查询: {query[:100]}...\n"
            f"  - Few-Shot示例数: {len(few_shot_examples)}\n"
            f"  - 系统提示词长度: {len(system_prompt)}\n"
            f"  - 流式模式: True",
            exc_info=True
        )
        raise


# ============================================================
# LLM客户端工厂函数
# ============================================================

class LLMClient:
    """
    LLM客户端封装类
    
    提供统一的接口来调用不同的LLM提供商
    """
    
    def __init__(self, provider: str = "deepseek"):
        """
        初始化LLM客户端
        
        Args:
            provider: LLM提供商，可选 "deepseek", "ollama", "moonshot", "anthropic"
        """
        self.provider = provider
        LLMConfig.validate()
    
    async def call(
        self,
        query: str,
        few_shot_examples: List[Dict[str, Any]] = None,
        tool_results: Dict[str, Any] = None,
        system_prompt: str = "你是一位专业的健身教练。",
        **kwargs
    ) -> str:
        """
        调用LLM生成回复
        
        Args:
            query: 用户查询
            few_shot_examples: Few-Shot示例
            tool_results: 工具调用结果
            system_prompt: 系统提示词
            **kwargs: 其他参数
        
        Returns:
            str: LLM生成的回复
        """
        few_shot_examples = few_shot_examples or []
        tool_results = tool_results or {}
        
        if self.provider == "deepseek":
            return await call_deepseek(
                query=query,
                few_shot_examples=few_shot_examples,
                tool_results=tool_results,
                system_prompt=system_prompt,
                **kwargs
            )
        elif self.provider == "ollama":
            return await call_ollama(
                query=query,
                few_shot_examples=few_shot_examples,
                tool_results=tool_results,
                system_prompt=system_prompt,
                **kwargs
            )
        elif self.provider == "moonshot":
            return await call_moonshot(
                query=query,
                few_shot_examples=few_shot_examples,
                tool_results=tool_results,
                system_prompt=system_prompt
            )
        elif self.provider == "anthropic":
            return await call_anthropic(
                query=query,
                few_shot_examples=few_shot_examples,
                tool_results=tool_results,
                system_prompt=system_prompt,
                **kwargs
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")
    
    async def stream(
        self,
        query: str,
        few_shot_examples: List[Dict[str, Any]] = None,
        tool_results: Dict[str, Any] = None,
        system_prompt: str = "你是一位专业的健身教练。",
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式调用LLM
        
        Args:
            query: 用户查询
            few_shot_examples: Few-Shot示例
            tool_results: 工具调用结果
            system_prompt: 系统提示词
            **kwargs: 其他参数
        
        Yields:
            str: 流式返回的文本片段
        """
        few_shot_examples = few_shot_examples or []
        tool_results = tool_results or {}
        
        if self.provider == "deepseek":
            async for chunk in stream_deepseek(
                query=query,
                few_shot_examples=few_shot_examples,
                tool_results=tool_results,
                system_prompt=system_prompt
            ):
                yield chunk
        elif self.provider == "anthropic":
            msgs = [{"role": "system", "content": system_prompt}]
            for example in few_shot_examples:
                msgs.append({"role": "user", "content": example.get("query", "")})
                msgs.append({"role": "assistant", "content": example.get("response", "")})
            tool_context = _format_tool_results(tool_results)
            if tool_context:
                msgs.append({"role": "system", "content": f"工具调用结果:\n{tool_context}"})
            msgs.append({"role": "user", "content": query})
            async for chunk in call_anthropic_stream(msgs):
                yield chunk
        else:
            # 其他提供商暂不支持流式，使用普通调用
            result = await self.call(
                query=query,
                few_shot_examples=few_shot_examples,
                tool_results=tool_results,
                system_prompt=system_prompt,
                **kwargs
            )
            yield result


def get_llm_client(provider: str = "deepseek") -> LLMClient:
    """
    获取LLM客户端实例（工厂函数）
    
    Args:
        provider: LLM提供商，可选 "deepseek", "ollama", "moonshot", "anthropic"
    
    Returns:
        LLMClient: LLM客户端实例
    
    Example:
        ```python
        client = get_llm_client("deepseek")
        response = await client.call("帮我设计一个训练计划")
        ```
    """
    return LLMClient(provider=provider)
