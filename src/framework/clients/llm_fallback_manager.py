# -*- coding: utf-8 -*-
"""
LLM降级管理器 - v2.0.0 (策略模式重构)

管理LLM调用的降级策略和错误恢复。
后端调用逻辑已拆分到 backends/ 子模块：
- IBackendClient: 统一接口
- AnthropicClient / DeepSeekClient: 具体实现
- BackendHealthChecker: 健康检查
- TemplateResponseGenerator: 模板降级

降级策略：Anthropic → DeepSeek → Template → Error

版本: v2.0.0
Task 45 - Phase 7 Batch 4 架构重构
"""

import logging
import asyncio
import time
import os
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """LLM后端类型"""
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    SILICONFLOW = "siliconflow"
    GLM = "glm"
    MOONSHOT = "moonshot"
    OLLAMA = "ollama"  # 保留枚举值，实际已禁用
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
    messages: Optional[List[Dict[str, str]]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    model_override: Optional[str] = None  # 蓝绿池指定的模型ID（覆盖后端默认模型）

    def has_vision_content(self) -> bool:
        """检查请求是否包含 image_url 类型的多模态内容"""
        if not self.messages:
            return False
        for msg in self.messages:
            content = msg.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        return True
        return False

    def strip_vision_content(self) -> None:
        """剥离 image_url，保留纯文本，清除 vision 模型覆盖"""
        if not self.messages:
            return
        for msg in self.messages:
            content = msg.get("content")
            if isinstance(content, list):
                text_parts = [
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                msg["content"] = "\n".join(text_parts) if text_parts else ""
        self.model_override = None


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
    LLM降级管理器 - 编排层

    职责：按降级链顺序尝试后端，处理重试和超时。
    后端调用委托给 IBackendClient 实现。
    """

    def __init__(
        self,
        primary_backend: str = "anthropic",
        fallback_backends: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: int = 30,
        enable_health_check: bool = True,
    ):
        self.primary_backend = BackendType(primary_backend)
        self.max_retries = max_retries
        self.timeout = timeout
        self.enable_health_check = enable_health_check

        # 构建降级链
        ollama_enabled = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
        anthropic_enabled = os.getenv("ANTHROPIC_ENABLED", "true").lower() == "true"
        if fallback_backends:
            if not ollama_enabled:
                fallback_backends = [b for b in fallback_backends if b != "ollama"]
            self.fallback_backends = [BackendType(b) for b in fallback_backends]
        else:
            if self.primary_backend == BackendType.ANTHROPIC:
                self.fallback_backends = [BackendType.DEEPSEEK, BackendType.TEMPLATE]
            else:
                self.fallback_backends = [BackendType.TEMPLATE]

        # 初始化后端客户端（延迟导入避免循环依赖）
        self._clients: Dict[BackendType, Any] = {}
        self._health_checker = None
        self._template_generator = None
        self._init_backends()

        # 兼容旧代码的健康缓存
        self._health_cache: Dict[BackendType, tuple[bool, float]] = {}
        self._health_cache_ttl = 60.0

        logger.info(
            f"LLM降级管理器初始化: "
            f"primary={self.primary_backend.value}, "
            f"fallbacks={[b.value for b in self.fallback_backends]}, "
            f"max_retries={self.max_retries}, timeout={self.timeout}s, "
            f"ollama_enabled={ollama_enabled}, anthropic_enabled={anthropic_enabled}"
        )

    def _init_backends(self):
        """延迟初始化后端客户端"""
        try:
            from .backends.anthropic_client import AnthropicClient
            from .backends.deepseek_client import DeepSeekClient
            from .backends.generic_openai_client import GenericOpenAIClient
            from .backends.health_checker import BackendHealthChecker
            from .backends.template_generator import TemplateResponseGenerator

            self._clients[BackendType.ANTHROPIC] = AnthropicClient()
            self._clients[BackendType.DEEPSEEK] = DeepSeekClient()

            # 通用OpenAI兼容后端（按环境变量ENABLED控制）
            if os.getenv("QWEN_ENABLED", "false").lower() == "true":
                self._clients[BackendType.QWEN] = GenericOpenAIClient(
                    backend_name="qwen",
                    base_url=os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                    api_key=os.getenv("QWEN_API_KEY", ""),
                    model=os.getenv("QWEN_MODEL", "qwen-plus"),
                )
                logger.info(f"✅ Qwen后端已注册: model={os.getenv('QWEN_MODEL', 'qwen-plus')}")

            if os.getenv("SILICONFLOW_ENABLED", "false").lower() == "true":
                self._clients[BackendType.SILICONFLOW] = GenericOpenAIClient(
                    backend_name="siliconflow",
                    base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
                    api_key=os.getenv("SILICONFLOW_API_KEY", ""),
                    model=os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen3-8B"),
                )
                logger.info(f"✅ SiliconFlow后端已注册: model={os.getenv('SILICONFLOW_MODEL', 'Qwen/Qwen3-8B')}")

            if os.getenv("GLM_ENABLED", "false").lower() == "true":
                self._clients[BackendType.GLM] = GenericOpenAIClient(
                    backend_name="glm",
                    base_url=os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
                    api_key=os.getenv("GLM_API_KEY", ""),
                    model=os.getenv("GLM_MODEL", "glm-4.7-flash"),
                )
                logger.info(f"✅ GLM后端已注册: model={os.getenv('GLM_MODEL', 'glm-4.7-flash')}")

            if os.getenv("MOONSHOT_ENABLED", "false").lower() == "true":
                self._clients[BackendType.MOONSHOT] = GenericOpenAIClient(
                    backend_name="moonshot",
                    base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
                    api_key=os.getenv("MOONSHOT_API_KEY", ""),
                    model=os.getenv("MOONSHOT_MODEL", "kimi-k2-0905-preview"),
                )
                logger.info(f"✅ Moonshot后端已注册: model={os.getenv('MOONSHOT_MODEL', 'kimi-k2-0905-preview')}")

            self._health_checker = BackendHealthChecker()
            self._template_generator = TemplateResponseGenerator()

            # YAML 池自动注册：补充 XXX_ENABLED 未覆盖的后端
            self._auto_register_from_yaml_pool()

        except ImportError as e:
            logger.warning(f"后端客户端初始化失败(降级到内联模式): {e}")

    def _auto_register_from_yaml_pool(self):
        """从 YAML 蓝绿池自动注册未注册的后端客户端"""
        try:
            from ...applications.fitness.config.model_routing import _get_yaml_pool
            from .backends.generic_openai_client import GenericOpenAIClient
        except ImportError:
            return

        enabled, pool = _get_yaml_pool()
        if not enabled or not pool:
            return

        seen_backends = set()
        for entry in pool:
            backend_name = entry.backend.lower()
            if backend_name in seen_backends:
                continue
            seen_backends.add(backend_name)

            # 跳过已注册的后端（显式配置优先）
            try:
                backend_type = BackendType(backend_name)
            except ValueError:
                logger.warning(f"⚠️ YAML池中未知后端类型: {backend_name}")
                continue

            if backend_type in self._clients:
                continue

            # 从环境变量获取 API_KEY
            api_key = os.getenv(f"{backend_name.upper()}_API_KEY", "")
            if not api_key:
                logger.warning(
                    f"⚠️ YAML池后端 {backend_name} 无 {backend_name.upper()}_API_KEY，跳过自动注册"
                )
                continue

            client = GenericOpenAIClient(
                backend_name=backend_name,
                base_url=entry.api_base,
                api_key=api_key,
                model=entry.model,
            )
            self._clients[backend_type] = client
            logger.info(
                f"🔄 YAML池自动注册: {backend_name}/{entry.model} "
                f"(api_base={entry.api_base})"
            )

    # ─── 非流式调用 ──────────────────────────────────────

    async def call_with_fallback(
        self, request: LLMRequest, *, primary_backend: Optional[str] = None,
        fallback_backends: Optional[List[str]] = None,
    ) -> LLMResponse:
        """带降级的LLM调用（非流式）

        Args:
            primary_backend: 覆盖默认主后端（蓝绿池路由用）
            fallback_backends: 覆盖默认降级链
        """
        start_time = time.time()
        effective_primary = BackendType(primary_backend) if primary_backend else self.primary_backend
        effective_fallbacks = [BackendType(b) for b in fallback_backends] if fallback_backends else self.fallback_backends
        backends_to_try = [effective_primary] + effective_fallbacks
        last_error = None
        attempt_count = 0

        for backend in backends_to_try:
            if backend != BackendType.TEMPLATE and self.enable_health_check:
                if not await self.check_backend_health(backend):
                    logger.warning(f"跳过不健康的后端: {backend.value}")
                    continue

            for retry in range(self.max_retries):
                attempt_count += 1
                try:
                    logger.info(
                        f"尝试调用LLM: backend={backend.value}, "
                        f"attempt={attempt_count}, retry={retry + 1}/{self.max_retries}"
                    )

                    if backend == BackendType.TEMPLATE:
                        content = self.get_template_response(
                            request.query, {"tool_results": request.tool_results}
                        )
                        duration_ms = (time.time() - start_time) * 1000
                        error_msg = (
                            f"所有LLM后端都失败（尝试{attempt_count}次）: {str(last_error)}"
                            if last_error else None
                        )
                        logger.warning(
                            f"⚠️ 使用模板响应: attempts={attempt_count}, "
                            f"duration={duration_ms:.0f}ms"
                        )
                        return LLMResponse(
                            content=content, backend_used=BackendType.TEMPLATE,
                            fallback_used=True, attempt_count=attempt_count,
                            duration_ms=duration_ms, error=error_msg,
                            partial_success=False,
                        )

                    content = await self._call_backend(backend, request)

                    # 空响应检测：正常LLM调用不可能返回空内容
                    if not content or not content.strip():
                        logger.warning(
                            f"⚠️ LLM调用返回空内容: backend={backend.value}, "
                            f"attempt={attempt_count} — 视为失败，继续降级"
                        )
                        self._mark_backend_unhealthy(backend)
                        if retry < self.max_retries - 1:
                            await asyncio.sleep(1.0 * (retry + 1))
                        continue

                    duration_ms = (time.time() - start_time) * 1000
                    fallback_used = backend != effective_primary
                    logger.info(
                        f"✅ LLM调用成功: backend={backend.value}, "
                        f"fallback={fallback_used}, attempts={attempt_count}, "
                        f"duration={duration_ms:.0f}ms, length={len(content)}"
                    )
                    return LLMResponse(
                        content=content, backend_used=backend,
                        fallback_used=fallback_used, attempt_count=attempt_count,
                        duration_ms=duration_ms,
                    )

                except asyncio.TimeoutError as e:
                    last_error = e
                    logger.warning(
                        f"⏱️ LLM调用超时: backend={backend.value}, "
                        f"retry={retry + 1}/{self.max_retries}, timeout={self.timeout}s"
                    )
                    self._mark_backend_unhealthy(backend)
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (retry + 1))
                    continue

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"❌ LLM调用失败: backend={backend.value}, "
                        f"retry={retry + 1}/{self.max_retries}, error={str(e)}"
                    )
                    self._mark_backend_unhealthy(backend)
                    # Vision 降级：剥离图片，切换纯文本模式
                    if request.has_vision_content() and self._is_vision_error(e):
                        logger.warning(
                            f"📷 Vision降级: {backend.value} 不支持图片，"
                            f"切换纯文本模式"
                        )
                        request.strip_vision_content()
                        break  # 跳出 retry，用下一个后端重试（纯文本）
                    if self._is_non_retryable_error(e):
                        break
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (retry + 1))
                    continue

            if backend == BackendType.TEMPLATE:
                break

        # 所有后端失败，最终模板降级
        return self._final_template_fallback(request, start_time, attempt_count, last_error)

    # ─── 流式调用 ─────────────────────────────────────────

    async def call_with_fallback_stream(
        self, request: LLMRequest, *, primary_backend: Optional[str] = None,
        fallback_backends: Optional[List[str]] = None,
    ) -> AsyncIterator[tuple[str, Optional[LLMResponse]]]:
        """带降级的LLM流式调用

        Args:
            primary_backend: 覆盖默认主后端（蓝绿池路由用）
            fallback_backends: 覆盖默认降级链
        """
        start_time = time.time()
        effective_primary = BackendType(primary_backend) if primary_backend else self.primary_backend
        effective_fallbacks = [BackendType(b) for b in fallback_backends] if fallback_backends else self.fallback_backends
        backends_to_try = [effective_primary] + effective_fallbacks
        last_error = None
        attempt_count = 0
        accumulated_content = ""

        for backend in backends_to_try:
            if backend != BackendType.TEMPLATE and self.enable_health_check:
                if not await self.check_backend_health(backend):
                    logger.warning(f"跳过不健康的后端: {backend.value}")
                    continue

            for retry in range(self.max_retries):
                attempt_count += 1
                accumulated_content = ""

                try:
                    logger.info(
                        f"尝试流式调用LLM: backend={backend.value}, "
                        f"attempt={attempt_count}, retry={retry + 1}/{self.max_retries}"
                    )

                    if backend == BackendType.TEMPLATE:
                        content = self.get_template_response(
                            request.query, {"tool_results": request.tool_results}
                        )
                        yield (content, None)
                        duration_ms = (time.time() - start_time) * 1000
                        yield ("", LLMResponse(
                            content=content, backend_used=backend,
                            fallback_used=True, attempt_count=attempt_count,
                            duration_ms=duration_ms, partial_success=False,
                        ))
                        return

                    async for chunk in self._call_backend_stream(backend, request):
                        accumulated_content += chunk
                        yield (chunk, None)

                    # 空响应检测：正常LLM调用不可能返回0个chunk
                    if not accumulated_content.strip():
                        logger.warning(
                            f"⚠️ LLM流式调用返回空内容: backend={backend.value}, "
                            f"attempt={attempt_count} — 视为失败，继续降级"
                        )
                        self._mark_backend_unhealthy(backend)
                        if retry < self.max_retries - 1:
                            await asyncio.sleep(1.0 * (retry + 1))
                        continue

                    duration_ms = (time.time() - start_time) * 1000
                    fallback_used = backend != effective_primary
                    logger.info(
                        f"✅ LLM流式调用成功: backend={backend.value}, "
                        f"fallback={fallback_used}, attempts={attempt_count}, "
                        f"duration={duration_ms:.0f}ms, length={len(accumulated_content)}"
                    )
                    yield ("", LLMResponse(
                        content=accumulated_content, backend_used=backend,
                        fallback_used=fallback_used, attempt_count=attempt_count,
                        duration_ms=duration_ms,
                    ))
                    return

                except (asyncio.TimeoutError, Exception) as e:
                    last_error = e
                    is_timeout = isinstance(e, asyncio.TimeoutError)
                    logger.warning(
                        f"{'⏱️' if is_timeout else '❌'} LLM流式调用"
                        f"{'超时' if is_timeout else '失败'}: backend={backend.value}, "
                        f"retry={retry + 1}/{self.max_retries}, "
                        f"partial_content={len(accumulated_content)}"
                    )
                    self._mark_backend_unhealthy(backend)

                    if accumulated_content:
                        duration_ms = (time.time() - start_time) * 1000
                        yield ("", LLMResponse(
                            content=accumulated_content, backend_used=backend,
                            fallback_used=True, attempt_count=attempt_count,
                            duration_ms=duration_ms, error=str(e),
                            partial_success=True,
                        ))
                        return

                    # Vision 降级：检测到 vision 错误时剥离图片，切换纯文本模式
                    if request.has_vision_content() and self._is_vision_error(e):
                        logger.warning(
                            f"📷 Vision降级: {backend.value} 不支持图片，"
                            f"切换纯文本模式"
                        )
                        request.strip_vision_content()
                        yield (
                            "📷 当前模型暂不支持图片识别，已切换为文本模式分析您的问题。\n\n",
                            None,
                        )
                        break  # 跳出 retry 循环，用下一个后端重试（纯文本）

                    if not is_timeout and self._is_non_retryable_error(e):
                        break
                    if retry < self.max_retries - 1:
                        # 指数退避: 200ms → 400ms → 800ms → 1600ms → 2000ms(上限)
                        delay = min(0.2 * (2 ** retry), 2.0)
                        await asyncio.sleep(delay)
                    continue

        # 所有后端失败
        duration_ms = (time.time() - start_time) * 1000
        error_msg = f"所有LLM后端都失败（尝试{attempt_count}次）: {str(last_error)}"
        logger.error(f"❌ LLM流式调用完全失败: attempts={attempt_count}, duration={duration_ms:.0f}ms")
        fallback_content = self.get_template_response(
            request.query, {"tool_results": request.tool_results, "error": error_msg}
        )
        yield (fallback_content, None)
        yield ("", LLMResponse(
            content=fallback_content, backend_used=BackendType.TEMPLATE,
            fallback_used=True, attempt_count=attempt_count,
            duration_ms=duration_ms, error=error_msg, partial_success=False,
        ))

    # ─── 后端调用委托 ────────────────────────────────────

    async def _call_backend(self, backend: BackendType, request: LLMRequest) -> str:
        """委托给对应的IBackendClient"""
        client = self._clients.get(backend)
        if client:
            return await client.call(request, timeout=self.timeout)
        # 降级到内联调用（兼容旧代码路径）
        return await self._call_backend_inline(backend, request)

    async def _call_backend_stream(
        self, backend: BackendType, request: LLMRequest
    ) -> AsyncIterator[str]:
        """委托给对应的IBackendClient（流式）"""
        client = self._clients.get(backend)
        if client:
            async for chunk in client.call_stream(request, timeout=self.timeout):
                yield chunk
            return
        # 降级到内联调用
        async for chunk in self._call_backend_stream_inline(backend, request):
            yield chunk

    async def _call_backend_inline(self, backend: BackendType, request: LLMRequest) -> str:
        """内联后端调用（兼容路径，当backends模块不可用时）"""
        if backend == BackendType.ANTHROPIC:
            from .llm_client import call_anthropic
            return await asyncio.wait_for(
                call_anthropic(
                    query=request.query, few_shot_examples=request.few_shot_examples,
                    tool_results=request.tool_results, system_prompt=request.system_prompt,
                    max_tokens=request.max_tokens, temperature=request.temperature,
                ), timeout=self.timeout,
            )
        elif backend == BackendType.DEEPSEEK:
            from .llm_client import call_deepseek
            return await asyncio.wait_for(
                call_deepseek(
                    query=request.query, few_shot_examples=request.few_shot_examples,
                    tool_results=request.tool_results, system_prompt=request.system_prompt,
                    max_tokens=request.max_tokens, temperature=request.temperature,
                ), timeout=self.timeout,
            )
        elif backend == BackendType.OLLAMA:
            from .llm_client import call_ollama
            return await asyncio.wait_for(
                call_ollama(
                    query=request.query, few_shot_examples=request.few_shot_examples,
                    tool_results=request.tool_results, system_prompt=request.system_prompt,
                    max_tokens=request.max_tokens, temperature=request.temperature,
                ), timeout=self.timeout,
            )
        raise ValueError(f"未知的后端类型: {backend}")

    async def _call_backend_stream_inline(
        self, backend: BackendType, request: LLMRequest
    ) -> AsyncIterator[str]:
        """内联流式调用（兼容路径）"""
        messages = request.messages or self._build_messages(request)
        if backend == BackendType.ANTHROPIC:
            from .llm_client import call_anthropic_stream
            async for chunk in call_anthropic_stream(
                messages=messages, max_tokens=request.max_tokens,
                temperature=request.temperature, timeout=self.timeout,
            ):
                yield chunk
        elif backend == BackendType.DEEPSEEK:
            from .llm_client import call_deepseek_stream
            async for chunk in call_deepseek_stream(
                messages=messages, max_tokens=request.max_tokens,
                temperature=request.temperature, timeout=self.timeout,
            ):
                yield chunk
        elif backend == BackendType.OLLAMA:
            from .llm_client import call_ollama
            content = await self._call_backend_inline(backend, request)
            yield content
        else:
            raise ValueError(
                f"后端 {backend.value} 未注册且无内联实现，"
                f"请检查 YAML 池配置和 {backend.value.upper()}_API_KEY 环境变量"
            )

    # ─── 公共辅助方法（保持向后兼容） ────────────────────

    def get_template_response(self, query: str, context: Dict[str, Any]) -> str:
        if self._template_generator:
            return self._template_generator.generate(query, context)
        # 内联降级
        error = context.get("error", "LLM服务暂时不可用")
        return f"抱歉，AI分析功能暂时不可用（{error}）。\n\n📝 您的查询：{query}\n\n💡 请稍后重试。"

    async def check_backend_health(self, backend: BackendType) -> bool:
        if backend == BackendType.TEMPLATE:
            return True
        client = self._clients.get(backend)
        if client and self._health_checker:
            return await self._health_checker.is_healthy(backend.value, client)
        # 降级到缓存检查
        if backend in self._health_cache:
            is_ok, last_check = self._health_cache[backend]
            if time.time() - last_check < self._health_cache_ttl:
                return is_ok
        return True  # 无法检查时假设健康

    def _mark_backend_unhealthy(self, backend: BackendType):
        self._health_cache[backend] = (False, time.time())
        if self._health_checker:
            self._health_checker.mark_unhealthy(backend.value)
        logger.warning(f"标记后端为不健康: {backend.value}")

    def _is_non_retryable_error(self, error: Exception) -> bool:
        import httpx
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            # 4xx 客户端错误一律不重试（400/401/403/404/422 等）
            # 请求本身有问题，重试也不会成功
            if 400 <= status < 500:
                return True
        if isinstance(error, ValueError):
            return True
        return False

    def _is_vision_error(self, error: Exception) -> bool:
        """检测是否为 vision 不支持的错误（模型不支持图片内容）"""
        err_str = str(error).lower()
        vision_error_patterns = [
            "image", "vision", "multimodal", "not support",
            "invalid content type", "image_url",
        ]
        return any(p in err_str for p in vision_error_patterns)

    def _build_messages(self, request: LLMRequest) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": request.system_prompt}]
        for ex in request.few_shot_examples:
            messages.append({"role": "user", "content": ex.get("query", "")})
            messages.append({"role": "assistant", "content": ex.get("response", "")})
        if request.tool_results:
            from .llm_client import _format_tool_results
            ctx = _format_tool_results(request.tool_results)
            if ctx:
                messages.append({"role": "system", "content": f"工具调用结果:\n{ctx}"})
        messages.append({"role": "user", "content": request.query})
        return messages

    def _final_template_fallback(
        self, request: LLMRequest, start_time: float,
        attempt_count: int, last_error: Optional[Exception],
    ) -> LLMResponse:
        attempt_count += 1
        try:
            content = self.get_template_response(
                request.query, {"tool_results": request.tool_results}
            )
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"所有LLM后端都失败（尝试{attempt_count}次）: {str(last_error)}"
            logger.error(
                f"❌ LLM调用完全失败，使用模板响应: attempts={attempt_count}, "
                f"duration={duration_ms:.0f}ms"
            )
            return LLMResponse(
                content=content, backend_used=BackendType.TEMPLATE,
                fallback_used=True, attempt_count=attempt_count,
                duration_ms=duration_ms, error=error_msg, partial_success=False,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"所有后端包括模板都失败: {str(e)}"
            logger.critical(error_msg)
            return LLMResponse(
                content=f"系统错误: {error_msg}",
                backend_used=BackendType.TEMPLATE, fallback_used=True,
                attempt_count=attempt_count, duration_ms=duration_ms,
                error=error_msg, partial_success=False,
            )
