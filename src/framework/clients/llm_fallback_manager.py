# -*- coding: utf-8 -*-
"""
LLM降级管理器

管理LLM调用的降级策略和错误恢复，确保系统在LLM服务不可用时仍能提供有意义的响应。

降级策略（服务器环境）：
1. 主要后端: DeepSeek API（支持API池轮询）
2. 降级后端: 模板化响应
3. 最终降级: 错误信息 + 部分结果

注意：Ollama已禁用（服务器无本地模型）

版本: v1.1.0
创建日期: 2025-12-21
更新日期: 2026-01-06 - 禁用Ollama，添加API池支持
"""

import logging
import asyncio
import time
import os
from typing import Dict, Any, List, Optional, AsyncIterator, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """LLM后端类型"""
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"  # 保留枚举值，但实际已禁用
    TEMPLATE = "template"


@dataclass
class LLMRequest:
    """LLM请求数据类"""
    query: str
    few_shot_examples: List[Dict[str, Any]]
    tool_results: Dict[str, Any]
    system_prompt: str = "你是一位专业的健身教练，擅长根据用户档案提供个性化的训练建议。"
    max_tokens: int = 2000
    temperature: float = 0.7
    stream: bool = False
    messages: Optional[List[Dict[str, str]]] = None  # 用于流式调用
    conversation_history: Optional[List[Dict[str, str]]] = None  # 对话历史（上下文工程）


@dataclass
class LLMResponse:
    """LLM响应数据类"""
    content: str
    backend_used: BackendType
    fallback_used: bool
    attempt_count: int
    duration_ms: float
    error: Optional[str] = None
    partial_success: bool = False


class LLMFallbackManager:
    """
    LLM降级管理器
    
    职责：
    - 管理LLM调用的降级策略
    - 实现自动重试机制
    - 提供超时控制
    - 后端健康检查
    - 模板化响应生成
    
    降级策略：
    DeepSeek → Ollama → Template → Error
    """
    
    def __init__(
        self,
        primary_backend: str = "deepseek",
        fallback_backends: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: int = 30,
        enable_health_check: bool = True
    ):
        """
        初始化LLM降级管理器
        
        Args:
            primary_backend: 主要后端（默认deepseek）
            fallback_backends: 降级后端列表（默认[template]，Ollama已禁用）
            max_retries: 最大重试次数（默认3）
            timeout: 超时时间（秒，默认30）
            enable_health_check: 是否启用健康检查（默认True）
        """
        self.primary_backend = BackendType(primary_backend)
        
        # ✅ 服务器环境：禁用Ollama，只保留template作为降级
        ollama_enabled = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
        if fallback_backends:
            # 过滤掉ollama（如果禁用）
            if not ollama_enabled:
                fallback_backends = [b for b in fallback_backends if b != "ollama"]
            self.fallback_backends = [BackendType(b) for b in fallback_backends]
        else:
            # 默认只使用template
            self.fallback_backends = [BackendType.TEMPLATE]
        
        self.max_retries = max_retries
        self.timeout = timeout
        self.enable_health_check = enable_health_check
        
        # 后端健康状态缓存（backend -> (is_healthy, last_check_time)）
        self._health_cache: Dict[BackendType, tuple[bool, float]] = {}
        self._health_cache_ttl = 60.0  # 健康状态缓存60秒
        
        logger.info(
            f"LLM降级管理器初始化: "
            f"primary={self.primary_backend.value}, "
            f"fallbacks={[b.value for b in self.fallback_backends]}, "
            f"max_retries={self.max_retries}, "
            f"timeout={self.timeout}s, "
            f"ollama_enabled={ollama_enabled}"
        )
    
    async def call_with_fallback(
        self,
        request: LLMRequest
    ) -> LLMResponse:
        """
        带降级的LLM调用（非流式）
        
        Args:
            request: LLM请求
        
        Returns:
            LLMResponse: LLM响应
        """
        start_time = time.time()
        backends_to_try = [self.primary_backend] + self.fallback_backends
        last_error = None
        attempt_count = 0
        
        for backend in backends_to_try:
            # 跳过不健康的后端（除了template）
            if backend != BackendType.TEMPLATE and self.enable_health_check:
                if not await self.check_backend_health(backend):
                    logger.warning(f"跳过不健康的后端: {backend.value}")
                    continue
            
            # 尝试调用后端
            for retry in range(self.max_retries):
                attempt_count += 1
                
                try:
                    logger.info(
                        f"尝试调用LLM: backend={backend.value}, "
                        f"attempt={attempt_count}, retry={retry + 1}/{self.max_retries}"
                    )
                    
                    # 根据后端类型调用不同的函数
                    if backend == BackendType.DEEPSEEK:
                        content = await self._call_deepseek(request)
                    elif backend == BackendType.OLLAMA:
                        content = await self._call_ollama(request)
                    elif backend == BackendType.TEMPLATE:
                        # Template后端作为最终降级，需要记录错误信息
                        content = self.get_template_response(
                            request.query,
                            {"tool_results": request.tool_results}
                        )
                        # Template后端成功，但需要标记为降级并记录错误
                        duration_ms = (time.time() - start_time) * 1000
                        error_msg = f"所有LLM后端都失败（尝试{attempt_count}次）: {str(last_error)}" if last_error else None
                        
                        logger.warning(
                            f"⚠️ 使用模板响应: attempts={attempt_count}, "
                            f"duration={duration_ms:.0f}ms"
                        )
                        
                        return LLMResponse(
                            content=content,
                            backend_used=BackendType.TEMPLATE,
                            fallback_used=True,
                            attempt_count=attempt_count,
                            duration_ms=duration_ms,
                            error=error_msg,  # ✅ 记录之前的错误
                            partial_success=False
                        )
                    else:
                        raise ValueError(f"未知的后端类型: {backend}")
                    
                    # 成功返回
                    duration_ms = (time.time() - start_time) * 1000
                    fallback_used = backend != self.primary_backend
                    
                    logger.info(
                        f"✅ LLM调用成功: backend={backend.value}, "
                        f"fallback={fallback_used}, attempts={attempt_count}, "
                        f"duration={duration_ms:.0f}ms, length={len(content)}"
                    )
                    
                    return LLMResponse(
                        content=content,
                        backend_used=backend,
                        fallback_used=fallback_used,
                        attempt_count=attempt_count,
                        duration_ms=duration_ms
                    )
                
                except asyncio.TimeoutError as e:
                    last_error = e
                    logger.warning(
                        f"⏱️ LLM调用超时: backend={backend.value}, "
                        f"retry={retry + 1}/{self.max_retries}, timeout={self.timeout}s"
                    )
                    # 标记后端不健康
                    self._mark_backend_unhealthy(backend)
                    
                    # 超时后等待再重试
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (retry + 1))  # 减少等待时间
                    continue
                
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"❌ LLM调用失败: backend={backend.value}, "
                        f"retry={retry + 1}/{self.max_retries}, error={str(e)}"
                    )
                    # 标记后端不健康
                    self._mark_backend_unhealthy(backend)
                    
                    # 某些错误不需要重试（如认证错误）
                    if self._is_non_retryable_error(e):
                        logger.info(f"检测到不可重试错误，跳过重试: {type(e).__name__}")
                        break
                    
                    # 等待后重试
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (retry + 1))  # 减少等待时间
                    continue
            
            # 如果是template后端失败，直接返回错误
            if backend == BackendType.TEMPLATE:
                break
        
        # 所有后端都失败，尝试template后端
        attempt_count += 1
        try:
            logger.info(f"尝试调用LLM: backend=template, attempt={attempt_count}")
            content = self.get_template_response(
                request.query,
                {"tool_results": request.tool_results}
            )
            
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"所有LLM后端都失败（尝试{attempt_count}次）: {str(last_error)}"
            
            logger.error(
                f"❌ LLM调用完全失败，使用模板响应: attempts={attempt_count}, "
                f"duration={duration_ms:.0f}ms, error={error_msg}"
            )
            
            return LLMResponse(
                content=content,
                backend_used=BackendType.TEMPLATE,
                fallback_used=True,
                attempt_count=attempt_count,
                duration_ms=duration_ms,
                error=error_msg,  # ✅ 确保设置error字段
                partial_success=False
            )
        except Exception as e:
            # 连模板都失败了（不太可能）
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"所有后端包括模板都失败: {str(e)}"
            logger.critical(error_msg)
            
            return LLMResponse(
                content=f"系统错误: {error_msg}",
                backend_used=BackendType.TEMPLATE,
                fallback_used=True,
                attempt_count=attempt_count,
                duration_ms=duration_ms,
                error=error_msg,
                partial_success=False
            )
    
    async def call_with_fallback_stream(
        self,
        request: LLMRequest
    ) -> AsyncIterator[tuple[str, Optional[LLMResponse]]]:
        """
        带降级的LLM流式调用
        
        Args:
            request: LLM请求（stream=True）
        
        Yields:
            tuple[str, Optional[LLMResponse]]: (文本片段, 最终响应元数据)
            - 流式过程中: (chunk, None)
            - 流式结束时: ("", LLMResponse)
        """
        start_time = time.time()
        backends_to_try = [self.primary_backend] + self.fallback_backends
        last_error = None
        attempt_count = 0
        accumulated_content = ""
        
        for backend in backends_to_try:
            # 跳过不健康的后端（除了template）
            if backend != BackendType.TEMPLATE and self.enable_health_check:
                if not await self.check_backend_health(backend):
                    logger.warning(f"跳过不健康的后端: {backend.value}")
                    continue
            
            # 尝试调用后端
            for retry in range(self.max_retries):
                attempt_count += 1
                accumulated_content = ""
                
                try:
                    logger.info(
                        f"尝试流式调用LLM: backend={backend.value}, "
                        f"attempt={attempt_count}, retry={retry + 1}/{self.max_retries}"
                    )
                    
                    # 只有DeepSeek支持流式
                    if backend == BackendType.DEEPSEEK:
                        async for chunk in self._call_deepseek_stream(request):
                            accumulated_content += chunk
                            yield (chunk, None)
                        
                        # 流式成功完成
                        duration_ms = (time.time() - start_time) * 1000
                        fallback_used = backend != self.primary_backend
                        
                        logger.info(
                            f"✅ LLM流式调用成功: backend={backend.value}, "
                            f"fallback={fallback_used}, attempts={attempt_count}, "
                            f"duration={duration_ms:.0f}ms, length={len(accumulated_content)}"
                        )
                        
                        # 返回最终元数据
                        yield ("", LLMResponse(
                            content=accumulated_content,
                            backend_used=backend,
                            fallback_used=fallback_used,
                            attempt_count=attempt_count,
                            duration_ms=duration_ms
                        ))
                        return
                    
                    elif backend == BackendType.OLLAMA:
                        # Ollama不支持流式，降级到非流式
                        content = await self._call_ollama(request)
                        accumulated_content = content
                        yield (content, None)
                        
                        duration_ms = (time.time() - start_time) * 1000
                        yield ("", LLMResponse(
                            content=content,
                            backend_used=backend,
                            fallback_used=True,
                            attempt_count=attempt_count,
                            duration_ms=duration_ms
                        ))
                        return
                    
                    elif backend == BackendType.TEMPLATE:
                        # 模板响应
                        content = self.get_template_response(
                            request.query,
                            {"tool_results": request.tool_results}
                        )
                        accumulated_content = content
                        yield (content, None)
                        
                        duration_ms = (time.time() - start_time) * 1000
                        yield ("", LLMResponse(
                            content=content,
                            backend_used=backend,
                            fallback_used=True,
                            attempt_count=attempt_count,
                            duration_ms=duration_ms,
                            partial_success=False
                        ))
                        return
                
                except asyncio.TimeoutError as e:
                    last_error = e
                    logger.warning(
                        f"⏱️ LLM流式调用超时: backend={backend.value}, "
                        f"retry={retry + 1}/{self.max_retries}, "
                        f"partial_content={len(accumulated_content)}"
                    )
                    self._mark_backend_unhealthy(backend)
                    
                    # 如果已经有部分内容，标记为部分成功
                    if accumulated_content:
                        duration_ms = (time.time() - start_time) * 1000
                        yield ("", LLMResponse(
                            content=accumulated_content,
                            backend_used=backend,
                            fallback_used=True,
                            attempt_count=attempt_count,
                            duration_ms=duration_ms,
                            error=str(e),
                            partial_success=True
                        ))
                        return
                    
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (retry + 1))  # 减少等待时间
                    continue
                
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"❌ LLM流式调用失败: backend={backend.value}, "
                        f"retry={retry + 1}/{self.max_retries}, "
                        f"partial_content={len(accumulated_content)}, error={str(e)}"
                    )
                    self._mark_backend_unhealthy(backend)
                    
                    # 如果已经有部分内容，标记为部分成功
                    if accumulated_content:
                        duration_ms = (time.time() - start_time) * 1000
                        yield ("", LLMResponse(
                            content=accumulated_content,
                            backend_used=backend,
                            fallback_used=True,
                            attempt_count=attempt_count,
                            duration_ms=duration_ms,
                            error=str(e),
                            partial_success=True
                        ))
                        return
                    
                    # 检查是否为不可重试的错误
                    if self._is_non_retryable_error(e):
                        logger.info(f"检测到不可重试错误，跳过重试: {type(e).__name__}")
                        break  # 跳出重试循环，尝试下一个后端
                    
                    # 等待后重试
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (retry + 1))  # 减少等待时间
                    continue
        
        # 所有后端都失败，返回错误响应
        duration_ms = (time.time() - start_time) * 1000
        error_msg = f"所有LLM后端都失败（尝试{attempt_count}次）: {str(last_error)}"
        
        logger.error(
            f"❌ LLM流式调用完全失败: attempts={attempt_count}, "
            f"duration={duration_ms:.0f}ms, error={error_msg}"
        )
        
        # 返回最终降级响应
        fallback_content = self.get_template_response(
            request.query,
            {"tool_results": request.tool_results, "error": error_msg}
        )
        
        yield (fallback_content, None)
        yield ("", LLMResponse(
            content=fallback_content,
            backend_used=BackendType.TEMPLATE,
            fallback_used=True,
            attempt_count=attempt_count,
            duration_ms=duration_ms,
            error=error_msg,
            partial_success=False
        ))
    
    async def _call_deepseek(self, request: LLMRequest) -> str:
        """调用DeepSeek API（非流式）"""
        from .llm_client import call_deepseek
        
        return await asyncio.wait_for(
            call_deepseek(
                query=request.query,
                few_shot_examples=request.few_shot_examples,
                tool_results=request.tool_results,
                system_prompt=request.system_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ),
            timeout=self.timeout
        )
    
    async def _call_deepseek_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """调用DeepSeek API（流式）"""
        from .llm_client import call_deepseek_stream
        
        # 构建消息
        messages = request.messages or self._build_messages(request)
        
        async for chunk in call_deepseek_stream(
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            timeout=self.timeout
        ):
            yield chunk
    
    async def _call_ollama(self, request: LLMRequest) -> str:
        """调用Ollama API"""
        from .llm_client import call_ollama
        
        return await asyncio.wait_for(
            call_ollama(
                query=request.query,
                few_shot_examples=request.few_shot_examples,
                tool_results=request.tool_results,
                system_prompt=request.system_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ),
            timeout=self.timeout
        )
    
    def _build_messages(self, request: LLMRequest) -> List[Dict[str, str]]:
        """构建消息列表（用于流式调用）"""
        messages = [{"role": "system", "content": request.system_prompt}]
        
        # 添加Few-Shot示例
        for example in request.few_shot_examples:
            messages.append({"role": "user", "content": example.get("query", "")})
            messages.append({"role": "assistant", "content": example.get("response", "")})
        
        # 添加工具结果
        if request.tool_results:
            from .llm_client import _format_tool_results
            tool_context = _format_tool_results(request.tool_results)
            if tool_context:
                messages.append({"role": "system", "content": f"工具调用结果:\n{tool_context}"})
        
        # 添加当前查询
        messages.append({"role": "user", "content": request.query})
        
        return messages
    
    def get_template_response(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """
        获取模板化响应（最终降级）
        
        Args:
            query: 用户查询
            context: 上下文信息（包含tool_results等）
        
        Returns:
            str: 模板化响应文本
        """
        tool_results = context.get("tool_results", {})
        error = context.get("error", "LLM服务暂时不可用")
        
        logger.info(f"生成模板化响应: query_length={len(query)}, tool_results_count={len(tool_results)}")
        
        # 基础响应模板
        response_parts = [
            f"抱歉，AI分析功能暂时不可用（{error}）。",
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
    
    async def check_backend_health(self, backend: BackendType) -> bool:
        """
        检查后端健康状态
        
        Args:
            backend: 后端类型
        
        Returns:
            bool: 是否健康
        """
        # 检查缓存
        if backend in self._health_cache:
            is_healthy, last_check = self._health_cache[backend]
            if time.time() - last_check < self._health_cache_ttl:
                return is_healthy
        
        # 执行健康检查
        try:
            if backend == BackendType.DEEPSEEK:
                is_healthy = await self._check_deepseek_health()
            elif backend == BackendType.OLLAMA:
                is_healthy = await self._check_ollama_health()
            elif backend == BackendType.TEMPLATE:
                is_healthy = True  # 模板总是健康的
            else:
                is_healthy = False
            
            # 更新缓存
            self._health_cache[backend] = (is_healthy, time.time())
            
            logger.debug(f"后端健康检查: backend={backend.value}, healthy={is_healthy}")
            return is_healthy
        
        except Exception as e:
            logger.warning(f"后端健康检查失败: backend={backend.value}, error={str(e)}")
            # 检查失败时，假设不健康
            self._health_cache[backend] = (False, time.time())
            return False
    
    async def _check_deepseek_health(self) -> bool:
        """检查DeepSeek健康状态"""
        from .llm_client import LLMConfig
        import httpx
        
        if not LLMConfig.DEEPSEEK_API_KEY:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{LLMConfig.DEEPSEEK_BASE_URL}/models",
                    headers={"Authorization": f"Bearer {LLMConfig.DEEPSEEK_API_KEY}"}
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def _check_ollama_health(self) -> bool:
        """检查Ollama健康状态"""
        from .llm_client import LLMConfig
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{LLMConfig.OLLAMA_BASE_URL}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    def _mark_backend_unhealthy(self, backend: BackendType):
        """标记后端为不健康"""
        self._health_cache[backend] = (False, time.time())
        logger.warning(f"标记后端为不健康: {backend.value}")
    
    def _is_non_retryable_error(self, error: Exception) -> bool:
        """判断是否为不可重试的错误"""
        import httpx
        
        # HTTP认证错误、权限错误等不需要重试
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in [401, 403, 404]
        
        # ValueError通常是配置错误，不需要重试
        if isinstance(error, ValueError):
            return True
        
        return False
